# `vllm-rbln 0.11.1` — dummy block lifecycle observation patch

[patches/README.md](../README.md)의 7개 항목을 이 문서가 채운다. 기존 [README.md](README.md)의 `[BUCKET]` patch([TASK12](../../docs/research/TASK12.md))와 **다른 파일**을 대상으로 하는 **두 번째** patch다. 승인 근거는 Advisor 지시문(탐색 실험 "dummy block의 생애 주기 관측", 사용자 전달, 2026-09-11)이며 선등록은 [DUMMY_LIFECYCLE_PLAN.md](../../docs/research/DUMMY_LIFECYCLE_PLAN.md)다.

**이 patch를 적용한 상태로 논문용 측정을 하지 않는다.** 논문 측정은 종결됐고, 이 patch는 탐색 관측이 끝나면 `revert`해 [TASK12](../../docs/research/TASK12.md) patch만 적용된 상태로 되돌린다(환경 분리).

## 1. 대상 package와 exact version

- Package: `vllm-rbln`, version **`0.11.1`** (`apply_dummy_lifecycle.sh`가 매 호출마다 확인, 다르면 중단)
- 실행 경로: optimum 경로(`VLLM_RBLN_USE_VLLM_MODEL=False`, 기본), prefix caching 켠 상태

## 2. Upstream file path와 SHA256

| 항목 | 값 |
|---|---|
| 경로 | `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py` |
| 적용 전 SHA256 | `81850a8be0ef16362db015dcc98dde71e3c902fbd48174a7e4c2a389505d296b` |
| 적용 후 SHA256 | `a51f93abab815107dd762da5f9d43cd3314eb12e163c95a0b32779c11ee60856` |
| patch 파일 | `dummy_lifecycle_observe.patch` |
| patch 파일 SHA256 | `645dc1a8067c2a20ad74e979be5bd44c7b43fc39f893c744df45e9831655b751` |
| Diff 규모 | **추가 42줄, 기존 줄 수정 0, 삭제 0** (7 hunk) |

추가 위치와 남기는 줄:

| 위치 | 추가 줄 | 기록 값 |
|---|---|---|
| module import | `import time` | — |
| `_allocate_new_blocks` 끝(기존 `[PFX] [ALLOC]` 뒤) | `[OBS] [ALLOC]` | 시각, 요청 id, OB 목록, 할당 후 free 수 |
| `_evict_block`(기존 `[PFX] [EVICTION]` 뒤) | `[OBS] [EVICT]` | 시각, OB, 회수 후 free 수 |
| `free_request`(기존 `[PFX] [FREE-REQUEST]` 뒤) | `[OBS] [FREE]` | 시각, 요청 id, preemption 여부, OB 목록, free 수 |
| `can_allocate` 진입(free 수 계산 직후) | `[OBS] [CAN-ALLOCATE]` | 시각, 인자 2개, 필요 OB 수, free 수 |
| `get_dummy_block` 비-full 분기 | `[OBS] [DUMMY-FIXED]` | 시각, 고정 dummy OB(이 구성에서는 타지 않는 분기) |
| `get_dummy_block` full 분기 진입 | `[OBS] [DUMMY-BEGIN]` | 시각, free 수, free list 머리 OB(없으면 −1) |
| `get_dummy_block` 반환 직전 | `[OBS] [DUMMY-END]` | 시각, 반환 OB, free 수 |

**할당 세대는 patch가 아니라 분석이 붙인다** — OB별 `[OBS] [ALLOC]` 등장 순서로 세대를 센다([TASK58](../../docs/research/TASK58.md)과 같은 방식). 세대를 patch 안에서 세려면 상태 변수를 추가해야 하므로 피했다.

**호출 경로 구분자**: `can_allocate`의 호출자는 소스 전체에서 둘뿐이다 — `get_dummy_block`(`optimum_prefix_cache_manager.py:520`)과 요청 admission(`optimum_kv_cache_manager.py:285`). dummy 경로를 `DUMMY-BEGIN`/`DUMMY-END`로 감싸고 `can_allocate` 진입을 표시하므로, 각 `[OBS] [EVICT]`는 (i) dummy 괄호 안이면 dummy 경로, (ii) 괄호 밖에서 직전 표지가 `CAN-ALLOCATE`면 요청 admission 경로, (iii) 직전 표지가 `PREEMPTION=True`인 `FREE`면 선점 경로로 **직접** 분류된다. 파일 하나만 고쳐 모든 회수에 호출 경로를 붙일 수 있어 두 번째 파일(scheduler, KV cache manager)은 건드리지 않았다.

## 3. Scheduler / batch selection / KV allocation semantics를 바꾸지 않는 근거

- **추가된 코드는 `logger.debug(...)` 호출 7개와 `import time` 1줄뿐**이다. 분기·반복·예외 경로·대입을 추가하지 않는다
- 인자로 읽는 값은 이미 계산된 지역 변수(`request_id`, `block_ids`, `block_id`, `preemption`, `outer_blocks`, `num_new_blocks`, `num_computed_tokens`, `required_num_ob`, `free_count`, `dummy_block`)와 **부작용 없는 조회**(`get_free_count()` = `len(deque)`, `_free_blocks[0].block_id` 읽기)뿐이다. `_free_blocks[0]` 읽기는 `get_free_count() > 0`일 때만 평가된다(조건식), 빈 deque에서 `IndexError`가 날 경로가 없다
- `time.time()`은 상태를 바꾸지 않는다
- 기존 `[PFX]` 줄과 로그 순서를 바꾸지 않는다 — 새 줄은 기존 줄 **뒤**(또는 반환·분기 직전)에 들어간다
- `can_allocate`의 새 줄은 `if free_count >= required_num_ob` **앞**에 있어 반환 경로 둘 다에서 한 번씩 남는다. 반환값은 바뀌지 않는다
- **DEBUG 수준이므로 `VLLM_LOGGING_LEVEL=DEBUG` 없이는 아무것도 출력하지 않는다**

## 4. Observation-only 변경을 우선했다는 검토 결과

[TASK58](../../docs/research/TASK58.md)이 기존 로그만으로 확인할 수 있는 한계를 적었다: `[PFX] [EVICTION]` 줄에 **호출자 표시가 없어** dummy 경로의 회수는 소거법으로만 귀속됐고, `get_dummy_block`은 아무 줄도 남기지 않는다. `/metrics`와 `VLLM_RBLN_METRICS`에는 dummy에 해당하는 항목이 없다. 값을 새로 만들지 않고 **이미 계산된 값을 읽어 내보내는** 변경만 선택했다.

## 5. 적용 명령과 복구 명령

```bash
bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh status          # root 불필요
sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh apply
sudo bash patches/vllm_rbln-0.11.1/apply_dummy_lifecycle.sh revert
```

site-packages가 root 소유이고 이 host의 sudo는 비밀번호를 요구하므로 **적용·복구는 사용자가 별도 터미널에서 실행한다**([TASK12](../../docs/research/TASK12.md)와 같은 절차). 적용 전 사본에서 apply → revert 왕복을 검증했다(`81850a8b…` → `a51f93ab…` → `81850a8b…`).

## 6. Version / hash drift 시 fail-loud 중단 방법

`apply.sh`와 같다: version ≠ 0.11.1, 대상 부재, SHA가 pristine·patched 어느 쪽도 아님, 이미 목표 상태, 적용/복구 후 SHA 불일치, 적용 후 문법 검사 실패 — 각각 파일을 건드리기 전(또는 직후 검증에서) 비-0으로 중단한다.

## 7. Patch 적용 여부를 run metadata에 남기는 방법

`run_dummy_lifecycle.sh`가 각 단계 전후로 **두 patch의 status를 모두** 남긴다 — `patch-bucket-<phase>-{before,after}.txt`(TASK12 patch), `patch-dummy-<phase>-{before,after}.txt`(이 patch). 둘 다 `patched`가 아니면 시작하지 않는다.

**다른 측정 script는 이 patch의 상태를 검사하지 않는다**(`apply.sh status`만 본다). 그래서 탐색이 끝나면 반드시 `revert`하고 `status`가 `pristine`인 것을 TASK에 기록한다.
