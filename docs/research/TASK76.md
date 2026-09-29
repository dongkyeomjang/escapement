# TASK76 — multi-turn 설계 결정 확정과 두 서버 작업 규약(결정 7)

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 04 §2를 기록한다. [MULTITURN_DESIGN_DRAFT.md](MULTITURN_DESIGN_DRAFT.md)의 결정 D1–D7 확정, `AGENTS.md`의 KNOWN_PITFALLS 항목 수 문구 수정, **결정 7(NPU·GPU 두 서버 작업 규약)** 신설, 후속 연구 6번(GPU)에 context 길이 재검토 메모.

**측정 0, 코드 변경 0.**

## 배경

관련 TASK:

- [TASK75](TASK75.md) — 설계 초안과 결정 D1–D7
- [TASK73](TASK73.md) — KNOWN_PITFALLS 6번 추가(그때 `AGENTS.md` 문구는 고치지 않고 보고)
- [TASK70](TASK70.md) — 결정 4 2차 개정(GPU 두 번째 기판)

## 시작 상태

- HEAD `03493db`([TASK75](TASK75.md)), `git status --short`: `?? .idea/`만

## 수행 내용

1. 설계 초안 §8에 확정 결정을 적었다: D1 (a) 8 token(tool 출력 크기 segment는 제외, GPU 단계에서 재검토), D2 K = 8, D3 파일럿 후, D4 포함하되 **모형 예측 h로 blind 선정**, D5 N = 12 포함(탐색·경계 cell), D6 60 s, D7 5회.
2. `AGENTS.md`: "함정 5종" → "재발·무효화 함정 5종과 잠재 함정 1종, 모두 6종". 규칙 내용은 바꾸지 않았다.
3. INDEX **결정 7**: GPU 에이전트는 `gpu-a6000` branch만, GPU 파일 영역(`docs/research/gpu/`, `experiments/gpu/`, `results/gpu/`)은 NPU 에이전트가 만들거나 고치지 않음, `src/continuum/`은 NPU 에이전트만 수정, rebase 금지, 통합 시점은 Advisor.
4. INDEX 후속 연구 6번에 "GPU 단계에서 segment 크기 재검토" 메모.

## 변경된 파일

- `AGENTS.md`, `docs/research/INDEX.md`, `docs/research/MULTITURN_DESIGN_DRAFT.md`, `docs/research/TASK76.md`(신규)

## 실험 또는 검증 방법

없음(문서).

## 결과

위 수행 내용과 같다. `requested_condition` 등: 해당 없음.

## 핵심 발견

없음.

## 해석

- 결정 7로 이 저장소는 두 에이전트가 쓰는 공유 저장소가 된다. NPU 쪽 작업은 GPU 파일 영역을 건드리지 않고, `src/continuum/` 변경은 GPU 쪽 결과에 영향을 줄 수 있으므로 앞으로도 기본값 불변·회귀 검사 원칙을 지킨다.

## 확인되지 않은 사항

- `gpu-a6000` branch의 현재 상태(이 서버에서 확인하지 않았다)

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- 결정 7이 작업 영역 규칙을 추가한다.

## 다음 작업

- 지시문 04 작업 A–D(runner, blind 격자·compile, streaming 파일럿, 예측 선등록).

## 재현 정보

- 선등록 commit: 해당 없음
