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

## 개정 1 — 장비 교체 후 재측정 (2026-09-29, 재측정 시작 전 commit)

**원 선등록**: `fc2d0ab` (2026-09-29 09:41:05 UTC). 이 개정은 판정 기준을 바꾸지 않는다(이 선등록에는 판정이 없다). 격자·요청 구성·lag 규칙·요약 방식·유효성 규칙은 **그대로**이며, 측정 장비와 run 범위만 바꾼다.

**사건 (관찰)**:

- 첫 run `results/gpu/stepcost/20260929T1021Z`(측정 시작 10:21:31 UTC)에서 G1 r0·G2 r0은 `rc=0`으로 끝났다. G3 r0은 server 로그가 10:28:57 UTC의 `[GSTEP]` 줄 뒤에서 NUL byte로 끊겼고, 그 boot에는 shutdown 기록이 없다 — **측정 중 host 다운**.
- 사용자가 문제가 있던 PCIe 슬롯을 비활성화했다. 빠진 카드는 uuid `GPU-00596b63-c6a5-db28-01a2-81c3a1d42a24`, serial `1320523024057`(GTASK01 inventory의 `17:00.0`)이다. **GTASK02–05의 모든 측정이 이 카드에서 이뤄졌다**(`lifecycle.json`의 `gpu0_uuid`).
- 슬롯이 빠지면서 bus 번호가 당겨져 `CUDA_VISIBLE_DEVICES=0` / `nvidia-smi` index 0이 **다른 카드**(예전 `18:00.0`)를 가리킨다.

**run `20260929T1021Z` 처리**:

- G3 r0: `INVALID`(host 다운).
- G1 r0·G2 r0: **결과에서 제외**한다. 이유 — (1) 곧 다운된 슬롯의 카드에서 나온 timing이다. (2) 나머지 lifecycle은 다른 카드에서 돌게 되므로 섞으면 카드 차이와 재기동 간 변동을 구분할 수 없다. raw는 삭제하지 않고 보존한다. 이 개정 작성 시점까지 첫 run의 `summary.json`·`events.json`은 열지 않았다(진단용으로 `sequence.log`와 server 로그 끝부분만 봤다).

**재측정 장비** (2026-09-29 15:58 UTC boot 이후 관찰):

| 항목 | 값 |
|---|---|
| `CUDA_VISIBLE_DEVICES=0` 대상 | uuid `GPU-4485e769-430a-430d-3383-b9c4ce92a175`, serial `1324321025786`, bus `00000000:17:00.0`(예전 `18:00.0`), PCIe link x8(예전 inventory의 같은 카드도 x8) |
| host의 GPU 수 | 2 (`17:00.0`, `65:00.0`) |
| 사전 점검 | 두 카드 모두 40 GB 메모리 쓰기·검증 통과, bf16 8192² matmul warmup 후 약 114 TFLOPS(GPU 0)·111 TFLOPS(GPU 1), throttle reason 없음, 현재 boot의 kernel log에 Xid·NVRM error 없음 |
| driver·venv·model·patch | 변경 없음(driver 580.178.04, `vllm 0.22.0`, revision `1cfa9a72…`, patch `state: patched`) |

**추가 유효성 규칙**: lifecycle마다 `lifecycle.json`의 `gpu0_uuid`가 `GPU-4485e769-430a-430d-3383-b9c4ce92a175`이고, ready 시점 `gpu_apps`에서 이 run의 process가 그 uuid에 있어야 한다. 어긋나면 그 lifecycle은 `INVALID`.

**재측정 범위**: 새 run 디렉터리(`results/gpu/stepcost/<새 UTC 시각>`)에서 **6 lifecycle 전체**(G1 r0, G2 r0, G3 r0, G1 r1, G2 r1, G3 r1)를 원 순서대로 `run_stepcost.sh`로 다시 돈다. script는 수정하지 않는다.

**해석 범위**: 결과는 **uuid `4485e769…` 카드 한 장**의 step 비용이다. 같은 모델명의 다른 카드(GTASK02–04에 쓴 카드)와 같은 값이라는 보장은 없다. 카드 간 차이는 이 run으로 판정하지 않는다.

**host 다운이 재발하면**: 그 lifecycle을 `INVALID`로 두고 run을 멈춘 뒤 사용자에게 보고한다. 자동으로 다시 시도하지 않는다.

## 개정 2 — p = 2048 probe의 chunk 분할 (2026-09-29, 측정 후·수치 확인 전 commit)

**원 규칙의 실패 (기록)**: run `20260929T1607Z`의 6 lifecycle은 모두 유효했다(`valid`, preemption 0, 전부 uuid `4485e769…`). 그런데 사전 등록한 `stepcost_analyze.py`는 `ValueError: max() iterable argument is empty`로 멈췄다. **lag 규칙을 정하는 cell(EAGER d=4, p=2048)의 probe step이 0개**였기 때문이다. 원 traceback은 `analyze.stdout`에 그대로 보존한다.

**원인 (관찰)**: server 인자 `--max-num-batched-tokens 2048` 때문에 `d + p > 2048`인 probe는 chunked prefill로 두 step에 나뉜다. G1 r0 로그의 step 모양은 다음과 같다.

- d=4, p=2048: `reqs=5 maxq=2044 toks=2048 mode=NONE` × 10, 이어서 `reqs=5 maxq=4 toks=8 mode=PIECEWISE` × 10
- d=1, p=2048: `reqs=2 maxq=2047 toks=2048` × 10

분석 코드는 probe를 `maxq == p`로 찾았으므로 이 cell들이 비었다. 설계 때 step token 상한과 `d + p`의 관계를 확인하지 않은 선등록의 오류다. p ≤ 1024인 cell과 MIXED는 영향이 없다(`d + p ≤ 2048`).

**수정 규칙 (데이터를 보기 전에 정함)**: probe는 **첫 chunk**로 찾는다. 조건은 `maxq == min(p, 2048 − d)`, `reqs == d + 1`이다. 구현은 opt-in flag `--chunk-budget 2048`이며, flag가 없으면 원 동작(원 오류)이 그대로 재현된다. lag 규칙 cell은 **그대로 EAGER d=4, p=2048**이고, 그 첫 chunk(2,044 prefill + 4 decode = 2,048 token)가 여전히 가장 큰 고립 step이다. `L` 후보 `{0,1,2}`와 argmax 규칙은 바꾸지 않는다.

**p = 2048 cell의 해석 제한**: 이 cell의 "고립 step"은 prompt 전체가 아니라 첫 chunk(`2048 − d` token)의 비용이다. 나머지 chunk(`p − (2048 − d)` token)는 다음 step에 PIECEWISE로 실행되며 이 cell에 포함하지 않는다. 표에는 `toks = d + 첫 chunk`와 `chunked` 표시를 남긴다.

**확인 순서**: 이 개정을 commit하기 전까지 본 것은 step 모양 집계(위 두 줄)와 lifecycle 유효성 field뿐이다. step 시간, 증분, lag elevation 수치는 보지 않았다.
