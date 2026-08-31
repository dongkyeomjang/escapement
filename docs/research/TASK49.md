# TASK49 — 채널 일치 허용차의 사후 민감도 분석

## 상태

DONE

## 날짜

2026-08-31

## 목적

채널 일치 허용차 `τ(N) = max(0.02, r_BASE / B_BASE)`의 기본값 0.02는 **관례값**이며
이론적 유도에 근거하지 않는다(두 번째 항은 [TASK36](TASK36.md)에서 유도됐다). 이
기본값을 0.005 / 0.01 / 0.02 / 0.03 / 0.05로 바꿨을 때 지금까지의 채널 판정이
어떻게 달라지는지를 저장된 측정 자료에서 전수 계산한다.

**이 TASK는 계산만 한다.** 지시에 따라 결과에 대한 평가·해석 문장을 쓰지 않으며,
해석은 Advisor·사용자 몫이다.

## 배경

관련 TASK:

- [TASK34](TASK34.md) — 채널 A(decode 전용)를 선등록했다가 3칸 전부 보류. 채널
  정의 결함의 원본 사례
- [TASK35](TASK35.md) — 채널 A′(decode + prefill)를 선등록. 고정 밴드 0.02로
  N=8 2칸 통과, N=6 2칸 보류
- [TASK36](TASK36.md) — 허용차를 `τ(N) = max(0.02, r_BASE/B_BASE)`로 교정해
  선등록. 두 번째 항의 상한 유도가 여기 있다
- [TASK40](TASK40.md) — 같은 τ 형태로 9칸 전부 통과
- [TASK16](TASK16.md) — 층 태깅 규칙

## 시작 상태

- Git commit: `7354def` (TASK48 종료 시점)
- Branch: `main`, 작업 시작 시 `git status --short`는 `?? .idea/`만
- 새 측정·compile·device 접근 없음. 입력은 아래 4개 run 디렉터리의 기존 artifact뿐

| TASK | run 디렉터리 |
|---|---|
| [TASK34](TASK34.md) | `results/npu/stage2/20260823-170201-compile-config` |
| [TASK35](TASK35.md) | `results/npu/stage2/20260823-183505-final-confirm` |
| [TASK36](TASK36.md) | `results/npu/stage2/20260824-160028-n6-reconfirm` |
| [TASK40](TASK40.md) | `results/npu/stage2/20260824-222453-batch-saturation` |

## 수행 내용

1. 채널 일치 요건이 판정에 선행한 측정을 [INDEX.md](INDEX.md)에서 식별했다 —
   [TASK34](TASK34.md), [TASK35](TASK35.md), [TASK36](TASK36.md),
   [TASK40](TASK40.md). 게이트가 적용된 셀은 **20칸**이다.
2. 재계산 script `channel_tolerance_sensitivity.py`를 작성했다. 채널 계산은
   `config_device.py`의 `channel_a_prime`·`channel_b`를 **그대로 import**하고,
   arm 정의는 `config_device.ARMS`·`batch_curve.ARMS`와 같은지 import 시점에
   assert한다. [TASK34](TASK34.md)의 채널 A는 decode 전용이므로 같은 함수의
   decode 항만 쓴다.
3. 재계산값을 각 TASK 문서의 기록값과 **자동 대조**하도록 script에 넣었다.
   불일치가 있으면 계산 결과를 내지 않고 종료한다.
4. 두 판정 형태를 각각 계산했다 — `fixed`(`차 ≤ 기본값`,
   [TASK34](TASK34.md)·[TASK35](TASK35.md)가 실제 등록한 형태)와 `tau`
   (`차 ≤ max(기본값, r_BASE/B_BASE)`, [TASK36](TASK36.md)·[TASK40](TASK40.md)가
   등록한 형태). τ 형태는 [TASK36](TASK36.md)에서 도입됐으므로 앞의 두 TASK
   시점에는 존재하지 않았고, 그래서 한 형태만 계산하면 앞 두 TASK의 원 판정을
   재현할 수 없다.
5. 기본값 5개 × 20칸 × 2형태 = **200 판정**을 전수 계산하고, 0.02 대비 뒤집히는
   셀과 원본 보류 셀의 전환 기본값을 목록으로 냈다.
6. 결과를 [CHANNEL_TOLERANCE_SENSITIVITY.md](CHANNEL_TOLERANCE_SENSITIVITY.md)에
   정리했다. 문서 머리에 사후 민감도 확인이며 판정의 재산출이 아님을 명시했다.

## 변경된 파일

- `experiments/npu/analysis/channel_tolerance_sensitivity.py` (신규)
- `docs/research/CHANNEL_TOLERANCE_SENSITIVITY.md` (신규)
- `docs/research/TASK49.md` (신규)
- `docs/research/INDEX.md` (갱신)

기존 TASK 문서의 판정은 **수정하지 않았다.**

## 실험 또는 검증 방법

측정 없음. 검증은 재현 대조 하나다 — script가 저장 artifact에서 다시 계산한
20칸의 A비·B비 40개와 문서가 인쇄한 잔차비 4건을 TASK 문서 기록값과 비교하고,
차이가 A비·B비 5e-4 또는 잔차비 1e-3을 넘으면 종료한다.

## 결과

- `requested_condition` — 기본값 5개 × 20칸 × 2형태 전수 계산
- `observed_condition` — 20칸 전부 계산됨, 대조 44건 전부 일치
- `condition_reached` — `YES`

### 재현 대조 — 44/44 일치

A비·B비 40개가 소수 넷째 자리까지 정확히 일치하고(최대 차 0.0000), 잔차비 4건도
일치한다(최대 차 0.0004, 문서가 소수 셋째 자리로 인쇄한 데서 온 차).

### 기본값별 (통과 / 보류)

| 기본값 | `fixed` | `tau` |
|---|---|---|
| 0.005 | 13 / 7 | 20 / 0 |
| 0.010 | 15 / 5 | 20 / 0 |
| **0.020 (원본)** | **15 / 5** | **20 / 0** |
| 0.030 | 18 / 2 | 20 / 0 |
| 0.050 | 18 / 2 | 20 / 0 |

### 뒤집히는 셀 — 0.02 대비

`tau` 형태: **없음.** 0.005–0.05 전 범위에서 20칸 판정이 모두 같다.

`fixed` 형태: 8건(셀 5개).

| 기본값 | 셀 | 방향 | 차 |
|---|---|---|---|
| 0.005 | TASK36·N6·`TUNED` | 통과 → 보류 | 0.0063 |
| 0.005 | TASK40·N6·`B32` | 통과 → 보류 | 0.0068 |
| 0.030 · 0.050 | TASK34·N6·`TUNED` | 보류 → 통과 | 0.0221 |
| 0.030 · 0.050 | TASK35·N6·`BATCHONLY` | 보류 → 통과 | 0.0205 |
| 0.030 · 0.050 | TASK35·N6·`TUNED` | 보류 → 통과 | 0.0236 |

0.010에서 뒤집히는 셀은 없다.

### 원본 보류 셀이 통과로 바뀌는 기본값

| 셀 | 차 | 최소 기본값 |
|---|---|---|
| TASK34·N6·`TUNED` | 0.0221 | **0.030** |
| TASK34·N8·`TUNED` | 0.0908 | 이 범위(≤0.05)에 없음 |
| TASK34·N10·`TUNED` | 0.0700 | 이 범위(≤0.05)에 없음 |
| TASK35·N6·`BATCHONLY` | 0.0205 | **0.030** |
| TASK35·N6·`TUNED` | 0.0236 | **0.030** |

같은 5칸을 `tau` 형태로 계산하면 원본 기본값 0.02에서 이미 전부 통과다 — 각 셀의
`r_BASE/B_BASE`가 0.0607([TASK35](TASK35.md) N=6) 및 0.2553–0.3371
([TASK34](TASK34.md))이기 때문이다.

### `tau` 형태에서 기본값이 허용차를 정하는 셀 수

| 기본값 | 구속 | 미구속 |
|---|---|---|
| 0.005 · 0.010 · 0.020 · 0.030 | 0 | 20 |
| 0.050 | 15 | 5 |

20칸의 최소 `r_BASE/B_BASE`는 0.0356([TASK40](TASK40.md) N=6)이다.

전체 표(셀별 채널 값, 여유 = 허용차 − 차)는
[CHANNEL_TOLERANCE_SENSITIVITY.md](CHANNEL_TOLERANCE_SENSITIVITY.md)에 있다.

## 핵심 발견

1. **`universal` — 판정 임계값의 민감도는 판정과 같은 코드 경로로 계산할 수
   있고, 그렇게 하면 재현 대조가 공짜로 따라온다.** 채널 계산을
   `config_device.py`에서 import했기 때문에 20칸 40개 값이 기록과 정확히 일치하는
   것이 자동으로 확인됐다. 대조를 통과하지 못하면 민감도 수치를 내지 않는다.
2. **`universal` — 한 프로그램 안에서 판정 형태가 바뀌었다면 민감도는 형태별로
   따로 계산해야 원 판정을 재현한다.** τ 형태는 [TASK36](TASK36.md)에서 생겼고
   [TASK34](TASK34.md)·[TASK35](TASK35.md)에는 없었다. 20칸에 τ 형태 하나만
   적용하면 앞 두 TASK의 보류 5칸이 계산상 사라지므로 그것은 민감도가 아니라
   기준의 소급 적용이 된다.
3. **`stack` — 이 substrate에서 관측된 `r_BASE/B_BASE`는 채널 A′ 17칸에서
   0.0356–0.0607이고, decode 전용 채널 3칸에서 0.2553–0.3371이다.** 값은 이
   stack의 오버헤드 구조에 딸린 상수이므로 `class`로 이식하지 않는다.

## 해석

**없음.** 이 TASK는 지시에 따라 계산만 수행한다. 위 수치에 대한 평가와 판단은
Advisor·사용자 몫이다.

## 확인되지 않은 사항

- 기본값 0.02가 어떤 근거로 정해졌는지는 이 저장소의 기록에서 확인되지 않는다.
  최초 등록은 [POLICY_DEVICE_PREREG.md](POLICY_DEVICE_PREREG.md)
  ([TASK28](TASK28.md))의 "두 채널의 busy ratio 차이가 0.02를 넘으면 그 N의
  판정을 보류한다"이며, 그 문장에도 0.02의 유도는 없다. **`UNKNOWN`.**
- 이 분석은 0.005–0.05 범위만 계산했다. 그 밖의 기본값에서의 판정은 계산하지
  않았다.
- [TASK34](TASK34.md)의 `r/B`(0.2553–0.3371)에 τ 형태를 적용하는 것이 타당한지는
  판단하지 않았다. 수치만 계산해 두었다.

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

없음. 저장소 규칙 17(동치 판정은 고정 밴드가 아니라 bootstrap CI)은 그대로이며,
채널 일치 요건은 동치 판정이 아니라 두 관측 채널의 합치 확인이므로 그 규칙의
대상이 아니다. 기존 판정도 전부 그대로다.

## 다음 작업

제안만 한다. 사용자 지시 없이 실행하지 않는다.

1. 이 수치를 논문 한계 절 또는 부록에 어떤 형태로 넣을지 결정 — 지금은 저장소
   문서로만 있다.
2. 기본값 0.02의 근거가 `UNKNOWN`인 사실을 논문에 적을지 결정.

## 재현 정보

- 선등록 commit: **해당 없음** — 새 측정이 없는 사후 재분석이다. 원 판정은 각
  TASK의 선등록에 따라 이미 확정됐고 이 TASK는 그것을 바꾸지 않는다.
- 시작 commit: `7354def`
- 분석: `env -u PYTHONPATH python3 experiments/npu/analysis/channel_tolerance_sensitivity.py --output results/npu/stage2/channel_tolerance_sensitivity.json`
- 입력 artifact: 위 4개 run 디렉터리의 `util.*.json`, `probe/requests.*.jsonl`
- 산출 artifact: `results/npu/stage2/channel_tolerance_sensitivity.json`
  (`results/`는 `.gitignore` 대상이므로 commit되지 않는다)
- Python: 시스템 `python3`, `vllm 0.22.0+cpu` / `vllm-rbln 0.11.1` 환경. device
  접근 없음
