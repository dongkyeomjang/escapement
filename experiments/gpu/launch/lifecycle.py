"""One vLLM serving lifecycle on the A6000 server (GPU directive G-02).

Shared by the gate (GTASK03), survival (GTASK04) and step-cost (GTASK05)
drivers. Rules it enforces (KNOWN_PITFALLS 1, 2):

* every path is absolute;
* the server is stopped through the PID this module started, never by pattern;
* ``nvidia-smi --query-compute-apps`` is captured before start, at ready and
  after stop, and any process other than this server's on the GPU makes the
  lifecycle ``INVALID`` (directive G-02 2.3);
* provenance (git HEAD, patch state, full command, env) goes next to the logs.

Fixed arguments every measurement run must state explicitly (G-02 2.3) are
checked in ``REQUIRED_FLAGS`` so a driver cannot silently rely on a default.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

import psutil

REPO = Path(__file__).resolve().parents[3]
VENV = Path("/home/csdc/kyeom/envs/vllm-0.22.0")
REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
PATCH_SH = REPO / "experiments/gpu/patches/vllm-0.22.0/apply.sh"
COLLECTOR = REPO / "experiments/gpu/obs/kv_events_collector.py"

REQUIRED_FLAGS = (
    "--block-size", "--num-gpu-blocks-override", "--max-num-seqs",
    "--max-num-batched-tokens", "--compilation-config",
    "--enable-prompt-tokens-details", "--max-model-len", "--seed", "--revision",
)


def base_args(*, num_gpu_blocks: int, max_num_seqs: int, max_num_batched_tokens: int,
              capture_sizes: list[int], port: int = 8100, extra: list[str] | None = None) -> list[str]:
    args = [
        "serve", "Qwen/Qwen3-4B", "--revision", REVISION, "--dtype", "bfloat16",
        "--max-model-len", "8192", "--seed", "20260929",
        "--host", "127.0.0.1", "--port", str(port),
        "--generation-config", "vllm", "--enable-prompt-tokens-details",
        "--block-size", "16",
        "--num-gpu-blocks-override", str(num_gpu_blocks),
        "--max-num-seqs", str(max_num_seqs),
        "--max-num-batched-tokens", str(max_num_batched_tokens),
        "--compilation-config", json.dumps({"cudagraph_capture_sizes": capture_sizes}),
    ]
    return args + (extra or [])


# vLLM's publisher binds only for "*", ipc:// or inproc:// endpoints and connects
# otherwise (vllm/distributed/kv_events.py:387-397). A tcp://127.0.0.1 endpoint
# made both sides connect and nothing arrived (GTASK03 first gate run). An ipc
# socket binds on the server side and stays local to this host.
KV_IPC_DIR = Path("/home/csdc/kyeom/envs/ipc")
KV_ENDPOINT = f"ipc://{KV_IPC_DIR}/kv_events.ipc"


def kv_events_args(endpoint: str = KV_ENDPOINT) -> list[str]:
    cfg = {"enable_kv_cache_events": True, "publisher": "zmq",
           "endpoint": endpoint, "topic": ""}
    return ["--kv-events-config", json.dumps(cfg)]


def _gpu_apps() -> list[dict]:
    out = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory,gpu_uuid",
         "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True).stdout
    rows = []
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        pid, name, mem, uuid = [x.strip() for x in line.split(",")]
        rows.append({"pid": int(pid), "name": name, "mem_mib": int(mem), "gpu_uuid": uuid})
    return rows


def _gpu0_uuid() -> str:
    out = subprocess.run(["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"],
                         capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        idx, uuid = [x.strip() for x in line.split(",")]
        if idx == "0":
            return uuid
    raise RuntimeError("GPU 0 not found")


def patch_state() -> str:
    out = subprocess.run(["bash", str(PATCH_SH), "status"], capture_output=True, text=True)
    return out.stdout + out.stderr


def _tree_cpu_s(pid: int) -> float | None:
    try:
        p = psutil.Process(pid)
        procs = [p] + p.children(recursive=True)
        total = 0.0
        for q in procs:
            try:
                t = q.cpu_times()
                total += t.user + t.system
            except psutil.NoSuchProcess:
                pass
        return total
    except psutil.NoSuchProcess:
        return None


def _get(url: str, timeout: float = 5.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode()


class Lifecycle:
    """Context manager: start server (and collector), yield, stop by PID."""

    def __init__(self, out_dir: Path, server_args: list[str], *, obs: bool,
                 kv_events: bool, port: int = 8100, kv_endpoint: str = KV_ENDPOINT,
                 ready_timeout_s: int = 900, extra_env: dict | None = None):
        if not Path(out_dir).is_absolute():
            raise ValueError("out_dir must be absolute (KNOWN_PITFALLS 1)")
        missing = [f for f in REQUIRED_FLAGS if f not in server_args]
        if missing:
            raise ValueError(f"required explicit flags missing: {missing}")
        self.out = Path(out_dir)
        self.args = server_args
        self.obs = obs
        self.kv_events = kv_events
        self.port = port
        self.kv_endpoint = kv_endpoint
        self.ready_timeout_s = ready_timeout_s
        self.extra_env = extra_env or {}
        self.base = f"http://127.0.0.1:{port}"
        self.meta: dict = {}
        self.srv: subprocess.Popen | None = None
        self.col: subprocess.Popen | None = None

    # -- helpers -----------------------------------------------------------
    def metrics(self) -> str:
        return _get(self.base + "/metrics")

    def server_cpu_s(self) -> float | None:
        return _tree_cpu_s(self.srv.pid) if self.srv else None

    def collector_cpu_s(self) -> float | None:
        return _tree_cpu_s(self.col.pid) if self.col else None

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "Lifecycle":
        self.out.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.update({"CUDA_VISIBLE_DEVICES": "0", "HF_HOME": "/mnt/nvme/hf",
                    "HF_HUB_OFFLINE": "1", "HF_HUB_ENABLE_HF_TRANSFER": "0"})
        if self.obs:
            env["ESCAPEMENT_OBS"] = "1"
        else:
            env.pop("ESCAPEMENT_OBS", None)
        env.update(self.extra_env)
        gpu0 = _gpu0_uuid()
        self.meta.update({
            "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repo_head": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                        capture_output=True, text=True).stdout.strip(),
            "repo_dirty_entries": len(subprocess.run(
                ["git", "-C", str(REPO), "status", "--porcelain"],
                capture_output=True, text=True).stdout.splitlines()),
            "patch_status": patch_state(),
            "command": [str(VENV / "bin/vllm")] + self.args,
            "env_selected": {k: env.get(k) for k in (
                "CUDA_VISIBLE_DEVICES", "HF_HOME", "HF_HUB_OFFLINE", "ESCAPEMENT_OBS",
                "VLLM_USE_V2_MODEL_RUNNER", "VLLM_LOGGING_LEVEL")},
            "obs": self.obs, "kv_events": self.kv_events,
            "gpu0_uuid": gpu0, "gpu_apps_pre": _gpu_apps(),
        })
        (self.out / "env.txt").write_text("\n".join(f"{k}={v}" for k, v in sorted(env.items())))
        try:
            _get(self.base + "/health", timeout=1)
            raise RuntimeError(f"port {self.port} already serving")
        except OSError:
            pass
        if self.kv_events:
            KV_IPC_DIR.mkdir(parents=True, exist_ok=True)
            sock = Path(self.kv_endpoint.removeprefix("ipc://"))
            if sock.exists():
                sock.unlink()
            self.col = subprocess.Popen(
                [str(VENV / "bin/python"), str(COLLECTOR), "--endpoint",
                 self.kv_endpoint, "--out", str(self.out / "kv_events.jsonl")],
                stdout=open(self.out / "collector.log", "w"), stderr=subprocess.STDOUT, env=env)
            self.meta["collector_pid"] = self.col.pid
        log = open(self.out / "server.log", "w")
        self.srv = subprocess.Popen([str(VENV / "bin/vllm")] + self.args, stdout=log,
                                    stderr=subprocess.STDOUT, env=env)
        self.meta["server_pid"] = self.srv.pid
        t0 = time.time()
        while True:
            if self.srv.poll() is not None:
                self.meta["startup_failed"] = True
                self._finish()
                raise RuntimeError(f"server exited during startup ({self.srv.returncode})")
            try:
                _get(self.base + "/health", timeout=1)
                break
            except OSError:
                pass
            if time.time() - t0 > self.ready_timeout_s:
                self._finish()
                raise RuntimeError("server not ready in time")
            time.sleep(1)
        self.meta["ready_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.meta["startup_s"] = round(time.time() - t0, 1)
        apps = _gpu_apps()
        self.meta["gpu_apps_ready"] = apps
        own = {self.srv.pid} | {c.pid for c in psutil.Process(self.srv.pid).children(recursive=True)}
        foreign = [a for a in apps if a["pid"] not in own]
        self.meta["foreign_gpu_processes_ready"] = foreign
        self.meta["own_on_gpu0_only"] = all(a["gpu_uuid"] == gpu0 for a in apps if a["pid"] in own)
        self._write_meta()
        return self

    def _finish(self) -> None:
        if self.srv and self.srv.poll() is None:
            self.srv.send_signal(signal.SIGTERM)
            try:
                self.srv.wait(timeout=60)
            except subprocess.TimeoutExpired:
                self.srv.kill()
                self.srv.wait()
        if self.col and self.col.poll() is None:
            time.sleep(1.0)  # let the last event batches arrive
            self.col.send_signal(signal.SIGTERM)
            try:
                self.col.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.col.kill()
                self.col.wait()
        self.meta["stop_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        time.sleep(2)
        self.meta["gpu_apps_post"] = _gpu_apps()
        self._write_meta()

    def __exit__(self, *exc) -> None:
        self._finish()

    def _write_meta(self) -> None:
        (self.out / "lifecycle.json").write_text(json.dumps(self.meta, indent=2))

    def valid(self) -> tuple[bool, list[str]]:
        why = []
        if self.meta.get("gpu_apps_pre"):
            why.append("GPU process present before start")
        if self.meta.get("foreign_gpu_processes_ready"):
            why.append("foreign GPU process at ready")
        if not self.meta.get("own_on_gpu0_only", False):
            why.append("server process not confined to GPU 0")
        return (not why, why)
