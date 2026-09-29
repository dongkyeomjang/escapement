# GPU step 비용 측정 설계 선등록 (FULL · PIECEWISE · eager)

## 문서 성격

GPU 지시문 G-02 작업 D의 **측정 설계 선등록**이다. 파라미터 측정이라 예측·판정은 없고, **측정 재현성(반복 간 변동)만 보고**한다. 요청 구성, 반복 수, step 시간의 정의와 귀속 규칙, 요약 방식, 보고 형식을 이 문서와 script([`stepcost_run.py`](../../../experiments/gpu/stepcost/stepcost_run.py), [`stepcost_analyze.py`](../../../experiments/gpu/stepcost/stepcost_analyze.py), [`run_stepcost.sh`](../../../experiments/gpu/stepcost/run_stepcost.sh))로 측정 전에 commit한다. 결과는 [GTASK05](GTASK05.md)에 쓴다.

대상은 GPU descriptor의 `step_cost_model`에 해당하는 세 곡선이다([GTASK02](GTASK02.md) FIT_GAPS 8).

## step 시간의 정의

- **관측**: observation patch([GTASK03](GTASK03.md), 관문 통과)의 `[GSTEP]` 줄. 같은 EngineCore process의 `time.perf_counter()` dispatch 시각 `t_k`. `Δ_k = t_{k+1} − t_k`.
- **async scheduling(배포 기본값 on)에서의 귀속**: engine은 batch 2개를 동시에 띄운다(`v1/engine/core.py:469–533`). step k+2는 step k의 출력이 온 뒤에야 dispatch되므로, GPU가 쉬지 않는 정상 상태에서 **`Δ_{k+1}`이 GPU step k를 덮는다**(가설 H-lag). 같은 폭의 decode가 이어지는 구간에서는 lag가 결과에 영향을 주지 않는다.
- **lag 규칙(사전 고정)**: 고립 step(혼합·eager)의 비용 = `Δ_{k+L}`. `L`은 EAGER `d=4, p=2048`(가장 큰 고립 step)에서 `{0,1,2}` 중 `median(Δ_{k+L}) − decode 기준선`이 가장 큰 값으로 **규칙에 따라** 정하고, 모든 고립 step·모든 lifecycle에 같은 `L`을 쓴다. H-lag가 맞으면 `L = 1`이다(예측). 이 규칙은 합성 로그로 검증했다(측정 아님).
- **측정하지 않는 것**: GPU kernel 시간 자체(CUDA event 없음), decode 폭 0에서의 prefill 단독 step(engine이 idle로 돌아가 dispatch 간격에 idle 시간이 섞인다) — 대신 **decode 폭 d ≥ 1 대비 증분**으로 보고한다.

## 격자와 lifecycle

| 요소 | 값 |
|---|---|
| server 공통 | `CUDA_VISIBLE_DEVICES=0`, `--revision 1cfa9a72… --dtype bfloat16 --max-model-len 8192 --seed 20260929 --generation-config vllm --enable-prompt-tokens-details --block-size 16 --num-gpu-blocks-override 4096 --max-num-seqs 16 --max-num-batched-tokens 2048`, `ESCAPEMENT_OBS=1`(patch 적용), KV events 끔, async scheduling 기본(on) |
| capture 격자 | **G1** `[1,2,4,8,16]`(`max_num_seqs=8` 기본값), **G2** `[1,2,4,6,8]`(GTASK02 L2), **G3** `[1..16]` 연속 |
| lifecycle | 격자 3 × 반복 2 = **6개**, 순서 G1 r0, G2 r0, G3 r0, G1 r1, G2 r1, G3 r1 |
| preemption 구조적 불가 | 가용 4,095 block ≥ `16 × ceil(3,064/16) = 3,072`(최장 요청: 배경 decoder 64 + 3,000 token) |
| 시간 추정 | lifecycle당 기동 ≈ 40 s + FULL ≈ 35 s + MIXED ≈ 30 s + EAGER ≈ 35 s → **약 15분** |

## 요청 구성 (lifecycle마다 같음, 내용 seed만 격자·반복별)

| 단계 | 구성 | 만들어지는 step |
|---|---|---|
| **FULL** | n = 1..16 차례로: n개 동시 요청(prompt 64 token, 서로 다름, `max_tokens 128`, `ignore_eos`) | 폭 n의 decode-only step ≈ 127개 연속. 격자에 따라 FULL(padding) 또는 eager(G2에서 n > 8) |
| **MIXED** | 배경 decoder d ∈ {1,2,4,8}(stream, prompt 64, `max_tokens 3000`, 단계 끝에 연결을 닫아 abort) 위에 probe(prompt p ∈ {2,4,8}, `max_tokens 1`)를 **하나씩** 20회(간격 50 ms) | 폭 d decode + p-token prefill의 고립 혼합 step(toks = d + p). toks ≤ 최대 capture면 PIECEWISE, 넘으면 eager |
| **EAGER** | 같은 방식, d ∈ {1,4}, p ∈ {32, 64, 128, 256, 512, 1024, 2048}, 10회 | toks > 최대 capture인 eager 혼합 step |

## 요약 방식 (NPU [TASK13](../TASK13.md)·[TASK55](../TASK55.md) 방식)

- **FULL**: (격자, n)마다, 각 homogeneous 구간의 앞뒤 3 step을 버린 `Δ`의 **중앙값·IQR·개수**, 그리고 **lifecycle별 중앙값의 범위**(재기동 간 변동). 형태 분해: G1·G3의 FULL cell로 `t(n) = F[bucket(n)] + g·n`을 최소자승 적합(bucket마다 고정 성분, 요청 수 의존 성분 g 공유)하고 최대 잔차를 보고한다. NPU `f(bucket) + g(actual)`에 대응한다.
- **MIXED/EAGER**: (격자, d, p)마다 lag `L`의 고립 step 시간 중앙값·IQR, **같은 구간의 폭 d decode 기준선** 중앙값, **증분 = 고립 step − 기준선**, lifecycle별 중앙값 범위. 증분을 p에 대해 그리면 NPU 식 (5)의 prefill 비용 모형(`prefill_s(n)`)에 대응하는 **혼합 prefill 증분 곡선**이 된다.
- 보고 형식: `summary.md`의 표 두 개(FULL: n × 격자, 고립 step: 격자 × phase × d × p)와 적합 계수. 기동 실패·무효 lifecycle은 표에서 빼고 그 사실을 적는다.

## 사전 기대 (판정 아님)

- FULL: 격자 G1에서 n = 3, 5–7, 9–15는 위 bucket 비용을 치르므로 G3의 같은 n보다 느리다. G2에서 n > 8은 eager라 G1·G3보다 느리다.
- 혼합 증분은 p에 대해 대략 선형이고, p ≤ 8의 PIECEWISE 증분은 1 ms 미만일 것이다(근거 약함).
- lag 규칙은 `L = 1`을 고를 것이다.

## 유효성

lifecycle마다 GPU 0 외 process 부재, `vllm:num_preemptions` 증분 0을 기록한다. 어긋나면 그 lifecycle은 `INVALID`로 표에서 뺀다.
