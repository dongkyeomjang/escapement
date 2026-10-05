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
