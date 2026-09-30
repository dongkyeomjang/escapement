# TASK81 — multi-turn 본 실험 선등록 개정 2와 N = 8 DP 격자 compile

## 상태

DONE

## 날짜

2026-09-30

## 목적

Advisor 지시문 05 §2–§3. 본 측정 전에 (1) 선등록 판정 기준에 **영(null) 예측기 대비 skill 조건**을 AND로 추가하고, (2) DP 격자 결정(N = 8만 compile, DP·TUNED 각 10 replicate)을 반영한 추가 plan·예측·측정 순서·재실행 규칙·판정 스크립트를 commit하고, (3) 승인된 compile 1회를 실행해 bucket 사상을 확인한다.

**본 측정 0.** 측정과 판정은 [TASK82](TASK82.md)(예정)에서 한다.

## 배경

관련 TASK:

- [TASK80](TASK80.md) — 본 실험 plan·blind 예측·판정 기준(초판) 선등록 `eedf5ed`
- [TASK78](TASK78.md) — N별 DP 격자 blind 선정, compile 보류(새 격자 4개 > 상한 3)
- [TASK79](TASK79.md) — streaming 파일럿 `EQUIVALENT`(짝 ratio 산포 0.998–1.023)
- [TASK73](TASK73.md) — 개발 집합 A4(재사용 영 예측기의 출처)
- [TASK72](TASK72.md) — R4, 원고 Table I 조건의 관측 h(n)(h 영 예측기의 출처)
- [TASK34](TASK34.md)·[TASK62](TASK62.md) — TUNED artifact의 compile 명령, 재compile 절차(`HF_HUB_OFFLINE=1`)
- [TASK23](TASK23.md) — 사상표 재검증 방식(`concurrency_probe.py`)

## 시작 상태

- HEAD `c702b57`([TASK80](TASK80.md)), `git status --short`: `?? .idea/`만, branch `main`
- `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`, `optimum-rbln 0.11.1`; patch 상태 `patched`(`model_base.py` `70942d16…`)
- device `rbln0`–`rbln3` 사용 전 비어 있음(`rbln-stat`, 0.0 B / 15.7 GiB)

## 수행 내용

1. **영 예측기 확정**(`null_predictors.py` → `plans/main/NULL_PREDICTORS.json`): 재사용 = A4 채점 모집단 675/998 = **0.67635**; 비용 비 = 1.0; h(n) = T01의 격자 (1,2,4,8) 행과 같은 방식으로 `padding_ratio.json` cell을 step 수로 합산한 같은 N의 관측 h(합산 padding이 T01 값과 일치함을 assert).
2. **N = 8 추가 plan r5–r9**(`make_main_plans_ext.py`, seed 20261485–20261489, `INDEX_EXT.json`)와 그 **세 예측기 예측**(`predict_ext.py` → `PREDICTIONS_EXT.json`, r5–r9와 r0–r9 합산).
3. **측정 순서표**(`make_main_order.py`, seed 20261410 → `ORDER.json`, 75 lifecycle).
4. **측정·판정 도구**: `mt_check.py`(lifecycle 유효성만 출력), `run_main.sh`(순서표 구동, `INVALID` 1회 재실행), `main_analyze.py`(§5.1–5.8 판정, 개정 2 규칙). 파일럿 산출을 symlink로 가짜 run에 배치해 코드 경로를 시험했다(값은 의미 없음).
5. [MULTITURN_MAIN_PREREG.md](MULTITURN_MAIN_PREREG.md) §7 **개정 2**를 쓰고 위 전부와 함께 commit `5f62fb4`(2026-09-30 00:54:27 +0900).
6. **compile 1회**(`compile_dp8.sh`) — 이 commit 이후 00:54:33에 시작.
7. **bucket 사상 확인**(`map_check_dp8.sh`, 동시성 2·3·5·6·7).

## 변경된 파일

개정 2 commit `5f62fb4`:

- `docs/research/MULTITURN_MAIN_PREREG.md` (§7 개정 2, 머리말, 개정 이력)
- `experiments/npu/stage3/{make_main_plans_ext.py, predict_ext.py, null_predictors.py, make_main_order.py, mt_check.py, run_main.sh, main_analyze.py, compile_dp8.sh, map_check_dp8.sh}` (신규)
- `experiments/npu/stage3/plans/main/{main-n8-r5..r9.json, INDEX_EXT.json, PREDICTIONS_EXT.json, NULL_PREDICTORS.json, ORDER.json}` (신규)

기록 commit: `docs/research/TASK81.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/make_main_plans_ext.py
env -u PYTHONPATH python3 experiments/npu/stage3/predict_ext.py --output results/npu/stage3/predict/ext_predictions.json
env -u PYTHONPATH python3 experiments/npu/stage3/null_predictors.py --output experiments/npu/stage3/plans/main/NULL_PREDICTORS.json
env -u PYTHONPATH python3 experiments/npu/stage3/make_main_order.py
bash experiments/npu/stage3/compile_dp8.sh /home/rebel/continuum-npu/results/npu/stage3/20260930-main
bash experiments/npu/stage3/map_check_dp8.sh /home/rebel/continuum-npu/results/npu/stage3/20260930-main
```

## 결과

### 영 예측기와 측정 전 참고값

| 항목 | 영 예측기 | 참고값(관측 = 해석 예측이라 가정) |
|---|---|---|
| §5.1 재사용 | 0.67635 (675/998) | 확증 cell 예측 범위 0.281, 영 MAE 0.171 |
| §5.2 비용 비 | 1.0 | 평균 \|1 − 비\| 0.032, Σ 0.225 |
| §5.6 h(n) | T01 (1,2,4,8): N=6 TASK20 2,193 step, N=8 TASK19+20+23-2a 5,677, N=10 TASK20 1,896 (N=12 TASK20 1,797, 탐색) | 영 h와 해석 h의 TVD 중앙값 0.297 |

관측이 sim 기본 예측과 같다면 Σ\|1 − m\| = 0.150, 해석의 Σ\|예측 − m\| = 0.075로 **skill 비가 정확히 0.50** — 해석의 §5.2 skill은 경계에 있을 것으로 예측했다(선등록 §7.3).

### 추가 plan과 예측

| plan | seed | `cycle_s` | 최대 context |
|---|---|---|---|
| main-n8-r5 | 20261485 | 5.779 | 3,099 |
| main-n8-r6 | 20261486 | 5.364 | 3,074 |
| main-n8-r7 | 20261487 | 5.582 | 3,019 |
| main-n8-r8 | 20261488 | 6.126 | 2,991 |
| main-n8-r9 | 20261489 | 5.470 | 3,082 |

DP/TUNED turn당 A′ 비 예측(해석 / sim 기본 / sim 관측): r5–r9 0.9956 / 0.9908 / 0.9908, **r0–r9 0.9958 / 0.9890 / 0.9890**. §5.4 사전 예측 `INCONCLUSIVE` 유지.

### 확증 cell 수(개정 2 반영)

§5.1 10 cell(PASS에 9/10), §5.2 7 cell(강화 6/7), §5.3 N=8 6쌍·N=6·10 각 3쌍, §5.5 7 cell(k ∈ {1..6}), §5.6 10 cell.

### compile

| 항목 | 값 |
|---|---|
| 명령 | `env -u PYTHONPATH HF_HUB_OFFLINE=1 /usr/bin/time -v timeout 1800 optimum-rbln-cli --model-id Qwen/Qwen3-4B --output-dir models/Qwen3-4B-rbln-b16-s8192-d4-dp8 --batch_size 16 --decoder_batch_sizes 1,2,3,4,6,16 --max_seq_len 8192 --num_devices 4` ([TASK34](TASK34.md) TUNED 명령과 decoder 폭·출력 경로만 다르고, `HF_HUB_OFFLINE=1`은 [TASK62](TASK62.md) 선례) |
| 시간 | 2026-09-30 00:54:33 → 01:02:18, wall **7:44.66**(464.7 s), exit 0, 최대 RSS 39.1 GB. TUNED 8:00.57 |
| 크기 | **14,119,853,902 B (13.15 GiB)**. TUNED 13.202 GiB. `models/` 110 GiB, 디스크 여유 666 GiB |
| manifest SHA256 | `7e30314c19b1b646de5edc6baad29f1b218e64b12e9874ab23f6577fbe58634d`(파일별 목록 `compile/manifest-dp8.txt`) |
| `rbln_config.json` | `batch_size` 16, `kvcache_num_blocks` 16, `max_seq_len` 8192, `decoder_batch_sizes` [16,6,4,3,2,1], `optimum_rbln_version` 0.11.1. TUNED와의 diff는 decoder 폭과 compiled model 이름뿐 |
| 기존 artifact | 지우거나 덮어쓰지 않음(스크립트가 출력 경로 존재 시 거부) |

### bucket 사상 확인

`map_check_dp8.sh`(01:03:05–01:04:37, [TASK23](TASK23.md)·[TASK34](TASK34.md) 방식: `concurrency_probe.py`, max_tokens 64, 동시성별 동시 요청). server 로그 `Bucket sizes for RBLN sampler: (1, 2, 3, 4, 6, 16)`.

| 동시성 | 기대 bucket (`bisect_left`) | 관측 bucket | step 수 |
|---|---|---|---|
| 2 | 2 | **2** | 63 |
| 3 | 3 | **3** | 63 |
| 5 | 6 | **6** | 63 |
| 6 | 6 | **6** | 63 |
| 7 | 16 | **16** | 63 |

**5/5 일치.** 응답 전부 200, peak running = 요청 동시성, SIGKILL 불필요, 종료 후 device memory 0.0 B.

- `requested_condition`: DP(8) 격자 `(1,2,3,4,6,16)`, `batch_size` 16, `max_seq_len` 8192, `num_devices` 4, 기존과 같은 compiler
- `observed_condition`: `rbln_config.json`과 server 로그의 격자 (1,2,3,4,6,16), 나머지 인자 동일, 사상 5/5 일치
- `condition_reached`: `YES`

## 핵심 발견

1. **`universal`** — **구성 효과가 작은 부하에서는 "허용 오차 안"이라는 기준이 정보 없는 예측기도 통과시킨다.** 예측 비용 비가 0.97–0.99이고 run 간 산포가 1–2 %면 "모든 비 = 1.0"도 \|예측 − m\| ≤ 0.03을 대부분 통과한다. 모형의 가치는 영 예측기 대비 오차 감소(skill)로 따로 판정해야 한다 — 기판과 무관한 판정 설계의 원칙이다.

## 해석

- 재사용 영 예측기(0.676)는 원고 조건의 개발 집합에서 왔으므로 steady-state 예측 범위(0.74–0.92)보다 낮다. 관측이 예측 근처라면 영 MAE가 커서(≈ 0.17) §5.1 skill은 v1 MAE ≤ 약 0.085를 요구한다. 이 영 예측기는 "cell 간 차이"뿐 아니라 "부하 조건이 바뀐 것"까지 벌점으로 준다는 점을 판정 해석 때 함께 적는다.
- §5.2 skill은 해석과 시뮬레이터가 갈리는 크기(Σ 0.075)가 영 예측기의 벌점 절반과 같은 자릿수라, 어느 예측기가 맞는지에 따라 경계에서 갈릴 것이다.

## 확인되지 않은 사항

- 본 측정 결과 전부([TASK82](TASK82.md) 예정)
- bucket 3의 step 비용은 미측정이며 descriptor 보간값을 쓴다(비용 모형의 기존 한계, [INDEX 후속 연구 2](INDEX.md#후속-연구))

## 실패 / 무효 시도

- `null_predictors.py` 첫 실행에서 `hist_agentic`을 문자열로 가정해 `ast.literal_eval`이 실패했다(JSON에는 dict로 저장). 파싱만 고쳐 재실행했다 — 값 계산 규칙은 바뀌지 않았다.
- 판정 스크립트 가짜 run 시험 첫 시도에서 BASE 격자 descriptor에 TUNED 파일럿 로그(bucket 6)를 넣어 `KeyError`가 났다 — 가짜 데이터 배치 문제이며 스크립트 수정 없이 배치를 바꿔 통과했다.

## 연구 원칙에 미치는 영향

- 판정 기준 설계에 **영 예측기 대비 skill 조건**이 들어갔다. 이후 선등록에서 효과 크기가 산포와 같은 자릿수면 같은 조건을 기본으로 둘 것을 권고한다.

## 다음 작업

- 지시문 05 §4–§5: 본 측정 75 lifecycle과 판정([TASK82](TASK82.md)).

## 재현 정보

- 위 명령. compile 산출 `results/npu/stage3/20260930-main/compile/`(비추적), 사상 확인 `…/mapping/`(비추적), artifact `models/Qwen3-4B-rbln-b16-s8192-d4-dp8`(gitignored).
- `NULL_PREDICTORS.json` SHA256 `1e7e38ac6be8debe7f76ca821d8845e9905b0895821d92f1d307663ad43ac690`, `INDEX_EXT.json` `e3e33cf0ee4a2da80f78a1a40ebd190a8c14bd30c26c6c3f53e4225197ccbff7`, `PREDICTIONS_EXT.json` `904ccd638511030918a7dbd410b450290c6f72e6b84aa21a0ef4eaa8372d7275`(= `results/npu/stage3/predict/ext_predictions.json` byte 동일), `ORDER.json` `bd2800a8da115afc8f782488f97b169deec107f675e5ba324c61d26dd9064c20`.
- **선등록 개정 2 commit: `5f62fb4630b15095c6a289ad645f1b765c2df8b4` (2026-09-30 00:54:27 +0900) → compile 시작 00:54:33 → 본 측정은 이 TASK 기록 commit 이후 시작한다.**
