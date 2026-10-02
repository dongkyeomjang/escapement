# GTASK21 — GPU 작업 마무리 기록 (G-08)

## 상태

DONE

## 날짜

2026-10-02

## 목적

GPU 지시문 G-08. 기록과 정리만 한다(**측정 0, 예측 0, 판정 변경 0**).
- GPU 실험 종료와 G-07 결정 요청에 대한 Advisor 결정 3건을 기록한다.
- GTASK01–20의 결과 요약표를 만든다.
- `gpu-a6000` → `main` merge 준비 상태를 확인한다(merge는 하지 않음).

## 배경

- [GTASK17](GTASK17.md)–[GTASK20](GTASK20.md)(G-07), Advisor 승인(G-08 §1)
- NPU 결과 색인 `paper/RESULTS_INDEX.md`(origin/main `58e67a6`)에 GPU 행 44개가 이미 있었다(GTASK04·11–16)

## 시작 상태

- HEAD `517cff8`(= `origin/gpu-a6000`), working tree 깨끗함

## 수행 내용

1. `git fetch`. `origin/main` `58e67a6`(TASK97–99가 merge-base `f6ffd8f` 뒤 3 commit)을 확인했다.
2. [GPU_RESULTS_SUMMARY.md](GPU_RESULTS_SUMMARY.md)를 작성했다.
   - 열·kind·layer 규칙은 NPU 색인과 같다.
   - NPU 색인에 이미 있는 GPU 행 44개는 값을 그대로 옮겼다. g11_collapse_curve 비고만 GTASK19 정정을 반영했다.
   - 나머지 GTASK(01–03, 05–10, 17–20)는 각 문서의 결과·핵심 발견에서 86행을 더했다. 층 태그는 원 문서의 태그만 쓰고, 태그가 없으면 `untagged`로 두었다.
   - source commit은 각 GTASK 파일의 마지막 commit이다(기존 행은 NPU 색인의 commit 유지).
3. GPU_INDEX에 다음을 기록했다: 실험 종료, G-08 결정 3건, 통합 확인용 입력(파일과 SHA256), 판정 종류별 목록.
4. merge 준비를 확인했다(`git diff`, `git merge-tree`; 작업 트리와 branch는 바꾸지 않음).

## 변경된 파일

- `docs/research/gpu/GPU_RESULTS_SUMMARY.md`(신규), `docs/research/gpu/GTASK21.md`(신규), `docs/research/gpu/GPU_INDEX.md`

## 결과

### 1. 결과 요약표

| kind | 행 |
|---|---|
| exploratory | 51 |
| blind_confirm | 32 |
| code_check | 19 |
| retro_check | 12 |
| blind_fail | 10 |
| dev_set | 5 |
| withheld | 1 |
| **합계** | **130** |

GTASK별 행 수: 01 9 · 02 8 · 03 7 · 04 4 · 05 9 · 06 3 · 07 4 · 08 6 · 09 5 · 10 6 · 11 18 · 12 8 · 13 5 · 14 2 · 15 4 · 16 3 · 17 5 · 18 9 · 19 1 · 20 14. id 중복 0.

### 2. merge 준비 (`gpu-a6000` `517cff8` 대 `origin/main` `58e67a6`)

| 항목 | 결과 |
|---|---|
| merge-base | `f6ffd8f`(G-07 작업 A의 merge `5f69657`가 반영한 main) |
| GPU 쪽 변경(merge-base..`gpu-a6000`) | 141 파일. `docs/research/gpu/` 34, `experiments/gpu/` 107. **GPU 영역 밖 변경 0** |
| main 쪽 변경(merge-base..`origin/main`) | 36 파일(TASK97–99: `docs/research/{INDEX, TASK97–99, CTXCOST_DESIGN}.md`, `experiments/npu/stage3/*`, `paper/RESULTS_INDEX.md`, `src/continuum/sim/engine.py`, `.gitignore` 등). **GPU 영역 변경 0** |
| 겹치는 파일 | 없음 |
| 충돌 | `git merge-tree`(git 2.34, 3-인자 형식) "changed in both" 0, 충돌 표지 0 |
| `results/gpu/` | git 비추적(`.gitignore`), merge 대상 아님 |

- 실제 merge는 하지 않았다(G-08 §3.3). 이번 commit(GTASK21)이 더해져도 GPU 영역 안 파일 3개뿐이라 결론은 같다.

## 핵심 발견

- 없음(기록·정리 작업)

## 해석

- `gpu-a6000`은 처음부터 GPU 영역 안에서만 바뀌었으므로, `main`으로 합칠 때 NPU 파일과 공유 코드에 영향이 없다.

## 확인되지 않은 사항

- NPU 통합 단계에서 GPU 예측(GTASK20)이 통합 시뮬레이터로 재현되는지(NPU 에이전트 소관)

## 실패 / 무효 시도

- `git merge-tree --write-tree`는 이 git(2.34.1)에 없어 rc 129로 실패했다. 3-인자 형식으로 대신했다.

## 연구 원칙에 미치는 영향

- 없음

## 다음 작업

- 없음(GPU 실험 종료). merge는 Advisor 지시 시에 한다.

## 재현 정보

```bash
git fetch origin
git diff --name-only origin/main...gpu-a6000 | grep -v -E '^(docs/research/gpu/|experiments/gpu/|results/gpu/)'
git diff --name-only gpu-a6000...origin/main | grep -E '^(docs/research/gpu/|experiments/gpu/|results/gpu/)'
git merge-tree $(git merge-base gpu-a6000 origin/main) gpu-a6000 origin/main | grep -c 'changed in both'
```
