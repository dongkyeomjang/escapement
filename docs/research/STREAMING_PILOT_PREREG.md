# streaming 관찰자 효과 파일럿 — 선등록

작성: 2026-09-29, Advisor 지시문 04 작업 C. **이 문서를 commit하기 전에는 파일럿 측정을 한 건도 하지 않았다.**

## 질문

multi-turn 본 실험에서 streaming(chunk마다 응답)으로 요청하면 host 쪽 작업이 늘어 device time이 바뀌는가? 바뀌지 않으면(동치) 본 실험은 streaming으로 해 turn ≥ 1 TTFT와 prefill 간섭 W를 직접 잰다([MULTITURN_DESIGN_DRAFT.md](MULTITURN_DESIGN_DRAFT.md) §5).

## 격자

- N = 8, 구성 BASE(`Qwen3-4B-rbln-b8-s8192-d4-mb`, `(1,2,4,8)`) · TUNED(`...-b16-s8192-d4-mb16`, `(1,4,6,8,10,16)`), 모드 streaming · non-streaming, replicate 3 → **12 lifecycle**.
- plan: `make_plan.py` 규칙(K=8, 첫 prompt U(800,1600), 이후 segment 8, 생성 U(32,256), gap `toolmix` 상한 60 s), **seed `20261300 + r`**(r = 0,1,2; 격자 선정 `20261200`대·본 실험과 겹치지 않음), plan_id `pilot-n8-r{r}`, `cycle_s` = 해석 모형(TUNED) 예측. 같은 replicate의 네 lifecycle(2 구성 × 2 모드)은 **같은 plan 파일**을 쓴다(짝 설계).
- 순서(고정): r0: BASE-ns, BASE-st, TUNED-st, TUNED-ns / r1: TUNED-ns, TUNED-st, BASE-st, BASE-ns / r2: BASE-st, BASE-ns, TUNED-ns, TUNED-st. 모드 순서를 번갈아 시간 추세와 모드 효과를 떼어 놓는다.
- lifecycle마다 서버를 새로 띄운다(`run_multiturn.sh`). 평가 120 s.
- 파일럿 plan 파일과 SHA256은 이 문서와 같은 commit에 들어간다:

| plan | seed | `cycle_s` | 내용 SHA256 (`_sha256`) | 파일 SHA256 | 최대 context |
|---|---|---|---|---|---|
| `plans/pilot-n8-r0.json` | 20261300 | 6.123 | `dc52078a…de249c6` | `3d339e8d…c7a949` | 2,995 |
| `plans/pilot-n8-r1.json` | 20261301 | 5.503 | `1d6dffed…64f3ec` | `54c29060…75384e` | 3,125 |
| `plans/pilot-n8-r2.json` | 20261302 | 5.475 | `feda1ddd…356b16` | `1c1951e0…fbee93f` | 3,179 |

- 계산 스크립트: `experiments/npu/stage3/mt_measure.py`(지표), `pilot_analyze.py`(판정), `run_pilot.sh`(순서). 측정 전 계기 점검: 가짜 server run 출력에 합성 server 로그를 붙여 `mt_measure`가 창·join·`null` 대체·h를 계산함을 확인했다.

## 지표

**turn당 채널 A′ device time** (평가 구간). 정의:

- server 창: 평가 구간(`WindowRule`, runner 기록)에 **보낸** 요청 중 첫 요청의 `[PFX] [ALLOC]` 줄부터 마지막 요청의 `[PFX] [ALLOC]` 줄까지(client id ⊂ server id join, [TASK18](TASK18.md)). 시각 정렬을 쓰지 않는다.
- decode 항 = 그 창 안 `[BUCKET]` step마다 `step_time_s(bucket, actual)`(TASK13 계수, `config_device.channel_a_prime`과 같은 식).
- prefill 항 = 평가 구간 요청마다 `prefill_s(prompt_tokens − cached)`. `cached`는 client `cached_tokens`, 그것이 `null`이면 server `[CACHE-HIT]`의 `IB_COUNT × 128` 또는 `[CACHE-PARTIAL]`의 `REUSED`, 조회 줄이 없으면 0(layer 1 miss). client `prompt_tokens`가 없으면 그 요청은 `UNKNOWN`이고 cell을 `INVALID`로 둔다.
- turn당 = (decode 항 + prefill 항) / 평가 구간 요청 수.

**짝 ratio**: 같은 (구성, replicate)의 `A′/turn(streaming) / A′/turn(non-streaming)` — 6개.

## 판정 기준 (원칙 17)

- 중앙 ratio = 6개 짝 ratio의 **중앙값**. **95 % percentile bootstrap CI**: 6개 짝을 복원 추출(10,000회, seed `20261310`)해 매번 중앙값을 계산.
- **CI 폭 상한 0.04.** 근거: 본 실험이 가르려는 효과의 크기 — 원고의 구성 절감률 X +2.1 % ~ +10.1 %([TASK35](TASK35.md)·[TASK36](TASK36.md)), 격자 의존 비용 이득 E(h) 2.9–3.0 %([TASK72](TASK72.md) R3) — 중 가장 작은 것이 약 2 %다. 관찰자 효과가 그 절반(±1 %)을 넘지 않으면 구성 간 비교에 쓸 수 있고, 추정 불확실성까지 합쳐 CI 전체가 [0.98, 1.02] 안에 들어야 한다고 보면 폭 0.04가 상한이다.
- **`EQUIVALENT` ⇔ CI가 1을 포함하고 폭 ≤ 0.04** → 본 실험 streaming.
- 그 밖(`NOT_EQUIVALENT` — CI가 1을 포함하지 않거나 폭 > 0.04) → 본 실험 non-streaming + streaming 보조 run(설계 초안대로).
- 보고만: 구성별 중앙 ratio, 재사용 수 차(짝별), 평가 구간 step 가중 h(n)의 TVD(짝별), 처리량 비, streaming에서 `prompt_tokens_details` 존재 여부.

## runner 동작 확인 (판정과 별개, 전건 기록)

lifecycle마다: runner exit 0, `stopped_by = window`, 고갈 slot 0, `WindowRule` 온라인 = 사후 재계산, 평가 끝 이후 발행 0, HTTP 오류 0, `provenance.json`의 runner commit = 이 선등록 이후 HEAD, plan SHA256 일치, 세션 갱신 지연 최댓값. 하나라도 어긋나면 그 lifecycle은 `INVALID`로 표시하고 원인을 보고한다(재실행은 하지 않는다 — 판정은 남은 짝으로 하되 그 사실을 적는다).

## 사전 예측

streaming은 요청당 chunk 수(평균 약 144)만큼 HTTP write가 늘지만, 서버의 step 실행(device)은 같은 scheduler가 정한다. **`EQUIVALENT`로 예측**, 중앙 ratio 0.995–1.005. 확신 중간 — host 부하가 scheduler 주기를 늦추면 h(n)이 바뀔 수 있다.

## 파일럿 데이터 사용 제한

파일럿 측정값으로 모형·시뮬레이터 파라미터를 조정하지 않는다. streaming 결정과 runner 동작 확인에만 쓴다. 본 실험 예측 선등록의 입력에 쓰지 않는다.

## 실행 절차

`experiments/npu/stage3/run_pilot.sh`가 위 순서로 `run_multiturn.sh`를 부른다. 실행 전 `rbln-stat`으로 device가 비어 있음을, `apply.sh status`가 `patched`(`70942d16…`)임을 확인한다. 실행 중 script를 편집하지 않는다.

## 개정 이력

- 2026-09-29 초판 (측정 전).
