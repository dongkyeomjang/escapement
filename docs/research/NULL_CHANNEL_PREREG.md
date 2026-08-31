# 선등록 — 무처치 반복 측정에 의한 채널 일치 null 분포

이 문서는 측정 **시작 전에** commit한다. 아래의 실험 격자, 산출 정의, 비교 기준,
예측, 무효 규칙은 측정 후에 바꾸지 않는다. 결과를 보고 완화하지 않으며, 완화가
불가피하면 원 기준의 실패를 함께 보고한다.

## 목적

채널 일치 허용차 `τ(N) = max(0.02, r_BASE / B_BASE)`에서 하한 0.02는 유도가 없는
관례값이다([TASK49](TASK49.md)에서 확인 — 최초 등록인
[POLICY_DEVICE_PREREG.md](POLICY_DEVICE_PREREG.md)에도 근거가 없다). 두 번째 항만
[TASK36](TASK36.md)에서 유도됐다.

허용차가 포괄해야 할 대상 — **처치가 전혀 없을 때 두 채널이 실제로 얼마나
어긋나는가** — 은 이 저장소에서 한 번도 측정된 적이 없다. 이 TASK는 그 null 분포를
측정하고 τ(N)과 **병치**한다.

**이 TASK는 기존 판정을 재산출하지 않고 τ를 개정하지 않는다.** τ 개정이 필요하다는
판단이 서면 그것은 결과가 아니라 별도 결정 항목으로 보고한다.

## 실험 격자

처치 없음. 조건 하나, N 둘, N당 같은 trace 10회 반복.

| 항목 | 값 |
|---|---|
| Model artifact | `models/Qwen3-4B-rbln-b8-s8192-d4-mb` (재compile 없음) |
| 컴파일 bucket 집합 𝓑 | `{1, 2, 4, 8}` |
| `batch_size` | 8 |
| N | 6, 8 |
| N당 반복 | **10회** (매회 서버 새로 기동·종료) |
| 총 serving lifecycle | **20회** (승인 20~30회) |
| plan seed | N=6 → **`20261300`**, N=8 → **`20261400`** (기존 사용 seed와 겹치지 않음) |
| `block_id` (고정) | N=6 → `null6`, N=8 → `null8` |
| sampling seed | `20260819` (기존과 동일) |
| turns / 세그먼트 / 생성 | `--turns 2`, `--first-segment uniform:800:1600`, `--later-segment fixed:8`, `--generation uniform:32:256` |
| gap | `toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60` ([TASK36](TASK36.md)·[TASK40](TASK40.md)과 동일) |
| return policy | `immediate`, budget 0 |

**반복의 정의**: `block_id`를 고정해 **같은 trace**를 다시 실행한다. `block_id`가
plan seed와 함께 세션 계획을 결정하므로(`derive_block_seed`), 이것을 고정하지 않으면
반복이 아니라 새 trace가 된다. 이를 위해 `run_sweep.sh`에 `SWEEP_BLOCK_ID` 환경
변수 override를 추가한다 — 설정하지 않으면 기존 동작과 완전히 같다.

**실행 순서**: 시간에 따른 표류가 한쪽 N에만 실리지 않도록 **N을 번갈아** 실행한다.

```
(N=6, r0) → (N=8, r0) → (N=6, r1) → (N=8, r1) → … → (N=6, r9) → (N=8, r9)
```

## 산출 정의

각 반복 `i`에서 두 채널을 [`config_device.py`](../../experiments/npu/analysis/config_device.py)의
함수로 그대로 계산한다.

- **채널 A′** = `[BUCKET]` step 열 × [TASK13](TASK13.md) decode 비용 + 실제 계산
  prefill token × [TASK22](TASK22.md) `PrefillCostModel`
- **채널 B** = client `sent_s`/`done_s`의 in-flight 구간 합집합 (모형 무의존)
- **잔차** `r_i = B_i − A′_i`

유효한 반복 전체에서 순서쌍이 아닌 **모든 조합** `i < j`에 대해

```
gap(i, j) = | A′_i / A′_j  −  B_i / B_j |
```

를 계산한다. 10회 → **45쌍**. 이것이 "처치 없는 두 실행 사이의 채널 비 차이"의
경험적 분포다.

**분위수 규약(선등록)**: nearest rank. 오름차순 정렬 후 `sorted[ceil(0.95 × n) − 1]`.
45쌍이면 43번째로 작은 값이다. 다른 규약으로 바꾸지 않는다.

함께 보고할 것:

- `r_i`와 `r_i / B_i`의 분포 (최솟값·중앙값·최댓값)
- 각 채널 절대값의 실행 간 변동 — 평균, 표준편차, CV, `(최대−최소)/평균` (부수 정보)

## 비교 기준 (선등록, 결과를 보고 바꾸지 않는다)

null 분포에서 τ 형태가 산출할 허용차를 정의한다. null run에는 BASE/arm 구분이
없으므로 두 번째 항을 반복들의 중앙값으로 잡는다.

```
τ_null(N) = max(0.02, median_i( r_i / B_i ))
```

95 분위수 `q95`를 이 두 값과 병치해 아래 셋 중 하나로 **분류**한다. 이것은
분류이지 기존 TASK에 대한 판정이 아니다.

| 분류 | 조건 | 뜻 |
|---|---|---|
| **C1** | `q95 ≤ 0.02` | 현행 하한 0.02가 무처치 변동의 95 분위수를 포괄한다 |
| **C2** | `0.02 < q95 ≤ τ_null(N)` | 하한 0.02만으로는 포괄되지 않고 τ 형태가 포괄한다 |
| **C3** | `q95 > τ_null(N)` | 허용차가 무처치 변동보다 좁다 |

병치 대상으로 함께 인쇄할 기존 값: [TASK36](TASK36.md)의 `τ(6) = 0.0377`,
[TASK40](TASK40.md)의 `τ(6) = 0.0356` · `τ(8) = 0.0400`.

## 예측 (선등록)

측정 전 예측이며 빗나가면 빗나간 대로 보고한다.

| # | 예측 | 근거 |
|---|---|---|
| **P1** | 두 N 모두 `중앙값 ≤ 0.010` | 확증된 셀들의 실측 채널 차가 0.0001–0.0068이었다([TASK36](TASK36.md)·[TASK40](TASK40.md)). 처치가 있는데도 그 정도면 무처치는 그보다 크지 않을 것으로 본다 |
| **P2** | 두 N 모두 `q95 ≤ 0.025` | 위와 같은 근거. 꼬리를 두 배 이상 잡아 둔다 |
| **P3** | `median(r_i / B_i)`가 0.030–0.050 | [TASK35](TASK35.md)·[TASK36](TASK36.md)·[TASK40](TASK40.md)이 관측한 0.036–0.046과 같은 자릿수일 것으로 본다 (N=8이 N=6보다 클 것) |
| **P4** | 분류가 **C1 또는 C2** (즉 `q95 ≤ τ_null`) | P2 + P3의 결합 |
| **P5** | 채널 B의 CV가 채널 A′의 CV보다 크다 | B는 queueing·HTTP·스케줄러 오버헤드를 포함하고 A′는 비용 모형으로 그 부분을 통과시키지 않는다 |

## 불변식과 무효 규칙 (선등록)

- 조합마다 [`utilization.py`](../../experiments/npu/analysis/utilization.py)로 기존
  불변식 P1–P3·I1–I5를 검사한다. 위반한 반복은 `INVALID`로 **제외하고 번호와 위반
  내용을 명시**한다. 관측 불가 field를 0으로 채우지 않는다.
- 어느 N의 **유효 반복이 8회 미만**이면 그 N은 `INVALID`로 보고하고 분포를 산출하지
  않는다. 8회 미만에서 분위수를 내지 않는다.
- 서버 기동 실패·health timeout은 실패로 기록하고 같은 반복 번호로 재시도한다.
  재시도 횟수를 보고한다.
- 반복 간 model artifact·patch·구성은 변경하지 않는다. 측정 전후로
  `apply.sh status`의 SHA256을 기록한다.

## 판정 구현

[`experiments/npu/analysis/null_channel.py`](../../experiments/npu/analysis/null_channel.py)를
이 선등록과 **같은 commit에** 고정한다. 분위수 규약, `τ_null` 정의, C1/C2/C3 분류,
`MIN_VALID = 8`이 코드에 들어 있다.

```
env -u PYTHONPATH python3 experiments/npu/analysis/null_channel.py \
    --run <RUN> --sessions 6,8 --output <RUN>/null_channel.json
```

## 예산

- 재compile **0회** (금지 항목)
- serving lifecycle **20회** / 승인 20~30회
- `models/` 증가 **0 GiB**
- patch 변경 없음. `apply.sh status`는 `patched`, SHA256
  `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`를 유지한다
