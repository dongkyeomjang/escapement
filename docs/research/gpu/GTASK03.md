# GTASK03 — GPU 관측 수단 확보: observation-only patch와 KV events collector, 관문 G1–G3

## 상태

IN_PROGRESS

## 날짜

2026-09-29

## 목적

GPU 지시문 G-02 작업 A·B. `origin/main` merge, v2 runner observation-only patch와 KV events collector 작성, 선등록 [GPU_OBS_GATE_PREREG.md](GPU_OBS_GATE_PREREG.md)에 따른 관문 판정.

(진행 중. 첫 관문 실행에서 원 기준 G1 `FAIL`(warmup step 미예상, collector endpoint 오류), G2·G3 `PASS` — [GPU_OBS_GATE_PREREG.md](GPU_OBS_GATE_PREREG.md) 개정 1 후 재실행한다.)
