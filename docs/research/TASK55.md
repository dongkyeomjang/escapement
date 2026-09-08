# TASK55 — 개입 격자의 step 비용 실측과 device time 검증

## 상태

PARTIAL

`PARTIAL`인 이유: 선등록 5개 판정 중 **P1·P3은 `PASS`, P2a·P2b·P2c는 `FAIL`** 이다.
P2의 실패는 "재compile이 기존 bucket의 비용을 바꿨다"는 뜻이 아니라 **선등록 밴드가
포괄해야 할 분산 성분을 잘못 골랐다**는 뜻으로 보이며(아래 해석), 그 판별에 필요한
반복 측정을 이번 예산에서 하지 않았다.

## 판정

선등록 문서: [GRID_STEP_COST_PREREG.md](GRID_STEP_COST_PREREG.md) (commit `1215579`,
2026-09-08T15:11:12+09:00). **측정 시작 15:12:22 — 선등록 이후 70초.**

| # | 예측 | 결과 | 판정 |
|---|---|---|---|
| **P1** | `mb6`의 `C_model`이 bucket 순 단조 증가 | 9.52 → 10.08 → 10.37 → **11.15** → 12.36 ms | **`PASS`** |
| **P2a** | 공유 bucket 4개에서 `|ΔC_model| ≤ 0.03 ms` | 1/4만 통과 (b2 −0.29, b4 +0.09, b8 +0.08) | **`FAIL`** |
| **P2b** | 공유 bucket 4개에서 `|ΔC_fixed| ≤ 0.06 ms` | 1/4만 통과 (b2 −0.49, b4 +0.09, b8 +0.07) | **`FAIL`** |
| **P2c** | 채널 C 중앙 ITL 비가 `1 ± 0.005` | 2/4 통과 (b2 0.9343, b4 1.0070) | **`FAIL`** |
| **P3** | 8개 조건 짝 전부 채널차 `≤ τ(N)` | **8/8 통과** (고정 0.02 기준으로는 6/8) | **`PASS`** |

**판정 기준을 측정 후에 완화하지 않았다.** P2의 밴드 0.03/0.06 ms는 선등록대로
[TASK13](TASK13.md)의 bucket 내 관측 범위에서 유도한 값이며, 실패를 그대로 보고한다.

**핵심 수치**: `C(6)` 실측 `C_fixed` = **11.660 ms**, 보간값 11.8975 ms 대비
**−0.238 ms (−2.00 %)**. 선형 보간이 **과대평가**했다.

## 날짜

2026-09-08

## 목적

[TASK54](TASK54.md)가 격자 → padding의 인과를 동일 trace로 확정하면서 남긴 세 구멍을
닫는다. (1) 개입 격자의 `C(6)`이 보간값이고, (2) 재compile이 기존 bucket의 실행 비용을
바꾸지 않았다는 통제 확인이 없으며, (3) padding → device time 환산이 무모형 채널과
대조된 적이 없다.

## 배경

관련 TASK:

- [TASK13](TASK13.md) — `C(1,2,4,8)` 원 측정. 방법과 변동 기준의 출처
- [TASK54](TASK54.md) — 검증 대상 배치(24칸). `prefill.rbln` 바이트 차이를 `UNKNOWN`으로 남겼다
- [TASK52](TASK52.md) / [PADDING_RATIO.md](PADDING_RATIO.md) — 보간 `C(6)`의 한계 기록
- [TASK26](TASK26.md) — device time 관측 4
- [TASK36](TASK36.md) / [TASK40](TASK40.md) — `τ(N) = max(0.02, r_BASE/B_BASE)` 유도와 사용례
- [TASK22](TASK22.md) — prefill 비용 모형

## 시작 상태

- 선등록 commit `1215579`, 직전 `63e67f3`
- `git status --short`: `?? .idea/`만
- Substrate: `patched`, SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`
  — 측정 전후 덤프 무차이
- Model artifact 2종, **재compile 없음**. manifest hash가 [TASK54](TASK54.md) 기록과
  **일치**함을 측정 전에 확인: `mb` `b4f5cbf1…f5f`, `mb6` `348f2863…4bf`
- 32 NPU 전부 idle, `/` 사용률 17 % (측정 전후 동일)

## 수행 내용

1. [TASK13](TASK13.md)의 `decode_cost_probe.py`를 **수정 없이** 쓰고, artifact와
   level 집합만 바꾸는 구동 script를 만들었다.
2. METRICS 파서를 [TASK13](TASK13.md)의 저장 로그 8개로 **선등록 전에 검증**했다 —
   8/8이 [TASK13](TASK13.md) 표와 일치.
3. 선등록 문서·구동 script·판정 script를 **측정 전에 같은 commit**(`1215579`)으로
   고정했다.
4. `mb` 4 level + `mb6` 5 level = **9 serving lifecycle**을 선등록 순서대로 실행했다.
5. [TASK54](TASK54.md)의 저장 step 열에 실측 `C`를 적용해 채널 A′를 다시 만들고
   채널 B와 8개 짝에서 대조했다.

## 변경된 파일

- `docs/research/GRID_STEP_COST_PREREG.md` (선등록, 측정 전 commit)
- `experiments/npu/stage2/run_step_cost.sh` (구동, 측정 전 commit)
- `experiments/npu/analysis/grid_step_cost.py` (판정, 측정 전 commit)
- `docs/research/TASK55.md` (신규)
- `docs/research/INDEX.md` (갱신)

[TASK13](TASK13.md)·[TASK54](TASK54.md)의 수치와 판정, `descriptor.py`의
`_FIXED_S_BY_BUCKET`은 **고치지 않았다.** substrate descriptor의 갱신 여부는 아래
「다음 작업」의 제안 사항이다.

## 실험 또는 검증 방법

```bash
RUN=results/npu/stage2/20260908-151119-step-cost
bash experiments/npu/stage2/run_step_cost.sh "$RUN"          # 9 lifecycle
env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py \
    --run "$RUN" --task54-run results/npu/stage2/20260908-133635-grid-paired \
    --output "$RUN/grid_step_cost.json"
```

실행 순서는 `balanced_arm_orders(9구성, rounds=1, base_seed=20260955,
block_id="task55-order")`이며 선등록 문서의 표와 실제 `order.txt`가 일치한다:
`mb.L8 → mb6.L2 → mb.L4 → mb6.L1 → mb.L2 → mb6.L8 → mb6.L6 → mb6.L4 → mb.L1`.

`requested_condition` / `observed_condition` / `condition_reached`:

| 항목 | requested | observed | reached |
|---|---|---|---|
| level 수 | 9 | 9 | `YES` |
| serving lifecycle | 9 | **9** (재실행 0) | `YES` |
| 재compile | **0** | 0 | `YES` |
| artifact 동일성 | TASK54와 같은 manifest | **2/2 일치** | `YES` |
| level당 decode step | 511 | **9/9 전부 511** | `YES` |
| 사상 (level → bucket) | 1,2,4,(6),8 | **9/9 기대와 일치** | `YES` |
| patch 상태 | 측정 전후 동일 | 동일 | `YES` |

## 결과

### 관측 1 — 게이트

| 게이트 | 결과 |
|---|---|
| G1 status 200 · chunk 512 | **9/9 통과** |
| G2 `[BUCKET]` 511줄 · `request_nums` 단일값 · 기대 bucket | **9/9 통과.** `mb6`에서 L6 → **bucket 6** 확인 |
| G4 patch SHA256 전후 | **무차이** |
| G5 채널 D ≈ 채널 C | **9/9에서 차이 ≤ 0.0025 ms** — 채널 C가 client threading에 오염되지 않았다 |

### 관측 2 — `C(bucket)` 실측 (원시값, ms)

| 격자 | level | bucket | `C_model` p50 | `C_sampler` p50 | **`C_fixed`** | ITL 중앙 | ITL 평균(C) | ITL 평균(D) |
|---|---|---|---|---|---|---|---|---|
| `mb` | 1 | 1 | 9.49 | 0.36 | 9.850 | 10.345 | 10.364 | 10.365 |
| `mb` | 2 | 2 | **10.37** | **0.57** | **10.940** | 11.863 | 11.634 | 11.633 |
| `mb` | 4 | 4 | 10.28 | 0.45 | 10.730 | 11.390 | 11.460 | 11.458 |
| `mb` | 8 | 8 | 12.28 | 0.57 | 12.850 | 13.762 | 13.949 | 13.946 |
| `mb6` | 1 | 1 | 9.52 | 0.36 | 9.880 | 10.392 | 10.407 | 10.408 |
| `mb6` | 2 | 2 | 10.08 | 0.37 | 10.450 | 11.084 | 11.263 | 11.264 |
| `mb6` | 4 | 4 | 10.37 | 0.45 | 10.820 | 11.470 | 11.556 | 11.555 |
| **`mb6`** | **6** | **6** | **11.15** | **0.51** | **11.660** | 12.419 | 12.663 | 12.661 |
| `mb6` | 8 | 8 | 12.36 | 0.56 | 12.920 | 13.698 | 13.893 | 13.891 |

### 관측 3 — `C(bucket)` 전후 비교표 (파트 4-1)

| bucket | `mb` `C_model` | `mb6` `C_model` | **Δ** | 밴드 0.03 | `mb` `C_fixed` | `mb6` `C_fixed` | **Δ** | 밴드 0.06 | ITL 중앙비 | 밴드 ±0.005 | [TASK13](TASK13.md) `C_model` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 9.49 | 9.52 | **+0.03** | `ok` | 9.850 | 9.880 | +0.030 | `ok` | 1.0046 | `ok` | 9.510 |
| 2 | **10.37** | 10.08 | **−0.29** | **`OUT`** | 10.940 | 10.450 | **−0.490** | **`OUT`** | **0.9343** | **`OUT`** | 10.050 |
| 4 | 10.28 | 10.37 | **+0.09** | **`OUT`** | 10.730 | 10.820 | +0.090 | **`OUT`** | 1.0070 | **`OUT`** | 10.355 |
| 8 | 12.28 | 12.36 | **+0.08** | **`OUT`** | 12.850 | 12.920 | +0.070 | **`OUT`** | 0.9953 | `ok` | 12.402 |
| **6** | — | **11.15** | — | — | — | **11.660** | — | — | — | — | 보간 **11.8975** (`C_fixed`) |

보조 bootstrap (채널 C, resamples 2,000, CI 폭 상한 0.10): 4 bucket 전부
`DIFFERENT`이며 CI 폭은 0.0011–0.0245다. **선등록대로 이것을 P2 기각 근거로 쓰지
않는다** — [TASK13](TASK13.md)이 이미 "표본이 수천이면 0.1 % 차이도 CI가 1을
배제한다"를 보였다.

### 관측 4 — 제3의 측정과의 대조 (같은 artifact, 다른 날)

[TASK13](TASK13.md)은 **`mb` artifact**를 2026-08-19에 쟀다. 이번 두 값과 나란히 둔다.

| bucket | [TASK13](TASK13.md) `mb` (08-19) | 이번 `mb` (09-08) | 차 | 이번 `mb6` (09-08) | `mb6` − [TASK13](TASK13.md) |
|---|---|---|---|---|---|
| 1 | 9.510 | 9.49 | −0.02 | 9.52 | **+0.01** |
| 2 | 10.050 | **10.37** | **+0.32** | 10.08 | **+0.03** |
| 4 | 10.355 | 10.28 | −0.08 | 10.37 | **+0.01** |
| 8 | 12.402 | 12.28 | −0.12 | 12.36 | **−0.04** |

- **같은 artifact(`mb`)의 session 간 차이 최대 0.32 ms**
- **다른 artifact(`mb6`)와 [TASK13](TASK13.md) `mb`의 차이 최대 0.04 ms**
- 선등록 밴드 **0.03 ms**는 [TASK13](TASK13.md)의 **session 안 level 간** 범위에서
  유도한 값이다

### 관측 5 — `mb.L2` 세션의 분포 이상

| 조건 | `C_model` mean | p50 | p90 | p99 | max | `C_sampler` mean | p50 |
|---|---|---|---|---|---|---|---|
| `mb.L2` | 10.28 | **10.37** | 10.46 | 10.74 | 14.05 | 0.51 | **0.57** |
| `mb6.L2` | 10.12 | 10.08 | 10.43 | 10.51 | 11.04 | 0.41 | 0.37 |

`mb.L2`는 **mean < p50**(model 10.28 < 10.37, sampler 0.51 < 0.57)이다. 나머지 8개
level은 전부 mean ≥ p50이다. 단봉 분포에서는 잘 나오지 않는 형태다.

### 관측 6 — 채널 A′/B와 조건 짝 (파트 3)

3반복 합산. 채널 A′는 **이번 실측 `C`**로 만들었다.

| 격자 | N | arm | A′ (s) | decode | prefill | B (s) | `r = B−A′` | `r/B` |
|---|---|---|---|---|---|---|---|---|
| `mb` | 6 | AGENTIC | 28.351 | 22.750 | 5.602 | 29.416 | 1.065 | 0.0362 |
| `mb` | 6 | CONVENTIONAL | 20.604 | 15.760 | 4.844 | 21.588 | 0.984 | 0.0456 |
| `mb` | 8 | AGENTIC | 32.969 | 24.199 | 8.770 | 34.940 | 1.972 | 0.0564 |
| `mb` | 8 | CONVENTIONAL | 25.406 | 15.607 | 9.799 | 27.212 | 1.806 | 0.0664 |
| `mb6` | 6 | AGENTIC | 28.013 | 21.963 | 6.049 | 29.671 | 1.659 | 0.0559 |
| `mb6` | 6 | CONVENTIONAL | 19.855 | 15.011 | 4.844 | 20.849 | 0.994 | 0.0477 |
| `mb6` | 8 | AGENTIC | 32.804 | 23.454 | 9.350 | 34.442 | 1.638 | 0.0476 |
| `mb6` | 8 | CONVENTIONAL | 25.214 | 15.415 | 9.799 | 26.295 | 1.081 | 0.0411 |

잔차 `r`은 0.98–1.97 s로 [TASK35](TASK35.md)가 관측한 1.2–1.7 s와 같은 자릿수다.

| 짝 | 라벨 | A′비 | B비 | **차** | `τ(N)` | 판정 | 고정 0.02 |
|---|---|---|---|---|---|---|---|
| arm | `mb`.n6 | 1.3760 | 1.3626 | 0.0134 | 0.0456 | **통과** | 통과 |
| arm | `mb`.n8 | 1.2977 | 1.2840 | 0.0136 | 0.0664 | **통과** | 통과 |
| arm | `mb6`.n6 | 1.4109 | 1.4231 | 0.0123 | 0.0477 | **통과** | 통과 |
| arm | `mb6`.n8 | 1.3010 | 1.3098 | 0.0088 | 0.0411 | **통과** | 통과 |
| 격자 | n6.AGENTIC | 0.9881 | 1.0087 | 0.0206 | 0.0362 | **통과** | 초과 |
| 격자 | n6.CONVENTIONAL | 0.9636 | 0.9658 | 0.0021 | 0.0456 | **통과** | 통과 |
| 격자 | n8.AGENTIC | 0.9950 | 0.9857 | 0.0093 | 0.0564 | **통과** | 통과 |
| 격자 | n8.CONVENTIONAL | 0.9924 | 0.9663 | 0.0261 | 0.0664 | **통과** | 초과 |

**8/8 통과.** 고정 하한 0.02만으로는 6/8이다.

### 관측 7 — 격자 × {Δpadding, Δdevice time} 요약표 (파트 4-2)

`Δpadding`은 [TASK54](TASK54.md)의 pooled `Δp = p_CONV − p_AGENTIC`을 **인용**한
것이고(재산출 아님), `Δdevice time`은 이번 실측 `C`로 만든 decode device time 비
`A/C`다([TASK26](TASK26.md)·[TASK53](TASK53.md)의 `busy 비`와 같은 정의).

**N = 6**

| 격자 | Δpadding (`Δp`) | Δdevice (`A/C`, 실측 `C`) | (보간 `C`) | 차 |
|---|---|---|---|---|
| `(1,2,4,8)` | **+0.0650** | **1.4435** | 1.4289 | +0.0146 |
| `(1,2,4,6,8)` | **−0.0400** | **1.4632** | 1.4524 | +0.0108 |

**N = 8**

| 격자 | Δpadding (`Δp`) | Δdevice (`A/C`, 실측 `C`) | (보간 `C`) | 차 |
|---|---|---|---|---|
| `(1,2,4,8)` | **−0.0570** | **1.5505** | 1.5342 | +0.0163 |
| `(1,2,4,6,8)` | **−0.0554** | **1.5215** | 1.5174 | +0.0041 |

**두 지표의 부호가 어긋나는 칸이 N=6의 `(1,2,4,8)` 한 칸**이다 — padding은 AGENTIC이
유리한데(`Δp` > 0) device time은 AGENTIC이 44 % 더 쓴다. [TASK53](TASK53.md)이
3.1절 표에서 본 반전이 개입 배치에서도 같은 모양으로 나타난다.

### 관측 8 — 사후 진단: 비용표 3종의 민감도 (판정 아님)

`interp`(보간), `measured`(이번 실측, 등록된 것), `hybrid`([TASK13](TASK13.md)의
공유 bucket + 이번 실측 `C(6)`).

| 격자 | N | 보간 | 실측(등록) | 혼합 | 실측−혼합 |
|---|---|---|---|---|---|
| `mb` | 6 | 1.4289 | 1.4435 | 1.4289 | +0.0146 |
| `mb` | 8 | 1.5342 | 1.5505 | 1.5342 | +0.0163 |
| `mb6` | 6 | 1.4524 | 1.4632 | 1.4625 | +0.0007 |
| `mb6` | 8 | 1.5174 | 1.5215 | 1.5184 | +0.0030 |

**보간 `C(6)`을 실측으로 갈아끼운 효과만 떼면** N=6에서 1.4524 → 1.4625(**+0.0101**),
N=8에서 1.5174 → 1.5184(**+0.0010**)다. `C(6)`의 −2.00 % 보간 오차가 device 비를
**0.7 % 이하** 움직인다.

bucket별 step 점유율(3반복 합산)이 이유를 보여준다. `mb6` N=6에서 bucket 6은
AGENTIC 12.4 %, CONVENTIONAL 47.3 %이고, N=8에서는 AGENTIC 12.0 %,
CONVENTIONAL 16.8 %다.

## 핵심 발견

1. **`silicon` — 개입 격자의 `C(6)`은 `C_fixed` 11.660 ms이며 선형 보간이 2.00 %
   과대평가했다.** `C(4)` 10.820과 `C(8)` 12.920 사이의 중점은 11.8975인데 실측은
   그보다 0.238 ms 아래다. `[4, 8]` 구간에서 비용은 batch 폭에 대해 **위로 볼록하지
   않다** — 중점이 현(chord) 아래에 있다. 절대값은 이 하드웨어·모델 고유다.

2. **`universal` — 선등록 밴드가 포괄해야 할 분산 성분을 잘못 골라 P2가 기각됐다.**
   밴드 0.03 ms는 [TASK13](TASK13.md)의 **한 session 안에서 level을 바꿔 가며** 관측한
   범위다. 이번에 관측된 **session 간** 변동은 같은 artifact에서도 최대 0.32 ms로 한
   자릿수 크다. **"같은 조건을 여러 번 재서 얻은 범위"와 "한 번의 실행 안에서 얻은
   범위"는 다른 양이며, 재현성 밴드는 전자에서 나와야 한다.** 이것은
   [TASK50](TASK50.md)이 τ 하한에 대해 제기한 것과 같은 종류의 문제다.

3. **`stack` — 재compile이 기존 bucket의 실행 비용을 바꿨다는 증거는 없다(해석).**
   제3의 측정([TASK13](TASK13.md)의 `mb`, 3주 전)과 대조하면 **`mb6`가 네 공유 bucket
   전부에서 0.04 ms 안**으로 맞고, 오히려 **이번 `mb`가 bucket 2에서 0.32 ms 벗어난다.**
   이상치는 artifact가 아니라 `mb.L2` 세션이다. **다만 P2는 선등록대로 `FAIL`이며 이
   대조는 사후 진단이다.**

4. **`stack` — 실측 `C`로 만든 채널 A′가 무모형 채널 B와 8/8에서 `τ(N)` 안에 든다.**
   arm 짝 4개(차 0.0088–0.0136)와 격자 짝 4개(0.0021–0.0261)가 전부 통과했다. 잔차
   `r/B`는 0.036–0.066으로 [TASK35](TASK35.md)의 관측과 같은 자릿수다. **padding →
   device time 환산이 이 배치에서 무모형 채널과 어긋나지 않는다.**

5. **`universal` — 보간 오차가 결론에 실리는 양은 그 bucket의 step 점유율이 정한다.**
   `C(6)`의 −2.00 % 오차가 device 비를 N=6에서 +0.7 %, N=8에서 +0.07 % 움직인다.
   bucket 6의 점유율이 각각 12–47 %와 12–17 %이기 때문이다. **"모형이 두 겹"이라는
   경고의 크기를 이제 수치로 말할 수 있다.**

6. **`stack` — N=6 `(1,2,4,8)`에서 padding과 device time의 부호가 어긋난다.**
   `Δp` = +0.0650(AGENTIC이 덜 pad)인데 device 비는 1.4435(AGENTIC이 44 % 더 씀)다.
   [TASK53](TASK53.md)이 3.1절에서 세운 논지 — **utilization/padding은 비용 지표가
   아니다** — 가 개입 배치에서 재현된다.

## 해석

- **(해석)** 발견 3이 P2 실패의 가장 그럴듯한 설명이다. 세 측정을 삼각 대조하면
  `mb6` ≡ [TASK13](TASK13.md)`mb`(≤ 0.04 ms)이고 이번 `mb`만 벗어난다. artifact 효과가
  실재한다면 `mb6`가 두 `mb` 측정 모두에서 같은 방향으로 벗어나야 하는데 그렇지 않다.
- **(hypothesis)** `mb.L2`의 mean < p50과 max 14.05 ms는 그 세션에 **이봉(bimodal)
  분포**가 있었음을 시사한다. 원인은 확인하지 않았다 — host 측 간섭, device clock
  상태, 그 세션에만 걸린 무언가일 수 있다. **어느 것도 관측하지 않았으므로
  `UNKNOWN`이다.**
- **(해석)** P2를 다시 세우려면 밴드가 아니라 **설계**를 바꿔야 한다. 같은 artifact를
  같은 level에서 여러 번 재서 session 간 분산을 먼저 얻고, artifact 효과를 그 분산에
  대해 판정해야 한다. 이번처럼 artifact당 1회씩만 재면 두 성분이 섞인다.
- **(해석)** 발견 4와 5를 합치면 **[TASK54](TASK54.md)·[TASK52](TASK52.md)의 device
  time 서술은 보간 `C`로도 안전했다.** 실측으로 바꿔도 device 비가 0.7 % 이하로
  움직이고 무모형 채널과의 일치는 유지된다. `확인되지 않은 사항`으로 남아 있던
  "모형이 두 겹"의 위험은 **이 배치에서는 작다**.
- **(해석)** 발견 1은 격자 설계에 함의가 있다. bucket 6의 실제 비용이 보간값보다
  싸다면, 조밀 격자의 이득은 [TASK23](TASK23.md)·[TASK40](TASK40.md)의 sim이 계산한
  것보다 **약간 크다**. 다만 0.238 ms는 bucket 경계 효과(2.05 ms)의 12 %에 불과하다.

## 확인되지 않은 사항

- **P2의 기각이 artifact 효과인지 session 간 변동인지 `UNKNOWN`.** 발견 3의 삼각
  대조는 후자를 가리키지만 **반복 측정 없이는 판별되지 않는다.** 이번 예산에서 하지
  않았다.
- **`mb.L2`의 이봉 분포 원인 `UNKNOWN`** (관측 5). host 간섭·device 상태·기타를
  구분할 계측이 없다.
- **session 간 변동의 크기 `UNKNOWN`.** 관측된 최대 0.32 ms는 표본 2개(같은 artifact
  2회)에서 나온 값이라 분포가 아니다.
- **`C(6)`의 재현성 `UNKNOWN`.** 1회 측정이며 [TASK13](TASK13.md)이 남긴 "1 블록
  파일럿의 CI는 재현성이 아니다"가 그대로 적용된다.
- **`[4, 8]` 구간 곡률의 원인 `UNKNOWN`** — [TASK13](TASK13.md)이 배수당 증가율
  비선형성(+5.7 %, +4.6 %, +17.8 %)에 대해 남긴 것과 같은 항목이다.
- **`prefill.rbln` 바이트 차이의 효과는 여전히 분리되지 않았다.** 이번 측정은
  prompt 20 token이라 prefill 비중이 작다.
- **`marginal_s_per_request`와 `intercept_s`는 이번에 재적합하지 않았다.** 선등록대로
  [TASK13](TASK13.md) 값을 그대로 썼다.

## 실패 / 무효 시도

- **무효 판정된 level은 없다.** 9/9가 1회에 게이트를 통과했고 재실행·server 기동
  실패·device 누수가 없었다. 측정 전후 `rbln-smi`에서 32 device 전부 `0.0B`이고
  잔여 context가 없다.
- **선등록 예측 P2a·P2b·P2c가 기각됐다.** 밴드를 넓히지 않고 실패로 기록한다.
  기각의 내용(발견 2·3)이 이 TASK의 실질적 산출이다.

## 연구 원칙에 미치는 영향

1. **재현성 밴드는 "같은 조건을 여러 번 잰 분산"에서만 유도한다.** 한 실행 안의
   조건 간 범위는 그 양이 아니다(발견 2). [TASK50](TASK50.md)이 τ에 대해 제기한
   문제와 같은 종류이며, 이후 선등록에서 밴드를 만들 때 **어느 분산 성분인지 명시**한다.
2. **처치 효과를 판정하려면 처치 없는 반복이 먼저 있어야 한다.** artifact당 1회씩
   재고 둘을 비교하면 artifact 효과와 session 효과가 섞인다.
3. **삼각 대조는 값싸고 강하다.** 과거의 제3 측정과 나란히 두는 것만으로 이상치가
   어디인지 좁혀졌다(발견 3). 과거 raw artifact를 보존한 덕이다.
4. **모형 항의 오차는 그 항의 점유율로 가중해 보고한다**(발견 5). "보간값이라
   위험하다"가 아니라 "보간 오차 2 %가 결론을 0.7 % 움직인다"로 쓴다.

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **session 간 변동의 null 측정** — 같은 artifact·같은 level을 5–10회 반복해
   `C(b)`의 실행 간 분산을 얻는다. 그것이 있어야 P2를 제대로 다시 세울 수 있다.
   재compile 불필요, lifecycle 10–20회.
2. **P2 재설계 후 재판정** — 1번의 분산으로 밴드를 유도해 artifact 효과를 다시
   판정한다. 이번 판정은 갱신하지 않고 병치한다.
3. **substrate descriptor 갱신 여부 결정** — `_FIXED_S_BY_BUCKET`에 `C(6)` 실측값을
   넣을지, 넣는다면 `mb6` 전용 descriptor로 분리할지. **사용자 판단 사항**이며 이번에
   고치지 않았다.
4. **`mb.L2` 이상 진단** — 재현되는지부터 확인한다. 1번에 포함시킬 수 있다.

## 재현 정보

- 선등록 commit: **`1215579`**, 2026-09-08T15:11:12+09:00.
  **측정 시작 2026-09-08T15:12:22+09:00 — 선등록 이후 70초**
- 측정 종료: 2026-09-08T15:23:52+09:00 (11분 30초, 9 lifecycle)
- Raw artifact: `results/npu/stage2/20260908-151119-step-cost/` (2.7 MiB, gitignored)
  - `order.txt`, `measurement-start.txt`/`measurement-end.txt`
  - `patch-before.txt`/`patch-after.txt`(무차이), `rbln-smi-before.txt`/`-after.txt`,
    `disk-after.txt`, `driver.out`
  - `manifest-mb.txt`/`manifest-mb6.txt`와 각 `.sha256` — artifact 동일성 대조
  - level별: `server-<격자>.L<n>.log`(METRICS·`[BUCKET]` 전문),
    `probe/decode_cost.<격자>.L<n>.json`(ITL raw 표본 전체), `probe-*.log`,
    `*-server-start.txt`/`-stop.txt`, `done.*`
  - 판정 산출: `grid_step_cost.json`
- 파트 3 입력: `results/npu/stage2/20260908-133635-grid-paired/` ([TASK54](TASK54.md), 24칸 `VALID`)
- 실행: `bash experiments/npu/stage2/run_step_cost.sh <RUN>`
- 판정: `env -u PYTHONPATH python3 experiments/npu/analysis/grid_step_cost.py --run <RUN> --task54-run <T54RUN> --output <RUN>/grid_step_cost.json`
- probe 설정: `--prompt-file experiments/npu/stage1/prompt.txt --max-tokens 512
  --seed 20260819` ([TASK13](TASK13.md)과 동일), server는 prefix caching flag 없음
- 실행 순서 seed `20260955`, bootstrap base seed `20260955`, resamples 2,000
- Model artifact: `mb` manifest `b4f5cbf1…f5f`, `mb6` manifest `348f2863…4bf`
  (측정 전 재산출해 [TASK54](TASK54.md) 기록과 대조, 2/2 일치)
- Package: `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`, `optimum-rbln 0.11.1`
- Substrate: `patched`, SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`
- 예산 사용: serving lifecycle **9/10**, 재compile **0**, `models/` 증가 **0 GiB**,
  `/` 사용률 17 %
- 측정 후 device 상태: 32 ID 전부 `0.0B / 15.7GiB`, 잔여 context 없음, 누수 server 없음
