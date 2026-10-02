# 운영 조건 step 비용 재측정 — 설계 선등록 (GPU 지시문 G-06 작업 A)

작성: 2026-10-01. [GTASK17](GTASK17.md). **이 문서와 측정·분석 코드를 측정 전에 commit한다.** 파라미터 측정이며 판정은 없다(재현성만 보고).

## 1. 목적

[GTASK15](GTASK15.md)에서 운영 조건의 FULL decode step은 GTASK05 가격보다 약 22 % 길었고, 그 초과는 decode 폭에 비례했다(요청당 약 0.35 ms). 이 초과가 아래 세 요인 중 어디에서 오는지 가른다.
- streaming 출력
- KV events 발행
- admission log
관측 수단(KV events, admission log)이 원인이면 관찰자 효과로 기록한다. GTASK11 조건의 곡선은 GTASK18 blind 예측의 step 비용 입력이 된다.

## 2. 조건과 부하

- **요인** 2 × 2 × 2 = 8 조건. 이름은 `s{stream}k{kv}a{admlog}`이다.
  - `stream`: client가 `stream: true`(+ `include_usage`, `return_token_ids`; GTASK11 runner와 같은 형식) / non-streaming
  - `kv`: `--kv-events-config`(zmq ipc, collector 동작; GTASK11과 같음) / 없음
  - `admlog`: `[GPFX]` admission log on / off
    - off는 patch를 바꾸지 않는다. vLLM 표준 `VLLM_LOGGING_CONFIG_PATH`로 vLLM 기본 logging 설정에 `vllm.v1.core.sched.scheduler` logger 수준 WARNING만 더한다. 그 module의 다른 INFO log도 함께 꺼진다.
  - step log(`[GSTEP]`)는 모든 조건에서 켠다(`ESCAPEMENT_OBS=1`).
  - **GTASK11 조건 = `s1k1a1`**
- **server 인자**: GTASK11 BASE와 같다. `--num-gpu-blocks-override 1900`, `--max-num-seqs 8`, `--max-num-batched-tokens 2048`, `cudagraph_capture_sizes [1,2,4,8,16]`, async scheduling 기본, 나머지는 `lifecycle.base_args`.
- **부하**: GTASK05 FULL 단계를 따른다. 동시 decoder n개(prompt 64 random id, `ignore_eos`)를 한 batch씩 보낸다. GTASK05와 다른 점은 둘이다.
  - **n = 1, …, 8**: 지시문의 n ∈ {1, 2, 4, 8, 16} 중 16은 `max_num_seqs 8`에서 FULL 폭 16이 될 수 없어 뺐다. 대신 폭 비례를 보려고 3·5·6·7을 넣었다.
  - 생성 256 token(GTASK05 128)을 n마다 3 batch 보낸다. 정상 step 수를 늘리기 위해서다.
- **반복**: 조건마다 lifecycle 2개(r0, r1), 총 16 lifecycle. 순서는 `experiments/gpu/stepcost/op_order.json`(seed 20262700, replicate 안에서 섞음)을 따른다.
- 카드 `GPU-4485e769…` 고정. 다른 GPU process가 있으면 `INVALID`다.

## 3. 유효성과 재실행

lifecycle이 유효하려면 다음을 모두 만족해야 한다.
- `Lifecycle.valid()`(GPU process 규칙)
- 카드 uuid 일치
- preemption 증분 0
- 모든 요청의 생성 길이 = 256
- `[GSTEP]`가 있음
- admission log 상태가 조건과 일치(on이면 `[GPFX]` > 0, off이면 0)

`INVALID` lifecycle은 순서표가 끝난 뒤 한 번만 다시 잰다(`.retry1`). 그래도 `INVALID`면 그 cell은 빈칸으로 보고한다.

## 4. 분석 (`stepcost_op_analyze.py`, 측정 전 commit)

- **step 시간**: batch 구간 안에서 연속한 두 `[GSTEP]`가 모두 `maxq = 1, reqs = n, mode FULL`일 때 그 dispatch 간격을 step 시간으로 쓴다(균질 구간이라 lag 영향 없음). batch마다 처음·끝 3개는 버린다.
- **cell 값**: lifecycle 안 세 batch의 모든 간격의 중앙값. 조건 곡선은 두 lifecycle 값의 중앙값이고, 재현성은 두 값의 차이로 본다.
- **폭 기울기**: 조건별 n = 1–8 곡선의 최소제곱 기울기(ms/요청). GTASK05 `g` = 0.041, GTASK15 추정은 약 0.35다.
- **요인 효과**: log step 시간의 2³ 요인 분석으로 주효과 3개, 2요인 상호작용 3개, 3요인 상호작용 1개를 비로 보고한다. n별 값과 n 평균을 함께 낸다.
- **GTASK11 조건 재현**: `s1k1a1` 곡선 / GTASK05 가격(`gpu_cost.decode_ms`, 격자 [1,2,4,8,16])을 n별로 내고, GTASK15의 운영 비율(n = 1–8: 1.034 … 1.219)과 나란히 놓는다.
- **관찰자 효과의 보고 규칙**: `kv` 또는 `admlog` 주효과가 반복 간 차이보다 크고 비 ≥ 1.02이면 "관찰자 효과 있음"으로 기록한다. 판정이 아니라 보고 분류다.

## 5. 예상 (기록용, 판정 아님)

- `s1k1a1` / 가격은 n = 8에서 약 1.2가 되고 n에 따라 커질 것이다.
- 가장 큰 요인은 streaming(요청별 출력 처리)일 것이다. 두 번째는 KV events(block이 찰 때마다 발행)일 것이다. admission log는 decode-only 부하에서 admission이 batch 시작에만 있으므로 효과가 거의 없을 것이다.
- **한계**: 이 부하는 admission 빈도가 GTASK11보다 훨씬 낮다. 그래서 admission log 효과의 상한을 재지 못한다.

## 6. 자동 commit

- 사용자 지시(2026-10-01)에 따라 driver `run_stepcost_op.sh`는 분석 뒤 기계 생성 요약 세 파일만 local `gpu-a6000`에 commit한다. 파일은 `experiments/gpu/stepcost/op_result/{summary.json, summary.md, sequence.log}`이다.
- push는 하지 않는다. 해석은 GTASK17 문서에서 따로 한다.
