# TASK79 — streaming 관찰자 효과 파일럿 (EQUIVALENT → 본 실험 streaming)

## 상태

DONE

## 날짜

2026-09-29

## 판정

**`EQUIVALENT`** (선등록 [STREAMING_PILOT_PREREG.md](STREAMING_PILOT_PREREG.md), commit `0a944069`, 2026-09-29 18:26:26 +0900 → 측정 시작 18:26:31, 종료 19:12:07).

| 항목 | 값 |
|---|---|
| 짝 ratio 6개 (streaming / non-streaming, turn당 채널 A′) | BASE r0 1.0063, r1 1.0135, r2 0.9998 / TUNED r0 0.9979, r1 1.0231, r2 1.0056 |
| **중앙 ratio** | **1.0060** |
| 95 % bootstrap CI (10,000회, seed 20261310) | **[0.9989, 1.0183]** — 1 포함 |
| CI 폭 / 상한 | **0.0194 / 0.04** |
| 구성별 중앙 ratio | BASE 1.0063, TUNED 1.0056 |

**결정: 본 multi-turn 실험은 streaming으로 한다**(선등록 규칙). 사전 예측(`EQUIVALENT`, 중앙 0.995–1.005)은 판정은 적중, 중앙값은 예측 범위보다 0.001 높았다.

## 목적

Advisor 지시문 04 작업 C. streaming이 device time을 바꾸는지(관찰자 효과) 짝 파일럿으로 확인하고 본 실험의 streaming 여부를 정한다. 같은 run으로 새 runner([TASK77](TASK77.md))의 실측 동작을 확인한다.

## 배경

관련 TASK:

- [TASK75](TASK75.md)·[TASK76](TASK76.md) — 설계와 결정 D3(파일럿 후 결정)
- [TASK77](TASK77.md) — runner와 오프라인 검사
- [TASK73](TASK73.md) — KNOWN_PITFALLS 6

## 시작 상태

- 선등록 commit `0a94406`. 측정 중 HEAD가 `c714b03`([TASK78](TASK78.md) 격자 선정 기록)으로 바뀌었다. runner·구동·측정·판정 스크립트와 `src/`는 두 commit 사이에 **변경 없음**(`git diff 0a94406 c714b03 -- …` 빈 출력). 그래서 lifecycle의 `runner_commit`이 둘로 갈린다(r0 BASE 두 개는 `0a94406`, 나머지 `c714b03`).
- patch `patched`(`70942d16…`) 전후 동일, device `rbln0`–`rbln3` 사용 전 비어 있음(`rbln-stat`).
- 측정 중 같은 host에서 CPU 단일 thread 계산 2개(격자 선정, 본 실험 plan·예측 계산)가 돌았다(96 core). 두 모드는 번갈아 측정했으므로 모드 간 차이에 대한 영향은 대칭이라고 본다.

## 수행 내용

1. 선등록 순서대로 12 lifecycle(`run_pilot.sh`)을 실행했다. 재실행 0.
2. `pilot_analyze.py`로 판정하고, lifecycle 검사를 전건 기록했다.
3. 부수 발견: `prompt_tokens_details` 누락 조건을 vLLM source와 교차 확인했다(아래).

## 변경된 파일

- `docs/research/TASK79.md` (신규), `docs/research/KNOWN_PITFALLS.md` (6번 보강), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
bash experiments/npu/stage3/run_pilot.sh /home/rebel/continuum-npu/results/npu/stage3/20260929-pilot-streaming
env -u PYTHONPATH python3 experiments/npu/stage3/pilot_analyze.py \
  --run results/npu/stage3/20260929-pilot-streaming \
  --output results/npu/stage3/20260929-pilot-streaming/pilot_verdict.json
```

## 결과

- `requested_condition`: N=8, BASE·TUNED × streaming·non-streaming × r0–r2, 평가 120 s
- `observed_condition`: 12/12 lifecycle runner exit 0, `stopped_by = window`, 평가 구간 요청 144–211개
- `condition_reached`: `YES`

### runner 동작 (12/12 전부)

| 검사 | 결과 |
|---|---|
| 고갈 slot | 0 |
| 구간: 온라인 = 사후 재계산 | 12/12 일치 |
| 평가 끝 이후 발행 | 0 |
| HTTP 오류 | 0 |
| plan SHA256 | 3 plan 모두 선등록 값과 일치 |
| 세션 갱신 | lifecycle당 26–28회, 최대 지연 8–18 ms |
| warm-up 끝 | r0 18.37 s(= 3c), r1 19.2–19.4 s, **r2 46–47 s**(한 slot이 2 turn을 마치는 데 오래 걸림 — gap 상한 60 s 꼬리) |
| lifecycle 시간 | 서버 기동 ≈ 65 s + run 140–170 s + 종료 → **3.5–4.2 분** |

### 보고 항목 (판정 외)

| 짝 | 재사용 stream / non-stream | h(n) TVD | 처리량 비 |
|---|---|---|---|
| BASE r0 | 118/143 / 119/143 | 0.019 | 1.000 |
| BASE r1 | 131/174 / 132/173 | 0.036 | 1.006 |
| BASE r2 | 93/125 / 97/126 | 0.055 | 0.993 |
| TUNED r0 | 128/145 / 127/144 | 0.060 | 1.006 |
| TUNED r1 | 170/187 / 170/185 | 0.056 | 1.010 |
| TUNED r2 | 114/129 / 112/127 | 0.043 | 1.013 |

- streaming에서도 `usage`(`stream_options.include_usage`)가 오고, `prompt_tokens_details`가 있는 행의 client 값 = server 값.
- **`prompt_tokens_details` 누락**: 플래그가 켜져 있어도 행의 25–37 %에 field가 없었다. 없는 행은 **전부** server 조회도 재사용 0(첫 turn 34/34 + 이후 turn), 있는 행은 전부 client = server. vLLM source(`completion/serving.py:446`·`:586`: `if self.enable_prompt_tokens_details and num_cached_tokens:`)가 **캐시 0이면 field를 생략**한다. KNOWN_PITFALLS 6번에 보강했다.

## 핵심 발견

1. **`stack`** — **streaming의 관찰자 효과는 turn당 device time에서 동치 밴드 안이다**(중앙 1.0060, CI [0.9989, 1.0183]). 값은 이 host·stack의 것이다.
2. **`stack`** — **vLLM은 캐시 token이 0이면 `prompt_tokens_details`를 생략한다**(source-read + 12 lifecycle 교차). 플래그가 켜진 run에서 field 부재는 "재사용 0"이다.
3. **`universal`** — 새 runner의 구간 규칙은 실측에서도 온라인 결정과 사후 재계산이 일치했다(12/12).

## 해석

- 짝 ratio의 산포(0.998–1.023)는 같은 plan·같은 구성의 반복에서 생기는 run 간 변동이다. 본 실험의 구성 간 예측 차가 N=6·8에서 1–3 %, DP 대 TUNED가 0.2–0.8 %이므로, replicate 5회로 앞의 것은 가를 수 있어도 뒤의 것은 가르기 어려울 것이다(본 실험 선등록 §5.4 예측 `INCONCLUSIVE`의 근거).
- **이 파일럿 측정값은 모형·시뮬레이터 파라미터와 본 실험 예측에 쓰지 않았다.** 본 실험 예측(`predict_main.py`)은 파일럿이 도는 동안(18:45경 시작) 파일럿 산출을 읽지 않고 계산됐다. 파일럿 도중 한 번 첫 lifecycle의 측정 모듈 동작(유효성·`cached` 출처 수)을 확인했을 뿐 A′ 값은 보지 않았다.

## 확인되지 않은 사항

- streaming 모드에서 prefill 간섭 W를 chunk 시각에서 재는 정의의 타당성(본 실험 선등록에서 탐색으로 둔다)

## 실패 / 무효 시도

없음. 무효 lifecycle 0, 재실행 0.

## 연구 원칙에 미치는 영향

- KNOWN_PITFALLS 6번 보강(누락 조건의 source 근거).
- 측정 중 HEAD 변경이 provenance를 둘로 가를 수 있다 — 본 실험 중에는 commit하지 않는 것이 안전하다(보고).

## 다음 작업

- 본 실험 예측 선등록(작업 D)은 이 판정(streaming)을 반영해 commit한다.

## 재현 정보

- run: `results/npu/stage3/20260929-pilot-streaming/`(비추적): `server-*.log`, `probe/<tag>/{requests,tokens,windows,provenance,lifecycle}`, `pilot_verdict.json`
- **선등록 commit `0a94406937f260300092ce8297fad35cbd213fa7` (18:26:26 +0900) → 측정 시작 18:26:31 → 종료 19:12:07.**
