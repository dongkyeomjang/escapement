# TASK99 — 익명 artifact export 도구 (도구만, 공개·업로드 없음)

## 상태

DONE

## 날짜

2026-10-02

## 목적

Advisor 지시문 10 작업 C. SIGMETRICS 저자 익명 심사에 대비해, 제출 직전에 익명 스냅샷을 만들 **도구만** 준비한다. 실제 공개·업로드·push는 하지 않는다. 문서는 재현 명령 표뿐이며 연구 내용 설명이나 논문 문장은 쓰지 않는다.

**측정 0.**

## 배경

- [결정 6](INDEX.md#결정-6--투고-타깃)(SIGMETRICS 2027 fall), [TASK94](TASK94.md)·[TASK96](TASK96.md)(결과 색인과 표 데이터)

## 시작 상태

- HEAD `dfd908d`. 작업은 background subagent가 [TASK97](TASK97.md) 측정과 병행했다(15:43–16:00경, 가벼운 scan과 export 시험).

## 수행 내용

1. 저자를 드러내는 문자열 목록: tracked 파일(`HEAD`), `origin/gpu-a6000`의 GPU 영역(읽기 전용, `git grep`/`git archive`), 비추적 `results/`를 scan. 88 대상(`tools/anon_targets.json`), 위치 표 `tools/ANON_TARGETS.md`(대상별 처음 20개 위치 + 총 수), 전체 위치 `tools/anon_occurrences.csv`(9,487행 — **추적하지 않음**, `anon_export.py --report-only`로 다시 만든다).
2. `tools/anon_export.py`: `git archive <commit>`(tracked만, 이력 없음) → 치환(텍스트만; binary는 보고만) → 전체 재scan(대상 + 일반 검사 `/home/`, email, `github.com/<owner>`) → `ANON_MANIFEST.json`. 옵션 `--gpu-ref`(GPU 영역을 다른 ref에서 읽기 전용으로 추가, branch 통합 없음), `--rename-package NAME`(기본 꺼짐), `--include-results LIST`(기본 없음), `--apply/--keep ID`(결정 필요 대상), `--exclude PATH`, `--report-only`. 종료 코드 0 통과, 1 실패, 2 결정 필요 대상만 남음. 대상 파일 자신과 `.idea/`는 export에서 뺀다. 출력 위치는 저장소 밖이어야 한다.
3. `tools/results_sizes.{md,csv}`: `results/` 크기·파일 수(57 단위, 651.8 MiB) — 포함 여부 결정은 하지 않음. TASK97 측정 종료 뒤 다시 만들었다.
4. `tools/ARTIFACT_COMMANDS.md`: 명령·입력 경로·산출 경로 표(표 생성 24행, TASK 162행, GTASK 15행; TASK 문서의 "실험 또는 검증 방법"에서 기계적으로 뽑았고 다시 실행하지 않았다). 기계 경로는 `<REPO>` 등 자리표시.

## 변경된 파일

- `tools/{anon_export.py, anon_targets.json, ANON_TARGETS.md, results_sizes.md, results_sizes.csv, ARTIFACT_COMMANDS.md}`(신규), `.gitignore`(`tools/anon_occurrences.csv`)
- `docs/research/TASK99.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 tools/anon_export.py --report-only --report-results     # 대상 표 재생성
env -u PYTHONPATH python3 tools/anon_export.py --commit HEAD --out <저장소 밖 빈 디렉터리>
env -u PYTHONPATH python3 tools/anon_export.py --commit HEAD --gpu-ref origin/gpu-a6000 --out <…>
env -u PYTHONPATH python3 tools/anon_export.py --commit HEAD --rename-package <NAME> --out <…>
```

## 결과

### 대상 (종류별, 자동 / 결정 필요)

| 종류 | 자동 | 결정 필요 |
|---|---|---|
| affiliation | 9 | 0 |
| device_id | 47 | 1 |
| email | 3 | 0 |
| hardware_model | 0 | 3 |
| hostname | 3 | 0 |
| other | 1 | 3 |
| path | 8 | 2 |
| real_name | 3 | 0 |
| url | 1 | 0 |
| username | 4 | 0 |
| **합계** | **79** | **9** |

결정 필요 9: 서버 모델(Supermicro), NPU host CPU, GPU host CPU, PCI bus id, `/mnt/ssd/tracelab`, `/mnt/nvme`, 장비 제공 감사 문구(TASK42·`paper/ARXIV_CHECKLIST.md`), 프로젝트명 `escapement`/`Escapement`, 옛 저장소명 `continuum-npu`.

### export 시험 (`dfd908d` 기준, scratch 출력 삭제)

| 실행 | 파일 | 치환 (대상 수) | 남은 hit |
|---|---|---|---|
| HEAD | 574 | 362 (22) | 자동 0, 일반 0; 결정 필요 대상 99 → 종료 코드 2 |
| `--gpu-ref origin/gpu-a6000` | 574 + 103 | 576 (32) | 자동 0, 일반 0; 결정 필요 117 → 2 |
| `--rename-package` | 574 | 362 (22) + 이름 변경 32 파일·참조 285 | 결정 필요 99 → 2; 새 이름으로 import 확인 |

결정 필요 대상을 모두 정하면 `PASS`(0)에 도달함을 확인했다. `--include-results`(작은 run 2개) 시험에서 device UUID·`sid`·IP·host명 5,234건 치환.

### results/ 크기 (상위)

| 경로 | MiB | 파일 |
|---|---|---|
| `npu/stage3/20260930-main/` | 173.9 | 870 |
| `npu/stage3/20261002-simblind/` | 114.7 | 506 |
| `npu/stage3/20261001-hiload/` | 77.5 | 341 |
| `npu/stage3/20261001-stepcost-op/` | 73.8 | 588 |
| `npu/stage3/20260929-pilot-streaming/` | 27.0 | 111 |
| `npu/stage3/20261002-ctxcost/` | 24.1 | 270 |
| 합계 | 651.8 | 6,163 |

## 핵심 발견

1. 자동 치환 대상은 export 후 0건이 남는다. 남는 것은 사용자 결정 대상 9종뿐이다.
2. **자동 익명화로 고칠 수 없는 것**: (i) stage3 plan JSON의 `spec`에 legacy 경로가 있어 치환하면 plan의 `_sha256`이 맞지 않는다(runner가 거부; 76 파일, GPU 포함 108). (ii) 하드코딩된 경로(`REPO=` 등)는 자리표시로 바뀌어 심사자가 고쳐야 한다. (iii) TASK 문서의 commit hash(선등록 증거)는 이력 없이 검증할 수 없고, 저장소가 공개돼 있으면 검색된다. (iv) 저자 목록을 기록한 문서(TASK42·43, `paper/ARXIV_CHECKLIST.md`)는 치환보다 `--exclude`가 나을 수 있다. (v) 원고 LaTeX는 저장소에 없다.

## 해석

- 없음(도구 작업).

## 확인되지 않은 사항

- 결정 필요 9종과 위 (i)–(iv)의 처리(사용자·Advisor 결정).

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- (Advisor) 결정 필요 대상, plan hash 처리, 포함할 results, 제외할 문서, 패키지 이름 변경 여부.

## 재현 정보

- 위 명령. 도구 작성 시 HEAD `dfd908d`, GPU branch `e820f48`.
