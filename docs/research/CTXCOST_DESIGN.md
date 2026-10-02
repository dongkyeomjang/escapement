# NPU context 길이 step 비용 측정 — 설계 (측정 전 commit)

작성: 2026-10-02, [TASK97](TASK97.md) (Advisor 지시문 10 작업 A). **파라미터 측정이며 판정·예측이 없다.** 재현성만 보고한다. GPU G-07과 같은 형태의 측정이다.

## 1. 왜

[TASK92](TASK92.md): 같은 serving 경로에서 짧은 context(128 + 512) decode는 통제 비용([TASK13](TASK13.md))과 같고, multi-turn형 긴 context(최대 4,283)에서는 1.03–1.15배였다(탐색). [TASK91](TASK91.md)의 운영 초과(step 가중 1.07–1.09)가 **통제 측정이 짧은 context로 쟀기 때문**인지 확인하려면 context 길이를 통제 변수로 재야 한다([결정 11](INDEX.md#결정-11--지시문-09-결정-task9195-결정-요청)-2, 후속 연구 11).

## 2. 조건

- runner·server·streaming 경로: [TASK92](TASK92.md)와 같다(`run_multiturn.sh … stream 40`, 평가 구간 40 s).
- artifact: BASE `…-b8-s8192-d4-mb` (1,2,4,8), TUNED `…-b16-s8192-d4-mb16` (1,4,6,8,10,16). 새 compile 없음.
- plan `ctx-n{n}-L{L}`(`make_ctxcost_plans.py`, `plans/ctxcost/`): n slot, 세션마다 1 turn, prompt 정확히 L token, 생성 정확히 256 token, 즉시 갱신, 세션 40개/slot, seed 20262000 + 10n + i_L.
  - n ∈ {1, 2, 4, 8}(BASE·TUNED), 16(TUNED만). L ∈ {512, 1,500, 3,000}.
  - decode step k(1..255)에서 요청 context = L + k. 세 L이 512–768, 1,500–1,756, 3,000–3,256을 덮는다. multi-turn plan(N = 12–17)의 요청 context(decode 중간) 십분위 1,206–2,379, 최대 약 3,060이므로 그 분포를 덮는다. [TASK92](TASK92.md) `op-decode`(L = 128, 128–640)는 같은 경로의 짧은 context 점으로 함께 적합에 쓴다(새로 재지 않음).
- 순서(`run_ctxcost.sh`): 27 lifecycle(BASE 12 + TUNED 15)을 seed 20262099로 섞고, 재현 반복 2개(TUNED n4 L1500, TUNED n8 L3000, `.rep2`). 실패는 1회 재실행(`.retry1`). 약 1.5 h.

### TASK92 설계 결함의 사전 회피

1. **plan 소진**: 가장 짧은 세션(n = 1, L = 512)이 약 2.7 s이므로 40 세션 = 108 s. `make_ctxcost_plans.check_exhaustion`이 모든 plan에서 "세션 수 × 가장 빠른 세션 길이 ≥ 1.5 × (warm-up 두 세션 + 40 s)"를 TASK13·22 비용(decode step 9.5 ms 하한, prefill 0.9배)으로 검사한다 — 여유 1.48–4.57.
2. **같은 박자**: 이번 부하는 **같은 박자를 의도**한다. TASK92의 결함은 배타 prefill 표본(다른 요청의 decode 간격에 낀 prefill)이 생기지 않는다는 것이었고, 이 측정은 prefill을 재지 않는다. 같은 박자에서는 갱신 prefill n개가 연달아 실행된 뒤 n개 요청이 255 step을 함께 decode하므로 running이 정확히 n이고 context가 모든 요청에서 L + k로 같다. 박자가 어긋나도(첫 시작 간격 0.01/n s) 분석은 step마다 실제 running·context로 귀속하므로 결과에 영향이 없다.

## 3. 귀속과 요약

- [TASK91](TASK91.md) 귀속 그대로: 요청 R의 ALLOC–FREE 사이 `[BUCKET]` = R의 decode step, R의 streaming chunk 간격 = step 시간, ALLOC 없는 간격 = 깨끗한 step. step의 **ΣL = 그 step의 모든 running 요청의 (prompt + 이미 생성한 token 수)의 합**(각 요청의 ALLOC–FREE 범위와 그 안의 위치로 계산).
- 요약: artifact × n × L별 깨끗한 step 시간 중앙값, k를 64 step 구간(4개)으로 나눈 중앙값(context 증가에 따른 기울기), lifecycle 반복의 중앙값 차(재현성).
- 형태 적합(artifact별, 64-step 구간 중앙값에 최소제곱):
  - **F1** `t = f(b) + β·n + c·ΣL` (지시문 형태; α는 f(b)에 흡수)
  - **F2** `t = f(b) + β·n + c_b·ΣL` (c가 bucket별)
  - **F3** `t = f(b) + β·n + c·b·L̄` (padding slot까지 context 비용, L̄ = 평균 context)
  - 잔차(RMS, 최대)로 비교하고, F1이 맞지 않으면 관측된 형태를 보고한다. 비용 형태를 기존 판정에 소급 적용하지 않는다.
- **운영 비율 재현 검사**: 적합된 비용을 TASK82·87·95 run의 실제 decode step 구조(running n, bucket b, ΣL — server 로그와 plan에서 계산, **step 시간은 쓰지 않음**)에 적용해 step 가중 "context 비용 / 통제 비용" 비를 artifact별로 계산하고 [TASK91](TASK91.md)의 관측 비(1.07–1.09)와 비교한다. 같은 계산을 [TASK92](TASK92.md) `op-prefill-mt`의 깨끗한 step에 적용해 1.03–1.15와 비교한다. **TASK91의 관측 step 시간은 적합 입력이 아니다.**
- 분석 코드(`ctxcost_analyze.py`)는 측정 뒤 작성한다 — 위 형태·요약·재현 검사의 정의는 이 문서로 고정한다.

## 4. 쓰는 곳

작업 B(사후 재예측, `post_hoc`): 이 비용으로 시뮬레이터의 시간을 진행해 TASK87·95 cell을 다시 예측한다. 관측을 이미 본 cell이므로 판정하지 않는다.

## 개정 1 — BATCHONLY 추가 (2026-10-02, 지시문 11 작업 A, [TASK100](TASK100.md), 측정 전 commit)

[TASK98](TASK98.md)은 BATCHONLY 비용을 측정하지 않고 규칙(f(b): b ∈ {1, 4, 8, 16} TUNED, b = 2 BASE; β·c = BASE·TUNED 평균)으로 정했다. blind 검증 입력에 규칙 추정이 섞이지 않도록 BATCHONLY(`…-b16-s8192-d4-batchonly`, grid 1,2,4,8,16)를 같은 설계로 잰다.

- plan: TASK97의 `ctx-n{n}-L{L}` 그대로(n ∈ {1, 2, 4, 8, 16} × L ∈ {512, 1,500, 3,000}, 15 lifecycle). 소진 검사·같은 박자 방침도 같다.
- 순서(`run_ctxcost_bo.sh`): seed 20262199로 섞고 재현 반복 1개(n8 L3000, `.rep2`). 실패는 1회 재실행. 약 40분.
- 분석: `ctxcost_analyze.py`에 BATCHONLY를 추가해 같은 F1–F3 적합(TASK92 BATCHONLY `op-decode` 짧은 context 점 포함)과 운영 비율 재현 검사. 보고: F1 f(b)·β·c와 TASK98 규칙값의 차이, 그 차이가 TASK98 재예측의 BATCHONLY 시간 진행에 주는 step 시간 차(대표 n·ΣL에서 ms). 판정 없음.
- **측정 중에는 다른 작업(저장소 scan, export, 분석, 시뮬레이션)을 돌리지 않는다**(지시문 11 §1).
