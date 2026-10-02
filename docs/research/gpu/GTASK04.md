# GTASK04 — 순차 생존 곡선: 첫 교차 기판 blind 예측

## 상태

DONE

## 날짜

2026-09-29

## 판정

**`CONFIRMED` — 60/60 trial 정확 일치.** 무효 trial 0, 채널 불일치 0, preemption 0. 선등록 [GPU_SURVIVAL_PREREG.md](GPU_SURVIVAL_PREREG.md)(`87731c5`, 09:37:14 UTC)의 확증 기준(60/60 유효·채널 일치·ch1 = 예측 정수, 허용 오차 없음)을 그대로 충족했다.

| | 예측 | 관측 |
|---|---|---|
| resume hit (60 trial) | 모형 코드 = block-exact replay, 60/60 사전 일치 | **60/60 정확히 같다**(ch1 응답 = ch2 `LOOKUP` = ch3 counter 2종) |
| T block 축출 수(KV events) | 60 trial 정수 | **60/60 같다**(ch4) |
| 반복 probe (i, 500, m=23 ×3), (i, 2000, m=6 ×3) | 1,024 / 704 | 3/3, 3/3 같다 |

**이것은 이 연구의 첫 교차 기판 blind 예측이다**: NPU 데이터로 만든 모형 코드(`src/continuum/model/`, import만)에 GPU 파라미터와 source-read로 확정된 GPU 의미론만 넣어, GPU에서 생존을 한 번도 재기 전에 60개 정수를 commit했고, 전부 맞았다.

## 목적

GPU 지시문 G-02 작업 C. NPU [TASK14](../TASK14.md)·[TASK15](../TASK15.md)의 순차 프로토콜(target → 배경 m개 → resume, 동시성 1, trial마다 새 server)을 A6000에서 재현하고, 모형의 예측을 측정 전에 선등록한 뒤 판정한다.

## 배경

관련 TASK:

- [TASK14](../TASK14.md), [TASK15](../TASK15.md) — NPU 순차 생존: 배경 요청 **개수** 7에서 절벽(크기 무관)
- [TASK29](../TASK29.md) — GPU 측 절제 계산(할당 후 조회 가정이라 **이번 예측에 쓰지 않음**, INDEX 결정 4 개정)
- [TASK71](../TASK71.md), [TASK73](../TASK73.md) — 모형 v0·v1(이번 예측의 코드)
- [GTASK01](GTASK01.md), [GTASK02](GTASK02.md) — GPU 파라미터·의미론 출처
- [GTASK03](GTASK03.md) — 관측 patch·KV events(관문 통과)

## 시작 상태

- branch `gpu-a6000`, HEAD `87731c5`(선등록), patch `apply.sh apply`로 재적용(09:37:20 UTC, hash 검증 `patched`)
- 모든 trial 기동 전 GPU compute process 0, ready 시 자기 EngineCore 1개(GPU 0), 외부 process 0

## 수행 내용

1. **예측**([`predict.py`](../../../experiments/gpu/survival/predict.py)): 모형 코드 `survival.sequential_window(..., resume_allocates_first=False)` + `survival.reusable_tokens(granularity="block")`에 `C = 800`, 단위 16, wrapper 입력(생성 token 포함 `u = ceil((P+g−1)/16)`, 캐시 가능 prefix `floor((P+g−1)/16)·16`)을 넣었다. 미사용 block 우선 + release 순서 LRU가 이 프로토콜에서 할당 FIFO와 같은 순서가 된다는 등가성으로 FIFO 창 식을 그대로 썼다. 독립 검산으로 vLLM free queue의 block-exact replay([`gpu_pool_replay.py`](../../../experiments/gpu/survival/gpu_pool_replay.py))를 돌려 60/60 같음을 확인한 뒤 commit했다.
2. **측정**([`survival_run.py`](../../../experiments/gpu/survival/survival_run.py)): 60 trial, 09:37:25–10:21:01 UTC(43.6분, trial당 약 44 s, 기동 35.0–36.1 s).
3. **판정**([`survival_judge.py`](../../../experiments/gpu/survival/survival_judge.py)): 네 채널을 trial마다 대조.

## 변경된 파일

- 선등록 `87731c5`: `docs/research/gpu/{GPU_SURVIVAL_PREREG.md,GTASK04.md(skeleton),GPU_INDEX.md}`, `experiments/gpu/survival/{gpu_pool_replay.py,predict.py,survival_run.py,survival_judge.py,prediction/predictions.json}`
- 이 commit: `docs/research/gpu/GTASK04.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

선등록 문서의 실행 절차 그대로. server: `--num-gpu-blocks-override 801 --max-num-seqs 1 --max-num-batched-tokens 2048 --block-size 16 --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 8, 16]}'` + 공통 인자, `ESCAPEMENT_OBS=1`, KV events(ipc).

## 결과

Population: resume 요청 60건(trial당 1건). Unit: token, block. Source: 응답 JSON, server 로그 `[GPFX]`, `/metrics`, KV events. Device scope: GPU 0.

- `requested_condition`: 선등록 격자 60 trial
- `observed_condition`: 60 trial 전부 실행, 예외 0, 모든 요청 status 200, 생성 길이 요청대로(`ignore_eos`), preemption 0, `ALLOC_FAIL` 0
- `condition_reached`: `YES`

### 예측 대 관측 (resume hit token; 네 채널이 모든 칸에서 같아 한 값으로 적는다)

| 배경 크기 | m | (i) 예측 | (i) 관측 | (ii) 예측 | (ii) 관측 | T 축출 block (i)/(ii) |
|---|---|---|---|---|---|---|
| — | 0 | 2,000 | **2,000** | 2,016 | **2,016** | 0 / 0 |
| 500 | 10, 20, 21 | 2,000 | **2,000** | 2,016 | **2,016** | 0 / 0 |
| 500 | 22 | 1,536 | **1,536** | 1,536 | **1,536** | 29 / 30 |
| 500 | 23 | 1,024 | **1,024** (×3) | 1,024 | **1,024** | 61 / 62 |
| 500 | 24 | 512 | **512** | 512 | **512** | 93 / 94 |
| 500 | 25, 26, 30, 40 | 0 | **0** | 0 | **0** | 125 / 126 |
| 1,000 | 5, 10 | 2,000 | **2,000** | 2,016 | **2,016** | 0 / 0 |
| 1,000 | 11 | 1,712 | **1,712** | 1,712 | **1,712** | 18 / 19 |
| 1,000 | 12 | 704 | **704** | 704 | **704** | 81 / 82 |
| 1,000 | 13, 14, 20 | 0 | **0** | 0 | **0** | 125 / 126 |
| 2,000 | 3, 5 | 2,000 | **2,000** | 2,016 | **2,016** | 0 / 0 |
| 2,000 | 6 | 704 | **704** (×3) | 704 | **704** | 81 / 82 |
| 2,000 | 7, 8, 10 | 0 | **0** | 0 | **0** | 125 / 126 |
| 4,000 | 2 | 2,000 | **2,000** | 2,016 | **2,016** | 0 / 0 |
| 4,000 | 3 | 752 | **752** | 752 | **752** | 78 / 79 |
| 4,000 | 4, 5 | 0 | **0** | 0 | **0** | 125 / 126 |

T가 남긴 hash block 수(KV events `BlockStored`)는 (i) 125, (ii) **126**으로 60 trial 모두 wrapper 입력(생성 token 캐시)과 같다. 전체 trial별 값은 `verdict.json`.

### NPU와의 대비 (같은 프로토콜 길이)

| | NPU (RBLN, [TASK15](../TASK15.md)) | GPU (A6000, 이번) |
|---|---|---|
| 생존 문턱의 변수 | 배경 요청 **개수**(크기 500–4,000 token에서 모두 B = 7) | 배경 **token 총량**(누적 block > `C − u_T` = 674에서 손실 시작, ≥ 800에서 전손) |
| 곡선 모양 | 절벽(1,920 → 0) | **16 token 계단**(500 token 배경: 2,000 → 1,536 → 1,024 → 512 → 0) |
| 부분 손실 | 없음(시퀀스 단위 slot) | 있음(꼬리부터, 앞 block이 남아 hit 유지) |
| 생성 token | 캐시 안 됨 | 캐시됨 — (ii)에서 무손실 hit 2,016(> 2,000) |

## 핵심 발견

1. **`universal`** — **NPU 데이터로 만든 생존 모형(v0 block 창 식)이 GPU 파라미터와 source-read 의미론만으로 GPU 순차 생존 60개 정수를 측정 전에 전부 맞혔다.** 모형 식 자체는 무수정 import였다. 예측이 맞은 것은 식의 형태(넘친 단위 = `u_T + Σu − C`, 꼬리부터 손실, hit 식)가 대기열 산술이기 때문이다.
2. **`class`** — **block 단위·release 순서 LRU 기판에서 생존 문턱은 요청 개수가 아니라 token 총량의 함수이고, 곡선은 절벽이 아니라 block 단위 계단이다.** 근거: 같은 프로토콜에서 배경 크기 4종이 모두 누적 block 674(손실 시작)·800(전손) 경계에서 갈렸다(500 token은 손실 시작 m = 22·전손 m = 25, 4,000 token은 3·4). [TASK29](../TASK29.md) 발견 1의 `class` 승격 조건("향후 GPU 실측 1건")이 **이 결과로 충족**된다 — 문턱의 성격이 슬롯 구조(개수) 대 block pool(총량)에서 나온다.
3. **`stack`** — **이 GPU 기판은 decode 생성 token을 캐시한다**(조건 (ii): 무손실 hit 2,016, T hash block 126). NPU 층 2와 반대다([TASK24](../TASK24.md)).
4. **`stack`** — **새 server의 순차 프로토콜에서 release 순서 LRU는 할당 순서 FIFO와 같은 순서로 축출한다**(미사용 block 우선 때문). 이 등가성은 동시 부하·재사용 block의 touch가 있으면 깨질 것이다(가설).
5. **`universal`** — 관측 네 채널(응답, admission 로그, counter, KV events)이 60 trial 전부에서 일치했다. GPU에서는 NPU의 층 1/층 2 괴리([TASK14](../TASK14.md))가 없다 — 단일 층이기 때문이다.

## 해석

- 이 확증은 **결정론적 순차 프로토콜**에 대한 것이다. 모형의 확률적 부분(v1 Poisson 근사, `lru_block_survival`의 λ), 동시 부하에서의 touch·공유 prefix, preemption은 검증하지 않았다. 다음 blind 검증은 steady-state multi-turn에서 해야 한다([TASK75](../TASK75.md) 설계 초안).
- 예측에서 wrapper가 넣은 것(생성 token 캐시, 미사용 우선, release 순서, hit 선보호)이 모두 맞았다는 것은, 그 field들을 descriptor에 올리면([DESCRIPTOR_REQUIREMENTS.md](DESCRIPTOR_REQUIREMENTS.md)) wrapper 없이 같은 예측이 나온다는 뜻이다.

## 확인되지 않은 사항

- 동시 부하에서 release LRU와 FIFO의 차이(touch된 block의 재배치, 공유 prefix)
- preemption 영역
- chat 경로(템플릿 재토큰화)에서 생성 token이 재도착 prompt에 같은 id로 실리는지

## 실패 / 무효 시도

없음. 60 trial 모두 첫 시도에 유효했다.

## 연구 원칙에 미치는 영향

- 원칙 4의 GPU 방향 적용이 맞았다: [TASK29](../TASK29.md)의 GPU 측 수치(할당 후 조회 가정)를 쓰지 않고 GPU source-read로 새로 예측했다.
- 교차 기판 예측에서 "모형 코드(무수정)"와 "기판 의미론 wrapper"를 분리해 적는 방식이 결과의 귀속을 분명하게 했다 — 맞은 것이 식인지 wrapper인지 따로 말할 수 있다.

## 다음 작업

- descriptor 개편 후 wrapper 없이 같은 예측이 재현되는지(회귀) — NPU 쪽 개편 뒤
- GPU steady-state multi-turn blind 예측(확률적 부분의 검증) — Advisor 지시 대상

## 재현 정보

- **선등록 commit `87731c52d6cc0b61f9d1ac976c3ab5541b29cf91` (2026-09-29 09:37:14 UTC) → patch 재적용 09:37:20 → 첫 trial 기동 09:37:25 UTC.** 선등록이 먼저다. 판정 기준·예측은 측정 후 바꾸지 않았다.
- 예측 산출물 `experiments/gpu/survival/prediction/predictions.json`(SHA256 `ee181fb2…85d1`)
- raw: `results/gpu/survival/20260929T0937Z/` — trial 60개 디렉터리(`trial.json`, `server.log`, `kv_events.jsonl`, `lifecycle.json`, `env.txt`, `collector.log`), `progress.log`, `verdict.json` (git 비추적)
- 판정: `survival_judge.py --run-dir <RUN> --pred <predictions.json> --out <RUN>/verdict.json`
