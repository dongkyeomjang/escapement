# `vllm-rbln 0.11.1` — step 실행 시간 관측 patch (steptime)

[patches/README.md](../README.md)의 7개 항목을 이 문서가 채운다. 목적은 Advisor 지시문(2026-10-08) 작업 A의 `DIRECT_EXEC` 채널 — 비용 함수와 독립인, 완료 시각 기반의 step 실행 시간 — 이다. 승인과 판정 근거는 이 patch를 도입한 TASK에 기록한다.

## 1. 대상 package와 exact version

- Package: `vllm-rbln` **`0.11.1`** (`apply_steptime.sh`가 매 호출 확인)
- 실행 경로: optimum 경로(`VLLM_RBLN_USE_VLLM_MODEL=False`, 기본) — `RBLNOptimumModelRunner`

## 2. Upstream file path와 SHA256

| 항목 | 값 |
|---|---|
| 경로 | `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/worker/optimum_model_runner.py` |
| 적용 전 SHA256 | `365ba136eb79d0ffb226e65670118ed825156b39ebcff96d6bada4989f3e0dc6` |
| 적용 후 SHA256 | `bd93cc04528461d1e0fcb9f48d002422f57593bf7b717ee87c8d54147e009f73` |
| 대상 함수 | module 수준 flag 1개, `execute_model`, `sample_tokens` |
| Diff 규모 | 추가만(기존 줄 수정 0, 삭제 0) |

## 3. Scheduler / batch selection / KV allocation semantics를 바꾸지 않는 근거

- **기본 꺼짐**: `CONTINUUM_OBS_STEPTIME=1`일 때만 기록한다. 꺼져 있으면 추가된 문장은 상수 거짓 분기, `0.0` 대입, `dict.pop` 1회뿐이다.
- 켜져 있을 때 추가되는 일: `time.perf_counter()` 4회, tuple 1개 보관, step 끝에 `logger.debug` 1줄. **분기·반복·예외 경로·동기화 호출을 추가하지 않는다.** 이미 계산된 값(`model_start_time`, `sampler_start_time`, `scheduler_output.num_scheduled_tokens`, `cached_length`, `model_input.is_prompt`)을 읽기만 한다.
- **완료 의미**: `rebel` runtime은 `PyRblnSyncRuntime.run()`(동기)으로 실행되고 출력 tensor가 host로 돌아온 뒤 반환한다(`rebel/sync_runtime.py`). 따라서 `t_model1`은 model forward(128 token chunk 반복 포함)의 완료 시각이고, 새 동기화를 넣지 않는다.
- scheduler(`optimum_scheduler.py`), KV cache manager, bucket 선택(`select_bucket_size`), sampler는 대상이 아니다.

### 기록 필드 (`[STEPTIME]`, 한 step 1줄, host `perf_counter` 초)

| field | 의미 |
|---|---|
| `prefill` | 1 = prefill step(`model_input.is_prompt`), 0 = decode |
| `t_exec` | `execute_model` 진입 |
| `t_model0` / `t_model1` | 기존 `model_start_time`(입력 구성·prefix KV 복사·forward 직전) / forward 반환 직후 |
| `t_samp0` / `t_samp1` | 기존 `sampler_start_time` / sampler 반환 직후 |
| `t_end` | `sample_tokens` 반환 직전(bookkeeping·출력 구성 뒤) |
| `n_reqs`, `n_tokens` | 이번 step의 요청 수, `total_num_scheduled_tokens` |
| `cached` | `scheduler_output.cached_length`(prefill의 재사용 token, 요청별 list) |
| `req_ids` | 요청 id(쉼표), 직전 step과 같으면 `=` |

decode step의 `[BUCKET]` 줄(TASK12 patch)은 같은 step의 `self.model(...)` 안에서 먼저 찍히므로 `[STEPTIME]`과 순서로 1:1 대응한다.

## 4. Observation-only 변경을 우선했다는 검토 결과

- `VLLM_RBLN_METRICS=1`(기존 run 전부 켜짐)은 호출별 `perf_counter` 구간을 재지만 **run 끝 평균만** 남긴다(`v1/worker/metrics.py` `show_stats`). `VLLM_RBLN_METRICS_FILE`·`_DIR`도 요약만 쓴다.
- `rebel.capture_reports()`의 device 시간은 `RBLN_RUNTIME_TIMER=1`일 때만 생성되며(`rebel/base_runtime.py` docstring) 기존 run에는 없었다. 이 patch는 그 환경변수를 켜지 않는다 — 장치 활동 시간(`HW_ACTIVE`)은 이 patch의 범위 밖이다.
- torch profiler(`record_function_or_nullcontext`)는 켜면 overhead가 크고 요청 id 연결이 없다.
- 따라서 이미 계산되는 시각을 읽어 1줄로 내보내는 변경을 택했다.

## 5. 적용 명령과 복구 명령

```bash
bash patches/vllm_rbln-0.11.1/apply_steptime.sh status
sudo bash patches/vllm_rbln-0.11.1/apply_steptime.sh apply
sudo bash patches/vllm_rbln-0.11.1/apply_steptime.sh revert
```

## 6. Version / hash drift 시 fail-loud 중단 방법

`apply.sh`와 같은 구조: version 불일치, 대상 부재, pristine·patched 어느 쪽도 아닌 hash, 이미 적용/복구됨, 적용 후 hash 불일치, 문법 검사 실패에서 파일을 건드리기 전에(또는 직후 검사에서) 비-0 종료.

## 7. Patch 적용 여부를 run metadata에 남기는 방법

`bash patches/vllm_rbln-0.11.1/apply_steptime.sh status > <RUN>/patch-steptime.txt`와, lifecycle별 `CONTINUUM_OBS_STEPTIME` 값을 `lifecycle.txt`에 기록한다.
