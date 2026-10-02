# GTASK05 — GPU step 비용 측정 (FULL · PIECEWISE · eager)

## 상태

PARTIAL

## 날짜

2026-09-29

## 목적

GPU 지시문 G-02 작업 D. GPU descriptor의 `step_cost_model`에 해당하는 세 곡선을 잰다([GTASK02](GTASK02.md) FIT_GAPS 8). 세 곡선은 FULL decode, PIECEWISE 혼합 증분, eager 혼합 증분이다. 설계는 [GPU_STEPCOST_PREREG.md](GPU_STEPCOST_PREREG.md)로 측정 전에 선등록했고, 예측·판정 없이 반복 간 재현성만 보고한다.

## 배경

- [GTASK03](GTASK03.md) — `[GSTEP]` dispatch 로그 patch와 관문 G1–G3 통과
- [TASK13](../TASK13.md) — NPU decode 비용 `f(bucket) + g(actual)`. 이번 FULL 적합은 이 형태에 대응한다.
- [TASK22](../TASK22.md) — NPU prefill 배타 실행과 비용 모형 v2
- [GTASK06](GTASK06.md) — descriptor의 `step_cost.*` field가 이 TASK의 값을 기다린다.

## 시작 상태

- branch `gpu-a6000`, 선등록 `fc2d0ab`
- 첫 run `20260929T1021Z`는 G3 r0 도중 host가 다운되며 중단됐다.
- 사용자가 문제의 PCIe 슬롯을 비활성화했고, 그 결과 측정 카드가 바뀌었다.

## 수행 내용

1. 장비를 다시 점검했다. 빠진 카드는 uuid `00596b63…`이며, GTASK02–05 측정이 모두 이 카드에서 이뤄졌다. 새로 GPU 0이 된 카드는 uuid `4485e769…`이다. 메모리 40 GB 쓰기·검증과 bf16 matmul 점검을 통과했다.
2. **개정 1**(`e7f9b45`)을 측정 전에 commit했다. 첫 run 전체를 제외하고, 카드 uuid를 유효성 규칙에 추가하고, 6 lifecycle을 모두 다시 재기로 했다.
3. `run_stepcost.sh`를 수정 없이 실행했다(16:07:03–16:21:02 UTC). 6 lifecycle 모두 `rc=0`이었다.
4. 사전 등록한 분석 코드가 실패했다(아래 「실패 / 무효 시도」). 수치를 보기 전에 **개정 2**(`05ceda4`)로 probe 매칭 규칙을 고쳐 commit한 뒤 분석했다.
5. 선등록 분석에서 작은 step의 증분이 음수로 나왔다. 이 현상을 해석하려고 **사후 탐색**(선등록 아님)으로 lag별 Δ와 3-step 창 증분을 계산했다(`stepcost_window_explore.py`).

## 변경된 파일

- `docs/research/gpu/GPU_STEPCOST_PREREG.md` — 개정 1, 개정 2
- `experiments/gpu/stepcost/stepcost_analyze.py` — `--chunk-budget` opt-in(개정 2). flag가 없으면 원 동작이 그대로다.
- `experiments/gpu/stepcost/stepcost_window_explore.py` (신규, 사후 탐색)
- `docs/research/gpu/GTASK05.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

- 격자 3개 × 반복 2 = lifecycle 6개. 격자는 G1 `[1,2,4,8,16]`, G2 `[1,2,4,6,8]`, G3 `[1..16]`이다.
- 요청 구성과 server 인자는 선등록 그대로다. `--max-num-batched-tokens 2048`, KV pool 4,096 block을 썼다.
- 유효성: 6 lifecycle 모두 `valid`, preemption 증분 0, 기동 전·후 GPU process 없음, ready 시점 이 run의 process가 uuid `GPU-4485e769…`에 있음.

Population: lifecycle 6개, FULL cell 16 × 3 격자, 고립 step cell 26 × 3 격자(MIXED는 cell당 probe 40개, EAGER는 20개).
Source: `[GSTEP]`의 `perf_counter` dispatch 시각(EngineCore process 하나)이다. `Δ_k = t_{k+1} − t_k`.
Device scope: GPU 1장(uuid `4485e769…`). 단위는 ms.

## 결과

### FULL decode (선등록 분석)

| n | G1 (pad) | G2 (mode) | G3 (pad = n) |
|---|---|---|---|
| 1 | 13.418 (1) | 13.414 FULL | 13.396 |
| 4 | 13.354 (4) | 13.343 FULL | 13.336 |
| 5 | 13.485 (8) | 13.375 FULL(6) | 13.384 |
| 8 | 13.620 (8) | 13.601 FULL | 13.604 |
| 9 | 14.069 (16) | **19.339 eager** | 13.607 |
| 12 | 14.209 (16) | **19.530 eager** | 13.807 |
| 16 | 14.360 (16) | **19.541 eager** | 14.339 |

- 전체 표는 `summary.md`에 있다.
- FULL cell의 lifecycle 간 중앙값 범위는 ≤ 0.039 ms, eager cell은 0.28–0.58 ms다.
- 적합 `t = F[b] + g·n`(G1·G3, 점 64개)의 결과는 `g = 0.0406 ms/요청`, `F[b]` 13.17–13.72 ms, 최대 |잔차| 0.035 ms다.
- `F[b]`와 `g`는 G1의 bucket 4·8·16에서만 분리된다. G3만 쓰이는 bucket의 `F[b]`는 `g·n`과 공선이다.

### lag 규칙 (선등록)

EAGER d=4 p=2048 첫 chunk에서 median elevation은 L=0: 3.2 ms, **L=1: 138.9 ms**, L=2: 3.3 ms였다. 따라서 **L = 1**이며, 사전 기대와 일치한다.

### 고립 step 증분 (선등록 분석, lag 1, 세 격자 범위)

| phase | d | p (첫 chunk) | mode | 증분 ms |
|---|---|---|---|---|
| EAGER | 1 | 32 / 64 | NONE | −3.8 ~ −2.5 (**음수**) |
| EAGER | 1 | 128 / 256 / 512 / 1024 | NONE | 1.5–1.7 / 11.8–12.2 / 30.7–31.2 / 74.3–74.9 |
| EAGER | 1 | 2048 (2047) | NONE | 137.0–137.6 |
| EAGER | 4 | 32 / 64 | NONE | −3.4 ~ −2.3 (**음수**) |
| EAGER | 4 | 128 / 256 / 512 / 1024 | NONE | 1.8–2.0 / 12.6–12.7 / 31.7–31.8 / 75.0–75.8 |
| EAGER | 4 | 2048 (2044) | NONE | 138.3–139.0 |
| MIXED | 1–8 | 2–8 | PIECEWISE | −0.08 ~ 1.47 |
| MIXED (G2, toks > 8) | 1–8 | 2–8 | NONE | −4.1 ~ −1.9 (**음수**) |

고립 step cell의 lifecycle 간 중앙값 범위는 ≤ 1.5 ms다.

### 사후 탐색 (선등록 아님)

- eager step은 모두 lag 0의 Δ가 약 17–18 ms로, decode 기준선(13.4–14.1 ms)보다 **약 3.5–4.5 ms 길다**. p와 거의 무관하다.
- 작은 eager step은 그만큼 lag 1이 기준선보다 짧다(p=32에서 9.5–10.0 ms).
- 3-step 창 증분 `Σ Δ_{k..k+2} − 3·기준선`(d=4): p=32 0.8, 64 1.7, 128 5.6, 256 16.6, 512 35.5, 1024 78.8–79.2, 2048(2044) 144.9–145.6 ms. 단조 증가한다.
- PIECEWISE 혼합 step의 창 증분은 −0.70 ~ 0.82 ms로, 0을 사이에 두고 흩어진다.

## 핵심 발견

1. **`class`** — **decode step의 bucket padding 비용은 작고, 격자 밖으로 벗어나는 비용은 크다.** G1에서 n=9를 16으로 padding한 비용은 14.07 대 13.61 ms, 즉 +0.46 ms(+3.4 %)다. 격자 밖 eager decode(G2, n > 8)는 19.3–19.5 ms로 FULL보다 +5.7–5.9 ms(+42 %) 느렸다. 이 모양을 `class`로 보는 이유는 cudagraph replay와 eager launch의 차이(kernel launch를 CPU가 매 step 다시 하는지)에서 나오기 때문이다. 특정 구현의 상수 때문이 아니다. 수치 13.4 ms, +42 %는 **`silicon`/`stack`**이다.
2. **`class`** — **decode 비용은 요청 수에 거의 평탄하다.** `F[b] + g·n` 적합에서 `g = 0.041 ms/요청`이고 n=1→16에서 약 7 % 증가했다. 형태는 NPU [TASK13](../TASK13.md)의 `f(bucket) + g(actual)`와 같다. 형태가 두 기판에서 같은 이유는 decode가 weight 적재 중심이라 batch 폭이 늘어도 비용이 조금만 늘기 때문이다. 수치 `g`는 **`silicon`**이다.
3. **`stack`** — **eager step마다 약 4 ms의 dispatch 지연이 붙는다.** 이 지연은 prompt 길이와 무관하다. 작은 eager step은 이 지연이 GPU 시간을 가려, lag 1 귀속 규칙에서 증분이 음수가 된다. 원인을 CPU kernel launch로 보는 것은 **가설**이다(CUDA event 없이 dispatch 간격만 봤다).
4. **`universal`** — **async scheduling의 dispatch 간격은 GPU 시간이 CPU 지연보다 충분히 클 때만 step 비용을 한 칸 뒤(lag 1)로 옮겨 담는다.** L=1 규칙은 p ≥ 256 eager step에서 창 증분과 3–7 ms 이내로 맞는다. 차이는 lag 0의 dispatch 지연에서 온다. 증분이 약 2 ms 아래인 step에서는 이 채널로 부호도 정할 수 없다.

## 해석

- **descriptor 값으로 쓸 수 있는 것** (카드 uuid `4485e769…`, 이 server 인자에 한정)
  - `step_cost.decode`: FULL `F[b] + g·n`이며, 표 값 그대로다.
  - 격자 밖 decode: 약 19.4 ms.
  - `step_cost.eager`: p ≥ 256에서 증분이 거의 선형 이상으로 늘어난다(256 → 2048에서 약 12 → 138 ms). dispatch 간 처리량 관점의 비용은 창 증분(약 4 ms 더 큼)이 더 가깝다.
- **쓸 수 없는 것**: `step_cost.mixed`(PIECEWISE, p ≤ 8). 증분이 −0.7 ~ 1.5 ms로 채널 분해능 아래다. 사전 기대 "PIECEWISE 증분 < 1 ms"는 확인도 반박도 할 수 없다. 이 곡선이 없어서 상태를 `PARTIAL`로 둔다.
- 사전 기대 대조 (판정 아님)
  - FULL 기대 두 개("G1 padding n은 G3보다 느리다", "G2 n > 8은 eager라 느리다")는 방향이 맞았다.
  - lag 기대 `L = 1`도 맞았다.
- NPU와 비교하면 NPU는 prefill이 배타 실행이라 prefill 비용 자체를 따로 잴 수 있다. GPU는 혼합 실행이라 decode 대비 **증분**으로만 정의되고, 작은 증분은 이 관측 채널로는 보이지 않는다.

## 확인되지 않은 사항

- GPU kernel 시간 자체: CUDA event를 쓰지 않았다. eager lag 0의 +4 ms가 CPU launch 때문인지는 `UNKNOWN`이다.
- PIECEWISE 혼합 증분(p ≤ 8): `UNKNOWN`이다(분해능 아래).
- 카드 간 차이: 빠진 카드(`00596b63…`)와 같은 값인지는 판정하지 않았다(개정 1).
- p = 2048 cell의 나머지 chunk(PIECEWISE, 1–4 token) 비용은 cell에 포함하지 않았다.

## 실패 / 무효 시도

1. **첫 run `20260929T1021Z`** — G3 r0 도중 host 다운(10:28:57 UTC 이후 로그가 NUL byte로 끊김). G3 r0은 `INVALID`, G1·G2 r0은 카드 교체 때문에 제외했다(개정 1). raw는 보존했다.
2. **선등록 분석 코드의 실패** — `ValueError: max() iterable argument is empty`.
   - 원인: `--max-num-batched-tokens 2048`에서 `d + p > 2048`인 probe가 두 chunk로 나뉘어, `maxq == p` 매칭이 lag 규칙 cell(d=4, p=2048)에서 0개가 됐다.
   - 선등록 설계가 step token 상한을 확인하지 않은 오류다.
   - 원 traceback은 `analyze.stdout`에 있다. 수정 규칙은 수치를 보기 전에 개정 2로 commit했다.
3. **lag 1 귀속의 적용 범위** — 선등록한 귀속 규칙은 작은 eager step과 PIECEWISE step에서 증분을 음수로 만든다. 이 cell의 선등록 표 값은 **비용 추정치로 쓰지 않는다**. 표 자체는 수정하지 않고 보존했다.

## 연구 원칙에 미치는 영향

- 선등록 설계에 server의 step token 상한(`--max-num-batched-tokens`)과 요청 크기의 관계 검사를 넣는다. GTASK02 발견 6("로그에 안 남으므로 명시 필수")의 연장이다.
- dispatch 간격 채널에는 분해능 한계(약 2 ms)가 있다. 이보다 작은 증분을 재는 TASK는 CUDA event 같은 device 시각 채널을 먼저 확보한다.

## 다음 작업

사용자·Advisor 지시 없이 시작하지 않는다. 권고 후보:

1. PIECEWISE 증분을 device 시각으로 재는 관측 수단 검토(CUDA event patch, 적용 전 보고 필요)
2. `DESCRIPTOR_REQUIREMENTS.md` §I에 이번 값과 제한을 반영(NPU 쪽 descriptor 개편 입력)

## 재현 정보

- **선등록 `fc2d0abd348a1fe835474f6260501ced84588a8a`(09:41:05 UTC)**
- **개정 1 `e7f9b4521082d8fd4a59bbc39e9d04966cbc4d39`(16:06:58 UTC) → 측정 시작 16:07:03 UTC** → 측정 종료 16:21:02
- **개정 2 `05ceda446385313f2c24d4c6cb68d23534a15781`(16:24:30 UTC) → 개정 분석 실행**
- 개정 2는 측정 후 commit했지만 step 시간 수치 확인 전이다.
- raw: `results/gpu/stepcost/20260929T1607Z/`(git 비추적)
  - `start.txt`, `sequence.log`
  - `{G1,G2,G3}_r{0,1}/{server.log,events.json,lifecycle.json,summary.json,env.txt}`
  - `analyze.stdout`(원 실패), `analyze_amend2.stdout`, `summary.{json,md}`(SHA256 `709f594174aa229f…`), `window_explore.json`
- 제외한 첫 run: `results/gpu/stepcost/20260929T1021Z/`
- 측정: `experiments/gpu/stepcost/run_stepcost.sh <RUN>`
- 분석: `stepcost_analyze.py --run-dir <RUN> --chunk-budget 2048 --out <RUN>/summary.json --md <RUN>/summary.md`
- 사후 탐색: `stepcost_window_explore.py --run-dir <RUN> --out <RUN>/window_explore.json`
- 환경: `vllm 0.22.0`(venv `/home/csdc/kyeom/envs/vllm-0.22.0`), driver 580.178.04, `Qwen/Qwen3-4B@1cfa9a72…`, observation patch `d75d04d8…`, GPU uuid `GPU-4485e769-430a-430d-3383-b9c4ce92a175`(serial `1324321025786`, bus `17:00.0`, PCIe x8)
