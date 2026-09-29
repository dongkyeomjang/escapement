# TASK75 — multi-turn steady-state 실험 설계 초안

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 03 작업 D. 모형 v1과 시뮬레이터의 blind 예측을 선등록하고 측정할 steady-state multi-turn 실험의 **설계 초안**을 쓴다. 예측·판정 기준은 쓰지 않는다(Advisor 검토 후 선등록). 산출물: [MULTITURN_DESIGN_DRAFT.md](MULTITURN_DESIGN_DRAFT.md).

**측정 0, device 0, compile 0, runner 작성 0.**

## 배경

관련 TASK:

- [TASK72](TASK72.md) — R4 ramp·drain 제안, R5 동시 시작 workload의 renewal 가정 위반
- [TASK73](TASK73.md) — 모형 v1(blind 검증 대상), KNOWN_PITFALLS 6
- [TASK74](TASK74.md) — 시뮬레이터 계통 오차의 다음 후보(일정)
- [TASK31](TASK31.md), [TASK48](TASK48.md) — TraceLab `toolmix`와 그 자료 한계
- [TASK35](TASK35.md) — 채널 A′·B, 세 구성과 artifact
- [TASK19](TASK19.md) — 짝 설계는 한 plan에서 파생

## 시작 상태

- HEAD `15b41d2`([TASK74](TASK74.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. context 길이 상한을 네 설계(A 원고 분포, B tool 출력 크기 segment, C 초기 prompt 축소, D 짧은 세션)로 계산했다.
2. TraceLab `toolmix` 분포를 상한 60 s·상한 없음으로 표본 추출(200,000개, seed 1)해 상한 효과를 쟀다.
3. 기존 run의 lifecycle 시간(final-confirm, null-channel)에서 고정 오버헤드를 추정하고 예산을 계산했다.
4. `models/`의 기존 artifact로 가능한 구성과 새 compile이 필요한 구성을 구분했다.

## 변경된 파일

- `docs/research/MULTITURN_DESIGN_DRAFT.md` (신규), `docs/research/TASK75.md` (신규), `docs/research/INDEX.md`
- `docs/research/TASK74.md` (핵심 발견 2의 괄호 수치 문구 정정 — 값 변경 없음)

## 실험 또는 검증 방법

계산만. `continuum.workload.tools.load_mix(summary.json, cap_s=60 / 1e9)` 표본, `results/npu/stage2/*/measurement-{start,end}.txt`.

## 결과

- **context**: 원고 분포(이후 segment 8 token)에서는 최악 24 turn까지 8,192 안에 든다 — 상한이 느슨하다. tool 출력 크기 segment U(64,512)를 넣으면 최악 8 turn이다. **권고 설계 A, K = 8**(최대 context 3,712, 평균 ≈ 2,416).
- **gap**: 상한 60 s에서 평균 4.23 s, 중앙값 0.16 s, 1 s 미만 70.5 %, 상한 도달 2.5 %. 상한 없으면 평균 6.99 s, 최대 961 s. **권고 60 s 유지.**
- **격자**: N 6·8·10(+12), 구성 BASE·BATCHONLY·TUNED는 기존 artifact로 가능, N별 DP 격자는 새 compile 2회. replicate 5, run ≈ 170 s(warm-up 25 + 평가 120 + drain).
- **예산**: lifecycle 고정 오버헤드 ≈ 80–90 s(기존 106–113 s/회에서 run 시간 차감). 82 lifecycle ≈ 6.2 h, 재시도 여유 포함 ≈ 9 h — **10월 말까지 충분**.
- **지표**: streaming이면 turn ≥ 1 TTFT와 prefill 간섭 W(원고 식 (6))를 직접 잴 수 있으나 관찰자 효과가 있을 수 있어 짝 파일럿(원칙 17 동치)을 먼저 제안.
- 채널 B(in-flight 합집합)는 steady state에서 평가 구간 전체에 가까워져 변별력이 떨어진다 — turn당 정규화 병기를 제안.

- `requested_condition` / `observed_condition` / `condition_reached`: 해당 없음(설계)

## 핵심 발견

1. **`stack`** — **원고 workload의 이후 turn segment(8 token)에서는 `max_seq_len` 8,192가 turn 수를 거의 제약하지 않는다(최악 24 turn).** 제약은 tool 출력을 context에 넣는 설계에서 생긴다. 상한 값은 이 compile 구성의 것이다.
2. **`universal`** — **TraceLab에는 tool 출력 token 수가 없어, 출력 크기를 넣는 설계는 근거 없는 분포를 도입한다.** 자료의 한계이며 기판과 무관하다.
3. **`universal`** — **steady state에서는 채널 B(in-flight 합집합)가 wall time에 수렴해 구성 간 변별력을 잃는다.** 정의에서 나오는 성질이다.

## 해석

- 측정 예산은 병목이 아니다. 병목은 선등록·검토 절차와 새 runner의 검증(계기 점검)이다.

## 확인되지 않은 사항

- streaming의 관찰자 효과 크기(파일럿 전 `UNKNOWN`)
- multi-turn에서 layer 1(inner LRU)이 구속하는지 — 설계 A에서는 가능성이 낮다고 보나 확인 안 됨
- 새 compile 2회의 실제 시간·크기

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

없음(설계 초안).

## 다음 작업

- Advisor 검토와 결정 D1–D7 → 선등록(예측·판정 기준) → runner 작성·계기 점검 → 측정. **지시 없이 착수하지 않는다.**

## 재현 정보

- gap 표본: `PYTHONPATH=src python3 -c "from continuum.workload.tools import load_mix; ..."` (seed 1, 200,000개)
- 선등록 commit: 해당 없음(측정 없음)
