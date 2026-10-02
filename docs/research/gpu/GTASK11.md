# GTASK11 — GPU multi-turn 본 측정과 판정

## 상태

DONE

## 날짜

2026-09-30

## 목적

GPU 지시문 G-04.
- 선등록 [GPU_MULTITURN_PREREG.md](GPU_MULTITURN_PREREG.md) 개정 1(§7, NPU 개정 2와 정렬)을 측정 전에 commit한다.
- 그 뒤 본 측정 55 lifecycle(확증 N 20·22·24 × BASE·POOL·POOL+GRID × 5, 탐색 N 26 × BASE·POOL × 5)을 streaming으로 하고 §5 전 항목을 판정한다.

## 배경

- [GTASK07](GTASK07.md)–[GTASK10](GTASK10.md): 설계, 구성 선정, 예측 선등록(`2bef619`), 파일럿
- NPU [TASK81](../TASK81.md)·[TASK82](../TASK82.md): NPU 개정 2와 본 측정

## 시작 상태

- HEAD `618cf27`
- `git merge origin/main` → **merge `eb6343c`**(`origin/main` `074aedc`, TASK81–82 포함, 충돌 없음)

## 수행 내용

1. NPU 개정 2(`5f62fb4`, `MULTITURN_MAIN_PREREG.md` §7)와 TASK82를 읽었다.
2. **선등록 개정 1**(§7)을 작성했다.
   - NPU 영 재사용 0.84718(TASK82 확증 10 cell 합산 5,771/6,812)
   - skill 0.5 비율 조건(§5.1·§5.2·§5.6), NPU식 `NOT_INFORMATIVE` 규칙
   - decode-only h 식별 규칙
   - 재실행 규칙, 순서표(`ORDER.json`, seed 20262410), 판정 시점
   - H-sim·고아 축출 등 추가 보고
   - 판정 script `main_judge.py`
   - **commit `721e4d0`(2026-09-30 14:11:43 UTC)**
   - 판정 script는 파일럿 산출을 symlink로 엮은 가짜 run에서 코드 경로만 시험했다(§7.8에 사실 기록). 이때 TTFT가 없는 non-streaming run에서 나던 빈 중앙값 오류를 측정 전에 고쳤다.
3. 본 측정을 했다. `run_schedule.py`를 세션과 분리해 실행했고, 첫 lifecycle은 14:11:50 UTC에 시작해 마지막은 17:26:57 UTC에 끝났다.
4. 모든 lifecycle이 끝난 뒤 유효성을 전수 확인하고 `main_judge.py`를 **한 번** 실행했다. 판정 script 수정은 0이다.

## 변경된 파일

- `docs/research/gpu/GPU_MULTITURN_PREREG.md`(개정 1), `docs/research/gpu/GTASK11.md`(신규), `docs/research/gpu/GPU_INDEX.md`
- `experiments/gpu/multiturn/{main_judge.py, make_main_order.py, plans/main/ORDER.json}`(신규, 개정 1 commit)

## 실험 또는 검증 방법

```bash
setsid nohup env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/run_schedule.py \
  --schedule <abs>/experiments/gpu/multiturn/plans/main/ORDER.json \
  --run-dir <abs>/results/gpu/multiturn/main/20260930T1411Z &
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/main_judge.py \
  --run-dir <RUN> --out <RUN>/verdict.json
```

- `requested_condition`: 선등록 §1·§2·§7의 55 lifecycle, streaming, 평가 120 s, 카드 `4485e769…`
- `observed_condition`
  - **55/55 유효**: runner 유효, preemption 0, 구간 온라인 = 재계산, 평가 끝 이후 발행 0, HTTP 오류 0, 생성 길이 불일치 0, join 누락 0
  - step mode 예측 불일치 0, client·server `cached` 불일치 0
  - 재실행 0
- `condition_reached`: `YES`

Population: 확증 45 lifecycle, 탐색 10. 확증 cell당 turn ≥ 1 요청은 1,477–1,596개(replicate 5개 합)다.
Source: client 행, server `[GSTEP]`·`[GPFX]`, KV events, `/metrics`.
Device scope: GPU 1장. 비용 단위는 ms/turn(A′-GPU 가격 채널, `lo`/`hi`).

## 결과

### 판정 요약 (두 bound 판정이 모든 항목에서 같았다)

| 항목 | 해석 v1 | sim LRU | sim FIFO | 사전 예측 |
|---|---|---|---|---|
| §5.1 재사용률 | **FAIL**((a) N24 BASE +0.138) | **PASS**(skill 0.35·0.31) | FAIL(계통 −0.10) | — |
| §5.2 비용 비 | **FAIL**(N24 두 cell 기본·강화 불통) | **PASS**(6/6, 6/6, skill 0.36·0.37) | FAIL | N20·22 `NOT_INFORMATIVE` 예상 → 아니었음(Σ\|1−m\|/6 = 0.035) |
| §5.3 순위(해석) | **PASS** N20·22·24 | — | — | BASE 쌍만 해소 — **적중** |
| §5.4 POOL+GRID 대 POOL | **INCONCLUSIVE** ×3 | — | — | `INCONCLUSIVE` — **적중** |
| §5.5 LRU 대 FIFO | — | — | — | **`LRU_SUPPORTED`** — **적중** |
| §5.6 h(n)(해석 B2) | **PASS**(decode-only, skill 통과) / 병기 `reqs` 정의 FAIL(최대 0.212) | — | — | — |

### §5.1 재사용률 (turn ≥ 1, r0–r4 합산; 예측은 `lo`, `hi`와 ±0.002 이내)

| cell | 관측 | 해석 | sim LRU | sim FIFO | 부분 hit 관측 / LRU / FIFO |
|---|---|---|---|---|---|
| N20 BASE | 0.856 (1,299/1,517) | 0.844 | 0.857 | 0.761 | 2.2 % / 1.1 / 12.4 |
| N20 POOL | 0.905 (1,392/1,538) | 0.877 | 0.904 | 0.819 | 1.1 / 1.1 / 9.8 |
| N20 POOL+GRID | 0.909 (1,402/1,543) | 0.877 | 0.900 | 0.821 | 1.6 / 0.9 / 9.7 |
| N22 BASE | 0.817 (1,225/1,499) | 0.828 | 0.849 | 0.735 | 4.5 / 2.3 / 13.4 |
| N22 POOL | 0.900 (1,403/1,559) | 0.862 | 0.895 | 0.787 | 1.2 / 1.1 / 11.0 |
| N22 POOL+GRID | 0.898 (1,403/1,562) | 0.862 | 0.892 | 0.788 | 0.9 / 0.8 / 11.7 |
| N24 BASE | **0.669** (988/1,477) | **0.807** | 0.753 | 0.611 | 7.4 / 5.3 / 14.2 |
| N24 POOL | 0.852 (1,360/1,596) | 0.850 | 0.861 | 0.717 | 1.3 / 1.1 / 13.0 |
| N24 POOL+GRID | 0.854 (1,361/1,594) | 0.850 | 0.862 | 0.702 | 1.9 / 1.3 / 14.0 |

- **MAE**(lo): 해석 0.0333, sim LRU 0.0173, sim FIFO 0.1021, **NPU 영 예측기(0.84718) 0.0502**
  - 영 MAE가 `NOT_INFORMATIVE` 경계 0.05를 0.0002 넘어 skill이 판정에 들어갔다.
  - skill 비: 해석 0.66(FAIL), sim LRU 0.35(PASS)
- **평균 부호 오차**: 해석 −0.0002, sim LRU +0.013, sim FIFO −0.102
- 관측 범위 0.240
- **구성 차이 설명력**(관측 POOL − BASE / 해석 / sim LRU)

| N | 관측 | 해석 | sim LRU |
|---|---|---|---|
| 20 | 0.049 | 0.034 | 0.046 |
| 22 | 0.083 | 0.034 | 0.045 |
| 24 | **0.183** | 0.043 | 0.108 |

  기존 합 비교(Σ|예측 − 관측| 대 BASE 예측 영)는 해석 0.299 대 0.522, sim LRU 0.156 대 0.515다.

### §5.2 비용 비 (BASE 대비, lo; hi는 ±0.003)

| cell | m | 95 % CI | 해석 | sim LRU | sim FIFO |
|---|---|---|---|---|---|
| N20 POOL | 0.9908 | [0.9690, 0.9959] | 0.9928 | 0.9886 | 0.9938 |
| N20 POOL+GRID | 0.9866 | [0.9678, 0.9916] | 0.9919 | 0.9836 | 0.9922 |
| N22 POOL | 0.9690 | [0.9525, 0.9841] | 0.9909 | 0.9839 | 0.9890 |
| N22 POOL+GRID | 0.9715 | [0.9354, 0.9826] | 0.9903 | 0.9835 | 0.9833 |
| N24 POOL | **0.9402** | [0.8122, 0.9704] | 0.9858 | 0.9583 | 0.9664 |
| N24 POOL+GRID | **0.9327** | [0.8150, 0.9690] | 0.9855 | 0.9568 | 0.9741 |

- Σ|1 − m| = 0.209(평균 0.035 ≥ 0.01, informative). 6 cell 모두 CI가 1을 포함하지 않아, 기존 규칙으로도 `NOT_INFORMATIVE`가 아니다.
- Σ|예측 − m|: 해석 0.146(비 0.70), sim LRU 0.075(0.36), sim FIFO 0.108(0.52)
- 해석은 N24 두 cell에서 |예측 − m| 0.046·0.053으로 기본·강화 기준 모두 불통이다.
- **두 bound에서 cell 판정이 갈린 곳**: sim FIFO N24 POOL 기본 기준(lo 통과, hi 불통)뿐이다. 최종 판정은 같다.

### §5.3·§5.4 (lo; hi 같음)

| N | BASE/POOL | BASE/POOL+GRID | POOL/POOL+GRID | 판정 |
|---|---|---|---|---|
| 20 | 1.0093 [1.0041, 1.0320] 해소 | 1.0135 [1.0085, 1.0333] 해소 | 1.0012 [0.9999, 1.0068] | PASS |
| 22 | 1.0320 [1.0161, 1.0499] 해소 | 1.0294 [1.0177, 1.0691] 해소 | 1.0014 [0.9911, 1.0183] | PASS |
| 24 | 1.0636 [1.0305, 1.2313] 해소 | 1.0721 [1.0320, 1.2270] 해소 | 1.0015 [0.9950, 1.0080] | PASS |

POOL+GRID/POOL: N20 0.9988 [0.9932, 1.0001], N22 0.9986 [0.9821, 1.0090], N24 0.9985 [0.9921, 1.0050] → `INCONCLUSIVE` ×3(예측 0.9991–0.9997).

### §5.5 LRU 대 FIFO

- 분리 cell 9/9, **d_L < d_F 8/9**(필요 7), Σd_L 0.148 대 Σd_F 0.937 → **`LRU_SUPPORTED`**
- 유일한 예외는 N24 BASE(관측 0.669, LRU 0.752, FIFO 0.611)다. sim LRU가 붕괴 직전 cell의 재사용을 과대 예측해서다(§5.1 표).
- **부분 hit 비율**: 관측 0.9–7.4 %가 LRU 예측(0.8–5.3 %)과 맞고, FIFO 예측(9.7–14.2 %)과는 9/9 cell에서 떨어져 있다.
- **재사용 token 비율**(관측 / LRU / FIFO)은 N20 BASE 0.846 / 0.852 / 0.699 등 같은 방향이다.
- **KV events 고아 축출(탐색)**: 모든 cell에서 **0건**이다.
  - 확증 9 cell `BlockRemoved` 702,050건, N26 256,028건
  - 축출되는 순간 자식 block이 캐시에 남아 있던 사건이 한 번도 없었다.
  - 해제 순서 LRU(요청 반납 tail 먼저)의 source 규칙이 기대하는 값이며, 할당 순서 FIFO라면 prefix block이 먼저 나가 고아가 생긴다.

### §5.6 h(n)

| 정의 | TVD 중앙 / 최대 (lo) | 균등 영 중앙 | sim LRU 중앙 | 판정 |
|---|---|---|---|---|
| **decode-only(판정)** | 0.081 / 0.184 | 0.645 | 0.102 | **PASS**(skill 0.081 ≤ 0.323) |
| `reqs`(병기) | 0.087 / 0.212 | 0.660 | 0.123 | FAIL(최대 > 0.20) |

- hi는 decode-only 0.077 / 0.179로 PASS다.
- padding 관측 0.001–0.014 대 해석 0.008–0.094, sim LRU 0.002–0.033이다. 해석은 padding을 과대 예측한다. B2 h가 관측보다 작은 n에 무게를 둔다.

### §5.7 간섭 (탐색)

- 예측/관측 중앙: 해석 1.14, sim LRU 0.96(두 bound)
- Spearman: 해석 0.88, sim LRU 0.83(lo)·0.87(hi)
- N24 BASE는 관측 354 ms/turn 대 해석 248, sim 272다. 붕괴 직전 miss prefill이 몰린다.

### H-sim 지표 (보고)

| | e = m − sim LRU 예측 (확증 6 cell) | 음 / 양 | 중앙 \|e\| |
|---|---|---|---|
| GPU lo | +0.002, +0.003, −0.015, −0.012, −0.018, −0.024 | 4 / 2 | 0.0135 |
| GPU hi | −0.003, −0.007, −0.016, −0.011, −0.018, −0.027 | 6 / 0 | 0.0134 |
| NPU TASK82 | — | 6 / 1 (7 cell) | 0.0055 |

### N = 26 탐색

| 구성 | 관측 재사용 | 해석 | sim LRU | sim FIFO |
|---|---|---|---|---|
| BASE | **0.450** (615/1,366) | 0.786 | 0.657 | 0.552 |
| POOL | 0.804 (1,241/1,543) | 0.831 | 0.833 | 0.674 |

- **붕괴가 관측됐다**: BASE 재사용은 N24 0.669 → N26 0.450(−0.219)으로 떨어졌고, zero hit가 55 %다.
- POOL/BASE 비 m = 0.899 [0.806, 0.907](lo). 예측은 해석 0.984, sim LRU 0.939, sim FIFO 0.964다.
- **세 예측기 모두 붕괴의 크기를 과소 예측했다.** sim LRU도 0.657로 관측보다 0.21 높다.

### 채널·기타

- **직접 dispatch / 가격 채널**: lifecycle 55개 중앙 **1.131**(0.973–1.156). 파일럿의 10–13 %가 본 측정에서도 그대로 나왔다.
- **turn ≥ 1 TTFT 중앙**
  - N20 0.65–0.77 s, N22 1.03–1.18 s, N24 1.54–1.94 s, N26 2.34–3.00 s
  - NPU의 0.07–0.08 s보다 한 자릿수 크다. 포화 근처의 대기열 때문이다.
- **turn당 A′-GPU(lo, replicate 평균)**
  - BASE: N20 283.9, N22 287.4, N24 298.3, N26 319.7 ms
  - POOL: 279.5, 277.7, 272.5, 278.3 ms

## 핵심 발견

1. **`class`**(형태) / **`stack`**(값) — **GPU vLLM의 KV 축출은 해제 순서 LRU이며, multi-turn 부하에서 할당 순서 FIFO와 구별된다.**
   - 근거는 세 가지이며 독립적이다.
     - 재사용률: 분리 cell 8/9에서 LRU 쪽, Σ 오차 0.148 대 0.937
     - 부분 hit 비율: 관측 0.9–7.4 %가 LRU 예측과 맞고 FIFO 예측(10–14 %)과 다르다.
     - KV events 고아 축출: 0 / 958,078
   - GTASK04가 순차 프로토콜로 구별하지 못한 것을 구별했다.
   - `class`인 근거: 해제 순서 LRU와 tail-first 반납은 block pool 설계 범주의 선택이며, 그 관측 서명(고아 축출 0, 부분 hit 소수)은 구현 상수가 아니라 규칙에서 나온다.
2. **`stack`** — **GPU 의미론 시뮬레이터(sim LRU)가 사전 예측으로 재사용률(MAE 0.017, NPU 영 대비 skill 0.35)과 구성 비용 비(Σ 오차가 구성 효과의 36 %)를 맞혔다.** 기판 의미론을 바꿔 넣은 같은 계열의 시뮬레이터가 두 번째 기판에서도 blind 예측을 통과했다.
3. **`stack`** — **해석 v1 GPU 인스턴스는 포화 근처에서 실패했다.** N24 BASE 재사용을 +0.138 과대, N24 비용 효과를 약 5 % 과소 예측했다.
   - 포화 전(N20·22)과 POOL 계열은 ±0.04 안이었다.
   - 평균 부호 오차는 0에 가깝다(−0.0002). 오차는 치우침이 아니라 되먹임 영역에서 나온다.
   - NPU TASK82 발견 2(BASE batch 8에서 오차 집중)와 같은 구조다. G-04 §6의 v1.1(대기열 항)이 다룰 과제다.
4. **`class`** — **재사용 붕괴는 시뮬레이터 예측보다 일찍, 더 크게 온다.**
   - 관측 BASE 재사용은 N22 0.817, N24 0.669, N26 0.450이다. sim LRU 예측은 0.849, 0.752, 0.657이다.
   - 구성 차이(POOL − BASE)도 관측 0.183 대 sim 0.108(N24)이다.
   - 되먹임(miss → prefill → 대기 → idle 연장 → miss)이 시뮬레이터 안에도 있지만, 관측의 가속이 더 세다.
   - `class`인 근거: 되먹임은 용량 제한 캐시 + 대기열이면 성립하는 구조다. 시뮬레이터가 무엇을 덜 담는지는 확인하지 않았다(가설: TTFT 1.5–3 s의 대기열 길이, 요청별 대기 분포).
5. **`stack`** — **H-sim 지표는 GPU에서도 음으로 기울었다**(sim이 구성 효과를 과소; lo 4/6, hi 6/6). 크기는 NPU의 약 2.5배다(0.0135 대 0.0055). 발견 4와 같은 방향이다.
6. **`stack`** — **POOL+GRID의 격자 이득은 GPU에서 해상도 아래다**(0.9985–0.9988, CI가 1 포함). `F[b]`가 평탄해서이며, 사전 예측과 같다.

## 해석

- 논문용으로 쓸 수 있는 결론 두 가지
  - **축출 순서 판별**(발견 1)은 세 독립 신호가 일치해 이 실험의 가장 강한 결과다.
  - **sim LRU의 blind 통과**(발견 2)는 NPU(sim 기본 §5.1 MAE 0.004, §5.2 Σ 0.039)보다 오차가 크지만 같은 기준을 통과했다.
- 해석 v1은 NPU에서 통과(TASK82)하고 GPU에서 실패했다. 실패 cell은 둘 다 용량이 부하에 닿는 BASE이고, GPU 확증 cell이 포화 근처에 몰린 것(GTASK08 발견 1)이 차이를 키웠다. 기준은 NPU와 같은 강도다.
- §5.1 skill이 판정에 들어간 것은 NPU 영 MAE가 0.0502로 경계(0.05)를 0.0002 넘었기 때문이다. 경계 근처 결과임을 적어 둔다. 해석 v1은 skill과 무관하게 (a)에서 이미 FAIL이다.
- h(n)은 decode-only 정의에서만 PASS다. `reqs` 정의는 최대 TVD 0.212로 FAIL이다. 알려진 정의 차이(혼합 step prefill 요청 포함)가 결론을 가른 사례다.
- 가격 채널과 직접 채널의 약 13 % 차는 본 측정에서도 일정하다. 구성 비는 두 채널에서 같은 방향이다(파일럿 확인). 절대 비용 비교에는 채널을 명시해야 한다.

## 확인되지 않은 사항

- 시뮬레이터가 붕괴를 과소 예측하는 기전(발견 4)
- 직접 채널과 가격 채널 차이의 원인(GTASK10 이후 미확인)
- 정상성(평가 구간 전·후반 비교)은 이번 판정 script에 넣지 않았다. 보고 항목으로 지정되지 않았다.

## 실패 / 무효 시도

- 없음. 무효 lifecycle 0, 재실행 0, 판정 후 script 수정 0.
- 판정 전(측정 전) 가짜 run 시험에서 TTFT 빈 중앙값 오류를 한 번 고쳤다.

## 연구 원칙에 미치는 영향

- 관측 불가 정의 차이(h의 `reqs` 대 decode 수)는 결론을 바꿀 수 있다. 식별 규칙을 측정 전에 고정한 것(개정 1 §7.4)이 이 차이를 판정 전에 분리했다.
- skill의 `NOT_INFORMATIVE` 경계 근처 결과(0.0502 대 0.05)는 판정에 그대로 쓰되 경계 근처임을 보고한다.

## 다음 작업 — Advisor 결정이 필요한 사항

1. **v1.1 blind 검증 설계**: 이번 N26 결과(BASE 0.450)는 v1.1 개발 입력으로 쓰일 수 있다. 그래서 새 붕괴 영역 cell(새 seed, N = 26·28 등)을 따로 만들어야 한다(GPU_INDEX 기록).
2. **시뮬레이터 붕괴 과소 예측**(발견 4): 원인 조사를 할지. 요청별 대기와 관측 재사용 시계열을 대조한다.
3. **직접 채널 13 %**: CUDA event 등 device 시각 채널로 확인할지(새 patch 필요, 승인 대상)
4. **논문 서술**: 해석 v1은 NPU PASS, GPU FAIL(포화 근처)이고 sim LRU는 두 기판 PASS다. 이를 "모형 기반" 주장에 어떻게 쓸지

## 재현 정보

- merge `eb6343c`
- **선등록 `2bef619`(2026-09-29 17:54:17 UTC) → 개정 1 `721e4d01a2a0468920de13d87de1cfd0236f21aa`(2026-09-30 14:11:43 UTC) → 첫 lifecycle 14:11:50 UTC → 마지막 lifecycle 끝 17:26:57 UTC → 판정 1회**
- raw: `results/gpu/multiturn/main/20260930T1411Z/`(비추적)
  - `n{N}.{구성}.r{r}/`: `requests.jsonl`, `token_ids.jsonl.gz`, `windows.json`, `provenance.json`, `server.log`, `kv_events.jsonl`, `lifecycle.json`, `env.txt`, `done`
  - `sequence.log`, `start.txt`, `verdict.json`, `judge.stdout`
- 입력: `PREDICTIONS.json` SHA256 `1be9a991…3e7c71a45f`(변경 없음), `ORDER.json` SHA256 `95aac4b5…`, `main_judge.py` SHA256 `72f3543f…`
- 환경: `vllm 0.22.0`, driver 580.178.04, `Qwen/Qwen3-4B@1cfa9a72…`, patch `d75d04d8…`, 카드 uuid `GPU-4485e769-430a-430d-3383-b9c4ce92a175`
