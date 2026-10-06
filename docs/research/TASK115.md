# TASK115 — 익명 사본 재생성 4: 옛 명칭·이전 버전 단서·시간대 표기 정리 (지시문 21)

## 상태

DONE

## 날짜

2026-10-06

## 목적

지시문 21: 사본에서 프로젝트 옛 명칭(대소문자 무관)과 그 명칭이 들어간 환경변수·patch 파일 이름, 이름 유래 설명, 이전 버전 단서(소스 공개 문장, 기준점 commit, 라이선스·초록 길이, 이전 기전 목록, 이전 workload 설명), 옛 저장소를 가리키는 식별자, 작업 지시 표현(TASK108–111), 문서의 시간대 이름을 지우거나 중립화하고, 바뀐 파일의 SHA256을 쓰는 곳을 다시 계산한 뒤 지시문 20 절차로 사본을 다시 만든다. **업로드 없음, 측정 0. 원본 저장소의 연구 기록은 바꾸지 않았다.**

## 배경

- [TASK114](TASK114.md) — 지시문 20 사본

## 시작 상태

- HEAD `2da2df8`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. **사본 전용 변환**(저장소 밖 작업 디렉터리의 변환 파일): 전역 치환 19종 + hash 치환 7종, 파일별 정확 일치 편집 31건(각 1회 일치해야 통과), 정규식 편집 3건, 줄 삭제 7건, 구간 교체 4건(INDEX 결정 5 본문 → 상태 한 줄, README 개명 안내·옛 GPU 시스템 관계 절, TASK37 명칭 관측 절), 문서(로그 제외)의 시간대 이름 → `+09:00`. 지시문 20 편집도 여기에 합쳤다. 제외에 TASK112·113 추가, RULES.md의 package 개명 줄 제거.
2. **patch 이름 변경과 hash 재계산**: 관측 patch 파일과 그 안의 환경변수·주석 이름을 `kvsim`으로 바꿨다. 이 서버의 vLLM 0.22.0 원본 두 파일이 `apply.sh`의 pristine hash와 같아(site-packages는 읽기만, scratch 복사본에 적용), 새 patch를 적용한 결과 hash를 계산해 `apply.sh`와 문서의 축약 hash를 바꿨다: patch `4b7bbef9…4f8b`, 적용 후 `72f169da…48c4` / `bd093207…a704`. 변환된 78개 파일의 원래 hash(전체·12·8자리)를 참조하는 곳은 사본에 없었다.
3. **옛 저장소 식별자 판단**: legacy 문서의 `*_policy.py`·`*_signal.py`·`*_client.py`와 관련 환경변수·`kv_transfer_params` 키는 옛 fork에서 저자가 새로 쓴 것이라(옛 저장소 commit 저자 확인) `kvsim`으로 개명했다. upstream(비교 대상 시스템 저자) commit에서 온 상수 `FIXED_THRESHOLD_*`, scheduler의 정책 상수, 실험 디렉터리, 그 정책을 가리키는 팔 이름은 비교 대상의 구현이라 유지했다(legacy 문서 14줄).
4. 빌드(코드 실행은 작업 디렉터리에서만) → tar → 새로 풀어 byte 단위 검사 → 또 다른 디렉터리에 풀어 `PYTHONDONTWRITEBYTECODE=1` 동작 확인 → 지시문 20 사본 디렉터리 삭제.

## 변경된 파일

- `docs/research/TASK115.md`(신규), `docs/research/INDEX.md`
- 저장소 밖: 작업 디렉터리(대상 파일·빌드·변환·검사 스크립트), 사본, `artifact.tar.gz`, `ANONYMIZATION_REPORT.md`(서버 보관용, 업로드 대상 아님)

## 실험 또는 검증 방법

```bash
PYTHONDONTWRITEBYTECODE=1 env -u PYTHONPATH python3 <export>/workspace/build.py --out <export>/artifact
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-06 00:00:00 UTC' -cf - artifact | gzip -n -9 > artifact.tar.gz
tar -xzf artifact.tar.gz -C <export>/scan  && PYTHONDONTWRITEBYTECODE=1 python3 <export>/workspace/final_scan.py <export>/scan
tar -xzf artifact.tar.gz -C <export>/check # 동작 확인은 여기서만
```

## 결과

- `artifact.tar.gz` 129 MB, 7,829 항목, **SHA256 `a5197ee155bcfba25d49b6ee8d4fd6cdac6ce1671957a3699a8e537d331bd3e5`**. 사본 7,321 파일(tracked 746 + results 6,575).
- **재추출 검사(텍스트·gzip 내부)**: 지시문 21 검색어 8종(옛 명칭 대소문자 무관, 이름 유래 단어, 소스 공개 문구, 기준점 commit, 라이선스 약칭, 비교 시스템 이름, 시간대 이름 2종) 0, 지시문 20 검색어 0, 홈 경로·사본 디렉터리 이름·사용자명·bytecode·적용 대상·제외 경로 0. 압축 byte 안에서만 우연 일치(시간대 약칭 7, 지시문 20 한 검색어 3). 소문자 비교 시스템 이름은 위 3의 유지 항목 14줄.
- **동작(별도 복제본)**: plan 127/127, runner + fake server exit 0(196 요청), 두 parity PASS, `PREDICTIONS_CTX.json` byte 동일, 새 patch 적용 → `apply.sh` 기록 hash 일치·되돌리기 → pristine, 격리 launcher가 새 환경변수 이름과 새 임시 디렉터리 이름으로 동작.

## 핵심 발견

- 관측 patch는 이 서버의 vLLM 원본과 같아서 GPU host 없이 적용 후 hash를 다시 계산할 수 있었다.

## 해석

- 없음.

## 확인되지 않은 사항

- 업로드 전 사용자 확인 사항(저자 이름 한국어 표기, 선등록 hash, 장비명 유지, 미포함 항목, placeholder). 바뀐 patch는 GPU host에서 실제로 적용해 보지 않았다(같은 원본 파일로 scratch에서 확인).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- 사용자 확인 후 업로드(사용자 직접).

## 재현 정보

- 사본 원본 commit `2da2df8`. 빌드·변환·검사 파일은 저장소 밖 작업 디렉터리.
