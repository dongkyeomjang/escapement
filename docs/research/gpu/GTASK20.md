# GTASK20 — 붕괴 영역 blind (N = 25·28), 세 비용 입력

## 상태

IN_PROGRESS

## 날짜

2026-10-02

## 목적

GPU 지시문 G-07 작업 C. 붕괴 영역의 새 seed·새 N(25·28)에서 sim LRU의 세 비용 입력을 blind로 판정한다. 세 입력은 (1) GTASK18 context 길이 비용(주), (2) GTASK13 ×1.210·mode_dist(보정), (3) 가격(기준선)이다.

## 수행 내용

1. 작업 B 결과 commit(`809a767`, `b75c2b1`) 뒤 plan 10개, POOL+GRID 격자(규칙 6), 네 예측기 예측을 계산했다(`predict_blind.py` 1회).
2. 설계·예측·판정 기준 [GPU_BLIND_COLLAPSE_PREREG.md](GPU_BLIND_COLLAPSE_PREREG.md), 순서표, 판정 script를 측정 전에 commit했다.
3. (진행 중) `run_blind.sh`를 세션과 분리해 실행한다. 30 lifecycle 측정 → 무효 재실행 → 판정 → `blind_result/verdict.json` 자동 local commit 순서다.

## 재개 방법

- run dir: `results/gpu/multiturn/blind/<시작 UTC>/`, 진행은 `sequence.log`, commit 결과는 `commit.log`, 판정 요약은 `judge.stdout`
- 자동 commit 대상: `experiments/gpu/multiturn/blind_result/verdict.json`
- 결과가 나오면 이 문서와 GPU_INDEX를 갱신·commit한다.
