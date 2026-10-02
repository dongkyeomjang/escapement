# GTASK03 — GPU 관측 수단 확보: observation-only patch, KV events collector, 관문 G1–G3

## 상태

DONE

## 날짜

2026-09-29

## 판정

| 관문 | 원 기준 (첫 실행 09:26:47 UTC) | 개정 1 기준 (재실행 09:30:58 UTC) |
|---|---|---|
| **G1 의미론** | **`FAIL`** — (a)(b)(e) 통과, (c)(d)(f) 실패 | **`PASS`** — (a)–(f) 전부 |
| **G2 관찰자 효과** | `PASS` (순차 15/15 동일, 시간 비 중앙값 0.975) | **`PASS`** (15/15 동일, 중앙값 1.0018) |
| **G3 복구** | `PASS` | **`PASS`** |

**원 기준 G1 실패의 원인은 patch가 아니다**: (c)(d)는 선등록이 server 기동의 warmup step 2개를 예상하지 못했고(요청 15건은 요청별로 전부 정확히 일치), (f)는 collector endpoint 설정 오류였다(양쪽 모두 connect). 개정 1([GPU_OBS_GATE_PREREG.md](GPU_OBS_GATE_PREREG.md) 끝 절, `b936da8`)은 (c)(d)의 계수 창을 첫 `LOOKUP` 이후로 한정하고 endpoint를 ipc로 고쳤을 뿐, 나머지 기준은 바꾸지 않았다. 재실행에서 전 관문을 통과해 **patch를 GTASK04·05 측정에 쓴다.**

## 목적

GPU 지시문 G-02 작업 A·B. (A) `origin/main`의 NPU 모형 v1(TASK73–75)을 merge로 받는다. (B) v2 runner를 기판으로 고정한 채 step dispatch와 admission을 관측하는 observation-only patch와, 축출 귀속용 KV events collector를 만들고, 관문 G1–G3을 선등록 후 판정한다.

## 배경

관련 TASK:

- [GTASK01](GTASK01.md) — 관측 수단 감사(항목 9), patch 후보 제안
- [GTASK02](GTASK02.md) — v2 runner에서 `--cudagraph-metrics` 무출력, v1 runner 기동 실패
- [TASK12](../TASK12.md) — NPU observation-only patch와 관문 3개(형식 선례)
- [TASK72](../TASK72.md) — 사건 재생 R5′(이 관측 수단이 겨냥하는 GPU 대응)
- [TASK73](../TASK73.md) — 모형 v1(`lru_block_survival` 등), merge로 받음

## 시작 상태

- branch `gpu-a6000`, HEAD `2c4e732`(GTASK02), working tree clean
- **작업 A**: `git fetch` 후 `git merge origin/main` → **merge commit `a48c7b46246085ac2ea5121874de439c31d90b3d`**, 충돌 없음. 받은 commit `a2d6f1f`(TASK73), `86dcf37`·`15b41d2`(TASK74), `03493db`(TASK75). rebase 없음
- 설치본 두 대상 파일 원본 SHA256: `scheduler.py` `41ff2e52…bb5983`, `v1/worker/gpu/model_runner.py` `c5332aad…8a16`

## 수행 내용

1. patch 작성(`escapement_obs.patch`, 추가 32줄·삭제 0), hash-guarded `apply.sh`(status/apply/revert, version guard, 적용 후 AST 검사). 실제 적용 전에 `patch --dry-run`만 했다.
2. KV events collector(zmq SUB, vLLM import 없는 msgpack generic decode), 공용 lifecycle(`launch/lifecycle.py`: PID 종료, 명시 인자 강제 목록, GPU process 전·ready·후 기록, patch 상태 provenance)과 client(`launch/client.py`, `cached_tokens` 부재를 `None`으로)를 만들었다.
3. 관문 선등록 `3eebb02`(09:26:42 UTC) → 첫 실행(09:26:47–09:28:39) → 원 기준 G1 실패 → 원인 진단 → 개정 1 `b936da8`(09:30:51) → 재실행(09:30:58–09:32:36) → 판정.
4. 관문 통과 후 patch는 **복구(pristine) 상태**로 두었다. GTASK04·05의 측정 시작 직전에 `apply.sh apply`로 다시 적용한다(hash 재검증).

## 변경된 파일

- 선등록 `3eebb02`: `docs/research/gpu/{GPU_OBS_GATE_PREREG.md,GTASK03.md(skeleton),GPU_INDEX.md}`, `experiments/gpu/patches/{.gitattributes,vllm-0.22.0/escapement_obs.patch,vllm-0.22.0/apply.sh}`, `experiments/gpu/launch/{lifecycle.py,client.py}`, `experiments/gpu/obs/{kv_events_collector.py,parse_obs.py,gate_run.py,gate_judge.py,run_gates.sh}`
- 개정 1 `b936da8`: `GPU_OBS_GATE_PREREG.md`(개정 절), `lifecycle.py`(ipc endpoint), `gate_judge.py`(warmup 제외 창)
- 이 commit: `docs/research/gpu/GTASK03.md`, `docs/research/gpu/GPU_INDEX.md`

`experiments/gpu/patches/.gitattributes`는 unified diff의 빈 context 줄(공백 1자)이 `git diff --check`에 걸리지 않게 `*.patch -whitespace`만 둔다.

## 실험 또는 검증 방법

```bash
experiments/gpu/obs/run_gates.sh /home/csdc/kyeom/Project/escapement/results/gpu/obs_gate/20260929T0931Z-rev1
# A(원본) → apply.sh apply → B(patch, ESCAPEMENT_OBS=1, KV events) → apply.sh revert → gate_judge.py
```

server 인자(두 arm 공통): `--revision 1cfa9a72… --dtype bfloat16 --max-model-len 8192 --seed 20260929 --generation-config vllm --enable-prompt-tokens-details --block-size 16 --num-gpu-blocks-override 2048 --max-num-seqs 8 --max-num-batched-tokens 2048 --compilation-config '{"cudagraph_capture_sizes": [1, 2, 4, 6, 8]}'`, `CUDA_VISIBLE_DEVICES=0`. arm B에만 `--kv-events-config '{"enable_kv_cache_events": true, "publisher": "zmq", "endpoint": "ipc:///home/csdc/kyeom/envs/ipc/kv_events.ipc", "topic": ""}'`.

## 결과

Population: arm마다 요청 23건(순차 15, 동시 8), lifecycle 1개. Source: server 로그(`[GSTEP]`·`[GPFX]`), 응답 JSON, `/metrics`, KV events JSONL, `apply.sh status`. Device scope: GPU 0.

- `requested_condition`: arm A 원본, arm B patch + KV events
- `observed_condition`: 두 실행 모두 A는 `pristine`, B는 `patched` 확인 뒤 시작. 네 lifecycle 모두 기동 전 GPU process 0개, ready 시 자기 EngineCore 1개(GPU 0), 외부 process 0, preemption 0
- `condition_reached`: `YES`

### G1 (재실행, arm B)

| 항목 | 기준 | 관측 |
|---|---|---|
| (a) 계수 | LOOKUP = ALLOC = 23 = `request_success` 증분, ALLOC_FAIL 0 | 23 / 23 / 23 / 23, 0 |
| (b) hit | 요청별 로그 `hit` = 응답 `cached_tokens`(순차는 counter 2종도) | **23/23** 일치 |
| (c) Σ toks (첫 LOOKUP 이후) | Σ(prompt − cached + completion − 1) = 5,127 | **5,127** |
| (d) 순차 step 수 | Σ(ceil((prompt − cached)/2048) + completion − 1) = 243 | **243** |
| (e) dispatch 사상 | toks ≤ 8 → 격자 올림 + FULL(maxq 1)/PIECEWISE, > 8 → 그대로 + NONE | 위반 **0**(warmup 2 step 포함 375 step) |
| (f) KV events | `BlockRemoved` 0, seed prompt full block 178개 전부 `BlockStored`에 존재 | 42 batch, 64 event, seq gap 0, 축출 0, **누락 0/178** |

warmup step(보고만): `reqs=8 toks=16 maxq=2 padded=16 NONE`, `reqs=8 toks=8 maxq=1 padded=8 FULL` — 두 실행 모두 같았다.

### G2

| | 첫 실행 | 재실행 |
|---|---|---|
| 순차 생성 token 동일 | 15/15 | **15/15** |
| `elapsed(B)/elapsed(A)` 중앙값 [최소, 최대] | 0.975 [0.753, 1.008] | **1.0018** [0.871, 1.085] |
| server CPU 시간(workload 구간) A / B | 6.44 / 6.39 s | 6.38 / 6.39 s |
| collector CPU 시간 | 0.02 s(수신 0) | 0.02 s |
| 동시 8건 token 동일 (보고만) | 8/8 | 5/8 (`conc5_1`·`conc5_3`·`conc5_4` 다름) |

### G3

두 실행 모두 `revert` 후 `scheduler.py` `41ff2e52…`, `model_runner.py` `c5332aad…`, `state: pristine`.

### 원 기준 실패 상세 (첫 실행)

(c) 기대 5,127 대 관측 5,151, (d) 243 대 245 — 차이는 정확히 warmup 2 step(16 + 8 token)이다. 요청별로 나눠 보면 15건 모두 step 수·token 수가 식과 같았다. (f) collector 수신 0: vLLM publisher는 endpoint에 `*`·`ipc://`·`inproc://`가 있을 때만 bind한다(`vllm/distributed/kv_events.py:387–397`).

## 핵심 발견

1. **`stack`** — **v2 runner를 바꾸지 않고 step 단위 격자 관측을 얻었다.** 로그 1줄/step이 실행된 모든 step(요청 없는 warmup 포함)을 기록하고, token 수·step 수가 요청 단위 식과 정확히 맞으며, (`padded`, `mode`)가 source-read 사상 규칙과 375/375 일치한다.
2. **`stack`** — **server 기동 warmup이 요청 없이 non-dummy step 2개를 실행한다**(8 요청, 16·8 token). scheduler와 KV pool을 거치지 않아(첫 LOOKUP 시 free 2,047) 생존에는 영향이 없지만, step 계수에는 들어간다.
3. **`stack`** — **KV events는 patch 없이 block 단위 저장을 내용과 함께 준다** — seed prompt block 178개를 token 내용으로 전부 찾았다. endpoint는 server가 bind하는 형식(ipc)이어야 한다.
4. **`universal`** — **관찰자 효과는 판정 가능한 크기 안이다**: 순차 요청의 생성은 동일, 시간 비 중앙값 1.002, server CPU 차 0.01 s.
5. **`stack`** — **동시 batch의 생성 token은 같은 설치·같은 입력에서도 run 사이에 달라질 수 있다**(재실행에서 5/8, 첫 실행 8/8). batch 구성이 도착 시각에 따라 달라지고 bf16 수치가 batch에 의존하기 때문으로 보인다(가설). 동시 workload의 token 동일성을 관찰자 효과 판정에 쓰지 않은 선등록 결정이 맞았다.

## 해석

- 발견 1·3으로 NPU의 `[BUCKET]`(step 격자)과 `[PFX]`(admission) 두 관측이 GPU에서 대응물을 얻었다. 요청 id를 담은 admission 로그와 token 내용을 담은 KV events를 합치면 [TASK72](../TASK72.md) R5′ 식의 사건 재생 입력이 된다.
- `GSTEP`의 시각은 CPU dispatch 시각이다. async scheduling에서 GPU 실행 시간과 같지 않으므로, step 비용(GTASK05)은 연속 dispatch 간격이 GPU 시간을 반영하는 조건을 설계에 넣어야 한다.

## 확인되지 않은 사항

- 동시 batch token 차이의 원인(batch 구성 차이인지 다른 비결정성인지) — 보고만
- KV events의 `ts`와 `[GSTEP] wall`의 정렬 정밀도(같은 process의 `time.time()`이나 step 끝과 시작의 차이) — GTASK04에서 사용하며 확인

## 실패 / 무효 시도

- 첫 관문 실행의 원 기준 G1 실패(위). 선등록을 개정해 재실행했고 원 결과를 보존했다(`results/gpu/obs_gate/20260929T0927Z/`).
- `git diff --check`가 patch 파일의 빈 context 줄을 trailing whitespace로 잡았다 → `experiments/gpu/patches/.gitattributes`.

## 연구 원칙에 미치는 영향

- 새 관측 채널의 선등록에는 **요청 없이 실행되는 경로**(warmup, profile)를 계수 창에서 명시적으로 다뤄야 한다. 같은 함정이 NPU에서 재발한 적은 없어 KNOWN_PITFALLS에는 올리지 않는다(추가 기준 미달).

## 다음 작업

- GTASK04(순차 생존 곡선 blind 예측), GTASK05(step 비용 측정). 둘 다 측정 전 patch 재적용·선등록.

## 재현 정보

- 선등록 commit: **초판 `3eebb02` (09:26:42 UTC) → 첫 실행 09:26:47. 개정 1 `b936da8` (09:30:51 UTC) → 재실행 09:30:58.** 두 경우 모두 선등록이 먼저다.
- merge commit `a48c7b4`
- raw: `results/gpu/obs_gate/20260929T0927Z/`(원 기준 실행), `results/gpu/obs_gate/20260929T0931Z-rev1/`(개정 1) — 각 `sequence.log`, `{A,B}/{server.log,requests.json,summary.json,lifecycle.json,env.txt}`, `B/{kv_events.jsonl,collector.log}`, `revert.log`, `verdict.json` (git 비추적)
- patch 파일 SHA256 `d75d04d8…427f`
