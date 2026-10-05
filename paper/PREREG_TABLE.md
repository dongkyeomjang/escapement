# 선등록 대조표 — 실험별 모형 버전·보정 자료·예측 commit·측정 시작

작성: 2026-10-05, Advisor 지시문 15 작업 D. **측정 0, 예측 0.** 기존 TASK/GTASK 기록과 git commit 시각, 이 host에 남은 raw run의 `measurement-start.txt`·`git-head.txt`에서 옮긴 값만 적는다.

**시간대**: NPU 기록은 KST(+09:00), GPU 기록은 UTC(+00:00)다. GPU 행은 원 기록의 UTC 값을 적고 괄호 안에 KST 환산을 붙인다. commit 시각은 `git log -1 --format='%H %cI' <hash>`의 committer date다.

**선후 확인 근거 표기**:

- `start file` — 이 host의 raw run `measurement-start.txt`(NPU)에서 직접 확인
- `git-head` — run이 기록한 `git-head.txt` = 예측 commit(NPU, 이 host에서 직접 확인). 같은 초일 때 commit이 먼저라는 근거
- `문서` — TASK/GTASK "재현 정보"에 적힌 값만 있음. GPU raw(`results/gpu/…`)는 이 host에 없어 대조하지 못했다

## 1. 확증·탐색 실험

| # | 실험 | 기록 (선등록 / 측정) | 모형 버전 (주 예측기 **굵게**) | 보정(파라미터)에 쓴 자료 | 예측 commit, 시각 | 측정 시작 | 선후 확인 근거 | 검증 조건 (N, 구성) | 판정 종류 |
|---|---|---|---|---|---|---|---|---|---|
| 1a | NPU 저부하 | [TASK80](../docs/research/TASK80.md)·[TASK81](../docs/research/TASK81.md) / [TASK82](../docs/research/TASK82.md) ([MULTITURN_MAIN_PREREG.md](../docs/research/MULTITURN_MAIN_PREREG.md)) | **v1 해석**(`mt_predict.analytic`); sim legacy(`sim_default`, `semantics="legacy"` 기본 스위치); sim legacy + 관측 의미론 스위치(`sim_observed`: `release_rule="immediate"`, `dummy_mode="pre_evict"` — TASK84에서 `semantics="descriptor"`와 75/75 run 동일) | decode step TASK13(b8 artifact; 폭 3·6·10·16은 `descriptor_for` 선형 보간·외삽), 배타 prefill TASK22, pool TASK08·TASK14(outer slot = batch), hit 단위 TASK11(128), 의미론 TASK72(즉시 release·`pre_evict`). 파일럿(TASK79) 측정값 미사용 | 예측 초판 `eedf5edb28b7caa98c5dfed7fc0c25530fb11a37` 2026-09-29T19:13:53+09:00 (`PREDICTIONS.json`, r0–r4); 개정 2 `5f62fb4630b15095c6a289ad645f1b765c2df8b4` 2026-09-30T00:54:27+09:00 (기준 개정, N = 8 DP, `PREDICTIONS_EXT.json` r5–r9). 기록 commit `aa63212` 01:05:23 | 2026-09-30T01:05:28+09:00 (종료 05:48:28) | start file, git-head = `aa63212` | N = 6·8·10 × BASE·BATCHONLY·TUNED × r0–r4; N = 8 DP 격자 (1,2,3,4,6,16) b16 r0–r9 와 N = 8 TUNED r5–r9(§5.4); 75 lifecycle 중 확증 몫 | 확증 |
| 1b | NPU 저부하 (N = 12) | 위와 같음 | 위와 같음 | 위와 같음 | `eedf5ed` 2026-09-29T19:13:53+09:00 | 위 run 안 | 위와 같음 | N = 12 × BASE·BATCHONLY·TUNED × r0–r4 | 탐색(모든 항목) |
| 2 | NPU 대기열 N = 14·16 | [TASK86](../docs/research/TASK86.md) / [TASK87](../docs/research/TASK87.md) ([HILOAD_PREREG.md](../docs/research/HILOAD_PREREG.md)) | **v1.1**(TASK85 동결 `ffd716f` 2026-10-01T01:48:50+09:00, `survival_v11.py`·`mt_predict_v11.py`·`predict_v11.py`); v1 해석; sim descriptor(`semantics="descriptor"`, 원래 비용) | TASK13 step, TASK22 prefill, descriptor v2 pool·의미론(TASK84). v1.1: plan별 gap 법칙 EM 적합(plan 파일), 구조는 개발 집합 TASK82 N = 12 관측으로 정함(TASK85) | `f75c8e7546e88f7a829b943902f597a9d04d9779` 2026-10-01T01:49:49+09:00. 기록 commit `fa1a23d` 01:50:24 | 2026-10-01T01:50:32+09:00 (종료 03:55:55) | start file, git-head = `fa1a23d` | N = 14·16 × BASE·BATCHONLY·TUNED × r0–r4 (30 lifecycle) | 확증 |
| 3 | NPU N = 13·17·20 | [TASK93](../docs/research/TASK93.md) / [TASK95](../docs/research/TASK95.md) ([SIMBLIND_PREREG.md](../docs/research/SIMBLIND_PREREG.md)) | **sim + 운영 비용**(`sim_op`: 시간 진행 = TASK92 운영 비용, 가격 = 원래 비용, `semantics="descriptor"`); sim descriptor(원래 비용); v1(참고, N > 동시 실행 상한 cell은 범위 밖) | `OPCOST_SIM.json`(TASK92, artifact별 decode `F[b] + β·n`과 배타 prefill), 가격·(2)는 TASK13·TASK22. TASK91 관측 비율, TASK82·87 배율 미사용 | `cc29e769e76e8bfe98c0402f528ea76390a3555a` 2026-10-02T00:49:42+09:00 | 2026-10-02T00:49:42+09:00 (종료 03:59:53) | 같은 초; git-head = `cc29e76`, run.log 첫 줄 00:49:42 | N = 13·17·20 × BASE·BATCHONLY·TUNED × r0–r4 (45 lifecycle); §5.1에서 N = 20 BASE 제외 | 확증 |
| 4 | NPU N = 15·18 | [TASK101](../docs/research/TASK101.md) / [TASK102](../docs/research/TASK102.md) ([CTXBLIND_PREREG.md](../docs/research/CTXBLIND_PREREG.md)) | **sim + context 비용**(`sim_ctx_op`: decode = context 비용, 배타 prefill = TASK92 운영 비용, 가격 = 원래 비용; `SimConfig.decode_cost_fn` hook으로 구현, TASK103에서 descriptor `context_cost` 경로와 6 cell 정확 일치); sim descriptor(원래 비용); v1(참고, 범위 밖 cell 있음); `sim_ctx`(보고만) | `CTXCOST_BLIND.json`(BASE·TUNED TASK97 F1, BATCHONLY TASK100 F1), `OPCOST_SIM.json` prefill(TASK92), 가격 TASK13·TASK22 | `cb1eec4b8014cfd36a3c405c23d94318aa4fe75f` 2026-10-02T18:02:44+09:00 | 2026-10-02T18:02:44+09:00 (종료 20:03:37) | 같은 초; git-head = `cb1eec4`, run.log 첫 줄 18:02:44 | N = 15·18 × BASE·BATCHONLY·TUNED × r0–r4 (30 lifecycle) | 확증 |
| 5 | GPU 순차 | [GTASK04](../docs/research/gpu/GTASK04.md) ([GPU_SURVIVAL_PREREG.md](../docs/research/gpu/GPU_SURVIVAL_PREREG.md)) | 모형 코드 순차 경로(`survival.sequential_window(resume_allocates_first=False)` + `reusable_tokens(granularity="block")`), block-exact replay(`gpu_pool_replay.py`)로 검산 후 commit. 비용 입력 없음 | GPU 의미론 GTASK01(source-read)·GTASK02(측정): 용량 C = 800 block, 단위 16 token, 소비 `ceil((P+g−1)/16)`, 캐시 prefix `floor((P+g−1)/16)·16` | `87731c52d6cc0b61f9d1ac976c3ab5541b29cf91` 2026-09-29T09:37:14+00:00 (18:37:14 KST) | 2026-09-29T09:37:25Z 첫 trial 기동 (18:37:25 KST; 종료 10:21:01Z) | 문서 | 60 trial((i) 32, (ii) 28; target 2,000 token, 배경 500·1,000·2,000·4,000 token × m), 동시성 1, `--num-gpu-blocks-override 801 --max-num-seqs 1 --max-num-batched-tokens 2048`, capture (1,2,4,8,16) | 확증 |
| 6a | GPU 상한 근처 | [GTASK09](../docs/research/gpu/GTASK09.md) / [GTASK11](../docs/research/gpu/GTASK11.md) ([GPU_MULTITURN_PREREG.md](../docs/research/gpu/GPU_MULTITURN_PREREG.md)) | **해석 v1 GPU 인스턴스**(`gpu_mt_model.analytic`); sim LRU(`gpu_mt_sim`, 병기); sim FIFO(반사실, §5.5). 비용 bound `lo`·`hi` 각각 | GTASK05 가격(`gpu_cost.py`: FULL `F[b] + g·n`, eager decode, PIECEWISE·eager prefill 증분 lo/hi), 의미론 GTASK01–04, 구성 GTASK08(`selection.json`) | 예측 `2bef619850953295caafd57f5b900deddc8bdc6c` 2026-09-29T17:54:17+00:00 (09-30 02:54:17 KST); 기준 개정 1 `721e4d01a2a0468920de13d87de1cfd0236f21aa` 2026-09-30T14:11:43+00:00 (23:11:43 KST), 예측 파일 불변(SHA256 `1be9a991…`) | 2026-09-30T14:11:50Z 첫 lifecycle (23:11:50 KST; 종료 17:26:57Z) | 문서 | N = 20·22·24 × BASE(pool 1,900)·POOL(2,300)·POOL+GRID(2,300, 격자 (1,5,7,8,16)) × r0–r4 (45 lifecycle), `max_num_seqs` 8, budget 2048 | 확증 |
| 6b | GPU 상한 근처 (N = 26) | 위와 같음 | 위와 같음 | 위와 같음 | `2bef619` 2026-09-29T17:54:17+00:00 | 위 run 안 | 문서 | N = 26 × BASE·POOL × r0–r4 (10 lifecycle) | 탐색(모든 항목) |
| 7 | GPU 포화 | [GTASK20](../docs/research/gpu/GTASK20.md) ([GPU_BLIND_COLLAPSE_PREREG.md](../docs/research/gpu/GPU_BLIND_COLLAPSE_PREREG.md)) | 모두 sim LRU(`gpu_mt_sim`), step 시간 입력만 다름: **(1) `ctx`**(가격 + context 비용); (2) `x1.210`; (2′) `mode_dist`; (3) `price`. bound `lo`·`hi` | (1) GTASK05 가격 + GTASK18 c = 2.120e-4 ms/token, 기준 128 token/decode; (2) GTASK13 ×1.210(GTASK11 관측으로 맞춘 보정 예측); (2′) GTASK11 관측 mode별 비 분포(GTASK13 `obs.json`); (3) GTASK05 가격. 구성 GTASK08 + `blind_grids.json` | `f0d8000ee905d8ba71afec93db489b74c17930e7` 2026-10-02T06:55:28+00:00 (15:55:28 KST) | 2026-10-02T06:55:28Z (15:55:28 KST; 종료 08:48:24Z) | 같은 초; 문서상 `start_commit.txt` = `f0d8000` | N = 25·28 × BASE·POOL·POOL+GRID((1,5,7,8,16)) × r0–r4 (30 lifecycle) | 확증 |

## 2. 사후 대조 (자료가 선등록보다 먼저 존재)

| # | 대조 | 기록 | 모형 버전 | 대조 자료 | 선등록 commit, 시각 | 계산 시작 | 선후 확인 근거 | 조건 | 판정 종류 |
|---|---|---|---|---|---|---|---|---|---|
| R1 | NPU 순차 생존 | [TASK72](../docs/research/TASK72.md) ([MODEL_V0_RETRO_PREREG.md](../docs/research/MODEL_V0_RETRO_PREREG.md)) | 모형 v0(`src/continuum/model/`, B1 생존) | TASK14·15·58·63·64 기존 측정 | 초판 `8c107a01d09fd6327cd7457e5e7d64ad2abf0b80` 2026-09-29T16:02:52+09:00; 개정 1 `1728f0d7322ca62093371f2c79486d7e1eefed61` 2026-09-29T16:25:38+09:00 | 2026-09-29T16:29:09+09:00 | `r1.json` `computed_at` 16:29:09 (이 host) | P1 29, P2 36, P3·P4 140 | 사후 대조(선등록 상 확증 항목) |
| R5′ | NPU 사건 순서 재생 | TASK72 | 서버 사건 순서 재생(`reference.FifoReplay`) | TASK40·50·54 기존 run 7개, 재도착 1,298 | 위와 같음 | 2026-09-29T16:30:03+09:00 첫 실행, 16:31:04 재실행 | `r5p.json` `computed_at` 16:31:04 (이 host), TASK72 실행 경위 | 1,298 재도착 | 사후 대조(선등록 상 확증 항목) |

## 3. 파라미터 측정 (보정 입력; 모형 판정 아님)

| 측정 | 기록 | 산출 → 사용처 | 설계·선등록 commit, 시각 | 측정 시작 | 선후 확인 근거 |
|---|---|---|---|---|---|
| NPU decode step 비용 | [TASK13](../docs/research/TASK13.md) | `STEP_COST`(b8) → 1a·1b·2 전 예측기, 3·4의 가격·(2) | `241b7b8084464d1d460c1d9607c9ecca305b4af8` 2026-08-19T19:48:25+09:00 | 2026-08-19T19:48:46+09:00 | start file |
| NPU 배타 prefill 비용 | [TASK22](../docs/research/TASK22.md) | `PREFILL_COST` → 1a·1b·2 전 예측기, 3·4의 가격·(2) | `ba6ee2bdee53266e339c7f8b4cb73e7f4f96f7a5` 2026-08-21T22:00:47+09:00 | 2026-08-21T22:01:09+09:00 | start file |
| NPU 운영 조건 step 비용 | [TASK92](../docs/research/TASK92.md) | `OPCOST_SIM.json` → 3(주), 4(prefill) | 설계 `6f0195aa01b1cf9019439c9fe047eb490facef3e` 2026-10-01T16:58:28+09:00; 개정 1 `8aa3801` 2026-10-02T00:09:56+09:00; 개정 2 `f812705` 2026-10-02T00:21:29+09:00 | 2026-10-01T16:58:35+09:00; 보충 1 00:08:16; 보충 2 00:21:29 | start file; git-head `6f0195a`·`6f0195a`·`f812705`. **개정 1은 보충 1 시작 뒤 commit**(TASK92 기록) |
| NPU context 비용 (BASE·TUNED) | [TASK97](../docs/research/TASK97.md) | `CTXCOST_BLIND.json` → 4(주) | `dfd908db70f7df0a7c239a463c991657659eb0f0` 2026-10-02T15:38:32+09:00 | 2026-10-02T15:38:32+09:00 | 같은 초; git-head = `dfd908d` |
| NPU context 비용 (BATCHONLY) | [TASK100](../docs/research/TASK100.md) | `CTXCOST_BLIND.json` → 4(주) | `f91b8e27e64ad76dec670cbe86a4ea4594ccb44e` 2026-10-02T17:01:26+09:00 | 2026-10-02T17:01:26+09:00 | 같은 초; git-head = `f91b8e2` |
| GPU step 비용 (가격) | [GTASK05](../docs/research/gpu/GTASK05.md) | `gpu_cost.py` → 6a·6b 전 예측기, 7의 (1)·(3) | 선등록 `fc2d0ab` 2026-09-29T09:41:05+00:00; 개정 1 `e7f9b45` 2026-09-29T16:06:58+00:00; 개정 2 `05ceda4` 2026-09-29T16:24:30+00:00 | 2026-09-29T16:07:03Z (09-30 01:07:03 KST; 종료 16:21:02Z) | 문서. **개정 2는 측정 뒤 commit**(분석 개정, step 시간 수치 확인 전 — GTASK05 기록) |
| GPU 운영 조건 step 비용 | [GTASK17](../docs/research/gpu/GTASK17.md) | 직접 입력 아님(GTASK20 문서: (3) 가격 = GTASK17 곡선) | `b59287c` 2026-10-01T07:32:42+00:00 | 2026-10-01T07:32:42Z (16:32:42 KST) | 같은 초; 문서상 `start_commit.txt` = `b59287c` |
| GPU context 비용 | [GTASK18](../docs/research/gpu/GTASK18.md) | c = 2.120e-4 ms/token → 7의 (1) | `b64eff35bdb5489ae68f964226775bdcca4e2f43` 2026-10-02T06:39:39+00:00 | 2026-10-02T06:39:44Z (15:39:44 KST) | 문서; 문서상 `start_commit.txt` = `b64eff3` |
| GPU 시간 척도 ×1.210·mode_dist | [GTASK13](../docs/research/gpu/GTASK13.md) | 7의 (2)·(2′) | 측정 없음 — GTASK11 관측(개발 집합)에서 도출 | — | — |

## 4. 출처 대조에 쓴 명령

```bash
git log -1 --format='%H %cI' <hash>
cat results/npu/stage3/{20260930-main,20261001-hiload,20261002-simblind,20261002-ctxblind,20261001-stepcost-op,20261002-ctxcost,20261002-ctxcost-bo}/{measurement-start,git-head}.txt
cat results/npu/stage2/{20260819-194900-decode-cost,20260821-220100-prefill-tax}/measurement-start.txt
git log --format='%h %cI' -- experiments/npu/stage3/plans/main/PREDICTIONS*.json experiments/gpu/survival/prediction/predictions.json experiments/gpu/multiturn/plans/PREDICTIONS.json experiments/gpu/multiturn/plans/blind/PREDICTIONS_BLIND.json
```

- 모든 예측 파일(`PREDICTIONS.json`, `PREDICTIONS_EXT.json`, `PREDICTIONS_HI.json`, `PREDICTIONS_SIM.json`, `PREDICTIONS_CTX.json`, GPU `predictions.json`, `PREDICTIONS.json`, `PREDICTIONS_BLIND.json`)의 git 이력은 위 예측 commit 1개뿐이다(commit 뒤 변경 없음).
- 이 host에 `results/gpu/`가 없다. GPU 행의 측정 시작 시각과 `start_commit.txt`는 GTASK 문서 값이다.

## 5. 판정 기준 대조표 (Advisor 지시문 16 작업 D-1)

작성 기준 HEAD `ea674be`(2026-10-05). 기준은 각 선등록 문서, 결과는 NPU verdict JSON(`results/npu/stage3/{20260930-main/main_verdict.json, 20261001-hiload/hiload_verdict.json, 20261002-simblind/simblind_verdict.json, 20261002-ctxblind/ctxblind_verdict.json}`), GPU GTASK20 `experiments/gpu/multiturn/blind_result/verdict.json`, GTASK04·GTASK11 문서에서 옮겼다. 기존 판정을 바꾸지 않는다.

**오차 계산식 기호**

- **E1**(재사용): `e_c = 예측_c − 관측_c`. 관측 = cell의 r0–r4 합산 `Σ hit / Σ (turn ≥ 1)`(요청 단위). `MAE = mean_c |e_c|`, 평균 부호 오차 = `mean_c e_c`.
- **E2**(비용 비): `m`, `[l, u]` = replicate 짝 비(구성/BASE)의 중앙값과 95 % bootstrap CI. 기본 = `|p − m| ≤ 0.03 ∧ sign(1 − p) = sign(1 − m)`(CI가 1을 포함하면 방향 대신 `|p − 1| ≤ 0.03`). 강화 = `p ∈ [l − 0.01, u + 0.01]`. `S = Σ_c |p_c − m_c|`.
- **E3**(순위): 쌍 X/Y의 짝 비 m·CI. 해소 ⇔ `1 ∉ [l, u]`. 일치 ⇔ 예측 싼 쪽 = 관측 싼 쪽(STATISTICS.md 2.1).
- **E4**(점유 분포): `TVD_c = ½ Σ_n |h_pred,c(n) − h_obs,c(n)|`. NPU h = `[BUCKET] request_nums` step 가중, GPU h = decode-only step 가중(GPU 개정 1 §7.4).
- 최종 표기(전 실험 공통): 기존 기준 FAIL → `FAIL`; 기존 PASS ∧ skill PASS → `PASS`; skill `NOT_INFORMATIVE` → `PASS (skill NOT_INFORMATIVE)`; skill FAIL → `NOT_CONFIRMED (base PASS, skill FAIL)`.
- GPU는 `lo`·`hi` bound마다 판정하고 **PASS는 두 bound 모두**에서 성립해야 한다.

| 실험 | 지표 | 판정 예측기 (그 밖) | 오차 계산식 | 통과 문턱 | 무정보 예측(영) 정의 | 적용 cell | 판정 결과 |
|---|---|---|---|---|---|---|---|
| TASK82 | §5.1 재사용 | 해석 v1 (sim_default, sim_observed 같은 계산) | E1 | `\|e_c\| ≤ 0.10` ≥ 9/10 cell ∧ `\|mean e\| ≤ 0.05` ∧ `MAE ≤ 0.5 × MAE(영)` | 상수 0.67635 = 675/998(TASK73 A4 개발 집합). 관측 범위 < 0.10이면 skill `NOT_INFORMATIVE` | 확증 10(N 6·8·10 × 3 구성 + DP N8) | **PASS**: 10/10, mean −0.012, MAE 0.0142 / 영 0.1746(비 0.08). sim 둘 PASS(MAE 0.0037·0.0036) |
| TASK82 | §5.2 비용 비 | 해석 v1 (sim 둘) | E2 | 기본 7/7 ∧ 강화 ≥ 6/7 ∧ `S ≤ 0.5 × Σ\|1 − m\|` | 모든 cell 1.0. `mean\|1 − m\| < 0.01`이면 `NOT_INFORMATIVE` | 7(BATCHONLY·TUNED × 3 N + DP N8) | **PASS**: 7/7, 7/7, S 0.048 / Σ\|1 − m\| 0.187(0.26). sim_default 0.21, sim_observed 0.17 PASS |
| TASK82 | §5.3 순위 | 해석 v1 (sim 둘 보고) | E3 | 해소된 모든 쌍 일치. 해소 0이면 N은 `UNRESOLVED` | 없음(skill 미적용) | N 6·8·10, 12쌍(N8 4구성 6쌍) | **PASS**: N6 `UNRESOLVED`, N8 4/4, N10 3/3 |
| TASK82 | §5.6 점유 h(n) | 해석 B2 (sim 둘) | E4 | TVD 중앙 ≤ 0.10 ∧ 최대 ≤ 0.20 ∧ 중앙 < 영 중앙 | 원고 Table I 같은 N 행의 관측 h(N8 합산 정정은 HILOAD_PREREG §4.1) | 확증 10 | **PASS**: 0.061 / 0.074, 영 중앙 0.296 |
| TASK82 | 추가 §5.4 DP 대 TUNED | — | 짝 비 DP/TUNED, k = 10(r0–r9) | PASS ⇔ u < 1, FAIL ⇔ l > 1 | — | N8 | **INCONCLUSIVE** 0.9920 [0.9857, 1.0050](사전 예측과 같음) |
| TASK82 | 추가 §5.5 H-sim | sim_default | `e = m − 예측`(비) | (a) 양수 개수 양측 이항 p ≥ 0.05 ∧ (b) median\|e\| < 0.0130 | — | 7 비 cell | **SUPPORTED**: 양 1/7(p 0.125), median 0.0055 |
| TASK87 | §5.1 | v1.1 (v1, sim) | E1 | 6/6 ∧ `\|mean e\| ≤ 0.05` ∧ skill 0.5× | 0.67635 | 6(N 14·16 × 3) | **FAIL**: v1.1 5/6(N14 BASE −0.125), MAE 0.049(skill 0.22 PASS). v1 FAIL 5/6, sim PASS(MAE 0.013) |
| TASK87 | §5.2 | v1.1 (v1, sim) | E2 | 기본 4/4 ∧ 강화 4/4 ∧ skill 0.5× | 1.0 | 4 | **FAIL**: v1.1 기본 3/4, 강화 4/4, S 0.087 / 1.012. v1 기본 0/4, sim 기본 0/4 |
| TASK87 | §5.3 | v1.1 (v1, sim) | E3 | 같음 | 없음 | 6쌍 | **PASS**: 6/6 해소, 6/6 일치 |
| TASK87 | §5.6 | v1.1 (v1, sim) | E4 | 중앙 ≤ 0.10 ∧ 최대 ≤ 0.20 ∧ 중앙 < 영 | Table I(N14 = 12·16 행 합산, N16 행) | 6 | **PASS**: 0.099 / 0.171, 영 0.541 |
| TASK87 | 추가 v1.1 대 v1 | v1.1 | 재사용 MAE, 비 S | 둘 다 v1.1 < v1 | — | 6 / 4 | **FAIL**: 재사용 0.049 > 0.033, 비 0.087 < 0.358 |
| TASK95 | §5.1 | sim_op (sim; v1 참고) | E1 | 8/8 ∧ `\|mean e\| ≤ 0.05` ∧ skill 0.5× | 0.67635 | 8(9 cell − N20 BASE, 사용자 결정 "정보 없음") | **PASS**: 8/8, mean +0.010, MAE 0.016(0.08). sim PASS, v1(범위 밖 포함, 참고) FAIL |
| TASK95 | §5.2 | sim_op (sim; v1 참고) | E2 | 기본 6/6 ∧ 강화 ≥ 5/6 ∧ skill 0.5× | 1.0 | 6(분모 BASE는 N20 포함) | **PASS**: 6/6, 6/6, S 0.109 / 1.440. sim FAIL(기본 5/6) |
| TASK95 | §5.3 | sim_op (sim, v1) | E3 | 같음 | 없음 | 9쌍 | **PASS**: N13 3/3, N17 3/3, N20 2/2(+ 미해소 1) |
| TASK95 | §5.6 | sim_op (sim, v1) | E4 | 중앙 ≤ 0.10 ∧ 최대 ≤ 0.20 ∧ 중앙 < 영 | Table I(N13 = 12·16 합산, N17·20 = 16 행) | 9(N20 BASE 포함) | **PASS**: 0.060 / 0.119, 영 0.586 |
| TASK95 | 추가 sim_op 대 sim | sim_op | 재사용 MAE(8 cell), 비 S(6 cell) | 둘 다 sim_op < sim | — | 8 / 6 | **FAIL**: 0.0161 > 0.0132, 0.1086 > 0.1017 |
| TASK102 | §5.1 | sim_ctx_op (sim; sim_ctx 보고; v1 참고) | E1 | 6/6 ∧ `\|mean e\| ≤ 0.05` ∧ skill 0.5× | 0.67635 | 6(N 15·18 × 3) | **PASS**: 6/6, mean −0.0015, MAE 0.0090(0.035) |
| TASK102 | §5.2 | sim_ctx_op | E2 | 기본 4/4 ∧ 강화 4/4 ∧ skill 0.5× | 1.0 | 4 | **PASS**: 4/4, 4/4, S 0.049 / 1.109 |
| TASK102 | §5.3 | sim_ctx_op | E3 | 같음 | 없음 | 6쌍 | **PASS**: N15 3/3, N18 2/2(+ 미해소 1) |
| TASK102 | §5.6 | sim_ctx_op | E4 | 중앙 ≤ 0.10 ∧ 최대 ≤ 0.20 ∧ 중앙 < 영 | Table I(N15 = 12·16 합산, N18 = 16 행) | 6 | **PASS**: 0.034 / 0.046, 영 0.588 |
| TASK102 | 추가 sim_ctx_op 대 sim | sim_ctx_op | 재사용 MAE(6), 비 S(4) | 둘 다 sim_ctx_op < sim | — | 6 / 4 | **PASS**: 0.0090 < 0.0093, 0.049 < 0.054 |
| GTASK04 | 순차 생존(resume hit token) — §5.x 구조 없음 | 모형 코드 순차 경로(= block-exact replay) | trial마다 `ch1 − 예측`(정수 token), 채널 일치 ch1 = ch2 = ch3, ch4 = 예측 T 축출 block | **60/60 유효 ∧ 채널 일치 ∧ ch1 = 예측(허용 오차 0)** | 정의 없음 | 60 trial | **CONFIRMED** 60/60 |
| GTASK11 | §5.1 | 해석 v1 (sim LRU 병기, sim FIFO 반사실) | E1, bound별 | (a) 9/9 `\|e_c\| ≤ 0.10` ∧ (b) `\|mean e\| ≤ 0.05` ∧ (c) `MAE ≤ 0.5 × MAE(영)` | 상수 0.84718 = 5,771/6,812(TASK82 확증 10 cell). `MAE(영) < 0.05`이면 skill `NOT_INFORMATIVE` | 확증 9(N 20·22·24 × 3) | **해석 FAIL**((a) N24 BASE +0.138, skill 0.66). **sim LRU PASS**(MAE 0.0173, skill 0.35·0.31). sim FIFO FAIL(mean −0.102). MAE(영) 0.0502 |
| GTASK11 | §5.2 | 해석 v1 (sim LRU, sim FIFO) | E2, bound별 | 기본 6/6 ∧ 강화 ≥ 5/6 ∧ skill 0.5× | 1.0. `Σ\|1 − m\|/6 < 0.01`이면 `NOT_INFORMATIVE` | 6 | **해석 FAIL**(N24 두 cell 기본·강화 불통, S 0.146 / 0.209). **sim LRU PASS**(6/6, 6/6, skill 0.36·0.37). sim FIFO FAIL(S 0.108, 0.52) |
| GTASK11 | §5.3 | 해석 v1 | E3, bound별 | 같음 | 없음 | 9쌍(N 20·22·24) | **PASS** ×3(lo; hi 같음) |
| GTASK11 | 추가 §5.4 POOL+GRID 대 POOL | — | 짝 비 m·CI | PASS ⇔ u < 1, FAIL ⇔ l > 1 | — | N 20·22·24 | **INCONCLUSIVE** ×3(사전 예측과 같음) |
| GTASK11 | 추가 §5.5 LRU 대 FIFO | sim LRU 대 sim FIFO | `d_L`, `d_F`(예측 = lo·hi 평균, DEFINITIONS.md §8) | d_L < d_F ≥ 7/9 분리 cell ∧ Σd_L < Σd_F | — | 분리 9(\|L − F\| ≥ 0.07 두 bound) | **LRU_SUPPORTED**: 8/9, 0.148 대 0.937 |
| GTASK11 | §5.6 | 해석 B2 (sim LRU 보고) | E4(decode-only h), bound별 | 중앙 ≤ 0.10 ∧ 최대 ≤ 0.20 ∧ 중앙 ≤ 0.5 × 영 중앙 | 균등 {1..8} | 9 | **PASS**: lo 0.081 / 0.184(영 0.645), hi 0.077 / 0.179. 병기 `reqs` 정의 FAIL(최대 0.212) |
| GTASK20 | §5.1 | ctx (x1.210, mode_dist, price 보고) | E1, bound별 | 6/6 ∧ `\|mean e\| ≤ 0.05` ∧ skill 0.5× | 0.84718. `MAE(영) < 0.05`이면 `NOT_INFORMATIVE` | 6(N 25·28 × 3) | **PASS**: MAE lo 0.022 / hi 0.023, 영 0.233. x1.210·mode_dist PASS, price FAIL(mean +0.108) |
| GTASK20 | §5.2 | ctx | E2, bound별 | 기본 4/4 ∧ 강화 ≥ 3/4 ∧ skill 0.5× | 1.0. `Σ\|1 − m\|/4 < 0.01`이면 `NOT_INFORMATIVE` | 4 | **PASS**: 4/4, 4/4, S lo 0.040 / 0.392, hi 0.028 / 0.406. price FAIL(기본 2/4) |
| GTASK20 | §5.3 | ctx | E3, bound별 | 같음 | 없음 | 6쌍 | **PASS**(N25·28, 두 bound) |
| GTASK20 | §5.6 | ctx | E4(decode-only h), bound별 | 중앙 ≤ 0.10 ∧ 최대 ≤ 0.20 ∧ 중앙 ≤ 0.5 × 영 중앙 | 균등 {1..8} | 6 | **PASS**: lo 0.049 / 0.052(영 0.763), hi 0.048 / 0.051. 네 예측기 모두 PASS |
| GTASK20 | 추가 ctx 대 price | ctx | BASE 재사용 Σ\|e\|(2 cell), 비 S(4 cell) | 두 지표 모두 ctx < price, 두 bound | — | 2 / 4 | **CONFIRMED**: lo 0.075 < 0.348, 0.040 < 0.135; hi 0.084 < 0.319, 0.028 < 0.110 |

- NPU와 GPU의 §5.6 skill 식이 다르다: NPU는 `중앙 < 영 중앙`(영 = Table I 관측 h), GPU는 `중앙 ≤ 0.5 × 영 중앙`(영 = 균등).
- §5.1 영 예측기: NPU는 개발 집합 상수 0.67635, GPU는 NPU 본 측정 상수 0.84718(기판 무관 예측). GPU 초판 §5의 "같은 예측기의 같은 N BASE 값"은 개정 1 §7.2에서 판정에서 빠졌다(구성 차이 설명력 보고로만 남음).
- GTASK11 §5.1·5.2·5.3의 수치는 GTASK11 문서 값이다(verdict는 GPU host에만 있다).

## 6. 순위(§5.3) 쌍 집계표 (Advisor 지시문 16 작업 D-2)

- **전체 쌍**: N마다 구성 쌍 전부(3구성 3쌍, TASK82 N8은 DP 포함 4구성 6쌍). 탐색 N(TASK82 N12, GTASK11 N26)은 §5.3 대상이 아니라 세지 않는다.
- **방향 일관 쌍**: replicate 짝 비 5개가 모두 1의 같은 쪽 ⇔ 해소 쌍. k = 5에서 CI = [최솟값, 최댓값]이므로 두 정의가 같다(STATISTICS.md 1.1 [파생]). GTASK20은 verdict의 `ratios` 5개로 직접 확인했다.
- **판정 제외 쌍** = 미해소 쌍(일치·불일치 어느 쪽으로도 세지 않음).
- 출처: NPU `5.3.per_n.<N>.pairs[*].{resolved, <예측기>_agrees}`, GTASK20 `5.3.<bound>.<N>.pairs.*.{resolved, observed_cheaper, predicted_cheaper}`, GTASK11 §5.3 표(해소 여부)와 `PREDICTIONS.json` `device_per_turn_s`(예측 싼 쪽).

| 실험 | 예측기 (역할) | bound | 전체 쌍 | 방향 일관(해소) 쌍 | 그중 예측과 일치 | 판정 제외(미해소) 쌍 |
|---|---|---|---|---|---|---|
| TASK82 | 해석 v1 (판정) | — | 12 | 7 | 7 | 5 (N6 3쌍, N8 BATCHONLY/TUNED·TUNED/DP) |
| TASK82 | sim_default (보고) | — | 12 | 7 | 7 | 5 |
| TASK82 | sim_observed (보고) | — | 12 | 7 | 7 | 5 |
| TASK87 | v1.1 (판정) | — | 6 | 6 | 6 | 0 |
| TASK87 | v1 (보고) | — | 6 | 6 | 6 | 0 |
| TASK87 | sim (보고) | — | 6 | 6 | 6 | 0 |
| TASK95 | sim_op (판정) | — | 9 | 8 | 8 | 1 (N20 BATCHONLY/TUNED) |
| TASK95 | sim (보고) | — | 9 | 8 | 8 | 1 |
| TASK95 | v1 (참고, 범위 밖 cell 포함) | — | 9 | 8 | 8 | 1 |
| TASK102 | sim_ctx_op (판정) | — | 6 | 5 | 5 | 1 (N18 BATCHONLY/TUNED) |
| TASK102 | sim (보고) | — | 6 | 5 | 5 | 1 |
| TASK102 | sim_ctx (보고) | — | 6 | 5 | 5 | 1 |
| TASK102 | v1 (참고) | — | 6 | 5 | 5 | 1 |
| **NPU 판정 예측기 합** | | | **33** | **26** | **26** | **7** |
| GTASK11 | 해석 v1 (판정) | lo | 9 | 6 | 6 | 3 (POOL/POOL+GRID × N 20·22·24) |
| GTASK11 | 해석 v1 (판정) | hi | 9 | 6 | 6 | 3 (문서 "hi 같음") |
| GTASK11 | sim LRU [사후] | lo / hi | 9 | 6 | 6 | 3 |
| GTASK11 | sim FIFO [사후] | lo / hi | 9 | 6 | 6 | 3 |
| GTASK20 | ctx (판정) | lo | 6 | 4 | 4 | 2 (POOL/POOL+GRID × N 25·28) |
| GTASK20 | ctx (판정) | hi | 6 | 4 | 4 | 2 |
| GTASK20 | x1.210 / mode_dist / price (보고) | lo, hi 각각 | 6 | 4 | 4 | 2 |
| **GPU 판정 예측기 합 (lo)** | | | **15** | **10** | **10** | **5** |

- 위 합은 STATISTICS.md 2.3의 "NPU 해소 26 / 일치 26 / 미해소 7, GPU(lo) 해소 10 / 일치 10 / 미해소 5"와 같다. 판정·보고 예측기 모두 해소 쌍에서 불일치 0이다.
- 해소 쌍은 모두 BASE가 들어간 쌍이거나(NPU·GPU) batch 16 구성 사이 쌍(NPU TASK82 N8 BATCHONLY/DP, N10 BATCHONLY/TUNED, TASK87 N14·16, TASK95 N13·17, TASK102 N15의 BATCHONLY/TUNED)이다. GPU의 POOL/POOL+GRID 쌍은 5개 N 모두 미해소다.
- **[사후]** GTASK11 sim LRU·FIFO의 예측 싼 쪽은 이번에 `PREDICTIONS.json`의 bound별 `device_per_turn_s`를 비교해 정했다(`main_judge.py`는 해석만 판정한다). 해소 6쌍은 모두 BASE 포함 쌍이고 세 예측기 모두 두 bound에서 BASE를 가장 비싸게 예측한다.
- 미해소 쌍에서는 예측기끼리 순서가 갈린다(판정 무관): TASK82 N6 BATCHONLY/TUNED(해석 BATCHONLY, sim 둘 TUNED), N8 BATCHONLY/TUNED(해석 TUNED, sim 둘 BATCHONLY). GTASK20 POOL/POOL+GRID: N25 lo ctx·x1.210 POOL+GRID, mode_dist·price POOL; N28 lo ctx·x1.210 POOL, mode_dist·price POOL+GRID; hi에서는 N25 ctx만 POOL, N28 mode_dist만 POOL+GRID.
