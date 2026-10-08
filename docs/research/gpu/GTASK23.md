# GTASK23 — 실행 구간 직접 계측(DIRECT_EXEC)과 계측 영향 점검 (G-10 작업 A)

## 상태

DONE

## 날짜

2026-10-08

## 목적

GPU 지시문 G-10 §3. 원고의 비용 채널(가격 `gpu_cost`)과 독립인 시간 채널을 만든다. GPU device event로 step 실행 구간을 재고, 그 계측이 실행을 바꾸지 않는지 저부하·포화 × GPU_BASE·GPU_KV에서 ON/OFF로 확인한다. 이 점검은 개발용이며 원고의 새 확증 결과가 아니다.

## 배경

- 원고 호출당 비용(A′-GPU)은 관측 window step마다 `gpu_cost.step_ms(d, p, b)`를 더한 값이다. 이 가격은 [GTASK05](GTASK05.md) 통제 부하의 host dispatch 간격이라 model 실행, sampler, CPU 후처리, launch overhead, 다음 step 준비를 모두 섞은 step 주기다.
- [GTASK15](GTASK15.md): 운영 dispatch 주기는 가격의 1.22배이고, 그 초과의 대부분은 FULL decode에서 나온다. [GTASK18](GTASK18.md): 초과의 81–96 %는 context 길이 비용(c = 0.212 µs/token)이다.
- 지시문 요구: 혼합 step은 한 번만 센다. 비동기 launch를 감싼 CPU timer는 쓰지 않는다. ON/OFF 중앙 변화가 1 %를 넘으면 계측을 줄여 한 번 다시 점검하고, 그래도 넘으면 B의 DIRECT 판정은 `BLOCKED`다.
- 선등록 [G10_A_PREREG.md](G10_A_PREREG.md)

## 시작 상태

- HEAD `228ce77`(G-10 C 사전 단계 microbenchmark 결과), branch `gpu-a6000`
- site-packages: 관측 patch 적용 상태(`model_runner.py` SHA256 `dc6221e9…`)

## 수행 내용

1. exec-timing layer `escapement_exec.patch`를 작성했다(관측 patch 위에 덧대는 층, `model_runner.py`만 변경, env `ESCAPEMENT_EXEC=1`일 때만 동작). guard `apply_exec.sh`(hash `dc6221e9…` ↔ `60bcc2a5…`)와 `apply.sh status`의 `exec_layer` 표시를 추가했다. runner에 `--exec-timing`을 넣었다(층이 없으면 시작 거부).
2. **사용자 승인 후** 층을 site-packages에 적용했다. 적용 후 hash `60bcc2a5…`를 확인했다.
3. smoke run 2회(개발 seed, `results/gpu/g10/smoke/`)에서 겹침 허용치와 범위 검사 기준을 정했다. 판정에는 쓰지 않았다.
4. 판정 기준·부하·순서·분석 script를 측정 전에 commit했다(`c4cf5d2`).
5. 점검 40 lifecycle(2 부하 × 2 구성 × 5 pair × ON/OFF)을 돌렸다(12:27:39–13:46:06 UTC). 40/40 유효, 재실행 0이었다.
6. 입력 동결 목록 `INPUT_MANIFEST.json`(head `0812f85`, dirty 0)을 만들었다.

## 변경된 파일

- 선등록 commit `c4cf5d2`: `docs/research/gpu/G10_A_PREREG.md`, `experiments/gpu/patches/vllm-0.22.0/{escapement_exec.patch, apply_exec.sh, apply.sh}`, `experiments/gpu/multiturn/gpu_mt_runner.py`(`--exec-timing`), `experiments/gpu/g10/{exec_measure.py, exec_check_run.py, make_exec_check_order.py, exec_check_order.json, run_exec_check.sh, exec_check_analyze.py}`
- 결과 commit `fc10373`: `experiments/gpu/g10/exec_check_result/summary.json`, `experiments/gpu/g10/INPUT_MANIFEST.json`
- 기록 commit: `docs/research/gpu/GTASK23.md`, `docs/research/gpu/GPU_INDEX.md`, `docs/research/gpu/GPU_RESULTS_SUMMARY.md`

## 실험 또는 검증 방법

- 계측 위치(v2 runner, async scheduling 켜짐, 모두 `torch.cuda.current_stream()`):
  - e0: `execute_model`의 `[GSTEP]` 직후
  - e1: forward 직전
  - e2: `sample_tokens` 끝(반환 직전)
- 매 step 시작에서 `query()`로 끝난 이전 step만 읽어 `[GEXEC] seq t s prep run`을 남긴다. 동기화 없음. `t`는 `[GSTEP]`과 join key다.
- **DIRECT_EXEC(step) = prep + run = e0→e2 device 구간.** step 안 stream idle을 포함하고, step 사이 device idle과 출력 D2H(copy stream)는 제외한다. hardware busy time이 아니다. HW_ACTIVE는 `NA`(profiler 신호 없음).
- 부하: closed-loop 통제 부하(prompt U(1000, 3000), 생성 128, streaming). low = client 2, sat = client 16. warm-up 15 s, window 60 s. seed 20264900 + pair.
- 지표: 처리율(window 생성 token / 60 s), FULL decode-only 연속 step dispatch 간격 중앙값(폭 w* = low 2, sat 8). 조건마다 pair별 `ON/OFF − 1`의 중앙값.
- 독립 대조(ON run): window `[GEXEC]` 누락, 연속 step device 구간 겹침(허용 0.01 ms), prep ≥ 0·run > 0, DIRECT 합 ≤ device 시각 범위, OFF run의 `[GEXEC]` 0줄.

```bash
R=<abs>/results/gpu/g10/exec_check/20261008T1227Z
setsid nohup experiments/gpu/g10/run_exec_check.sh $R > $R/outer.log 2>&1 &
```

## 결과

### 계측 영향 (pair 5개의 ON/OFF − 1)

| 조건 | 처리율 중앙 (범위) | w* 간격 중앙 (범위) | 판정 |
|---|---|---|---|
| low / GPU_BASE | −0.06 % (−0.31 – 0) | +0.07 % (0 – +0.08) | OK |
| low / GPU_KV | 0.00 % (−0.03 – +0.03) | +0.02 % (−0.06 – +0.09) | OK |
| sat / GPU_BASE | −0.01 % (−0.41 – +0.08) | −0.02 % (−0.14 – +0.02) | OK |
| sat / GPU_KV | +0.12 % (−0.19 – +0.25) | −0.01 % (−0.21 – +0.15) | OK |

**overall `OK`**: 모든 조건에서 |중앙 변화| ≤ 0.12 %로 문턱 1 % 안이다. 경량화 재점검은 하지 않았다. 다만 점 추정이 1 % 안이라는 뜻이며, 영향이 없음을 증명한 것은 아니다.

### 독립 대조 (ON run 20개)

| 항목 | 값 |
|---|---|
| window `[GEXEC]` 누락 | 0 |
| 겹침 > 0.01 ms | 0 |
| 비양수 prep·run | 0 |
| DIRECT 합 / device 시각 범위 | 최대 0.99978 |
| DIRECT 합 / host `[GSTEP]` 범위 (보고) | 0.9960–1.0052 |
| OFF run의 `[GEXEC]` 줄 | 0 |
| FULL decode DIRECT 중앙 / 같은 run dispatch 간격 중앙 | low 14.19–14.29 ms, 비 0.998–1.001; sat 16.94–17.04 ms, 비 0.998–1.001 |

### 사전 예측 대조

- 영향 |중앙| < 0.3 %: 적중.
- **FULL decode DIRECT/가격 0.85–0.98: 빗나감.** DIRECT는 dispatch 주기와 같았다(비 0.998–1.001). async scheduling에서 host가 다음 step을 device 실행 중에 준비하므로, device 구간이 step 주기를 정한다. 이 부하의 가격 대비 초과(low 약 14.2 대 13.3 ms, sat 약 16.9 대 13.6 ms)는 context 길이 비용 쪽이다(GTASK18).

## 핵심 발견

1. CUDA event 층은 저부하·포화, 두 pool 모두에서 처리율과 decode 주기를 0.12 % 넘게 바꾸지 않았다. B의 DIRECT 직접 검증은 `BLOCKED`가 아니다.
2. 포화 FULL decode에서 DIRECT_EXEC은 host dispatch 주기와 같다. 따라서 이 장비의 운영 step 주기는 device 실행이 정한다.
3. 1분 길이 점검 run에서는 겹침이 0이었다. 2분이 넘는 B·C lifecycle에서는 float32 시각 분해능 때문에 이 검사가 실패했다([GTASK24](GTASK24.md)). 이 점검은 짧은 run이라 그 문제를 드러내지 못했다.

## 해석

- DIRECT는 원고 가격과 범위가 다른 시간 채널이다. 가격은 짧은 context 통제 부하의 dispatch 주기이고 context 항이 없다. DIRECT는 실제 context에서의 device 구간이다. 둘의 절대값을 같다고 쓰지 않고, 비(GPU_KV / GPU_BASE)만 비교한다.

## 확인되지 않은 사항

- HW_ACTIVE(실제 SM busy)는 재지 않았다(`NA`).
- mixed step 안의 prefill·decode 몫은 분리하지 않았다(분리 신호 없음).
- 출력 D2H 복사(copy stream)는 DIRECT 범위 밖이다.

## 실패 / 무효 시도

- 점검 run INVALID 0.
- smoke run에서 겹침이 95–132건 나왔다. 원인은 `%.4f` 출력과 event timer 분해능(약 0.5 µs) 때문에 생긴 1–6 µs 차이였다. 이를 보고 허용치 0.01 ms와 device 범위 기준을 정했고, 둘 다 선등록 문서에 사실로 기록했다. 이 허용치가 긴 run의 float32 간격(0.0156 ms)보다 작다는 점은 그때 확인하지 못했다(GTASK24 실패 원인).

## 연구 원칙에 미치는 영향

- 관측 불가 field(HW_ACTIVE)를 0으로 채우지 않고 `NA`로 두었다.
- site-packages 변경은 hash guard patch로만 했다. 층은 **지금도 적용된 상태**이며 `apply_exec.sh revert`로 관측 patch 상태(`dc6221e9…`)로 되돌릴 수 있다. 층은 `ESCAPEMENT_EXEC=1`일 때만 동작한다.

## 다음 작업

- [GTASK24](GTASK24.md)(B)와 [GTASK25](GTASK25.md)(C)가 이 계측을 쓴다.

## 재현 정보

- **선등록 commit `c4cf5d211ffdac3a45e01b8b62ebe4d84da667a4`(2026-10-08 12:27:39 UTC) → 측정 시작 12:27:39 UTC.** 같은 초이지만 driver의 `start_commit.txt` = `c4cf5d2`이므로 commit이 먼저다. 측정 종료·분석 13:46:06.
- 측정 중 HEAD가 `8bfeee8`·`c2f37d3`·`0812f85`(B·C 선등록, 연결 driver)로 바뀌었다. A가 쓰는 script(`run_exec_check.sh`, `exec_check_run.py`, `exec_check_analyze.py`, `exec_measure.py`)는 그 commit들에서 바뀌지 않았다.
- 순서 `exec_check_order.json`(seed 20264901). run dir(비추적): `results/gpu/g10/exec_check/20261008T1227Z/`
- 입력 동결: `experiments/gpu/g10/INPUT_MANIFEST.json`(head `0812f85`, 각 입력의 경로·마지막 commit·SHA256)
- patch: `escapement_exec.patch` SHA256 `e2892b8e…`, 적용 후 `model_runner.py` `60bcc2a5…`
- 환경: venv `/home/csdc/kyeom/envs/vllm-0.22.0`, `vllm 0.22.0`, `Qwen/Qwen3-4B@1cfa9a72…`, A6000 `GPU-4485e769-430a-430d-3383-b9c4ce92a175`, 관측 patch + exec 층, KV events
