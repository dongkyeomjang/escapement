# arXiv 선행 공개 준비 점검표

**공개 승인**: 사용자 판정 2026-08-25. **시스템 명칭**: `Escapement` ([결정 5](../docs/research/INDEX.md#결정-5--시스템-명칭-충돌)).

**제출은 이 저장소의 작업 범위가 아니다.** arXiv 제출은 사용자 계정으로 하는 행위이고 되돌리기 어렵다(v1은 철회해도 목록에 남는다). 이 문서는 **제출 직전에 사람이 확인할 항목**을 모아 둔 것이며, agent는 제출하지 않는다.

---

## 1. 카테고리 제안

| 구분 | 카테고리 | 근거 |
|---|---|---|
| **주 (primary)** | **`cs.DC`** — Distributed, Parallel, and Cluster Computing | 이 논문의 대상은 **서빙 시스템의 자원 회계**다: batch 격자, KV slot pool 회계, prefill 직렬화, 동시 세션의 도착 과정. 기여의 형태가 스케줄링·자원 관리이고, 비교 대상(Sarathi-Serve OSDI'24, Autellix, Continuum, MORI)이 대부분 이 카테고리이거나 시스템 학회다. **cs.DC가 이 논문을 찾는 독자가 있는 곳이다** |
| 교차 1 | **`cs.LG`** — Machine Learning | LLM 추론이 대상이고 워크로드가 agentic LLM이다. 다만 **학습 기여는 없다.** 이 논문이 cs.LG에 실릴 이유는 독자 도달이지 방법론적 소속이 아니므로 **주 카테고리로 쓰지 않는다** |
| 교차 2 (권고) | **`cs.PF`** — Performance | 이 논문의 절반은 **성능 특성화와 비용 모형**이다(step 비용 분해, prefill 비용 모형, compile 비용 모형, 시뮬레이터 검증). cs.PF는 그 형태의 결과를 정확히 담는 카테고리이고, LENS(arXiv:2606.18042) 같은 인접 결과가 있는 곳이다 |
| 검토만 | `cs.AR`, `cs.OS` | **권고하지 않는다.** microarchitecture 기여가 없고(`cs.AR`), OS 계층을 건드리지 않는다(`cs.OS`) |

**권고: primary `cs.DC`, cross-list `cs.PF`, `cs.LG`.** arXiv는 cross-list를 나중에 추가할 수 있으므로 확신이 낮은 것부터 빼도 된다. **primary는 나중에 바꾸기 번거로우므로 여기서 정한다.**

## 2. 라이선스 선택지

arXiv가 제시하는 선택지와 이 논문에 대한 평가다. **판정은 사용자**다.

| 선택지 | 내용 | 이 논문에 대한 평가 |
|---|---|---|
| **CC BY 4.0** (권고) | 출처 표시만 하면 재배포·개작·상업적 이용 자유 | **가장 열려 있고 학회 투고와 충돌하지 않는다.** 그림·표가 후속 서베이에 인용되기 쉬워진다. 시스템 분야에서 흔한 선택 |
| CC BY-SA 4.0 | 동일조건 변경허락 | 파생물에 같은 라이선스를 강제한다. 이 논문이 얻을 것이 없다 |
| CC BY-NC-SA 4.0 | 비상업적 한정 | 기업 연구자의 인용·재사용을 불필요하게 제약한다 |
| CC Zero | 저작권 포기 | 출처 표시조차 요구하지 않는다. 이 연구는 **인용으로 추적되는 것이 목적**이므로 부적합 |
| arXiv non-exclusive license | arXiv 배포만 허용, 그 외 권리 유보 | 가장 보수적. **학회 저작권 정책이 불확실할 때의 안전한 선택**이며, 나중에 더 열 수 있다 |

**확정: CC BY 4.0** (사용자 판정 2026-08-25). 제출 시 arXiv 라이선스 선택 화면에서 `Creative Commons Attribution 4.0 International (CC BY 4.0)`을 고른다. **소속(동국대학교)에 preprint 라이선스 규정이 따로 있으면 그것이 우선하므로 제출 직전에 한 번 확인한다.**

## 3. 저자 표기 — **확정** (2026-08-25)

| 순서 | 이름 | 소속 | 이메일 |
|---|---|---|---|
| 1 (제1저자) | **Dongkyeom Jang** | 동국대학교 컴퓨터AI학과 | `jangelliot0404@dgu.ac.kr` |
| 2 | **In-Nea Wang** | 동국대학교 사물인터넷 혁신융합대학 | `innea@dgu.ac.kr` |
| 3 (**교신저자**) | **Junho Jeong** | 동국대학교 컴퓨터AI학과 | `yanyenli@dongguk.edu` |

[main.tex](latex/main.tex)의 `\author` 블록과 `\thanks`에 반영했다.

| 항목 | 상태 |
|---|---|
| 소속 영문 표기 | 컴퓨터AI학과 → **Department of Computer Science and Artificial Intelligence, Dongguk University**. 사물인터넷 혁신융합대학은 **`IoT Convergence, Dongguk University`** 로 잠정 표기했고 `main.tex`에 TODO 주석을 달았다 — **기관의 공식 영문 명칭 확인 필요** |
| ORCID | 있으면 제출 시 연결 권장 (인용 추적). 미기입 |
| **AI 사용 고지** | **활성화됨** — [main.tex](latex/main.tex)의 `\section*{Use of AI Tools}`. 문구는 아래 §7 |
| 하드웨어 감사 | **활성화됨** — 리벨리온 CA25 장비 제공 감사. [main.tex](latex/main.tex)의 `\section*{Acknowledgment}` |

**arXiv 제출자 계정이 저자 목록에 기록되므로, 제출은 저자 중 한 명의 계정으로 한다.**

## 4. 초록의 arXiv 형식 제약 점검

arXiv 초록 필드는 **plain text**다. 다음이 제약이고, 오른쪽이 [ABSTRACT.md](ABSTRACT.md) 현재 상태에 대한 점검 결과다.

| 제약 | 현재 초록 |
|---|---|
| **마크다운 강조(`**`)가 렌더되지 않는다** | ✅ **해소됨** — 압축본에는 마크다운이 없다 |
| **수식은 `$...$` TeX만 지원**(제한적) | ✅ 초록에 수식 없음. `ε=2 s`, `N=8` 같은 표기는 평문으로 읽힌다. 압축본에는 그리스 문자가 남지 않았다 |
| **줄바꿈이 보존되지 않는다**(단락은 빈 줄로) | ⚠️ 현재 3문단 구조. arXiv는 단락 구분을 유지하므로 **문단 3개 그대로 제출 가능**하되, 일부 시스템이 한 문단으로 합치므로 **문단 첫 문장이 독립적으로 읽히는지** 확인했다 — 세 문단 모두 통과 |
| **유니코드**: 대부분 통과하나 일부 문자가 깨진다 | ✅ **해소됨** — 압축본은 **전부 ASCII**다(자동 확인). `−`·`→`·`×`·`①②③`이 남아 있지 않다 |
| **길이 제한 1,920자**(공백 포함, 하드 캡) | ✅ **해소됨** — [ABSTRACT.md](ABSTRACT.md) §1의 압축본이 **248단어 / 1,706자**로 상한에 여유가 있다. 평문 파일은 [`abstract_arxiv.txt`](abstract_arxiv.txt)다. 전체판(3,029자)은 논문 본문용으로 §3에 남겼다 |
| **제목 형식** | 제안: `Escapement: Compile-Time Coordination for Agentic LLM Serving on NPUs`. 콜론 형식은 arXiv에서 통상적이다. **`stack` 조건(NPU)을 제목에 넣은 것은 의도적이다** — [CLAIMS.md](CLAIMS.md) 전수 점검의 오독 방지 규칙을 제목에도 적용한다 |
| **국문 초록** | arXiv 초록 필드는 **영문 하나만** 받는다. 국문 초록은 본문 부록이나 별도 배포용으로 남긴다 |

**압축에서 본문으로 이관한 것**: 격자 개입 전후 pooled ratio, 재사용 절벽의 12/12, 예측기 오차의 문턱 초과 배수, N=6 확증 수치, 자유 파라미터 함정 수치, 절제의 항별 크기. **남은 수치의 조건 병기는 유지했다** — `60 %`에 "median", `9.7-10.1 %`에 "at N=8 concurrent sessions"와 "on two channels registered before measurement". 상세는 [ABSTRACT.md](ABSTRACT.md) 머리의 판본 표에 있다.

길이는 다음으로 확인한다:

```bash
python3 -c "import sys; t=open('paper/abstract_arxiv.txt').read(); \
print(len(t), 'chars', 'OK' if len(t)<=1920 else 'OVER by '+str(len(t)-1920))"
```

## 5. LaTeX 골격 필요 여부 — **필요하다. 다만 지금은 아니다**

| 판단 축 | 내용 |
|---|---|
| arXiv가 PDF 직접 업로드를 받는가 | 받는다. **그러나 TeX source 제출이 표준이고**, PDF-only는 `(PDF only)` 표시가 붙어 HTML 렌더(arXiv의 `/html/` 경로)가 생성되지 않는다. 이 분야 독자가 `/html/`로 읽는 비율이 커지고 있으므로 **불리하다** |
| 목표 학회 요구 | MLSys·EuroSys 모두 LaTeX 템플릿을 요구한다(EuroSys는 ACM `sigconf`). **어차피 써야 한다** |
| 지금 만들 것인가 | **아니다.** 본문이 아직 없다. 지금 골격만 만들면 서사([OUTLINE.md](OUTLINE.md))가 바뀔 때마다 두 곳을 고쳐야 한다 |
| **권고 순서** | (1) [OUTLINE.md](OUTLINE.md)를 따라 **마크다운으로 본문 초고**를 쓴다 → (2) 그림 8종을 SVG → PDF로 변환한다 → (3) MLSys 2027 템플릿(또는 ACM `sigconf`)으로 옮긴다 → (4) arXiv에 TeX source로 제출 |

**그림 형식**: ✅ **해소됨** ([TASK39](../docs/research/TASK39.md)). `paper/figures/pdf/`에 **영문 PDF 8종**이 있고 `\includegraphics`로 바로 들어간다. 변환기를 설치하지 않고 [svgplot.py](figures/svgplot.py)에 PDF 백엔드를 직접 넣었다 — 이 host에 cairo가 없어 `cairosvg`는 apt 없이는 설치되지 않고, **CJK 폰트가 하나도 없어** 국문 라벨은 애초에 PDF에 넣을 수 없었기 때문이다. 그래서 논문용 그림은 [labels_en.py](figures/labels_en.py)의 번역표로 **영문 라벨**을 쓴다(영문 논문에는 어차피 필요하다). 폰트는 이미 있는 DejaVuSans를 임베딩하고 글자 폭은 이미 설치된 Pillow에서 읽는다. **새로 설치한 것은 없다.**

**남은 LaTeX 작업**: 본문 초고 → 템플릿 이식. 그림은 준비돼 있다.

## 6. 제출 전 최종 확인 목록

### 해소된 항목 ([TASK39](../docs/research/TASK39.md))

- [x] **초록 길이** — 압축본 248단어 / 1,706자 (상한 1,920자). [`abstract_arxiv.txt`](abstract_arxiv.txt)
- [x] **초록 형식** — 마크다운 없음, 전부 ASCII, 3문단
- [x] **그림 PDF 변환** — `paper/figures/pdf/` 8종. 구조 검사 8/8, 변환 손실 0, 캔버스 넘침 0
- [x] **primary/cross-list 제안** — `cs.DC` / `cs.PF`·`cs.LG` (§1)
- [x] **제목 제안** — `Escapement: Compile-Time Coordination for Agentic LLM Serving on NPUs`

### 해소된 항목 (2026-08-25, 사용자 확정)

- [x] **저자 목록·순서·소속·교신저자** — §3. `main.tex`의 `\author`/`\thanks` 반영 완료
- [x] **라이선스** — **CC BY 4.0** 확정 (§2)
- [x] **AI 사용 고지** — `\section*{Use of AI Tools}`로 활성화 (§7의 초안 그대로)
- [x] **하드웨어 감사** — 리벨리온 CA25 장비 제공 문구 활성화
- [x] **부록 연결** — `\appendices` + Appendix A–D

### 남은 항목

- [ ] **첫 Overleaf 컴파일** — 이 host에 TeX가 없어 소스가 **한 번도 컴파일된 적이 없다.** 첫 빌드가 첫 검증이며 오류를 전제한다
- [ ] **그림 육안 검수** — `paper/figures/en/*.svg`를 브라우저로 열어 [INSPECTION.md](figures/INSPECTION.md)와 대조. **글자 겹침은 자동 검사가 잡지 못한다.** 그림 ⑨는 2패널이라 특히 확인이 필요하다
- [ ] **표 캡션·상호참조 교정** — 캡션은 작성됐으나 본문에서 표를 `\ref`로 가리키지 않는다
- [x] **서지 완결** — 19항목 전부 1차 출처로 저자 확인 완료 ([TASK46](../docs/research/TASK46.md))
- [ ] **소속 영문 명칭 확인** — 사물인터넷 혁신융합대학
- [ ] **소속 기관 preprint 규정 확인** — CC BY 4.0과 충돌 여부
- [ ] **제출** — arXiv 업로드는 **저자 계정 작업**이며 이 저장소의 작업 범위 밖이다

### 제출 순서

1. `bash paper/latex/make_package.sh` → `cd paper/latex && zip -r escapement.zip main.tex refs.bib sections figures`
2. **Overleaf 업로드 → pdfLaTeX로 컴파일 → 오류 수정** (두 번 컴파일해야 참고문헌이 나온다)
3. **육안 검수** — 그림 겹침·잘림, 표 넘침, 저자란·감사의 글 렌더링
4. **arXiv 업로드** — TeX source 제출(PDF-only는 HTML 렌더가 생기지 않는다). primary `cs.DC`, cross-list `cs.PF`·`cs.LG`, 라이선스 CC BY 4.0, 초록은 [abstract_arxiv.txt](abstract_arxiv.txt) 그대로 붙여넣기(248단어 / 1,706자)
5. **접수 확인** — announce 이후 abs 페이지에서 제목·저자·라이선스·그림 렌더를 확인하고, 필요하면 v2로 정정

## 7. AI 사용 고지 — 초안 (판정은 사용자)

arXiv는 AI 도구 사용 시 본문에 밝히기를 권고한다. 이 연구는 실험 실행·분석·문서화 전반에 coding agent를 썼으므로 고지 대상이라고 본다. **아래는 초안이며, 어떤 범위로 어떻게 쓸지는 사용자가 정한다.**

> **Use of AI tools.** The experiments, analyses, figures and research records in this
> work were carried out by an AI coding agent (Claude Code) operating on the authors'
> hardware under a written protocol: every measurement task registers its decision
> criteria, predictions and experimental grid in a commit before measurement begins,
> and each task is recorded with its raw artefacts, invariant checks and the layer
> (silicon / stack / class / universal) at which each finding is claimed to hold. The
> research direction, the choice of questions, the preregistration criteria and every
> judgement reported here are the authors'. The agent did not select which results to
> report, and no criterion was relaxed after measurement; where one was corrected, the
> original criterion's failure is reported alongside it.

**이 초안이 주장하는 것과 주장하지 않는 것**을 분명히 해 둔다. 주장하는 것: 실행·분석·기록의 수행 주체와, 그것을 통제한 프로토콜(선등록·층 태깅·불변식). 주장하지 않는 것: agent가 연구 방향이나 판정을 정했다는 것. **저장소의 [CLAUDE.md](../CLAUDE.md)와 `docs/research/`의 TASK 39건이 이 진술의 근거이며, 필요하면 그 자체를 공개 자료로 제시할 수 있다.**