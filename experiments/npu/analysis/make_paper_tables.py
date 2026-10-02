#!/usr/bin/env python3
"""Paper table and figure data (P* tables, F_* CSVs) for directive 08 work D.

Same contract as ``make_tables.py``: each table is built by one named function
from named artifacts, written to ``results/tables/P*.md`` + ``P*.csv``, and
checked against the value a TASK/GTASK document already records. **A mismatch
is reported, never repaired.** Figure data go to ``results/tables/figures/``.

Inputs are committed files or analysis outputs that already exist under
``results/``; nothing is measured and no simulator sweep is run. GPU values
are read from the GPU branch with ``git show origin/gpu-a6000:<path>`` (never
checked out); each GPU input is cited with that file's last commit on the
branch. A table whose input is missing is recorded as not built, with the
reason, in ``results/tables/paper_manifest.json``.

    env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all
    env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --table P02
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))

from make_tables import Check, render_md  # noqa: E402

S3 = REPO / "results/npu/stage3"
MAIN_VERDICT = S3 / "20260930-main/main_verdict.json"
HI_VERDICT = S3 / "20261001-hiload/hiload_verdict.json"
SIM_VERDICT = S3 / "20261002-simblind/simblind_verdict.json"
QUEUE_OBS = S3 / "queue_obs/queue_obs.json"
STATIONARITY = S3 / "20260930-main/stationarity.json"
R1 = S3 / "model_v0_retro/r1.json"
R5P = S3 / "model_v0_retro/r5p.json"
V11_MAIN = S3 / "predict/v11_main_predictions.json"
AUDIT = S3 / "step_audit/audit.json"
EXPLAIN = S3 / "step_audit/explain.json"
B2_DIAG = S3 / "v12_dev/b2_diag.json"
FREEZE = S3 / "v12_dev/freeze_check.json"

GPU_BRANCH = "origin/gpu-a6000"
G_SURV_PRED = "experiments/gpu/survival/prediction/predictions.json"
G_MT_PRED = "experiments/gpu/multiturn/plans/PREDICTIONS.json"
G04 = "docs/research/gpu/GTASK04.md"
G11 = "docs/research/gpu/GTASK11.md"
G12 = "docs/research/gpu/GTASK12.md"
G13 = "docs/research/gpu/GTASK13.md"
G14 = "docs/research/gpu/GTASK14.md"
G16 = "docs/research/gpu/GTASK16.md"

#: GPU null reuse predictor fixed in GPU_MULTITURN_PREREG revision 1 (GTASK11:
#: "NPU 영 재사용 0.84718(TASK82 확증 10 cell 합산 5,771/6,812)").
GPU_REUSE_NULL = 0.84718

#: BASE queue depth of the v1 B2 fixed point, computed before measurement and
#: recorded in HILOAD_PREREG.md §2 (TASK86). Not recomputed here.
NPU_B2_QUEUE = {12: ("0.058", "0.08"), 14: ("0.27", "0.50"), 16: ("0.51", "1.24")}

FIG_DIR_NAME = "figures"


# -- provenance helpers ------------------------------------------------------

def _git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise MissingInput(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def gpu_show(path: str) -> str:
    return _git("show", f"{GPU_BRANCH}:{path}")


def gpu_commit(path: str) -> str:
    return _git("log", GPU_BRANCH, "--format=%h", "-1", "--", path).strip()


def npu_commit(path: str) -> str:
    return _git("log", "--format=%h", "-1", "--", path).strip()


def gpu_ref(path: str) -> str:
    return f"{GPU_BRANCH}:{path} @ {gpu_commit(path)}"


def npu_doc(task: str) -> str:
    p = f"docs/research/{task}.md"
    return f"{p} @ {npu_commit(p)}"


class MissingInput(RuntimeError):
    pass


def load(path: Path):
    if not path.exists():
        raise MissingInput(f"없음: {path.relative_to(REPO)}")
    return json.loads(path.read_text())


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def f3(x) -> str:
    return "" if x is None else f"{x:.3f}"


def f4(x) -> str:
    return "" if x is None else f"{x:.4f}"


def fmt(x, dp: int = 4) -> str:
    return "" if x is None else f"{x:.{dp}f}"


# -- markdown table parsing (GPU docs are read, never edited) ----------------

def num(s: str) -> float:
    """First number in a cell: '**0.669** (988/1,477)' -> 0.669."""
    s = s.replace("−", "-").replace("**", "")
    m = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", s)
    if not m:
        raise ValueError(f"숫자 없음: {s!r}")
    return float(m.group(0).replace(",", ""))


def nums(s: str) -> list[float]:
    s = s.replace("−", "-").replace("**", "")
    return [float(x.replace(",", "")) for x in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", s)]


def table_after(text: str, marker: str) -> list[list[str]]:
    """Rows (without header/separator) of the first markdown table after marker."""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if marker in ln)
    i = start if lines[start].startswith("|") else start + 1
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    rows = []
    for ln in lines[i + 2:]:
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]
        rows.append(cells)
    return rows


# -- shared extraction --------------------------------------------------------

def npu_cells():
    """Per-cell observed/predicted reuse and ratio for TASK82 (N=6-12) and TASK87 (N=14,16)."""
    mv = load(MAIN_VERDICT)
    hv = load(HI_VERDICT)
    v11 = load(V11_MAIN)
    out = []
    for key, c in mv["cells"].items():
        cfg, n = key.split(".n")
        n = int(n)
        pop = "blind_exploratory_cell" if n == 12 else "blind_confirm_cell"
        row = {"substrate": "NPU", "cell": key, "N": n, "config": cfg,
               "reuse_obs": c["reuse_obs"], "reuse_k": c["reuse"],
               "ttft_s": c.get("ttft_turn_ge1_median_s"),
               "mean_running_obs": c.get("mean_running_obs"),
               "pred": {}, "population": pop, "source": "TASK82",
               "src_file": rel(MAIN_VERDICT)}
        for p in ("analytic", "sim_default", "sim_observed"):
            row["pred"][{"analytic": "analytic_v1"}.get(p, p)] = {
                "reuse": c["pred"][p]["reuse"], "ratio": c["pred"][p].get("ratio")}
        if n == 12:
            row["mean_running_obs"] = mv["n12"][cfg]["mean_running_obs"]
            if "ratio" in mv["n12"][cfg]:
                row["ratio_obs"] = mv["n12"][cfg]["ratio"]["m"]
                row["ratio_ci"] = mv["n12"][cfg]["ratio"]["ci"]
        elif key in mv["5.2"]["cells"]:
            row["ratio_obs"] = mv["5.2"]["cells"][key]["m"]
            row["ratio_ci"] = mv["5.2"]["cells"][key]["ci"]
        vc = v11["cells"].get(str(n), {}).get(cfg)
        if vc is not None:
            row["pred"]["v1.1"] = {"reuse": vc["v11"]["reuse_rate"],
                                   "ratio": vc["v11"]["ratio_to_base"],
                                   "population": "dev_set" if n == 12 else "post_hoc"}
        out.append(row)
    for key, c in hv["cells"].items():
        cfg, n = key.split(".n")
        n = int(n)
        row = {"substrate": "NPU", "cell": key, "N": n, "config": cfg,
               "reuse_obs": c["reuse_obs"], "reuse_k": c["reuse"],
               "ttft_s": c.get("ttft_turn_ge1_median_s"),
               "mean_running_obs": c.get("mean_running_obs"),
               "pred": {}, "population": "blind_confirm_cell", "source": "TASK87",
               "src_file": rel(HI_VERDICT)}
        names = {"v11": "v1.1", "v1": "analytic_v1", "sim": "sim_descriptor"}
        for p, lab in names.items():
            row["pred"][lab] = {"reuse": c["pred"][p]["reuse"], "ratio": c["pred"][p]["ratio"]}
        if key in hv["5.2"]["cells"]:
            r = hv["5.2"]["cells"][key]
            row["ratio_obs"], row["ratio_ci"] = r["m"], r["ci"]
            for p, lab in names.items():
                row["pred"][lab]["ratio"] = r[p]["pred"]
        out.append(row)
    sv = load(SIM_VERDICT)
    for key, c in sv["cells"].items():
        cfg, n = key.split(".n")
        n = int(n)
        row = {"substrate": "NPU", "cell": key, "N": n, "config": cfg,
               "reuse_obs": c["reuse_obs"], "reuse_k": c["reuse"],
               "ttft_s": c.get("ttft_turn_ge1_median_s"),
               "mean_running_obs": c.get("mean_running_obs"),
               "pred": {}, "population": "blind_confirm_cell", "source": "TASK95",
               "src_file": rel(SIM_VERDICT)}
        names = {"sim_op": "sim_opcost", "sim": "sim_descriptor", "v1": "analytic_v1"}
        for p, lab in names.items():
            row["pred"][lab] = {"reuse": c["pred"][p]["reuse"], "ratio": c["pred"][p]["ratio"]}
        row["pred"]["analytic_v1"]["population"] = (
            "reference_in_scope" if c["v1_in_scope"] else "reference_out_of_scope")
        if key == "BASE.n20":           # user decision: excluded from §5.1 (no information)
            row["population"] = "blind_no_information_cell"
        if key in sv["5.2"]["cells"]:
            r = sv["5.2"]["cells"][key]
            row["ratio_obs"], row["ratio_ci"] = r["m"], r["ci"]
            for p, lab in names.items():
                row["pred"][lab]["ratio"] = r[p]["pred"]
        out.append(row)
    return out


def with_cell_set(header, rows):
    """Append ``cell_set`` = the TASK/GTASK that owns the row (blind cell set
    TASK82 / TASK87 / TASK95 on NPU, GTASK11 on GPU; GTASK13 rows are dev set)."""
    i = header.index("source")
    return header + ["cell_set"], [r + [str(r[i]).split(";")[0]] for r in rows]


def gpu_cells():
    """GTASK11 cells: observed from the GTASK11 tables, predictions from PREDICTIONS.json (lo)."""
    g11 = gpu_show(G11)
    pred = json.loads(gpu_show(G_MT_PRED))
    reuse_rows = table_after(g11, "### §5.1 재사용률")
    ratio_rows = table_after(g11, "### §5.2 비용 비")
    n26_rows = table_after(g11, "### N = 26 탐색")
    obs = {}
    for r in reuse_rows:
        n, cfg = r[0].split(" ", 1)
        k = nums(r[1])
        obs[(int(n[1:]), cfg)] = {"reuse_obs": num(r[1]), "reuse_k": [int(k[1]), int(k[2])],
                                  "doc_pred": [num(x) for x in r[2:5]]}
    for r in ratio_rows:
        n, cfg = r[0].split(" ", 1)
        ci = nums(r[2])
        obs[(int(n[1:]), cfg)].update(ratio_obs=num(r[1]), ratio_ci=ci,
                                      doc_ratio_pred=[num(x) for x in r[3:6]])
    for r in n26_rows:
        k = nums(r[1])
        obs[(26, r[0])] = {"reuse_obs": num(r[1]), "reuse_k": [int(k[1]), int(k[2])],
                           "doc_pred": [num(x) for x in r[2:5]]}
    m26 = re.search(r"POOL/BASE 비 m = ([\d.]+) \[([\d.]+), ([\d.]+)\]", g11)
    obs[(26, "POOL")].update(ratio_obs=float(m26.group(1)),
                             ratio_ci=[float(m26.group(2)), float(m26.group(3))])
    out = []
    for (n, cfg), o in sorted(obs.items()):
        pc = pred["cells"][str(n)][cfg]
        row = {"substrate": "GPU", "cell": f"{cfg}.n{n}", "N": n, "config": cfg,
               "reuse_obs": o["reuse_obs"], "reuse_k": o["reuse_k"],
               "population": "blind_exploratory_cell" if n == 26 else "blind_confirm_cell",
               "source": "GTASK11", "src_file": gpu_ref(G11), "pred": {},
               "doc_pred": o["doc_pred"], "doc_ratio_pred": o.get("doc_ratio_pred")}
        for p, lab in (("analytic/lo", "analytic_v1"), ("sim_lru/lo", "sim_lru"),
                       ("sim_fifo/lo", "sim_fifo")):
            row["pred"][lab] = {"reuse": pc[p]["reuse_rate"], "ratio": pc[p]["ratio_to_base"]}
        if "ratio_obs" in o:
            row["ratio_obs"], row["ratio_ci"] = o["ratio_obs"], o["ratio_ci"]
            # digits as recorded: 4 in the §5.2 table, 3 in the N = 26 sentence
            row["ratio_dp"] = 3 if n == 26 else 4
        row["reuse_dp"] = 3
        out.append(row)
    return out


def gpu_queue():
    """GTASK14 queue/time table: observed value (first of five) per cell."""
    rows = table_after(gpu_show(G14), "### 대기열과 시간")
    q = {}
    for r in rows:
        n, cfg = r[0].split(" ", 1)
        q[(int(n[1:]), cfg)] = {"queue_mean_obs": nums(r[1])[0], "wait_median_obs_s": nums(r[2])[0],
                                "ttft_median_obs_s": nums(r[3])[0]}
    return q


# -- table builders ------------------------------------------------------------
# Each returns (header, rows, notes, Check, inputs, tasks).

def p01_sequential_survival():
    """Sequential survival: NPU cliff (retro) and GPU staircase (blind), per trial group."""
    r1 = load(R1)
    gp = json.loads(gpu_show(G_SURV_PRED))
    g04 = gpu_show(G04)
    ck = Check()
    header = ["기판", "판정 종류", "조건", "배경 크기 (token)", "배경 요청 수 m", "trial",
              "예측 hit/생존", "관측 hit/생존", "일치", "출처"]
    rows = []
    groups: dict = {}
    for t in r1["trials"]:
        if t["kind"] != "sequential":
            continue
        p = t["P1"]
        g = groups.setdefault((t["task"], p["m"]), {"n": 0, "pred": set(), "obs": set(), "ok": 0})
        g["n"] += 1
        g["pred"].add(p["pred_survive"])
        g["obs"].add(p["obs_survive"])
        g["ok"] += int(p["ok"])
    for (task, m), g in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        rows.append(["NPU", "retro_check", "outer FIFO 8", "2,000" if task in ("TASK14", "TASK15") else "",
                     str(m), str(g["n"]), "/".join(str(x) for x in sorted(g["pred"])),
                     "/".join(str(x) for x in sorted(g["obs"])), f"{g['ok']}/{g['n']}",
                     f"{task}; {rel(R1)}"])
    seq = [t for t in r1["trials"] if t["kind"] == "sequential"]
    ck.eq("NPU 순차 trial 수", len(seq), 29, source="TASK72 R1 P1 29/29")
    ck.eq("NPU 순차 P1 일치", sum(t["P1"]["ok"] for t in seq), 29, source="TASK72 R1 P1 29/29")
    # GPU: predictions file x GTASK04 observed table
    obs_tab = table_after(g04, "### 예측 대 관측")
    obs = {}
    for r in obs_tab:
        bg = 0 if r[0] == "—" else int(num(r[0]))
        for m in nums(r[1]):
            obs[(bg, int(m), "i")] = int(num(r[3]))
            obs[(bg, int(m), "ii")] = int(num(r[5]))
    match = 0
    ggroups: dict = {}
    for t in gp["trials"]:
        key = (t["bg"], t["m"], t["cond"])
        o = obs.get(key)
        g = ggroups.setdefault(key, {"n": 0, "pred": t["pred_hit"], "obs": o})
        g["n"] += 1
        match += int(o == t["pred_hit"])
    for (bg, m, cond), g in sorted(ggroups.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
        rows.append(["GPU", "blind_confirm", f"({cond})", f"{bg:,}", str(m), str(g["n"]),
                     f"{g['pred']:,}", "" if g["obs"] is None else f"{g['obs']:,}",
                     "1" if g["obs"] == g["pred"] else "0",
                     f"GTASK04; {GPU_BRANCH}:{G_SURV_PRED}"])
    ck.eq("GPU trial 수", len(gp["trials"]), 60, source="GTASK04 판정 60/60")
    ck.eq("GPU 예측 = GTASK04 관측 표", match, 60, source="GTASK04 판정 60/60")
    notes = ["NPU 행: 생존 = target prefix 층 2 재사용(True/False), 같은 TASK·m의 trial을 묶었다.",
             "GPU 행: hit token, 관측은 GTASK04 「예측 대 관측」 표(네 채널 동일값).",
             "NPU 순차 trial의 배경 크기는 TASK14·TASK15가 2,000 token; TASK63 trial은 공란."]
    inputs = [rel(R1), gpu_ref(G_SURV_PRED), gpu_ref(G04)]
    return header, rows, notes, ck, inputs, "TASK14, TASK15, TASK72, GTASK04"


def p02_npu_multiturn_main():
    """TASK82 §5.1 and §5.2 per cell, three predictors and the null predictor."""
    mv = load(MAIN_VERDICT)
    s51, s52 = mv["5.1"], mv["5.2"]
    header = ["cell", "판정 종류", "재사용 관측", "해석 v1", "sim 기본", "sim 관측", "영",
              "비 m", "95 % CI", "비 해석", "비 sim 기본", "비 sim 관측"]
    rows = []
    for key, c in s51["cells"].items():
        r = s52["cells"].get(key)
        rows.append([key, "blind_confirm", f3(c["obs"]), f3(c["analytic"]), f3(c["sim_default"]),
                     f3(c["sim_observed"]), f3(c["null"]),
                     f4(r["m"]) if r else "", f"[{r['ci'][0]:.4f}, {r['ci'][1]:.4f}]" if r else "",
                     f4(r["analytic"]["pred"]) if r else "", f4(r["sim_default"]["pred"]) if r else "",
                     f4(r["sim_observed"]["pred"]) if r else ""])
    for cfg, c in mv["n12"].items():
        r = c.get("ratio")
        rows.append([f"{cfg}.n12", "exploratory", f3(c["reuse_obs"]), f3(c["reuse_pred"]["analytic"]),
                     f3(c["reuse_pred"]["sim_default"]), f3(c["reuse_pred"]["sim_observed"]),
                     f3(s51["cells"]["BASE.n6"]["null"]),
                     f4(r["m"]) if r else "", f"[{r['ci'][0]:.4f}, {r['ci'][1]:.4f}]" if r else "",
                     f4(r["pred"]["analytic"]) if r else "", f4(r["pred"]["sim_default"]) if r else "",
                     f4(r["pred"]["sim_observed"]) if r else ""])
    ck = Check()
    src = "TASK82 §5.1"
    ck.eq("§5.1 MAE 해석", round(s51["analytic"]["MAE"], 4), 0.0142, tol=5e-5, source=src)
    ck.eq("§5.1 MAE sim 기본", round(s51["sim_default"]["MAE"], 4), 0.0037, tol=5e-5, source=src)
    ck.eq("§5.1 MAE sim 관측", round(s51["sim_observed"]["MAE"], 4), 0.0036, tol=5e-5, source=src)
    ck.eq("§5.1 MAE 영", round(s51["MAE_null"], 4), 0.1746, tol=5e-5, source=src)
    ck.eq("§5.1 평균 부호 오차 해석", round(s51["analytic"]["mean_signed_error"], 4), -0.0125,
          tol=5e-5, source="TASK82 판정 요약")
    src = "TASK82 §5.2"
    ck.eq("§5.2 Σ|1 − m|", round(s52["sum_abs_1_minus_m"], 4), 0.1871, tol=5e-5, source=src)
    ck.eq("§5.2 Σ 해석", round(s52["analytic"]["sum_abs_err"], 4), 0.0483, tol=5e-5, source=src)
    ck.eq("§5.2 Σ sim 기본", round(s52["sim_default"]["sum_abs_err"], 4), 0.0392, tol=5e-5, source=src)
    ck.eq("§5.2 Σ sim 관측", round(s52["sim_observed"]["sum_abs_err"], 4), 0.0312, tol=5e-5, source=src)
    ck.eq("§5.2 skill 해석", round(s52["analytic"]["skill_ratio"], 2), 0.26, tol=5e-3,
          source="TASK82 판정 요약 (0.26)")
    ck.eq("BASE N10 재사용 관측", round(s51["cells"]["BASE.n10"]["obs"], 3), 0.699, tol=5e-4,
          source="TASK82 §5.1 표")
    ck.eq("TUNED N10 m", round(s52["cells"]["TUNED.n10"]["m"], 4), 0.9523, tol=5e-5,
          source="TASK82 §5.2 표")
    ck.eq("§5.4 DP/TUNED m", round(mv["5.4"]["m"], 4), 0.9920, tol=5e-5, source="TASK82 §5.4")
    ck.eq("N12 BATCHONLY m", round(mv["n12"]["BATCHONLY"]["ratio"]["m"], 3), 0.844, tol=5e-4,
          source="TASK82 N = 12 표")
    notes = ["재사용 = turn ≥ 1 요청, r0–r4 합산. 비 m = BASE 대비 turn당 A′ 짝 비 중앙.",
             "N=12 행은 TASK82에서 탐색 cell(판정 없음). 영 = NULL_PREDICTORS.json 0.676."]
    return header, rows, notes, ck, [rel(MAIN_VERDICT)], "TASK82"


def p03_npu_hiload():
    """TASK87 cells: v1.1 (main predictor), v1, sim; ratio with CI."""
    hv = load(HI_VERDICT)
    header = ["cell", "판정 종류", "재사용 관측", "v1.1", "v1", "sim", "영", "비 m", "95 % CI",
              "비 v1.1", "비 v1", "비 sim", "평균 running 관측", "TTFT 중앙 (s)"]
    null = 0.6763527054108216
    rows = []
    for key, c in hv["cells"].items():
        r = hv["5.2"]["cells"].get(key)
        rows.append([key, "blind_confirm", f3(c["reuse_obs"]), f3(c["pred"]["v11"]["reuse"]),
                     f3(c["pred"]["v1"]["reuse"]), f3(c["pred"]["sim"]["reuse"]), f3(null),
                     f3(r["m"]) if r else "", f"[{r['ci'][0]:.3f}, {r['ci'][1]:.3f}]" if r else "",
                     f3(r["v11"]["pred"]) if r else "", f3(r["v1"]["pred"]) if r else "",
                     f3(r["sim"]["pred"]) if r else "", f"{c['mean_running_obs']:.2f}",
                     f3(c["ttft_turn_ge1_median_s"])])
    ck = Check()
    s51, s52 = hv["5.1"], hv["5.2"]
    ck.eq("평균 |1 − m|", round(s52["mean_abs_1_minus_m"], 3), 0.253, tol=5e-4, source="TASK87 비용 비")
    ck.eq("Σ|오차| v1.1", round(s52["v11"]["sum_abs_err"], 3), 0.087, tol=5e-4, source="TASK87 판정 요약")
    ck.eq("Σ|오차| v1", round(s52["v1"]["sum_abs_err"], 3), 0.358, tol=5e-4, source="TASK87 판정 요약")
    ck.eq("Σ|오차| sim", round(s52["sim"]["sum_abs_err"], 3), 0.189, tol=5e-4, source="TASK87 판정 요약")
    ck.eq("재사용 MAE v1.1", round(s51["v11"]["MAE"], 3), 0.049, tol=5e-4, source="TASK87 판정 요약")
    ck.eq("재사용 MAE v1", round(s51["v1"]["MAE"], 3), 0.033, tol=5e-4, source="TASK87 판정 요약")
    ck.eq("재사용 MAE sim", round(s51["sim"]["MAE"], 3), 0.013, tol=5e-4, source="TASK87 판정 요약")
    ck.eq("영 MAE", round(s51["MAE_null"], 4), 0.2245, tol=5e-5, source="TASK87 cell별 표 아래")
    ck.eq("BASE N14 재사용 관측", round(hv["cells"]["BASE.n14"]["reuse_obs"], 3), 0.298, tol=5e-4,
          source="TASK87 cell별 표")
    ck.eq("TUNED N16 m", round(s52["cells"]["TUNED.n16"]["m"], 3), 0.696, tol=5e-4,
          source="TASK87 비용 비 표")
    ck.eq("h TVD 중앙 v1.1", round(hv["5.6"]["v11"]["median"], 4), 0.0989, tol=5e-5,
          source="TASK87 판정 요약")
    notes = ["주 예측기 v1.1(HILOAD_PREREG.md). sim = descriptor 의미론. 영 = NULL_PREDICTORS_HI.json.",
             "평균 running 관측은 step 가중(`[BUCKET]`)."]
    return header, rows, notes, ck, [rel(HI_VERDICT)], "TASK86, TASK87"


def p04_gpu_multiturn():
    """GTASK11 cells: observed (GTASK11 tables) vs PREDICTIONS.json (lo)."""
    cells = gpu_cells()
    header = ["cell", "판정 종류", "재사용 관측", "해석 v1", "sim LRU", "sim FIFO", "영",
              "비 m", "95 % CI", "비 해석", "비 sim LRU", "비 sim FIFO"]
    rows = []
    ck = Check()
    for c in cells:
        p = c["pred"]
        rows.append([c["cell"], "exploratory" if c["N"] == 26 else "blind_confirm",
                     f3(c["reuse_obs"]), f3(p["analytic_v1"]["reuse"]), f3(p["sim_lru"]["reuse"]),
                     f3(p["sim_fifo"]["reuse"]), f"{GPU_REUSE_NULL:.5f}",
                     fmt(c.get("ratio_obs"), c.get("ratio_dp", 4)) if c["config"] != "BASE" else "",
                     "[{}, {}]".format(fmt(c["ratio_ci"][0], c["ratio_dp"]), fmt(c["ratio_ci"][1], c["ratio_dp"]))
                     if "ratio_ci" in c else "",
                     f4(p["analytic_v1"]["ratio"]) if c["config"] != "BASE" else "",
                     f4(p["sim_lru"]["ratio"]) if c["config"] != "BASE" else "",
                     f4(p["sim_fifo"]["ratio"]) if c["config"] != "BASE" else ""])
        for i, lab in enumerate(("analytic_v1", "sim_lru", "sim_fifo")):
            ck.eq(f"{c['cell']} 재사용 예측 {lab} (문서 3자리)", round(p[lab]["reuse"], 3),
                  c["doc_pred"][i], tol=5e-4, source="GTASK11 §5.1 / N = 26 표")
        if c.get("doc_ratio_pred"):
            for i, lab in enumerate(("analytic_v1", "sim_lru", "sim_fifo")):
                ck.eq(f"{c['cell']} 비 예측 {lab} (문서 4자리)", round(p[lab]["ratio"], 4),
                      c["doc_ratio_pred"][i], tol=5e-5, source="GTASK11 §5.2 표")
    conf = [c for c in cells if c["N"] != 26]
    for lab, rec in (("analytic_v1", 0.0333), ("sim_lru", 0.0173), ("sim_fifo", 0.1021)):
        mae = statistics.mean(abs(c["pred"][lab]["reuse"] - c["reuse_obs"]) for c in conf)
        ck.eq(f"§5.1 MAE {lab} (문서 관측 3자리로 재계산)", round(mae, 4), rec, tol=6e-4,
              source="GTASK11 §5.1 MAE(lo)")
    mae0 = statistics.mean(abs(GPU_REUSE_NULL - c["reuse_obs"]) for c in conf)
    ck.eq("§5.1 영 MAE (재계산)", round(mae0, 4), 0.0502, tol=6e-4, source="GTASK11 §5.1")
    rc = [c for c in conf if c["config"] != "BASE"]
    for lab, rec in (("analytic_v1", 0.146), ("sim_lru", 0.075), ("sim_fifo", 0.108)):
        s = sum(abs(c["pred"][lab]["ratio"] - c["ratio_obs"]) for c in rc)
        ck.eq(f"§5.2 Σ|예측 − m| {lab} (재계산)", round(s, 3), rec, tol=1.5e-3,
              source="GTASK11 §5.2")
    ck.eq("§5.2 Σ|1 − m|", round(sum(abs(1 - c["ratio_obs"]) for c in rc), 3), 0.209, tol=1e-3,
          source="GTASK11 §5.2")
    n26 = next(c for c in cells if c["cell"] == "POOL.n26")
    for lab, rec in (("analytic_v1", 0.984), ("sim_lru", 0.939), ("sim_fifo", 0.964)):
        ck.eq(f"POOL.n26 비 예측 {lab} (문장 3자리)", round(n26["pred"][lab]["ratio"], 3), rec, tol=5e-4,
              source="GTASK11 N = 26 탐색 문장")
    b24 = next(c for c in cells if c["cell"] == "BASE.n24")
    ck.eq("BASE.n24 sim LRU 재사용 (§5.5·발견 4 문장의 값)", round(b24["pred"]["sim_lru"]["reuse"], 3),
          0.752, tol=5e-4, source="GTASK11 §5.5 «LRU 0.752», 발견 4 «0.849, 0.752, 0.657» — GPU 쪽 정정 대기")
    notes = ["관측은 GTASK11 문서 표(재사용 3자리, 비 4자리)에서 읽었다 — GPU raw는 이 host에 없다.",
             "예측은 PREDICTIONS.json `lo` bound. 영 = GPU 선등록 개정 1의 NPU 영 재사용 0.84718.",
             "N=26은 탐색 cell. N26 POOL 비 m·CI는 GTASK11 본문 문장에서 읽었다."]
    inputs = [gpu_ref(G11), gpu_ref(G_MT_PRED)]
    return header, rows, notes, ck, inputs, "GTASK11"


def p05_ranking():
    """§5.3 configuration ranking on both substrates."""
    mv, hv = load(MAIN_VERDICT), load(HI_VERDICT)
    header = ["기판", "N", "쌍", "m", "95 % CI", "해소", "관측 싼 쪽", "예측기 일치", "판정 종류", "출처"]
    rows = []
    for src, d, preds in (("TASK82", mv, ("analytic", "sim_default", "sim_observed")),
                          ("TASK87", hv, ("v11", "v1", "sim"))):
        for n, pn in d["5.3"]["per_n"].items():
            for p in pn["pairs"]:
                agree = "; ".join(f"{q} {p.get(q + '_agrees')}" for q in preds)
                rows.append(["NPU", n, p["pair"], f4(p["m"]), f"[{p['ci'][0]:.4f}, {p['ci'][1]:.4f}]",
                             str(p["resolved"]), p["obs_cheaper"] or "", agree, "blind_confirm", src])
    g11 = gpu_show(G11)
    for r in table_after(g11, "### §5.3·§5.4"):
        n = r[0]
        for pair, cell in zip(("BASE/POOL", "BASE/POOL+GRID", "POOL/POOL+GRID"), r[1:4]):
            v = nums(cell)
            rows.append(["GPU", n, pair, f4(v[0]), f"[{v[1]:.4f}, {v[2]:.4f}]",
                         str("해소" in cell), "", "해석 " + r[4], "blind_confirm", "GTASK11"])
    ck = Check()
    res82 = sum(p["resolved"] for pn in mv["5.3"]["per_n"].values() for p in pn["pairs"])
    res87 = sum(p["resolved"] for pn in hv["5.3"]["per_n"].values() for p in pn["pairs"])
    ck.eq("TASK82 해소 쌍", res82, 7, source="TASK82 판정 요약 (해소된 7쌍)")
    ck.eq("TASK87 해소 쌍", res87, 6, source="TASK87 판정 요약 (해소 6/6쌍)")
    ck.eq("TASK82 §5.3 N=6 판정", mv["5.3"]["per_n"]["6"]["verdict"], "UNRESOLVED", source="TASK82")
    bo_t = next(p for p in hv["5.3"]["per_n"]["14"]["pairs"] if p["pair"] == "BATCHONLY/TUNED")
    ck.eq("TASK87 N14 BATCHONLY/TUNED m", round(bo_t["m"], 3), 1.036, tol=5e-4, source="TASK87 순위")
    notes = ["GPU 행은 GTASK11 §5.3·§5.4 표(lo)에서 읽었다. 관측 싼 쪽 열은 GPU 표에 없어 공란."]
    return header, rows, notes, ck, [rel(MAIN_VERDICT), rel(HI_VERDICT), gpu_ref(G11)], \
        "TASK82, TASK87, GTASK11"


def p06_event_replay():
    """Event replay on both substrates: NPU R5' per run, GPU GTASK12 per cell."""
    r5 = load(R5P)
    header = ["기판", "run / cell", "요청", "정확 일치", "일치율", "대안: RESERVED", "대안: 지연 release",
              "닫힌 형태 보조", "판정 종류", "출처"]
    rows = []
    tot = {"n": 0, "m": 0, "def": 0}
    labels = {"TASK54": iter(["TASK54 mb", "TASK54 mb6"])}
    for run in r5["runs"]:
        reqs = run["requests"]
        deferred = sum(int(q["pred_deferred"] == q["obs"]) for q in reqs) / len(reqs)
        name = next(labels[run["run"]]) if run["run"] in labels else run["run"]
        rows.append(["NPU", name, f"{run['total']:,}", f"{run['match']:,}", f3(run["agreement"]),
                     f3(run["reserved_agreement"]), f3(deferred), f3(run["closed_form_agreement"]),
                     "retro_check", "TASK72 R5′"])
        tot["n"] += run["total"]
        tot["m"] += run["match"]
        tot["def"] += sum(int(q["pred_deferred"] == q["obs"]) for q in reqs)
    g12 = gpu_show(G12)
    gtot = {"pop": 0, "life": 0}
    for r in table_after(g12, "| cell | 판정 모집단"):
        head = r[0].replace("**", "")
        n, cfgs = head.split(" ", 1)
        pops, lives = nums(r[1]), nums(r[3])
        for cfg, pop, life in zip(cfgs.split(" / "), pops, lives):
            rows.append(["GPU", f"{n} {cfg}", f"{int(pop):,}", r[2].replace("**", "") if r[2] != "전부"
                         else f"{int(pop):,}", "1.000", "", "", "", "retro_check", "GTASK12"])
            gtot["pop"] += int(pop)
            gtot["life"] += int(life)
    ck = Check()
    ck.eq("NPU 요청 합", tot["n"], 1298, source="TASK72 R5′ (1,298)")
    ck.eq("NPU 일치 합", tot["m"], 1298, source="TASK72 R5′ (1,298)")
    ck.eq("NPU 지연 release 합산 일치율", round(tot["def"] / tot["n"], 3), 0.934, tol=5e-4,
          source="TASK72 R5′ 표 합 행")
    ck.eq("NPU RESERVED 합산", round(r5["summary"]["reserved_agreement"], 3), 0.847, tol=5e-4,
          source="TASK72 R5′")
    ck.eq("NPU 닫힌 형태 합산", round(r5["summary"]["closed_form_agreement"], 3), 0.833, tol=5e-4,
          source="TASK72 핵심 발견 4")
    ck.eq("GPU 판정 모집단 합 (cell 표)", gtot["pop"], 16794, source="GTASK12 판정 (16,794)")
    ck.eq("GPU lifecycle 전체 합 (cell 표)", gtot["life"], 23076, source="GTASK12 보고 모집단 (23,076)")
    notes = ["NPU: turn ≥ 1 재도착, 관측 = client cached_tokens·server 조회 교차. 대안 열은 같은 사건 순서의 다른 규칙.",
             "GPU: GTASK12 cell 표의 판정 모집단(평가 구간 turn ≥ 1). 대안 재생 일치율은 GTASK12 §7 표(cell 범위만 기록)."]
    return header, rows, notes, ck, [rel(R5P), gpu_ref(G12)], "TASK72, GTASK12"


def p07_time_scale():
    """Operating-condition step time: GPU GTASK13 (dev set) and NPU TASK91 (dev set)."""
    g13 = gpu_show(G13)
    ex, au = load(EXPLAIN), load(AUDIT)
    header = ["기판", "항목", "cell", "관측", "orig", "변형 1", "변형 2", "변형 3", "판정 종류", "출처"]
    rows = []
    for r in table_after(g13, "### 붕괴 곡선"):
        rows.append(["GPU", "BASE 재사용 (관측 / orig / x1.131 / x1.210 / mode_dist)", f"BASE.n{r[0]}",
                     *[f3(num(x)) for x in r[1:6]], "dev_set", "GTASK13"])
    summ = table_after(g13, "### 요약 지표")
    for r in summ:
        rows.append(["GPU", "확증 9 cell 재사용 MAE · 비 Σ|오차| (6 cell)", r[0], "",
                     f"{num(r[3]):.4f}", f"{num(r[5]):.4f}", "", "", "dev_set", "GTASK13 요약 지표"])
    for key, c in ex["cells"].items():
        if "orig_ratio_bias" in c:
            rows.append(["NPU", "sim 비 편향 (원래 / 시간 척도 적용 / 설명 비율)", key, "",
                         f"{c['orig_ratio_bias']:+.4f}", f"{c['scaled_ratio_bias']:+.4f}",
                         f"{c['ratio_bias_explained']:.2f}", "", "dev_set", "TASK91"])
        else:
            rows.append(["NPU", "BASE 재사용 편향 (원래 / 시간 척도 적용)", key, "",
                         f"{c['orig_reuse_bias']:+.3f}", f"{c['scaled_reuse_bias']:+.3f}", "", "",
                         "dev_set", "TASK91"])
    ts = au["decode_time_scale"]
    for cfg in ("BASE", "BATCHONLY", "TUNED", "DP"):
        rows.append(["NPU", "decode step 관측/예측 (step 가중)", cfg,
                     f3(ts[cfg]["step_weighted_ratio"]), "", "", "", "", "dev_set", "TASK91"])
    ck = Check()
    s = ex["summary"]
    ck.eq("NPU Σ|편향| 원래", round(s["ratio_bias_sum_orig"], 3), 0.262, tol=5e-4, source="TASK91 발견 4 표")
    ck.eq("NPU Σ|편향| 적용", round(s["ratio_bias_sum_scaled"], 3), 0.135, tol=5e-4, source="TASK91 발견 4 표")
    ck.eq("NPU 설명 비율", round(s["explained_share"] * 100, 1), 48.5, tol=0.05, source="TASK91 (48.5 %)")
    for cfg, rec in (("BASE", 1.084), ("BATCHONLY", 1.076), ("TUNED", 1.085), ("DP", 1.069)):
        ck.eq(f"NPU step 가중 {cfg}", round(ts[cfg]["step_weighted_ratio"], 3), rec, tol=5e-4,
              source="TASK91 decode step 표")
    curve = {r[0]: [num(x) for x in r[1:6]] for r in table_after(g13, "### 붕괴 곡선")}
    g11 = {c["cell"]: c for c in gpu_cells()}
    for n in ("20", "22", "24", "26"):
        ck.eq(f"GTASK13 orig BASE N{n} = PREDICTIONS sim_lru/lo (3자리)", curve[n][1],
              round(g11[f"BASE.n{n}"]["pred"]["sim_lru"]["reuse"], 3), tol=5e-4,
              source="GTASK13 회귀 문장(orig = PREDICTIONS.json sim_lru/lo)")
    notes = ["두 기판 모두 개발 집합: 비율을 같은 관측에서 얻었다(GTASK13, TASK91). blind 예측 입력이 아니다."]
    inputs = [gpu_ref(G13), gpu_ref(G11), gpu_ref(G_MT_PRED), rel(EXPLAIN), rel(AUDIT)]
    return header, rows, notes, ck, inputs, "GTASK13, TASK91"


def p08_stationarity():
    """Same-length stationarity: NPU TASK83 and GPU GTASK16."""
    st = load(STATIONARITY)
    header = ["기판", "cell", "median W", "median B", "q_h", "median Δ reuse", "q_Δ", "판정 종류", "출처"]
    rows = []
    for key, c in st["cells"].items():
        rows.append(["NPU", key, f3(c["median_W"]), f3(c["median_B"]), f"{c['q_h']:.2f}",
                     f"{c['median_delta']:+.3f}", f"{c['q_delta']:.2f}", "retro_check", "TASK83"])
    for r in table_after(gpu_show(G16), "| cell | median W"):
        rows.append(["GPU", r[0], r[1], r[2], r[3], r[5].replace("−", "-"), r[7], "retro_check", "GTASK16"])
    ck = Check()
    h, ru = st["summary"]["h"], st["summary"]["reuse"]
    ck.eq("NPU q_h 중앙", round(h["median_q_h"], 3), 0.638, tol=5e-4, source="TASK83 결과")
    ck.eq("NPU q_h > 0.5 cell", h["cells_q_gt_half"], 10, source="TASK83 결과 (10/13)")
    ck.eq("NPU h 분류", h["class"], "WEAK_EVIDENCE", source="TASK83")
    ck.eq("NPU q_Δ 중앙", round(ru["median_q_delta"], 2), 0.45, tol=5e-3, source="TASK83 결과")
    ck.eq("NPU 재사용 분류", ru["class"], "NOT_NONSTATIONARY", source="TASK83")
    gq = [float(r[4]) for r in rows if r[0] == "GPU"]
    ck.eq("GPU q_h 중앙 (표에서 재계산)", round(statistics.median(gq), 2), 0.43, tol=5e-3,
          source="GTASK16 분류 표")
    notes = ["NPU 13 cell, GPU 11 cell(h는 decode-only). 같은 길이(60 s) run 사이 기준."]
    return header, rows, notes, ck, [rel(STATIONARITY), gpu_ref(G16)], "TASK83, GTASK16"


def _descriptor_test_module():
    spec = importlib.util.spec_from_file_location("test_descriptor_v2", REPO / "tests/test_descriptor_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RULE_FIELDS = [("reuse layer eviction_order", None),
               ("semantics.initial_free_order", "initial_free_order"),
               ("semantics.intra_request_loss", "intra_request_loss"),
               ("semantics.resume_allocates_first", "resume_allocates_first"),
               ("semantics.hit_protection", "hit_protection"),
               ("semantics.kv_tokens_held", "kv_tokens_held"),
               ("semantics.cacheable_tokens", "cacheable_tokens")]


def p09_descriptor_rules():
    """TASK84 finding 1: the seven rule fields on both substrates, and the two reproductions."""
    T = _descriptor_test_module()
    rbln, PR = T.RBLN_CA25_V2, T.PR
    gp = json.loads(gpu_show(G_SURV_PRED))
    gpu = T.gpu_test_descriptor(num_gpu_blocks=gp["num_gpu_blocks"])
    header = ["field", "RBLN CA25 (v2 인스턴스)", "A6000 (테스트 전용 descriptor)"]
    rows = []
    for label, attr in RULE_FIELDS:
        if attr is None:
            vals = [d.layers[d.reuse_layer].eviction_order for d in (rbln, gpu)]
        else:
            vals = [getattr(d.semantics, attr) for d in (rbln, gpu)]
        rows.append([label, str(vals[0]), str(vals[1])])
    ck = Check()
    for bg in (500, 1000, 2000, 4000):
        alive = [PR.sequential_protocol(rbln, target_prompt=2000, target_generated=8,
                                        backgrounds=[(bg, 8)] * m, resume_prompt=2008).hit_tokens
                 for m in range(9)]
        ck.eq(f"RBLN 절벽 배경 {bg} token (m = 0..8)", alive, [1920] * 7 + [0, 0],
              source="TASK84 테스트 (B = 7에서 1,920 → 0)")
    ok = 0
    for t in gp["trials"]:
        gen = gp["target_gen"][t["cond"]]
        resume = gp["target_prompt"] + (gen if t["cond"] == "ii" else 0) + gp["suffix"]
        r = PR.sequential_protocol(gpu, target_prompt=gp["target_prompt"], target_generated=gen,
                                   backgrounds=[(t["bg"], gp["bg_gen"])] * t["m"], resume_prompt=resume)
        ok += int(r.hit_tokens == t["pred_hit"]
                  and r.cacheable_units_evicted == t["pred_target_blocks_evicted"])
    ck.eq("GPU 60 trial 무wrapper 재현", ok, 60, source="TASK84 (60/60)")
    ck.eq("규칙 field 수", len(rows), 7, source="TASK84 핵심 발견 1 (7개)")
    notes = ["값은 descriptor 객체에서 읽었다(code_check). GPU descriptor는 tests/test_descriptor_v2.py의 테스트 전용 객체."]
    inputs = ["experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py", "tests/test_descriptor_v2.py",
              gpu_ref(G_SURV_PRED)]
    return header, rows, notes, ck, inputs, "TASK84, GTASK04"


def p10_b2_diagnosis():
    """TASK90 B2 ladder and freeze check (development set)."""
    bd, fc = load(B2_DIAG), load(FREEZE)
    header = ["cell", "A B2", "D 지수 gap·배타", "E plan gap", "F sim", "O 관측", "gap 모양 (E−D)",
              "gap 모양 비배타 (C′−C)", "편향 v1", "편향 v1.1", "편향 v1.2 후보", "편향 sim"]
    rows = []
    for key, c in bd.items():
        a = c["attribution"]
        t = fc["table"][key]

        def b(p):
            x = t[p]
            s = f"{x['reuse_bias']:+.3f}"
            if "ratio_bias" in x:
                s += f" / {x['ratio_bias']:+.3f}"
            return s + ("*" if x["over_half"] else "")
        rows.append([key, f3(c["A"]), f3(c["D"]), f3(c["E"]), f3(c["F"]), f3(c["O"]),
                     f"{a['gap_shape']:+.3f}", f"{a['gap_shape_without_exclusive_prefill']:+.3f}",
                     b("v1"), b("v11"), b("v12"), b("sim")])
    ck = Check()
    for key, rec in (("BASE.n14", -0.395), ("BASE.n16", -0.450), ("BASE.n12", 0.077)):
        ck.eq(f"{key} gap 모양 (E−D)", round(bd[key]["attribution"]["gap_shape"], 3), rec, tol=5e-4,
              source="TASK90 B2 진단 표")
    ck.eq("BASE.n14 비배타 (C′−C)", round(bd["BASE.n14"]["attribution"]["gap_shape_without_exclusive_prefill"], 3),
          0.663, tol=5e-4, source="TASK90 B2 진단 표")
    s = fc["summary"]
    for p, cnt, mae, rs in (("v1", 8, 0.036, 0.450), ("v11", 7, 0.042, 0.187),
                            ("v12", 8, 0.054, 0.132), ("sim", 6, 0.012, 0.262)):
        ck.eq(f"{p} 초과 cell 수", len(s[p]["cells_over_half"]), cnt, source="TASK90 동결 전 점검 표")
        if p == "v11":   # TASK90 표 0.042는 반올림 오기; 산출 파일 값 0.0415로 정정 기록 (지시문 09 §2.7)
            ck.eq("v11 재사용 MAE", round(s[p]["reuse_mae"], 4), 0.0415, tol=5e-5,
                  source="TASK90 정정 기록 (지시문 09, 원 표 0.042)")
        else:
            ck.eq(f"{p} 재사용 MAE", round(s[p]["reuse_mae"], 3), mae, tol=5e-4, source="TASK90 동결 전 점검 표")
        ck.eq(f"{p} 비 Σ|편향|", round(s[p]["ratio_sum_abs"], 3), rs, tol=5e-4, source="TASK90 동결 전 점검 표")
    ck.eq("v1.2 동결", fc["freeze_v12"], False, source="TASK90 (동결하지 않음)")
    notes = ["개발 집합(N = 12·14·16), 판정 없음. 편향 = 예측 − 관측, 재사용 / 비. * = 허용치 절반(0.05 / 0.015) 초과.",
             "running = step 가중 평균 running."]
    return header, rows, notes, ck, [rel(B2_DIAG), rel(FREEZE)], "TASK90"


TABLES = {
    "P01": (p01_sequential_survival, "순차 생존: NPU 절벽(사후 재생)과 GPU 계단(blind)"),
    "P02": (p02_npu_multiturn_main, "NPU multi-turn 본 측정: 재사용·비용 비, 세 예측기와 영"),
    "P03": (p03_npu_hiload, "NPU 고부하 N = 14·16: v1.1·v1·sim"),
    "P04": (p04_gpu_multiturn, "GPU multi-turn: 해석 v1·sim LRU·sim FIFO"),
    "P05": (p05_ranking, "구성 순위 (§5.3), 두 기판"),
    "P06": (p06_event_replay, "사건 재생, 두 기판"),
    "P07": (p07_time_scale, "운영 step 시간 척도 (개발 집합), 두 기판"),
    "P08": (p08_stationarity, "같은 길이 정상성, 두 기판"),
    "P09": (p09_descriptor_rules, "descriptor 규칙 field 7개와 두 기판 재현"),
    "P10": (p10_b2_diagnosis, "B2 진단 사다리와 v1.2 동결 전 점검 (개발 집합)"),
}


# -- figure data ---------------------------------------------------------------

def fig_a_survival():
    """(a) sequential survival: NPU cliff vs GPU staircase, prediction and observation."""
    T = _descriptor_test_module()
    r1 = load(R1)
    gp = json.loads(gpu_show(G_SURV_PRED))
    g04 = gpu_show(G04)
    header = ["substrate", "population", "condition", "bg_tokens", "m_background", "bg_units_cum",
              "pred_hit_tokens", "obs_hit_tokens", "pred_survive_frac", "obs_survive_frac", "source"]
    rows = []
    for t in r1["trials"]:
        if t["kind"] != "sequential":
            continue
        p = t["P1"]
        rows.append(["NPU", "retro_check", "outer_fifo_8", "2000" if t["task"] in ("TASK14", "TASK15") else "",
                     p["m"], "", "", "", int(p["pred_survive"]), int(p["obs_survive"]),
                     f"{t['task']}; {rel(R1)}"])
    for bg in (500, 1000, 2000, 4000):
        for m in range(11):
            h = T.PR.sequential_protocol(T.RBLN_CA25_V2, target_prompt=2000, target_generated=8,
                                         backgrounds=[(bg, 8)] * m, resume_prompt=2008).hit_tokens
            rows.append(["NPU", "code_check", "descriptor_v2_prediction", bg, m, "", h, "",
                         f"{h / 1920:.4f}", "", "TASK84; experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py"])
    obs = {}
    for r in table_after(g04, "### 예측 대 관측"):
        bg = 0 if r[0] == "—" else int(num(r[0]))
        for m in nums(r[1]):
            obs[(bg, int(m), "i")] = int(num(r[3]))
            obs[(bg, int(m), "ii")] = int(num(r[5]))
    full = {"i": 2000, "ii": 2016}
    for t in gp["trials"]:
        o = obs.get((t["bg"], t["m"], t["cond"]))
        rows.append(["GPU", "blind_confirm", f"({t['cond']})", t["bg"], t["m"], t["m"] * t["u_bg"],
                     t["pred_hit"], "" if o is None else o, f"{t['pred_hit'] / full[t['cond']]:.4f}",
                     "" if o is None else f"{o / full[t['cond']]:.4f}",
                     f"GTASK04; {gpu_ref(G_SURV_PRED)}; obs {gpu_ref(G04)}"])
    return header, rows


def _pred_rows(c, metric):
    out = []
    for lab, p in c["pred"].items():
        v = p.get(metric)
        if v is None:
            continue
        out.append((lab, v, p.get("population", c["population"])))
    return out


def fig_b_vs_n():
    """(b) BASE reuse and configuration cost ratio vs N, per predictor."""
    header = ["substrate", "N", "config", "metric", "predictor", "value", "ci_lo", "ci_hi",
              "population", "source"]
    rows = []
    cells = npu_cells() + gpu_cells()
    for c in cells:
        src = f"{c['source']}; {c['src_file']}"
        if c["config"] == "BASE":
            rows.append([c["substrate"], c["N"], "BASE", "reuse", "observed", fmt(c["reuse_obs"], c.get("reuse_dp", 4)),
                         "", "", c["population"], src])
            for lab, v, pop in _pred_rows(c, "reuse"):
                rows.append([c["substrate"], c["N"], "BASE", "reuse", lab, f"{v:.4f}", "", "",
                             pop, src])
            null = GPU_REUSE_NULL if c["substrate"] == "GPU" else 0.6763527054108216
            rows.append([c["substrate"], c["N"], "BASE", "reuse", "null", f"{null:.4f}", "", "",
                         c["population"], src])
        elif "ratio_obs" in c:
            ci = c["ratio_ci"]
            dp = c.get("ratio_dp", 4)
            rows.append([c["substrate"], c["N"], c["config"], "ratio_to_BASE", "observed",
                         fmt(c["ratio_obs"], dp), fmt(ci[0], dp), fmt(ci[1], dp), c["population"], src])
            for lab, v, pop in _pred_rows(c, "ratio"):
                rows.append([c["substrate"], c["N"], c["config"], "ratio_to_BASE", lab, f"{v:.4f}",
                             "", "", pop, src])
            rows.append([c["substrate"], c["N"], c["config"], "ratio_to_BASE", "null", "1.0000",
                         "", "", c["population"], src])
    g13 = gpu_show(G13)
    for r in table_after(g13, "### 붕괴 곡선"):
        for lab, x in zip(("sim_lru_orig", "sim_lru_x1.131", "sim_lru_x1.210", "sim_lru_mode_dist"), r[2:6]):
            rows.append(["GPU", int(r[0]), "BASE", "reuse", lab, f"{num(x):.3f}", "", "", "dev_set",
                         f"GTASK13; {gpu_ref(G13)}"])
    m = re.search(r"N26 POOL/BASE 비\*\*: 관측 ([\d.]+), orig ([\d.]+), x1\.131 ([\d.]+), "
                  r"x1\.210 ([\d.]+), mode_dist ([\d.]+)", g13)
    if m:
        for lab, x in zip(("sim_lru_orig", "sim_lru_x1.131", "sim_lru_x1.210", "sim_lru_mode_dist"),
                          m.groups()[1:]):
            rows.append(["GPU", 26, "POOL", "ratio_to_BASE", lab, x, "", "", "dev_set",
                         f"GTASK13; {gpu_ref(G13)}"])
    return with_cell_set(header, rows)


def fig_c_pred_vs_obs():
    """(c) predicted vs observed per cell (reuse, ratio), null predictor included."""
    header = ["substrate", "cell", "N", "config", "metric", "predictor", "predicted", "observed",
              "error_pred_minus_obs", "population", "source"]
    rows = []
    for c in npu_cells() + gpu_cells():
        src = f"{c['source']}; {c['src_file']}"
        null = GPU_REUSE_NULL if c["substrate"] == "GPU" else 0.6763527054108216
        preds = _pred_rows(c, "reuse") + [("null", null, c["population"])]
        for lab, v, pop in preds:
            rows.append([c["substrate"], c["cell"], c["N"], c["config"], "reuse", lab, f"{v:.4f}",
                         fmt(c["reuse_obs"], c.get("reuse_dp", 4)), f"{v - c['reuse_obs']:+.4f}", pop, src])
        if c["config"] != "BASE" and "ratio_obs" in c:
            for lab, v, pop in _pred_rows(c, "ratio") + [("null", 1.0, c["population"])]:
                rows.append([c["substrate"], c["cell"], c["N"], c["config"], "ratio_to_BASE", lab,
                             f"{v:.4f}", fmt(c["ratio_obs"], c.get("ratio_dp", 4)),
                             f"{v - c['ratio_obs']:+.4f}", pop, src])
    return with_cell_set(header, rows)


def fig_d_applicability():
    """(d) analytic-model applicability: queue depth vs prediction error per cell."""
    header = ["substrate", "cell", "N", "config", "max_running_M", "N_over_M",
              "queue_p_wait_gt0_b2v1", "queue_E_wait_b2v1", "queue_depth_source",
              "queue_mean_obs", "queue_p_gt0_obs", "queue_obs_source",
              "ttft_median_obs_s", "mean_running_obs", "predictor",
              "reuse_error", "ratio_error", "population", "source"]
    rows = []
    gq = gpu_queue()
    qo = load(QUEUE_OBS)["cells"]
    gpred = json.loads(gpu_show(G_MT_PRED))
    for c in npu_cells() + gpu_cells():
        if c["substrate"] == "NPU":
            M = 8 if c["config"] == "BASE" else 16
            if c["config"] == "BASE" and c["N"] in NPU_B2_QUEUE:
                pw, ew = NPU_B2_QUEUE[c["N"]]
                qsrc = f"HILOAD_PREREG.md §2 @ {npu_commit('docs/research/HILOAD_PREREG.md')}"
            elif c["config"] != "BASE" and c["N"] <= 16:
                pw, ew = "0", "0"
                qsrc = "HILOAD_PREREG.md §2 (batch 16, N ≤ 16: 대기 0)"
            else:
                pw = ew = None
                qsrc = "B2 v1 예측 기록 없음 (관측은 queue_mean_obs 열)"
            q = qo[c["cell"]]
            assert q["source"] == c["source"], (c["cell"], q["source"], c["source"])
            qobs, qp, ttft = f"{q['mean_q']:.3f}", f"{q['p_q_gt0']:.3f}", c.get("ttft_s")
            qosrc = (f"queue_depth_obs.py: client in-flight − [BUCKET] request_nums, 평가 구간 decode "
                     f"step 가중 ({q['steps']} step, {c['source']} 로그)")
        else:
            M = gpred["cells"][str(c["N"])][c["config"]]["config"]["max_num_seqs"]
            pw = ew = None
            q = gq.get((c["N"], c["config"]))
            qsrc = f"GTASK14 관측 @ {gpu_commit(G14)}" if q else "기록 없음"
            qobs = q["queue_mean_obs"] if q else ""
            qp = ""
            qosrc = f"GTASK14 관측 @ {gpu_commit(G14)}" if q else "기록 없음"
            ttft = q["ttft_median_obs_s"] if q else None
        for lab, p in c["pred"].items():
            re_ = p["reuse"] - c["reuse_obs"]
            ra = (p["ratio"] - c["ratio_obs"]) if (c["config"] != "BASE" and "ratio_obs" in c
                                                   and p.get("ratio") is not None) else None
            rows.append([c["substrate"], c["cell"], c["N"], c["config"], M, f"{c['N'] / M:.3f}",
                         "" if pw is None else pw, "" if ew is None else ew, qsrc, qobs, qp, qosrc,
                         "" if ttft is None else f"{ttft:.3f}",
                         "" if c.get("mean_running_obs") is None else f"{c['mean_running_obs']:.3f}",
                         lab, f"{re_:+.4f}", "" if ra is None else f"{ra:+.4f}",
                         p.get("population", c["population"]), f"{c['source']}; {c['src_file']}"])
    return with_cell_set(header, rows)


FIGURES = {
    "F_a_survival": fig_a_survival,
    "F_b_reuse_ratio_vs_N": fig_b_vs_n,
    "F_c_pred_vs_obs": fig_c_pred_vs_obs,
    "F_d_applicability": fig_d_applicability,
}


# -- writers --------------------------------------------------------------------

def p11_npu_simblind():
    """TASK95 cells: sim_op (main), sim, v1 (reference); ratio with CI; observed queue."""
    sv = load(SIM_VERDICT)
    qo = load(QUEUE_OBS)["cells"]
    header = ["cell", "판정 종류", "재사용 관측", "sim_op", "sim", "v1", "영", "비 m", "95 % CI",
              "비 sim_op", "비 sim", "비 v1", "v1 범위", "평균 running 관측", "관측 대기 Q 평균",
              "TTFT 중앙 (s)"]
    null = 0.6763527054108216
    rows = []
    for key, c in sv["cells"].items():
        r = sv["5.2"]["cells"].get(key)
        kind = "blind_confirm (§5.1 정보 없음)" if key == "BASE.n20" else "blind_confirm"
        rows.append([key, kind, f3(c["reuse_obs"]), f3(c["pred"]["sim_op"]["reuse"]),
                     f3(c["pred"]["sim"]["reuse"]), f3(c["pred"]["v1"]["reuse"]), f3(null),
                     f4(r["m"]) if r else "", f"[{r['ci'][0]:.4f}, {r['ci'][1]:.4f}]" if r else "",
                     f4(r["sim_op"]["pred"]) if r else "", f4(r["sim"]["pred"]) if r else "",
                     f4(r["v1"]["pred"]) if r else "", "안" if c["v1_in_scope"] else "밖",
                     f"{c['mean_running_obs']:.2f}", f"{qo[key]['mean_q']:.3f}",
                     f3(c["ttft_turn_ge1_median_s"])])
    ck = Check()
    s51, s52, s56 = sv["5.1"], sv["5.2"], sv["5.6"]
    ck.eq("재사용 MAE sim_op", round(s51["sim_op"]["MAE"], 3), 0.016, tol=5e-4, source="TASK95 판정 표")
    ck.eq("재사용 MAE sim", round(s51["sim"]["MAE"], 3), 0.013, tol=5e-4, source="TASK95 판정 표")
    ck.eq("영 MAE", round(s51["MAE_null"], 4), 0.1899, tol=5e-5, source="TASK95 판정 표")
    ck.eq("Σ|오차| sim_op", round(s52["sim_op"]["sum_abs_err"], 4), 0.1086, tol=5e-5, source="TASK95 판정 표")
    ck.eq("Σ|오차| sim", round(s52["sim"]["sum_abs_err"], 4), 0.1017, tol=5e-5, source="TASK95 판정 표")
    ck.eq("Σ|1 − m|", round(s52["sum_abs_1_minus_m"], 4), 1.4400, tol=5e-5, source="TASK95 판정 표")
    ck.eq("h TVD 중앙 sim_op", round(s56["sim_op"]["median"], 3), 0.060, tol=5e-4, source="TASK95 판정 표")
    ck.eq("BASE N17 재사용 관측", round(sv["cells"]["BASE.n17"]["reuse_obs"], 3), 0.047, tol=5e-4,
          source="TASK95 cell별 표")
    ck.eq("TUNED N13 m", round(s52["cells"]["TUNED.n13"]["m"], 4), 0.8614, tol=5e-5,
          source="TASK95 cell별 표")
    ck.eq("(1) 대 (2)", sv["simop_vs_sim"]["verdict"], "FAIL", source="TASK95 판정 표")
    notes = ["주 예측기 sim_op(SIMBLIND_PREREG.md: TASK92 운영 비용으로 시간 진행, 원래 비용으로 가격). "
             "sim = 원래 비용. v1 = 참고(N > 동시 실행 상한이면 범위 밖).",
             "BASE N20은 §5.1·skill에서 제외(정보 없음), 비용 비 분모로는 사용.",
             "관측 대기 Q = `queue_depth_obs.py`(client in-flight − `[BUCKET]` request_nums, decode step 가중). "
             "구조적으로 대기 0인 cell에서도 0이 아니다: N ≤ 8 전 구성 0.013–0.018, batch 16 N10–16 0.022–0.040 "
             "(전송·응답 종료 시간의 바닥값, 요청률과 함께 증가)."]
    return header, rows, notes, ck, [rel(SIM_VERDICT), rel(QUEUE_OBS)], "TASK93, TASK95"


TABLES["P11"] = (p11_npu_simblind, "NPU 통합 시뮬레이터 blind N = 13·17·20: sim_op·sim·v1")


def write_csv(path: Path, header, rows) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_table(tid: str, out_dir: Path) -> dict:
    fn, title = TABLES[tid]
    header, rows, notes, ck, inputs, tasks = fn()
    body = [f"# {tid} — {title}", "",
            f"- 근거: {tasks}",
            f"- 생성 명령: `env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py "
            f"--table {tid}`",
            "- 입력: " + ", ".join(f"`{i}`" for i in inputs), ""]
    body.append(render_md(header, rows))
    if notes:
        body += ["", "## 비고", ""] + [f"- {n}" for n in notes]
    body += ["", "## 기존 TASK 기록과의 대조", "",
             f"대조 {len(ck.rows)}건 중 불일치 **{len(ck.mismatches)}건**.", "",
             render_md(["항목", "재계산", "기록", "허용차", "일치", "출처"],
                       [[r["항목"], r["재계산"], r["기록"], r["허용차"],
                         "OK" if r["일치"] else "**불일치**", r["출처"]] for r in ck.rows])]
    (out_dir / f"{tid}.md").write_text("\n".join(body) + "\n")
    write_csv(out_dir / f"{tid}.csv", header, rows)
    return {"id": tid, "title": title, "tasks": tasks, "inputs": inputs, "rows": len(rows),
            "checks": len(ck.rows), "mismatches": [dict(m) for m in ck.mismatches], "built": True}


README_BEGIN = "<!-- paper-tables:begin (make_paper_tables.py --all) -->"
README_END = "<!-- paper-tables:end -->"


def update_readme(out_dir: Path, tables: list[dict], figures: list[dict]) -> None:
    path = out_dir / "README.md"
    text = path.read_text() if path.exists() else ""
    lines = [README_BEGIN, "", "## 논문 표·그림 데이터 (P·F 계열, 지시문 08 작업 D)", "",
             "```bash", "env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all",
             "```", "",
             "| 표 | 제목 | 파일 | 생성 명령 | 근거 | 대조 | 불일치 |", "|---|---|---|---|---|---|---|"]
    for s in tables:
        if s["built"]:
            lines.append(f"| {s['id']} | {s['title']} | `{s['id']}.md` / `{s['id']}.csv` | "
                         f"`make_paper_tables.py --table {s['id']}` | {s['tasks']} | {s['checks']} | "
                         f"{len(s['mismatches'])} |")
        else:
            lines.append(f"| {s['id']} | {s['title']} | 미생성 | `make_paper_tables.py --table {s['id']}` | "
                         f"— | — | 미생성: {s['reason']} |")
    lines += ["", "| 그림 데이터 | 파일 | 행 | 생성 명령 |", "|---|---|---|---|"]
    for f in figures:
        lines.append(f"| {f['id']} | `{FIG_DIR_NAME}/{f['id']}.csv` | {f.get('rows', '미생성')} | "
                     f"`make_paper_tables.py --all` |")
    lines += ["", "생성 시각·commit·미생성 사유는 `paper_manifest.json`.", "", README_END]
    block = "\n".join(lines)
    if README_BEGIN in text:
        pre = text.split(README_BEGIN)[0].rstrip("\n")
        post = text.split(README_END, 1)[1].lstrip("\n") if README_END in text else ""
        text = pre + "\n\n" + block + "\n" + (("\n" + post) if post else "")
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    path.write_text(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", help="single table id, e.g. P02")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out-dir", type=Path, default=REPO / "results/tables")
    a = ap.parse_args()
    if not a.table and not a.all:
        raise SystemExit("--table ID 또는 --all 중 하나가 필요하다")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    ids = list(TABLES) if a.all else [a.table]
    summary = []
    for tid in ids:
        if tid not in TABLES:
            raise SystemExit(f"알 수 없는 표 id {tid!r}. 가능한 값: {', '.join(TABLES)}")
        try:
            s = write_table(tid, a.out_dir)
        except MissingInput as e:
            s = {"id": tid, "title": TABLES[tid][1], "built": False, "reason": str(e)}
            print(f"{tid:>4}  미생성 — {e}")
            summary.append(s)
            continue
        summary.append(s)
        mark = "OK" if not s["mismatches"] else f"불일치 {len(s['mismatches'])}건"
        print(f"{tid:>4}  {s['title']:<44} 행 {s['rows']:>3}  대조 {s['checks']:>3}  {mark}")
        for m in s["mismatches"]:
            print(f"        - {m['항목']}: 재계산 {m['재계산']} 대 기록 {m['기록']} ({m['출처']})")
    if not a.all:
        return 0
    fig_dir = a.out_dir / FIG_DIR_NAME
    fig_dir.mkdir(exist_ok=True)
    figs = []
    for fid, fn in FIGURES.items():
        try:
            header, rows = fn()
        except MissingInput as e:
            figs.append({"id": fid, "built": False, "reason": str(e)})
            print(f"{fid}  미생성 — {e}")
            continue
        write_csv(fig_dir / f"{fid}.csv", header, rows)
        figs.append({"id": fid, "built": True, "rows": len(rows), "columns": header})
        print(f"{fid:<22} 행 {len(rows)}")
    update_readme(a.out_dir, summary, figs)
    head = _git("rev-parse", "HEAD").strip()
    dirty = _git("status", "--porcelain").strip()
    gpu_head = _git("rev-parse", "--short", GPU_BRANCH).strip()
    (a.out_dir / "paper_manifest.json").write_text(json.dumps(
        {"generated_at": dt.datetime.now().astimezone().isoformat(), "git_head": head,
         "git_dirty": dirty, "gpu_branch": GPU_BRANCH, "gpu_branch_head": gpu_head,
         "python": sys.version, "tables": summary, "figures": figs,
         "not_built_here": [
             {"id": "arXiv 세 기전 (padding·격자, prefill 직렬화, 재사용 절벽)",
              "reason": "기존 make_tables.py 표 T01–T14·A01·S02–S08이 이미 담는다; P 계열로 중복 생성하지 않음"},
             {"id": "R1–R5′ 판정 요약", "reason": "기존 M01–M05가 담는다"}]},
        indent=2, ensure_ascii=False) + "\n")
    tot = sum(len(s.get("mismatches", [])) for s in summary)
    print(f"\n표 {sum(s['built'] for s in summary)}/{len(summary)}개, 대조 "
          f"{sum(s.get('checks', 0) for s in summary)}건, 불일치 {tot}건 → {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
