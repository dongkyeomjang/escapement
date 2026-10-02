# 붕괴 영역 blind (N = 25·28) — 세 비용 입력 예측과 판정 기준 선등록 (GPU 지시문 G-07 작업 C)

작성: 2026-10-02. [GTASK20](GTASK20.md). **이 문서, 예측 파일, plan, 순서표, 판정 script를 측정 전에 commit한다.** 작업 B([GTASK18](GTASK18.md)) 결과 commit(`809a767`, `b75c2b1`) 뒤에 예측을 계산했다.

## 1. 목적

GTASK11의 붕괴 과소 예측(N24·26 BASE)이 시간 척도에서 왔다면, step 시간을 운영 비용으로 진행시키는 sim LRU는 **새 seed·새 N**의 붕괴 영역에서 재사용·비용 비·h를 맞혀야 한다. 비용 입력 세 가지를 같은 시뮬레이터에 넣어 비교한다.

## 2. plan과 구성

- **N = 25, 28**, replicate r = 0..4, plan `gblind-n{N}-r{r}`, seed `20263000 + i`(i = 0..9; GPU 선정 20262100–26, GTASK11 20262300–19, 파일럿 20262500–02, NPU 20261200–524와 겹치지 않음).
- 생성 규칙은 GTASK09와 같다(`make_plan.build`, 첫 prompt U(800, 1600), segment 8, 생성 U(32, 256), 8 turn, gap `toolmix` 상한 60 s, `cycle_s` = 해석 POOL 예측).
- 파일: `experiments/gpu/multiturn/plans/blind/` 10개와 `INDEX.json`. 최대 context는 3,094–3,254 token, preemption 불가에 필요한 block은 최대 1,633 ≤ 1,899다.
- N = 26 plan(`gmain-n26-r*`)은 쓰지 않는다(GTASK11 §7.9, G-07 §5.4).
- **구성**: BASE(1,900, (1,2,4,8,16)), POOL(2,300, 같은 격자), POOL+GRID(2,300, 격자는 GTASK08 규칙 6을 이 plan에 적용한 결과로 N = 25·28 모두 (1,5,7,8,16)). `selection/blind_grids.json`에 있고 `configs.config_by_name`이 이 파일을 읽는다.
- 짝 설계: 같은 (N, r)의 plan을 세 구성이 쓴다. lifecycle은 2 N × 3 구성 × 5 = **30개**다.

## 3. 예측기 (모두 sim LRU, `gpu_mt_sim`; step 시간 입력만 다름)

| 예측기 | step 시간 | 성격 |
|---|---|---|
| **(1) `ctx` (주)** | 가격 + c · (Σ decode context − decodes · 128). c = 2.12 × 10⁻⁴ ms/token(GTASK18 F1), 128 = GTASK05 가격 측정 부하의 평균 decode context. decode가 있는 모든 step(FULL·혼합·eager)에 적용 | 결과와 독립된 통제 측정 |
| (2) `x1.210` | 가격 × 1.210 | GTASK11 관측(N = 20–26)에서 맞춘 값을 새 seed·새 N에 적용한 **보정된 예측** |
| (2′) `mode_dist` | 가격 × GTASK11 step class별 lag 1 dispatch/가격 분포에서 뽑은 비(GTASK13 `obs.json`, SHA256 `200c08be40b545f6…`) | 보정된 예측(변형) |
| (3) `price` | GTASK05 가격(= GTASK17 곡선) | 기준선 |

- 비용 지표(turn당 A′, BASE 대비 비)는 관측과 같은 가격 채널로, 시뮬레이션된 평가 구간 step에서 같은 bound로 계산한다. 시간 입력은 동역학만 바꾼다.
- h는 평가 구간 step의 decode 수(≥ 1) step 가중 분포다(개정 1 §7.4 정의).
- `simulate`에 `step_cost` hook을 더했다(기본 `None` = 원래 timing). 회귀 확인: `gmain-n20-r0` BASE lo의 재사용·device/turn이 `PREDICTIONS.json`과 정확히 같다(0.858757, 0.295591 s).
- 산출: `plans/blind/PREDICTIONS_BLIND.json`(SHA256 `ee6ddc0734aedc85…`), `predict_blind.py` 1회 실행.

### 3.1 예측값 (lo / hi)

재사용률(turn ≥ 1):

| cell | (1) ctx | (2) x1.210 | (2′) mode_dist | (3) price |
|---|---|---|---|---|
| N25 BASE | 0.514 / 0.525 | 0.494 / 0.475 | 0.490 / 0.455 | 0.696 / 0.670 |
| N25 POOL | 0.770 / 0.778 | 0.770 / 0.777 | 0.775 / 0.769 | 0.812 / 0.817 |
| N25 POOL+GRID | 0.772 / 0.779 | 0.782 / 0.779 | 0.774 / 0.763 | 0.813 / 0.811 |
| N28 BASE | 0.403 / 0.401 | 0.353 / 0.354 | 0.379 / 0.351 | 0.494 / 0.491 |
| N28 POOL | 0.677 / 0.673 | 0.657 / 0.642 | 0.657 / 0.656 | 0.764 / 0.764 |
| N28 POOL+GRID | 0.682 / 0.667 | 0.662 / 0.642 | 0.663 / 0.661 | 0.755 / 0.763 |

BASE 대비 비용 비:

| cell | (1) ctx | (2) x1.210 | (2′) mode_dist | (3) price |
|---|---|---|---|---|
| N25 POOL | 0.9047 / 0.8990 | 0.9041 / 0.8832 | 0.8966 / 0.8876 | 0.9565 / 0.9409 |
| N25 POOL+GRID | 0.9039 / 0.8998 | 0.9012 / 0.8798 | 0.8981 / 0.8867 | 0.9575 / 0.9402 |
| N28 POOL | 0.8969 / 0.9041 | 0.8955 / 0.9022 | 0.9009 / 0.8934 | 0.9077 / 0.8997 |
| N28 POOL+GRID | 0.9005 / 0.9041 | 0.8968 / 0.9026 | 0.8988 / 0.8913 | 0.9073 / 0.9025 |

- (1)의 wall/가격 비는 1.15–1.18이다(GTASK13의 운영 1.21보다 조금 작다. GTASK18 발견 3과 같은 방향).
- (1) BASE replicate별 재사용: N25 0.20–0.72, N28 0.06–0.63. 붕괴 cell의 plan 간 산포가 크다(GTASK16과 같은 성질).

### 3.2 G-07 §5.4 점검 (N = 28 전 구성 붕괴 여부)

N = 28에서 (1)의 예측은 BASE 0.40, POOL 0.68, POOL+GRID 0.68이고, 비용 비는 약 0.90이다. 구성 간 정보가 있으므로 N = 28을 그대로 쓴다.

## 4. 측정

- GTASK11과 같다: runner `gpu_mt_runner.py`(streaming), 관측 patch, KV events, 카드 `4485e769…`, 평가 구간 120 s.
- 순서: `plans/blind/ORDER.json`(`make_blind_order.py`, seed 20263010, SHA256 `ef31b5febf373b30…`). 5 round이고, round k에서 N = 25·28 블록(r = k)을 무작위 순서로 돈다. 블록 안 구성 순서는 replicate마다 다른 순열이다.
- **INVALID 재실행**: GTASK11 개정 1 §7.5와 같다. 순서를 다 돈 뒤 무효(runner 또는 측정 모듈 검사) lifecycle을 같은 plan으로 한 번 다시 잰다(`.retry1`). 그래도 무효면 그 replicate는 빠지고 수를 표기한다.
- driver `run_blind.sh`: 측정 → 재실행 → `blind_judge.py` 1회 → `blind_result/verdict.json`만 local `gpu-a6000`에 commit(git 종료 코드와 HEAD 이동을 확인한다). push는 하지 않는다. 측정 중 HEAD를 바꾸지 않는다.
- 예산: lifecycle 약 3.5–4분 × 30 ≈ 2 h.

## 5. 판정 기준 (GPU 선등록 개정 1 §5.1·5.2·5.3·5.6 그대로, 주 예측기 (1))

공통:
- cell 6개(2 N × 3 구성), 비 cell 4개(2 N × POOL·POOL+GRID)
- bound 규칙: lo 예측 대 lo 관측, hi 대 hi. **PASS는 두 bound 모두에서 성립해야 한다.**
- 최종 표기는 개정 1 §7.2 표를 쓴다.
- 모든 판정은 네 예측기에 같은 규칙으로 계산한다. **판정의 주체는 (1)**이고 나머지는 보고다.

| 항목 | 기준 |
|---|---|
| §5.1 재사용 | (a) 6/6 cell \|예측 − 관측\| ≤ 0.10, (b) \|mean(예측 − 관측)\| ≤ 0.05, skill `MAE ≤ 0.5 × MAE(NPU 영 0.84718)`. `MAE(영) < 0.05`이면 skill `NOT_INFORMATIVE` |
| §5.2 비용 비 | 기본: \|예측 − m\| ≤ 0.03 ∧ 방향 일치(CI가 1을 포함하면 \|예측 − 1\| ≤ 0.03). 강화: 예측 ∈ [l − 0.01, u + 0.01]. **PASS ⇔ 기본 4/4 ∧ 강화 3/4 이상 ∧ skill(Σ\|예측 − m\| ≤ 0.5 × Σ\|1 − m\|)**. Σ\|1 − m\|/4 < 0.01이면 skill `NOT_INFORMATIVE`. m은 replicate 짝 비의 중앙값, CI는 percentile bootstrap(10,000회, `random.Random(20262420)`, `main_judge.boot_ci` 그대로) |
| §5.3 순위 | N마다 세 쌍. CI가 1을 포함하지 않는 쌍만 해소된 쌍이다. 해소된 모든 쌍에서 (1)의 turn당 가격 순서 = 관측 순서이면 PASS. 해소된 쌍이 없으면 `UNRESOLVED` |
| §5.6 h | decode-only h(개정 1 §7.4). 6 cell TVD 중앙값 ≤ 0.10 ∧ 최댓값 ≤ 0.20 ∧ skill(중앙값 ≤ 0.5 × 균등 {1..8}의 TVD 중앙값). `reqs` 정의는 병기 |
| **추가 확증** | **(1)이 (3)보다 BASE 재사용 오차(Σ\|예측 − 관측\|, 2 cell)와 비용 비 Σ 오차(4 cell)가 모두 작다**(두 bound 모두) → `CONFIRMED`, 아니면 `NOT_CONFIRMED` |
| 보고(판정 없음) | (1) 대 (2)·(2′)의 같은 두 오차, cell별 네 예측기 대 관측, replicate별 BASE 재사용, 직접/가격 채널 비 |

- 판정 script: `blind_judge.py`(측정 전 commit). 측정 뒤 한 번만 실행한다. 판정 전에 script 버그로 수정이 필요하면 멈추고 고친 뒤 기록한다.
- **사실 기록**: 판정 script는 GTASK11 run을 symlink로 엮은 가짜 run(N24 → "N25", N22 → "N28")에서 코드 경로만 시험했다. blind cell 데이터는 존재하지 않는다.

## 6. 사전 예측 (기록용, 판정 아님)

| 항목 | 예측 |
|---|---|
| §5.1 (1) | PASS 쪽. 다만 BASE cell은 plan 간 산포가 커서 (a)의 0.10이 위험하다 |
| §5.2 (1) | 기본 기준 FAIL 쪽. 비 효과는 약 0.10으로 크지만 붕괴 cell은 replicate 산포가 커서(GTASK11 N24 비 CI 폭 0.15–0.16) 중앙값 m이 흔들리고, 기본 기준 0.03은 그보다 훨씬 좁다. 강화 기준은 CI가 넓어 통과하기 쉽다 |
| §5.3 | PASS. BASE 포함 쌍은 해소되고 POOL 대 POOL+GRID는 미해소일 것이다 |
| §5.6 (1) | PASS 쪽 |
| 추가 확증 | CONFIRMED 쪽. (3)은 N25 BASE를 0.70으로 높게 예측한다 |
| (1) 대 (2) | 차이는 replicate 산포보다 작을 것이다(BASE 재사용 0.02–0.05 차) |
