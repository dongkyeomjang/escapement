#!/usr/bin/env python3
"""English figure labels.

The figures were authored in Korean because every research document in this
repository is. The paper is in English, so the paper's figures must be too --
and there is a second, harder reason: **no CJK font exists on this host**, so a
Korean label cannot be embedded in a PDF at all. This table is therefore both a
translation and the thing that makes PDF output possible.

Every string must be Latin-1, because the PDF fonts use WinAnsiEncoding. Arrows
become ``->``, the minus sign becomes ``-``, Greek letters are spelled out, and
the circled figure numbers are dropped entirely -- LaTeX numbers the figures
from its own captions.

``svgplot.set_language`` raises on any non-ASCII label this table does not
cover, so a Korean string cannot silently survive into an English figure.
"""

TABLE: dict[str, str] = {
    # -- (1) reuse cliff ---------------------------------------------------
    "metric은 hit이라 하고": "the metric reports a hit",
    "device는 재계산한다": "while the device recomputes",
    "생존": "alive",
    "소멸": "gone",
    "gap 중 도착한 배경 요청 수 B": "background requests arriving during the gap, B",
    "① 재사용 절벽 — 문턱은 token 총량이 아니라 요청 개수다":
        "Reuse cliff: the threshold counts requests, not tokens",
    "층 2 = outer 8 slot × 8,192 token, FIFO. 2,000 token 요청, 12/12 재현 (실측)":
        "Layer 2 = 8 outer slots x 8,192 tokens, FIFO. 2,000-token requests, "
        "12/12 reproduced (measured)",
    "실측 · 층 2 실제 재사용 (FIFO 8 slot)":
        "measured - layer 2 actual reuse (FIFO, 8 slots)",
    "`prefix_cache_hits_total` (층 1, LRU 512)":
        "prefix_cache_hits_total (layer 1, LRU 512)",
    "절제(모형): LRU·block 단위 회수 (요청 크기별)":
        "ablation (model): LRU, block-granular reclaim, by request size",

    # -- (2) grid alignment ------------------------------------------------
    "연속 격자 → 1.0000 (절제, 모형)": "continuous grid -> 1.0000 (ablation, model)",
    "격자에 bucket 6만 추가": "add only bucket 6 to the grid",
    "(재compile 개입)": "(recompile intervention)",
    "1 위 = gap이 오히려 이롭다 (역전)": "above 1 = the gap helps (sign reversal)",
    "동시 세션 수 N   (max_num_seqs = 8)": "concurrent sessions N   (max_num_seqs = 8)",
    "② 격자 정렬이 gap 효과의 부호를 정한다 — 개입으로 확정":
        "Grid alignment sets the sign of the gap effect",
    "워크로드·seed·모델·slot 수를 고정하고 격자만 바꿨다 (개입)":
        "Workload, seed, model and slot count fixed; only the grid changed (intervention)",
    "측정 격자 (1,2,4,8)": "measured grid (1,2,4,8)",
    "개입 격자 (1,2,4,6,8)": "intervened grid (1,2,4,6,8)",
    "동치 밴드 [0.98, 1.02]": "equivalence band [0.98, 1.02]",

    # -- (3) prefill tax ---------------------------------------------------
    "v1 = decode 항만": "v1 = decode term only",
    "v2 = decode + prefill 직렬화 항": "v2 = decode + prefill serialisation term",
    "동시 세션 수 N": "concurrent sessions N",
    "예측 ITL 합 / 실측 ITL 합": "predicted ITL sum / measured ITL sum",
    "③ prefill은 시스템 비용이다 — 그 항을 넣으면 N 의존 편향이 사라진다":
        "Prefill is a system cost - adding its term removes the N-dependent bias",
    "스파이크/prefill = 1.012–1.140 (9/9 run). v1 0.565–0.855 → v2 0.973–1.039 (실측)":
        "spike/prefill = 1.012-1.140 (9/9 runs). v1 0.565-0.855 -> v2 0.973-1.039 (measured)",
    "속 빈 표식 = v1, 채운 표식 = v2": "hollow marker = v1, filled marker = v2",

    # -- (4) simulator validation -----------------------------------------
    "±0.03 밴드": "+/-0.03 band",
    "시뮬레이터 예측 ratio (보정 파라미터 0개)":
        "simulator prediction ratio (zero fitted parameters)",
    "실측 ratio": "measured ratio",
    "④ 무보정 시뮬레이터의 예측력": "Predictive power of the uncalibrated simulator",
    "선등록된 점(파랑·주황·빨강)은 전부 측정 전에 commit됐다":
        "Every preregistered point (blue, orange, red) was committed before measurement",
    "in-sample 재현 (11점)": "in-sample reproduction (11 points)",
    "out-of-sample 선등록 (3점)": "out-of-sample, preregistered (3 points)",
    "device + 정책 개입 (2점)": "device + policy intervention (2 points)",
    "device + compile 구성 (4점)": "device + compile configuration (4 points)",
    "N=6 재확증 (2점)": "N=6 reconfirmation (2 points)",

    # -- (5) headroom decomposition ---------------------------------------
    "device time 절감 (%)": "device time saved (%)",
    "⑤ headroom의 절반 이상은 조율의 몫이고 지식으로 살 수 없다":
        "Most of the headroom is coordination, and knowledge cannot buy it",
    "막대 위 숫자 = 조율의 비중 (a−e)/a. 중앙 60 %, 범위 49–73 %. 현실 tool latency 워크로드에서 계산":
        "Bar label = coordination share (a-e)/a; median 60 %, range 49-73 %",
    "(e) 전지적 지식 · 세션별 독립 결정":
        "(e) omniscient, per-session decisions",
    "(a)−(e) 조율의 몫 — 어떤 per-session 정책도 닿을 수 없다":
        "(a)-(e) coordination - no per-session policy reaches it",
    "(b) 반환 시각만": "(b) return times only",
    "(c) 생성 길이만": "(c) generation lengths only",
    "(d) 둘 다": "(d) both",
    "탐색 seed에서 +4.32 % → 평가 seed에서 −0.14 %:":
        "+4.32 % on exploration seeds -> -0.14 % on held-out seeds:",
    "자유 파라미터 2개·20조합 탐색이 만든 허구 이득":
        "phantom gain from 2 free parameters, 20-config search",

    # -- (6) predictor error ----------------------------------------------
    "σ* = 1.06–1.82 s": "sigma* = 1.06-1.82 s",
    "B(δ) — 논문 그대로": "B(delta) - as published",
    "μ̂ — 점추정": "mu-hat - point estimate",
    "수렴 후 예측 오차 std (s, 로그 축)":
        "converged prediction error std (s, log axis)",
    "⑥ 예측기는 문턱을 5.6–9.7배 초과하고, 표본을 늘려도 줄지 않는다":
        "The predictor misses the threshold by 5.6-9.7x",
    "표본 10 → 100,000에서 std 8.4 → 10.5 s. 상한도 점추정도 같은 벽에 부딪힌다 (실측)":
        "Samples 10 -> 100,000: std 8.4 -> 10.5 s; bound and point estimate hit one wall",
    "『Bash』가 27 ms일지 300 s일지는 명령이 정하고, 도구 이름은 그것을 담지 않는다":
        "Whether 'Bash' takes 27 ms or 300 s is set by the command; the tool name does not "
        "carry it",

    # -- (7) compile cost --------------------------------------------------
    "42.3 + 61.33 × compiled model 수": "42.3 + 61.33 x (compiled models)",
    "같은 bucket 수의 두 점 → 재현 오차 시간 2.2 %, 크기 0.6 %":
        "two points at the same bucket count -> repeat error 2.2 % time, 0.6 % size",
    "compiled model 수 (decoder bucket 수 + prefill graph 1)":
        "compiled models (decoder buckets + 1 prefill graph)",
    "⑦ 재compile은 7분이다 — 두 점으로 세운 모형이 다섯 번째 점에서도 맞는다":
        "A recompile costs seven minutes",
    "Qwen3-4B, max_seq_len 8192, num_devices 4. 마지막 점 오차 시간 −0.7 %, 크기 +0.6 %":
        "Qwen3-4B, max_seq_len 8192, num_devices 4. Last point: -0.7 % time, +0.6 % size",
    "모형을 세운 관측점": "points the model was fitted to",
    "모형을 시험한 관측점": "points that tested the model",

    # -- (8) final result --------------------------------------------------
    "device time ratio (arm / BASE) — 1보다 작으면 개선":
        "device time ratio (arm / BASE) - below 1 is an improvement",
    "⑧ compile 구성이 device time을 회수한다 — 그리고 그 출처는 조건부다":
        "Compile configuration recovers device time",
    "채널 A′(막대) · 채널 B(속 빈 원) · 선등록 예측(×). 두 N 모두 확증 PASS (실측)":
        "Channel A' (bars), B (hollow), prereg. prediction (x). Both N: PASS (measured)",
    "② BATCHONLY — batch_size만 (KV pool 8 → 16)":
        "(2) BATCHONLY - batch_size only (8 -> 16)",
    "③ TUNED — batch_size + bucket 격자": "(3) TUNED - batch_size + bucket grid",
    "격자가 더한 몫": "what the grid adds",
    "선등록 sim 예측": "preregistered sim prediction",
    "채널 B (모형 무의존)": "channel B (model-free)",
    "N=8에서는 batch_size가 이득의 대부분(+8.25 %)을 낸다.":
        "At N=8, batch_size supplies most of the gain (+8.25 %).",
    "N=6(신규 seed)에서는 BASE가 이미 17/18을 재사용해 batch_size 레버에 살 것이 남아 있지 않다.":
        "At N=6 (fresh seed) BASE already reuses 17/18, so the batch_size lever has nothing "
        "left to buy.",

    # -- (9) batch_size saturation ----------------------------------------
    "KV 한계 B ≈ 46 (외삽)": "KV ceiling B ~ 46 (extrapolated)",
    "B=16 이후 평평": "flat beyond B=16",
    "이득은 KV 한계의": "the gain ends at one third",
    "3분의 1에서 끝난다": "of the KV ceiling",
    "device time ratio (B8 대비)": "device time ratio vs B8",
    "⑨ batch_size의 이득은 생존율이 포화하는 곳에서 끝난다":
        "The batch_size gain ends where the survival rate saturates",
    "실선·채운 표식 = 채널 A′, 속 빈 표식 = 채널 B (두 채널 차 ≤ 0.0068), 점선 = 측정 전 commit한 sim":
        "Solid/filled = channel A', hollow = channel B (gap <= 0.0068), dashed = sim committed "
        "before measurement",
    "생존율 100 %": "100 % survival",
    "N=10만 28/30 — 여기서만 B24가 2 % 더 준다":
        "only N=10 is at 28/30 - the one place B24 still buys 2 %",
    "batch_size B  (= outer KV slot 수 = max_num_seqs)":
        "batch_size B  (= outer KV slots = max_num_seqs)",
    "층 2 재사용 생존율": "layer-2 reuse survival rate",
}

#: Labels built with an f-string: fixed text, variable number.
PATTERNS: list[tuple[str, str]] = [
    (r"ε=(\d+)", r"eps=\1"),
    (r"격자 ([-+][\d.]+) %p", r"grid \1 pp"),
]
