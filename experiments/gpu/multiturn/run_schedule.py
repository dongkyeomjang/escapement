#!/usr/bin/env python3
"""Run a fixed list of GPU multi-turn lifecycles in order (pilot or main).

The schedule is a JSON list of ``{"tag", "plan", "config", "n", "stream"}``
committed with the prereg. Each entry runs ``gpu_mt_runner.py`` into
``<RUN>/<tag>/``; a finished entry leaves ``<RUN>/<tag>/done`` and is skipped
on a restart (a lifecycle that did not finish is re-run from scratch in a
fresh directory ``<tag>.retry<k>`` only if ``--retry`` is given; the failed
directory is kept). Meant to be started detached (``setsid nohup``) so it
survives the controlling session. Do not edit the scripts while it runs
(KNOWN_PITFALLS 5).

usage: run_schedule.py --schedule <abs json> --run-dir <abs> [--retry]
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PY = "/home/csdc/kyeom/envs/vllm-0.22.0/bin/python"


def log(run: Path, msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}"
    with (run / "sequence.log").open("a") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--retry", action="store_true")
    a = ap.parse_args()
    if not (a.schedule.is_absolute() and a.run_dir.is_absolute()):
        raise SystemExit("paths must be absolute (KNOWN_PITFALLS 1)")
    a.run_dir.mkdir(parents=True, exist_ok=True)
    sched = json.loads(a.schedule.read_text())
    for e in sched:
        d = a.run_dir / e["tag"]
        if (d / "done").exists():
            log(a.run_dir, f"skip {e['tag']} (done)")
            continue
        if d.exists():
            if not a.retry:
                log(a.run_dir, f"stop: {e['tag']} exists without done (use --retry)")
                return 2
            k = 1
            while (a.run_dir / f"{e['tag']}.retry{k}").exists():
                k += 1
            d = a.run_dir / f"{e['tag']}.retry{k}"
        cmd = [PY, str(HERE / "gpu_mt_runner.py"), "--plan", e["plan"], "--config", e["config"],
               "--n", str(e["n"]), "--out-dir", str(d)] + (["--stream"] if e["stream"] else [])
        log(a.run_dir, f"start {e['tag']} -> {d.name}")
        with open(a.run_dir / f"{d.name}.stdout", "w") as fh:
            rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())}).returncode
        log(a.run_dir, f"end {e['tag']} rc={rc}")
        if rc == 0:
            (d / "done").write_text(datetime.now(timezone.utc).isoformat() + "\n")
        else:
            log(a.run_dir, f"lifecycle {e['tag']} not valid (rc={rc}); continuing")
    log(a.run_dir, "schedule finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
