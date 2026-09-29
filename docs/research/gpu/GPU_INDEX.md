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

GPU 기판 착수 단계(Stage 0). [GTASK01](GTASK01.md)에서 환경 inventory, `vllm 0.22.0`(CUDA 13.0 빌드, NPU upstream과 같은 버전) 설치, `Qwen/Qwen3-4B@1cfa9a72…`(NPU와 같은 revision·byte 수) download, source 감사 9항목을 마쳤다. Stage 0 선등록은 [GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md), 실행·판정은 [GTASK02](GTASK02.md)다.

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
| [GTASK02](GTASK02.md) | IN_PROGRESS | GPU Stage 0 기능 확인과 descriptor 초안 | 선등록 [GPU_STAGE0_PREREG.md](GPU_STAGE0_PREREG.md) 후 L1·L2·L3 serving lifecycle 실행 |

## 다음 작업

GTASK02 완료 후에는 Advisor 지시 없이 다음 GPU 작업을 시작하지 않는다.
