# GTASK12 — 사건 재생 검사: GPU 정확 의미론의 요청 단위 hit 재현

## 상태

IN_PROGRESS

## 날짜

2026-10-01

## 목적

GPU 지시문 G-05 작업 A. GTASK11의 관측 사건 순서 위에서 GPU 정확 의미론을 재생해 turn ≥ 1 요청마다 hit token 수를 예측하고, 관측 `cached_tokens`와 대조한다. 붕괴 과소 예측(GTASK11 발견 4)이 의미론 오류인지 동역학 오류인지 가른다.

## 배경

- [GTASK11](GTASK11.md): 본 측정 55 lifecycle, sim LRU가 N24·N26 BASE 붕괴를 과소 예측
- NPU [TASK72](../TASK72.md) R5′: 같은 방법(사건 재생, 일치율 ≥ 0.95, 결정 불가 ≤ 5 %)

## 시작 상태

- HEAD `22b50f4`, `git merge origin/main` → **merge `309871a`**(`origin/main` `235bad2`, TASK83–87, 충돌 없음)

## 수행 내용

1. 선등록 [GPU_REPLAY_PREREG.md](GPU_REPLAY_PREREG.md)를 계산 전에 commit했다.
2. (진행 중) 재생 script 작성, 백그라운드 실행, 판정

## 재현 정보

- 선등록 commit: 이 문서와 같은 commit(`git log -- docs/research/gpu/GPU_REPLAY_PREREG.md`)
