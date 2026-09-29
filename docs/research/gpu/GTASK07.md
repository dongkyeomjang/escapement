# GTASK07 — GPU multi-turn 설계: token id prompt, runner, GPU 의미론 예측기

## 상태

DONE

## 날짜

2026-09-29

## 목적

GPU 지시문 G-03 작업 A.
- NPU multi-turn 설계([TASK75](../TASK75.md)–[TASK80](../TASK80.md))를 기본으로 하고, GPU 기판에서 달라져야 하는 것만 바꾼다. 바뀐 점과 이유는 [GPU_MULTITURN_DESIGN.md](GPU_MULTITURN_DESIGN.md)에 표로 적는다.
- token id prompt 경로를 source와 실제 server에서 확인한다.
- 이후 작업 B·C가 쓸 GPU runner와 GPU 의미론 예측기(시뮬레이터, 해석 모형 v1 GPU 인스턴스, step 비용 모형)를 작성한다.

## 배경

- merge `fe8a4df`(`origin/main` `c702b57`, TASK75–80 포함)
- [GTASK02](GTASK02.md) H5: 생성 token 캐시
- [GTASK03](GTASK03.md): 관측 patch, 발견 5(동시 batch 생성 내용 비결정)
- [GTASK04](GTASK04.md): token id prompt·`return_token_ids`·`ignore_eos`로 60/60
- [GTASK05](GTASK05.md): step 비용
- [GTASK06](GTASK06.md): descriptor 요구사항

## 시작 상태

- branch `gpu-a6000`, HEAD `3f5d930`
- `git merge origin/main` → merge commit **`fe8a4df`**(충돌 없음)

## 수행 내용

1. **source 확인** (`vllm 0.22.0`)
   - `CompletionRequest.prompt`는 `list[int]`를 받는다(`entrypoints/openai/completion/protocol.py:46`).
   - `return_token_ids`(`:142`)를 켜면 비streaming은 `choices[0].token_ids`, streaming은 chunk마다 delta `token_ids`와 첫 chunk의 `prompt_token_ids`를 준다(`serving.py:336–412, 563–567`).
2. **기능 확인** `tokid_check.py`(측정 아님)
   - 새 server에서 두 세션 × 3 turn을 streaming으로 보냈다.
   - 재도착 prompt는 이전 prompt id + 수신한 생성 id + 새 id 8개다.
3. **설계 문서** [GPU_MULTITURN_DESIGN.md](GPU_MULTITURN_DESIGN.md) — NPU와 달라진 15개 항목, 측정 정의, 예측기 코드 위치.
4. **GPU 의미론 코드** (`experiments/gpu/multiturn/`)
   - `gpu_cost.py`: GTASK05 비용. 혼합 step 증분은 하한·상한 구간이다.
   - `gpu_mt_sim.py`: vLLM v1 scheduler·block pool. LRU와 반사실 FIFO.
   - `gpu_mt_model.py`: 해석 v1 GPU 인스턴스. B2·B1 LRU·B3·B4는 neutral 코드를 import한다.
   - `gpu_mt_runner.py`: runner. plan·갱신·`WindowRule`은 neutral 코드를 import한다.
   - `gpu_mt_measure.py`: 측정 정의.
5. **NPU runner를 import하지 않은 이유**
   - NPU runner의 요청 구성부(`run_slot`)는 텍스트 prompt와 `build_exact`에 묶여 있다.
   - GPU runner는 plan·갱신·구간 규칙을 같은 neutral 모듈에서 import하고, 요청 구성과 server lifecycle만 새로 썼다. NPU 파일은 고치지 않았다.

## 변경된 파일

- `docs/research/gpu/GPU_MULTITURN_DESIGN.md`, `docs/research/gpu/GTASK07.md` (신규)
- `docs/research/gpu/GPU_INDEX.md`
- `experiments/gpu/multiturn/{gpu_cost.py, gpu_mt_sim.py, gpu_mt_model.py, gpu_mt_runner.py, gpu_mt_measure.py, tokid_check.py}` (신규)

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python \
  experiments/gpu/multiturn/tokid_check.py --out-dir <abs>/results/gpu/multiturn/tokid_check/<UTC>
```

- server 인자: pool 2,048, `max_num_seqs` 8, budget 2,048, 격자 (1,2,4,8,16)
- 관측 patch 없음, 카드 uuid `4485e769…`

Population: 요청 6건(2 세션 × 3 turn), lifecycle 1개.
Source: streaming 응답(chunk `token_ids`, `usage`).
Device scope: GPU 0.

## 결과

| 세션·turn | prompt | 생성 id / `completion_tokens` / 요청 | chunk | `cached_tokens` (기대) |
|---|---|---|---|---|
| 0·0 | 1,000 | 33 / 33 / 33 | 33 | 없음(첫 turn) |
| 0·1 | 1,041 | 150 / 150 / 150 | 150 | **1,024** (1,024) |
| 0·2 | 1,199 | 64 / 64 / 64 | 64 | **1,184** (1,184) |
| 1·0 | 1,137 | 33 / 33 / 33 | 33 | 없음 |
| 1·1 | 1,178 | 150 / 150 / 150 | 150 | **1,168** (1,168) |
| 1·2 | 1,336 | 64 / 64 / 64 | 64 | **1,312** (1,312) |

- 6/6에서 prompt echo가 보낸 id와 같았다.
- 모든 turn에서 `prompt_tokens` = 보낸 id 수였다.
- 기대값은 `floor((이전 prompt + 이전 생성 − 1)/16)·16`이다.
- 예측기 간 대조(설계 점검, 측정 아님; 선정 전용 plan은 GTASK08)는 아래와 같다.
  - 해석 모형과 시뮬레이터의 BASE 재사용은 포화 전(running < 8) N에서 0.02–0.03 안으로 맞는다.
  - 포화 근처에서는 시뮬레이터 쪽이 더 낮다(재사용 붕괴의 되먹임, GTASK08).

## 핵심 발견

1. **`stack`** — **vLLM 0.22.0 completions endpoint는 streaming에서도 생성 token id를 chunk delta로 주고, 그 id를 이어 붙인 재도착 prompt는 생성 token까지 hit한다**(6/6, 식과 정확 일치). multi-turn에서 NPU처럼 텍스트로 이어 붙이지 않아도 된다.
2. **`stack`** — **`continuum.sim`으로는 GPU 기판을 옵션만 바꿔 표현할 수 없다.** 전제가 셋이다.
   - prefill 배타 실행
   - prompt token만 캐시
   - sequence slot 단위 pool

   GPU의 혼합 chunked prefill, 생성 token 캐시, 조회 후 할당, 16-token block은 새 wrapper로만 표현된다. 이것은 GTASK06 FIT_GAPS의 시뮬레이터 쪽 대응물이다.
3. **`stack`** — **neutral `lru_block_survival`은 Poisson 평균 ≈ 745를 넘으면 underflow로 "전부 손실"을 낸다**(`exp(-mean)` = 0).
   - GPU 입력(할당률 × 수십 초 gap)이 이 영역에 들어가, 수정 전 해석 모형은 pool 크기에 무감응이었다(N=12에서 pool 1,900·2,600 모두 0.913).
   - wrapper가 같은 식을 log 공간에서 계산한다(`_self_check`로 비-underflow 영역 일치 확인).
   - `src/` 수정은 NPU 쪽 몫으로 보고한다.

## 해석

- token id 방식은 NPU 조건과 다르다. NPU runner는 텍스트였지만 NPU는 prefill token만 캐시해 응답 부분이 hit와 무관했으므로, 두 기판의 hit 산술은 각자 의도대로 성립한다.
- GPU 예측기 3종은 plan·갱신·구간 규칙을 NPU와 같은 코드로 공유한다. 달라지는 것은 기판 의미론과 비용뿐이다.

## 확인되지 않은 사항

- streaming 관찰자 효과(GPU): 파일럿(GTASK10)에서 확인한다.
- runner의 전체 동작(갱신, 구간, uuid·preemption 검사, 측정 모듈 join): 파일럿에서 확인한다.

## 실패 / 무효 시도

- 해석 모형 첫 판의 pool 무감응(발견 3). 원인 확인 후 wrapper에서 고쳤다. 선정(GTASK08)은 고친 판으로만 계산했다.

## 연구 원칙에 미치는 영향

- neutral 모형 함수의 수치 영역을 기판 입력으로 다시 확인해야 한다. NPU 입력 범위에서 문제가 없던 함수도 GPU 입력에서 깨졌다.

## 다음 작업

GTASK08(구성 blind 선정).

## 재현 정보

- merge `fe8a4df`
- raw: `results/gpu/multiturn/tokid_check/20260929T*/`(`tokid_check.json`, `server.log`, `lifecycle.json`; git 비추적)
- 환경: `vllm 0.22.0` venv, driver 580.178.04, `Qwen/Qwen3-4B@1cfa9a72…`, 카드 uuid `GPU-4485e769-430a-430d-3383-b9c4ce92a175`
- 선등록: 해당 없음(측정·판정 없음)
