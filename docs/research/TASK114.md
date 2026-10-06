# TASK114 — 익명 사본 재생성 3: 이전 버전 연결 표현 정리 (지시문 20)

## 상태

DONE

## 날짜

2026-10-06

## 목적

지시문 20: 제외 목록에 `paper/latex/` 전체와 TASK38·39·70 문서를 더하고, 남은 파일에서 지시문의 검색어 7개(이전 버전을 가리키는 치환 문자열, 점검표·tag 이름, 투고처·초록 길이 표현 등)를 지우거나 중립 표현으로 바꾸며, INDEX의 TASK38·39·70 행을 삭제한 사본을 지시문 19 절차로 다시 만든다. 재현에 필요한 `ANONYMIZATION/`, `tools/ARTIFACT_COMMANDS.md`, 결과 색인, 모형 문서, 코드, 로그는 유지. **업로드 없음, 측정 0.**

## 배경

- [TASK113](TASK113.md) — 지시문 19 사본

## 시작 상태

- HEAD `a40c091`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. 검색: 원본 저장소의 남은 파일에는 4건뿐이었고, 사본에서는 92건이었다 — 대부분이 지시문 13의 치환 문자열(이전 버전을 가리키는 표현, tag·점검표 이름)에서 나왔다. 그래서 **원본 저장소의 연구 기록은 바꾸지 않고 사본 빌드에서** 처리했다.
2. 빌드 변경(저장소 밖 작업 디렉터리): (a) 제외 4항목 추가; (b) 이전 버전 관련 치환 대상 9개의 치환 문자열을 중립 표현(`이전 버전`, `기준점 tag`, `CHECKLIST`, `previous version`, `[previous version title]`)으로 변경; (c) 사본 전용 텍스트 편집 파일(`post_edits.json`, 각 편집이 정확히 1회 일치해야 통과): INDEX TASK38·39·70 행 삭제, TASK37·TASK60의 다른 논문 서지 표현 4곳 중립화. 편집은 익명화 전 원문에 적용(placeholder 줄 번호 보존).
3. 첫 빌드 검사 실패 2회: 사본에 들어간 내 기록(TASK113, INDEX TASK113 행)에 검사 문자열(홈 경로·사본 디렉터리 이름, 로그인 이름 단어)이 그대로 적혀 있었다. 원본에서 표현만 일반어로 바꿨다(commit `d0fa87f`, `7951224`).
4. tar 생성(사본 디렉터리에서 코드 실행 없음) → 새로 풀어 byte 단위 최종 검사(검색어 7개 + 영문 표현 포함) → 또 다른 디렉터리에 풀어 `PYTHONDONTWRITEBYTECODE=1` 동작 확인.
5. 새 사본 확인 뒤 지시문 19 사본 디렉터리(`-r2`) 삭제.

## 변경된 파일

- `docs/research/TASK113.md`, `docs/research/INDEX.md`(표현 정리, commit `d0fa87f`·`7951224`)
- `docs/research/TASK114.md`(신규), `docs/research/INDEX.md`
- 저장소 밖: 작업 디렉터리(대상 파일·빌드·편집·검사 스크립트), 사본, `artifact.tar.gz`, `ANONYMIZATION_REPORT.md`

## 실험 또는 검증 방법

```bash
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 <export>/workspace/build.py --out <export>/artifact
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-06 00:00:00 UTC' -cf - artifact | gzip -n -9 > artifact.tar.gz
tar -xzf artifact.tar.gz -C <export>/scan && PYTHONDONTWRITEBYTECODE=1 python3 <export>/workspace/final_scan.py <export>/scan
tar -xzf artifact.tar.gz -C <export>/check   # 동작 확인은 여기서만
```

## 결과

- `artifact.tar.gz` 129 MB, 7,830 항목, **SHA256 `f3e2deef40e35406689a6ac48a7bd85c35d23289e485a6765acb081868fecd7f`**. 사본 7,322 파일(tracked 747 + results 6,575) + `ANONYMIZATION/`.
- 치환 267,152건(other 1,517 — 제외 확대로 감소).
- **재추출 검사**: bytecode 0, 홈 경로 0, 사본 디렉터리 이름 0, 사용자명 0(vendor SDK 호출 1곳은 SDK 모듈 이름), 지시문 20 검색어 7개 + 영문 표현: 텍스트·gzip 내부 0. 대소문자 무시 검색에서 한 검색어가 `.gz` 3개의 **압축 byte** 안에서만 3회 우연히 일치(풀면 0). 적용 대상 0, 제외 경로 0, generic은 허용 주소 3건과 압축 byte 오탐뿐.
- **동작(별도 복제본)**: plan 127/127, runner + fake server exit 0(196 요청), 두 parity PASS, `PREDICTIONS_CTX.json` byte 동일. 이후 모든 디렉터리에 bytecode 0, SHA256 불변.

## 핵심 발견

- 검색어 대부분은 원문이 아니라 지시문 13의 치환 문자열이었다 — 치환 문자열 자체가 이전 버전과의 연결을 드러냈다.
- 익명화 작업 기록(TASK문서)도 사본에 들어가므로, 기록에 검사 문자열을 그대로 적으면 검사에 걸린다.

## 해석

- 없음.

## 확인되지 않은 사항

- 업로드 전 사용자 확인 사항은 TASK113과 같다. 제외 문서로 가는 링크는 끊긴다.

## 실패 / 무효 시도

- 첫 두 빌드: 내 기록 문서의 검사 문자열 때문에 `CHECK FAIL` / 최종 검사 일치 → 원본 표현 정리 후 재빌드.

## 연구 원칙에 미치는 영향

- 익명화 관련 기록에는 검사 대상 문자열을 그대로 쓰지 않는다.

## 다음 작업

- 사용자 확인 후 업로드(사용자 직접).

## 재현 정보

- 사본 원본 commit `7951224`. 빌드·편집·검사 파일은 저장소 밖 작업 디렉터리.
