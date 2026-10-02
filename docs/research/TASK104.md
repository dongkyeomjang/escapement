# TASK104 — GPU branch 통합 (`gpu-a6000` → `main`, merge commit)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 12 작업 B. GPU 실험 종료(GTASK21)에 따라 `gpu-a6000`(`614a4c4`)을 `main`에 merge commit으로 통합한다. rebase·squash 없이 양쪽 선등록 commit hash를 보존한다.

**측정 0.**

## 배경

- [결정 7](INDEX.md#결정-7--두-서버-작업-규약-npugpu-에이전트) — 두 서버 작업 규약(GPU 에이전트는 `gpu-a6000`에서 GPU 영역만)
- GTASK21 — GPU 작업 마무리, GPU 영역 밖 변경 없음·main과 충돌 0 확인
- [TASK103](TASK103.md) — 작업 A 완료 후 통합(지시 순서)

## 시작 상태

- HEAD `a953e03`(TASK103), `origin/gpu-a6000` = `614a4c4`

## 수행 내용

1. `git merge --no-ff origin/gpu-a6000` → merge commit **`af3dfe3`**(충돌 0). 들어온 commit 41개(GTASK01–21, GPU 쪽이 이전에 main을 merge한 commit 포함).
2. 확인: (i) `git diff --name-only a953e03 af3dfe3` 143 파일 **전부 `docs/research/gpu/`·`experiments/gpu/` 아래**(GPU 영역 밖 0). (ii) `614a4c4`, GPU 선등록 commit(예: GTASK20 `f0d8000`), NPU 선등록 commit(예: TASK101 `cb1eec4`)이 모두 HEAD의 조상(hash 보존). (iii) merge 후 회귀: `descriptor_v2_regression.sh` 72 파일 차이 0(변경 전 기준 대비), `tests/test_descriptor_v2.py` PASS.
3. 결정 7 종료 기록. GTASK 번호와 `docs/research/gpu/GPU_INDEX.md`는 그대로 둔다.

## 변경된 파일

- merge commit `af3dfe3`(GPU 영역 143 파일)
- `docs/research/TASK104.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
git merge --no-ff origin/gpu-a6000
git diff --name-only a953e03 HEAD | grep -v '^docs/research/gpu/\|^experiments/gpu/\|^results/gpu/'   # 비어 있어야 함
git merge-base --is-ancestor 614a4c4 HEAD && git merge-base --is-ancestor f0d8000 HEAD && git merge-base --is-ancestor cb1eec4 HEAD
bash experiments/npu/analysis/descriptor_v2_regression.sh <scratch>/reg_C
env -u PYTHONPATH python3 experiments/npu/analysis/descriptor_v2_compare.py <scratch>/reg_base <scratch>/reg_C
env -u PYTHONPATH python3 tests/test_descriptor_v2.py
```

## 결과

| 확인 | 결과 |
|---|---|
| 충돌 | 0 |
| GPU 영역 밖 변경 | 0 / 143 파일 |
| 양쪽 선등록 commit hash | 보존(조상 확인) |
| 회귀 72 파일 | 차이 0 |
| descriptor 테스트 | PASS |

## 핵심 발견

- 없음(통합 작업).

## 해석

- 없음.

## 확인되지 않은 사항

- 없음.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 결정 7(두 서버 규약) 종료. 이후 GPU 영역도 main에서 관리한다(GTASK 번호 체계는 유지).

## 다음 작업

- 결과 색인·표·그림 갱신([TASK105](TASK105.md)).

## 재현 정보

- merge commit `af3dfe3`, 첫 부모 `a953e03`, 둘째 부모 `614a4c4`.
