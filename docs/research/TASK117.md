# TASK117 — 지시문(2026-10-08) 측정과 판정: 계측 영향 A·A2, 대기시간 상한 C, 최대 절감 조건 B(직접 판정 BLOCKED), 동일 자원 선택 E, 단순 근사 D

## 상태

PARTIAL

작업 B의 핵심인 비용 함수와 독립인 직접 시간 판정(DIRECT_EXEC)은 계측 영향 점검을 두 번 통과하지 못해 선등록 규칙대로 `BLOCKED: instrumentation perturbation`이다. C·E는 선등록 판정 완료, B·B 확장은 PRED 대 RECON 보고만, D는 사후 분석 완료.

## 날짜

2026-10-08 – 2026-10-09

## 목적

Advisor 지시문(2026-10-08) A → B → C → (D, B 확장, E)을 [DX_PREREG.md](DX_PREREG.md)(선등록 [TASK116](TASK116.md), 개정 1·2)대로 측정·판정한다. 원고·원고용 문장은 만들지 않는다.

## 배경

- [TASK116](TASK116.md) — 선등록, patch `steptime`
- [TASK102](TASK102.md) — N18 TUNED 0.671, [TASK111](TASK111.md) — 경계 보정, [TASK87](TASK87.md) — N14, [TASK101](TASK101.md) — 재사용 기준선 0.6764

## 시작 상태

- HEAD `983f7e6`(선등록), `?? .idea/`. `[BUCKET]` patch·`steptime` v1 `patched`.

## 수행 내용

1. **A1**(v1, `20261008-dx-a`): 21:44:52–23:51:05, 40/40 유효 → `PERTURBATION`.
2. **개정 1**(`0726acd`, 23:52:31): C를 계측 끔으로 먼저 측정, v2 patch로 A 반복.
3. **C**(`20261008-dx-c`): 23:52:35–01:14:13, 20/20 유효 → 판정.
4. **patch v2**(`e928feb`): 메모리 buffer·1 s flush. 사용자 승인·적용(v1 revert → v2, `a95faf27…`).
5. **개정 2**(`1a0f015`, 01:16:41): A2 결과별 B·E 분기 고정, 집계 기계적 수정.
6. **A2**(v2, `20261009-dx-a2`): 02:44:56–04:51:01, 40/40 유효 → `PERTURBATION` → 분기 `off`.
7. **B**(`20261008-dx-b`): 04:51:31–06:20:44, 20 유효(INVALID 1 → 재실행 유효). **B 확장**(`-b8`): 06:20:44–07:37:37(시간 규칙 통과), 20/20. **E**(`-e`): 07:37:37–09:47:23(시간 규칙 통과), 30/30.
8. **D**: background agent, `taskset -c 64-95 nice -n 19`, 2026-10-08 21:57 시작(284 s, A1 측정 중 — 다른 CPU core로 분리). 주 agent가 결과 검토.

## 변경된 파일

- `experiments/npu/stage3/{dx_analyze.py, dx_steps.py, dx_check.py, dx_tables.py, run_dx.sh, run_dx_lifecycle.sh, run_dx_chain2.sh}`, `plans/dx/ORDER_DX*_OBSOFF.json`
- `patches/vllm_rbln-0.11.1/{steptime_v2_observe.patch, apply_steptime_v2.sh, STEPTIME.md}`
- `docs/research/dx/{DX_A_PERTURBATION.csv, DX_B_PER_REP.csv, DX_C_CELLS.csv, DX_C_COST_PER_REP.csv, DX_C_GAPS.csv, DX_E_PER_REP.csv, D_SIMPLE_APPROX.md, D_SIMPLE_APPROX.csv}`, `experiments/npu/analysis/dx_simple_approx.py`
- `docs/research/DX_PREREG.md`(§11·§12), `docs/research/TASK117.md`, `docs/research/INDEX.md`, `paper/RESULTS_INDEX.md`(§23)

## 실험 또는 검증 방법

```bash
S3=experiments/npu/stage3; R=results/npu/stage3
python3 $S3/dx_analyze.py a --run $R/20261008-dx-a --output $R/20261008-dx-a/dx_verdict_a.json
python3 $S3/dx_analyze.py a --run $R/20261009-dx-a2 --output $R/20261009-dx-a2/dx_verdict_a.json
python3 $S3/dx_analyze.py c --run $R/20261008-dx-c --output $R/20261008-dx-c/dx_verdict_c.json
python3 $S3/dx_analyze.py b_off --n 18 --run $R/20261008-dx-b --output $R/20261008-dx-b/dx_report_b_off.json
python3 $S3/dx_analyze.py b_off --n 8 --run $R/20261008-dx-b8 --output $R/20261008-dx-b8/dx_report_b_off.json
python3 $S3/dx_analyze.py e --channel RECON --run $R/20261008-dx-e --output $R/20261008-dx-e/dx_verdict_e.json
python3 $S3/dx_tables.py
```

Population: lifecycle(server 1개, rbln0–3 한 card), 평가창 120 s(A 60 s), 통계 단위 replicate. 비용 = 호출당 A′(RECON) 또는 시뮬레이터 가격(PRED), 단위 s/turn.

## 결과

### 작업 A — 계측 영향 (개발용 점검, 검증 결과 아님)

조건별 `on/off − 1` paired median (5쌍). 판정 신호는 처리율과 MODEL DECODE 평균.

| 점검 | 조건 | 처리율 | DECODE 평균 | 쌍별 sd(처리율 / DECODE) | 1 % 초과 |
|---|---|---:|---:|---|---|
| A1 v1 | BASE N6 | 0.000 | −0.009 | 0.031 / 0.006 | — |
| A1 v1 | BASE N18 | 0.000 | −0.006 | 0.011 / 0.010 | — |
| A1 v1 | TUNED N6 | **−0.015** | −0.002 | 0.019 / 0.007 | 예 |
| A1 v1 | TUNED N18 | 0.000 | **−0.013** | 0.026 / 0.014 | 예 |
| A2 v2 | BASE N6 | **+0.013** | −0.006 | 0.016 / 0.003 | 예 |
| A2 v2 | BASE N18 | −0.009 | +0.002 | 0.009 / 0.003 | — |
| A2 v2 | TUNED N6 | 0.000 | +0.009 | 0.028 / 0.015 | — |
| A2 v2 | TUNED N18 | −0.008 | +0.008 | 0.014 / 0.011 | — |

두 번 모두 `PERTURBATION`(선등록 기준). 전체 신호(ITL·지연·RECON·step 수·prefill)는 `DX_A_PERTURBATION.csv`. v2의 decode record는 bucket보다 lifecycle마다 3–88개 적었다(on 20개) — 종료 직전 1 s buffer가 쓰이지 않은 꼬리로, 집계 범위 밖(귀속 누락 0, 전 lifecycle 유효).

### 작업 B — N18·N8, 계측 끔 (직접 판정 BLOCKED, 보고만)

| N | R_RECON median [95 % CI] | 1 미만 / 10 (sign p) | R_PRED median | \|PRED − RECON\| | 재사용 관측 / PRED (BASE, TUNED) |
|---|---|---|---:|---:|---|
| 18 | **0.6725** [0.6666, 0.6998] | 10 (0.002) | 0.6774 | 0.0049 | 0.019 / 0.023, 0.722 / 0.733 |
| 8 | 0.9795 [0.9555, 0.9950] | 9 (0.021) | 0.9838 | 0.0043 | 0.792 / 0.797, 0.886 / 0.888 |

- 판정 1–4(DIRECT_EXEC 기준)는 판정하지 않는다. PRED와 RECON은 같은 비용 함수를 공유하므로 위 일치는 지시문 §1.1의 공통 비용 함수 문제를 해소하지 않는다.
- 절대 호출당 시간(median, s/turn): BASE PRED 0.556 / RECON 0.554, TUNED 0.377 / 0.377(N18).
- INVALID 1: `B.TUNED.n18.r4`(평가 종료 뒤 발송 1건, runner 경계 사례) → `.retry1` 유효.

### 작업 C — N14, 상한 60 대 120 s (계측 끔, 선등록 검증)

| cell | 재사용 관측 | PRED | 오차 | h TVD | 처리율 /s | 평균 running | TTFT 중앙 s |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE cap60 | 0.2786 | 0.3005 | +0.0219 | 0.059 | 1.757 | 6.48 | 0.372 |
| BASE cap120 | 0.3692 | 0.4067 | +0.0375 | 0.055 | 1.727 | 5.89 | 0.345 |
| TUNED cap60 | 0.8025 | 0.8095 | +0.0071 | 0.054 | 2.165 | 6.19 | 0.079 |
| TUNED cap120 | 0.8227 | 0.8283 | +0.0056 | 0.029 | 2.050 | 5.42 | 0.082 |

- **주 재사용 PASS**(4/4 ≤ 0.05, MAE 0.0180, 최대 0.0375 — BASE 오차가 TUNED보다 크고 둘 다 과대). **skill PASS**(Σ 0.072 ≤ 0.5 × 0.977).
- **주 비용 PASS — 공통 비용 모형 아래 검증**: cap60 PRED 0.7869 대 RECON 0.7834 [0.7568, 0.8278] (오차 0.0035), cap120 0.8275 대 0.8182 [0.7905, 0.8992] (오차 0.0093). DIRECT_EXEC 열 없음(A 미통과).
- **민감도(관측, 같은 replicate)**: cap120/cap60 RECON 비 BASE 0.9964 [0.9859, 1.0311], TUNED 1.0728 [1.0224, 1.1179]; 재사용 차 BASE +0.091(PRED +0.106), TUNED +0.020(PRED +0.019). 대기 분포: 상한 60 s는 대기의 2.63 %·대기 합의 37.8 %를, 120 s는 1.42 %·21.1 %를 자른다.

### 작업 E — N19, 동일 자원(batch·KV 16) 선택 (계측 끔, 주 채널 RECON)

| 후보 | R 관측 (BATCHONLY 대비) | PRED |
|---|---:|---:|
| BATCHONLY | 1.0000 | 1.0000 |
| **TUNED (선택)** | **0.9708** | 0.9696 |
| DP_N8 | 1.0160 | 1.0225 |

- 손실 = 0.0000(관측 최저 = 선택), bootstrap [0, 0] → **PASS**. 낮은 판별력 표시 없음(폭 4.7 %). **이점 확인**: TUNED/BATCHONLY 0.9708 [0.9642, 0.9852], 10/10(p 0.002). 관측 최저는 유한 반복의 최저이며 참 최적의 증명이 아니다.

### 작업 D — 사후 기전 분석 (`post_hoc`, [dx/D_SIMPLE_APPROX.md](dx/D_SIMPLE_APPROX.md))

- 개발 미사용 검증 집합(TASK95·102, 재도착 22,612): 전체 규칙 22,612/22,612 관측 일치. 도구 대기 중 할당 수만 세는 근사(`survives_gap`) 0.748 일치, 실패 5,705건 전부 과대 생존(자기 체류 중 할당 4,734, pinned 702, dummy 269), 재사용 token +44 %. TASK72 닫힌 형태 0.890.
- 저부하 4 cell(N ≤ batch): 재사용 MAE Poisson 근사 0.0088, binomial 0.0106, 요청별 v1 0.0278, 선등록 v1 0.0152; Brier Poisson 0.0295, binomial 0.0354, v1 0.0312(cell 값만 있는 선등록 v1에는 Brier 없음). CI 미계산이라 순서를 차이로도 동치로도 판정하지 않는다.

## 핵심 발견

- `[stack]` 이 serving 경로에서 step당 1줄(v1) 또는 1 s buffer(v2) 계측의 on/off 차이는 처리율·DECODE 평균의 paired median 기준 |·| ≤ 0.015였고, 1 %를 넘은 조건이 두 점검에서 서로 달랐으며(A1 TUNED N6·N18, A2 BASE N6) 넘은 방향은 모두 on이 더 빠른 쪽이었다. 선등록 기준으로는 `PERTURBATION`이다.
- `[stack]` N18 TUNED/BASE의 재구성 비 0.6725(새 seed 10쌍, 10/10 < 1)는 TASK102의 0.671과 같은 수준이고 PRED 0.6774와 0.005 차이다 — 단 공통 비용 함수 아래다.
- `[class]` 대기 상한을 60 → 120 s로 올리면 BASE 재사용이 오르고(+0.09) TUNED의 상대 절감이 줄며(TUNED 호출당 비용 +7 %), 통합 시뮬레이터가 두 방향과 크기를 측정 전에 맞혔다(재사용 차 +0.106/+0.019 대 관측 +0.091/+0.020). 잘린 대기의 개수(2.6 %)가 아니라 잘린 합(38 %)이 영향의 크기를 정한다. 값은 이 trace·인스턴스의 값.
- `[stack]` 같은 batch·KV 자원(16)에서 시뮬레이터가 고른 격자(TUNED)가 미사용 N = 19에서 관측 최저였고 BATCHONLY 대비 2.9 % 낮았다(RECON).

## 해석

- 관찰: A의 1 % 초과는 계측 on이 더 빠른 방향이고 조건이 반복마다 바뀐다. 파생 해석: 이 점검(5쌍, 60 s 창, 처리율은 요청 1건 ≈ 1 %)의 해상도가 1 % 기준보다 거칠 가능성이 크다. 이 해석으로 기준을 소급 완화하지 않으며 B의 직접 판정은 `BLOCKED`로 남긴다.
- C·E의 비용 판정은 RECON을 참조로 한 공통 비용 모형 아래 검증이다. 재사용 판정(C)과 선택 순위(E)의 관측 방향은 비용 모형과 무관한 관측(`cached_tokens`)·같은 비용 함수 아래 비교다.

## 확인되지 않은 사항

- 비용 함수와 독립인 직접 시간 기준의 절감 방향·크기(B의 목적) — `BLOCKED`.
- HW_ACTIVE(측정하지 않음). E의 DP_N8 예측은 context 비용 규칙 추정 포함.
- A 점검의 실제 해상도(같은 조건 무처치 반복의 분산) — 재지 않았다.

## 실패 / 무효 시도

- A1·A2 `PERTURBATION`(선등록 기준 실패, 보존). INVALID 1(B TUNED r4, 재실행 유효). C 집계 첫 실행 `KeyError`(obs-off 경로, 기계적 수정 — 개정 2 기록).

## 연구 원칙에 미치는 영향

- 계측 영향 점검은 무처치 반복으로 해상도를 먼저 재고 기준을 정해야 한다는 교훈(후보). 이번 기준은 바꾸지 않았다.

## 다음 작업

- (Advisor 결정) B 직접 판정 `BLOCKED` 처리: (i) 그대로 보고, (ii) 무처치 반복으로 점검 해상도를 잰 뒤 새 선등록으로 B 직접 측정, (iii) 120 s 창·더 많은 쌍으로 A 재설계. steptime v2 patch는 flag가 꺼져 있으면 무동작이며 현재 `patched` 상태로 두었다(복구: `sudo bash patches/vllm_rbln-0.11.1/apply_steptime_v2.sh revert`).

## 재현 정보

| run | 측정 | 선행 commit(시각) | run HEAD | lifecycle | 판정 파일 SHA256 |
|---|---|---|---|---|---|
| A1 `20261008-dx-a` | 10-08 21:44:52–23:51:05 | `983f7e6` 21:44:44 | `983f7e6` | 40/40 | `a5a51c7144b3fb09…` |
| C `20261008-dx-c` | 23:52:35–10-09 01:14:13 | `0726acd` 23:52:31 | `0726acd` | 20/20 | `568edf1e73e13c1e…` |
| A2 `20261009-dx-a2` | 02:44:56–04:51:01 | `1a0f015` 01:16:41 | `da6a78c` | 40/40 | `c71e946752673f6a…` |
| B `20261008-dx-b` | 04:51:31–06:20:44 | `1a0f015` | `da6a78c` | 20(+1 INVALID) | `8755296c96f38abb…` |
| B8 `20261008-dx-b8` | 06:20:44–07:37:37 | `1a0f015` | `da6a78c` | 20/20 | `667b16ffaee67654…` |
| E `20261008-dx-e` | 07:37:37–09:47:23 | `983f7e6`(선택 고정) | `da6a78c` | 30/30 | `8fb6e1750e15afb7…` |

측정 중 HEAD 불변. run은 `results/npu/stage3/`(비추적). package vllm 0.22.0+cpu, vllm-rbln 0.11.1(`[BUCKET]` patch, steptime v1 → v2), Qwen3-4B artifact 4종(새 compile 없음), RBLN CA25 rbln0–3.
