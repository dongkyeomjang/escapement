# TASK65 — 논문 텍스트의 저장소 제거

## 상태

DONE

## 날짜

2026-09-12

## 목적

논문 집필과 관리는 전적으로 사용자 소관이며, 저장소에는 실험·기록·코드만 남긴다. 저장소 안의 논문 텍스트(CLAIMS 포함)는 사용하지 않기로 확정됐으므로 목록화해 제거한다(Advisor 지시, 사용자 전달, 2026-09-12). 표·그림 산출물과 생성 스크립트, `refs.bib`, 실험 기록·선등록·INDEX·코드·results는 남긴다. 판단이 애매한 파일은 지우지 않고 판단 요청으로 표시한다.

## 배경

관련 TASK:

- [TASK37](TASK37.md)–[TASK46](TASK46.md) — `paper/` 산출물(서사·CLAIMS·초록·related work·본문 초고·LaTeX 패키지·그림)을 만들고 교정했다
- [TASK53](TASK53.md) — 3.1절 표(`table_3_1.md/.tex`)와 생성기. **유지 대상**
- [TASK58](TASK58.md) / [TASK59](TASK59.md) — `paper/` 밖의 논문 문안 `PAPER_3_2.md`·`PAPER_3_3.md`와 근거표 `PROVENANCE_3_2.md`·`EVIDENCE_3_3.md`를 만들었다. 문안은 제거, 근거표는 유지
- [TASK63](TASK63.md) / [TASK64](TASK64.md) — CLAIMS 1.13 기전 문장 재검토를 사용자 결정으로 올렸다. 이번에 파일 제거로 종결

## 시작 상태

- 시작 commit `bf30461`(TASK64), `git status --short`: `?? .idea/`만, `main`은 `origin/main`과 같음
- `paper/` 아래 추적 파일 75개

## 수행 내용

1. **목록화**: `paper/` 추적 파일 75개 전부와 `paper/` 밖의 비-TASK 문서 전부(`docs/` 51개 — `.gitkeep` 포함, 루트 문서 3개)를 머리글·절 제목으로 분류했다. 남길 코드가 지울 파일에 의존하는지 전수 검색했다 — `src/`·`experiments/`·`scripts/`에는 `paper/` 참조가 없고, 그림·표 생성기는 TASK 문서와 `experiments/npu/analysis/padding_ratio.py`만 읽는다.
2. **삭제**: 아래 34개를 `git rm`했다.
3. **유지 확인**: 삭제 뒤 `env -u PYTHONPATH python3 paper/draft/make_table_3_1.py`(`--write` 없이)가 exit 0으로 표를 계산했고, `paper/figures/`의 `svgplot`·`labels_en`·`make_figures`·`verify_figures`가 import된다. `verify_figures.py` 본실행은 추적 파일 `INSPECTION.md`를 다시 쓰므로 하지 않았다.
4. **INDEX/README 갱신**: "논문 텍스트는 이 저장소에 포함되지 않으며 별도 관리된다" 한 줄(README 머리, INDEX 현재 상태). INDEX의 CLAIMS 1.13 결정을 "해당 파일 제거로 종결(문안은 사용자 원고에서 관리)"로 닫고 미해결 결정 수를 4 → 3으로 고쳤다. **원고 조립 경로가 사라져 사실과 달라진 INDEX 문장 2곳**("남은 것은 첫 Overleaf 빌드…", 다음 권장 작업의 `make_package.sh` 절차)을 고쳤다. INDEX 안에서 제거 파일을 가리키던 링크 12개는 링크 표기만 벗겨 일반 텍스트로 바꿨다(남은 제거 파일 링크 0).

## 변경된 파일

- 삭제 34개 (아래 표)
- `docs/research/TASK65.md` (신규), `docs/research/INDEX.md` (갱신), `README.md` (한 단락 추가)

TASK 기록, 선등록 문서, 근거표, 코드, 표·그림 산출물, results는 수정하지 않았다.

## 실험 또는 검증 방법

```bash
git ls-files paper                                     # 목록화 (75)
git rm <아래 34개>
env -u PYTHONPATH python3 paper/draft/make_table_3_1.py   # --write 없이, exit 0
cd paper/figures && env -u PYTHONPATH python3 -c "import svgplot, labels_en, make_figures, verify_figures"
git diff --check; git diff --cached --check
```

측정 없음. `requested_condition` / `observed_condition` / `condition_reached`는 해당 없음.

## 결과

### 삭제 목록 (34개, 246,783 B)

| 분류 | 파일 |
|---|---|
| 초록·CLAIMS·서론·개요·related work (6) | `paper/ABSTRACT.md`, `paper/abstract_arxiv.txt`, `paper/CLAIMS.md`, `paper/INTRO.md`, `paper/OUTLINE.md`, `paper/RELATED.md` |
| 원고 md (11) | `paper/draft/01_introduction.md`, `02_background.md`, `03_mechanisms.md`, `04_simulator.md`, `05_impossibility.md`, `06_prescription.md`, `07_generality.md`, `08_related.md`, `09_limitations.md`, `10_conclusion.md`, `11_appendices.md` |
| 원고 관리 문서 (2) | `paper/draft/NEEDS_EVIDENCE.md`(근거 미비 목록), `paper/draft/README.md`(집필 규칙·절 구성) |
| 원고 tex (13) | `paper/latex/main.tex`(문서 골격·제목·저자 블록·감사의 글·AI 고지), `paper/latex/sections/00_abstract.tex`, `01_introduction.tex`, `02_background.tex`, `03_mechanisms.tex`, `04_simulator.tex`, `05_impossibility.tex`, `06_prescription.tex`, `07_generality.tex`, `08_related.tex`, `09_limitations.tex`, `10_conclusion.tex`, `11_appendices.tex` |
| `paper/` 밖 논문 문안 (2) | `docs/research/PAPER_3_2.md`("논문 3.2용 문장·표·주석"), `docs/research/PAPER_3_3.md`("논문 3.3 수정 문장과 부록 1·2") |

**복원 가능**: 삭제는 git 이력에 남는다. 제거 직전 commit `bf30461`(= 이 TASK commit의 부모)에 34개가 모두 있으며, 필요하면 `git checkout bf30461 -- <경로>`로 되살린다. `PAPER_3_2.md`·`PAPER_3_3.md`의 표에 실린 수치는 근거표(`PROVENANCE_3_2.md`, `EVIDENCE_3_3.md`)와 원 TASK([TASK58](TASK58.md), [TASK59](TASK59.md))에도 있다.

### 유지 확인

| 지시문 유지 항목 | 이 저장소의 해당 파일 | 상태 |
|---|---|---|
| 표 산출물과 생성 스크립트 | `paper/draft/table_3_1.md`, `table_3_1.tex`, `make_table_3_1.py` | 유지, 생성기 실행 exit 0 |
| `refs.bib` | `paper/latex/refs.bib` | 유지 |
| 그림 산출물과 생성 스크립트 | `paper/figures/*.svg` 9, `en/*.svg` 9, `pdf/*.pdf` 9, `make_figures.py`, `labels_en.py`, `svgplot.py`, `verify_figures.py`, `SOURCES.md`(값↔출처 사상), `INSPECTION.md`(`verify_figures.py`가 생성하는 검수표) | 유지, 모듈 import 확인 |
| 실험 기록·선등록·INDEX | `docs/research/TASK*.md`, `*_PREREG.md`·`*_PLAN.md`, `INDEX.md`, `TASK_GUIDE.md`, `KNOWN_PITFALLS.md`, `ENVIRONMENT.md` 등 | 유지(INDEX만 갱신) |
| 근거·출처 기록 | `PROVENANCE_3_2.md`, `EVIDENCE_3_3.md`, `TABLE_3_1_PROVENANCE.md`, `PADDING_RATIO.md`, `CHANNEL_TOLERANCE_SENSITIVITY.md`, `EXECUTION_MODEL_TERMS.md` | 유지 — 논문 문장이 아니라 TASK의 근거표·계산 결과·문헌 조사 기록이다 |
| 코드, results | `src/`, `experiments/`, `scripts/`, `patches/`, `results/` | 유지 |

삭제 뒤 `paper/`에는 41개가 남는다(아래 판단 요청 6개 포함).

### 판단 요청 (삭제하지 않음, 6개)

| 파일 | 내용 | 애매한 이유 |
|---|---|---|
| `paper/ARXIV_CHECKLIST.md` | arXiv 제출 점검표 — 카테고리, 라이선스(CC BY 4.0) 확정, 저자 표기 확정, 초록 형식, 제출 순서, **AI 사용 고지 초안(§7)** | 논문 관리 문서이고 산문(AI 고지 초안)이 들어 있으나, 사용자 확정 사항의 기록이기도 하며 INDEX가 여러 곳에서 참조한다 |
| `paper/VENUES.md` | 투고 타깃 조사(2026-08-24) | 논문 관리 문서이나 원고 텍스트는 아니다 |
| `paper/draft/check_claims.py` | 원고의 `CLAIMS` 주석과 `CLAIMS.md`를 대조하는 검사기 | 코드이지만 읽는 대상(`CLAIMS.md`, 원고 md)이 전부 제거돼 **실행 대상이 없다** |
| `paper/latex/md2tex.py` | 원고 md → `sections/*.tex` 이송기 | 코드이지만 입력(`paper/draft/[0-9]*.md`, `abstract_arxiv.txt`)이 제거됐다 |
| `paper/latex/make_package.sh` | 그림 PDF 복사와 `main.tex`·`sections/`·`refs.bib` 청결 검사, Overleaf용 zip 안내 | 코드이지만 조립 대상(`main.tex`, `sections/`)이 제거됐다 |
| `paper/latex/README.md` | LaTeX 패키지 설명서 | 원고 도구의 설명서라 위 세 도구의 처분을 따르는 것이 자연스럽다 |

### 제거 파일을 가리키는 링크·참조 (수정하지 않음)

제거 직전 commit `bf30461`에서 열린다.

| 위치 | 대상 |
|---|---|
| TASK 기록 13개: [TASK37](TASK37.md), [TASK38](TASK38.md), [TASK39](TASK39.md), [TASK40](TASK40.md), [TASK41](TASK41.md), [TASK42](TASK42.md), [TASK43](TASK43.md), [TASK44](TASK44.md), [TASK46](TASK46.md), [TASK48](TASK48.md), [TASK51](TASK51.md), [TASK63](TASK63.md), [TASK64](TASK64.md) | `CLAIMS.md`, 원고 md·tex, `ABSTRACT.md`, `OUTLINE.md`, `RELATED.md`, `PAPER_3_*.md` 등 — 기록이므로 원문 그대로 둔다 |
| [ENVIRONMENT.md](ENVIRONMENT.md) 295·314·315·324행 | `paper/draft/02_background.md`, `01_introduction.md`, `09_limitations.md`의 줄 인용 |
| [PROVENANCE_3_2.md](PROVENANCE_3_2.md) 3행 | `PAPER_3_2.md` |
| [LAYER_AUDIT_PLAN.md](LAYER_AUDIT_PLAN.md) 128행, [OBSERVATION_AUDIT_PLAN.md](OBSERVATION_AUDIT_PLAN.md) 174행 | `PAPER_3_2.md`, `PAPER_3_3.md`(링크 아닌 파일명) |
| [TABLE_3_1_PROVENANCE.md](TABLE_3_1_PROVENANCE.md) 127행, `paper/draft/make_table_3_1.py` 163행, `paper/draft/table_3_1.tex` 1행 | `main.tex`(주석·서술 속 이름) |
| 판단 요청 6개 | `main.tex`, `sections/`, `RELATED.md`, `OUTLINE.md`, `CLAIMS.md`, 원고 md, `abstract_arxiv.txt` |
| INDEX | **링크 12개를 일반 텍스트로 바꿨다**(남은 제거 파일 링크 0) |

## 핵심 발견

연구 발견 없음 — 저장소 범위를 조정한 작업이다. 기록할 사실만 적는다.

1. **`universal`** — **표·그림 생성 경로는 원고에 의존하지 않았다.** 원고 34개를 지운 뒤에도 표 생성기가 실행되고 그림 모듈이 import된다. 산출물이 원고가 아니라 TASK 기록과 분석 코드에서 값을 읽도록 만들어 둔 구조([TASK38](TASK38.md)의 자동 대조, [TASK53](TASK53.md)의 import 재사용)가 이 분리를 가능하게 했다. 방법론의 문제이므로 substrate와 무관하다.

## 해석

- 원고 전용 도구 3개와 그 설명서(판단 요청 4건)는 코드로서 남아 있지만 입력이 사라져 실행할 대상이 없다. 처분은 사용자 판단이다.
- CLAIMS 1.13 결정은 파일이 없어져 종결됐으나, 그 결정의 근거가 된 관측([TASK63](TASK63.md) 회수 14/14 dummy 경로, [TASK64](TASK64.md) 연속 admission의 admission 경로 회수 5/5)은 기록으로 남는다. 사용자 원고에서 해당 문장을 다룰 때 참조할 수 있다.

## 확인되지 않은 사항

- `verify_figures.py`·`make_figures.py`의 **본실행**은 추적 파일(`INSPECTION.md`, `SOURCES.md`, 그림)을 다시 쓰므로 하지 않았다. import만 확인했다.
- `.gitignore` 26–27행(`paper/latex/figures/`, `make_package.sh` 산출물)은 판단 요청 도구의 처분에 따라 남길지가 정해진다. 이번에는 건드리지 않았다.

## 실패 / 무효 시도

- 목록화 보고 중간에 삭제 대상을 "35개"라고 적었다가 셈을 다시 해 **34개**로 바로잡았다(6 + 11 + 2 + 1 + 12 + 2). 삭제 전 파일 목록으로 대조했으므로 실제 삭제에는 영향이 없다.

## 연구 원칙에 미치는 영향

1. **저장소 범위**: 논문 텍스트는 이 저장소에 두지 않는다. TASK는 논문 문장을 만들지 않고, 필요한 경우 근거표·수치·출처만 기록한다.
2. **기록 문서의 링크는 고치지 않는다.** 제거된 파일을 가리키는 TASK 기록의 링크는 제거 직전 commit에서 열리며, 진입점 문서(INDEX)만 깨진 링크가 없게 정리한다.

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **판단 요청 6건 처분** — 제출 점검표·투고 조사·원고 전용 도구 4건.
2. 도구를 지우기로 하면 `.gitignore` 26–27행도 함께 정리한다.

## 재현 정보

- 시작 commit: `bf30461`(제거 직전, 34개 전부 포함)
- 삭제 명령: `git rm` 34개(위 목록), 합계 246,783 B(`git cat-file -s`)
- 복원: `git checkout bf30461 -- <경로>`
- 유지 확인: 위 「실험 또는 검증 방법」
- 선등록 commit: 해당 없음(측정 없음)
