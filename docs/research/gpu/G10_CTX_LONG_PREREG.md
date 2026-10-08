# G-10 작업 C 사전 단계 — 긴 문맥 decode step 비용 microbenchmark 선등록

작성: 2026-10-08. GPU 지시문 G-10(2026-10-08) §5.3. 기록 TASK는 [GTASK25](GTASK25.md)(작업 C)다. **이 문서와 script를 측정 전에 commit한다.**

## 1. 왜 필요한가

- 작업 C의 LONG_TOOL 조건(호출 사이 도구 결과 512 token, 8 turn)은 workload 법칙상 요청 하나의 문맥이 최대 1,600 + 7 × 512 + 8 × 256 = **7,232 token**까지 간다.
- 현행 문맥 인지 시뮬레이터(GTASK20 예측기 (1) `ctx`)의 context 항 `c = 2.120 × 10⁻⁴ ms/token`은 GTASK18에서 **L ≤ 3,000(+64)** 의 통제 부하로만 맞췄다(`experiments/gpu/stepcost/ctx_result/summary.json`). LONG_TOOL 문맥은 이 범위 밖이다.
- 지시문 §5.3에 따라 타깃 측정과 독립인 작은 microbenchmark로 **필요한 문맥 길이의 decode step 시간만** 먼저 잰다. 함수 형태(F1: `t = a(n) + c·ΣL`, 예측기 형태 `price + c·(Σ decode context − decodes·128)`)는 바꾸지 않고 계수 `c`만 갱신한다.

## 2. 측정

- protocol: GTASK18과 같다(`stepcost_ctx_run.py`를 복제한 `experiments/gpu/g10/ctx_long_run.py`). 조건 s1k1a1(streaming, KV events, admission log), 격자 (1,2,4,8,16), `max_num_seqs` 8, budget 2,048, GEN 128, 3 round, lifecycle 2개.
- 다른 점: cell = n ∈ {1,2,4,8} × L ∈ {64, 1500, 3000, 4500, 6000, 7000}(24개, `ctx_long_order.json`, 순서 seed 20264800). KV pool 4,400 block(8 × 7,128 token이 들어가야 한다. pool 크기는 decode step 계산에 들어가지 않는다). prompt id seed `20264800 + 100000·rep + 1000·k + 20·ci + j`(모든 plan seed·검증 seed와 분리).
- 카드 `GPU-4485e769…`, 관측 patch 상태 `patched`(GTASK03), 다른 GPU process 없음.
- INVALID: lifecycle 검사 실패(외부 GPU process, 생성 길이 불일치, preemption, step log 없음)면 순서를 다 돈 뒤 한 번 다시 잰다.
- driver: `experiments/gpu/g10/run_ctx_long.sh <abs run dir>`. 실행 중 script를 고치지 않는다.

## 3. 분석과 산출 (판정 없음, calibration)

- cell 값: GTASK18 `cell_times` 그대로(같은 폭 n의 연속 FULL decode-only step의 dispatch 간격, 양 끝 3개 제외, lifecycle 중앙의 중앙).
- **F1을 24 cell 전부로 맞춘 `c_long`이 작업 C 예측기에 넘기는 유일한 숫자다.** 예측기 형태는 GTASK20 `ctx`와 같고 `c`만 `c_long`으로 바꾼다(이름 `ctx_long`).
- 보고만: n별 기울기, L별 잔차, GTASK18 `c`로 계산한 값과 실측 차이.
- B(포화 구간 비용 비 검증)의 동결 예측에는 소급 적용하지 않는다. 작업 C의 예측은 "새 timing 입력을 쓴 예측"이며 기존 모형 그대로의 외삽 검증이 아니다.
- 산출: `experiments/gpu/g10/ctx_long_result/summary.json`(측정 후 commit).

## 4. 범위 밖

- 혼합(prefill+decode) step과 prefill chunk의 문맥 의존은 재지 않는다(기존 함수 형태 유지, G-08 결정 1). 작업 C에서 이로 인한 오차가 나오면 결과로 보고한다.
