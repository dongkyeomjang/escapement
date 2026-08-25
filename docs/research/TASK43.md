# TASK43 — repository 개명 후 정합화

## 상태

DONE

측정 없음. `origin`을 신 URL로 갱신하고, 현행 참조 문서의 명칭을 통일했으며, [README](../../README.md) 머리에 개명 사실과 **명칭 충돌 이력**을 능동적으로 명시했다. **구 URL 치환 대상은 0건이었다** — 아래 관측 1이 이유다.

## 판정

| 항목 | 결과 |
|---|---|
| Remote 갱신 | `git@github.com:dongkyeomjang/escapement.git`. `fetch`·`ls-remote` 동작 확인 |
| 구 URL 치환 | **대상 0건 / 비대상 1건**. 현행 문서에 GitHub URL이 하드코딩된 곳이 없었다 |
| 명칭 통일 | README·INDEX·TASK_GUIDE **표제 3건** |
| README 개명 안내 | 추가 — 개명 사실 + Continuum과 무관함 + 바꾸지 않는 것과 이유 |
| INDEX 결정 5 | 개명 실행 사실·날짜·**바꾸지 않는 것 3종과 각각의 이유** 기록 |
| 검증 | 현행 문서 구 URL 잔존 **0**, `check_claims` 47/47, 그림 대조 177/177 |

## 날짜

2026-08-25

## 목적

사용자가 GitHub에서 `dongkyeomjang/continuum-npu` → `dongkyeomjang/escapement` 개명을 실행했다. GitHub이 구 URL을 redirect하지만 **redirect 의존을 없애고**, 남은 참조와 표제를 신 명칭으로 정리한다.

## 배경

관련 TASK: [TASK37](TASK37.md)(명칭 충돌 재확인 — v6에서 `Continuum`으로 되돌아왔다), [TASK38](TASK38.md)(명칭 `Escapement` 확정), [TASK07](TASK07.md)(remote 기록의 출처), [TASK12](TASK12.md)(patch — 비대상 판정의 근거), [INDEX 결정 5](INDEX.md#결정-5--시스템-명칭-충돌).

## 시작 상태

- Base commit: `444d9d4` ([TASK42](TASK42.md))
- 측정 없음. serving 기동 0회, 재compile 0회, device 접근 0회, 설치 0건
- 개명 전 `origin`: `git@github.com:dongkyeomjang/continuum-npu.git`

## 수행 내용

1. `git remote set-url origin` 실행 후 `git remote -v`·`git fetch`·`git status -sb`·`git ls-remote`로 확인했다.
2. `dongkyeomjang/continuum-npu`와 `continuum-npu` 문자열을 저장소 전체에서 전수 탐색하고 **한 건씩 대상/비대상을 판별**했다.
3. 현행 참조 문서 3건의 표제를 신 명칭으로 통일하고 [README](../../README.md)에 개명 안내를 넣었다.
4. [INDEX](INDEX.md) 결정 5에 개명 실행과 **바꾸지 않는 것 3종의 이유**를 기록했다.
5. "저장소"라는 말이 GitHub repo와 로컬 경로 사이에서 모호해진 곳을 정리했다.
6. 검증 script를 재실행해 경로 변화가 없음을 확인했다.

## 변경된 파일

- `README.md` — 표제 + 개명 안내
- `docs/research/INDEX.md` — 표제, 결정 5, "저장소" 표현 정리
- `docs/research/TASK_GUIDE.md` — 표제
- `paper/ABSTRACT.md`, `paper/OUTLINE.md` — "저장소 경로" → 로컬 경로임을 명시
- `paper/draft/11_appendices.md` — 부록 D의 `[NEEDS-EVIDENCE]`에 URL 안정 사실 추가
- `docs/research/TASK43.md`(신규)

## 실험 또는 검증 방법

측정 없음.

- Remote: `git remote -v` → 신 URL 2줄. `git fetch origin` 성공. `git ls-remote --heads origin main` → `444d9d4`(local과 동일).
- 문자열: `grep -rn "dongkyeomjang/continuum-npu"`와 `grep -rn "continuum-npu"`를 `.git` 제외 전수 실행.
- 문서: `check_claims.py`, `verify_figures.py` 재실행.

## 결과

### 관측 1 — 구 URL 치환 대상이 0건이었다

`dongkyeomjang/continuum-npu` 전수 탐색 결과는 **단 한 건**이다.

| 위치 | 내용 | 판정 | 이유 |
|---|---|---|---|
| `docs/research/TASK07.md:27` | `- Remote: origin → git@github.com:dongkyeomjang/continuum-npu.git` | **비대상** | **과거 기록.** 그 TASK가 remote를 도입하던 시점의 사실이며, 당시 URL이 그것이었다는 것 자체가 기록의 내용이다 |

**현행 참조 문서(README, `paper/`, AGENTS.md, CLAUDE.md)에는 GitHub URL이 한 곳도 하드코딩돼 있지 않았다.** 지시문이 치환 대상으로 지목한 "`paper/` 하위, 부록 B의 clone URL"도 실재하지 않는다 — 부록 B는 선등록 commit hash 표이고 clone URL을 담지 않으며, 저장소 위치를 언급하는 곳은 **부록 D 하나뿐인데 그마저 URL 없이 "released with the paper"로만 적고 공개 방식을 `[NEEDS-EVIDENCE]`로 남겨 두었다.**

따라서 **redirect 의존은 애초에 remote 설정 한 곳뿐이었고, 그것을 갱신한 것으로 해소됐다.**

### 관측 2 — `continuum-npu` 문자열의 나머지는 전부 비대상

| 종류 | 건수 | 판정 | 이유 |
|---|---|---|---|
| 로컬 경로 `/home/rebel/continuum-npu` (TASK 문서·`STAGE*`/`*_PREREG` 재현 command) | 다수 | **비대상** | 지시문이 로컬 경로 이동·개명을 금지했고, 이 문자열들은 실재하는 경로를 가리킨다 |
| `README.md:23` | 1 | **비대상** | legacy 경로와 대비해 **이 저장소의 로컬 위치**를 적은 문장. 경로 자체는 바뀌지 않았다 |
| `paper/figures/SOURCES.md:32` | 1 | **비대상** | `cd /home/rebel/continuum-npu` — 그림 재생성 command |
| **`patches/vllm_rbln-0.11.1/decoder_bucket_observe.patch:7`** | 1 | **절대 비대상** | patch 본문의 주석 문자열이다. **고치면 적용 후 SHA256이 달라지고, 그 hash(`70942d16…`)는 모든 측정 run의 provenance에 기록돼 있다.** 문자열 하나를 바꾸면 과거 run 전체의 substrate 검증이 깨진다 |
| `.idea/` | 1 | **비대상** | IDE 설정. untracked이며 이 저장소가 소유하지 않는다 |

### 관측 3 — 명칭 통일 대상은 표제 3건

「과거 기록 본문은 수정하지 않는다」는 경계를 **문서 단위가 아니라 내용 단위**로 적용했다. `docs/research/`에 있어도 [INDEX](INDEX.md)와 [TASK_GUIDE](TASK_GUIDE.md)는 **현행 참조 문서**이므로 표제는 통일 대상이고, 그 안의 과거 서술은 아니다.

| 파일 | 변경 전 | 변경 후 |
|---|---|---|
| `README.md` | `# Continuum NPU` | `# Escapement` + 개명 안내 blockquote |
| `docs/research/INDEX.md` | `# Continuum-NPU Research Task Index` | `# Escapement Research Task Index` (+ 경계 주석) |
| `docs/research/TASK_GUIDE.md` | `# Continuum-NPU 연구 TASK 작성 지침` | `# Escapement 연구 TASK 작성 지침` |

**본문 서술은 한 곳도 고치지 않았다.**

### 관측 4 — "저장소"라는 말이 모호해졌다

개명 전에는 "저장소 = 로컬 디렉터리 = GitHub repo"가 한 덩어리였지만, 이제 **GitHub repo는 `escapement`이고 로컬 경로는 `continuum-npu`** 다. 기존 문장 중 "저장소 경로는 그대로 둔다"는 형태가 오독을 부르므로 **"로컬 디렉터리 경로"** 로 바꿨다([INDEX](INDEX.md) 결정 5, [ABSTRACT.md](../../paper/ABSTRACT.md), [OUTLINE.md](../../paper/OUTLINE.md)).

### 관측 5 — README 안내문이 하는 일

세 가지를 한 blockquote에 넣었다.

1. **개명 사실과 구 이름** — 구 URL로 들어온 사람이 같은 저장소임을 즉시 안다.
2. **Continuum과 무관한 별개 연구임** — 이것이 지시문의 핵심 의도다. `Continuum`을 검색해 들어온 독자가 **이 저장소를 arXiv:2511.02230의 구현으로 오해하지 않게** 하는 것이, 개명이 실제로 해결하려던 문제다. 개명만 하고 이력을 감추면 혼동은 남는다.
3. **바꾸지 않는 것과 이유** — 로컬 경로와 package 이름이 옛 이름인 것을 보고 "개명이 덜 됐다"고 판단해 고치는 일을 막는다.

## 핵심 발견

1. **`universal` — 개명의 실제 위험은 URL이 아니라 *정체성 혼동*이다.** 치환할 URL은 한 건도 없었지만(관측 1), 개명이 겨눈 문제(선행 시스템과의 혼동)는 URL 갱신으로 해결되지 않는다. **README에 이력을 능동적으로 적는 것이 개명의 본체이고 remote 갱신은 부수 작업이다.**
2. **`universal` — 이름을 바꾸지 않는 결정에는 각각 다른 이유가 있고, 이유를 적어야 나중에 뒤집히지 않는다.** 로컬 경로(재현 command), package(import 경로), patch 주석(**SHA256 provenance**) 세 가지는 위험의 종류가 다르다. 셋 중 patch가 가장 조용하고 가장 위험하다 — 주석 한 줄을 고치면 40여 개 run의 substrate 검증이 소급해 깨진다.
3. **`universal` — "과거 기록은 수정하지 않는다"는 경계는 디렉터리가 아니라 내용에 긋는다.** `docs/research/`에도 현행 참조 문서가 섞여 있다.
4. **`universal` — 개명은 어휘를 모호하게 만든다.** "저장소"가 두 대상을 가리키게 되므로, 그 단어를 쓰는 기존 문장을 훑어야 한다.

## 해석

- **(해석)** 치환 대상이 0건이었던 것은 운이 아니라 기존 문서 규율의 결과로 보인다. 이 저장소는 재현 command에 **로컬 절대 경로**를 쓰고 GitHub URL은 쓰지 않았다. 그 습관이 개명 비용을 remote 한 줄로 줄였다. **자기 저장소의 원격 URL을 문서에 박지 않는 것이 개명 비용을 낮춘다.**
- **(해석)** 부록 D가 URL 없이 "released with the paper"로만 적혀 있던 것이 이번에는 이점이 됐다 — 개명 전에 URL을 박았다면 논문 원고까지 고쳐야 했다. 다만 그 자리는 여전히 비어 있고, **남은 판정은 주소가 아니라 공개 여부와 시점**임을 `[NEEDS-EVIDENCE]`에 적어 두었다.

## 확인되지 않은 사항

- **GitHub 쪽 상태** (`UNKNOWN`). `fetch`와 `ls-remote`가 신 URL에서 동작함은 확인했으나, 저장소 설명·topic·GitHub Pages 등 **웹 UI 설정**은 이 저장소에서 볼 수 없다. 필요하면 사용자가 확인한다.
- **구 URL redirect의 지속 기간** (`UNKNOWN`). GitHub은 새 저장소가 같은 이름을 차지하지 않는 한 redirect를 유지한다고 문서화하지만, 이 저장소는 이제 redirect에 의존하지 않는다.
- **저장소 공개 방식** (`UNKNOWN`, 이월). 부록 D의 `[NEEDS-EVIDENCE]`.
- 이월된 항목: LaTeX 컴파일 미검증, 그림 육안 검수, 소속 영문 명칭.

## 실패 / 무효 시도

없다.

## 연구 원칙에 미치는 영향

1. **자기 저장소의 원격 URL을 문서에 하드코딩하지 않는다.** 재현 command에는 로컬 절대 경로를 쓴다. 개명·이전 비용이 remote 설정 한 곳으로 줄어든다.
2. **개명할 때는 URL 갱신보다 이력 명시가 본체다.** 특히 개명 이유가 **명칭 충돌**이면, 충돌 상대와 무관함을 저장소 첫 화면에 적는다.
3. **hash로 검증되는 artifact(patch 등)의 본문은 문자열 하나도 고치지 않는다.** provenance가 소급해 깨진다.
4. **"과거 기록 불변" 경계는 내용 단위로 적용한다.**

## 다음 작업

1. **첫 Overleaf 빌드와 그림 육안 검수** ([TASK42](TASK42.md)에서 이월).
2. 저장소 공개 방식 판정 → 부록 D 채우기.
3. 후속 연구 항목은 [INDEX](INDEX.md#후속-연구) — 지시 없이 착수하지 않는다.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `444d9d4`
- Remote: `git remote set-url origin git@github.com:dongkyeomjang/escapement.git`
- 탐색: `grep -rn "dongkyeomjang/continuum-npu" . --exclude-dir=.git`, `grep -rn "continuum-npu" . --exclude-dir=.git`
- 검증: `env -u PYTHONPATH python3 paper/draft/check_claims.py`, `env -u PYTHONPATH python3 paper/figures/verify_figures.py`
- 예산: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
