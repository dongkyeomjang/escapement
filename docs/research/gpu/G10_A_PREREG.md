# G-10 작업 A — 실행 구간 직접 계측(DIRECT_EXEC)과 계측 영향 점검 선등록

작성: 2026-10-08. GPU 지시문 G-10 §3. 기록 TASK는 [GTASK23](GTASK23.md)다. **이 문서, patch, script를 점검 측정 전에 commit한다.** 이 점검은 개발용이며 논문의 새 확증 결과가 아니다.

## 1. 현행 비용 함수가 포함하는 범위 (코드 확인)

- 원고의 호출당 비용(A′-GPU)은 `gpu_mt_measure.lifecycle_metrics`가 관측 window step마다 `gpu_cost.step_ms(decodes=d, prefill_tokens=p, bound)`를 더한 값이다. `gpu_cost`의 값은 GTASK05 통제 부하에서 **연속한 `[GSTEP]` 사이의 host dispatch 간격**(lag 0/1)으로 잰 것이다. 따라서 이 가격은 model 실행, sampler, CPU 후처리(postprocess·출력 준비), launch/runtime overhead, scheduler의 다음 step 준비를 **모두 섞은 step 주기**다(device 시간만이 아니다).
- 두 비용 설정 lo / hi는 prefill이 든 step의 증분만 다르다(PIECEWISE 0 / 1.5 ms, eager는 lag 1 clamp / 3-step 창). decode-only step은 같다.
- 채널 매핑:

| 채널 | 활동량 | 시간 값 |
|---|---|---|
| PRED_lo / PRED_hi | 동결 시뮬레이터(GTASK20 `ctx`)의 사건 | `gpu_cost` lo / hi 가격(원고 정의) |
| RECON_lo / RECON_hi | 관측 window step의 (d, p) | `gpu_cost` lo / hi 가격 (기존 A′-GPU 그대로) |
| DIRECT_EXEC | 같은 관측 window step | 아래 §2의 CUDA event 구간 |
| HW_ACTIVE | — | **NA**: 이 실행에서는 device profiler(CUPTI/nsys) 신호를 쓰지 않는다 |

- RECON은 lo/hi 두 개다(공통 RECON 하나가 아니다). 두 설정 모두 동결하고 결과를 보고 고르지 않는다.

## 2. 계측 수단 — exec-timing layer (`ESCAPEMENT_EXEC=1`)

- 파일: `experiments/gpu/patches/vllm-0.22.0/escapement_exec.patch`(관측 patch 위에 덧대는 층, `model_runner.py`만 변경), guard `apply_exec.sh`(관측 patch 적용 상태 `dc6221e9…` ↔ 층 적용 상태 `60bcc2a5…`). `apply.sh status`는 층이 있으면 `exec_layer: present`를 함께 출력하고 `state: patched`를 유지한다.
- 위치(v2 runner, async scheduling 켜짐):
  - e0: `execute_model`의 `[GSTEP]` 직후(입력 준비 전), 현재 stream에 record
  - e1: forward 직전(FULL graph replay 또는 PIECEWISE/eager 호출 직전)
  - e2: `sample_tokens` 끝(sampling, postprocess, KV connector hook 뒤, 반환 직전)
  - 모든 event는 `torch.cuda.current_stream()`(= main stream)에 기록된다. FULL graph replay도 이 stream에서 돈다. 출력 D2H 복사(copy stream)는 범위 밖이다.
- **동기화 없음**: 매 step 시작에서 e2가 이미 끝난(`query()`) 이전 step만 읽어 `[GEXEC] seq t s prep run`을 한 줄 남긴다. 강제 `synchronize`를 넣지 않는다. `t`는 `[GSTEP]`의 `t`와 같은 값·형식이며 join key다. `s`는 process 첫 event 기준 device 시각(ms).
- **DIRECT_EXEC(step) = prep + run = e0→e2 device 구간.** step 안의 모든 kernel과 그 사이 host launch를 기다리는 stream idle을 포함하고, 한 step의 e2와 다음 step의 e0 사이(host가 다음 step을 준비하는 동안의 device idle)는 포함하지 않는다. stream 순서상 연속 step 구간은 겹치지 않는다(검사). prefill과 decode가 함께 든 혼합 step은 **한 번만** 센다. 비동기 launch를 감싼 CPU timer가 아니다.
- 이 구간은 "실제 hardware busy time"이 아니다(stream idle 포함, 다른 stream 제외). 원고 비용(dispatch 주기)과 범위가 다르다는 점을 결과에 함께 표시한다.
- step 분류: 순수 decode(p = 0), 순수 prefill(d = 0), mixed. **mixed step 안의 prefill/decode 몫은 분리하지 않는다**(분리 신호 없음). 비용 모형으로 나눈 값을 독립 prefill 계측이라 부르지 않는다.
- 최소 로그 연결: `[GSTEP]`(step_id = `t`, step 종류, executing requests, scheduled tokens, padded, graph mode) ↔ `[GEXEC]`(시간) ↔ `[GPFX]`(request id, lookup·alloc) ↔ KV events. `request_ids`·`context_total`·`prefill_tokens`는 `[GPFX]`와 GTASK12 재생(membership)으로 복원한다(새 로그 field 없음).

## 3. 계측 영향 점검 (개발 부하, 검증 seed와 분리)

- 부하: `experiments/gpu/g10/exec_check_run.py`. multi-turn plan이 아닌 closed-loop 통제 부하. client마다 고정 순서의 요청(무작위 id prompt U(1000, 3000), 생성 128, ignore_eos, streaming, 공유 prefix 없음). seed 20264900 + pair 기반(같은 pair의 ON/OFF는 같은 prompt). 저부하 `low` = client 2, 포화 `sat` = client 16(> `max_num_seqs` 8).
- 구성: GPU_BASE(1,900 block), GPU_KV(2,300 block), 격자 (1,2,4,8,16), `max_num_seqs` 8, budget 2,048, 관측 patch 로그·KV events 둘 다 켬. ON/OFF는 `ESCAPEMENT_EXEC`만 다르다.
- 행렬: 2 부하 × 2 구성 × **5 pair** × ON/OFF = 40 lifecycle. warm-up 15 s, window 60 s(wall), 이후 새 요청 없음. 순서: `exec_check_order.json`(seed 20264901) — 20 pair를 무작위로 섞고 pair 안 ON/OFF 순서도 무작위.
- 비교 지표(두 arm에서 똑같이 얻는 값):
  1. 처리율: window 안에 도착한 생성 token 수 / 60 s (client streaming 시각)
  2. 공통 범위 실행시간: window 안에서 연속한 FULL decode-only step의 dispatch 간격 중앙값, 대표 폭 w* (low: 2, sat: 8)
- **판정**: 조건(부하 × 구성)마다 pair별 상대 변화 `ON/OFF − 1`의 중앙값. 어느 조건에서든 처리율 또는 w* 간격의 |중앙 변화| > 1 %이거나, 동기화로 실행이 구조적으로 바뀌면(예: ON에서 step 주기 분포가 계단식으로 이동) → 계측을 경량화(e1 event 제거, `[GEXEC]`를 prep 없이)하고 같은 행렬을 새 pair seed로 한 번 재점검한다. 그래도 해소되지 않으면 **작업 B의 직접 검증은 `BLOCKED`**, 작업 C는 RECON을 참조로 계속한다.
- 반복별 값과 변동(범위)을 함께 보고한다. 1 % 이하 점 추정만으로 "영향 없음을 증명했다"고 쓰지 않는다.
- 독립 대조(ON run): (a) window step 중 `[GEXEC]` 누락 수·비율, (b) 연속 step의 device 구간 겹침 0(허용 0.01 ms: s·prep·run을 각각 `%.4f`로 출력하고 event timer 분해능이 약 0.5 µs라 stream 순서상 연속인 step도 1–6 µs 겹쳐 보인다 — smoke run에서 확인), (c) prep ≥ 0, run > 0, (d) window의 DIRECT 합 ≤ 같은 step들의 device 시각 범위(첫 e0 – 마지막 e2; 단위·중복 집계 확인. host `[GSTEP]` 시각 범위와의 비는 보고만), (e) FULL decode DIRECT 중앙값과 가격(13.3–13.6 ms) 대조(단위), (f) OFF run에 `[GEXEC]` 0줄.
- 사실 기록: 선등록 전 코드 경로 시험으로 smoke run 2회(pair 99, 개발 seed, `results/gpu/g10/smoke/`)를 돌렸다. 포화 ON run에서 window 누락 0, 겹침 > 0.01 ms 0, DIRECT 합 / device 범위 0.978, FULL decode(폭 8) DIRECT 16.94 ms 대 dispatch 16.96 ms였다. 판정에 쓰지 않는다.
- 점검 run의 INVALID: lifecycle 검사 실패(외부 GPU process, 생성 길이 불일치, preemption), 또는 ON run의 window 누락 > 0. INVALID pair는 순서를 다 돈 뒤 한 번 다시 잰다.

## 4. 이후 사용 규칙 (B·C 선등록에 넘김)

- 주 판정의 DIRECT_EXEC은 window의 필수 step이 모두 `[GEXEC]`에 귀속된 lifecycle만 쓴다. 누락을 비용 모형·chunk 간격 추정으로 채워 DIRECT_EXEC이라 부르지 않는다. 원본과 누락 수를 보존한다.
- 누락·겹침이 있는 lifecycle은 계측 결함으로 그 lifecycle의 DIRECT만 INVALID이며, 순서를 다 돈 뒤 같은 plan으로 한 번 다시 잰다(`.retry1`).

## 5. 사전 예측 (기록용)

- 층의 비용은 step당 event 3개 record와 `query()` 1–2회, log 한 줄이다(수 µs, step 13–20 ms의 0.1 % 미만). 처리율·w* 간격 변화는 |중앙| < 0.3 % 쪽이다.
- FULL decode DIRECT는 가격(dispatch 주기)보다 작다(sampler 뒤 host 처리와 다음 step 준비가 빠지므로). 비(DIRECT/가격) 0.85–0.98 예상.
