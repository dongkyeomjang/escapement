# context 길이 step 비용 측정 — 설계 선등록 (GPU 지시문 G-07 작업 B)

작성: 2026-10-02. [GTASK18](GTASK18.md). **이 문서와 측정·분석 코드를 측정 전에 commit한다.** 파라미터 측정이며 판정은 없다(재현성과 형태만 보고).

## 1. 목적과 가설

- [GTASK17](GTASK17.md): 관측 수단은 운영 초과(GTASK15, n = 8에서 1.219)를 만들지 않았다. 통제 부하의 step은 가격과 같았다.
- NPU [TASK92](../TASK92.md): 짧은 context에서는 decode가 통제 비용과 같았고(0.99–1.01), multi-turn처럼 긴 context에서는 1.03–1.15배로 running 수에 따라 커졌다.
- 가설(G-07 §2): GTASK15의 "decode 폭에 비례하는 초과"는 요청 수가 아니라 running 요청들의 **context 길이 합**에서 온다. decode attention 비용이 Σ context에 비례하기 때문이다.

## 2. 통제 부하의 context 길이 (작업 B-1, 기록에서 확인)

| 측정 | prompt | 생성 | decode 중 요청당 context | 출처 |
|---|---|---|---|---|
| GTASK05 FULL(가격) | 64 random id | 128 | 64–192(평균 128) | `stepcost_run.py` `FULL_PROMPT, FULL_GEN = 64, 128` |
| GTASK17 | 64 random id | 256 | 64–320(평균 192) | `stepcost_op_run.py` `PROMPT, GEN = 64, 256` |
| GTASK11 plan(운영) | 첫 segment U(800, 1600), 이후 8 | U(32, 256), 최대 8 turn | decode step 가중 평균 1,810, p05 1,102, p25 1,485, 중앙 1,796, p75 2,128, p95 2,551, 최대 3,273 | `plans/main/gmain-n{20,22,24}-r*.json` 전체 session(평가 구간 제한 없음) |

GTASK05·17의 통제 부하는 운영 context의 약 1/10–1/15 길이였다.

## 3. 조건과 부하

- **server**: GTASK11 조건 `s1k1a1`(streaming client, KV events, admission log, step log)과 GTASK11 BASE 인자. `--num-gpu-blocks-override 1900`, `--max-num-seqs 8`, `--max-num-batched-tokens 2048`, capture `[1,2,4,8,16]`.
- **cell 18개** (`experiments/gpu/stepcost/ctx_order.json`):
  - 균일 cell 16개: n ∈ {1, 2, 4, 8} × L ∈ {64, 512, 1,500, 3,000}. L은 요청당 prompt 길이(random id)다.
    - L 범위는 plan 분포(p05 1,102 – 최대 3,273)를 덮는다.
    - **조정 1(지시문 허용 범위)**: L = 64를 더했다. GTASK17과 같은 짧은 context를 같은 lifecycle에서 재서 a(n)을 잡기 위해서다.
  - 혼합 cell 2개: n ∈ {4, 8}, 절반은 512이고 절반은 3,000이다(**조정 2**). 균일 cell만으로는 비용이 Σ L에 비례하는지 n · max L에 비례하는지 가를 수 없다. 혼합 cell은 Σ L이 같은 균일 cell(L ≈ 1,756)과 비교된다.
- **생성**: 요청마다 128 token, `ignore_eos`. 같은 cell의 n개 요청을 동시에 보내고 모두 끝나면 다음으로 간다. decode 중 context는 L … L + 128이다.
- **순서와 반복**: lifecycle 2개(r0, r1, GTASK05·17 방식). lifecycle마다 3 round, round마다 18 cell을 한 번씩 섞은 순서로 돈다(seed 20262800).
- **pool 확인**: 가장 큰 cell(n = 8, L = 3,000)은 8 × 3,128 token = 1,564 block이다. 사용 가능 1,899 block 안에 든다. preemption이 없어야 한다.
- prompt는 요청마다 다른 seed의 random id다. prefix cache hit는 기대하지 않는다.
- 카드 `GPU-4485e769…` 고정.

## 4. 유효성, 분석, 보고

**유효성**(lifecycle 단위, 모두 만족해야 함):
- `Lifecycle.valid()`
- 카드 uuid 일치
- preemption 증분 0
- 모든 요청의 생성 = 128
- `[GSTEP]`와 `[GPFX]`가 모두 있음

`INVALID` lifecycle은 순서가 끝난 뒤 한 번 다시 잰다(`.retry1`). 그래도 `INVALID`면 빈칸으로 둔다.

**step 시간**: GTASK17과 같다. cell 구간 안에서 연속한 두 `[GSTEP]`가 모두 `maxq = 1, reqs = n, mode FULL`일 때 그 dispatch 간격을 쓴다. batch마다 앞뒤 3개는 버린다. lifecycle 값은 세 batch 전체 간격의 중앙값이다. cell 값은 두 lifecycle 값의 중앙값이고, 재현성은 두 값의 차이로 본다.

**Σ L**: cell 요청들의 (prompt + 64) 합이다. 64는 decode 중 평균 생성 위치다.

**형태 보고**(판정 없음, `stepcost_ctx_analyze.py`):
- F1 `t(n, L) = a(n) + c · Σ L`: 균일 16 cell에 최소제곱 적합(a 4개, c 1개)한다. 잔차, 그리고 혼합 cell 잔차(Σ L 대 max L 구분)를 보고한다.
- n별 따로 적합 `t = a_n + c_n · Σ L`: c_n의 퍼짐과 잔차를 보고한다. F1이 맞지 않으면 이것과 표 자체를 관측 형태로 보고한다.

**GTASK15 운영 비율 재현**(판정 없음):
- 입력은 §2의 plan 분포 평균 L̄ = 1,810뿐이다. **GTASK11·13의 관측값은 적합 입력으로 쓰지 않는다.**
- d ∈ {1, 2, 4, 8}: (a) F1 값 (a(d) + c · d · L̄) / 가격(d), (b) 모형 없이 측정 균일 cell을 L 축에서 선형 보간한 값(L̄ 위치) / 가격(d).
- d ∈ {3, 5, 6, 7}: F1, a(d) = GTASK17 `s1k1a1` 곡선(d) − c · d · 192.
- GTASK15 비율(1.034 … 1.219)과 나란히 놓고 차이를 보고한다.
- **한계**: 운영 중 동시에 달리는 요청들의 context는 plan 전체 step 가중 분포의 독립 표본이 아니다(평가 구간, 세션 위치, 붕괴 cell의 miss). 선형 형태에서는 평균만 들어가므로 영향은 평균 차이로 한정된다.

## 5. 예상 (기록용, 판정 아님)

- GTASK15의 초과를 Σ L로 나누면 c ≈ 0.2–0.25 µs/token이다(d = 1: 0.46 ms / 1,810; d = 8: 약 3.0 ms / 14,500). 가설이 맞다면 다음과 같을 것이다.
  - c는 그 범위에 있다.
  - n = 8, L = 3,000 cell은 가격의 약 1.35–1.4배다.
  - F1 재현값은 GTASK15 비율과 ±0.03 안이다.
- 혼합 cell은 Σ L 형태 쪽(잔차 작음)일 것이다.
- L = 64 cell은 GTASK17 곡선과 0.5 % 안일 것이다.

## 6. 자동 commit과 산출

- driver `run_stepcost_ctx.sh`는 분석 뒤 `experiments/gpu/stepcost/ctx_result/{summary.json, summary.md}`만 local `gpu-a6000`에 commit한다. git 종료 코드와 HEAD 이동을 직접 확인한다(GTASK17 수정). push는 하지 않는다.
- run dir(비추적): `results/gpu/stepcost_ctx/<시작 UTC>/`
- 결과 commit 뒤 작업 C(붕괴 영역 blind)를 선등록한다.
