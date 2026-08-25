# LaTeX 이식 패키지

논문 원고의 LaTeX 소스다. **이 host에는 TeX가 설치돼 있지 않으므로 한 번도 컴파일되지 않았다** — 아래 "한계"를 먼저 읽는다.

## 구성

| 경로 | 내용 |
|---|---|
| [main.tex](main.tex) | 문서 골격. IEEEtran `journal` 모드(TPDS 대상), 절별 `\input` |
| [sections/](sections/) | 절 11개(`00_abstract` + `01`–`10`). **[../draft/](../draft/)의 마크다운에서 생성** |
| [refs.bib](refs.bib) | BibTeX. [../RELATED.md](../RELATED.md) §8에서 arXiv 1차 출처로 확인한 항목만 값으로 넣고, 미확인은 `TODO` 주석 |
| [md2tex.py](md2tex.py) | 마크다운 → LaTeX 이송기 |
| [make_package.sh](make_package.sh) | 그림 PDF를 `figures/`로 복사해 업로드 가능한 상태로 만든다 |

## Overleaf에서 컴파일하기

```bash
bash paper/latex/make_package.sh
cd paper/latex && zip -r escapement.zip main.tex refs.bib sections figures
```

Overleaf에서 **New Project → Upload Project**로 zip을 올리고, **Menu → Compiler를 pdfLaTeX**로 둔다. IEEEtran은 Overleaf에 기본 포함돼 있어 별도 설치가 없다. 참고문헌이 나오려면 두 번 컴파일해야 한다(BibTeX 경유).

## 원고를 고치는 순서

**초고 단계**: [../draft/](../draft/)의 마크다운을 고치고 `python3 paper/latex/md2tex.py`로 다시 생성한다. 근거 추적(`CLAIMS` 주석)이 마크다운에 있고 이송기가 그것을 LaTeX 주석으로 옮기므로, 이 방향이 추적을 유지한다.

**교정 단계**: LaTeX를 직접 고치기 시작하면 **이송기를 다시 돌리지 않는다** — 덮어쓴다. 그 시점에 이 README에 "이송 종료" 날짜를 적는다.

## 이송기가 하는 일과 하지 않는 일

**한다**: 제목·강조·인라인 코드, `<!-- CLAIMS x.y -->`를 LaTeX 주석으로 보존, 파이프 표를 `tabular`로, `**Figure ⑨.**` 표식을 `figure` 환경으로(그림 파일명·캡션 연결), 원문자와 `§`를 `\ref{sec:NN}` 상호참조로, 비-ASCII 기호를 수식으로.

**하지 않는다**: 표의 캡션(전부 `TODO caption`), 그림 배치 조정, 줄바꿈·하이픈, 인용 삽입. **`refs.bib`의 항목들은 아직 본문에서 `\cite`되지 않는다** — §⑧이 arXiv id를 본문에 적고 있어 교정 단계에서 `\cite` 키로 바꿔야 한다.

## 한계 — 반드시 읽을 것

1. **컴파일된 적이 없다.** TeX 설치는 이번 작업의 승인 범위 밖이다. 첫 Overleaf 빌드가 이 소스의 첫 실제 검증이며, **오류가 나올 것을 전제로 본다.**
2. **표 캡션과 인용이 미완이다.** 위 "하지 않는다" 참조.
3. ~~저자란·감사의 글이 placeholder다.~~ → **2026-08-25 확정·활성화됨.** 저자 3인(제1저자 Dongkyeom Jang, In-Nea Wang, 교신저자 Junho Jeong)이 `\author`/`\thanks`에 들어갔고, 리벨리온 CA25 장비 감사와 AI 사용 고지가 각각 `\section*{Acknowledgment}`·`\section*{Use of AI Tools}`로 활성화됐다. **남은 것은 사물인터넷 혁신융합대학의 공식 영문 명칭 확인 하나이고 `main.tex`에 TODO 주석이 있다.**
4. **제출하지 않았다.** arXiv·TPDS 어느 쪽에도 올리지 않았고, 올리는 것은 저자 계정 작업이다. 제출 순서는 [../ARXIV_CHECKLIST.md](../ARXIV_CHECKLIST.md) §6 "제출 순서"에 있다.
5. 서지 일부가 `TODO`다. 저자 전체 목록이 1차 출처로 확인되지 않은 항목은 `refs.bib`에 그렇게 표시돼 있다.

## 제출 전 확인

[../ARXIV_CHECKLIST.md](../ARXIV_CHECKLIST.md) §6의 잔여 항목과 함께 본다 — 저자 표기, 라이선스, AI 사용 고지, 그림 육안 검수.
