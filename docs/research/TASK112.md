# TASK112 — GPU branch 재병합(GTASK22), Python 3.12 재현 조건 명시, 익명 사본 재생성 (지시문 18)

## 상태

DONE

## 날짜

2026-10-06

## 목적

Advisor 지시문 18: (1) `origin/gpu-a6000`(`954dd03`, GTASK22 포함)을 main에 fast-forward로 합친다. (2) `tools/ARTIFACT_COMMANDS.md`에 GPU 예측 파일 bit 재현에 Python 3.12가 필요하다는 점을 적는다. (3) 지시문 13과 같은 결정·검사 기준으로 익명 사본과 `tar.gz`를 다시 만든다. **업로드 없음, 측정 0.**

## 배경

- [TASK104](TASK104.md) — 첫 GPU branch 통합, [TASK107](TASK107.md) — 첫 익명 사본(지시문 13)
- GTASK22(`docs/research/gpu/GTASK22.md`) — GPU 경계 효과 민감도. Python 3.10.12에서 GPU 예측 22/22가 상대 ~10⁻¹⁴ 불일치, 3.12.13에서 정확 일치(3.12의 float `sum()` 보상 합산)

## 시작 상태

- HEAD `167c4dd`(= `origin/main`), `?? .idea/`만. `origin/gpu-a6000` `954dd03`은 main의 자손(fast-forward 가능 확인).

## 수행 내용

1. `git merge --ff-only origin/gpu-a6000` → `954dd03`(GPU 문서·스크립트 7파일, 충돌 없음).
2. `tools/ARTIFACT_COMMANDS.md` §4 머리에 "Python version (bit-exact predictions)" 단락 추가: GPU 예측 파일 bit 재현은 Python 3.12(`<GPU_VENV>`, 3.12.13) 필요, 3.10은 상대 ~1e-14 차(GTASK22), `+=` 누적 관측 집계는 두 버전 동일, NPU 예측 파일은 시스템 Python 3.10.12로 정확히 재현됨(TASK111 22/22; 파일에 인터프리터 버전 기록 없음). commit `4f903db`.
3. 익명 사본: 지시문 13의 `workspace/build.py`·`targets.json`을 바꾸지 않고 새 작업 디렉터리(저장소 밖)에 복사해 `4f903db`에서 빌드, `tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-06 00:00:00 UTC' | gzip -n -9`.
4. 사본 안 동작 점검(지시문 13과 같은 항목).

## 변경된 파일

- `tools/ARTIFACT_COMMANDS.md`(commit `4f903db`), GPU branch 7파일(fast-forward)
- `docs/research/TASK112.md`(신규), `docs/research/INDEX.md`
- 저장소 밖: 익명 사본 디렉터리, `artifact.tar.gz`, `ANONYMIZATION_REPORT.md`

## 실험 또는 검증 방법

```bash
git merge --ff-only origin/gpu-a6000
env -u PYTHONPATH python3 <export>/workspace/build.py --out <export>/artifact
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-06 00:00:00 UTC' -cf - artifact | gzip -n -9 > artifact.tar.gz
# 사본 안: plan 검증, multiturn_runner.py + fake_server.py, tests/ctx_descriptor_npu.py,
#          tests/gpu_ctx_parity.py --gpu-root <copy>, predict_ctxblind.py 출력 cmp
```

## 결과

- 사본: 내보낸 파일 7,363(tracked 788 + results 6,575) + `ANONYMIZATION/`, 797 MB. `artifact.tar.gz` 135 MB, 7,924 항목, SHA256 `551f637407dc38e2273534beaa8743c1d4becd1ad73d35bd956ac28558d7c3d2`.
- 치환 267,238건(path 222,313, device_id 42,916, other 1,591, hostname 394, username 18, real_name 3, url 2, affiliation 1). 지난 사본 대비 path +7, other +2(새 GTASK22·TASK110–111 문서).
- **최종 검사(gzip 296개 내부 포함) 남은 식별 문자열 0건, generic 0건, `CHECK PASS`.** 유지 결정 장비명 10건. 수동 검색(저자 이름·e-mail local part·사용자·host·home 경로·원 저장소 이름) 0건; 남은 일치는 지난 사본과 같다(vendor·compiler 이름, 공개 upstream 이름, 소문자 patch 파일 이름).
- **정정([TASK113](TASK113.md))**: 이 사본의 `tar.gz`(SHA256 `551f6374…`)에는 사본 안 동작 점검으로 생긴 `.pyc` 37개가 들어갔고 모두 절대 경로를 담고 있다. 위 "남은 0건"은 tar가 아니라 빌드 직후 디렉터리 기준이다. 이 tar는 사용하지 않는다.
- 사본 안: plan 검증 127/127, runner + fake server exit 0(window 종료, 196 요청), `ctx_descriptor_npu` PASS, `gpu_ctx_parity` PASS, `PREDICTIONS_CTX.json` byte 동일.

## 핵심 발견

- 없음(재생성 작업).

## 해석

- 없음.

## 확인되지 않은 사항

- 업로드 전 사용자 확인 사항은 TASK107과 같다(저자 이름 한국어 표기, `paper/figures/` 연결, 선등록 hash, 장비명 유지, 미포함 항목, placeholder).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- 사용자 확인 후 업로드(사용자 직접).

## 재현 정보

- 사본 원본 commit `4f903db`. 대상 파일·빌드 스크립트는 저장소 밖 작업 디렉터리(지시문 13 것과 동일 내용).
