# TASK46 — 제출 준비 최종 교정

## 상태

DONE

측정 없음(기존 artifact 재분석 1건 포함). Blocker 2건, Major 11건, Minor·Nit 전항을 반영하고 기각 3건의 근거를 기록했다. **완료 기준 3종 중 2종을 소스에서 확인**했고 하나(렌더링 PDF)는 컴파일 불가로 미확인이다.

## 판정

| 완료 기준 | 결과 |
|---|---|
| `TODO` = 0 | **소스 TODO 1건** — `main.tex`의 저자 소속 확인 항목이며 **`%` 주석이라 PDF에 렌더되지 않는다.** `refs.bib`는 0 |
| `TASK` = 0 | **0** (TeX·bib·그림 SVG·그림 PDF 텍스트 레이어) |
| 미참조 그림·표 = 0 | **0** — 라벨 12개(그림 9 + 표 3) 전부 본문에서 참조 |
| 그림 겹침 | **0** (신규 해석적 검출) |
| 수치 대조 | **177/177** |
| 인용 검증 | **50/50**, 미존재 0, 미인용 0 |
| 패키지 청결 | TASK 0 · ASCII 전용 · CLAIMS 주석 103개 유지 |

## 날짜

2026-08-25

## 목적

투고 직전 교정을 한 배치로 마감한다. 이 지시문은 앞선 "교정 배치 1"과 "TASK 표기 제거" 지시문을 포함·대체하므로, 이미 [TASK44](TASK44.md)·[TASK45](TASK45.md)에서 반영된 항목은 확인만 하고 건너뛰었다.

## 배경

관련 TASK: [TASK41](TASK41.md)–[TASK45](TASK45.md)(원고·이송기·검수), [TASK35](TASK35.md)·[TASK36](TASK36.md)·[TASK40](TASK40.md)(꼬리 지연 재분석의 자료), [TASK27](TASK27.md)·[TASK28](TASK28.md)(2×2의 centralized-causal 칸), [TASK42](TASK42.md)(Inferentia·Gaudi 확인분).

## 시작 상태

- Base commit: `75fa4ff` ([TASK45](TASK45.md))
- 새 측정 없음. serving 기동 0회, device 접근 0회, 설치 0건
- 이미 반영돼 건너뛴 것: **B10**(TASK 표기 제거, [TASK45](TASK45.md)에서 0건 확인), **B11**(외부 검토 수용분·빌드 수정, [TASK44](TASK44.md))

## 수행 내용

블록별로 A → B → C 순서로 반영하고, 각 단계마다 `check_claims`·`verify_figures`·패키지 검사를 재실행했다.

## 변경된 파일

- `paper/abstract_arxiv.txt`, `paper/ABSTRACT.md`, `paper/CLAIMS.md`
- `paper/draft/` 9개 파일, `paper/latex/refs.bib`, `paper/latex/md2tex.py`, `paper/latex/sections/*.tex`(12)
- `paper/figures/make_figures.py`, `svgplot.py`, `labels_en.py`, `verify_figures.py`, SVG·PDF 27개, `INSPECTION.md`
- `experiments/npu/analysis/tail_latency.py`(신규)
- `docs/research/TASK46.md`(신규), `docs/research/INDEX.md`

## 결과

### A1 — refs.bib 전면 완결

19항목 전부를 1차 출처(arXiv abs 또는 출판사 페이지)로 확인해 **저자 전체 목록을 채웠다.** 새로 확인한 4건: KVFlow 9인(NeurIPS 2025 정식 서지로 전환), SAGA 3인, Autellix 11인, Sarathi-Serve 8인(OSDI '24, 쪽수 포함).

작업 메모를 전부 제거했다 — `TODO`, `Same system as`, 개명 이력, ICML 등재 등급 유보. cachescout 두 편의 동일 시스템 관계는 **§VIII 본문 서술로만** 남는다.

**한 건은 남겼다**: KV-RM의 `note = {Withdrawn by the authors}`. 이것은 작업 메모가 아니라 **인용 대상의 출판 상태**이며, 철회된 논문을 그 사실 없이 인용하는 것이 오히려 문제다. `grep -ci todo`에도 걸리지 않는다.

Inferentia·Gaudi 벤더 문서를 서지 항목으로 추가해 §I의 클래스 선언이 `\cite`를 갖게 했다.

### A2 — 초록 전면 재작성

**277단어 → 248단어**(1,706자, ASCII, 3문단). 지시된 요소를 전부 반영했다.

| 요구 | 반영 |
|---|---|
| 첫 문장 when-절 수리 | "the timing of a session's return from a tool call sets its serving cost" |
| "four more orders" 어순 | "a margin that four additional orders of magnitude in sample size do not close" |
| Escapement 명시 | "Escapement selects one compile-time configuration from …" |
| "We establish the first of these causally" | 반영 |
| "prediction gate" | "preregistered out-of-sample prediction gate" |
| 명령문 → 조건문 | "if every session is given omniscient knowledge yet decides independently, that share disappears" |
| 7분 → 8분 | "an eight-minute recompile" |

**뺀 것 하나**: 기존 마지막 문장("Some levers can be bought with a distribution…")을 250단어 상한 때문에 뺐다. 그 문장은 §X 결론과 전체판 초록에 남아 있다. **조건 병기(median, at eight concurrent sessions, on two independently registered channels)는 한 글자도 줄이지 않았다.**

### B1 — 그림·표 본문 참조

라벨 **12개**(그림 9 + 표 3: gates, twobytwo, tail)를 전부 본문에서 최소 1회 참조한다. 이송기가 자동으로 넣지 않고 **서술 흐름에 맞는 문장에 손으로** 넣었다 — 마크다운 표식 `[[fig:figN]]`·`[[tab:name]]`을 도입하고 이송기가 `Fig.~\ref{}`·`Table~\ref{}`로 옮긴다. 표에는 `TABLELABEL` 표식으로 `\label`을 붙였다.

### B2·B3 — 8분 통일과 Escapement 정의

초록·§I·§X의 "seven-minute"를 **"an eight-minute recompile"** 로 통일했다. §VI-B에만 근거를 남겼다 — 적합식이 6-rung을 **7.9분**으로 놓고 실제로 지은 두 6-rung artifact가 8.1분·7.9분이었으므로 반올림해 8분을 쓴다.

§VI-A 도입부에서 명명한다: **"the zero-fitted-parameter substrate model of Section IV together with the distribution-driven configuration search built on it"**, 그리고 "runtime component가 아니라 compiled artifact를 내고 물러나는 절차"임을 덧붙였다. §VI·§X에서 일관 사용한다.

### B4 — §V 2×2 재구성

`{중앙집중/분산} × {causal/전지}` 표를 §5.2로 신설하고 각 칸이 무엇으로 닫히는지 적었다.

| | causal | 전지 |
|---|---|---|
| **중앙집중** | **실증적으로 닫힘** — 실기기 −105 %·−70 % | **결과로 닫히지 않음** — offline bound 자체이며 예측 불가로 도달 불능 |
| **분산** | **실증적으로 닫힘** — 후보 전부 평균 절감 음수 | **구조적으로 닫힘** — 전지적이어도 독립 결정이면 중앙 60 % 소실 |

**gateway 상위 집합 논증을 명문화했다**([CLAIMS 2.11](../../paper/CLAIMS.md) 신설). 실기기에서 평가한 정책은 세션과 engine 사이 gateway에서 돌았고, 그 위치는 **반환을 언제 방출할지 결정할 권한**을 쥔다. server-side scheduler는 이미 제출된 일의 순서를 정할 뿐이므로 그 권한의 부분집합이다 — **따라서 중앙집중 × causal은 추측이 아니라 실증으로 닫혔다.** 이에 맞춰 [CLAIMS 2.6](../../paper/CLAIMS.md)의 "server scheduler는 열리지 않은 경로" 표현도 고쳤다.

**60 % 방어 1문단**을 §5.4에 넣었다: 60 %는 **집계 device time**에서 나오고, [TASK25](TASK25.md)가 실격시킨 것은 **세션 단위 귀속**이므로 두 축이 다르다. [CLAIMS 2.5](../../paper/CLAIMS.md)에 같은 취지의 scope를 달았다.

### B5 — N=10 exploratory 명시

§VI-E 본문에 문단을 넣고(확증은 동시성 6·8의 6칸에 근거하며 N=10은 제외), **그림 ⑨ 캡션에도 직접** 넣었으며, §IX에 한 줄을 더했다. 지시대로 §IX 언급만으로 그치지 않았다.

### B6 — 꼬리 지연 (신규 분석, 재측정 없음)

기존 run의 per-request JSONL에서 `done_s − sent_s`의 p50/p99를 산출했다([tail_latency.py](../../experiments/npu/analysis/tail_latency.py)).

| run | N | p50 ratio | p99 ratio |
|---|---|---|---|
| 확증([TASK35](TASK35.md)) | 6 | 0.915 | 0.956 |
| 확증([TASK35](TASK35.md)) | 8 | **0.895** | **0.841** |
| 재확증([TASK36](TASK36.md), 신규 seed) | 6 | 0.954 | 0.954 |
| 탐색([TASK35](TASK35.md)) | 10 | 0.937 | **0.716** |
| 포화([TASK40](TASK40.md)) B8→B16 | 8 | 0.911 | 0.847 |
| 포화([TASK40](TASK40.md)) B8→B16 | 10 | 0.891 | 0.724 |

**꼬리가 device time과 같은 방향으로, 그리고 더 크게 움직인다** — 모든 칸에서 p99 ratio가 p50 ratio 이하이고 그 격차가 동시성과 함께 벌어진다. 기전이 설명한다: 꼬리에 있는 요청이 곧 prefix를 재계산해야 했던 요청이고, 구성의 효과가 바로 그 수를 줄이는 것이다.

**두 가지를 명시했다.** 이것은 **선등록되지 않은 사후 관측**이며, per-request 기록이 있는 조합만 다뤘고 **빈 칸을 채우려 재측정하지 않았다.** [CLAIMS 3.15](../../paper/CLAIMS.md)에 그 scope와 함께 넣었다.

**결과가 유리하게 나왔다는 점을 특히 조심해서 적었다** — 유리한 사후 분석일수록 선등록되지 않았다는 사실을 크게 적어야 한다.

### B7 — "zero fitted parameters"의 정의

§IV-A에 정의 문단을 넣었다. 모든 상수는 **상류에서 독립 측정된 component 성질**이며 provenance triple을 달고 부록 A로 연결된다. **시뮬레이터 출력에 맞춰 조정된 파라미터가 0개**라는 것이 이 표현의 뜻이고, 잔차·스케일 인자·워크로드별 보정이 모형 어디에도 없다. prefill 비용식은 회귀이지만 **전용 주입 실험의 회귀**이므로 component-level measurement로 분류하고, 그 분류를 명시해 독자가 이의를 제기할 수 있게 했다([CLAIMS 1.19](../../paper/CLAIMS.md) 신설).

### B8 — trace 출처

§II-D에 문단 둘을 넣었다. 수집 주체(저자 본인의 두 agent front-end 사용), 계측 위치(client), 규모(**665,453 레코드 / 8,058 세션**, 그중 sampler가 쓰는 **43개 도구**, 60 s cap), latency 출처(front-end가 보고하면 wall clock, 아니면 내부 계측 — 분할이 trace에 기록됨). 공개는 **도구별 지속시간 분포**를 내되 원자료는 내지 않으며, 사유는 그것이 저자의 작업 세션 prompt·출력이라 무관한 제3자 자료를 공개하지 않고는 낼 수 없다는 것이다.

### B9 — 그림 겹침, 해석적으로 검출

**모든 글자 위치를 이 프로젝트가 직접 계산하므로 겹침은 눈이 아니라 계산으로 판정할 수 있다.** `svgplot.py`에 `text_boxes()`·`text_collisions()`를 넣어 배치에 쓰는 **같은 폭 표**로 bounding box를 만들고 쌍마다 교차를 본다(회전 라벨 제외).

첫 실행에서 **8건**이 나왔고 전부 실재였다.

| 그림 | 겹침 | 조치 |
|---|---|---|
| ② | 좌상단 주석 × 범례 | 주석을 우상단으로 (`anchor="end"`) |
| ⑤ | 막대 위 비율 라벨 × 범례 | **범례를 축 아래로 외부화**(캔버스 448 → 540, bottom 76 → 160), 하단 주석도 재배치 |
| ⑦ | 같은 model 수 두 점의 GiB 라벨끼리 | 두 번째 라벨을 표식 반대편으로 |
| ⑦ | 모형식 라벨 × 재현 오차 주석 × 범례 | 모형식을 좌하단으로, 주석을 우하단으로 |

재실행 후 **0건**. `verify_figures.py`에 §3으로 상설 편입했다. ⑥의 도구명은 이미 −30° 회전돼 있었고 ⑧에서는 검출되지 않았다.

**남는 한계**: 이 검사는 **글자끼리만** 본다. 글자와 선·표식·막대의 겹침과 전체 가독성은 여전히 눈으로만 확인된다 — [INSPECTION.md](../../paper/figures/INSPECTION.md) 머리에 그렇게 적었다.

### C — Minor·Nit

| 항목 | 조치 |
|---|---|
| 상호참조 파손 `Sections Section V` | **이송기 원인 수정** — `Section` 앞의 선택 접두 패턴이 `Sections`의 복수형을 먹지 못해 이중 접두가 났다. 정규식을 `Sections?`로 고쳤다 |
| Table I 폭 | [TASK44](TASK44.md)에서 열 폭 지정 완료. 이번에 `\label` 추가 |
| "direction 11/11" 정의 | "sign of the arm effect matched in 11/11 grid-by-concurrency cells"로 풀어 썼다 |
| Inferentia/Gaudi `\cite` | 벤더 문서 2건을 서지에 넣고 §I에서 인용 |
| 부록 D repo URL | `github.com/dongkyeomjang/escapement` 명시. 부록 B의 선등록 commit이 같은 저장소를 가리킨다고 연결 |
| §VI-F 모형 의존 | "선택 단계는 model-derived이고, device가 확인한 것은 선택된 구성이 값을 낸다는 것이지 모형이 후보 전체를 옳게 줄 세웠다는 것이 아니다"를 명시 |
| 1.3–1.5 %p 정합 | "at these two cells"를 붙여 §6.4의 +1.52 %p와 충돌하지 않게 했다 |
| §VII chunked 한정 | "model-derived, substrate-conditional"이며 **GPU chunked prefill에 대한 주장이 아니다**(그쪽은 연산 중첩이라 비교가 다르다)를 명시하고 [@sarathi2024]를 붙였다 |
| §IV-E 방어 | "잔차는 확정 비교의 후보 간 격차보다 작고, 상위 후보의 순위는 device 절제로 확인됐다 — 이 크기의 계통 잔차는 크기를 옮기지 그 선택을 뒤집지 않는다" |
| AI 고지 형식 | IEEE 양식에서 `\section*`은 참고문헌 앞 비번호 절로 통상적이며 현재 배치가 그에 맞다. **다만 IEEE의 최신 AI 고지 규정 원문은 확인하지 못했다**(아래 미확인) |

### C-기각 — 반영 금지 3건

지시대로 반영하지 않았고 근거는 [TASK44](TASK44.md)에 이미 기록돼 있다. 요약하면 (i) OCR 잔여 문자열과 (ii) 하이픈 누락은 소스·PDF 텍스트 레이어에 **실재하지 않는** 검토자 추출기의 손실이며, 고치면 실재하는 조판이 깨진다. (iii) #18("pure tax … batching subsidy") 평탄화는 Advisor 판정으로 기각이고 원문을 유지했다 — 다만 §VII에 위 한정 문장을 더해 **주장의 범위**를 좁혔다.

## 핵심 발견

1. **`universal` — 자기 계산으로 배치한 그림은 겹침을 눈이 아니라 계산으로 판정할 수 있다.** 폭 표가 배치와 검사 양쪽의 근거이므로 결과가 일관된다. 첫 실행에서 8건이 나왔고 **전부 실재**였다 — 눈으로 훑었다면 ⑦의 GiB 라벨 두 개(9 s 차이)는 놓쳤을 것이다.
2. **`universal` — 유리하게 나온 사후 분석일수록 선등록되지 않았음을 크게 적는다.** 꼬리 지연은 device time보다 더 좋게 나왔고, 그래서 "선등록되지 않았다 / 재측정하지 않았다"를 문단 안에 두 번 적었다.
3. **`universal` — 2×2로 가르면 "무엇이 닫히지 않았는가"가 한 칸으로 특정된다.** 흩어진 음성 결과 셋이 표 하나에서 세 칸을 채우고, 남은 한 칸이 무엇으로 닫히는지가 그 자리에서 보인다.
4. **`universal` — "보정 파라미터 0개"는 정의를 적기 전까지 검증 불가능한 주장이다.** 무엇이 파라미터로 세어지고 무엇이 component 측정으로 세어지는지를 밝혀야 독자가 동의하거나 반대할 수 있다. prefill 회귀를 분류하고 **그 분류를 드러낸 것**이 그 문단의 핵심이다.

## 해석

- **(해석)** B4의 gateway 논증은 이 연구의 주장 범위를 **넓히는 동시에 좁힌다.** 넓히는 쪽: 중앙집중 causal이 추측이 아니라 실증으로 닫힌다. 좁히는 쪽: 그 논증은 "반환 방출권"이라는 위치 정의에 의존하므로, 방출 시점 자체를 바꿀 수 없는 스케줄러에는 그대로 적용되지만 **더 넓은 권한을 가진 중앙 구성 요소**(예: 세션 생성 자체를 조절하는 것)까지 닫지는 못한다. 표의 칸 이름을 "centralised"로 두되 근거 문장을 방출권으로 한정한 이유다.
- **(해석)** A2에서 뺀 폐지 문장은 이 논문에서 가장 인용되기 쉬운 한 줄이었다. 250단어 상한과 조건 병기 중 어느 쪽도 양보할 수 없어 그것을 뺐고, §X과 전체판 초록에 남겼다. **초록의 기능은 인상이 아니라 요약**이라는 판단이다.
- **(해석)** B9의 검출기는 [TASK41](TASK41.md) 이래 "육안 검수는 사람 몫"이라 적어 온 항목의 절반을 기계로 옮겼다. 남은 절반(글자 대 도형, 전체 가독성)은 여전히 사람 몫이고, 그 경계를 문서에 정확히 적었다.

## 확인되지 않은 사항

- **렌더링 PDF의 `pdftotext` 검사 2종** (`UNKNOWN`) — TeX 미설치. 소스 grep으로 간접 확인했고, `main.tex`에 남은 `TODO` 1건은 **`%` 주석이라 렌더되지 않는다**.
- **글자와 도형의 겹침·전체 가독성** (`UNKNOWN`) — 검출기가 보지 않는다.
- **IEEE의 AI 사용 고지 규정 원문** (`UNKNOWN`) — 현재 배치가 관행에 맞다고 판단했으나 규정 문서를 대조하지 못했다.
- **소속 영문 명칭** (`UNKNOWN`, 이월).
- **trace 배포 형식** (`NEEDS-EVIDENCE` 1건, §II-D) — 도구별 분포를 어떤 형태로 낼지.

## 실패 / 무효 시도

없다. 겹침 수정이 2회 반복됐다 — ⑦의 주석을 옮기자 모형식 라벨과 새로 겹쳐 두 번째 배치가 필요했다. **검출기가 있었기에 두 번째 겹침이 즉시 드러났다.**

## 연구 원칙에 미치는 영향

1. **자기 계산으로 배치한 산출물은 배치 규칙을 검사로도 쓴다.** 같은 상수를 배치와 검증 양쪽에 쓰면 결과가 일관된다.
2. **사후 분석은 유리할수록 그 사실을 크게 적는다.**
3. **"파라미터 0개"류의 방법 주장은 세는 규칙을 함께 적는다.**
4. **논증을 2×2로 가르면 미해결이 한 칸으로 특정된다.**

## 다음 작업

1. **첫 Overleaf 빌드** → `pdftotext main.pdf - | grep -ci todo` 와 `| grep -c TASK` 로 완료 기준 2종 확인.
2. **그림 육안 검수** — 글자 대 도형, 전체 가독성.
3. 이월: 소속 영문 명칭, IEEE AI 고지 규정 대조, trace 배포 형식.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `75fa4ff`
- 꼬리 지연: `env -u PYTHONPATH python3 experiments/npu/analysis/tail_latency.py --run <RUN> --arms BASE,TUNED --sessions 6,8,10`
- 그림: `make_figures.py`(겹침 0), 검수: `verify_figures.py`(177/177), 초고: `check_claims.py`(50/50)
- 패키지: `bash paper/latex/make_package.sh` → TASK 0 · ASCII 전용 · CLAIMS 주석 103
- 예산: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
