# GTASK05 — GPU step 비용 측정 (FULL · PIECEWISE · eager)

## 상태

IN_PROGRESS

## 날짜

2026-09-29

## 목적

GPU 지시문 G-02 작업 D. 설계 선등록 [GPU_STEPCOST_PREREG.md](GPU_STEPCOST_PREREG.md) 뒤 측정한다.

(측정 전 skeleton.)

첫 run `20260929T1021Z`는 G3 r0 도중 host 다운으로 중단됐다. 문제 PCIe 슬롯을 비활성화해 측정 카드가 바뀌었으므로 [개정 1](GPU_STEPCOST_PREREG.md#개정-1--장비-교체-후-재측정-2026-09-29-재측정-시작-전-commit)을 측정 전에 commit하고 6 lifecycle 전체를 다시 측정한다.
