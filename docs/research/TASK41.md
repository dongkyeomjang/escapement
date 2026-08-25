# TASK41 — TASK40의 논문 반영, 본문 초고 완결, LaTeX 이식 패키지

## 상태

DONE

측정 없음. 그림 ⑨를 두 패널로 개편해 "포화점 = 생존율 100 % 도달점"이 읽히게 만들고, 본문 초고 10절을 완성했으며, IEEEtran 기반 LaTeX 패키지를 만들었다. **제출은 하지 않았고 저자란·감사의 글은 placeholder다.**

## 판정

측정이 없으므로 선등록·판정 기준이 없다.

| 항목 | 결과 |
|---|---|
| 그림 ⑨ 개편 | 2패널(device time / 생존율) + 채널 B 병기 + sim 점선 + KV 한계 외삽선. **수치 대조 177/177, 불일치 0** |
| CLAIMS 추가 | 포화 법칙(`class`)·위치(`stack`)·최적 B(`stack`)·음성 예측(`universal`) **4항목**, 위험 표 **3항목** |
| 알려진 함정 | [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 신규 **5종**, [AGENTS.md](../../AGENTS.md)에서 참조 |
| 본문 초고 | [paper/draft/](../../paper/draft/) **10/10 절 완성** |
| CLAIMS 인용 검증 | **46/46 인용, 존재하지 않는 id 0, 인용되지 않은 주장 0** |
| `[NEEDS-EVIDENCE]` | **3건 잔존** (전부 "근거는 있으나 배치 미정") |
| LaTeX | [paper/latex/](../../paper/latex/) — main·11절·BibTeX 18항목·이송기·패키징 script·README |
| 제출 | **하지 않음.** 저자란 `TBD`, 감사의 글 주석 |

## 날짜

2026-08-25

## 목적

[TASK40](TASK40.md)의 포화 곡선을 논문 자산으로 옮기고, [TASK37](TASK37.md)–[TASK39](TASK39.md)이 만든 뼈대 위에 **본문 초고를 완결**한 뒤, 교수 승인 후 바로 컴파일할 수 있는 LaTeX 패키지로 포장한다.

## 배경

관련 TASK: [TASK40](TASK40.md)(포화 곡선), [TASK37](TASK37.md)(서사·주장 매핑·그림), [TASK38](TASK38.md)(서지 정정·검수 자동화), [TASK39](TASK39.md)(초록·PDF 백엔드), [TASK36](TASK36.md)(잔량 법칙), [TASK06](TASK06.md)·[TASK09](TASK09.md)·[TASK10](TASK10.md)·[TASK17](TASK17.md)·[TASK23](TASK23.md)(함정 목록의 출처).

### 지시문 전제와 저장소 상태의 불일치 (작업 전 확인)

지시문은 "직전 배치의 집필 규칙 전부 유지", "절 구성 ①~⑩ 그대로", "`[SWEEP-PENDING]` 자리는 작업 1의 결과로 채운다"고 적었으나, **이 저장소에 `paper/draft/`도 `[SWEEP-PENDING]` 표식도 존재한 적이 없다.** 해당 배치는 실행되지 않았다.

지시문 본문이 규칙을 완전히 명시하고 있으므로(CLAIMS id 주석, `stack` 조건 병기, 신규 주장 금지, `[NEEDS-EVIDENCE]` 목록화) **그 규칙을 적용해 초고를 새로 만들었다.** 절 구성 ①~⑩은 [OUTLINE.md](../../paper/OUTLINE.md)의 3막 구조에서 도출했고, 지시문이 지목한 §6(처방)·§9(한계)와 일치한다. `[SWEEP-PENDING]` 자리는 §6.5로 신설해 [TASK40](TASK40.md) 결과를 넣었다.

## 시작 상태

- Base commit: `44289a6` ([TASK40](TASK40.md))
- 측정 없음. serving 기동 0회, 재compile 0회, device 접근 0회, 설치 0건
- TeX 미설치 — 지시문이 "texlive 설치는 하지 않고 Overleaf 컴파일 전제"로 범위를 정했다

## 수행 내용

1. 그림 ⑨를 2패널로 다시 만들고 검수기를 확장했다.
2. [CLAIMS.md](../../paper/CLAIMS.md)에 포화 관련 4항목과 오독 위험 3항목을 넣고, 한계 절의 "batch > 16 미검증"을 해소로 갱신했다.
3. [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md)를 신설하고 [AGENTS.md](../../AGENTS.md)에서 참조하게 했다.
4. [paper/draft/](../../paper/draft/)에 10절 초고와 집필 규칙, 검증기, `[NEEDS-EVIDENCE]` 목록을 만들었다.
5. [paper/latex/](../../paper/latex/)에 IEEEtran 소스·BibTeX·이송기·패키징 script·README를 만들었다.

## 변경된 파일

- `paper/figures/make_figures.py`·`labels_en.py`·`verify_figures.py`, `fig9_*`(국문 SVG·영문 SVG·PDF), `INSPECTION.md`
- `paper/CLAIMS.md`, `paper/figures/SOURCES.md`
- `docs/research/KNOWN_PITFALLS.md`(신규), `AGENTS.md`
- `paper/draft/`(신규 13파일), `paper/latex/`(신규 15파일), `.gitignore`
- `docs/research/TASK41.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음. 검증은 전부 기계적이다.

- **그림**: `verify_figures.py`가 데이터 상수를 원 TASK·선등록 문서에서 **독립적으로 다시 파싱**해 대조하고, 영문 넘침과 PDF 구조·변환 손실을 검사한다.
- **초고**: `check_claims.py`가 (i) 인용된 CLAIMS id의 존재, (ii) 인용되지 않은 주장, (iii) `[NEEDS-EVIDENCE]` 목록을 낸다.
- **LaTeX**: 중괄호 균형과 이스케이프되지 않은 `%`를 검사했다. **컴파일은 하지 못했다.**
- 링크: 새·수정 문서의 상대 링크 전건 확인.

## 결과

### 관측 1 — 그림 ⑨가 두 패널로 기전을 보인다

위 패널이 device time ratio(채널 A′ 실선·채운 표식, 채널 B 속 빈 표식, sim 점선), 아래 패널이 층 2 생존율이다. 두 패널을 세로로 겹치면 **곡선이 평평해지는 B와 생존율이 100 %에 닿는 B가 같은 자리**임이 보인다.

- `B = 46`에 **KV 한계 외삽선**을 세로 점선으로 넣고 "외삽"이라 표기했다. 데이터 구간(8–32)이 축의 왼쪽 절반을 차지하므로 **"이득은 한계의 3분의 1에서 끝난다"가 거리로 읽힌다.**
- N=10의 B=16 점만 붉은 원으로 강조했다 — 생존율 28/30으로 유일하게 포화 미달인 지점이고, 위 패널에서 유일하게 B24가 더 주는 지점이다. **두 패널의 예외가 같은 x에 있다.**

검수: **수치 대조 177/177 일치**(그림 ⑨분 39항목 추가 — sim 9, 채널 A′ 9, 채널 B 9, 생존율 12), 영문 넘침 0, PDF 9/9 구조 정상·변환 손실 0.

### 관측 2 — 포화 주장의 층 분리

지시문이 요구한 대로 **형태와 위치를 다른 주장으로 갈랐다.**

| id | 주장 | 층 | 조건 |
|---|---|---|---|
| 3.10 | 이득은 회수 가능한 캐시 손실의 잔량에 비례하고, 생존이 포화하면 끝난다 | **`class`** | 수치 금지. **3회 재현**([TASK35](TASK35.md)/[TASK36](TASK36.md)/[TASK40](TASK40.md)) |
| 3.11 | 이 워크로드에서 그 포화 지점은 **B=16** | **`stack`** | 눈금 고정·N ≤ 10·현실 워크로드. N > 16 미측정 |
| 3.12 | 최상위 눈금 미사용이 포화를 **무해**하게 만든다 | **`class`** | 수치 금지(0.0 %는 `stack`) |
| 3.13 | 최적 B는 HW 상한이 아니라 **분포의 함수** | **`stack`** | B ≈ 46은 3점 적합의 **외삽** |
| 3.14 | 무보정 sim이 **효과 없음**을 미리 맞혔다 | **`universal`** | 예측은 측정 전 commit |

3.10을 `class` 후보로 세운 근거는 지시문이 지정한 **3회 재현**이다 — 잔량이 컸을 때(+9.7 %), 없었을 때(밴드 안), 2건 남았을 때(+2 %).

### 관측 3 — 함정 5종의 재발 횟수

| # | 함정 | 발생 | 대가 |
|---|---|---|---|
| 1 | 상대 경로 × 임시 디렉터리 실행기 | [TASK06](TASK06.md), [TASK40](TASK40.md) | lifecycle 4회 |
| 2 | pattern 기반 process 종료·확인 | [TASK09](TASK09.md), [TASK10](TASK10.md), [TASK23](TASK23.md) | **6개 조합 연쇄 붕괴** |
| 3 | 동시 실행 중 counter 증분 per-request 귀속 | [TASK17](TASK17.md) | 관측 무효 |
| 4 | 따옴표 없는 heredoc 치환 | [TASK40](TASK40.md) | lifecycle 2회 |
| 5 | 실행 중인 실험의 script 편집 | [TASK23](TASK23.md), [TASK34](TASK34.md) | server 누수 → 연쇄 |

**지시문이 지목한 4종에 5번을 더했다** — 2회 발생했고 [TASK23](TASK23.md)에서 연쇄 붕괴를 일으켰으며 이후 모든 선등록의 실행 절차에 같은 문장이 반복되고 있어, 목록의 추가 기준("2회 이상 또는 측정 무효화")을 충족한다.

### 관측 4 — 초고 10절과 인용 검증

| 절 | 파일 | 상태 | 비고 |
|---|---|---|---|
| ① Introduction | `01_introduction.md` | 완 | [INTRO.md](../../paper/INTRO.md) §4 완고를 포지셔닝 절로 통합 |
| ② Background | `02_background.md` | 완 | `[NEEDS-EVIDENCE]` 1 |
| ③ Mechanisms | `03_mechanisms.md` | 완 | 기전 3개 + 왜 곱해지는가 |
| ④ Simulator | `04_simulator.md` | 완 | `[NEEDS-EVIDENCE]` 2 |
| ⑤ Impossibility | `05_impossibility.md` | 완 | 벽 3개 + 방법론 경고 |
| ⑥ Prescription | `06_prescription.md` | 완 | **§6.5에 포화 곡선**([TASK40](TASK40.md)) |
| ⑦ Generality | `07_generality.md` | 완 | 절제·GPU source·방법론 이식 |
| ⑧ Related | `08_related.md` | 완 | 레버 분류학 + 최근접 선행 |
| ⑨ Limitations | `09_limitations.md` | 완 | **N > 16·눈금 24/32 미측정 명시** |
| ⑩ Conclusion | `10_conclusion.md` | 완 | — |

`check_claims.py`: **CLAIMS 46항목 전부 인용, 존재하지 않는 id 0, 인용되지 않은 주장 0.**

### 관측 5 — 이송기가 옮기는 것과 못 옮기는 것

마크다운 → LaTeX 이송에서 기계적으로 처리한 것: 제목·강조·코드, `<!-- CLAIMS -->`를 **LaTeX 주석으로 보존**(근거 추적이 원고까지 따라간다), 파이프 표 → `tabular`, `**Figure ⑨.**` → `figure` 환경, 원문자·`§` → `\ref{sec:NN}`, 비-ASCII 기호 → 수식.

**옮기지 못한 것**: 표 캡션(전부 `TODO`), 그림 배치, `\cite` 삽입 — §⑧이 arXiv id를 본문에 적고 있어 교정 단계에서 BibTeX 키로 바꿔야 한다.

문장 중간의 HTML 주석을 그대로 두면 LaTeX 주석이 **문장 나머지를 삼키므로**, 문장에서 떼어내 다음 줄에 `% CLAIMS x.y`로 재배치했다. 목록 항목과 표 칸에서도 같은 처리가 필요했다.

## 핵심 발견

1. **`universal` — 근거 추적은 원고까지 따라갈 수 있고, 따라가게 만들어야 한다.** CLAIMS id를 마크다운 주석으로 달고 이송기가 그것을 LaTeX 주석으로 옮기면, 최종 원고의 어느 문장이든 근거 TASK로 되짚을 수 있다. **인용 검증이 기계적이 되면 "주장 표는 만들었는데 본문이 안 따른다"가 불가능해진다.**
2. **`universal` — "인용되지 않은 주장"이 "존재하지 않는 id"만큼 중요하다.** 전자는 주장 표의 사장 항목이거나 본문의 누락이다. 이번에는 46/46이 인용돼 둘 다 아니었지만, **검사에 넣지 않았다면 알 수 없었다.**
3. **`universal` — 함정 목록은 발생 횟수와 대가를 함께 적어야 읽힌다.** 규칙만 적힌 목록은 읽히지 않는다. "6개 조합이 연쇄로 무너졌다"가 붙으면 읽힌다.
4. **`universal` — 2패널 그림이 기전을 주장이 아니라 배치로 말한다.** 생존율 패널을 device time 패널 **바로 아래** 같은 x축에 두면 "포화점 = 생존 100 % 도달점"을 문장으로 주장할 필요가 없어진다. 예외(N=10 B=16)가 두 패널에서 같은 x에 있는 것도 마찬가지다.

## 해석

- **(해석)** 지시문이 전제한 "직전 배치"가 없었다는 점은 기록해 둘 값어치가 있다. **지시문의 전제와 저장소 상태가 어긋날 때 기본 동작은 "전제를 확인하고 보고한 뒤 명시된 규칙으로 진행"** 이다. 이번에는 규칙이 지시문에 전부 적혀 있어 진행에 지장이 없었으나, 규칙이 "직전 배치 참조"로만 돼 있었다면 진행할 수 없었을 것이다.
- **(해석)** `[NEEDS-EVIDENCE]` 3건이 모두 "근거는 있는데 배치가 미정"인 것은 우연이 아니라 규칙의 결과다. **신규 주장 금지 규칙이 있으면 "근거 없는 문장"이 애초에 생기지 않고**, 남는 것은 배치 판정뿐이다.
- **(해석)** LaTeX가 컴파일된 적이 없다는 것은 이 패키지의 실질적 위험이다. 중괄호 균형과 이스케이프는 검사했지만, IEEEtran 특유의 제약(표 폭, `\columnwidth` 그림, 참고문헌 스타일)은 첫 빌드에서만 드러난다. **첫 Overleaf 빌드를 "검증"이 아니라 "첫 시험"으로 예고해 두었다.**

## 확인되지 않은 사항

- **LaTeX 컴파일** (`UNKNOWN`). TeX 미설치. 첫 Overleaf 빌드가 첫 검증이다.
- **그림의 시각적 품질** (`UNKNOWN`, 이월). 겹침·잘림은 육안으로만 확인된다. 그림 ⑨는 2패널이라 이전보다 확인 필요가 크다.
- **`[NEEDS-EVIDENCE]` 3건의 배치** — Advisor 첨삭 판정 대기. 목록은 [NEEDS_EVIDENCE.md](../../paper/draft/NEEDS_EVIDENCE.md).
- **서지 일부의 저자 전체 목록** (`PARTIAL`). `refs.bib`에 `TODO`로 표시.
- **저자란·소속·감사의 글·AI 고지 문구** (`UNKNOWN`). 교수 승인 전 채우지 않는다.

## 실패 / 무효 시도

없다. 다만 이송기를 만들며 **세 번 고쳤다**: 문장 중간 HTML 주석이 LaTeX 주석으로 바뀌며 나머지를 삼킨 것, `Section~`의 tilde가 이스케이프된 것, 목록·표 칸의 주석이 남은 것. 셋 다 생성물 검사로 잡았고 측정과 무관하다.

## 연구 원칙에 미치는 영향

1. **원고의 모든 주장 문장에 근거 id를 달고, 그 관계를 기계적으로 검사한다.** 검사에는 "존재하지 않는 id"와 **"인용되지 않은 주장"** 을 모두 넣는다.
2. **재발한 함정은 [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md)에 발생 횟수·대가와 함께 모으고, 새 실행 script를 쓰기 전에 읽는다.**
3. **지시문의 전제가 저장소 상태와 어긋나면 확인하고 보고한 뒤, 명시된 규칙으로 진행한다.** 없는 것을 있다고 가정하지 않는다.
4. **컴파일·렌더링이 불가능한 환경에서 만든 산출물은 "미검증"을 산출물 안에 적는다.** README 1항이 그것이다.

## 다음 작업

1. **Advisor 첨삭** — 초고 10절과 `[NEEDS-EVIDENCE]` 3건 판정.
2. **첫 Overleaf 빌드** — 오류 수정 후 이송기 사용 중단 시점을 README에 기록.
3. 교수 승인 후 저자란·감사의 글·AI 고지 확정. **그 전에는 제출하지 않는다.**
4. 후속 연구 항목([INDEX.md](INDEX.md#후속-연구))은 지시 없이 착수하지 않는다.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `44289a6`
- 그림: `env -u PYTHONPATH python3 paper/figures/make_figures.py` → 국문 SVG 9 + 영문 SVG 9 + PDF 9
- 검수: `env -u PYTHONPATH python3 paper/figures/verify_figures.py` → **177 checks, 0 mismatches**, 넘침 0, pdf 9/9
- 초고 검증: `env -u PYTHONPATH python3 paper/draft/check_claims.py` → **46/46, 미존재 0, 미인용 0, NEEDS-EVIDENCE 3**
- LaTeX 생성: `env -u PYTHONPATH python3 paper/latex/md2tex.py` → `sections/` 11파일
- Overleaf 패키징: `bash paper/latex/make_package.sh`
- 예산: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
