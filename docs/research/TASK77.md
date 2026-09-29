# TASK77 — multi-turn runner, 세션 갱신 plan, 시뮬레이터 갱신 옵션, 오프라인 검사

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 04 작업 A. steady-state multi-turn 실험용 runner를 새로 만든다(기존 `session_runner.py`는 고치지 않는다). 같은 plan을 시뮬레이터에도 넣을 수 있게 시뮬레이터에 **세션 갱신 옵션**(기본값 불변)을 추가하고, device 없이 동작을 검사한다.

**측정 0, device 0.**

## 배경

관련 TASK:

- [TASK75](TASK75.md), [TASK76](TASK76.md) — 설계 초안과 확정 결정(K=8, 8 token segment, gap 60 s, 구간 규칙)
- [TASK72](TASK72.md) — runner commit `PARTIAL`, R4 warm-up 규칙
- [TASK73](TASK73.md) — KNOWN_PITFALLS 6(`cached_tokens` 0 채움)
- [TASK18](TASK18.md) — client id ⊂ server id join

## 시작 상태

- HEAD `ea62f85`([TASK76](TASK76.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. **`src/continuum/workload/multiturn.py`** (신규, neutral): `generate_plan`(slot × 세션 목록 전체를 미리 생성, slot i는 `i·stagger_s`에 시작, 첫 세대 세션의 turn 수는 `1..K` 무작위), `MultiTurnPlan`(JSON 직렬화·SHA256), `max_context_tokens`, **`WindowRule`**(warm-up 끝 = `max(3·cycle, 모든 slot이 2 turn 완료한 시각)`, 평가 120 s, 이후 발행 중단) — runner와 분석이 같은 함수를 쓴다. `to_sim_inputs`(plan → 시뮬레이터 입력).
2. **시뮬레이터 갱신 옵션**: `SimConfig.session_start_s`, `SimConfig.successor`(기본 `None` = 기존 동작). successor 세션은 앞 세션의 마지막 turn이 끝나는 순간 첫 turn이 도착한다. 회귀: `make_tables.py --all` 표 29개 byte 동일.
3. **runner** `experiments/npu/stage3/multiturn_runner.py`: slot마다 thread, 세션 갱신, `WindowRule` 온라인 적용과 발행 중단, `--stream`(chunk 도착 시각을 `tokens.<label>.jsonl.gz`로), `prompt_tokens_details`가 없으면 `cached_tokens: null`, `provenance.json`(runner commit·dirty 상태·인자·plan SHA256), `windows.<label>.json`. 절대 경로 강제.
4. **구동** `run_multiturn.sh`(서버를 자기 PID로 종료, patch 상태·`rbln_config.json` SHA·plan SHA를 `lifecycle.txt`에), **plan 생성** `make_plan.py`(TASK76 결정이 기본값, `max_seq_len` 초과 plan 거부), **가짜 server** `fake_server.py`, **오프라인 검사** `runner_offline_check.py`.

## 변경된 파일

- `src/continuum/workload/multiturn.py` (신규), `src/continuum/sim/engine.py` (옵션 2개)
- `experiments/npu/stage3/{multiturn_runner.py, run_multiturn.sh, make_plan.py, fake_server.py, runner_offline_check.py}` (신규)
- `docs/research/TASK77.md` (신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/runner_offline_check.py --work <scratch>/offline
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all   # 시뮬레이터 회귀
```

오프라인 검사 조건: N = 3 slot, K = 3, gap U(0,1) s, 생성 U(32,64), cycle 0.4 s, 평가 4 s. 세 run — A(non-stream, details 있음), B(A와 같은 plan 반복), C(stream, details 없음).

## 결과

| 검사 | A | B | C |
|---|---|---|---|
| runner exit / 멈춘 이유 | 0 / window | 0 / window | 0 / window |
| 요청 수 | 46 | 46 | 46 |
| 세션 갱신 수 / 최대 지연 | 16 / 0.017 s | 16 / 0.017 s | 16 / 0.019 s |
| 최대 in-flight (≤ N=3) | 2 | 2 | 2 |
| warm-up 끝: 온라인 = 오프라인 재계산 | 1.2 = 1.2 | 1.2 = 1.2 | 1.2 = 1.2 |
| 평가 끝 이후 발행 | 0 | 0 | 0 |
| provenance(commit·plan SHA) | OK | OK | OK |

- **재현성**: A·B가 같이 보낸 (session, turn) 46개의 prompt SHA256 **46/46 동일**.
- **관측 불가 값**: C의 모든 행 `cached_tokens: null`, `details_present: false`. A는 전부 `0`·`true`(가짜 server가 details를 줌).
- **streaming**: C의 요청마다 chunk 시각 수 = `completion_tokens`.
- **시뮬레이터 갱신**: 같은 plan에서 successor 21개 전부 앞 세션 종료 시각에 첫 turn 도착(불일치 0), slot 첫 세션은 offset에 도착, 최대 running 3.
- **종합 `PASS`**.

- `requested_condition` 등: 해당 없음(오프라인)

## 핵심 발견

1. **`universal`** — 구간 규칙을 runner와 분석이 **같은 함수**로 적용하면 온라인 결정과 사후 재계산이 비트 단위로 같다(3/3 run). 분석 단계에서 구간을 다시 정의할 여지를 없앤다.

## 해석

- 가짜 server에서는 in-flight가 N에 못 미쳤다(gap이 서비스보다 길다). 실측에서는 서비스가 길어 N에 가까울 것이다 — 파일럿에서 확인한다.

## 확인되지 않은 사항

- 실제 vLLM의 streaming 응답에서 `stream_options.include_usage`의 `usage`에 `prompt_tokens_details`가 실리는지(파일럿에서 확인; 없으면 `null`로 남는다)
- 실제 server에서의 lifecycle 시간

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- KNOWN_PITFALLS 6번의 대응(`null` 기록)이 새 runner에 들어갔다.

## 다음 작업

- 지시문 04 작업 B(blind 격자 선정), C(파일럿), D(예측 선등록).

## 재현 정보

- 위 명령. 오프라인 산출은 scratch(비추적).
- 선등록 commit: 해당 없음(측정 없음)
