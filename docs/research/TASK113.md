# TASK113 — 익명 사본 재생성 2: 제외 목록 확대, bytecode 오염 제거, tar 재추출 검사 (지시문 19)

## 상태

DONE

## 날짜

2026-10-06

## 목적

지시문 19: export 제외 목록에 `__pycache__/`·`*.pyc` 전부, `docs/research/TASK99.md`, `docs/research/TASK107.md`, `paper/VENUES.md`, `paper/figures/` 전체를 추가하고(`ANONYMIZATION/`의 치환 규칙·plan hash 대응표는 유지), 원본 저장소의 `paper/latex/README.md` 40행(저자 수·장비 감사·단과대학 문장)을 지우고 INDEX의 TASK42 행을 "제출 패키지 완성"으로 중립화한 뒤 사본을 다시 만든다. 동작 확인은 tar를 만든 뒤 별도 복제본에서 `PYTHONDONTWRITEBYTECODE=1`로, 최종 검사는 tar를 다시 풀어서 한다. **업로드 없음, 측정 0.**

## 배경

- [TASK112](TASK112.md) — 지시문 18 사본(SHA256 `551f6374…`)

## 시작 상태

- HEAD `39878a3`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. **TASK112 사본 결함 확인**: 그 `tar.gz`에 `.pyc` 37개가 들어 있었고, 37개 모두 사본 경로(`/home/…/anon-export…`)를 담고 있었다. 원인: 식별 문자열 검사를 빌드 직후에 하고, 그 뒤 사본 디렉터리 안에서 동작 점검(Python 실행)을 한 다음 tar를 만들었다. TASK112의 "남은 식별 문자열 0건"은 tar 기준으로 틀렸다(업로드 없음). 2026-10-02 사본(TASK107)의 tar에는 `.pyc`가 0개였다.
2. 원본 저장소: `paper/latex/README.md` 한계 3번 항목(40행) 삭제·번호 재정렬, INDEX TASK42 행을 `| [TASK42](TASK42.md) | DONE | 제출 패키지 완성 | 제출 패키지 완성. |`로 바꿈. commit `2af3531`.
3. 빌드: 지시문 13 대상 파일에 제외 6항목 추가, 빌드 스크립트의 제외 판정에 경로 성분 `__pycache__`와 `.pyc` 접미사 처리 추가, `RULES.md`의 제외 설명 문장을 중립 문장으로 바꿈(치환 규칙 표·plan hash 대응표는 그대로). 저장소 밖 새 작업 디렉터리에서 `PYTHONDONTWRITEBYTECODE=1`로 빌드, 사본 디렉터리에서는 아무 코드도 실행하지 않고 tar 생성.
4. 최종 검사: tar를 새 디렉터리에 풀어 모든 파일을 byte로(텍스트·바이너리, gzip 296개 풀어서) 검사 — 대상 치환 규칙, generic 검사, `/home/`, `anon-export`, 사용자명.
5. 동작 확인: tar를 또 다른 디렉터리에 풀어 `PYTHONDONTWRITEBYTECODE=1`로 실행. 끝난 뒤 세 디렉터리 모두 `__pycache__`·`.pyc` 0, tar SHA256 불변 확인.

## 변경된 파일

- `paper/latex/README.md`, `docs/research/INDEX.md`(commit `2af3531`)
- `docs/research/TASK113.md`(신규), `docs/research/TASK112.md`(정정 한 줄), `docs/research/INDEX.md`
- 저장소 밖: 새 작업 디렉터리의 대상 파일·빌드 스크립트·검사 스크립트, 사본, `artifact.tar.gz`, `ANONYMIZATION_REPORT.md`

## 실험 또는 검증 방법

```bash
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 <export>/workspace/build.py --out <export>/artifact
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-06 00:00:00 UTC' -cf - artifact | gzip -n -9 > artifact.tar.gz
tar -xzf artifact.tar.gz -C <export>/scan  && PYTHONDONTWRITEBYTECODE=1 python3 <export>/workspace/final_scan.py <export>/scan
tar -xzf artifact.tar.gz -C <export>/check # 동작 확인은 여기서만, PYTHONDONTWRITEBYTECODE=1
```

## 결과

- `artifact.tar.gz` 129 MB, 7,837 항목, **SHA256 `09148c28a4ba6eda45ea410b5e7aaacc8d9fcb266caa64211b003bd78b60b698`**. 사본 7,328 파일(tracked 753 + results 6,575) + `ANONYMIZATION/`.
- 치환 267,218건(path 222,305, device_id 42,916, other 1,583, hostname 394, username 18, url 2; real_name·affiliation 0 — README 문장 삭제로).
- **재추출 검사**: `.pyc`/`__pycache__` 0, `/home/` 0, `anon-export` 0, 사용자명 0, 적용 대상 0, 제외 경로 0. generic 검사는 텍스트·gzip 내부에서 허용된 `noreply@anthropic.com` 3건뿐; 압축 byte 열(PDF 그림 3, `.gz` 7)에 우연히 e-mail 모양인 byte 열이 있으나 풀면 없다(오탐). "rebel"은 vendor SDK·compiler 이름으로만 남음.
- **동작(별도 복제본)**: plan 검증 127/127, runner + fake server exit 0(window 종료, 196 요청), `ctx_descriptor_npu` PASS, `gpu_ctx_parity` PASS, `PREDICTIONS_CTX.json` byte 동일.

## 핵심 발견

- 사본 안에서 코드를 실행하면 bytecode가 절대 경로를 남긴다. 검사 순서(빌드 → 검사 → 실행 → tar)가 원인이었다.

## 해석

- 없음.

## 확인되지 않은 사항

- 업로드 전 사용자 확인 사항(저자 이름 한국어 표기, 선등록 hash, 장비명 유지, 미포함 항목, placeholder). 제외된 문서로 가는 링크는 사본 안에서 끊긴다.

## 실패 / 무효 시도

- TASK112 사본(SHA256 `551f6374…`): `.pyc` 37개에 절대 경로 — **사용 금지**. 그 보고의 "남은 0건"은 빌드 직후 디렉터리 기준이었다.

## 연구 원칙에 미치는 영향

- 익명 사본 절차: 사본(tar 원천) 디렉터리에서 코드를 실행하지 않는다. 검사는 tar를 다시 푼 것에서 한다.

## 다음 작업

- 사용자 확인 후 업로드(사용자 직접).

## 재현 정보

- 사본 원본 commit `2af3531`. 빌드·검사 스크립트와 대상 파일은 저장소 밖 작업 디렉터리.
