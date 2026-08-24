# TASK39 — arXiv 초록 압축과 제출 준비 마감: 그림 PDF 백엔드 자체 구현

## 상태

DONE

측정 없음. 영문 초록을 arXiv 상한 안으로 압축했고(3,029 → **1,876자**), **설치 없이** SVG→PDF 경로를 열어 영문 그림 8종을 PDF로 냈다. 남은 항목은 전부 사용자 판정·확인 사항이다.

## 판정

측정이 없으므로 선등록·판정 기준이 없다.

| 항목 | 결과 |
|---|---|
| 영문 초록 압축 | **1,876자** (arXiv 하드 캡 1,920자, 목표 1,880자). 전부 ASCII, 마크다운 없음, 3문단 |
| 판본 병존 | [ABSTRACT.md](../../paper/ABSTRACT.md)에 **압축본(arXiv 필드용)·전체판(논문 본문용)·국문**을 용도 표기와 함께 병존 |
| SVG→PDF | **설치 0건.** [svgplot.py](../../paper/figures/svgplot.py)에 PDF 백엔드를 직접 구현 |
| 영문 그림 | 라벨 번역표 [labels_en.py](../../paper/figures/labels_en.py) 73항목(패턴 2 포함), 영문 SVG 8 + PDF 8 |
| PDF 구조 검사 | **8/8 정상** (header·xref offset 전건·trailer·font 임베딩·graphics state 균형·MediaBox 안) |
| 변환 손실 검사 | **8/8 문자열 전건 일치** (PDF가 그리는 텍스트 = 영문 SVG가 그리는 텍스트) |
| 영문 넘침 검사 | **0건** (초기 15건을 라벨 단축으로 해소) |
| 수치 대조 | **138/138 유지** ([TASK38](TASK38.md)의 검사가 리팩터링 후에도 통과) |
| 체크리스트 | [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6을 해소/잔여로 분리, §7에 AI 사용 고지 초안 |

## 날짜

2026-08-25

## 목적

[TASK38](TASK38.md)이 남긴 공개 준비 항목 둘을 닫는다. (1) 영문 초록이 arXiv 상한을 1,109자 초과했고, (2) LaTeX가 SVG를 받지 못하는데 이 host에 변환기가 없었다. 사용자 판정으로 **도구 설치 1건이 사전 승인**됐으므로 그 범위 안에서 가장 가벼운 경로를 고른다.

## 배경

관련 TASK: [TASK38](TASK38.md)(공개 준비, 이 TASK가 이어받는다), [TASK37](TASK37.md)(그림·초록 초안), [TASK36](TASK36.md)(그림 ④·⑧의 N=6 원본).

사용자 판정 2건이 이 TASK에 전달됐다: **SVG→PDF 도구 설치 사전 승인**(단 apt가 필요하면 중단하고 보고), **arXiv 선행 공개 승인**([TASK38](TASK38.md)에서 이미 반영).

## 시작 상태

- Base commit: `5671847` ([TASK38](TASK38.md))
- 측정 없음. serving 기동 0회, 재compile 0회, device 접근 0회
- 설치된 것: Pillow 12.3.0. 없는 것: matplotlib, cairo(`libcairo` 부재), reportlab, lxml, rsvg-convert, inkscape
- **이 host 전체에 CJK 폰트가 하나도 없다** (`find / -xdev -iname "*.ttf" -o ...` 134개 전부 DejaVu·STIX·Computer Modern)

## 수행 내용

1. 영문 초록을 Advisor가 확정한 우선순위대로 압축하고 평문 파일 [`abstract_arxiv.txt`](../../paper/abstract_arxiv.txt)를 만들었다.
2. 변환 경로 후보를 조사해 **설치 없는 경로**를 선택했다(아래 관측 1).
3. [svgplot.py](../../paper/figures/svgplot.py)를 **원시 SVG 문자열 누적 → 프리미티브 기록**으로 리팩터링하고 SVG·PDF 두 렌더러를 붙였다.
4. 영문 라벨 번역표를 만들고, 번역이 없는 비-ASCII 라벨에서 **생성이 실패하도록** 했다.
5. 영문 SVG 8종과 PDF 8종을 생성했다.
6. [verify_figures.py](../../paper/figures/verify_figures.py)에 **영문 넘침 검사**와 **PDF 구조·변환 손실 검사**를 추가했다.
7. [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md)를 갱신하고 AI 사용 고지 초안을 넣었다.

## 변경된 파일

- `paper/ABSTRACT.md`(판본 3종 재구성), `paper/abstract_arxiv.txt`(신규)
- `paper/figures/svgplot.py`(프리미티브 모델 + PDF 백엔드 + 번역 훅), `paper/figures/make_figures.py`(2개 언어 출력), `paper/figures/labels_en.py`(신규), `paper/figures/verify_figures.py`(검사 2종 추가)
- `paper/figures/en/*.svg`(신규 8), `paper/figures/pdf/*.pdf`(신규 8), `paper/figures/INSPECTION.md`, `paper/figures/SOURCES.md`
- `paper/ARXIV_CHECKLIST.md`
- `docs/research/TASK39.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음. 검증은 전부 기계적이다.

- **초록**: 마크다운 제거 후 문자 수와 비-ASCII 문자 집합을 계산.
- **PDF 구조**: PDF 라이브러리가 없으므로 파일을 직접 걷는다 — `%PDF` header, `startxref`가 가리키는 xref 표, **모든 객체 offset이 실제 `N 0 obj`를 가리키는지**, trailer, `/FontFile2` 임베딩 존재, 압축 해제한 content stream의 `q`/`Q` 균형, 모든 text 원점이 MediaBox 안인지.
- **변환 손실**: content stream을 inflate해 `(...) Tj`의 피연산자를 뽑고, 같은 그림의 영문 SVG `<text>` 내용과 **다중집합으로 비교**.
- **넘침**: PDF의 `/Widths`와 **같은 폭 표**로 각 문자열의 폭을 계산해 anchor를 적용한 뒤 캔버스 경계와 대조.

## 결과

### 관측 1 — 변환 경로 선택: 설치 후보가 전부 막혀 있었다

| 후보 | 판정 | 근거 |
|---|---|---|
| `cairosvg` (pip) | **불가** | `cairocffi` → `libcairo` 필요. `ldconfig -p`에 `libcairo` 없음. **apt가 필요하므로 지시문에 따라 선택하지 않는다** |
| `rsvg-convert` / `inkscape` | **불가** | 시스템 패키지. 미설치 |
| `svglib` + `reportlab` (pip, 순수 Python) | **가능하나 부적합** | 설치는 되지만 SVG의 font-family를 PDF base-14로 사상하므로 **비-Latin 글자가 사라진다.** 이 그림들의 라벨이 정확히 그 대상이다 |
| **`make_figures.py`에 PDF 백엔드 직접 구현** | **채택** | **설치 0건.** 폰트는 이 host에 이미 있는 DejaVuSans(`/usr/share/fonts/truetype/dejavu/`)를 임베딩하고, 글자 폭은 **이미 설치된 Pillow**에서 읽는다 |

**채택 근거는 "가장 가볍다"만이 아니다.** 폭 표를 PDF의 `/Widths` 배열과 이 모듈의 anchor 계산에 **같은 출처로** 쓰므로, 글자 위치가 뷰어의 계산과 *비슷한* 것이 아니라 *일치한다*. 외부 변환기를 썼다면 이 성질이 없다.

### 관측 2 — CJK 폰트 부재가 설계를 정했다

`find / -xdev`로 찾은 폰트 134개가 전부 DejaVu·STIX·Computer Modern이다. **한글 글리프가 이 host에 존재하지 않는다.** 따라서 국문 라벨은 어떤 경로로도 PDF에 들어갈 수 없다.

이것은 제약이자 이미 필요했던 작업의 강제였다 — **영문 논문의 그림은 어차피 영문이어야 한다.** 그래서 산출물을 3종으로 나눴다.

| 경로 | 언어 | 형식 | 용도 |
|---|---|---|---|
| `paper/figures/*.svg` | 국문 | SVG | 국문 연구 문서와 함께 보는 검토용 |
| `paper/figures/en/*.svg` | 영문 | SVG | 논문 그림의 브라우저 확인 |
| `paper/figures/pdf/*.pdf` | 영문 | PDF | **LaTeX 원고에 들어가는 것** |

번역은 [labels_en.py](../../paper/figures/labels_en.py)의 표 71항목과 f-string 라벨용 패턴 2개다. **번역이 없는 비-ASCII 라벨을 만나면 생성이 예외로 죽으므로**, 국문 문자열이 영문 그림에 남는 경로가 없다.

### 관측 3 — 압축의 결과

| 판본 | 길이 | 용도 |
|---|---|---|
| 영문 압축본 | **1,876자** | arXiv 초록 필드 (상한 1,920, 여유 44) |
| 영문 전체판 | 3,029자 | 논문 본문 |
| 국문 | 1,511자 | 국문 배포 (**자수 제약이 없으므로 압축하지 않았다**) |

**본문으로 이관**: 격자 개입 전후 pooled ratio, 재사용 절벽 12/12, 예측기 오차 배수, N=6 확증 수치, 자유 파라미터 함정 수치, 절제의 항별 크기(+8.25 % / +1.52 %p).

**유지**: 세 기전의 명명과 인과 확정 방식, 무보정 시뮬레이터 + 선등록 out-of-sample 게이트, 조율 60 %와 원리적 도달 불가, compile-time 처방 + N=8 확증(두 채널), 폐지 문장.

**조건 병기는 남은 수치에만 적용했다** — `median 60%`, `at N=8 concurrent sessions`, `on two channels registered before measurement`.

### 관측 4 — 검사 결과

| 검사 | 결과 |
|---|---|
| 수치 대조 ([TASK38](TASK38.md)) | **138/138** — 리팩터링이 데이터를 건드리지 않았음의 회귀 검사 역할을 했다 |
| 영문 넘침 | 초기 **15건** → 라벨 단축 후 **0건** |
| PDF 구조 | **8/8 정상** |
| PDF 변환 손실 | **8/8 전건 일치** (문자열 19–43개씩) |
| PDF 크기 | 717–719 KB/장. 폰트 프로그램을 Flate 압축해 1.47 MB에서 절반으로 줄였다 |

### 관측 5 — 검사기를 만들자 검사기의 버그가 먼저 나왔다

[TASK38](TASK38.md)에서 파서 오류 2건이 나온 데 이어 이번에도 3건이 검사기 자신의 버그였다.

1. PDF 텍스트 추출이 "첫 번째 `b\" Tj\"`를 포함한 stream"을 content stream으로 삼았는데, **폰트 프로그램의 바이너리에 그 두 바이트가 우연히 들어 있었다.** 실제로 피연산자가 나오는 stream을 고르도록 고쳤다.
2. SVG 텍스트를 HTML escape된 채로 비교해 `-&gt;`가 불일치로 잡혔다. unescape를 넣었다.
3. `q`/`Q` 균형을 정규식으로 셌더니 8개 그림 전부에서 1개씩 어긋났다. **정규식이 선행 공백을 소비해 인접 쌍을 잘못 셌던 것**이고, 토큰 분리로 세니 전부 균형이었다.

**세 번 다 "그림이 틀렸다"가 아니라 "검사기가 틀렸다"였다.** 자동 검사의 첫 산출물을 결과로 믿지 않는 것이 이 프로그램의 기록 원칙과 같은 자리에 있다.

## 핵심 발견

1. **`universal` — 검증 도구는 대상과 *같은 상수*를 쓸 때만 위치 일치를 보장한다.** PDF의 `/Widths`와 이 모듈의 anchor 계산이 같은 폭 표에서 나오므로 글자 위치가 뷰어 계산과 일치한다. 외부 변환기를 썼다면 "비슷함"에 그친다.
2. **`universal` — 환경의 결핍이 설계를 정할 수 있고, 그것이 나쁜 일만은 아니다.** CJK 폰트 부재가 영문 그림 세트를 강제했는데, 영문 논문에는 어차피 필요한 것이었다. **제약을 우회하지 않고 따라가면 미뤄 둔 작업이 드러난다.**
3. **`universal` — 번역표는 "없으면 실패"로 만들어야 번역표다.** 누락 시 조용히 원문을 남기면 국문이 영문 그림에 섞이고, 그것은 육안 검수에서만 잡힌다. 이 host에는 육안 검수가 없다.
4. **`universal` — 압축은 조건 병기를 먼저 지우려 한다.** 1,109자를 덜어내면서 가장 쉽게 사라질 뻔한 것이 "median", "at N=8", "on two channels"였다. **압축 규칙에 "조건은 마지막에 자른다"를 명시하지 않으면 오독 방지 규칙이 압축 단계에서 무너진다.**

## 해석

- **(해석)** 관측 1의 선택은 "설치 승인을 받았지만 쓰지 않은" 경우다. 승인이 있다고 해서 설치가 최선이 되는 것은 아니며, 이번에는 apt 제약과 폰트 부재가 겹쳐 **설치 경로가 오히려 더 나쁜 결과**(비-Latin 소실)를 냈을 것이다. 승인 범위 안에서 더 가벼운 답을 찾은 것을 기록해 둔다.
- **(해석)** PDF 크기 717 KB의 대부분은 임베딩된 두 폰트다. 8장 합계 5.7 MB로 arXiv 제한에 여유가 있지만, 폰트 subsetting을 넣으면 한 자릿수 KB로 줄어든다. **지금 하지 않는 이유는 subsetting이 glyph 재사상을 요구해 검사기의 "폭 표가 곧 위치"라는 성질을 깨기 때문**이다. 필요해지면 그때 검사기와 함께 바꾼다.
- **(해석)** 영문 라벨 단축 15건은 정보 손실이 아니라 **부제·본문으로의 이동**이다. 예를 들어 그림 ⑦의 제목에서 "두 점으로 세운 모형이 다섯 번째 점에서도 맞는다"를 뺐지만 그 사실은 부제에 남아 있다. 그림 캡션은 LaTeX 본문에서 다시 쓰므로 최종 원고에서 회복된다.

## 확인되지 않은 사항

- **그림의 시각적 품질** (`UNKNOWN`, [TASK38](TASK38.md)에서 이월). 글자 겹침·잘림은 여전히 육안으로만 확인된다. 넘침 검사는 캔버스 경계만 본다.
- **PDF가 실제 뷰어에서 어떻게 보이는가** (`UNKNOWN`). 구조는 검사했지만 렌더링은 확인하지 못했다. 이 host에 뷰어도 래스터라이저도 없다.
- **저자 표기·소속·라이선스·AI 사용 고지 확정** (`UNKNOWN`). [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6.
- **MLSys 2027 분량 규정**, **EuroMLSys 2027 CFP**, **SAGA 저자 전체 목록** (`UNKNOWN`, 이월).
- 국문 SVG의 PDF 변환 (`불가`). CJK 폰트를 설치하지 않는 한 방법이 없다. **필요해지면 폰트 설치가 별도 승인 대상이다.**

## 실패 / 무효 시도

없다. 검사기 버그 3건은 이 TASK 안에서 발견·수정했다(관측 5).

**설치 승인을 받고도 쓰지 않았다.** 조사 결과 승인 범위(비-apt) 안의 설치 후보가 전부 부적합했고, 설치 없는 경로가 더 나은 성질을 가졌다. 이것을 "승인 미사용"으로 기록한다.

## 연구 원칙에 미치는 영향

1. **번역·사상표는 누락 시 실패하게 만든다.** 조용한 통과는 육안 검수가 없는 환경에서 발견되지 않는다.
2. **검사기를 새로 만들면 검사기 자신을 먼저 의심한다.** 첫 실행의 불일치는 대상보다 검사기의 버그일 확률이 높았다(이 프로그램에서 5/5).
3. **압축·요약 작업에는 "무엇을 마지막에 자르는가"를 먼저 정한다.** 이 연구에서 그것은 수치의 조건 병기다.
4. **설치 승인은 설치 의무가 아니다.** 승인 범위 안에서 더 가벼운 경로가 있으면 그것을 택하고 근거를 기록한다.

## 다음 작업

1. **논문 본문 집필** — [OUTLINE.md](../../paper/OUTLINE.md) 기준. 그림·초록·서지는 준비됐다.
2. 사용자 확인: [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6 잔여 항목(저자·라이선스·AI 고지·육안 검수).
3. 후속 연구 항목은 [INDEX.md 후속 연구](INDEX.md#후속-연구) 절 — **사용자 지시 없이 착수하지 않는다.**

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `5671847`
- 그림 생성: `env -u PYTHONPATH python3 paper/figures/make_figures.py` → 국문 SVG 8 + 영문 SVG 8 + PDF 8
- 검사: `env -u PYTHONPATH python3 paper/figures/verify_figures.py` → 138 checks 0 mismatches, 넘침 0, pdf 8/8
- 초록 길이: `python3 -c "t=open('paper/abstract_arxiv.txt').read().strip(); print(len(t))"` → **1876**
- 폰트: `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`, `DejaVuSans-Bold.ttf` (임베딩, Flate 압축)
- 설치: **0건.** Pillow 12.3.0은 기존 설치
- 예산 사용: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**
