#!/usr/bin/env python3
"""Generate the eight paper figures as SVG.

Every data table below carries the TASK and the artifact path it came from;
those same annotations are written to SOURCES.md so a reader can walk from a
figure back to raw evidence. Numbers that come from a *model* rather than a
measurement are marked in the figure itself, because this project's whole
record-keeping discipline turns on not letting the two blur.

    env -u PYTHONPATH python3 paper/figures/make_figures.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from svgplot import Axes, PALETTE  # noqa: E402

REPO = HERE.parents[1]
C = PALETTE


# --------------------------------------------------------------------------
# ① reuse cliff and the LRU ablation
# --------------------------------------------------------------------------
def fig1() -> None:
    ax = Axes(width=680, height=452, bottom=112, xlim=(0, 68), ylim=(-0.18, 1.35))
    # measured: layer-2 FIFO, 2,000-token requests (TASK14 / TASK15, 12/12)
    ax.hspan(-0.18, 1.35, color=C["bad"], opacity=0.0)
    # false-positive region: layer 1 still reports hits while layer 2 is gone
    left, right = ax.px(7), ax.px(33)
    ax.add(f'<rect x="{left:.1f}" y="{ax.py(1.02):.1f}" width="{right - left:.1f}" '
           f'height="{ax.py(0.0) - ax.py(1.02):.1f}" fill="{C["bad"]}" fill-opacity="0.10"/>')
    ax.text((7 + 33) / 2, 0.52, "metric은 hit이라 하고", size=11.5, fill=C["bad"])
    ax.text((7 + 33) / 2, 0.40, "device는 재계산한다", size=11.5, fill=C["bad"], weight="bold")

    def step(thr, color, width=2.4, dash=None):
        ax.line([(0, 1), (thr, 1), (thr, 0), (68, 0)], color=color, width=width, dash=dash)

    step(7, C["base"], 3.0)                       # measured layer 2, FIFO
    step(33, C["muted"], 2.0, dash="6 4")         # layer-1 metric
    for thr, lab, col in ((16, "2,000 tok", C["arm2"]),
                          (31, "1,000 tok", C["arm3"]),
                          (61, "500 tok", C["accent"])):
        step(thr, col, 1.8, dash="3 3")
        ax.text(thr, 1.08, lab, size=10.5, fill=col)

    ax.vline(7, color=C["base"], dash="2 2")
    ax.text(7, 1.22, "B = 7", size=12, fill=C["base"], weight="bold")
    ax.frame(xticks=[0, 7, 16, 33, 61], yticks=[0, 1],
             yfmt=lambda v: "생존" if v else "소멸",
             xlabel="gap 중 도착한 배경 요청 수 B",
             title="① 재사용 절벽 — 문턱은 token 총량이 아니라 요청 개수다",
             subtitle="층 2 = outer 8 slot × 8,192 token, FIFO. 2,000 token 요청, 12/12 재현 (TASK14·TASK15)")
    ax.legend([("실측 · 층 2 실제 재사용 (FIFO 8 slot)", C["base"], "line"),
               ("`prefix_cache_hits_total` (층 1, LRU 512)", C["muted"], "line"),
               ("절제(모형): LRU·block 단위 회수 (요청 크기별)", C["arm2"], "line")],
              x=ax.x0 + 4, y=ax.y0 + 44)
    ax.save(HERE / "fig1_survival_cliff.svg")


# --------------------------------------------------------------------------
# ② N-ratio curve and the grid intervention
# --------------------------------------------------------------------------
MEASURED_GRID = [(3, 1.0820), (4, 1.0414), (5, 1.1336), (6, 1.1504),
                 (7, 1.0220), (8, 0.9205), (10, 0.9103), (12, 0.9192), (16, 0.9944)]
INTERVENED = [(6, 0.9717), (8, 0.9508)]


def fig2() -> None:
    ax = Axes(width=680, height=400, xlim=(2, 17), ylim=(0.88, 1.19))
    ax.hspan(0.98, 1.02, color=C["muted"], opacity=0.18)
    ax.hline(1.0, color=C["ink"], dash="4 3")
    ax.line(MEASURED_GRID, color=C["base"], width=2.6)
    for n, v in MEASURED_GRID:
        ax.marker(n, v, color=C["base"], r=4.5)
    ax.line([(2, 1.0), (17, 1.0)], color=C["ok"], width=2.0, dash="7 4")
    ax.text(14.2, 1.006, "연속 격자 → 1.0000 (절제, 모형)", size=11, fill=C["ok"], anchor="end")
    for n, v in INTERVENED:
        ax.marker(n, v, color=C["arm3"], r=5.5, shape="s")
    ax.line(INTERVENED, color=C["arm3"], width=2.2, dash="5 3")
    # the intervention arrow at N=6
    ax.line([(6, 1.1504), (6, 0.9717)], color=C["arm3"], width=1.6, dash="3 3")
    ax.text(6.35, 1.065, "격자에 bucket 6만 추가", size=11, fill=C["arm3"], anchor="start")
    ax.text(6.35, 1.045, "(재compile 개입)", size=11, fill=C["arm3"], anchor="start")
    ax.text(2.4, 1.17, "1 위 = gap이 오히려 이롭다 (역전)", size=11, fill=C["muted"], anchor="start")
    ax.frame(xticks=[3, 4, 5, 6, 7, 8, 10, 12, 16],
             yticks=[0.90, 0.95, 1.00, 1.05, 1.10, 1.15],
             yfmt=lambda v: f"{v:.2f}",
             xlabel="동시 세션 수 N   (max_num_seqs = 8)",
             ylabel="pooled utilization ratio (AGENTIC / CONVENTIONAL)",
             title="② 격자 정렬이 gap 효과의 부호를 정한다 — 개입으로 확정",
             subtitle="워크로드·seed·모델·slot 수를 고정하고 격자만 바꿨다 (TASK20·23·24·29)")
    ax.legend([("측정 격자 (1,2,4,8)", C["base"], "o"),
               ("개입 격자 (1,2,4,6,8)", C["arm3"], "s"),
               ("동치 밴드 [0.98, 1.02]", C["muted"], "box")],
              x=ax.x0 + 14, y=ax.y1 + 24)
    ax.save(HERE / "fig2_grid_alignment.svg")


# --------------------------------------------------------------------------
# ③ prefill serialisation and cost model v2
# --------------------------------------------------------------------------
V1V2 = [  # N, arm, v1, v2   (TASK22 사후 대조)
    (4, "AGENTIC", 0.8553, 0.9897), (4, "CONVENTIONAL", 0.8118, 1.0387),
    (6, "AGENTIC", 0.7911, 0.9730), (6, "CONVENTIONAL", 0.7839, 1.0163),
    (8, "AGENTIC", 0.7223, 0.9909), (8, "CONVENTIONAL", 0.6499, 0.9946),
    (10, "AGENTIC", 0.6610, 1.0059), (10, "CONVENTIONAL", 0.5931, 0.9975),
    (12, "AGENTIC", 0.5986, 1.0215), (12, "CONVENTIONAL", 0.5698, 0.9794),
    (16, "AGENTIC", 0.5693, 0.9785), (16, "CONVENTIONAL", 0.5645, 0.9969),
]


def fig3() -> None:
    ax = Axes(width=680, height=400, xlim=(3, 17.5), ylim=(0.52, 1.10))
    ax.hline(1.0, color=C["ink"], dash="4 3")
    ax.hspan(0.96, 1.04, color=C["ok"], opacity=0.13)
    for series, color, shape, dx in (("AGENTIC", C["arm3"], "o", -0.18),
                                     ("CONVENTIONAL", C["arm2"], "^", 0.18)):
        v1 = [(n + dx, a) for n, s, a, _ in V1V2 if s == series]
        v2 = [(n + dx, b) for n, s, _, b in V1V2 if s == series]
        ax.line(v1, color=color, width=1.6, dash="4 3", opacity=0.55)
        ax.line(v2, color=color, width=2.4)
        for x, y in v1:
            ax.marker(x, y, color=color, r=4, shape=shape, fill="#ffffff")
        for x, y in v2:
            ax.marker(x, y, color=color, r=4, shape=shape)
    ax.text(4.2, 0.575, "v1 = decode 항만", size=11.5, fill=C["muted"], anchor="start")
    ax.text(4.2, 1.065, "v2 = decode + prefill 직렬화 항", size=11.5, fill=C["ok"],
            anchor="start", weight="bold")
    ax.frame(xticks=[4, 6, 8, 10, 12, 16], yticks=[0.6, 0.7, 0.8, 0.9, 1.0, 1.1],
             yfmt=lambda v: f"{v:.1f}",
             xlabel="동시 세션 수 N",
             ylabel="예측 ITL 합 / 실측 ITL 합",
             title="③ prefill은 시스템 비용이다 — 그 항을 넣으면 N 의존 편향이 사라진다",
             subtitle="스파이크/prefill = 1.012–1.140 (9/9 run). v1 0.565–0.855 → v2 0.973–1.039 (TASK22)")
    ax.legend([("AGENTIC", C["arm3"], "o"), ("CONVENTIONAL", C["arm2"], "^"),
               ("속 빈 표식 = v1, 채운 표식 = v2", C["muted"], "line")],
              x=ax.x0 + 300, y=ax.y1 + 24)
    ax.save(HERE / "fig3_prefill_tax.svg")


# --------------------------------------------------------------------------
# ④ simulator validation scatter
# --------------------------------------------------------------------------
def _task36_pairs():
    """Read the TASK36 measurement if it is on disk; fall back to the values
    recorded in TASK36.md so the figure builds on a clean checkout too."""
    runs = sorted((REPO / "results/npu/stage2").glob("*-n6-reconfirm/config_device.n6.json"))
    pred = {"BATCHONLY": 0.9874, "TUNED": 0.9713}
    if runs:
        d = json.loads(runs[-1].read_text())[0]
        return [(pred[a["arm"]], a["a_prime_ratio"]) for a in d["arms"]]
    return [(0.9874, 0.9941), (0.9713, 0.9789)]


SIM_INSAMPLE = [(1.0852, 1.0820), (1.0409, 1.0414), (1.1345, 1.1336), (1.1523, 1.1504),
                (1.0171, 1.0220), (0.9211, 0.9205), (0.9065, 0.9103), (0.9395, 0.9192),
                (0.9807, 0.9944), (0.9687, 0.9717), (0.9474, 0.9508)]
SIM_OOS = [(1.1145, 1.1123), (1.0161, 1.0166), (1.0362, 1.0322)]
SIM_DEVICE = [(1.0554, 1.0732), (1.0332, 1.0541)]
SIM_CONFIG = [(0.9610, 0.9793), (0.9466, 0.9660), (0.9101, 0.9175), (0.8971, 0.9028)]


def fig4() -> None:
    ax = Axes(width=900, height=500, left=78, right=316, xlim=(0.86, 1.18), ylim=(0.86, 1.18))
    lo, hi = 0.86, 1.18
    for d, op in ((0.03, 0.16), (0.01, 0.0)):
        ax.add(f'<polygon points="{ax.px(lo):.1f},{ax.py(lo + d):.1f} '
               f'{ax.px(hi - d):.1f},{ax.py(hi):.1f} {ax.px(hi):.1f},{ax.py(hi):.1f} '
               f'{ax.px(hi):.1f},{ax.py(hi - d):.1f} {ax.px(lo + d):.1f},{ax.py(lo):.1f} '
               f'{ax.px(lo):.1f},{ax.py(lo):.1f}" fill="{C["ok"]}" fill-opacity="{op}"/>')
    ax.line([(lo, lo), (hi, hi)], color=C["ink"], width=1.4, dash="4 3")
    for pts, color, shape, _lab in (
            (SIM_INSAMPLE, C["muted"], "o", "in-sample"),
            (SIM_OOS, C["arm2"], "s", "out-of-sample"),
            (SIM_DEVICE, C["accent"], "^", "device + 정책 개입"),
            (SIM_CONFIG, C["arm3"], "o", "device + compile 구성"),
            (_task36_pairs(), C["bad"], "s", "TASK36 (N=6 재확증)")):
        for x, y in pts:
            ax.marker(x, y, color=color, r=5, shape=shape)
    ax.text(1.155, 0.878, "±0.03 밴드", size=11, fill=C["ok"], anchor="end")
    ax.frame(xticks=[0.90, 0.95, 1.00, 1.05, 1.10, 1.15],
             yticks=[0.90, 0.95, 1.00, 1.05, 1.10, 1.15],
             xfmt=lambda v: f"{v:.2f}", yfmt=lambda v: f"{v:.2f}",
             xlabel="시뮬레이터 예측 ratio (보정 파라미터 0개)",
             ylabel="실측 ratio",
             title="④ 무보정 시뮬레이터의 예측력",
             subtitle="선등록된 점(파랑·주황·빨강)은 전부 측정 전에 commit됐다")
    ax.legend([("in-sample 재현 (TASK24, 11점)", C["muted"], "o"),
               ("out-of-sample 선등록 (TASK25, 3점)", C["arm2"], "s"),
               ("device + 정책 개입 (TASK28, 2점)", C["accent"], "^"),
               ("device + compile 구성 (TASK35, 4점)", C["arm3"], "o"),
               ("N=6 재확증 (TASK36, 2점)", C["bad"], "s")],
              x=ax.x1 + 22, y=ax.y1 + 150)
    ax.save(HERE / "fig4_simulator_validation.svg")


# --------------------------------------------------------------------------
# ⑤ headroom decomposition — coordination is most of it
# --------------------------------------------------------------------------
DECOMP = [  # eps, N, (a), (b), (c), (d), (e)
    (1, 6, 2.00, 0.12, 0.00, 0.40, 0.54), (1, 8, 6.99, -0.31, -0.06, -0.49, 2.19),
    (1, 10, 4.48, -1.82, 0.12, -0.19, 2.23), (2, 6, 1.96, -0.33, 0.09, 1.16, 0.78),
    (2, 8, 8.87, 0.98, -0.71, 0.59, 4.54), (2, 10, 6.24, -1.53, 0.14, -0.33, 2.79),
    (5, 6, 4.64, 1.11, 0.09, 1.16, 2.02), (5, 8, 7.42, 0.98, -0.50, 0.59, 3.00),
    (5, 10, 8.78, -1.86, 0.14, 0.49, 2.58),
]


def fig5() -> None:
    ax = Axes(width=700, height=448, bottom=76, xlim=(-0.7, 8.7), ylim=(-2.4, 9.6))
    ax.hline(0.0, color=C["ink"], dash=None, width=1.2)
    for i, (eps, n, a, b, c, d, e) in enumerate(DECOMP):
        ax.bar(i, e, w=0.62, color=C["arm2"], y_base=0.0, opacity=0.9)
        ax.bar(i, a, w=0.62, color=C["arm3"], y_base=e, opacity=0.85)
        for v, col, sh in ((b, C["accent"], "o"), (c, C["ok"], "^"), (d, C["ink"], "x")):
            ax.marker(i, v, color=col, r=4, shape=sh)
        ax.text(i, a + 0.42, f"{100 * (a - e) / a:.0f} %", size=10.5, fill=C["arm3"], weight="bold")
    ax.frame(xticks=list(range(9)), yticks=[-2, 0, 2, 4, 6, 8],
             xtick_labels=[f"ε={e}\nN={n}" for e, n, *_ in DECOMP],
             yfmt=lambda v: f"{v:g} %",
             ylabel="device time 절감 (%)",
             title="⑤ headroom의 절반 이상은 조율의 몫이고 지식으로 살 수 없다",
             subtitle="막대 위 숫자 = 조율의 비중 (a−e)/a. 중앙 60 %, 범위 49–73 %. 현실 tool latency 워크로드 (TASK33)")
    ax.legend([("(e) 전지적 지식 · 세션별 독립 결정", C["arm2"], "box"),
               ("(a)−(e) 조율의 몫 — 어떤 per-session 정책도 닿을 수 없다", C["arm3"], "box"),
               ("(b) 반환 시각만", C["accent"], "o"),
               ("(c) 생성 길이만", C["ok"], "^"),
               ("(d) 둘 다", C["ink"], "o")],
              x=ax.x0 + 232, y=ax.y1 + 22)
    ax.text(ax.x0 + 232, ax.y0 - 12, "탐색 seed에서 +4.32 % → 평가 seed에서 −0.14 %:",
            size=11, anchor="start", fill=C["bad"], data=False)
    ax.text(ax.x0 + 232, ax.y0 + 2, "자유 파라미터 2개·20조합 탐색이 만든 허구 이득",
            size=11, anchor="start", fill=C["bad"], data=False, weight="bold")
    ax.save(HERE / "fig5_headroom_decomposition.svg")


# --------------------------------------------------------------------------
# ⑥ predictor error against the accuracy threshold sigma*
# --------------------------------------------------------------------------
PRED_ERR = [("Read", 0.459, 17196), ("apply_patch", 1.501, 8785), ("TaskUpdate", 1.544, 2402),
            ("exec", 3.319, 12726), ("Bash", 16.052, None), ("write_stdin", 17.847, None)]
AGG = [("B(δ) — 논문 그대로", 10.196), ("μ̂ — 점추정", 10.185)]


def fig6() -> None:
    lg = lambda v: math.log10(v)  # noqa: E731
    ax = Axes(width=700, height=420, left=132, bottom=92,
              xlim=(-0.8, 7.8), ylim=(lg(0.25), lg(45)))
    ax.hspan(lg(1.056), lg(1.823), color=C["ok"], opacity=0.22)
    ax.text(7.6, lg(1.40), "σ* = 1.06–1.82 s", size=11.5, fill=C["ok"], anchor="end")
    labels = []
    for i, (name, std, _) in enumerate(PRED_ERR):
        ok = std <= 1.823
        ax.bar(i, lg(std), w=0.6, color=C["ok"] if ok else C["bad"],
               y_base=lg(0.25), opacity=0.85)
        ax.text(i, lg(std) + 0.045, f"{std:.2f}", size=10.5,
                fill=C["ok"] if ok else C["bad"])
        labels.append(name)
    for j, (name, std) in enumerate(AGG):
        i = len(PRED_ERR) + j
        ax.bar(i, lg(std), w=0.6, color=C["ink"], y_base=lg(0.25), opacity=0.9)
        ax.text(i, lg(std) + 0.045, f"{std:.2f}", size=10.5, fill=C["ink"], weight="bold")
        labels.append(name)
    ax.frame(xticks=list(range(len(labels))), xtick_labels=labels,
             yticks=[lg(v) for v in (0.3, 1, 3, 10, 30)],
             yfmt=lambda v: f"{10 ** v:g}",
             ylabel="수렴 후 예측 오차 std (s, 로그 축)",
             xtick_rotate=-30,
             title="⑥ 예측기는 문턱을 5.6–9.7배 초과하고, 표본을 늘려도 줄지 않는다",
             subtitle="표본 10 → 100,000에서 std 8.4 → 10.5 s. 상한도 점추정도 같은 벽에 부딪힌다 (TASK32)")
    ax.text(ax.x0 + 8, ax.y0 + 74,
            "『Bash』가 27 ms일지 300 s일지는 명령이 정하고, 도구 이름은 그것을 담지 않는다",
            size=11.5, anchor="start", fill=C["muted"], data=False)
    ax.save(HERE / "fig6_predictor_error.svg")


# --------------------------------------------------------------------------
# ⑦ compile cost model, five observations
# --------------------------------------------------------------------------
COMPILE = [  # buckets, compiled models, wall clock s, artifact GiB, TASK
    (1, 2, 165.0, 9.083, "TASK06"), (4, 5, 349.0, 11.501, "TASK10"),
    (5, 6, 416.0, 12.306, "TASK23"), (6, 7, 480.0, 13.202, "TASK34"),
    (5, 6, 407.0, 12.378, "TASK35"),
]


def fig7() -> None:
    ax = Axes(width=680, height=400, xlim=(1.4, 7.7), ylim=(120, 540))
    ax.line([(1.4, 42.3 + 61.33 * 1.4), (7.7, 42.3 + 61.33 * 7.7)],
            color=C["muted"], width=2.2, dash="6 4")
    ax.text(6.9, 42.3 + 61.33 * 6.9 - 34, "42.3 + 61.33 × compiled model 수",
            size=11.5, fill=C["muted"], anchor="end")
    for buckets, models, t, gib, task in COMPILE:
        first = task in ("TASK06", "TASK10")
        ax.marker(models, t, color=C["base"] if first else C["arm3"], r=5.5,
                  shape="s" if first else "o")
        ax.text(models, t + 22, f"{task}", size=10, fill=C["muted"])
        ax.text(models, t - 30, f"{gib:.2f} GiB", size=10, fill=C["ink"])
    ax.text(6.05, 470, "같은 bucket 수의 두 점 → 재현 오차 시간 2.2 %, 크기 0.6 %",
            size=11, fill=C["arm3"], anchor="end")
    ax.frame(xticks=[2, 5, 6, 7], yticks=[150, 250, 350, 450, 530],
             xlabel="compiled model 수 (decoder bucket 수 + prefill graph 1)",
             ylabel="compile wall-clock (s)",
             title="⑦ 재compile은 7분이다 — 두 점으로 세운 모형이 다섯 번째 점에서도 맞는다",
             subtitle="Qwen3-4B, max_seq_len 8192, num_devices 4. 마지막 점 오차 시간 −0.7 %, 크기 +0.6 %")
    ax.legend([("모형을 세운 관측점 (TASK06·TASK10)", C["base"], "s"),
               ("모형을 시험한 관측점 (TASK23·TASK34·TASK35)", C["arm3"], "o")],
              x=ax.x0 + 14, y=ax.y1 + 24)
    ax.save(HERE / "fig7_compile_cost.svg")


# --------------------------------------------------------------------------
# ⑧ final three-arm result and the ablation
# --------------------------------------------------------------------------
def fig8() -> None:
    t36 = {a: (p, m) for (p, m), a in zip(_task36_pairs(), ("BATCHONLY", "TUNED"))}
    cells = [
        ("N=6\nseed 20261100\n(TASK36)", t36["BATCHONLY"][1], t36["TUNED"][1],
         t36["BATCHONLY"][0], t36["TUNED"][0], 0.9940, 0.9726),
        ("N=8\nseed 20261000\n(TASK35)", 0.9175, 0.9028, 0.9101, 0.8971, 0.9183, 0.8993),
    ]
    ax = Axes(width=700, height=448, xlim=(-0.62, 1.62), ylim=(0.86, 1.035), bottom=92)
    ax.hline(1.0, color=C["ink"], dash="4 3")
    ax.hspan(0.98, 1.02, color=C["muted"], opacity=0.16)
    for i, (lab, a2, a3, p2, p3, b2, b3) in enumerate(cells):
        # arm 2: what batch_size alone buys; arm 3 adds the grid on top
        ax.bar(i - 0.17, a2, w=0.28, color=C["arm2"], y_base=1.0, opacity=0.9,
               stroke=C["arm2"])
        ax.bar(i + 0.17, a3, w=0.28, color=C["arm3"], y_base=1.0, opacity=0.9,
               stroke=C["arm3"])
        # the grid's marginal contribution, drawn on the arm-3 bar
        ax.bar(i + 0.17, a3, w=0.28, color=C["accent"], y_base=a2, opacity=0.55)
        ax.marker(i - 0.17, p2, color=C["ink"], r=4.5, shape="x")
        ax.marker(i + 0.17, p3, color=C["ink"], r=4.5, shape="x")
        ax.marker(i - 0.17, b2, color=C["ink"], r=3.4, shape="o", fill="#ffffff")
        ax.marker(i + 0.17, b3, color=C["ink"], r=3.4, shape="o", fill="#ffffff")
        ax.text(i - 0.17, a2 - 0.006, f"{100 * (1 - a2):+.2f} %", size=11,
                fill=C["arm2"], weight="bold")
        ax.text(i + 0.17, a3 - 0.006, f"{100 * (1 - a3):+.2f} %", size=11,
                fill=C["arm3"], weight="bold")
        ax.text(i + 0.17, (a2 + a3) / 2, f"격자 {100 * (a2 - a3):+.2f} %p",
                size=10, fill=C["accent"])
    ax.frame(xticks=[0, 1], xtick_labels=[c[0] for c in cells],
             yticks=[0.88, 0.92, 0.96, 1.00],
             yfmt=lambda v: f"{v:.2f}",
             ylabel="device time ratio (arm / BASE) — 1보다 작으면 개선",
             title="⑧ compile 구성이 device time을 회수한다 — 그리고 그 출처는 조건부다",
             subtitle="채널 A′(막대) · 채널 B(속 빈 원) · 선등록 예측(×). 두 N 모두 확증 PASS (TASK35·TASK36)")
    ax.legend([("② BATCHONLY — batch_size만 (KV pool 8 → 16)", C["arm2"], "box"),
               ("③ TUNED — batch_size + bucket 격자", C["arm3"], "box"),
               ("격자가 더한 몫", C["accent"], "box"),
               ("선등록 sim 예측", C["ink"], "o"),
               ("채널 B (모형 무의존)", C["muted"], "o")],
              x=ax.x0 + 300, y=ax.y1 + 22)
    ax.text(ax.x0 + 8, ax.y0 + 60,
            "N=8에서는 batch_size가 이득의 대부분(+8.25 %)을 낸다.",
            size=11, anchor="start", fill=C["muted"], data=False)
    ax.text(ax.x0 + 8, ax.y0 + 75,
            "N=6(신규 seed)에서는 BASE가 이미 17/18을 재사용해 batch_size 레버에 살 것이 남아 있지 않다.",
            size=11, anchor="start", fill=C["muted"], data=False)
    ax.save(HERE / "fig8_final_result.svg")


def main() -> int:
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8):
        f()
        print(f"wrote {f.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
