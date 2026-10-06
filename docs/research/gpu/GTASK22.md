# GTASK22 — 경계 효과 민감도와 GPU host 전용 재사용 값 (G-09)

## 상태

DONE

## 날짜

2026-10-06

## 목적

GPU 지시문 G-09(마감 2026-10-07). 기존 로그 계산과 값 추출만 한다(**측정 0, 새 예측 0, 원고 문장 0, 판정 변경 0**).
- 작업 A: NPU [TASK111](../TASK111.md)의 경계 효과 분석을 GPU 정상 상태 로그(GTASK11 N = 20·22·24·26, GTASK20 N = 25·28)에 적용한다.
- 작업 B: [TASK110](../TASK110.md)이 "GPU host 확인 필요"로 남긴 재사용 값(token 비율, replicate별 재사용률·분모, 부분 재사용)을 표로 만든다.

## 배경

- A′-GPU 정의: `gpu_mt_measure.lifecycle_metrics`([GTASK07](GTASK07.md), 개정 1 [GTASK11](GTASK11.md)), `paper/DEFINITIONS.md` §2(TASK109)
- step 진행 규칙: [GTASK12](GTASK12.md) `replay.py`(16,794/16,794 일치)
- 주 예측기: GTASK11 sim LRU(`PREDICTIONS.json`, `2bef619`), GTASK20 ctx(`PREDICTIONS_BLIND.json`, `f0d8000`)
- NPU 대응: TASK111 `paper/BOUNDARY_SENSITIVITY.md`, TASK110 `paper/STATISTICS.md` §5

## 시작 상태

- branch `gpu-a6000` = `614a4c4`, working tree 깨끗함. `git fetch` 후 `gpu-a6000`이 `origin/main`(`167c4dd`, TASK109–111 포함)의 조상이라 `git merge --ff-only origin/main`으로 `167c4dd`에 맞췄다(merge commit 없음, rebase 없음, GPU 선등록 hash 보존)

## 수행 내용

1. TASK109–111, NPU `boundary_sensitivity.py`, GPU `gpu_mt_measure`·`main_judge`·`blind_judge`·`predict_mt`·`predict_blind`·`gpu_mt_sim`·`replay` 확인.
2. `experiments/gpu/multiturn/boundary_sensitivity.py` 작성. 관측: verdict `used` lifecycle 85개의 A′-GPU를 같은 w0에서 L ∈ {60, 90, 120} s, bound lo·hi로 재집계. 예측: GTASK11 `sim_lru`(plan 20 × 3 구성 × 2 bound, N26은 2 구성)와 GTASK20 `ctx`(plan 10 × 3 × 2)를 commit된 코드 경로로 다시 돌려 창별 집계.
3. **재현 점검**: L = 120에서 관측 22/22 행이 verdict 비와, 예측 22/22 행이 예측 파일 `ratio_to_base`와 정확히 같다(Python 3.12.13 venv). 시스템 Python 3.10.12에서는 예측 22/22가 상대 ~10⁻¹⁴ 차로 불일치했다 — 원래 `predict_blind.run_one`을 그대로 불러도 같은 차가 나서 원인을 Python 3.12의 float `sum()` 보상 합산으로 확인했다(실패/무효 시도 참조).
4. 작업 A-3: step 구성원을 GTASK12 step 진행 규칙으로 재구성(구성원 수·token 수 802,567/802,567 step 일치, 첫 ALLOC 이전 server warm-up step 170개 제외)하고, A′-GPU 가격을 decode 몫 `decode_ms(d)`와 prefill 몫(나머지)으로 나눠 시작 잔여 S·끝 잔여 E·보정 비를 냈다.
5. `experiments/gpu/multiturn/reuse_supplement.py` 작성(작업 B). `lifecycle_metrics`와 같은 값을 lifecycle별로 다시 읽고(85/85 assert 일치), G-09 B1의 prefix 정의를 같은 행에서 계산.
6. `experiments/gpu/multiturn/boundary_tables.py`로 두 JSON에서 표를 만들어 [GPU_BOUNDARY_SENSITIVITY.md](GPU_BOUNDARY_SENSITIVITY.md)(작업 A)와 [GPU_REUSE_SUPPLEMENT.md](GPU_REUSE_SUPPLEMENT.md)(작업 B, 표만)를 작성.

## 변경된 파일

- `experiments/gpu/multiturn/{boundary_sensitivity.py, reuse_supplement.py, boundary_tables.py}`(신규)
- `docs/research/gpu/{GPU_BOUNDARY_SENSITIVITY.md, GPU_REUSE_SUPPLEMENT.md, GTASK22.md}`(신규), `docs/research/gpu/GPU_INDEX.md`
- `results/gpu/multiturn/boundary/`(ignored raw: `boundary_sensitivity.json`, `reuse_supplement.json`, `tables.md`, stdout)

## 실험 또는 검증 방법

```bash
PY=/home/csdc/kyeom/envs/vllm-0.22.0/bin/python   # 3.12.13; 예측 bit 재현에 필요
OMP_NUM_THREADS=1 $PY experiments/gpu/multiturn/boundary_sensitivity.py --output results/gpu/multiturn/boundary/boundary_sensitivity.json
OMP_NUM_THREADS=1 $PY experiments/gpu/multiturn/reuse_supplement.py --output results/gpu/multiturn/boundary/reuse_supplement.json
python3 experiments/gpu/multiturn/boundary_tables.py --boundary results/gpu/multiturn/boundary/boundary_sensitivity.json \
  --reuse results/gpu/multiturn/boundary/reuse_supplement.json
```

## 결과

**작업 A** (비 11 cell × bound 2 = 22 행; 전체 표 [GPU_BOUNDARY_SENSITIVITY.md](GPU_BOUNDARY_SENSITIVITY.md) §2)

| 항목 | 값 |
|---|---|
| 120 s 재현 | 관측 22/22, 예측 22/22 정확 일치 |
| 창 폭(max − min, 60/90/120 s), 관측 | 0.0014–0.0378, 중앙 약 0.019 (최대 GTASK20 N25 POOL+GRID 0.037–0.038, GTASK11 N26 POOL 0.033) |
| 창 폭, 예측 | 0.0023–0.0373, 중앙 약 0.010 |
| POOL·POOL+GRID 순서가 창에 따라 바뀌는 N | 관측 5/5(N20·22·24·25·28, lo·hi 모두), 예측 lo 3/5(N20·22·25)·hi 3/5(N22·24·25). BASE는 항상 최대. 관측 두 구성 비 차 ≤ 0.011 |
| 시작 잔여 S / 끝 잔여 E (L = 120, 총합 대비) | 0.79–1.27 % / 2.17–2.96 %; E − S 전 cell 양수(+1.22–+2.10 %) |
| 보정 비 − 원래 비 (L = 120), 중앙끼리 차 > 0.01 | **GTASK11 N22 POOL**: lo +0.0110(0.9690 → 0.9799), hi +0.0108. 나머지 20 행 ≤ 0.0096 |
| 쌍별 차 중앙 (L = 120) | 22 행 모두 \|·\| ≤ 0.0064 |
| replicate 110쌍 \|보정 − 원래\| | 중앙 0.0053, 최대 0.0179, > 0.01 14쌍(7 replicate × lo·hi) |
| 60·90 s에서 > 0.01 | N22 POOL 90 s, N24 POOL 60 s, N24 POOL+GRID 90 s, N26 POOL 60 s(−0.021), GTASK20 N25 POOL+GRID 90 s |
| step 가격 분할 규칙 | decode 몫 `decode_ms(d)` → 재구성 decoder 균등, prefill 몫 = `step_ms(d, p) − decode_ms(d)` → prefill 구성원 token 비례(d = 0이면 전체) |

**작업 B** (전체 표 [GPU_REUSE_SUPPLEMENT.md](GPU_REUSE_SUPPLEMENT.md))

| 항목 | 값 |
|---|---|
| token 비율(prefix 정의), GTASK11 11 cell | 0.4062(N26 BASE)–0.9020(N20 POOL+GRID); N20 BASE 0.8459(cap 0.8463 = GTASK11 §5.5 0.846) |
| token 비율(prefix), GTASK20 6 cell | 0.3465(N28 BASE)–0.7421(N25 POOL) |
| cap − prefix 비율 차 | 0.0002–0.0005(모든 cell) |
| replicate별 재사용률·분모 | GTASK11 55, GTASK20 30 lifecycle 전부(예: N24 BASE r4 75/255 = 0.294, N28 BASE r3 7/249 = 0.028) |
| 부분 재사용(cap, 합산) | GTASK11 0.90 %(N22 POOL+GRID)–8.49 %(N26 BASE), GTASK20 3.79 %(N25 POOL)–10.83 %(N25 BASE); prefix 정의는 4.93–12.66 % |

## 핵심 발견

- 끝 잔여가 시작 잔여보다 모든 cell에서 크다(A′-GPU는 평가 요청 작업을 1.2–2.1 % 덜 센다). NPU(+0.69–+1.64 %)보다 약간 크다 **[post_hoc]**.
- 창에 따라 순서가 바뀌는 것은 POOL·POOL+GRID 쌍뿐이고, 그 차는 ≤ 0.011로 GTASK11 §5.4(`INCONCLUSIVE`) 해상도 안이다. BASE 대비 방향은 모든 창에서 유지된다.
- 경계 보정이 120 s 중앙 비를 0.01 넘게 움직이는 곳은 GTASK11 N22 POOL 하나다(쌍별 차 중앙은 +0.006).
- prefix 정의의 부분 재사용 비율이 cap 정의보다 1.8–5.1 %p 크다: shared가 16의 배수인 요청은 마지막 block이 KV 미계산 token을 포함해 hit 상한이 한 block 작다(cap 정의에서는 full, prefix 정의에서는 partial) **[post_hoc]**.

## 해석

- 없음(민감도 수치와 값 추출만).

## 확인되지 않은 사항

- 예측 쪽 경계 보정(작업 B는 관측만, NPU TASK111과 같다)
- GTASK20 token 비율·부분 재사용 **예측**(예측 파일에 필드 없음, 새 예측 금지)
- 150 s 이상 창(로그에 없음)

## 실패 / 무효 시도

- 첫 실행을 시스템 Python 3.10.12로 해서 예측 120 s 재현이 22/22 불일치(상대 ~10⁻¹⁴)였다. 예측 파일은 venv Python 3.12.13으로 만들어졌고 3.12의 float `sum()`은 보상 합산이라 합이 다르다. venv로 다시 실행해 22/22 일치를 확인했고 3.10 출력은 지웠다. 관측 A′-GPU는 누적 `+=`라 두 버전에서 같았다.

## 연구 원칙에 미치는 영향

- 없음. 기존 판정 변경 없음.
- 재현 정보: GPU 예측 파일의 bit 재현에는 Python 3.12(venv)가 필요하다.

## 다음 작업

- 없음(사용자/Advisor 지시 대기).

## 재현 정보

- 위 명령. HEAD `167c4dd`(= `origin/main`) + 이 작업 파일. Python 3.12.13(`/home/csdc/kyeom/envs/vllm-0.22.0`).
- 입력: GTASK11 `results/gpu/multiturn/main/20260930T1411Z/`(verdict SHA256 `12af692b185e73d0…`), GTASK20 `results/gpu/multiturn/blind/20261002T0655Z/`(verdict `a6609d1eae06d43f…`), `plans/PREDICTIONS.json`(`1be9a99129d24564…`), `plans/blind/PREDICTIONS_BLIND.json`(`ee6ddc0734aedc85…`), `selection/{selection.json, blind_grids.json}` — 모두 변경 없음.
- 산출(ignored): `boundary_sensitivity.json`(`4d18035837adfdd5…`), `reuse_supplement.json`(`a1950b395e116473…`).
- 측정·판정이 없어 선등록 대상 아님(CLAUDE.md 16).
