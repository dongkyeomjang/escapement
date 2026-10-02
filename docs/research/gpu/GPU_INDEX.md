# Escapement GPU(A6000) 기판 Task Index

이 문서는 A6000 서버 작업의 진입점이다. NPU 연구 전체의 source of truth는 [docs/research/INDEX.md](../INDEX.md)이며, 이 색인은 그 **결정 4**(A6000을 두 번째 기판으로 격상)와 Advisor GPU 지시문 G-01의 작업 규약 아래에서만 쓴다. 작성 규칙은 [TASK_GUIDE.md](../TASK_GUIDE.md)를 따른다.

## 작업 규약 (GPU 지시문 G-01 §0, 저장소 규칙보다 우선)

- **branch**: `gpu-a6000`에서만 작업한다(시작 `e1f791e`, `origin/main` TASK72 시점). `main`에 commit·push하지 않는다.
- **main 반영**: `git fetch` 후 `git merge origin/main`(merge commit)만. **rebase 금지**(선등록 commit hash 보존). 충돌 시 즉시 중단·보고.
- **파일 영역**: `docs/research/gpu/`, `experiments/gpu/`, `results/gpu/`(git 비추적)만 쓴다. `src/continuum/`, `docs/research/INDEX.md`, 기존 `TASK*.md`, `experiments/npu/`는 읽기만 한다. `src/continuum/` 수정이 필요하면 보고한다.
- **번호**: `GTASKNN`은 이 디렉터리 안에서만 센다. `docs/research/TASK*.md` 번호 계산에 영향을 주지 않는다.
- **push**: 작업 종료 보고 끝에 `origin/gpu-a6000` push 여부를 묻고 승인 시에만 push한다.
- 나머지 규칙(INDEX-first, 선등록, provenance, `UNKNOWN`/`PARTIAL`, 관측 불가 값을 0으로 채우지 않음, 파일 명시 stage, `git diff --check`)은 그대로다.

## 현재 상태

**GPU Stage 0 `PASS`** ([GTASK02](GTASK02.md), 선등록 [GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md) `7bb07f5` → 측정 08:52:18 UTC). [GTASK01](GTASK01.md)에서 환경 inventory, `vllm 0.22.0`(CUDA 13.0 빌드, NPU upstream과 같은 버전) 설치, `Qwen/Qwen3-4B@1cfa9a72…`(NPU와 같은 revision·byte 수) download, source 감사 9항목을 마쳤다. GTASK02에서 KV pool(`--num-gpu-blocks-override`)과 decode 격자(`cudagraph_capture_sizes`)가 server 인자로 고정·확인됐고, hit 공식 `floor(min(shared, query−1)/16)·16`이 5/5로 맞았으며, **decode 생성 token도 캐시됨**(H5 1,024)을 확인했다. Qwen3-4B는 기본으로 model runner v2에서 돌며 v2에서는 `--cudagraph-metrics`가 비어 있다. v1 runner(L3)는 FlashInfer sampler의 JIT build가 `nvcc`를 요구해 기동하지 못했다. descriptor 초안은 [`a6000_vllm_0220_draft.py`](../../../experiments/gpu/substrate/a6000_vllm_0220_draft.py)이며 `SubstrateDescriptor`와의 적합성 문제 11건을 보고했다.

**G-07 진행 중**: GTASK17 마무리 → main 반영 → context 길이 step 비용(작업 B) → 붕괴 영역 blind N 25·28, 세 비용 입력(작업 C) → 정정 기록(작업 D).

**G-06(GTASK17)**: **관측 수단에 의한 관찰자 효과 없음**(streaming·KV events·admission log 비 0.9998–0.9999). 통제 부하(context 64–320 token)에서 GTASK11 조건 step은 가격과 같다(n = 8에서 1.009 대 운영 1.219). 22 % 초과는 이 세 요인 밖에서 온다.

**G-05 완료(GTASK12–16), Advisor 승인(G-06 §1)**: GTASK11 데이터의 분석만(측정 0).
- **사건 재생 `PASS`**(GTASK12, 선등록 `0973228`): 16,794/16,794. 따라서 **붕괴 과소 예측은 동역학 오류**다.
- **시간 척도(개발 집합, GTASK13)**: 운영 부하 step은 가격 채널의 1.21배(lag 1). 이를 넣으면 N26 BASE 오차가 +0.207 → +0.009(×1.210)·+0.033(mode_dist)로 줄어든다. 비용 비는 ×1.131이 가장 좋다(Σ 0.013).
- **대기열(GTASK14)**: 재사용 오차와 가장 같이 움직이는 양은 idle 중 다른 요청의 할당량(ρ −0.87–−0.95)이다. 할당 속도는 sim과 관측이 같고, 다른 것은 대기 길이다.
- **채널(GTASK15)**: 초과분의 89 %는 FULL decode(1.22배, decode 폭 비례)에서 나온다. idle 조각 0, small-p eager 5 %. 1.131은 lag 0 cap에 의한 과소 추정이다.
- **정상성(GTASK16)**: h·재사용 모두 `NOT_NONSTATIONARY`(11 cell).
- **v1.1(GPU)에 넘길 사항**: (1) 시간 척도는 가격 채널이 아니라 운영 부하 step 시간이다(FULL 16.5 ms, lag 1 귀속; 개발 집합 값). (2) 대기열 항은 대기 시간을 idle 길이에 더하고, 할당 속도(block/s) × idle 길이로 재조회 전 할당 수를 만든다. (3) 붕괴 cell의 miss → 할당 속도 증가(N26 BASE 200 대 172 block/s) 되먹임. (4) 붕괴 cell은 run 간 산포가 크다(60 s 창 재사용 |D| 0.20–0.22).

**G-04 완료(GTASK11), Advisor 승인(G-05 §1)**: 본 측정 55/55 유효, LRU_SUPPORTED, sim LRU PASS / 해석 v1 FAIL(포화 근처). N=26 plan은 v1.1 blind 검증에 재사용 금지.

**G-03 완료(GTASK07–10)**: GPU multi-turn 설계·구성 blind 선정(N 20·22·24, pool 1,900/2,300)·세 예측기 blind 예측과 판정 기준 선등록(`2bef619`)·파일럿(streaming `EQUIVALENT`). 본 측정은 G-04.

**GTASK05 (step 비용) `PARTIAL`**: 2026-09-29 문제 PCIe 슬롯 비활성화로 host의 A6000이 2장이 됐고, 이후 측정은 uuid `4485e769…` 카드에서 한다(GTASK02–04는 빠진 카드 `00596b63…`). FULL·eager 곡선은 확보, PIECEWISE 증분은 관측 채널 분해능 아래.

**Advisor 결정 대기**: (1) step 단위 격자 관측 수단(v1 runner + `VLLM_USE_FLASHINFER_SAMPLER=0` 또는 `CUDA_HOME` 지정 / v2 observation-only patch), (2) `SubstrateDescriptor` 확장(`src/continuum/`, 이 branch에서 수정 금지), (3) GPU 간섭 통제(`EXCLUSIVE_PROCESS`·persistence mode, root 필요).

**환경 요약**: RTX A6000 × 3 (48 GiB, cc 8.6), driver 580.178.04, venv `/home/csdc/kyeom/envs/vllm-0.22.0`(Python 3.12.13, torch 2.11.0+cu130), `HF_HOME=/mnt/nvme/hf`. 계정 1개, 조사 시점 GPU 전부 idle.

**source 감사가 정한 GPU 기판의 성질** (NPU와의 차이, 상세는 [GTASK01](GTASK01.md) 표):

| 축 | GPU (vLLM 0.22.0) | NPU (RBLN) |
|---|---|---|
| 조회·할당 순서 | 조회 → hit block `touch` → 새 할당. 같은 admission에서 hit block 축출 경로 없음 | 할당 → 조회 |
| 회수 | release 시점 LRU, 요청 안에서 tail-first, 16-token block | 할당 순서 FIFO, 시퀀스 단위 outer slot |
| hit 공식 | `floor(min(shared, query−1)/16)·16`, **생성 token도 캐시** | 같은 형태, 128 token, prefill token만 |
| KV 용량 | `--num-gpu-blocks-override N` (사용 가능 N−1) | compile `batch_size` |
| preemption | **있음**(recompute, FCFS 최신 admission, 끌 수 없음) | 없음 |
| 격자 | cudagraph capture size, **token 수**로 사상, server 인자로 변경 | compile bucket, 요청 수로 사상 |
| prefill | chunked 기본, **꺼도 decode와 혼합** | 배타 실행 |
| 비요청 KV 소비자 | null block 1개(상수) | step마다 dummy block |

## Task Index

| Task | 상태 | 제목 | 간략 설명 |
|---|---|---|---|
| [GTASK01](GTASK01.md) | DONE | A6000 기판 착수: inventory, vLLM 0.22.0 설치, source 감사 | 환경 inventory와 간섭 위험 판단, 격리 venv에 `vllm 0.22.0` 설치, NPU와 같은 revision의 model download(byte 일치), 조회·할당 순서·회수·hit·용량·preemption·격자·chunked prefill·비요청 소비자·관측 수단 9항목 source 감사 |
| [GTASK02](GTASK02.md) | DONE | GPU Stage 0 기능 확인과 descriptor 초안 | 선등록 C0–C5 전부 충족으로 **Stage 0 `PASS`**. override 16,034→2,048 block, 격자 `[1,2,4,6,8]` 반영, hit 5/5, 생성 token 캐시(H5 1,024), v2 runner에서 cudagraph 통계 없음, v1 runner는 `nvcc` 부재로 기동 실패. descriptor 초안과 적합성 문제 11건 |
| [GTASK03](GTASK03.md) | DONE | GPU 관측 수단: observation-only patch·KV events collector·관문 G1–G3 | merge `a48c7b4`. v2 runner `[GSTEP]`·scheduler `[GPFX]` 로그 patch(32줄, env gate)와 KV events collector. 원 기준 G1 `FAIL`(warmup 2 step 미예상, endpoint 오류) → 개정 1 후 **G1·G2·G3 `PASS`**(hit 23/23, 사상 375/375, 시간 비 1.002) |
| [GTASK04](GTASK04.md) | DONE | 순차 생존 곡선: 첫 교차 기판 blind 예측 | **`CONFIRMED` 60/60 정확 일치**(네 채널 일치, 무효 0). NPU 데이터로 만든 모형 코드(무수정)에 GPU 파라미터·의미론만 넣어 측정 전 commit. 문턱은 token 총량, 곡선은 16 token 계단, 생성 token 캐시 확인(2,016) |
| [GTASK05](GTASK05.md) | PARTIAL | GPU step 비용 측정 (FULL · PIECEWISE · eager) | 첫 run은 host 다운으로 중단 → 문제 PCIe 슬롯 비활성화, **측정 카드 변경**(uuid `4485e769…`, 개정 1) 후 6 lifecycle 전부 유효. 선등록 분석은 p=2048 chunk 분할로 실패 → 개정 2(수치 확인 전). FULL decode 13.3–14.4 ms, `g` 0.041 ms/요청, padding +3.4 % 대 격자 밖 eager +42 %, lag `L = 1` 확인, eager 증분 p=256→2048에서 12→138 ms. **PIECEWISE 증분은 dispatch 채널 분해능(약 2 ms) 아래라 `UNKNOWN`** |
| [GTASK06](GTASK06.md) | DONE | descriptor 구조 요구사항 정리 (두 기판 공통 표현) | 코드 변경 0. 층 목록·`reuse_layer`·규칙 field 5개(축출 기준, 창 시작, 요청 내부 손실 순서, 조회·할당 순서, 캐시 대상)·`value_source`·`grid_unit` 등 11개 묶음을 NPU 값·GPU 값과 함께 [DESCRIPTOR_REQUIREMENTS.md](DESCRIPTOR_REQUIREMENTS.md)에 정리. GPU step 비용 값은 GTASK05 대기 |
| [GTASK07](GTASK07.md) | DONE | GPU multi-turn 설계: token id prompt, runner, GPU 의미론 예측기 | merge `fe8a4df`(TASK75–80). NPU 설계 대비 바뀐 15개 항목([GPU_MULTITURN_DESIGN.md](GPU_MULTITURN_DESIGN.md)). streaming token id prompt·`return_token_ids` 기능 확인 6/6(생성 token까지 hit 식 일치). `continuum.sim`은 GPU 의미론을 표현할 수 없어 `experiments/gpu/multiturn/`에 시뮬레이터(LRU·FIFO)·해석 v1 GPU 인스턴스·비용 모형 작성. neutral `lru_block_survival` underflow(평균 > 745) 발견·wrapper 우회 |
| [GTASK08](GTASK08.md) | DONE | GPU multi-turn 구성·pool blind 선정 | 측정 없이 모형으로 선정. 확증 N = 20·22·24, BASE pool 1,900(preemption 불가 하한 1,857)/격자 (1,2,4,8,16), POOL 2,300, POOL+GRID (1,5,7,8,16), `max_num_seqs` 8. 원 규칙 5(상한 0.85) 해 없음 → 개정 1(상한 0.90). 재사용 압력은 포화 근처에서만 생기고 N=26에서 붕괴(sim 0.37, 해석 0.78) |
| [GTASK09](GTASK09.md) | DONE | GPU multi-turn 본 실험 blind 예측·판정 기준 선등록, 파일럿 선등록 | plan 20(N 20·22·24 확증, 26 탐색)+파일럿 3. 세 예측기 × 두 bound. LRU−FIFO 재사용 차 0.08–0.17(9/9 cell) → 판별 가능. POOL/BASE 비 0.96–0.99(해상도 경계). §2.1 구간 영향 ≤ 0.04 %(재도착 혼합 step은 대부분 eager). 계기 점검에서 id join 오류 수정 |
| [GTASK10](GTASK10.md) | DONE | GPU multi-turn 파일럿: runner·streaming·산포 | 12/12 유효, preemption 0, step mode 예측 불일치 0. streaming `EQUIVALENT`(중앙 1.0066, CI [0.994, 1.009]) → 본 실험 streaming. POOL/BASE 짝 ratio 산포 0.025–0.038. lifecycle 3.2–4.0분 |
| [GTASK11](GTASK11.md) | DONE | GPU multi-turn 본 측정과 판정 | 개정 1 `721e4d0`(NPU 개정 2와 정렬) → 55/55 유효, 재실행 0. **LRU_SUPPORTED**(8/9, Σ오차 0.148 대 0.937, 부분 hit·고아 축출 0/958,078 일치). sim LRU §5.1·§5.2 PASS, 해석 v1 §5.1·§5.2 FAIL(N24 BASE 포화 근처), §5.3 PASS, §5.4 INCONCLUSIVE, §5.6 PASS(decode-only). N26 BASE 재사용 붕괴 0.450(세 예측기 모두 과소). **N = 26 plan(`gmain-n26-r*`)은 v1.1 blind 검증에 다시 쓰지 않는다** |
| [GTASK12](GTASK12.md) | DONE | 사건 재생 검사(G-05 작업 A) | 선등록 `0973228` → 계산. **`PASS`: 55/55 lifecycle 정확 일치율 1.000, 16,794/16,794**(N24 BASE 1,477, N26 BASE 1,366 전부), 결정 불가 0. free 수 27,652건·KV 축출 순서열 958,078건 전부 일치. 반사실(FIFO 0.63–0.84 등)은 포화 cell에서 크게 틀림. **붕괴 과소 예측은 의미론이 아니라 동역학 오류** |
| [GTASK13](GTASK13.md) | DONE | 시간 척도 가설 — **개발 집합** (G-05 작업 B) | sim 시간 진행 = 가격 채널 `gpu_cost.step_ms`(client 지연 0) 확인. 변형 ×1.131 / ×1.210 / mode별 분포. N24·N26 BASE 오차 +0.084·+0.207 → ×1.210 +0.014·+0.009, mode_dist +0.026·+0.033. 발견 4 차이의 설명 비율 34–66 %(×1.131), 70–84 %(mode_dist), 83–96 %(×1.210). 비용 비 Σ는 ×1.131이 최선(0.013). **판정 없음, blind 검증은 새 붕괴 cell에서** |
| [GTASK14](GTASK14.md) | DONE | 대기열 동역학 비교 (G-05 작업 C) | 원래 sim은 대기를 과소 재현한다(N20 대기 중앙 0.02 대 0.69 s, 대기열 평균 약 절반). ×1.210이면 관측과 거의 같다. 재사용 오차와 가장 같이 움직이는 양: idle 중 다른 요청의 할당량 평균(Spearman orig −0.95, 합산 −0.87). 할당 속도는 차이 없음 |
| [GTASK15](GTASK15.md) | DONE | 직접 채널 대 가격 채널 분해 (G-05 작업 D) | lag 1 귀속 wall/price 1.210, idle 조각 0.0003 %, small-p eager 4.8 %, **FULL decode 89 %**(1.22배, d = 1 1.03 → d = 8 1.22, 대기열 무관). GTASK11 직접 채널 1.131은 lag 0 cap이 큰 prefill 시간을 자른 과소 추정. 계측 제안 3건(승인 대상) |
| [GTASK16](GTASK16.md) | DONE | 정상성, 같은 길이 기준 (G-05 작업 E) | 방법 `f61b4fd` 계산 전 commit(NPU TASK83 방법). h(decode-only)·재사용 모두 `NOT_NONSTATIONARY`(q_h 중앙 0.43, q_Δ 0.44). 붕괴 cell은 60 s 창 재사용 산포 큼(\|D\| 0.20–0.22) |
| [GTASK17](GTASK17.md) | DONE | 운영 조건 step 비용 재측정, 요인 분해 (G-06 작업 A) | 설계 `b59287c` 측정 전 commit. 16/16 유효. streaming·KV events·admission log 효과 모두 비 0.9998–0.9999 → **관찰자 효과 없음**. GTASK11 조건 / 가격 n = 8에서 1.009(운영 1.219), 기울기 0.0615 ms/요청 → 22 % 초과는 세 요인에서 오지 않는다. 예상(streaming 최대)은 빗나감. driver 자동 commit 실패(ignored `sequence.log`) 경위 기록·수정 |

## 다음 작업

Advisor 지시 없이 다음 GPU 작업을 시작하지 않는다. G-05 결정 요청: (1) v1.1 + 시간 척도 변형의 blind 검증 cell(새 seed, N = 26·28 등)과 시간 척도 동결값(×1.210 / mode_dist), (2) FULL decode 22 % 초과의 원인 계측(GTASK15 제안 1–3, patch·측정은 승인 대상), (3) 붕괴 cell의 replicate 수(run 간 산포가 크다, GTASK16), (4) GTASK11 직접 채널(1.131) 기록의 정정 범위(시간 척도로는 1.21).
