# TASK107 — 익명 공개 자료(사본) 생성

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 13. [TASK99](TASK99.md)의 export 도구로 익명 사본과 `tar.gz`를 만들고 검사한다. **업로드·공개하지 않는다**(사용자가 직접 한다). 원본 저장소는 이 기록 외에 바꾸지 않았다.

**측정 0.**

## 배경

- [TASK99](TASK99.md) — `tools/anon_export.py`, 대상 88개
- [TASK104](TASK104.md) — GPU branch 통합(지시문 13 §0 전제, `af3dfe3`이 main에 있음 확인)
- [TASK103](TASK103.md) — 사본 안 재계산 검사에 쓴 `tests/ctx_descriptor_npu.py`, `tests/gpu_ctx_parity.py`

## 시작 상태

- HEAD `8a11520`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. 저장소 밖 작업 디렉터리 `/home/rebel/anon-export-20261002/`에 지시문 13 결정을 반영한 대상 파일(`workspace/targets.json`, 98 대상)과 구동 스크립트(`workspace/build.py`)를 두었다. 저장소의 도구 함수를 그대로 쓰고, 도구에 없던 처리 셋을 더했다: (i) gzip 296개를 풀어 치환·검사 후 다시 압축(mtime 0), (ii) 내용이 바뀐 plan 96개의 `_sha256` 재계산과 INDEX hash field 186개 갱신, 대응표, (iii) placeholder 위치표.
2. 결정 반영: 장비명 3종 유지, PCI bus id·`/mnt` 경로 치환, 장비 제공 감사 문구 삭제, 프로젝트명 → `artifact`, 옛 저장소명 → `artifact-repo`, 패키지 `continuum` → `kvsim`, TASK42·43·`paper/ARXIV_CHECKLIST.md` 제외, 선등록 commit hash 유지, `results/` 원자료 전부 포함.
3. §2 추가 대상: 한국어 소속 약칭, 이전 원고 연결(이전 버전 tag, 점검표 파일명, "arXiv 제출본/원고/…" 등 자기 원고 언급 → "이전 원고", 원고 제목). 다른 논문의 arXiv 인용은 그대로. 이전 원고의 arXiv 번호는 저장소에 없었다. 한국어 실명은 저장소에서 찾지 못했다.
4. 첫 빌드 검사 실패 2건을 고쳤다: 사본 안 규칙 문서에 대상 id(호스트명이 들어간 id)를 적은 것 → 번호로 바꿈; GPU driver script의 commit trailer `noreply@anthropic.com`(저자 주소 아님) → email 허용 목록.
5. 사본 안 동작 확인(아래)과 결정적 `tar.gz`(소유자 0/0, 고정 mtime).

## 변경된 파일

- `docs/research/TASK107.md`(신규), `docs/research/INDEX.md` — 원본 저장소의 다른 파일은 바꾸지 않았다.
- 저장소 밖: `/home/rebel/anon-export-20261002/{artifact/, artifact.tar.gz, ANONYMIZATION_REPORT.md, workspace/}`

## 실험 또는 검증 방법

```bash
cd /home/rebel/anon-export-20261002/workspace && env -u PYTHONPATH python3 build.py --out ../artifact
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-02 00:00:00 UTC' -cf - artifact | gzip -n -9 > artifact.tar.gz
# 사본 안: tests/ctx_descriptor_npu.py, tests/gpu_ctx_parity.py --gpu-root <copy>, predict_ctxblind.py,
#          plan 검증(127개), multiturn_runner.py + fake_server.py, 표 재생성(임시 git init 복제본)
```

## 결과

- 사본 7,334 파일(tracked 762 + results 6,572) + `ANONYMIZATION/`, 793 MB. `artifact.tar.gz` 133 MB, SHA256 `2c49ce1c17d89e5d5b2a26e5baddf7237f72e729673ffff70f75f41bad918901`.
- 치환 267,229건: path 222,306, device_id 42,916(PCI bus id 42,796), other 1,589, hostname 394, username 18, real_name 3, url 2, affiliation 1. **최종 검사(gzip 내부 포함) 남은 건수 0**, 유지 결정 장비명 10건.
- 사본 안 동작: plan 검증 127/127, runner + fake server 정상 종료, TASK101 주 예측기 6 cell·GTASK20 주 예측기 12 cell 정확 일치, `PREDICTIONS_CTX.json` byte 동일. 표: 72 파일 동일, 14 파일 출처 commit hash만 다름(검사용 임시 git), T07은 legacy 저장소의 trace 요약 파일이 사본에 없어 생성 불가, T11은 `models/` 미포함으로 artifact 크기 열이 빔.
- 보고서: `/home/rebel/anon-export-20261002/ANONYMIZATION_REPORT.md`.

## 핵심 발견

1. export 도구만으로는 gzip 로그(296개)를 익명화할 수 없었다 — 풀어서 치환·재압축하는 단계가 필요했다.
2. 표 생성기는 출처 commit을 git에서 읽으므로 이력 없는 사본에서는 git 저장소를 만들어야 돌아간다. T07은 저장소 밖 입력에 의존한다.

## 해석

- 없음.

## 확인되지 않은 사항

- 저자 이름의 한국어 표기(저장소에 없음), `paper/figures/`가 이전 원고 그림과 같은 이미지라는 연결, 원 GitHub 저장소 공개 여부(선등록 hash 검색 가능성) — 사용자 확인 사항.

## 실패 / 무효 시도

- 첫 빌드 검사 실패 2건(수행 내용 4).

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- 사용자 확인 후 업로드(사용자 직접).

## 재현 정보

- 원본 commit `8a11520`, 위 명령. 대상 파일·구동 스크립트는 저장소 밖 `workspace/`.
