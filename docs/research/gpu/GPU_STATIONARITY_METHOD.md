# GPU 정상성 분석 — 방법 (G-05 작업 E, 계산 전 고정)

작성: 2026-10-01. [GTASK16](GTASK16.md). **분석만, 판정 없음(보고).**

- 이 문서는 계산 전에 commit한다. 결과는 GTASK16에 적는다.
- NPU 방법 [STATIONARITY_REANALYSIS.md](../STATIONARITY_REANALYSIS.md) §2–§4(`c7b444b`, [TASK83](../TASK83.md))를 merge(`309871a`)로 받아 그대로 따른다. 아래는 GPU 데이터에 맞춘 차이만 적는다.
- commit 전에 GPU 데이터의 전·후반 값은 계산하지 않았다.

## 1. 데이터

- [GTASK11](GTASK11.md) run `results/gpu/multiturn/main/20260930T1411Z/`, **11 cell**(N 20·22·24 × BASE·POOL·POOL+GRID, N 26 × BASE·POOL), cell마다 r0–r4 5 lifecycle(전부 유효)

## 2. 창

- 평가 구간 `[w0, w0 + 120)`를 전반 `[w0, w0 + 60)`과 후반 `[w0 + 60, w0 + 120)`으로 나눈다.
- 요청은 보낸 시각(`sent_s`)으로 창에 속한다.
- step은 server 창(평가 구간 첫 요청의 ALLOC ~ 마지막 요청의 ALLOC, GTASK11 가격 채널과 같은 범위)의 `[GSTEP]`이다. **후반 첫 요청의 ALLOC 줄 위치**에서 둘로 나눈다(NPU 정의와 같다).
- **h(n)**: GTASK11 판정 정의인 **decode-only h**를 주 지표로 쓴다. 이것은 step마다의 decoder 수 분포이며, decoder 수는 `reqs` 또는 `reqs − k`(k = 직전 step 이후 ALLOC 수, 최소 1)이고 decoder 0인 step은 뺀다. `reqs` 정의의 h는 병기한다.
- **재사용률**: 창에 속한 turn ≥ 1 요청 중 client `cached_tokens > 0`인 비율(`null`은 flag 확인 후 0).

## 3. 통계

NPU §3과 같다.
- `W_r = TVD(h_전(r), h_후(r))`
- `B` = 같은 위치 창의 replicate 쌍 TVD, 5 replicate에서 20개
- `q_h = mean_r F_B(W_r)`(중간 순위 백분위)
- `Δ_r = reuse_후 − reuse_전`
- `D` = 같은 위치 순서쌍 차, 부호 대칭
- `q_Δ = mean_r F_D(Δ_r)`, `q_|Δ| = mean_r F_{|D|}(|Δ_r|)`

## 4. 보고 분류

NPU §4의 분류 규칙을 cell 수만 바꿔 쓴다.
- **h 비정상**: 11 cell `q_h` 중앙값 > 0.75 **그리고** 단측 부호 검정 `P(K ≥ k | Bin(11, 0.5)) < 0.05`(k = `q_h > 0.5`인 cell 수; k ≥ 9에서 성립)
  - 둘 중 하나만 성립하면 `WEAK_EVIDENCE`, 둘 다 불성립이면 `NOT_NONSTATIONARY`
- **재사용 후반 하락**: `q_Δ` 중앙값 < 0.25 **그리고** `q_Δ < 0.5`인 cell 수에 같은 부호 검정. `WEAK_EVIDENCE`도 같은 방식이다.
- 보조로 확증 9 cell만의 분류도 적는다(`Bin(9, 0.5)`, k ≥ 8).
- 결과를 본 뒤 이 조건을 바꾸지 않는다. NPU 결과(h `WEAK_EVIDENCE`, 재사용 `NOT_NONSTATIONARY`)와 나란히 보고한다.
