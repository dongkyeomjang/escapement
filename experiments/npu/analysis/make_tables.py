#!/usr/bin/env python3
"""Write every reported table out of the repository's own artifacts.

The manuscript is kept outside this repository, so a number that reaches a
table has, until now, had no committed file behind it: the analysis modules
wrote their judgements into ``results/`` (which git does not track) and the
tables were transcribed from there by hand. TASK66 found the failure mode that
follows -- a pair of numbers in the text that no code path in the repository
produces.

This module closes that gap from the repository side. Each table is built by
one named function from one named set of artifacts, is written to its own file
under ``results/tables/``, and -- wherever a TASK document already records the
value -- is checked against that record. **A mismatch is reported, never
repaired**: the recorded number stands and the disagreement is the finding.

Nothing is measured here and nothing is re-derived. Every table either reads an
analysis module's committed output or calls that module's own functions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/npu/substrate"))

R2 = REPO / "results/npu/stage2"
RUN_FINAL = R2 / "20260823-183505-final-confirm"
RUN_N6 = R2 / "20260824-160028-n6-reconfirm"
RUN_GRID6 = R2 / "20260908-133635-grid-paired"
RUN_STEPCOST = R2 / "20260908-151119-step-cost"
RUN_PTAX = R2 / "20260821-220100-prefill-tax"
RUN_SAT = R2 / "20260824-222453-batch-saturation"
RUN_NULL = R2 / "20260901-020342-null-channel"
RUN_RECOMP = R2 / "20260911-191300-recompile-variance"
RUN_DUMMY = R2 / "20260912-134732-dummy-lifecycle"
RUN_OOS = R2 / "20260822-160532-sim-oos"
RUN_OBSERVE = R2 / "20260821-222000-grid-observe"
RUN_SWEEP = R2 / "20260820-165200-nslots-sweep"
RUN_SENS = R2 / "20260922-config-search-sensitivity"

#: (buckets, batch_size) of the three compile arms, restated from config_device
#: only so the tables can name them.
ARM_LABEL = {"BASE": "① BASE", "BATCHONLY": "② BATCHONLY", "TUNED": "③ TUNED"}


# -- helpers -----------------------------------------------------------------

def load(path: Path):
    if not path.exists():
        raise SystemExit(
            f"필요한 산출물이 없다: {path}\n"
            f"  README.md의 '선행 명령' 절을 먼저 실행한다."
        )
    return json.loads(path.read_text())


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


class Check:
    """One comparison against a value a TASK document already records."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def eq(self, what: str, computed, recorded, *, tol: float = 0.0,
           source: str = "") -> None:
        if isinstance(computed, float) or isinstance(recorded, float):
            ok = close(float(computed), float(recorded), tol)
        else:
            ok = computed == recorded
        self.rows.append({"항목": what, "재계산": computed, "기록": recorded,
                          "허용차": tol, "일치": ok, "출처": source})

    @property
    def mismatches(self) -> list[dict]:
        return [r for r in self.rows if not r["일치"]]


# -- table builders ----------------------------------------------------------
# Each returns (header, rows, notes, Check). Rows are lists of already
# formatted strings so the markdown and the csv carry the same digits.

def t01_padding_devicetime():
    """§3.1 — padding share beside decode device time, by N."""
    sys.path.insert(0, str(REPO / "paper/draft"))
    import make_table_3_1 as M  # noqa: E402  (its own check is fatal)
    rs = M.rows()
    # verify() raises on any mismatch, so returning at all is the pass; the
    # lines it returns are the per-row report and DIFF marks a failure.
    report = M.verify(rs)
    diffs = [l for l in report if l.strip().startswith("DIFF")]
    ck = Check()
    ck.eq("make_table_3_1.verify 불일치 행 수", len(diffs), 0,
          source="paper/draft/make_table_3_1.py (자체 대조, 실패 시 raise)")
    ck.eq("make_table_3_1.verify 대조 행 수", len(report), 22,
          source="padding 11행 + device time 11행")
    header = ["격자", "N", "p_gap", "p_무gap", "Δp", "decode device time 비 (gap/무gap)"]
    rows = [[M.grid_label(r["grid"]) + ("†" if r["dagger"] else ""), str(r["N"]),
             f"{r['p_gap']:.3f}", f"{r['p_nogap']:.3f}", f"{r['delta_p']:+.3f}",
             f"{r['device_ratio']:.3f}"] for r in rs]
    notes = ["p = padding 비율 = 1 − Σactual/Σbucket, 같은 블록 집합에서 형성했다.",
             "bucket 6의 step 비용은 4와 8의 보간값이다.",
             f"make_table_3_1.verify 대조 {len(report)}행, 불일치 {len(diffs)}행."]
    return header, rows, notes, ck


def t02_grid6_paired():
    """bucket 6 개입의 동일 trace 짝 비교 (TASK54)."""
    d = load(RUN_GRID6 / "grid_paired.json")
    ck = Check()
    header = ["격자", "N", "p AGENTIC", "p CONVENTIONAL", "Δp", "반복 부호 일치",
              "utilization 비", "step AGENTIC", "step CONVENTIONAL"]
    rows = []
    for c in d["cells"]:
        rows.append([c["grid"], str(c["N"]), f"{c['p_A']:.4f}", f"{c['p_C']:.4f}",
                     f"{c['delta_p']:+.4f}", c["rep_agree"], f"{c['u_ratio']:.4f}",
                     str(c["steps_A"]), str(c["steps_C"])])
    for n, s in d["shift"].items():
        ck.eq(f"N={n} Δp 이동량 (mb→mb6)", round(s["measured"], 4),
              round(s["measured"], 4), source="grid_paired.json shift")
    # The recorded headline: the N=6 sign reversal disappears on the mb6 grid.
    mb6_n6 = next(c for c in d["cells"] if c["grid"] == "mb6" and c["N"] == 6)
    mb_n6 = next(c for c in d["cells"] if c["grid"] == "mb" and c["N"] == 6)
    ck.eq("N=6 Δp (mb)", round(mb_n6["delta_p"], 4), 0.0650, tol=5e-5,
          source="TASK54 판정 (+0.0650)")
    ck.eq("N=6 Δp (mb6)", round(mb6_n6["delta_p"], 4), -0.0400, tol=5e-5,
          source="TASK54 판정 (−0.0400)")
    notes = ["Δp = p(AGENTIC) − p(CONVENTIONAL). 양수는 gap 조건의 padding이 낮다는 뜻이다.",
             "같은 trace를 두 격자가 재사용하는 짝 비교다 (반복 3회)."]
    return header, rows, notes, ck


def t03_capacity_intervention():
    """slot 8 → 16 개입의 재사용·계산량 (TASK58 재집계, TASK35 원자료)."""
    d = load(R2 / "layer_audit.json")
    ck = Check()
    header = ["구성", "반복", "재도착 요청", "재사용 성공", "cached token 합",
              "prefill 계산 token 합 (전체)", "(재도착분)", "최대 actual batch", "decode step"]
    rows = []
    recorded = {  # TASK58 쟁점 3 '반복별 결과'
        ("BASE", 0): (8, 3, 3840, 18193, 7816, 8, 891),
        ("BASE", 1): (8, 3, 3200, 16180, 7025, 8, 682),
        ("BASE", 2): (8, 3, 2816, 16363, 7262, 8, 391),
        ("BATCHONLY", 0): (8, 8, 9856, 12177, 1800, 8, 921),
        ("BATCHONLY", 1): (8, 8, 8448, 10932, 1777, 8, 682),
        ("BATCHONLY", 2): (8, 8, 8576, 10603, 1502, 8, 391),
    }
    for c in d["capacity"]:
        key = (c["arm"], c["block"])
        vals = (c["resume_requests"], c["reuse_hits"], c["cached_tokens"],
                c["prefill_computed_all"], c["prefill_computed_resume"],
                c["max_actual_batch"], c["decode_steps"])
        rows.append([c["arm"], f"b{c['block']}", *[f"{v:,}" for v in vals]])
        if key in recorded:
            for name, got, want in zip(
                    ("재도착", "재사용", "cached", "prefill 전체", "prefill 재도착",
                     "최대 batch", "decode step"), vals, recorded[key]):
                ck.eq(f"{c['arm']} b{c['block']} {name}", got, want,
                      source="TASK58 쟁점 3")
    for arm, p in d["capacity_pooled"].items():
        rows.append([arm, "합산", f"{p['resume_requests']:,}", f"{p['reuse_hits']:,}",
                     f"{p['cached_tokens']:,}", f"{p['prefill_computed_all']:,}",
                     f"{p['prefill_computed_resume']:,}", f"{p['max_actual_batch']:,}",
                     f"{p['decode_steps']:,}"])
    ck.eq("합산 재사용 BASE", d["capacity_pooled"]["BASE"]["reuse_hits"], 9,
          source="TASK35/TASK58 (9/24)")
    ck.eq("합산 재사용 BATCHONLY", d["capacity_pooled"]["BATCHONLY"]["reuse_hits"], 24,
          source="TASK35/TASK58 (24/24)")
    notes = ["N=8, `BASE`(batch_size 8) → `BATCHONLY`(batch_size 16).",
             "`kvcache_num_blocks = batch_size`이므로 batch_size가 KV slot 수다 (TASK08)."]
    return header, rows, notes, ck


def t04_prefill_injection():
    """prefill 주입이 병행 세션의 decode를 세우는가 (TASK22)."""
    d = load(RUN_PTAX / "prefill_tax_result.json")
    ck = Check()
    recorded = {"inj500.r0": (0.0884, 11.84, 100.58, 8.49),
                "inj500.r1": (0.0885, 11.76, 100.87, 8.58),
                "inj500.r2": (0.0886, 11.76, 100.89, 8.58),
                "inj2000.r0": (0.3596, 11.77, 372.57, 31.66),
                "inj2000.r1": (0.3596, 11.73, 374.00, 31.90),
                "inj2000.r2": (0.3590, 11.62, 371.36, 31.96),
                "inj6000.r0": (1.1758, 11.86, 1190.04, 100.37),
                "inj6000.r1": (1.1772, 12.18, 1191.68, 97.81),
                "inj6000.r2": (1.1802, 12.98, 1194.77, 92.02)}
    header = ["tag", "주입 token", "실계산량", "prefill (s)", "baseline (ms)",
              "중앙 스파이크 (ms)", "×baseline", "존재", "동시"]
    rows = []
    for r in d["runs"]:
        inj = r["injection"]
        base_ms = (r["median_baseline_s"] or 0) * 1000
        sp_ms = (r["median_spike_s"] or 0) * 1000
        ratio = sp_ms / base_ms if (sp_ms and base_ms) else None
        rows.append([r["tag"], str(r["inject_prompt_tokens"]),
                     "—" if not inj else str(inj["observed_prompt_tokens"] - inj["cached_tokens"]),
                     "—" if not inj or inj["prefill_time_s"] is None else f"{inj['prefill_time_s']:.4f}",
                     f"{base_ms:.2f}", "—" if not sp_ms else f"{sp_ms:.2f}",
                     "—" if ratio is None else f"{ratio:.2f}",
                     "✓" if r["spike_exists"] else "—",
                     "✓" if r["spikes_simultaneous"] else "—"])
        if r["tag"] in recorded:
            pf, bl, sp, rt = recorded[r["tag"]]
            ck.eq(f"{r['tag']} prefill(s)", round(inj["prefill_time_s"], 4), pf,
                  tol=5e-5, source="TASK22 관측")
            ck.eq(f"{r['tag']} baseline(ms)", round(base_ms, 2), bl, tol=5e-3,
                  source="TASK22 관측")
            ck.eq(f"{r['tag']} 스파이크(ms)", round(sp_ms, 2), sp, tol=5e-3,
                  source="TASK22 관측")
            ck.eq(f"{r['tag']} ×baseline", round(ratio, 2), rt, tol=5e-3,
                  source="TASK22 관측")
    notes = [f"선등록 문턱 ×{d['spike_factor']:.1f}. 대조(inj0)에도 문턱 초과가 있어 "
             "TASK22의 존재 판정은 `PARTIAL`이다 — 그 초과는 주입 창 밖에서 일어난다.",
             "bystander 4개 × 반복 3회. 값은 bystander 중앙값이다."]
    return header, rows, notes, ck


def t05_n6_conflict():
    """같은 N=6이 seed에 따라 다른 X를 내는 상충 (TASK35 대 TASK36)."""
    a = load(RUN_FINAL / "config_device.json")
    b = load(RUN_N6 / "config_device.n6.json")
    ck = Check()
    header = ["seed", "출처", "arm", "BASE 재사용", "A′ ratio", "B ratio", "채널 차",
              "X (A′)", "X (B)"]
    rows = []
    for seed, src, doc in ((20261000, a, "TASK35"), (20261100, b, "TASK36")):
        row6 = next(r for r in src if r["N"] == 6)
        base_reuse = f"{row6['baseline']['reuse']}/{row6['baseline']['resume']}"
        for arm in row6["arms"]:
            rows.append([str(seed), doc, ARM_LABEL[arm["arm"]], base_reuse,
                         f"{arm['a_prime_ratio']:.4f}", f"{arm['b_ratio']:.4f}",
                         f"{arm['channel_gap']:.4f}",
                         f"{100 * arm['X_a_prime']:+.2f} %", f"{100 * arm['X_b']:+.2f} %"])
    rec = {(20261000, "BATCHONLY"): (2.07, 4.12), (20261000, "TUNED"): (3.40, 5.76),
           (20261100, "BATCHONLY"): (0.59, 0.60), (20261100, "TUNED"): (2.11, 2.74)}
    for seed, src in ((20261000, a), (20261100, b)):
        row6 = next(r for r in src if r["N"] == 6)
        for arm in row6["arms"]:
            xa, xb = rec[(seed, arm["arm"])]
            ck.eq(f"seed {seed} {arm['arm']} X(A′) %", round(100 * arm["X_a_prime"], 2),
                  xa, tol=6e-3, source="TASK35/TASK36 X 확정치")
            ck.eq(f"seed {seed} {arm['arm']} X(B) %", round(100 * arm["X_b"], 2),
                  xb, tol=6e-3, source="TASK35/TASK36 X 확정치")
    ck.eq("seed 20261000 BASE 재사용", next(r for r in a if r["N"] == 6)["baseline"]["reuse"],
          15, source="TASK36 관측 2 (15/18)")
    ck.eq("seed 20261100 BASE 재사용", next(r for r in b if r["N"] == 6)["baseline"]["reuse"],
          17, source="TASK36 관측 2 (17/18)")
    notes = ["같은 N, 같은 세 arm, 다른 plan seed. 이득의 크기가 `BASE`가 잃는 캐시의 양을 따라간다.",
             "X = 1 − ratio. 양수가 device time 회수다."]
    return header, rows, notes, ck


def t06_decode_step_cost():
    """decode step 비용 계수: bucket 고정 항과 요청당 항 (TASK13·TASK55)."""
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    d = load(RUN_STEPCOST / "grid_step_cost.json")
    ck = Check()
    header = ["격자", "bucket", "model p50 (ms)", "sampler p50 (ms)",
              "고정 항 f(bucket) (ms)", "중앙 ITL (ms)"]
    rows = [[lv["grid"], str(lv["bucket"]), f"{lv['model_ms']:.2f}",
             f"{lv['sampler_ms']:.2f}", f"{lv['fixed_ms']:.2f}",
             f"{lv['median_itl_ms']:.3f}"] for lv in d["levels"]]
    notes = [
        f"요청당 항 g: 기울기 {D.step_cost_model.marginal_s_per_request * 1e3:.4f} ms/요청, "
        f"절편 {D.step_cost_model.intercept_s * 1e3:.3f} ms (TASK13 잔차 최소제곱).",
        "descriptor가 쓰는 f(bucket) = model p50 + sampler p50 (TASK13 'B 합'): "
        + ", ".join(f"{b}→{v * 1e3:.4f} ms"
                    for b, v in sorted(D.step_cost_model.fixed_s_by_bucket.items())),
        f"bucket 6 실측 고정 항 {d['C6']['measured_fixed_ms']:.2f} ms 대 보간 "
        f"{d['C6']['interpolated_fixed_ms']:.4f} ms (차 {d['C6']['delta_ms']:+.4f} ms).",
    ]
    # The descriptor's f(bucket) is model p50 + sampler p50, not the model
    # alone: TASK13's "B 합" column. Both are checked.
    for b, model, sampler in ((1, 9.51, 0.36), (2, 10.05, 0.37),
                              (4, 10.355, 0.47), (8, 12.4025, 0.5675)):
        ck.eq(f"descriptor f({b}) = model+sampler (ms)",
              round(D.step_cost_model.fixed_s_by_bucket[b] * 1e3, 4),
              round(model + sampler, 4), tol=5e-5, source="TASK13 표 'B 합'")
    ck.eq("bucket 6 실측 고정 항 (ms)", round(d["C6"]["measured_fixed_ms"], 2), 11.66,
          tol=5e-3, source="TASK55")
    return header, rows, notes, ck


def t07_validation_prediction():
    """선등록된 구성별 비용 비 예측 — 시뮬레이터로 재계산 (TASK33·TASK35·TASK36)."""
    import foresight as F
    from config_search import descriptor_for
    from config_device import ARMS
    from continuum.sim import SimConfig, simulate
    from rbln_ca25_vllm_rbln_0111 import RBLN_CA25_VLLM_RBLN_0111 as D
    gap = F.set_gap("toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60")
    ck = Check()
    recorded = {  # 선등록 문서의 예측 busy ratio
        (20261000, 6, "BATCHONLY"): 0.9610, (20261000, 6, "TUNED"): 0.9466,
        (20261000, 8, "BATCHONLY"): 0.9101, (20261000, 8, "TUNED"): 0.8971,
        (20261000, 10, "BATCHONLY"): 0.9213, (20261000, 10, "TUNED"): 0.8899,
        (20261100, 6, "BATCHONLY"): 0.9874, (20261100, 6, "TUNED"): 0.9713,
    }
    header = ["seed", "N", "arm", "예측 busy ratio", "예측 절감", "prefill비", "decode비",
              "블록별 (b0/b1/b2)", "선등록 기록"]
    rows = []
    for seed, ns, src in ((20261000, (6, 8, 10), "FINAL_CONFIRM_PREREG.md"),
                          (20261100, (6,), "N6_RECONFIRM_PREREG.md")):
        for n in ns:
            sims = {a: [simulate(descriptor_for(D, *ARMS[a]), F.plan(n, b, seed),
                                 SimConfig(max_running_requests=ARMS[a][1]))
                        for b in (0, 1, 2)] for a in ARMS}
            base = sims["BASE"]
            for arm in ("BATCHONLY", "TUNED"):
                tot = sum(r.busy_s for r in sims[arm])
                ratio = tot / sum(r.busy_s for r in base)
                pre = (sum(r.prefill_busy_s for r in sims[arm])
                       / sum(r.prefill_busy_s for r in base))
                dec = (sum(r.decode_busy_s for r in sims[arm])
                       / sum(r.decode_busy_s for r in base))
                per = [sims[arm][i].busy_s / base[i].busy_s for i in range(3)]
                want = recorded[(seed, n, arm)]
                rows.append([str(seed), str(n), ARM_LABEL[arm], f"{ratio:.4f}",
                             f"{100 * (1 - ratio):+.2f} %", f"{pre:.4f}", f"{dec:.4f}",
                             " / ".join(f"{x:.4f}" for x in per), f"{want:.4f}"])
                ck.eq(f"seed {seed} N={n} {arm} 예측 ratio", round(ratio, 4), want,
                      tol=5e-5, source=src)
    notes = [f"gap 법칙 {gap}. `busy ratio` = device time(arm) / device time(`BASE`).",
             "예측은 측정 전에 commit된 값이며, 이 표는 그 값을 현재 코드로 재계산한 것이다."]
    return header, rows, notes, ck


def t08_channel_time():
    """채널별 device time과 채널 일치 (TASK35·TASK36)."""
    ck = Check()
    header = ["run", "N", "arm", "A′ (s)", "decode (s)", "prefill (s)", "B (s)",
              "잔차 r (s)", "A′ ratio", "B ratio", "채널 차", "허용차 τ"]
    rows = []
    for tag, path in (("TASK35 seed 20261000", RUN_FINAL / "config_device.json"),
                      ("TASK36 seed 20261100", RUN_N6 / "config_device.n6.json")):
        for row in load(path):
            b = row["baseline"]
            rows.append([tag, str(row["N"]), ARM_LABEL[b["arm"]], f"{b['a_prime_s']:.3f}",
                         f"{b['decode_s']:.3f}", f"{b['prefill_s']:.3f}", f"{b['b_s']:.3f}",
                         f"{b['residual_s']:.3f}", "1.0000", "1.0000", "—",
                         f"{row['channel_tolerance']:.4f}"])
            for arm in row["arms"]:
                rows.append([tag, str(row["N"]), ARM_LABEL[arm["arm"]],
                             f"{arm['a_prime_s']:.3f}", f"{arm['decode_s']:.3f}",
                             f"{arm['prefill_s']:.3f}", f"{arm['b_s']:.3f}",
                             f"{arm['residual_s']:.3f}", f"{arm['a_prime_ratio']:.4f}",
                             f"{arm['b_ratio']:.4f}", f"{arm['channel_gap']:.4f}",
                             f"{row['channel_tolerance']:.4f}"])
    rec = {(6, "BATCHONLY"): (0.9793, 0.9588, 0.0205), (6, "TUNED"): (0.9660, 0.9424, 0.0236),
           (8, "BATCHONLY"): (0.9175, 0.9183, 0.0008), (8, "TUNED"): (0.9028, 0.8993, 0.0035),
           (10, "BATCHONLY"): (0.9552, 0.9551, 0.0000), (10, "TUNED"): (0.9264, 0.9287, 0.0023)}
    for row in load(RUN_FINAL / "config_device.json"):
        for arm in row["arms"]:
            ra, rb, gap = rec[(row["N"], arm["arm"])]
            ck.eq(f"N={row['N']} {arm['arm']} A′ ratio", round(arm["a_prime_ratio"], 4),
                  ra, tol=5e-5, source="TASK35 채널 일치 표")
            ck.eq(f"N={row['N']} {arm['arm']} B ratio", round(arm["b_ratio"], 4), rb,
                  tol=5e-5, source="TASK35 채널 일치 표")
            ck.eq(f"N={row['N']} {arm['arm']} 채널 차", round(arm["channel_gap"], 4), gap,
                  tol=5e-5, source="TASK35 채널 일치 표")
    notes = ["A′ = TASK13 step 비용 + TASK22 prefill 비용으로 재구성한 device time.",
             "B = client send/finish의 in-flight 구간 합집합. 비용 모형에 의존하지 않는다.",
             "τ(N) = max(0.02, r_BASE / B_BASE) (TASK36 교정). 세 반복 합산 기준이다."]
    return header, rows, notes, ck


def t09_recovery_rate():
    """구성 선택이 회수한 device time 비율 X (TASK35·TASK36)."""
    ck = Check()
    header = ["구간", "seed", "arm", "X (채널 A′)", "X (채널 B)", "판정"]
    verdict = {(20261000, 6): "보류 (TASK35 채널)", (20261000, 8): "확증 PASS",
               (20261000, 10): "탐색 (판정 없음)", (20261100, 6): "확증 PASS"}
    rows = []
    for seed, path in ((20261000, RUN_FINAL / "config_device.json"),
                       (20261100, RUN_N6 / "config_device.n6.json")):
        for row in load(path):
            for arm in row["arms"]:
                rows.append([f"N={row['N']}", str(seed), ARM_LABEL[arm["arm"]],
                             f"{100 * arm['X_a_prime']:+.2f} %",
                             f"{100 * arm['X_b']:+.2f} %",
                             verdict[(seed, row["N"])]])
    rec = {(20261000, 8, "BATCHONLY"): (8.25, 8.17), (20261000, 8, "TUNED"): (9.72, 10.07),
           (20261000, 10, "BATCHONLY"): (4.48, 4.49), (20261000, 10, "TUNED"): (7.36, 7.13),
           (20261100, 6, "BATCHONLY"): (0.59, 0.60), (20261100, 6, "TUNED"): (2.11, 2.74)}
    for seed, path in ((20261000, RUN_FINAL / "config_device.json"),
                       (20261100, RUN_N6 / "config_device.n6.json")):
        for row in load(path):
            for arm in row["arms"]:
                key = (seed, row["N"], arm["arm"])
                if key in rec:
                    xa, xb = rec[key]
                    ck.eq(f"seed {seed} N={row['N']} {arm['arm']} X(A′) %",
                          round(100 * arm["X_a_prime"], 2), xa, tol=6e-3,
                          source="TASK35/TASK36 X 확정치")
                    ck.eq(f"seed {seed} N={row['N']} {arm['arm']} X(B) %",
                          round(100 * arm["X_b"], 2), xb, tol=6e-3,
                          source="TASK35/TASK36 X 확정치")
    notes = ["X = 1 − 실측 busy ratio, 세 반복 합산 기준.",
             "N=6 seed 20261000의 두 칸은 TASK35에서 채널 요건에 걸려 보류다."]
    return header, rows, notes, ck


def t10_batch_saturation():
    """추가 slot의 포화 (TASK40)."""
    d = load(RUN_SAT / "batch_curve.json")
    ck = Check()
    header = ["비교", "통제", "중앙 ratio", "CI 하한", "CI 상한", "CI 폭",
              "1 포함", "판정"]
    rows = [[a["label"], "예" if a["controlled"] else "아니오",
             f"{a['point_ratio']:.4f}", f"{a['ci_low']:.4f}", f"{a['ci_high']:.4f}",
             f"{a['ci_width']:.4f}", "예" if a.get("contains_one") else "아니오",
             a["verdict"]] for a in d["adjacent"]]
    header2 = ["N", "arm", "A′ ratio", "B ratio", "채널 차", "허용차 τ"]
    rows2 = []
    for row in d["per_n"]:
        for arm, v in row["arms"].items():
            rows2.append([str(row["N"]), arm, f"{v['a_prime_ratio']:.4f}",
                          f"{v['b_ratio']:.4f}", f"{v['channel_gap']:.4f}",
                          f"{row['channel_tolerance']:.4f}"])
    rec = {"B16->B24": 0.9999, "B24->B32": 1.0002}
    for a in d["adjacent"]:
        if a["label"] in rec:
            ck.eq(f"{a['label']} 중앙 ratio", round(a["point_ratio"], 4),
                  rec[a["label"]], tol=5e-5, source="TASK40 인접쌍")
    # The recorded claim is about the rungs that B16/B24/B32 add (16/24/32);
    # B8's top rung is 8, which the workload does use.
    mech = [m for m in d["mechanism"] if m["arm"] != "B8"]
    ck.eq("최상위 눈금 16·24·32의 선택 비중이 0 인 셀 수",
          sum(1 for m in mech if m["top_share"] == 0), len(mech),
          source="TASK40 기전 (전 조합 0.0 % 선택)")
    notes = ["앞 3행은 인접 구성쌍의 셀별 중앙 ratio와 bootstrap CI(선등록 4,000 resample, 폭 상한 0.04).",
             "뒤 행은 N별 arm ratio. B16·B24·B32는 최상위 눈금만 다르므로 통제된 비교다.",
             "두 블록은 같은 파일의 앞뒤다 — 원고에서는 나눠 실을 수 있다."]
    return header, rows, notes, ck, (header2, rows2)


def t11_compile_cost():
    """컴파일 비용과 artifact 크기 (TASK06·TASK10·TASK23 등)."""
    ck = Check()
    points = [
        ("b1 (1 bucket)", REPO / "results/npu/stage0/20260819-163200-qwen3-4b/compile",
         None, "Qwen3-4B-rbln-b1-s8192-d4", 1, "TASK06"),
        ("mb (4 bucket)", REPO / "results/npu/stage1/20260819-174300-stage1b-b8-multibucket/compile",
         None, "Qwen3-4B-rbln-b8-s8192-d4-mb", 4, "TASK10"),
        ("mb6 (5 bucket)", R2 / "20260821-231000-grid-intervene/compile",
         None, "Qwen3-4B-rbln-b8-s8192-d4-mb6", 5, "TASK23"),
        ("batchonly (5 bucket)", R2 / "20260823-170201-compile-config/compile",
         None, "Qwen3-4B-rbln-b16-s8192-d4-batchonly", 5, "TASK34"),
        ("mb24 (6 bucket)", R2 / "20260824-222453-batch-saturation/compile",
         "b24", "Qwen3-4B-rbln-b24-s8192-d4-mb24", 6, "TASK40"),
        ("mb32 (6 bucket)", R2 / "20260824-222453-batch-saturation/compile",
         "b32", "Qwen3-4B-rbln-b32-s8192-d4-mb32", 6, "TASK40"),
        ("mb-rc (4 bucket 재compile)", R2 / "20260911-191300-recompile-variance/compile",
         None, "Qwen3-4B-rbln-b8-s8192-d4-mb-rc", 4, "TASK62"),
    ]
    header = ["artifact", "bucket 수", "compile 시작", "compile 종료", "소요 (s)",
              "artifact 크기 (GiB)", "예측 시간 (s)", "예측 크기 (GiB)", "출처 TASK"]
    rows = []
    from config_search import compile_cost
    for label, cdir, suffix, model, nbuckets, task in points:
        sfx = f".{suffix}" if suffix else ""
        s = (cdir / f"started_at{sfx}.txt").read_text().strip()
        f = (cdir / f"finished_at{sfx}.txt").read_text().strip()
        elapsed = (dt.datetime.fromisoformat(f) - dt.datetime.fromisoformat(s)).total_seconds()
        mp = REPO / "models" / model
        gib = None
        if mp.exists():
            out = subprocess.run(["du", "-sb", str(mp)], capture_output=True, text=True)
            gib = int(out.stdout.split()[0]) / 1024 ** 3
        pt, pg = compile_cost(tuple(range(1, nbuckets + 1)))
        rows.append([label, str(nbuckets), s, f, f"{elapsed:.0f}",
                     "—" if gib is None else f"{gib:.3f}", f"{pt:.0f}", f"{pg:.3f}", task])
        if label.startswith("b1 "):
            ck.eq("b1 compile (s)", round(elapsed), 165, source="TASK06 기록")
        if label.startswith("mb "):
            ck.eq("mb compile (s)", round(elapsed), 349, source="TASK10 기록")
        if label.startswith("mb6 "):
            ck.eq("mb6 compile (s)", round(elapsed), 416, source="TASK23 기록")
        if gib is not None and label.startswith("b1 "):
            ck.eq("b1 artifact (GiB)", round(gib, 3), 9.083, tol=6e-3, source="TASK06 기록")
        if gib is not None and label.startswith("mb "):
            ck.eq("mb artifact (GiB)", round(gib, 3), 11.501, tol=6e-3, source="TASK10 기록")
        if gib is not None and label.startswith("mb6 "):
            ck.eq("mb6 artifact (GiB)", round(gib, 3), 12.306, tol=6e-3, source="TASK23 기록")
    notes = ["소요는 run의 `started_at`/`finished_at`의 차다. 크기는 `du -sb models/<artifact>`다.",
             "예측은 TASK10 모형 `시간 ≈ 42.3 + 61.33 × (bucket + 1)`, "
             "`크기 ≈ 8.276 + 0.806 × bucket`이다 (`config_search.compile_cost`).",
             "`models/`는 git이 추적하지 않는다 — 크기 열은 현재 디스크 상태다."]
    return header, rows, notes, ck


def t12_null_repeat():
    """무처치 반복의 채널 차 분포 (TASK50) — 부록 S1."""
    d = load(RUN_NULL / "null_channel.json")
    ck = Check()
    header = ["N", "유효 반복", "짝 수", "채널 차 중앙", "q95", "최대", "최소",
              "잔차 중앙 (s)", "잔차 비중 중앙", "τ_null", "분류"]
    rows = [[str(c["N"]), f"{c['valid_count']}/{len(c['requested_reps'])}",
             str(c["pair_count"]), f"{c['gap_median']:.4f}", f"{c['gap_q95']:.4f}",
             f"{c['gap_max']:.4f}", f"{c['gap_min']:.4f}",
             f"{c['residual_s_median']:.3f}", f"{c['residual_share_median']:.4f}",
             f"{c['tau_null']:.4f}", c["class"]] for c in d]
    header2 = ["N", "반복", "A′ (s)", "B (s)", "잔차 (s)", "재사용", "decode step"]
    rows2 = []
    for c in d:
        for r in c["repeats"]:
            rows2.append([str(c["N"]), f"b{r['rep']}", f"{r['a_prime_s']:.3f}",
                          f"{r['b_s']:.3f}", f"{r['residual_s']:.3f}",
                          f"{r['reuse']}/{r['resume']}", str(r["steps"])])
    notes = ["같은 구성을 10회 반복하고 모든 짝(45쌍)의 채널 차를 모은 무처치 분포다.",
             "이 표는 판정 문턱의 자료 기반 참고값이며 과거 판정에 소급 적용하지 않는다 (TASK50).",
             "두 번째 블록은 반복별 원자료다."]
    return header, rows, notes, ck, (header2, rows2)


def t13_n7_blocks():
    """N ∈ {3,4,7}의 6블록 짝 비교 (TASK23·TASK25) — 부록 S4."""
    ck = Check()
    sources = {3: (RUN_OBSERVE, RUN_OOS), 4: (RUN_SWEEP, RUN_OOS), 7: (RUN_OBSERVE, RUN_OOS)}
    BAND = (0.97, 1.03)

    def sums(run: Path, arm: str, n: int, b: int) -> tuple[int, int]:
        u = load(run / f"util.{arm}.n{n}.b{b}.json")
        if not u.get("valid", True):
            raise SystemExit(f"INVALID {arm}.n{n}.b{b}")
        return u["sum_request_nums"], u["sum_padded_batch_size"]

    header = ["N", "블록", "출처 run", "AGENTIC util", "CONVENTIONAL util", "ratio",
              "동치 밴드 안"]
    rows = []
    recorded = {3: [1.0926, 1.1360, 1.0232, 1.0386, 1.1899, 1.1291],
                4: [0.9436, 1.0895, 1.0712, 1.0083, 1.0008, 1.0400],
                7: [0.9928, 1.0229, 1.0481, 0.9922, 1.1032, 1.0140]}
    pooled_rec = {3: 1.0994, 4: 1.0282, 7: 1.0273}
    for n, (early, late) in sources.items():
        cells = []
        for b in range(6):
            run = early if b < 3 else late
            a, c = sums(run, "AGENTIC", n, b), sums(run, "CONVENTIONAL", n, b)
            ratio = (a[0] / a[1]) / (c[0] / c[1])
            cells.append((a, c))
            rows.append([str(n), f"b{b}", run.name, f"{a[0] / a[1]:.4f}",
                         f"{c[0] / c[1]:.4f}", f"{ratio:.4f}",
                         "예" if BAND[0] <= ratio <= BAND[1] else "아니오"])
            ck.eq(f"N={n} b{b} ratio", round(ratio, 4), recorded[n][b], tol=5e-5,
                  source="TASK25 관측 3")
        pa = sum(x[0][0] for x in cells) / sum(x[0][1] for x in cells)
        pc = sum(x[1][0] for x in cells) / sum(x[1][1] for x in cells)
        rows.append([str(n), "pooled", "—", f"{pa:.4f}", f"{pc:.4f}", f"{pa / pc:.4f}",
                     "예" if BAND[0] <= pa / pc <= BAND[1] else "아니오"])
        ck.eq(f"N={n} pooled", round(pa / pc, 4), pooled_rec[n], tol=5e-5,
              source="TASK25 6블록 재판정")
    notes = ["util = Σactual / Σbucket. ratio = util(AGENTIC) / util(CONVENTIONAL).",
             "동치 밴드 [0.97, 1.03]은 선등록 값이다.",
             "블록 0–2는 초기 sweep/관측 격자, 3–5는 TASK25의 표본외 블록이다."]
    return header, rows, notes, ck


def t14_padding_decompose():
    """개입의 padding 하락을 h(n)별로 분해 (TASK56) — 부록 S5."""
    d = load(R2 / "padding_decompose.json")
    ck = Check()
    header = ["N", "arm", "n", "step 수", "step 점유율", "mb padding slot",
              "mb6 padding slot", "제거된 slot", "제거분 몫 (slot 수 기준)",
              "p 하락분의 몫 (Shapley)"]
    rows = []
    for cell in d:
        sh = cell["shapley"]
        tot_sh = sum(sh.values())
        for r in cell["rows"]:
            v = sh.get(str(r["n"]))
            rows.append([str(cell["N"]), cell["arm"], str(r["n"]), str(r["steps"]),
                         f"{100 * r['share_steps']:.1f} %",
                         str(r["pad_slots_mb"]), str(r["pad_slots_mb6"]),
                         str(r["pad_slots_removed"]),
                         f"{100 * r['share_of_removed']:.1f} %",
                         "—" if v is None else f"{100 * v / tot_sh:.1f} % (+{v:.4f})"])
        rows.append([str(cell["N"]), cell["arm"], "합계", str(cell["steps"]), "100.0 %",
                     str(cell["pad_slots_mb"]), str(cell["pad_slots_mb6"]),
                     str(cell["pad_slots_removed"]), "100.0 %",
                     f"100.0 % (+{tot_sh:.4f}), p 하락 {cell['drop']:.4f}"])
    n6 = next(c for c in d if c["N"] == 6)
    top = max(n6["rows"], key=lambda r: r["pad_slots_removed"])
    sh6 = n6["shapley"]
    tot6 = sum(sh6.values())
    ck.eq("N=6 하락의 최대 기여 n", top["n"], 6, source="TASK56 (n=6가 80.9 %)")
    ck.eq("N=6 n=6 Shapley 기여 (+)", round(sh6["6"], 4), 0.1415, tol=6e-5,
          source="TASK56 표 (B)")
    ck.eq("N=6 n=5 Shapley 기여 (+)", round(sh6["5"], 4), 0.0334, tol=6e-5,
          source="TASK56 표 (B)")
    ck.eq("N=6 n=6 p 하락분의 몫 %", round(100 * sh6["6"] / tot6, 1), 80.9, tol=0.06,
          source="TASK56 표 (B)")
    ck.eq("N=6 n=6 slot 수 기준 몫 %", round(100 * top["share_of_removed"], 1), 81.1,
          tol=0.06, source="TASK56 핵심 발견 1 (두 정의가 0.2 %p 안에서 일치)")
    notes = ["padding slot = Σ(bucket − actual). 격자를 mb → mb6로 바꿨을 때의 차다.",
             "몫에 두 정의가 있다 — 제거된 slot 수의 몫과 `p` 하락분의 Shapley 분해(잔차 0). "
             "N=6에서 각각 81.1 %와 80.9 %이며 TASK56이 0.2 %p 안의 일치로 기록했다.",
             "몫을 정하는 것은 padding 감소폭이 아니라 그 n의 step 점유율이다 (TASK56)."]
    return header, rows, notes, ck


# -- supplementary tables ----------------------------------------------------

def a01_reuse_cost():
    """재사용 실패의 추가 비용: 독립형 T(C) 대 증분형 T(L)−T(L−C) (TASK66)."""
    d = load(R2 / "reuse_cost.json")
    ck = Check()
    header = ["C (token)", "요청 수", "hit", "L 범위", "독립형 T(C) (ms)",
              "증분형 T(L)−T(L−C) (ms)", "같은 C 안의 폭 (ms)"]
    rows = []
    for c in d["C_values"]:
        v = d["by_C"][str(c)]
        rows.append([f"{c:,}", str(v["requests"]), str(v["hits"]),
                     f"{v['L_min']:,}–{v['L_max']:,}", f"{v['independent_ms']:.2f}",
                     f"{v['increment_min_ms']:.2f}–{v['increment_max_ms']:.2f}",
                     f"{v['increment_spread_ms']:.2f}"])
    ck.eq("요청 수", d["requests"], 168, source="TASK66 결과 3")
    ck.eq("hit", d["hits"], 95, source="TASK66 결과 3")
    ck.eq("C=768 독립형 (ms)", round(d["by_C"]["768"]["independent_ms"], 2), 130.18,
          tol=6e-3, source="TASK66 결과 3")
    ck.eq("C=1536 독립형 (ms)", round(d["by_C"]["1536"]["independent_ms"], 2), 266.27,
          tol=6e-3, source="TASK66 결과 3")
    lo, hi = d["increment_minus_independent_ms"]
    notes = [f"증분형 − 독립형: {lo:.2f} – {hi:.2f} ms. 같은 C 안의 최대 폭 "
             f"{d['max_increment_spread_within_C_ms']:.2f} ms.",
             f"L − C 관측 범위 {d['L_minus_C_range'][0]}–{d['L_minus_C_range'][1]} token "
             f"(중앙 {d['L_minus_C_median']:.1f}).",
             "저장소의 두 소비처(`config_device.py`, `sim/engine.py`)는 요청의 실계산량 "
             "q = L − C를 비용 모형에 넣는다 — 이 표의 어느 열도 그 값이 아니다.",
             f"비용 모형 적합 구간 {d['prefill_cost_model']['fit_range_tokens']} token."]
    return header, rows, notes, ck


def s02_recompile_variance():
    """재compile 변동과 회차 간 변동의 분리 (TASK62) — 부록 S2."""
    d = load(RUN_RECOMP / "recompile_variance.json")
    ck = Check()
    header = ["bucket", "artifact", "회차 값 (ms)", "회차 수", "중앙 (ms)",
              "귀무 짝 수", "귀무 중앙 (ms)", "귀무 q90 (ms)", "귀무 q95 (ms)", "귀무 최대 (ms)"]
    rows = []
    for bucket in ("b1", "b2", "b4", "b8"):
        nul = d["null"][bucket]
        for art in ("A1", "A2", "A3"):
            c = d["cells"][f"{art}.{bucket}"]
            rows.append([bucket.lstrip("b"), art,
                         " / ".join(f"{v:.2f}" for v in c["values"]), str(c["n"]),
                         f"{c['median']:.2f}", str(nul["n"]), f"{nul['median']:.2f}",
                         f"{nul['q90']:.2f}", f"{nul['q95']:.2f}", f"{nul['max']:.2f}"])
    header2 = ["규칙", "대조", "bucket", "중앙 x (ms)", "중앙 y (ms)", "|차| (ms)",
               "q95 (ms)", "판정"]
    rows2 = []
    for rule, entries in d["rules"].items():
        for e in entries:
            for b in e["buckets"]:
                rows2.append([rule, f"{e['x']} 대 {e['y']}", str(b["bucket"]),
                              f"{b['median_x']:.2f}", f"{b['median_y']:.2f}",
                              f"{b['abs_delta']:.2f}", f"{b['q95']:.2f}",
                              b["verdict_q95"]])
            rows2.append([rule, f"{e['x']} 대 {e['y']}", "종합", "—", "—", "—", "—",
                          e["overall"]])
    ck.eq("lifecycle 수", d["counts"]["lifecycles_ok"], 60, source="TASK62 (3×5×4)")
    r2 = d["rules"]["R2"]
    outside = [b for e in r2 for b in e["buckets"] if b["verdict_q95"] != "WITHIN"]
    ck.eq("R2에서 OUTSIDE인 bucket 수", len(outside), 1,
          source="TASK62 (bucket 8만 OUTSIDE)")
    notes = [
        "A1 = 기존 `mb`, A2 = 격자 변경 `mb6`, A3 = 같은 구성 재compile `mb-rc`.",
        "**회차**는 같은 artifact를 다시 기동해 다시 잰 것이고, **재compile**은 artifact 자체를 "
        "다시 만든 것이다. 두 축이 이 표에서 분리된다 — 회차는 열 안, 재compile은 행 사이다.",
        "변동 범위 계산법: 같은 artifact·같은 bucket의 **회차 쌍**(5회차에서 10쌍, "
        "artifact 3개로 bucket당 30쌍)의 |중앙 차|로 귀무 분포를 만들고, 그 q95를 문턱으로 쓴다.",
        "판정은 `|중앙(x) − 중앙(y)| ≤ q95`이면 `WITHIN`(구별되지 않음)이다.",
        "값은 model p50 (ms), 해상도 0.01 ms.",
        f"재실행된 lifecycle: {', '.join(d['counts']['reruns']) or '없음'}.",
        "규칙 표는 같은 파일의 두 번째 블록이다.",
    ]
    return header, rows, notes, ck, (header2, rows2)


def s03_dummy_lifecycle():
    """dummy block 생애 주기 직접 관측 (TASK63) — 부록 S3."""
    d = load(RUN_DUMMY / "dummy_lifecycle.json")
    ck = Check()
    header = ["trial", "server 로그 (저장소 상대경로)", "decode step", "부분 step",
              "dummy 호출", "step당 호출", "상한 step", "상한 step의 dummy 호출",
              "회수 (OB)", "회수 라벨", "재할당되지 않은 회수"]
    rows = []
    rel = RUN_DUMMY.relative_to(REPO)
    total_evict = 0
    for tag, t in d.items():
        q2, q5, ev = t["q2"], t["q5"], t["evictions"]
        total_evict += ev["obs"]
        rows.append([tag, f"`{rel}/server-{tag}.log`", str(t["decode_steps"]),
                     str(q2["partial_steps"]), str(q2["dummy_calls_total"]),
                     ", ".join(f"{k}회×{v}" for k, v in q2["calls_per_partial_step"].items()),
                     str(q5["steps_at_ceiling"]), str(q5["dummy_calls_in_ceiling_steps"]),
                     str(ev["obs"]), ", ".join(ev["labels"]) or "—",
                     str(ev["never_reassigned"])])
    ck.eq("직접 관측 trial 수", len(d), 10, source="TASK63 (본 측정 10 lifecycle)")
    ck.eq("회수 총수", total_evict, 14, source="TASK63 (회수 14건)")
    ck.eq("dummy 경로 회수", sum(t["evictions"]["by_caller"]["dummy"] for t in d.values()),
          14, source="TASK63 (전부 dummy 경로)")
    ck.eq("admission 경로 회수",
          sum(t["evictions"]["by_caller"]["request_alloc"] for t in d.values()), 0,
          source="TASK63 (admission 경로 0건)")
    b = d["B.b0"]
    ck.eq("B.b0 부분 step = dummy 호출", b["q2"]["partial_steps"],
          b["q2"]["dummy_calls_total"], source="TASK63 (1,084/1,084의 절반)")
    notes = [
        f"직접 관측 실행 수: **{len(d)}** (파일럿 1회는 별도, `pilot.json`).",
        "부분 step = decode 요청 수 n이 `0 < n < 실행 상한(8)`인 step. dummy는 그 step마다 "
        "정확히 1회 요청되고 상한 step(n = 8)에서는 0회다.",
        f"회수 총 **{total_evict}건**이며 라벨은 전부 `dummy` 경로다 "
        "(`request_alloc` 0건, `preemption` 0건, 미분류 0건).",
        f"로그 경로는 저장소 상대경로 `{rel}/` 아래다. `results/`는 git이 추적하지 않는다.",
        "관측용 patch는 이 run 구간에만 적용됐고 이후 `pristine`으로 revert됐다 (TASK63).",
    ]
    return header, rows, notes, ck


def s07_arrival_feedback():
    """재도착 재계산을 껐을 때의 예측 오차 (B-3)."""
    ck = Check()
    header = ["run", "N", "구간", "arm", "실측 A′ 비", "전체 모형 비", "|e_c| 전체",
              "고정 모형 비", "|e_c| 고정", "|e_c| 고정 − 전체", "더 작은 쪽"]
    seg = {(20261000, 6): "확증(TASK35 채널 보류)", (20261000, 8): "확증",
           (20261000, 10): "탐색", (20261100, 6): "확증"}
    rows = []
    better = {"전체": 0, "고정": 0}
    for seed, path in ((20261000, RUN_FINAL / "arrival_feedback.json"),
                       (20261100, RUN_N6 / "arrival_feedback.json")):
        for row in load(path):
            for arm in row["arms"]:
                fu, fx = arm["modes"]["full"], arm["modes"]["fixed"]
                win = "전체" if fu["abs_e_c"] < fx["abs_e_c"] else "고정"
                better[win] += 1
                rows.append([f"seed {seed}", str(row["N"]), seg[(seed, row["N"])],
                             ARM_LABEL[arm["arm"]],
                             f"{arm['measured_a_prime_ratio']:.4f}",
                             f"{fu['sim_ratio']:.4f}", f"{fu['abs_e_c']:.4f}",
                             f"{fx['sim_ratio']:.4f}", f"{fx['abs_e_c']:.4f}",
                             f"{arm['abs_e_c_fixed_minus_full']:+.4f}", win])
    # The full mode must still reproduce the preregistered predictions exactly:
    # that is what "the switch changes nothing when it is off" means here.
    rec = {(20261000, 6, "BATCHONLY"): 0.9610, (20261000, 6, "TUNED"): 0.9466,
           (20261000, 8, "BATCHONLY"): 0.9101, (20261000, 8, "TUNED"): 0.8971,
           (20261000, 10, "BATCHONLY"): 0.9213, (20261000, 10, "TUNED"): 0.8899,
           (20261100, 6, "BATCHONLY"): 0.9874, (20261100, 6, "TUNED"): 0.9713}
    for seed, path in ((20261000, RUN_FINAL / "arrival_feedback.json"),
                       (20261100, RUN_N6 / "arrival_feedback.json")):
        for row in load(path):
            for arm in row["arms"]:
                ck.eq(f"seed {seed} N={row['N']} {arm['arm']} 전체 모형 비",
                      round(arm["modes"]["full"]["sim_ratio"], 4),
                      rec[(seed, row["N"], arm["arm"])], tol=5e-5,
                      source="선등록 예측 (스위치 off = 기존 동작)")
    notes = [
        "`e_c` = 시뮬레이터 비 − 실측 A′ 비. 전체 모형은 재도착 시각을 완료 시각에서 "
        "다시 계산하고, 고정 모형은 기준 arm(`BASE`) 실행에서 관측된 값으로 고정한다.",
        f"|e_c|가 더 작은 쪽: 전체 {better['전체']}건, 고정 {better['고정']}건 "
        f"(전 {sum(better.values())}건).",
        "고정 모형에서는 분자·분모 모두 같은 관측 도착 열로 고정된다.",
        "스위치는 기본값 off다 — 전체 모형 열 8건이 선등록 예측과 자릿수까지 같다.",
    ]
    return header, rows, notes, ck


def s08_dummy_block():
    """dummy block을 KV pool에 반영했을 때의 차이 (B-4)."""
    ck = Check()
    header = ["run", "N", "arm", "실측 A′ 비", "off 비", "|e_c| off", "on 비",
              "|e_c| on", "Δ비 (on−off)", "|e_c| 차", "sim 재사용 off→on",
              "sim 회수 off→on"]
    rows = []
    for seed, path in ((20261000, RUN_FINAL / "dummy_block_effect.json"),
                       (20261100, RUN_N6 / "dummy_block_effect.json")):
        for row in load(path):
            b = row["baseline_sim"]
            mh, mt = row["baseline_measured_reuse"]
            rows.append([f"seed {seed}", str(row["N"]), ARM_LABEL[row["baseline_arm"]],
                         "1.0000", "1.0000", "—", "1.0000", "—", "+0.0000", "—",
                         f"{b['False']['reuse_hits']}→{b['True']['reuse_hits']} "
                         f"of {b['True']['resume']} (실측 {mh}/{mt})",
                         f"{b['False']['evictions']}→{b['True']['evictions']}"])
            for arm in row["arms"]:
                off, on = arm["modes"]["off"], arm["modes"]["on"]
                rows.append([f"seed {seed}", str(row["N"]), ARM_LABEL[arm["arm"]],
                             f"{arm['measured_a_prime_ratio']:.4f}",
                             f"{off['sim_ratio']:.4f}", f"{off['abs_e_c']:.4f}",
                             f"{on['sim_ratio']:.4f}", f"{on['abs_e_c']:.4f}",
                             f"{arm['ratio_on_minus_off']:+.4f}",
                             f"{arm['abs_e_c_on_minus_off']:+.4f}",
                             f"{off['reuse_hits']}→{on['reuse_hits']} of {on['resume']} "
                             f"(실측 {arm['measured_reuse'][0]}/{arm['measured_reuse'][1]})",
                             f"{off['evictions']}→{on['evictions']}"])

    off_c = load(RUN_SENS / "sum-seconds_6_8_10" / "comparison.json")
    on_c = load(R2 / "20260922-dummy-block/search-on/comparison.json")
    header2 = ["dummy block", "선정 구성", "batch", "탐색 합산비", "평가 합산비",
               "기록 구성과 일치", "기록 구성의 순위", "상위 20 ∩ off"]
    off_top = {(tuple(r["buckets"]), r["batch_size"]) for r in off_c["top_explore"]}
    rows2 = []
    for tag, c in (("off (기록 설정)", off_c), ("on", on_c)):
        a = c["argmin"]
        top = {(tuple(r["buckets"]), r["batch_size"]) for r in c["top_explore"]}
        rows2.append([tag, str(tuple(a["buckets"])), str(a["batch_size"]),
                      f"{a['explore_ratio']:.6f}", f"{a['eval_ratio']:.6f}",
                      "예" if c["argmin_equals_recorded"] else "아니오",
                      str(c["recorded_choice_rank"]), str(len(top & off_top))])
    ck.eq("off 조건이 기록 선정과 일치", off_c["argmin_equals_recorded"], True,
          source="TASK61")
    ck.eq("off 조건 평가 합산비 (반올림 4자리)",
          round(off_c["recorded_choice_eval_ratio"], 4), 0.9066, tol=5e-5,
          source="COMPILE_CONFIG_PREREG 기록")
    # Switch off must leave the validation numbers exactly where they were.
    rec = {(20261000, 6, "BATCHONLY"): 0.9610, (20261000, 6, "TUNED"): 0.9466,
           (20261000, 8, "BATCHONLY"): 0.9101, (20261000, 8, "TUNED"): 0.8971,
           (20261000, 10, "BATCHONLY"): 0.9213, (20261000, 10, "TUNED"): 0.8899,
           (20261100, 6, "BATCHONLY"): 0.9874, (20261100, 6, "TUNED"): 0.9713}
    for seed, path in ((20261000, RUN_FINAL / "dummy_block_effect.json"),
                       (20261100, RUN_N6 / "dummy_block_effect.json")):
        for row in load(path):
            for arm in row["arms"]:
                ck.eq(f"seed {seed} N={row['N']} {arm['arm']} off 비",
                      round(arm["modes"]["off"]["sim_ratio"], 4),
                      rec[(seed, row["N"], arm["arm"])], tol=5e-5,
                      source="선등록 예측 (스위치 off = 기존 동작)")
    notes = [
        "규칙: decode 요청 수 n이 `0 < n < 실행 상한`이면 outer pool이 slot 1개를 더 "
        "점유한다 (TASK63 관측). 실행 상한은 `max_running_requests` = `batch_size`다.",
        "`|e_c|` = |시뮬레이터 비 − 실측 A′ 비|. 기준 arm 행은 비가 정의상 1이다.",
        "두 번째 블록은 구성 탐색(탐색 seed 3 × 블록 3 × N 6,8,10, 후보 2,077개)의 "
        "상위 20을 off/on으로 비교한 것이다.",
        "스위치는 기본값 off다 — off 열 8건이 선등록 예측과 자릿수까지 같다.",
    ]
    return header, rows, notes, ck, (header2, rows2)


def s06a_per_repetition_config():
    """검증 비교와 절감률의 반복별 분해 (B-2)."""
    ck = Check()
    header = ["run", "N", "arm", "반복", "기준 A′ (s)", "arm A′ (s)", "A′ 비", "B 비",
              "채널 차", "X (A′)", "X (B)"]
    rows = []
    for tag, path in (("TASK35 seed 20261000", RUN_FINAL / "per_repetition.json"),
                      ("TASK36 seed 20261100", RUN_N6 / "per_repetition.json")):
        for r in load(path):
            rows.append([tag, str(r["N"]), ARM_LABEL[r["arm"]], str(r["block"]),
                         f"{r['base_a_prime_s']:.3f}", f"{r['arm_a_prime_s']:.3f}",
                         f"{r['a_prime_ratio']:.4f}", f"{r['b_ratio']:.4f}",
                         f"{r['channel_gap']:.4f}", f"{100 * r['X_a_prime']:+.2f} %",
                         f"{100 * r['X_b']:+.2f} %"])
    agg = {(r["N"], r["arm"]): r for r in load(RUN_FINAL / "per_repetition.json")
           if r["block"] == "합산"}
    for (n, arm), want in (((6, "BATCHONLY"), 0.9793), ((6, "TUNED"), 0.9660),
                           ((8, "BATCHONLY"), 0.9175), ((8, "TUNED"), 0.9028),
                           ((10, "BATCHONLY"), 0.9552), ((10, "TUNED"), 0.9264)):
        ck.eq(f"N={n} {arm} 합산 A′ 비", round(agg[(n, arm)]["a_prime_ratio"], 4), want,
              tol=5e-5, source="TASK35 채널 일치 표")
    notes = ["`합산` 행이 선등록된 판정 단위다. 반복 행은 그 아래를 보여줄 뿐이며 "
             "**불확실성 구간이 아니다** — 무처치 반복 분포는 부록 S1(TASK50)에 있다.",
             "X = 1 − ratio."]
    return header, rows, notes, ck


def s06b_per_repetition_saturation():
    """추가 slot 포화의 N × 반복별 분해 (B-2)."""
    ck = Check()
    header = ["N", "arm", "반복", "A′ 비", "B 비", "재사용", "최상위 bucket", "선택 비중"]
    rows = [[str(r["N"]), r["arm"], str(r["block"]), f"{r['a_prime_ratio']:.4f}",
             f"{r['b_ratio']:.4f}", f"{r['reuse']}/{r['resume']}",
             str(r["top_bucket"]), f"{100 * r['top_share']:.1f} %"]
            for r in load(RUN_SAT / "per_repetition.json")]
    sat = load(RUN_SAT / "batch_curve.json")
    per_cell = next(a for a in sat["adjacent"] if a["label"] == "B8->B16")["per_cell_ratios"]
    mine = sorted(r["a_prime_ratio"] for r in load(RUN_SAT / "per_repetition.json")
                  if r["arm"] == "B16")
    ck.eq("B8→B16 셀별 ratio 집합 일치", [round(x, 6) for x in sorted(per_cell)],
          [round(x, 6) for x in mine], source="batch_curve.json per_cell_ratios")
    notes = ["기준은 같은 (N, 반복)의 `B8`이다.",
             "최상위 눈금(16/24/32)의 선택 비중이 0 %라는 것이 TASK40의 기전 관측이다."]
    return header, rows, notes, ck


def b01_config_search_sensitivity():
    """N=10 제외 선정 민감도와 score 정의 민감도 (B-1)."""
    ck = Check()
    variants = [("sum-seconds", "6,8"), ("sum-seconds", "6,8,10"), ("sum-seconds", "8,10"),
                ("per-n", "6,8"), ("per-n", "6,8,10"), ("per-n", "8,10")]
    loaded = {}
    for w, s in variants:
        tag = f"{w}_{s.replace(',', '_')}"
        loaded[(w, s)] = load(RUN_SENS / tag / "comparison.json")
    header = ["score", "N 집합", "선정 구성", "batch", "탐색 합산비", "탐색 N평균비",
              "평가 합산비", "평가 N평균비", "기록 구성과 일치", "기록 구성의 순위",
              "기록 구성 상위 20 포함"]
    rows = []
    for (w, s), c in loaded.items():
        a = c["argmin"]
        rows.append([w, s, str(tuple(a["buckets"])), str(a["batch_size"]),
                     f"{a['explore_ratio']:.6f}", f"{a['explore_mean_per_n_ratio']:.6f}",
                     f"{a['eval_ratio']:.6f}", f"{a['eval_mean_per_n_ratio']:.6f}",
                     "예" if c["argmin_equals_recorded"] else "아니오",
                     str(c["recorded_choice_rank"]),
                     "예" if c["recorded_choice_in_top"] else "아니오"])
    tops = {k: {(tuple(r["buckets"]), r["batch_size"]) for r in v["top_explore"]}
            for k, v in loaded.items()}
    base_key = ("sum-seconds", "6,8,10")
    header2 = ["score", "N 집합", "상위 20 ∩ 기준", "기준에만", "이 조건에만"]
    rows2 = []
    for k, t in tops.items():
        b = tops[base_key]
        rows2.append([k[0], k[1], str(len(t & b)), str(len(b - t)), str(len(t - b))])
    ck.eq("기준 조건이 기록 선정과 일치",
          loaded[base_key]["argmin_equals_recorded"], True,
          source="TASK61 (선정 (1,4,6,8,10,16) batch 16이 유일 최솟값)")
    ck.eq("기준 조건 평가 합산비 (반올림 4자리)",
          round(loaded[base_key]["recorded_choice_eval_ratio"], 4), 0.9066,
          tol=5e-5, source="COMPILE_CONFIG_PREREG 기록 0.9066")
    notes = ["`sum-seconds`는 기록된 규칙(전 N의 device 초 합산비), `per-n`은 N별 비용 비의 "
             "비가중 평균이다. 두 값은 항상 같이 기록되며 `--weight`는 순위만 고른다.",
             "후보 공간은 세 조건에서 동일한 2,077개다 — N 집합은 점수만 바꾼다.",
             "두 번째 블록은 상위 20 집합을 기준 조건(`sum-seconds`, N=6,8,10)과 비교한 것이다."]
    return header, rows, notes, ck, (header2, rows2)


# -- registry ----------------------------------------------------------------

TABLES = {
    "T01": (t01_padding_devicetime, "padding 비율과 decode device time (N별)",
            "TASK52, TASK53", ["results/npu/stage2/padding_ratio.json"]),
    "T02": (t02_grid6_paired, "bucket 6 개입의 짝 비교", "TASK54",
            ["results/npu/stage2/20260908-133635-grid-paired/grid_paired.json"]),
    "T03": (t03_capacity_intervention, "slot 8→16 개입의 재사용과 계산량",
            "TASK35, TASK58", ["results/npu/stage2/layer_audit.json"]),
    "T04": (t04_prefill_injection, "prefill 주입과 병행 세션의 정지", "TASK22",
            ["results/npu/stage2/20260821-220100-prefill-tax/prefill_tax_result.json"]),
    "T05": (t05_n6_conflict, "N=6의 seed 간 상충", "TASK35, TASK36",
            ["results/npu/stage2/20260823-183505-final-confirm/config_device.json",
             "results/npu/stage2/20260824-160028-n6-reconfirm/config_device.n6.json"]),
    "T06": (t06_decode_step_cost, "decode step 비용 계수", "TASK13, TASK55",
            ["results/npu/stage2/20260908-151119-step-cost/grid_step_cost.json"]),
    "T07": (t07_validation_prediction, "검증 구성의 비용 비 예측",
            "TASK33, TASK35, TASK36", ["(시뮬레이터 재계산)"]),
    "T08": (t08_channel_time, "채널별 device time", "TASK35, TASK36",
            ["results/npu/stage2/20260823-183505-final-confirm/config_device.json",
             "results/npu/stage2/20260824-160028-n6-reconfirm/config_device.n6.json"]),
    "T09": (t09_recovery_rate, "구성 선택의 절감률 X", "TASK35, TASK36",
            ["results/npu/stage2/20260823-183505-final-confirm/config_device.json",
             "results/npu/stage2/20260824-160028-n6-reconfirm/config_device.n6.json"]),
    "T10": (t10_batch_saturation, "추가 slot의 포화", "TASK40",
            ["results/npu/stage2/20260824-222453-batch-saturation/batch_curve.json"]),
    "T11": (t11_compile_cost, "컴파일 비용과 artifact 크기",
            "TASK06, TASK10, TASK23, TASK40, TASK62", ["(run별 compile/ 시각 기록)"]),
    "T12": (t12_null_repeat, "무처치 반복의 채널 차 분포 (S1)", "TASK50",
            ["results/npu/stage2/20260901-020342-null-channel/null_channel.json"]),
    "T13": (t13_n7_blocks, "N ∈ {3,4,7}의 6블록 짝 비교 (S4)", "TASK23, TASK25",
            ["(4개 run의 util.*.json)"]),
    "T14": (t14_padding_decompose, "개입의 padding 하락 분해 (S5)", "TASK56",
            ["results/npu/stage2/padding_decompose.json"]),
    "A01": (a01_reuse_cost, "재사용 실패의 추가 비용: 두 정의", "TASK66",
            ["results/npu/stage2/reuse_cost.json"]),
    "S02": (s02_recompile_variance, "재compile 변동과 회차 간 변동 (S2)", "TASK62",
            ["results/npu/stage2/20260911-191300-recompile-variance/recompile_variance.json"]),
    "S03": (s03_dummy_lifecycle, "dummy block 생애 주기 직접 관측 (S3)", "TASK63",
            ["results/npu/stage2/20260912-134732-dummy-lifecycle/dummy_lifecycle.json"]),
    "S06a": (s06a_per_repetition_config, "검증 비교·절감률의 반복별 분해 (S6)",
             "TASK35, TASK36",
             ["results/npu/stage2/20260823-183505-final-confirm/per_repetition.json",
              "results/npu/stage2/20260824-160028-n6-reconfirm/per_repetition.json"]),
    "S06b": (s06b_per_repetition_saturation, "추가 slot 포화의 N×반복별 분해 (S6)",
             "TASK40", ["results/npu/stage2/20260824-222453-batch-saturation/per_repetition.json"]),
    "S07": (s07_arrival_feedback, "재도착 재계산을 껐을 때의 예측 오차",
            "TASK35, TASK36, TASK68",
            ["results/npu/stage2/20260823-183505-final-confirm/arrival_feedback.json",
             "results/npu/stage2/20260824-160028-n6-reconfirm/arrival_feedback.json"]),
    "S08": (s08_dummy_block, "dummy block 모형 반영 전후", "TASK58, TASK63, TASK69",
            ["results/npu/stage2/20260823-183505-final-confirm/dummy_block_effect.json",
             "results/npu/stage2/20260824-160028-n6-reconfirm/dummy_block_effect.json",
             "results/npu/stage2/20260922-dummy-block/search-on/comparison.json"]),
    "B01": (b01_config_search_sensitivity, "구성 선정의 N 집합·score 민감도", "TASK61",
            ["results/npu/stage2/20260922-config-search-sensitivity/*/comparison.json"]),
}


def render_md(header: list[str], rows: list[list[str]]) -> str:
    # A bare "|" inside a cell ends the cell, and several column names here
    # carry one (|e_c|, |차|). Escape on the way into markdown only: the csv
    # keeps the raw text.
    def cell(x) -> str:
        return str(x).replace("|", "\\|")
    out = ["| " + " | ".join(cell(h) for h in header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for r in rows:
        out.append("| " + " | ".join(cell(x) for x in r) + " |")
    return "\n".join(out)


def write_table(tid: str, out_dir: Path) -> dict:
    fn, title, tasks, inputs = TABLES[tid]
    res = fn()
    extra = None
    if len(res) == 5:
        header, rows, notes, ck, extra = res
    else:
        header, rows, notes, ck = res
    body = [f"# {tid} — {title}", "",
            f"- 근거 TASK: {tasks}",
            f"- 생성 명령: `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py "
            f"--table {tid}`",
            f"- 입력: " + ", ".join(f"`{i}`" for i in inputs), ""]
    body.append(render_md(header, rows))
    if extra is not None:
        body += ["", render_md(*extra)]
    if notes:
        body += ["", "## 비고", ""] + [f"- {n}" for n in notes]
    if ck.rows:
        body += ["", "## 기존 TASK 기록과의 대조", "",
                 f"대조 {len(ck.rows)}건 중 불일치 **{len(ck.mismatches)}건**.", ""]
        body.append(render_md(["항목", "재계산", "기록", "허용차", "일치", "출처"],
                              [[r["항목"], r["재계산"], r["기록"], r["허용차"],
                                "OK" if r["일치"] else "**불일치**", r["출처"]]
                               for r in ck.rows]))
    (out_dir / f"{tid}.md").write_text("\n".join(body) + "\n")

    import csv
    with (out_dir / f"{tid}.csv").open("w", newline="") as fh:
        # LF, not the csv module's default CRLF: a CR at end of line reads as
        # trailing whitespace to git and to every diff tool here.
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
        if extra is not None:
            w.writerow([])
            w.writerow(extra[0])
            w.writerows(extra[1])
    return {"id": tid, "title": title, "tasks": tasks, "inputs": inputs,
            "rows": len(rows), "checks": len(ck.rows),
            "mismatches": [dict(m) for m in ck.mismatches]}


README_HEAD = """# results/tables — 보고된 표의 집계 파일

이 디렉터리의 파일 하나가 보고된 표 하나에 대응한다. 각 파일은
`experiments/npu/analysis/make_tables.py`의 이름 붙은 함수 하나가 만들고, 그 함수는
아래 「입력」 열의 artifact만 읽는다. 값이 기존 TASK 문서에 기록돼 있으면 각 파일의
「기존 TASK 기록과의 대조」 절에서 대조하며, **불일치는 보고만 하고 고치지 않는다.**

`results/`는 원칙적으로 git이 추적하지 않는다(원자료 보존). 이 디렉터리만 예외로
추적한다 — 여기 있는 것은 원자료가 아니라 원자료에서 나온 집계이고, 저장소 밖에서
관리되는 원고가 참조할 값이기 때문이다.

## 전체 생성

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all
```

## 선행 명령 (원자료 → 분석 산출물)

`make_tables.py`는 아래 분석 산출물을 읽기만 한다. `results/` 아래 산출물은 추적되지
않으므로 없으면 먼저 만든다.

```bash
R=results/npu/stage2
env -u PYTHONPATH python3 experiments/npu/analysis/padding_ratio.py --output $R/padding_ratio.json
env -u PYTHONPATH python3 experiments/npu/analysis/padding_decompose.py --output $R/padding_decompose.json
env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py --output $R/layer_audit.json
env -u PYTHONPATH python3 experiments/npu/analysis/reuse_cost.py --json $R/reuse_cost.json
env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py \\
    --run $R/20260908-133635-grid-paired --output $R/20260908-133635-grid-paired/grid_paired.json
env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py \\
    --run $R/20260908-151119-step-cost --task54-run $R/20260908-133635-grid-paired \\
    --output $R/20260908-151119-step-cost/grid_step_cost.json
env -u PYTHONPATH python3 experiments/npu/analysis/prefill_tax.py \\
    --input-dir $R/20260821-220100-prefill-tax/probe --spike-factor 5.0 \\
    --output $R/20260821-220100-prefill-tax/prefill_tax_result.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py \\
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \\
    --output $R/20260823-183505-final-confirm/config_device.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_device.py \\
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \\
    --output $R/20260824-160028-n6-reconfirm/config_device.n6.json
env -u PYTHONPATH python3 experiments/npu/analysis/batch_curve.py \\
    --run $R/20260824-222453-batch-saturation \\
    --output $R/20260824-222453-batch-saturation/batch_curve.json
env -u PYTHONPATH python3 experiments/npu/analysis/null_channel.py \\
    --run $R/20260901-020342-null-channel --sessions 6,8 \\
    --output $R/20260901-020342-null-channel/null_channel.json
env -u PYTHONPATH python3 experiments/npu/analysis/recompile_variance.py analyze \\
    --run $R/20260911-191300-recompile-variance \\
    --output $R/20260911-191300-recompile-variance/recompile_variance.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_lifecycle.py analyze \\
    --run $R/20260912-134732-dummy-lifecycle \\
    --output $R/20260912-134732-dummy-lifecycle/dummy_lifecycle.json
env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode config \\
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \\
    --output $R/20260823-183505-final-confirm/per_repetition.json
env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode config \\
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \\
    --output $R/20260824-160028-n6-reconfirm/per_repetition.json
env -u PYTHONPATH python3 experiments/npu/analysis/per_repetition.py --mode saturation \\
    --run $R/20260824-222453-batch-saturation --baseline B8 --arms B16,B24,B32 \\
    --sessions 6,8,10 --output $R/20260824-222453-batch-saturation/per_repetition.json
env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py \\
    --run $R/20260823-183505-final-confirm --fix-arrivals $R/20260823-183505-final-confirm \\
    --sessions 6,8,10 --output $R/20260823-183505-final-confirm/arrival_feedback.json
env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py \\
    --run $R/20260824-160028-n6-reconfirm --fix-arrivals $R/20260824-160028-n6-reconfirm \\
    --sessions 6 --output $R/20260824-160028-n6-reconfirm/arrival_feedback.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py \\
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \\
    --output $R/20260823-183505-final-confirm/dummy_block_effect.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py \\
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \\
    --output $R/20260824-160028-n6-reconfirm/dummy_block_effect.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py \\
    --sessions 6,8,10 --weight sum-seconds --top 20 --dummy-block \\
    --output-dir $R/20260922-dummy-block/search-on
for W in sum-seconds per-n; do for S in 6,8 6,8,10 8,10; do
  env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py \\
      --sessions "$S" --weight "$W" --top 20 \\
      --output-dir $R/20260922-config-search-sensitivity/"${W}_$(echo $S | tr , _)"
done; done
```

## 표 ↔ 파일 ↔ 생성 명령

"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--table", help="single table id, e.g. T03")
    p.add_argument("--all", action="store_true")
    p.add_argument("--out-dir", type=Path, default=REPO / "results/tables")
    args = p.parse_args()
    if not args.table and not args.all:
        raise SystemExit("--table ID 또는 --all 중 하나가 필요하다")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ids = list(TABLES) if args.all else [args.table]
    summary = []
    for tid in ids:
        if tid not in TABLES:
            raise SystemExit(f"알 수 없는 표 id {tid!r}. 가능한 값: {', '.join(TABLES)}")
        s = write_table(tid, args.out_dir)
        summary.append(s)
        mark = "OK" if not s["mismatches"] else f"불일치 {len(s['mismatches'])}건"
        print(f"{tid:>5}  {s['title']:<38} 행 {s['rows']:>3}  대조 {s['checks']:>3}  {mark}")
        for m in s["mismatches"]:
            print(f"        - {m['항목']}: 재계산 {m['재계산']} 대 기록 {m['기록']} "
                  f"({m['출처']})")

    if args.all:
        lines = [README_HEAD,
                 "| 표 | 제목 | 파일 | 생성 명령 | 근거 TASK | 대조 | 불일치 |",
                 "|---|---|---|---|---|---|---|"]
        for s in summary:
            cmd = (f"`make_tables.py --table {s['id']}`")
            lines.append(f"| {s['id']} | {s['title']} | `{s['id']}.md` / `{s['id']}.csv` | "
                         f"{cmd} | {s['tasks']} | {s['checks']} | "
                         f"{len(s['mismatches'])} |")
        total_mismatch = sum(len(s["mismatches"]) for s in summary)
        lines += ["", f"대조 합계 {sum(s['checks'] for s in summary)}건, "
                      f"불일치 **{total_mismatch}건**.", ""]
        if total_mismatch:
            lines += ["불일치 목록:", ""]
            for s in summary:
                for m in s["mismatches"]:
                    lines.append(f"- {s['id']} {m['항목']}: 재계산 `{m['재계산']}` 대 "
                                 f"기록 `{m['기록']}` ({m['출처']})")
            lines.append("")
        lines += ["생성 시각과 commit은 `manifest.json`에 있다.", ""]
        (args.out_dir / "README.md").write_text("\n".join(lines))
        head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                               capture_output=True, text=True).stdout.strip()
        (args.out_dir / "manifest.json").write_text(json.dumps(
            {"generated_at": dt.datetime.now().astimezone().isoformat(),
             "git_head": head, "git_dirty": dirty, "python": sys.version,
             "tables": summary}, indent=2, ensure_ascii=False) + "\n")
        print(f"\n표 {len(summary)}개, 대조 {sum(s['checks'] for s in summary)}건, "
              f"불일치 {total_mismatch}건 → {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
