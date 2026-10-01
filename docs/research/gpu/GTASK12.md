# GTASK12 — 사건 재생 검사: GPU 정확 의미론의 요청 단위 hit 재현

## 상태

DONE

## 날짜

2026-10-01

## 목적

GPU 지시문 G-05 작업 A.
- GTASK11의 관측 사건 순서 위에서 GPU 정확 의미론을 재생해 turn ≥ 1 요청마다 hit token 수를 예측하고, 관측 `cached_tokens`와 대조한다.
- 붕괴 과소 예측(GTASK11 발견 4)이 의미론 오류인지 동역학 오류인지 가른다.

## 배경

- [GTASK11](GTASK11.md): 본 측정 55 lifecycle. sim LRU가 N24·N26 BASE 붕괴를 과소 예측했다(0.752 대 0.669, 0.657 대 0.450).
- NPU [TASK72](../TASK72.md) R5′: 같은 방법(사건 재생, 일치율 ≥ 0.95, 결정 불가 ≤ 5 %)

## 시작 상태

- HEAD `22b50f4`
- `git merge origin/main` → **merge `309871a`**(`origin/main` `235bad2`, TASK83–87, 충돌 없음)

## 수행 내용

1. 선등록 [GPU_REPLAY_PREREG.md](GPU_REPLAY_PREREG.md)를 commit했다(`0973228`, 07:09:00 UTC).
   - commit 전에 본 것은 구조 개수와 vLLM source뿐이다(선등록 머리말).
2. 재생 script `replay.py`를 선등록 뒤에 작성했다.
   - 세션과 분리해 한 번 실행했다(07:11:10 UTC 시작, 6.9 s).
   - 실행 시 script SHA256 `b3931502…`, 판정 후 수정 0
3. `replay_summary.py`로 판정표를 만들었다. §7 반사실 재생 6종의 일치율도 계산했다(판정 밖).

## 변경된 파일

- `docs/research/gpu/GPU_REPLAY_PREREG.md`(선등록 commit), `docs/research/gpu/GTASK12.md`, `docs/research/gpu/GPU_INDEX.md`
- `experiments/gpu/multiturn/replay.py`, `experiments/gpu/multiturn/replay_summary.py`(신규)

## 실험 또는 검증 방법

```bash
D=<abs>/results/gpu/multiturn/main/20260930T1411Z
setsid nohup env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python \
  experiments/gpu/multiturn/replay.py --run-dir $D --out $D/replay/run1.json --jobs 16 &
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python \
  experiments/gpu/multiturn/replay_summary.py --run-dir $D --replay $D/replay/run1.json --out $D/replay/summary.json
```

- `requested_condition`: 선등록 §1–§5. 55 lifecycle, 평가 구간 turn ≥ 1 요청
- `observed_condition`
  - 판정 모집단 16,794건(선등록 §1의 "약 13,600"은 확증 45 lifecycle만 센 추정이었다; 실제 확증 13,885 + 탐색 2,909)
  - `UNKNOWN` 0, `UNDECIDABLE` 0, 모호 해제 0
- `condition_reached`: `YES`

Population: 위 모집단. 보고 모집단(lifecycle 전체 turn ≥ 1)은 23,076건.
Source: server `[GPFX]`·`[GSTEP]` log 순서(입력), client `cached_tokens`(관측), KV events(검증).
Unit: 요청당 hit token 수.
Device scope: GTASK11의 카드 1장(재측정 없음).

## 결과

### 판정: **`PASS`**

- **55/55 lifecycle에서 정확 일치율 1.000**(최소 1.000, 기준 0.95), 결정 불가 비율 0(기준 0.05)
- 판정 모집단 **16,794 / 16,794**, 보고 모집단 23,076 / 23,076 정확 일치
- 불일치 0 → 범주 (i)–(vii) 모두 0

| cell | 판정 모집단 | 정확 일치 | lifecycle 전체 |
|---|---|---|---|
| N20 BASE / POOL / POOL+GRID | 1,517 / 1,538 / 1,543 | 전부 | 2,163 / 2,191 / 2,196 |
| N22 BASE / POOL / POOL+GRID | 1,499 / 1,559 / 1,562 | 전부 | 1,959 / 2,030 / 2,035 |
| **N24 BASE** | **1,477** | **1,477** | 2,073 |
| N24 POOL / POOL+GRID | 1,596 / 1,594 | 전부 | 2,222 / 2,223 |
| **N26 BASE** | **1,366** | **1,366** | 1,888 |
| N26 POOL | 1,543 | 1,543 | 2,096 |

관측 재사용률이 0.450까지 떨어진 N26 BASE도, 0.669인 N24 BASE도 요청 단위로 전부 맞았다.

### 재생 무결성 (§6, 입력으로 쓰지 않은 관측과 비교)

- **free block 수**: `LOOKUP` 27,652 / 27,652, `ALLOC` 27,652 / 27,652 일치(`scheduled`·`computed` 포함)
- **KV events 축출 순서열**: 관측 `BlockRemoved` 958,078건과 재생 축출 958,078건이 **같은 위치에서 전부 같은 `(session, block index)`**. 사상 실패 0
- **`[GSTEP]` (reqs, toks)**: lifecycle마다 2개만 불일치. 두 개 모두 첫 `LOOKUP` 이전에 있는 기동 warmup step이다(GTASK03 G1의 "warmup 2 step"). 요청이 들어온 뒤의 step은 전부 일치했다.

### 반사실 재생의 판별력 (§7 대안, 판정 밖)

판정 모집단 정확 일치율(cell 범위)과 `LOOKUP` free 수 일치율(55 lifecycle 합)이다.

| 재생 | hit 정확 일치 | free 수 일치 |
|---|---|---|
| **주 규칙(§3)** | **1.000** | **1.000** |
| (i) 해제 lag 0 | 1.000 | 0.955 |
| (i) 해제 lag 2 | 1.000 | 0.142 |
| (ii) 할당 후 조회 | 0.816–0.976 | 0.989 |
| (iii) 할당 순서 FIFO | 0.627–0.837 | 0.942 |
| (iv) head 먼저 반납 | 0.915–0.991 | 0.989 |
| (v) prompt만 캐시 | 0.091–0.608 | 0.996 |

- 대안이 틀리는 정도는 포화 cell(N24·N26 BASE)에서 가장 크다. 예를 들어 FIFO는 0.627–0.636, 할당 후 조회는 0.816–0.824다.
- 해제 시점 ±1 step은 hit로는 구별되지 않는다. 그러나 free 수로는 lag 1만 전부 맞는다.

## 핵심 발견

1. **`stack`** — **GPU 정확 의미론이 관측 사건 순서 위에서 요청 단위 hit를 16,794/16,794 재현했다.** free 수 27,652건과 축출 순서열 958,078건까지 같다. 해당 규칙은 해제 순서 LRU, tail-first 반납, 조회 후 할당 + hit 선보호, 생성 token 캐시, null block 1개, async lag 1 해제다. 판정은 `PASS`이고, 선등록 §8에 따라 **GTASK11 발견 4(sim LRU의 붕괴 과소 예측)는 의미론 오류가 아니라 동역학 오류**다.
2. **`class`** — **포화 영역의 재사용 붕괴는 의미론이 아니라 사건 순서가 만든다.** 같은 규칙이 N26 BASE(관측 0.450)를 전부 맞히고, 같은 규칙을 sim 일정 위에서 돌린 sim LRU는 0.657을 냈다. 차이는 전부 사건 순서(어떤 요청이 언제 들어오고 그사이 얼마나 할당되는가)에 있다. `class`인 근거: 축출 규칙이 고정된 용량 제한 캐시에서 hit는 "해제부터 재조회까지의 할당 수"의 함수이므로, 규칙이 맞아도 그 할당 수를 만드는 시간 진행이 틀리면 예측이 틀린다. 구현 상수와 무관한 구조다.
3. **`stack`** — **async scheduling의 해제 시점은 lag 1이다**(batch queue 2, 종료 step e의 반납이 e+2 schedule 앞에 보인다). hit는 ±1 step 해제 차이에 둔감하다(lag 0·2도 1.000). free 수는 lag 1만 전부 맞는다(lag 0 0.955, lag 2 0.142).
4. **`universal`** — **사건 재생 검사는 시간에 의존하는 동역학을 빼고 의미론만 시험한다.** NPU R5′(1,298/1,298)와 GPU(16,794/16,794)에서 모두 통과했다. "예측기가 틀린 원인"을 의미론과 일정으로 나누는 표준 절차로 쓸 수 있다.

## 해석

- 시뮬레이터 오차의 위치가 좁혀졌다. 블록 pool 규칙은 맞으므로, 남는 원인은 시뮬레이터가 만드는 사건 순서다.
  - step 시간(작업 B, [GTASK13](GTASK13.md))
  - client 쪽 지연(요청 간격, 관측에 있고 sim에는 0)
  - 대기열 길이와 admission 시점(작업 C, [GTASK14](GTASK14.md))
- 대안 재생의 차이가 포화 cell에서 커지는 것은, 포화 근처에서 재사용이 "해제부터 재조회까지의 할당 수"에 민감해진다는 뜻이다. 같은 민감도가 동역학 오차를 키운다.

## 확인되지 않은 사항

- 해제 시점 lag 1의 근거는 source와 free 수 일치다. 한 step 안에서 해제가 일어나는 정확한 시각은 log에 없다(판정에 영향 없음).

## 실패 / 무효 시도

- 없음. 첫 실행 결과가 그대로 판정이다. script 수정 0.

## 연구 원칙에 미치는 영향

- 사건 재생이 통과했으므로 GPU 쪽 v1.1·시뮬레이터 개정은 **의미론을 고치지 않는다.** 시간 진행·대기열·client 지연을 다룬다.

## 다음 작업

- G-05 작업 B–E([GTASK13](GTASK13.md)–[GTASK16](GTASK16.md))

## 재현 정보

- **선등록 `0973228d5312f3b891838a6b2c4d0bee7fdcbbf4`(2026-10-01 07:09:00 UTC) → 재생 실행 시작 07:11:10 UTC**(선후 성립)
- 재생 script SHA256 `b39315022a7993173105345cc6477776e992c7248c008c4d710970cfb55af7e9`(실행본 사본 `replay/run1.replay.py`), summary script `01df267a…`
- 입력: `results/gpu/multiturn/main/20260930T1411Z/`(비추적, GTASK11 raw)
- 산출: 같은 디렉터리 `replay/{run1.json, summary.json, run1.log, run1.start, run1.commit}`(비추적)
- 환경: 분석용 python `/home/csdc/kyeom/envs/vllm-0.22.0/bin/python`(Python 3.12.13), vLLM 0.22.0 source(근거 줄은 선등록 §3)
