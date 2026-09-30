# TASK83 — 정상성 재분석(같은 길이 기준)과 지시문 06 결정 기록

## 상태

DONE

## 날짜

2026-09-30

## 목적

Advisor 지시문 06 작업 A와 §2·§9. (1) [TASK82](TASK82.md)의 정상성 비교가 창 길이가 다른 두 TVD를 비교했으므로, **같은 길이(60 s) replicate 간 기준**으로 다시 본다(분석만, 판정 없음). (2) TASK82 결정 요청 1–6에 대한 Advisor 결정과 원고 수정 후보 갱신(M2, 정상성, 재사용 영 예측기의 약함)을 INDEX에 기록한다.

**측정 0, device 0, 코드 변경은 분석 스크립트 1개.**

## 배경

관련 TASK:

- [TASK82](TASK82.md) — 본 측정·판정, 정상성 보고(전·후반 h TVD 0.25–0.48 대 replicate 간 120 s TVD 0.10–0.24)
- [TASK81](TASK81.md) — 개정 2(영 예측기)

## 시작 상태

- HEAD `074aedc`([TASK82](TASK82.md), `origin/main`과 같음), `git status --short`: `?? .idea/`만

## 수행 내용

1. 방법(비교 분포, 요약 통계, "비정상" 분류 조건)을 [STATIONARITY_REANALYSIS.md](STATIONARITY_REANALYSIS.md) §1–§4에 쓰고 스크립트 `stationarity.py`와 함께 **계산 전에 commit**했다(`c7b444b`, 22:25:41).
2. 같은 명령에서 곧바로 계산했다(22:25:41). 결과를 문서 §5에 덧붙였다.
3. INDEX에 [결정 8](INDEX.md#결정-8--지시문-06-결정-task82-결정-요청-16)(지시문 06 §2 결정 1–6)과 원고 수정 후보 M2 갱신·M4(정상성)·M5(재사용 영 예측기의 약함)를 기록했다.

## 변경된 파일

- 선등록 `c7b444b`: `docs/research/STATIONARITY_REANALYSIS.md`(§1–§4), `experiments/npu/stage3/stationarity.py`
- 이 commit: `docs/research/STATIONARITY_REANALYSIS.md`(§5), `docs/research/TASK83.md`, `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/stage3/stationarity.py \
  --run results/npu/stage3/20260930-main --output results/npu/stage3/20260930-main/stationarity.json
```

Population: [TASK82](TASK82.md)의 75 lifecycle 중 13 cell의 전부(N8 TUNED·DP 10, 나머지 5). Unit: TVD(무차원), 재사용률(비율). Source: server `[BUCKET]`·`[PFX]` 로그, client `requests.*.jsonl`.

## 결과

- **h: `WEAK_EVIDENCE`** — 13 cell q_h 중앙값 0.638(비정상 조건 > 0.75 불성립), q_h > 0.5 cell 10/13(단측 부호 p = 0.046, 성립).
- **재사용 후반 하락: `NOT_NONSTATIONARY`** — q_Δ 중앙값 0.45, q_Δ < 0.5 cell 9/13(p = 0.133). 크기 q_\|Δ\| 중앙값 0.49.
- 같은 길이 기준 B(run 사이 같은 위치 60 s 창 TVD)의 cell별 중앙값 **0.17–0.45**, run 안 W 0.25–0.48. TASK82가 쓴 120 s 기준은 0.10–0.24였다.
- N ≤ 8 7 cell q_h 0.64–0.72, N ≥ 10 6 cell 0.33–0.61.
- cell별 표는 [STATIONARITY_REANALYSIS.md](STATIONARITY_REANALYSIS.md) §5.

- `requested_condition` / `observed_condition` / `condition_reached`: 해당 없음(기존 데이터 재분석)

## 핵심 발견

1. **`universal`** — **창 길이가 다른 두 TVD를 비교하면 짧은 창의 표본 잡음이 비정상성처럼 보인다.** 같은 60 s 창끼리 비교하자 [TASK82](TASK82.md)의 "비정상" 신호의 대부분이 사라졌다(run 사이 60 s TVD 중앙 0.17–0.45 ≈ run 안 0.25–0.48). 분포 차이 지표는 같은 표본 크기의 기준과 비교해야 한다.
2. **`stack`** — 남는 신호는 약하다(`WEAK_EVIDENCE`): 저부하(N ≤ 8)에서 run 안 두 창이 run 사이보다 약간 더 다르고, 고부하(N ≥ 10)에서는 그렇지 않다. 재사용률의 후반 하락은 run 사이 변동과 구별되지 않는다.

## 해석

- 120 s 합산 구간을 비교 단위로 쓴 [TASK82](TASK82.md) 판정은 이 결과로 영향을 받지 않는다. 논문에는 "60 s 해상도의 점유 분포는 run 사이 변동 수준으로 요동하며, 저부하에서 약한 run 내 이동이 있다" 정도로 보고한다.
- 저부하의 약한 이동은 세션 수가 적어 renewal 위상이 오래 남는 것과 맞는 방향이다(hypothesis). 원인 분리 분석은 문서 §5에 제안만 했다.

## 확인되지 않은 사항

- 저부하 약한 이동의 원인(warm-up 위상 대 gap 꼬리) — 제안만 함
- replicate 간 기준에 섞인 plan 차이의 몫(같은 plan 반복이 없어 분리 불가)

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- 분포 차이(TVD 등)를 비교할 때 **같은 창 길이·표본 크기의 기준 분포**를 쓴다는 점을 TASK82의 정정으로 남긴다(TASK82 원문은 고치지 않는다).

## 다음 작업

- 지시문 06 작업 B(descriptor v2, [TASK84](TASK84.md) 예정).

## 재현 정보

- 위 명령. 산출 `results/npu/stage3/20260930-main/stationarity.json`(비추적).
- **방법 선등록 commit `c7b444b2e43c46139e8bf6a039fd7b91134b0673` (2026-09-30 22:25:41 +0900) → 같은 명령에서 계산 시작 22:25:41**(commit이 먼저 끝난 뒤 실행).
