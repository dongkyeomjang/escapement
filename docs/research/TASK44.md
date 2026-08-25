# TASK44 — 원고 교정 배치 1: 빌드 수정과 외부 검토 반영

## 상태

DONE

측정 없음. Advisor가 로컬 컴파일에서 검증한 조판 수정 4건과 외부 검토 수용분 18건을 반영하고, 검토 지적 3건을 **근거를 들어 기각**했으며, 서지 3건을 1차 출처로 완결했다.

## 판정

| 항목 | 결과 |
|---|---|
| A. 빌드 수정 | **4/4 반영.** 표 2종에 열 폭 지정 + `\footnotesize`, 긴 `\texttt`에 `\allowbreak`, 부록 B commit 칸 축약 + **각주로 정보 복원** |
| B. 외부 검토 수용 | **18건 반영** (초록 6, §I 6, §III 1, §IV 1, §V 5 — 아래 대조표) |
| C. 기각 | **3건**, 각각 근거 기록 |
| D. 서지 | mori·leyline·smetric **3건 1차 출처로 완결**. 잔여 `TODO` 4건 |
| 초록 길이 | 1,876 → **1,887자** (상한 1,920, 여유 33), 전부 ASCII |
| 검증 | `check_claims` **47/47**, LaTeX 구조 문제 0, 비-ASCII 본문 0, 그림 177/177 |

## 날짜

2026-08-25

## 목적

[TASK42](TASK42.md)의 교정 1차 이후 (i) Advisor가 로컬 컴파일에서 확인한 조판 결함과 (ii) 외부 검토 의견을 반영한다. **컴파일 검증을 이 host에서 할 수 없으므로 Advisor의 검증 결과를 그대로 받아 적용하되, 조판 수정을 일회성 손질이 아니라 이송기가 재생성 가능한 형태로 넣는다.**

## 배경

관련 TASK: [TASK41](TASK41.md)(초고·이송기), [TASK42](TASK42.md)(교정 1차·저자 확정), [TASK38](TASK38.md)(서지 1차 출처 확인 원칙).

## 시작 상태

- Base commit: `3100119` ([TASK43](TASK43.md))
- 측정 없음. serving 기동 0회, device 접근 0회, 설치 0건
- TeX 미설치 — **이 TASK도 컴파일로 확인하지 못했다**

## 수행 내용

1. 조판 수정 4건을 **마크다운 표식 + 이송기 규칙**으로 구현했다(아래 관측 1).
2. 외부 검토 수용분을 `paper/draft/`와 `paper/abstract_arxiv.txt`에 적용했다.
3. 기각 3건의 근거를 기록했다.
4. 서지 3건의 저자 목록을 arXiv abs 페이지에서 확인해 채웠다.
5. 초록 길이를 재고 상한 안으로 되돌린 뒤 `ABSTRACT.md`·`ARXIV_CHECKLIST.md`의 인용 수치를 갱신했다.
6. 이송기를 재실행하고 `check_claims`·LaTeX 구조·비-ASCII·그림 대조를 재확인했다.

## 변경된 파일

- `paper/abstract_arxiv.txt`, `paper/ABSTRACT.md`
- `paper/draft/` — `01`, `03`, `04`, `05`, `06`, `11_appendices`
- `paper/latex/md2tex.py`(표 열 폭·표 각주·위첨자·`\allowbreak`), `paper/latex/sections/*.tex` 12파일, `paper/latex/refs.bib`
- `paper/ARXIV_CHECKLIST.md`
- `docs/research/TASK44.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음. `check_claims.py`, `verify_figures.py`, LaTeX 중괄호·`%`·`$` 균형 검사, 비-ASCII 검사, 초록 자수·ASCII 검사. **컴파일은 하지 못했다.**

## 결과

### 관측 1 — 조판 수정을 일회성이 아니라 재생성 가능하게 넣었다

`paper/latex/sections/`는 이송기가 생성하므로 손으로 고치면 다음 재생성에서 사라진다. [TASK41](TASK41.md)의 README가 "LaTeX를 직접 고치기 시작하면 이송기를 다시 돌리지 않는다"고 적었지만, **`check_claims`가 마크다운을 읽으므로 초고를 source of truth로 유지하는 편이 낫다.** 그래서 네 수정을 전부 이송기 기능으로 넣었다.

| # | Advisor 수정 | 구현 방식 |
|---|---|---|
| A1 | `04` 게이트 표 `p{1.55cm}p{3.35cm}p{2.6cm}` + `\footnotesize` | 마크다운 `<!-- TABLECOLS: ... -->` 표식. 열 폭이 지정되면 이송기가 `\footnotesize`를 함께 낸다 |
| A2 | 부록 B 표 `p{2.2cm}p{2.35cm}p{2.7cm}` + `\footnotesize` | 같은 표식 |
| A3 | 긴 `\texttt` 경로·환경변수에 `\allowbreak` | 이송기가 **24자를 넘는 code span**의 `/`·`_`·`.` 뒤에 자동 삽입. 손으로 넣은 곳뿐 아니라 **전 문서에 일관 적용**된다(현재 5곳) |
| A4 | 부록 B commit 칸 축약 | `` `492abe2`, `28dd252`^a^ `` + `<!-- TABLENOTE: ... -->`로 각주 |

**A4의 정보 손실 금지 조건을 각주로 지켰다.** 삭제된 부연("28dd252 = 판정 코드 선등록")을 표 아래 각주로 복원하면서, 무엇이 선등록됐는지(bootstrap 절차·resample 수·CI 폭 상한)까지 적어 **축약 전보다 오히려 구체적**이 됐다.

이송기에 위첨자(`^a^` → `$^{\mathrm{a}}$`)와 표 각주 기능이 함께 들어갔다.

### 관측 2 — 외부 검토 반영/기각 대조표

**반영 18건**

| 위치 | 원문 | 수정 | 성격 |
|---|---|---|---|
| 초록 | "and when a session returns from a tool call sets" | "and **the timing of** a session's return from a tool call sets" | 비문 교정 |
| 초록 | "None responds" | "None **of these mechanisms** responds" | 지시 대상 명확화 |
| 초록 | "out-of-sample gate" | "out-of-sample **prediction** gate" | 용어 정확화 |
| 초록 | "hand every session … and that share disappears" | "**if** every session **is given** … that share disappears" | 명령문 → 조건문 |
| 초록 | "a margin four more orders of sample magnitude do not close" | "a margin **that four additional orders of magnitude in sample size** do not close" | 문법 |
| 초록 | "Escapement chooses one from" | "Escapement **selects one compile-time configuration** from" | 지시 대상 명확화 |
| §I | "residency is what the accelerator prices" | "**the accelerator charges for residency**" | 어법 |
| §I | "decides not merely the size but the sign" | "**determines not only the magnitude but also** the sign" | 어법 |
| §I | "reuse … survives … disappears at the seventh" | "**a completed prefix remains cached through** six background requests **and is evicted at** the seventh" | 정확성 |
| §I | "decode is stopped" | "decode is **stalled**" | §VII과 용어 통일 |
| §I | "the axis along which one session's KV-slot occupancy decides another session's cache survival is undefined" | "**the cross-session dependency — where** one session's KV-slot occupancy **determines** another session's cache survival **— is** undefined" | 삽입구 분리 |
| §I | "That the intersection was empty is what left room for this work, and it is where …: the chain from" | "**That intersection was empty, and it is where … . The chain runs from**" | 문장 분리 |
| §I | (초록과 동일 문장) | 동일 수정 | 문법 |
| §IV | "Every one of those errors" | "**Each of** those errors" | 어법 |
| §V | "Under a rearrangement that conserves work" | "Under a **rescheduling that preserves total** work" | 어법 |
| §V | "the wrong way" | "**in the wrong direction**" | 어법 |
| §V | "The only places coordination can live are" | "**The only mechanisms that can achieve coordination are**" | 어법 |
| §V | "Give every session omniscient knowledge … and" | "**If** every session **is given** … **, 27–51 % is recovered, and**" | 명령문 → 조건문 |
| §V | "−105 % and −70 % in the two confirmation cells." | 뒤에 "**— the policy increased device time rather than reducing it**" 부연 추가 | 부호 해석 명시 |
| §VI-B | compile 비용 한 문장 | **두 문장으로 분리 재작성**(모형 적합 대상과 검증 결과를 분리) | 가독성 |

초록의 "No per-session runtime policy can reach it, in principle."는 지시대로 **원형 유지**했다.

**기각 3건**

| # | 지적 | 판정 | 근거 |
|---|---|---|---|
| 1 | "OCR 잔여 문자열" 제거 | **기각** | 소스·PDF 텍스트 레이어 전수 검색에서 해당 문자열이 **존재하지 않는다.** 검토자 추출기의 글리프 손실로 판정되며, 초록 2문단의 자음 골격과 일치한다 |
| 2 | 하이픈 누락(`sequencegranular` 등) 수정 | **기각** | 소스·조판 모두 정상이다. 행말 하이픈을 추출기가 dehyphenate하면서 생긴 현상이며, **소스를 고치면 오히려 조판이 깨진다** |
| 3 | #18 "pure tax … batching subsidy" 평탄화 | **기각** (Advisor 판정) | 원문 유지 |

**1·2번은 같은 원인의 두 얼굴이다** — 검토자가 PDF에서 텍스트를 추출하는 과정의 손실이지 원고의 결함이 아니다. **원고를 고치면 실재하지 않는 문제를 좇아 실재하는 조판을 망가뜨린다.**

### 관측 3 — 초록이 길어졌다가 다시 들어왔다

수용분 6건을 넣자 1,876 → **1,960자**로 상한(1,920)을 40자 초과했다. 조건 병기와 수용분을 건드리지 않고 네 곳을 줄여 **1,887자**로 맞췄다.

| 줄인 곳 | 근거 |
|---|---|
| "on real hardware" 삭제 | 같은 문단이 이미 "confirms … device-time recovery"로 실기기임을 말한다 |
| "the concurrent request count" → "concurrent request count" | 관사 |
| "recompile intervention" → "recompile" | 같은 문장의 "changes only the grid"가 개입임을 이미 말한다 |
| "That leaves one reachable lever: a compile-time configuration — coordination decided once…" → "…: coordination decided once…" | **다음 문장이 "selects one compile-time configuration"으로 레버를 명시**하므로 중복이었다. 부수 효과로 마지막 남은 비-ASCII 문자(em dash)도 사라졌다 |

**조건 병기(median, at N=8, on two channels)는 한 글자도 줄이지 않았다** — [CLAIMS.md](../../paper/CLAIMS.md)의 압축 규칙이다.

### 관측 4 — 서지 3건 완결

| 항목 | 저자 (1차 출처 확인) |
|---|---|
| MORI (arXiv:2606.00866) | Xia, Li, Li, Chen, Kang, Qiao, Xu, Stoica (8인). 2026-05-30 |
| Leyline (arXiv:2606.01065) | Ma, Eitzinger, Koestler (3인). 2026-05-31 |
| SMetric (arXiv:2607.08565) | Wang, Lin, Zhang, Han, Wei, Shen, Fang, Yu, Chen, Chen (10인). 2026-07-09 |

**잔여 `TODO` 4건**: kvflow, saga, autellix, sarathi의 저자 전체 목록. 이번 지시 범위 밖이라 그대로 두었다.

## 핵심 발견

1. **`universal` — 생성되는 산출물의 조판 수정은 생성기에 넣는다.** 손으로 고치면 다음 재생성에서 사라지거나, 재생성을 포기해 source of truth가 둘로 갈라진다. `\allowbreak`를 규칙으로 넣자 Advisor가 지목한 두 곳뿐 아니라 **전 문서 5곳**에 일관 적용됐다.
2. **`universal` — 검토 의견 중에는 검토 *도구*의 산물이 있다.** OCR 잔여 문자열과 하이픈 누락은 둘 다 PDF 텍스트 추출의 손실이었다. **지적을 그대로 반영하면 실재하지 않는 결함을 좇아 실재하는 조판을 망가뜨린다.** 반영 전에 소스에서 그 문자열이 실재하는지 확인하는 단계가 필요하다.
3. **`universal` — 축약 요구는 각주로 정보를 보존하면서 만족시킬 수 있다.** A4에서 표 칸을 줄이되 각주로 복원했더니 **축약 전보다 구체적**이 됐다.
4. **`universal` — 문장 교정은 길이 예산을 건드린다.** 초록 수용분 6건이 상한을 40자 넘겼다. 자수 제약이 있는 판본은 **교정 후 반드시 다시 재야** 한다.

## 해석

- **(해석)** 관측 1의 선택은 [TASK41](TASK41.md) README의 "교정 단계에서는 이송기를 멈춘다"를 **뒤집은 것**이다. 그 규칙은 조판 손질이 마크다운으로 표현 불가능하다는 전제 위에 있었는데, 표식 세 개(`TABLECOLS`·`TABLENOTE`·위첨자)와 자동 규칙 하나(`\allowbreak`)로 이번 수정이 전부 표현됐다. **표현 가능한 동안에는 이송기를 유지하는 편이 낫다** — `check_claims`의 근거 추적이 마크다운에 걸려 있기 때문이다. 표현 불가능한 손질이 나오면 그때 멈춘다.
- **(해석)** 기각 3건 중 둘이 도구의 산물이었다는 것은 **외부 검토의 입력 형식**에 대한 교훈이다. PDF 추출 텍스트로 검토하면 조판 층의 잡음이 원고의 결함으로 보고된다. 다음 검토에는 마크다운 초고를 함께 제공하는 편이 낫다.
- **(해석)** 이 TASK도 컴파일로 확인하지 못했다. **Advisor가 검증한 열 폭 값을 그대로 재현하도록 이송기를 맞췄으므로 생성물은 그 검증과 같아야 하지만, 그것은 추론이지 확인이 아니다.**

## 확인되지 않은 사항

- **LaTeX 컴파일** (`UNKNOWN`, 이월). 이번 조판 수정도 이 host에서 확인하지 못했다.
- **그림 육안 검수** (`UNKNOWN`, 이월).
- **소속 영문 명칭** (`UNKNOWN`, 이월) — 사용자 확정값 미수신이라 `main.tex`의 TODO를 유지했다.
- **`refs.bib` 잔여 `TODO` 4건** (`PARTIAL`) — kvflow·saga·autellix·sarathi.
- **저장소 공개 방식** (`UNKNOWN`, 이월) — 부록 D.

## 실패 / 무효 시도

이송기 수정 중 위첨자 치환이 공용 종결자(`\x02`)를 써 `$^{\mathrm{a}`로 닫히지 않는 결함이 생겼고, 생성물 검사에서 잡아 자체 종결자로 고쳤다.

**그리고 이 TASK에서 더 큰 것이 드러났다 — [INDEX](INDEX.md) TASK 표에서 TASK38–44 행 7개가 통째로 빠져 있었다.**

원인은 [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 4번(따옴표 없는 heredoc 치환)과 **같은 부류**다. [TASK38](TASK38.md) 이래 표 행을 넣을 때 다음 형태를 썼다.

```python
for i, line in enumerate(rows):
    if line.startswith("| [TASK37](TASK37.md) |"):
        rows.insert(i + 1, "...")
        break
```

**anchor를 찾지 못해도 loop가 조용히 끝나고 예외도 경고도 없다.** 문자열 치환에는 `assert old in s`를 걸어 두었으면서 **행 삽입에는 걸지 않았다** — 같은 실수의 다른 표면이다. 7개 TASK에 걸쳐 누적됐고, 이번에 표를 손대다 발견했다.

이번 복구에서는 (i) anchor 존재를 `assert`하고, (ii) 삽입 전 중복을 `assert`하고, (iii) 삽입 개수를 `assert`하고, (iv) 사후에 1–44 전 범위의 누락을 계산해 확인했다. **중복 검사에서 첫 시도가 실패했는데**, `| [TASK38](TASK38.md) |`가 후속 연구 표의 셀에도 나타나 행 시작 기준으로 다시 검사해야 했다 — 검사 자체가 한 번 더 검사를 요구한 셈이다.

**이 실패는 측정에 영향을 주지 않는다**(TASK 문서 본문은 전부 정상이고 INDEX의 서술·결정·후속 연구 절도 정상이었다). 영향은 **연구 이력 색인의 완결성**이며, INDEX가 "모든 agent가 작업 전에 읽는 단일 진입점"이라는 점에서 가볍지 않다.

## 연구 원칙에 미치는 영향

1. **생성되는 산출물의 수정은 생성기에 넣는다.** 표현 가능한 동안 source of truth를 하나로 유지한다.
2. **검토 의견은 소스에서 실재를 확인한 뒤 반영한다.** 특히 문자·하이픈·공백 수준의 지적은 검토 도구의 산물일 수 있다.
3. **자수 제약이 있는 판본은 교정 후 다시 잰다.** 조건 병기는 마지막에 자른다.
4. **문서를 기계적으로 고칠 때는 치환뿐 아니라 *삽입*에도 assert를 건다.** anchor 미발견 시 조용히 지나가는 loop는 실패를 몇 개 TASK에 걸쳐 누적시킨다. 삽입 후에는 **결과를 독립적으로 세어** 확인한다.

## 다음 작업

1. **첫 Overleaf 빌드와 그림 육안 검수** (이월).
2. 소속 영문 명칭 수신 시 교체, `refs.bib` 잔여 `TODO` 4건.
3. 저장소 공개 방식 판정 → 부록 D.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `3100119`
- 이송: `env -u PYTHONPATH python3 paper/latex/md2tex.py`
- 검증: `env -u PYTHONPATH python3 paper/draft/check_claims.py` → **47/47**, `verify_figures.py` → 177/177
- 초록: 1,887자 / 상한 1,920, 전부 ASCII
- 서지 조회: arXiv abs 2606.00866 · 2606.01065 · 2607.08565, 2026-08-25
- 예산: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
