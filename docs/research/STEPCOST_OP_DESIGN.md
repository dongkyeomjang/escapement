# NPU 운영 조건 step 비용 재측정 — 설계 (측정 전 commit)

작성: 2026-10-01, [TASK92](TASK92.md) (Advisor 지시문 08 작업 B). **파라미터 측정이며 판정·예측이 없다.** 재현성만 보고한다. GPU G-06 작업 A와 같은 원칙: 결과 관측(재사용·비용 비)과 독립된 통제 부하.

## 1. 왜

[TASK91](TASK91.md): multi-turn 운영 조건의 decode step이 통제 측정 비용([TASK13](TASK13.md))보다 1.03–1.17배(step 가중 1.07–1.09) 길고 running 수에 비례해 커지며, 작은 배타 prefill은 1.2–1.35배다. 이 시간 척도가 시뮬레이터 비용 비 편향의 48.5 %를 설명했다. 그 비율은 개발 집합(TASK82·87)에서 얻었으므로 blind 예측에 쓸 수 없다. 운영과 **같은 serving 조건**에서 독립 통제 부하로 비용을 다시 잰다.

## 2. 조건

- runner·server: `run_multiturn.sh`(multi-turn과 같은 runner `multiturn_runner.py`, 같은 server 인자 `--enable-prefix-caching --enable-prompt-tokens-details`, `VLLM_LOGGING_LEVEL=DEBUG`, `VLLM_RBLN_METRICS=1`, patch 상태 기록), **streaming**, 평가 구간 40 s(`run_multiturn.sh`의 선택 인자 6, 생략 시 기존 120 s 그대로).
- artifact 전부: BASE `…-b8-s8192-d4-mb`, BATCHONLY `…-b16-…-batchonly`, TUNED `…-b16-…-mb16`, DP `…-b16-…-dp8`(기존, 새 compile 없음).
- plan(`make_stepcost_plans.py`, `plans/stepcost/`):
  - decode `op-decode-n{n}`: n slot, 세션마다 1 turn(prompt 128, 생성 512), 즉시 갱신 → running ≈ n 상시. BASE n = 1..8, batch 16 artifact n ∈ {1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16}.
  - prefill `op-prefill`: 4 slot, 1 turn(prompt U(64, 4096), 생성 32) → 알려진 크기의 배타 prefill이 몇 decode step마다.
  - seed 20261800 + n, 20261899; `cycle_s` 1 s.
- 순서(`run_stepcost_op.sh`): 44 decode + 4 prefill lifecycle을 seed 20261810으로 섞어 실행, 끝에 재현성 반복 2개(TUNED n4·n8, tag `.rep2`). 실패 lifecycle은 1회 재실행(`.retry1`).

## 3. 귀속과 적합

- [TASK91](TASK91.md)의 귀속 그대로(`step_audit.lifecycle`): R의 ALLOC–FREE 사이 `[BUCKET]` = R의 decode step, chunk 간격 = step 시간, ALLOC 없는 간격 = 깨끗한 decode step, ALLOC 하나 낀 간격 − 같은 (b, n) 깨끗한 step 중앙값 = 관측 배타 prefill.
- decode: artifact마다 `t(n) = F[b(n)] + β·n` 최소제곱(표본 ≥ 50인 n의 중앙값). prefill: artifact마다 `ceil(c/128)·(a + d·c)` 최소제곱. **비용 형태는 기존 descriptor와 같다** — 새 자유도를 넣지 않는다.
- 유효성: runner exit 0, `stopped_by = window`, 고갈 slot 0, HTTP 오류 0. 요청–step 대응(step 수 = 생성 − 1)이 안 맞는 요청은 건너뛰고 센다.
- 산출 `stepcost_op_analyze.py` → artifact별 `F`, `β`, `a`, `d`, 잔차, 통제 측정 대비 비, 재현성(반복 lifecycle 중앙값 차).

## 4. 쓰는 곳

작업 C(통합 시뮬레이터 blind cell)의 주 예측기 (1)이 이 비용으로 시뮬레이터의 **시간을 진행**한다(대기·batch 폭·축출 시점 등 동역학). 예측 비용(turn당 A′)의 **가격**은 관측 채널 A′의 정의와 같이 원래 비용 모형(TASK13 decode, TASK22 prefill)으로 매긴다 — 관측 m이 그 가격으로 계산되기 때문이다. **[TASK91](TASK91.md)의 관측 step 비율이나 TASK82·87에서 얻은 어떤 배율도 입력으로 쓰지 않는다.**

## 개정 1 (2026-10-02, 보충 측정 시작 00:08:16 직후 commit)

본 순서 실행(16:58:35–19:08:38)에서 **n = 1(4 artifact 전부)과 DP n = 2의 10-세션 plan이 평가 구간 끝 전에 소진**됐다(`exhausted_slots`, runner exit 3; BATCHONLY n = 2는 재실행에서 통과). 원인은 설계의 세션 수 계산 실수다 — 빠른 decoder 하나가 512 token 세션 10개를 약 55 s에 끝내 warm-up(약 11 s) + 평가 40 s를 채우지 못한다. 고침: 같은 부하에 세션만 30개로 늘린 `op-decode-n1-s30`·`op-decode-n2-s30`(seed 20261820 + n, `INDEX_SUPP.json`)으로 빠진 5개(BASE·BATCHONLY·TUNED·DP n = 1, DP n = 2)를 `run_stepcost_supp.sh`로 같은 run 디렉터리에 보충 측정한다. 분석은 유효 lifecycle만 쓰므로 소진된 lifecycle은 들어가지 않는다. 다른 설정은 바꾸지 않는다.

기록: 보충 구동이 이 개정의 commit보다 먼저 시작됐다(문서 끝 공백 줄로 `git diff --check`가 실패해 commit이 빠진 채 구동이 시작됨; run의 `git-head.txt`는 6f0195a). 보충 plan 파일은 구동 전에 생성되어 이후 바뀌지 않았고, 그 content/file sha256이 `INDEX_SUPP.json`에 있다. 이 보충은 판정 없는 파라미터 측정이라 선등록 대상 기준·예측은 없다.

## 개정 2 (2026-10-02, 보충 2 측정 전 commit)

보충 1 뒤 첫 적합에서 **`op-prefill`이 설계대로 작동하지 않았음**을 확인했다: 모든 요청이 정확히 32 token을 생성해 4 slot이 같은 박자로 돈다(4개 prefill이 연달아 실행된 뒤 31개 decode step을 함께 진행). 그래서 다른 요청의 prefill이 낀 decode 간격이 거의 없다 — 배타 prefill 표본이 BASE·BATCHONLY 각 60개(대부분 2,049–4,096 token), **TUNED·DP 0개**. 이 결과로는 운영 조건의 작은 prefill(TASK91: ≤ 512 token에서 1.2–1.35배)을 잴 수 없다.

고침: `op-prefill-mt`(seed 20261830, `INDEX_SUPP2.json`) — 4 slot, 세션당 4 turn, 첫 prompt U(64, 4096), 이후 segment 8 token, 생성 U(8, 64), gap 0, 세션 150개/slot, 최대 context 4,283. 생성 길이가 달라 같은 박자가 깨지고, multi-turn 실험과 같은 모양(새로 계산하는 큰 prefill + 긴 context 위 cache hit 뒤의 작은 prefill)이 된다. 4 artifact 각 1회, **평가 구간 120 s**(작은 크기 bin마다 표본 확보), `run_stepcost_supp2.sh`. prefill 적합은 `op-prefill-mt` 표본만 쓴다. `op-prefill` 표본 수는 기록만 한다. decode 적합은 바꾸지 않는다.

함께 고친 것: `step_audit.lifecycle`의 평가 구간이 120 s로 고정돼 있었다. 인자 `eval_s`(기본 120, TASK91 경로는 그대로)를 추가했고, 이 분석은 각 lifecycle의 `windows.*.json` `eval_s`를 넘긴다. 첫 적합은 40 s 구간 뒤 runner 종료까지(약 0.5 s)의 요청 몇 개를 포함했다. 개정 후 decode 적합을 다시 계산한다.

비용 형태 `ceil(c/128)·(a + d·c)`는 바꾸지 않는다. 이 형태는 cache된 context 길이 항이 없으므로 작은 cache-hit prefill과 큰 새 prefill의 차이는 적합 잔차로 보고한다.
