# TASK42 — Advisor 첨삭 반영, 교정 1차, 저자 확정과 제출 패키지 완성

## 상태

DONE

측정 없음. 첨삭 3건과 `[NEEDS-EVIDENCE]` 판정 3건을 집행하고, 캡션·인용을 채워 교정 1차를 마쳤으며, **확정된 저자·소속·감사의 글을 반영해 제출 패키지를 완성**했다. **제출은 하지 않았다.**

## 판정

측정이 없으므로 선등록·판정 기준이 없다.

| 항목 | 결과 |
|---|---|
| §1 substrate 클래스 선언 | Inferentia·Gaudi·cudagraph 격자를 **web 1차 출처로 확인** 후 1문단 추가, §⑦ 연결 |
| §1 stack 버전 병기 | "the vLLM stack" → `vllm 0.22.0` + `vllm-rbln 0.11.1` + `optimum-rbln 0.11.1` |
| §5.2 제목 교체 | 결론 선취 제거 |
| `[NEEDS-EVIDENCE]` | **3건 전부 집행**, 본문 잔존 **0건** (부록 D에 신규 1건 — 저장소 공개 방식) |
| 부록 | **A–D 신설**, C가 요청된 patch 정책 7항목 |
| CLAIMS | **1.18 신규**(계통 오차, scope 표기) + 오독 위험 1항목. 총 **47항목** |
| Figure 캡션 | **9/9 작성** — 각 그림의 주장 1문장 + 조건 병기 |
| Table 캡션 | **2/2 작성** (`TODO caption` 잔존 0) |
| `\cite` | **18개 삽입**, 본문 인라인 arXiv id 잔존 0 |
| 인용 검증 | CLAIMS **47/47**, 미존재 id 0, 미인용 주장 0 |
| **저자·소속·교신저자** | **확정 반영** (사용자 기입) |
| **감사의 글·AI 고지** | **활성화** |
| 라이선스 | **CC BY 4.0 확정** |
| 제출 | **하지 않음** |

## 날짜

2026-08-25

## 목적

[TASK41](TASK41.md)의 초고에 Advisor 첨삭을 반영하고, 남겨 둔 `[NEEDS-EVIDENCE]` 3건을 판정대로 집행하며, LaTeX 이송에서 미완이던 캡션과 인용을 채운다. 작업 중 사용자가 저자 정보를 확정해 전달했으므로 그 반영과 제출 패키지 완성을 같은 TASK에 병합했다.

## 배경

관련 TASK: [TASK41](TASK41.md)(초고·LaTeX 패키지), [TASK40](TASK40.md)(포화 곡선), [TASK38](TASK38.md)(서지 1차 출처 확인 원칙), [TASK12](TASK12.md)(patch — 부록 C의 출처), [TASK28](TASK28.md)·[TASK35](TASK35.md)·[TASK36](TASK36.md)(계통 오차의 출처).

## 시작 상태

- Base commit: `6ef9d7a` ([TASK41](TASK41.md))
- 측정 없음. serving 기동 0회, 재compile 0회, device 접근 0회, 설치 0건
- TeX 미설치 — 컴파일 검증 불가는 [TASK41](TASK41.md)에서 이월된 한계

## 수행 내용

1. §1에 substrate 클래스 선언을 넣고 stack 버전을 병기했다. **클래스 예시는 web 1차 출처로 확인한 뒤 썼다.**
2. §5.2 제목을 내용 서술로 바꿨다.
3. `[NEEDS-EVIDENCE]` 3건을 판정대로 집행했다 — ① 부록 C 신설, ② §4.3.1 "validated envelope" + §9 반향, ③ §4.3.2 "known error structure" + CLAIMS 1.18.
4. 그림 9종과 표 2종의 캡션을 쓰고, 인용 표식을 도입해 `\cite` 18개를 넣었다.
5. **사용자가 확정한 저자·소속·교신저자를 `main.tex`에 반영**하고 감사의 글과 AI 사용 고지를 활성화했다.
6. 라이선스를 CC BY 4.0으로 확정 표기하고 [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6을 해소/잔여로 다시 갈랐으며 **제출 순서 5단계**를 넣었다.
7. `make_package.sh`로 업로드 패키지를 재생성했다.

## 변경된 파일

- `paper/draft/` — `01`(클래스 선언·버전·인용), `02`(patch 1문장), `04`(§4.3.1·§4.3.2·표 캡션), `05`(제목·인용), `08`(인용 18), `09`(envelope·계통 오차), **`11_appendices.md`(신규)**
- `paper/CLAIMS.md` — 1.18 신규, 오독 위험 1항목
- `paper/latex/` — `main.tex`(저자·감사·AI 고지·`\appendices`), `md2tex.py`(캡션·`\cite`·표 캡션·부록 heading), `sections/*.tex` 12파일, `README.md`
- `paper/ARXIV_CHECKLIST.md` — §2 라이선스 확정, §3 저자 확정, §6 재편·제출 순서
- `docs/research/TASK42.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음.

- **서지**: Inferentia·Gaudi의 고정 shape/bucketing 성질을 벤더 문서로 확인했다([TASK38](TASK38.md) 원칙).
- **초고**: `check_claims.py`로 인용 id 존재·미인용 주장·`[NEEDS-EVIDENCE]`를 검사했다.
- **LaTeX**: 중괄호 균형과 이스케이프되지 않은 `%`를 검사했다(줄 끝 `%`는 공백 억제 관용이므로 제외). **컴파일은 하지 못했다.**
- **그림**: `verify_figures.py` 재실행.

## 결과

### 관측 1 — substrate 클래스 선언의 근거

| 예시 | 확인된 성질 | 출처 |
|---|---|---|
| AWS Inferentia | **입력 shape가 compile 시점에 고정**되고, 가변 크기의 문서화된 해법이 **bucketing**이다. Inferentia2는 dynamic shape를 지원하지 않아 재compile이 필요하다 | AWS Neuron 문서 |
| Intel Gaudi | 그래프의 **정적 사전 compile**을 요구하고 static shape를 권장하며, shape가 바뀌면 재compile이 발생한다(dynamic 지원은 opt-in) | Gaudi 문서 |
| GPU serving stack | **cudagraph capture size 열거** — 이미 [TASK29](TASK29.md)에서 source로 확인 | [CLAIMS 4.1](../../paper/CLAIMS.md) |

**세 예시 모두 "compile 시점에 shape를 고정하고 이산 집합을 열거한다"는 성질을 공유한다.** 이 문단은 그 성질만 진술하고 **세 substrate가 같은 결과를 낸다고 말하지 않는다** — 그런 주장은 GPU 축에 대해서만, source 근거와 승격 조건과 함께 §⑦에 있다.

### 관측 2 — `[NEEDS-EVIDENCE]` 3건의 집행 결과

**① patch 정당화 → 부록 C.** `patches/README.md`의 7개 항목을 부록으로 이식하고 §②는 한 문장으로 줄였다. 부록 문자 순서를 맞추려면 A·B·D도 있어야 하므로 함께 썼다 — A는 descriptor와 층 태그 규칙, B는 **선등록 commit 표**(10건), D는 §4.2와 저장소 기록을 가리킨다. **B가 뜻밖에 강한 부록이다** — 논문이 "선등록했다"고 말할 때 독자가 확인할 수 있는 hash 목록이 된다.

**② validated envelope → §4.3.1 + §9.** 게이트 4개가 각각 어떤 격자를 덮었는지 적고 **"확증은 동시성 8 이하, 이 격자 계열, 이 워크로드에서만 주장한다"** 를 명시했다. 새 주장을 만들지 않고 기존 게이트 주장(1.14–1.17)의 범위를 서술한 것이다.

**③ 계통 오차 → §4.3.2 + CLAIMS 1.18.** 5회 동일 부호를 진술하되 **scope 세 항을 함께** 냈다 — (i) 전부 선등록 허용치 안이라 판정이 뒤집히지 않는다, (ii) 높은 동시성에 집중되며 그 구간은 §4.3.1이 이미 확증에서 제외한다, (iii) 방향이 **보수적**이다(device가 예측보다 덜 준다). 그 다음에 "누락 항 미특정, 후속 모형 개정의 입력"을 적었다. 오독 위험 표에 **"순서를 바꾸면 자기 비판이 결과 부정으로 읽힌다"** 를 처리 규칙으로 넣었다.

### 관측 3 — 캡션 9종

각 캡션이 **그림이 주장하는 한 문장으로 시작하고 그 뒤에 조건을 병기**한다. 모형·절제에서 온 요소는 캡션 안에서 "model", "ablation", "extrapolated"로 표시했다.

| 그림 | 캡션의 주장 문장 | 병기한 조건 |
|---|---|---|
| ① | 재사용은 all-or-nothing이고 문턱은 token이 아니라 요청 수를 센다 | 이 artifact의 층 2(8 slot × 8,192 token, FIFO), 2,000 token 요청, 12/12. 회색은 상위 층 metric, 점선은 **절제(모형)** |
| ② | gap이 이로운지 해로운지는 격자 위 위치가 정하고 부호가 바뀐다 | `max_num_seqs=8`, 사각 계열은 **한 눈금만 추가한 재compile** — 인과의 근거. 1.0000선은 **절제(모형)** |
| ③ | prefill은 모든 동시 세션에 부과되고, 빠뜨린 비용 모형은 동시성에 따라 편향된다 | 이 하드웨어·모델, 속 빈 표식은 직렬화 항 제외 |
| ④ | 모형이 재현이 아니라 **예측**한다 | 파랑·주황·빨강은 **측정 전 commit**, 회색 in-sample은 예측의 증거가 아님 |
| ⑤ | 도달 가능한 headroom의 대부분은 지식이 아니라 조율이다 | 중앙 60 %, 실측 tool latency 워크로드, 예산 3 × 동시성 3 |
| ⑥ | 예측기가 문턱을 못 넘고 자료를 늘려도 좁혀지지 않는다 | 로그 축, 녹색 밴드는 **합성 gap에서만 정의되는** 문턱 |
| ⑦ | 재compile은 구성 선택으로 다룰 만큼 싸고 비용이 예측된다 | 점선은 **사각 두 점만으로 적합**, 원은 그것을 시험한 관측 |
| ⑧ | device 실측 없이 고른 구성이 device time을 회수하고, 이득의 출처는 조건부다 | 채널 A′/B, ×는 **측정 전 commit**, N=8은 pool 지배, N=6 신규 seed는 이미 17/18 재사용 |
| ⑨ | 이득은 생존율이 포화하는 곳에서 끝나며 그곳은 물리 한계의 3분의 1이다 | 눈금 `(1,4,6,8,10,B)` 고정, 세로 점선은 **3점 적합의 외삽**, 원은 유일한 미포화 셀, 동시성 10 이하 |

### 관측 4 — 인용

본문의 인라인 arXiv id를 전부 `\cite`로 바꿨다(18개). 마크다운에 `[@key]` 표식을 도입해 **이송기가 `\cite{}`로 옮기므로 초고가 계속 source of truth로 남는다.** 확인되지 않은 서지는 `refs.bib`에서 `TODO` 주석으로 유지했다.

### 관측 5 — 저자 확정과 제출 패키지

| 순서 | 이름 | 소속 | 이메일 |
|---|---|---|---|
| 1 (제1저자) | Dongkyeom Jang | 동국대학교 컴퓨터AI학과 | `jangelliot0404@dgu.ac.kr` |
| 2 | In-Nea Wang | 동국대학교 사물인터넷 혁신융합대학 | `innea@dgu.ac.kr` |
| 3 (**교신저자**) | Junho Jeong | 동국대학교 컴퓨터AI학과 | `yanyenli@dongguk.edu` |

`\author` + `\thanks` 3개로 반영했다. **소속 영문 표기 중 사물인터넷 혁신융합대학은 `IoT Convergence`로 잠정 표기하고 `main.tex`에 TODO 주석을 달았다** — 기관의 공식 영문 명칭을 확인하지 못했고, 지어내지 않았다.

감사의 글에 **리벨리온 CA25 장비 제공**을 적고, **AI 사용 고지**를 별도 절로 활성화했다. 라이선스는 **CC BY 4.0** 확정이다.

## 핵심 발견

1. **`universal` — 자기 비판을 논문에 실을 때는 scope를 먼저, 미해결을 나중에 적는다.** 계통 오차를 그냥 쓰면 게이트 결과 전체가 흔들리는 것처럼 읽힌다. "선등록 밴드 안 → 확증 제외 구간에 집중 → 보수적 방향 → 누락 항 미특정" 순서여야 **정직이 결과 부정으로 오독되지 않는다.**
2. **`universal` — 선등록 commit 표는 부록으로 실을 값어치가 있다.** "선등록했다"는 주장은 hash 목록이 있을 때만 검증 가능한 주장이 된다.
3. **`universal` — 캡션은 그림의 설명이 아니라 그림의 주장이다.** 주장 문장으로 시작하고 조건을 병기하면, 본문을 읽지 않는 독자가 얻는 것과 논문이 주장하는 것이 어긋나지 않는다.
4. **`universal` — 초고를 source of truth로 유지하려면 LaTeX 전용 요소도 마크다운에 표식을 둬야 한다.** `[@key]`와 `<!-- TABLE: -->`가 그것이다. 이송기가 덮어쓰는 구조에서 LaTeX만 고치면 다음 재생성에서 사라진다.

## 해석

- **(해석)** `[NEEDS-EVIDENCE]` 3건이 모두 "배치 판정"이었다는 [TASK41](TASK41.md)의 관찰이 집행에서 확인됐다. 세 건 다 **새 측정 없이** 닫혔고, 그중 둘은 오히려 논문을 **더 보수적으로** 만들었다(확증 범위 명시, 계통 오차 자백). **신규 주장 금지 규칙이 있으면 미해결이 "빈 곳"이 아니라 "배치 미정"으로만 쌓인다.**
- **(해석)** 저자란이 채워지면서 이 저장소의 산출물이 처음으로 **되돌리기 어려운 형태**에 가까워졌다. 그래서 제출 순서를 체크리스트로 못 박고, 컴파일·육안 검수를 arXiv 업로드 **앞에** 두었다. 첫 빌드가 첫 검증인 소스를 검수 없이 올리는 것이 이 시점의 가장 큰 위험이다.
- **(해석)** 소속 영문 명칭을 지어내지 않고 TODO로 남긴 것은 사소해 보이지만 [TASK38](TASK38.md)의 "1차 출처로 확인" 원칙과 같은 성질이다. **저자 정보는 서지보다 정정 비용이 크다** — arXiv는 v1 메타데이터를 목록에 남긴다.

## 확인되지 않은 사항

- **LaTeX 컴파일** (`UNKNOWN`, 이월). TeX 미설치. 첫 Overleaf 빌드가 첫 검증이다.
- **그림 육안 검수** (`UNKNOWN`, 이월). 그림 ⑨는 2패널이라 확인 필요가 더 크다.
- **사물인터넷 혁신융합대학의 공식 영문 명칭** (`UNKNOWN`). `main.tex`에 TODO 주석.
- **소속 기관의 preprint 라이선스 규정** (`UNKNOWN`). CC BY 4.0과 충돌 여부 확인 필요.
- **`refs.bib`의 `TODO` 6건** (`PARTIAL`). 저자 전체 목록 미확인.
- **표 상호참조** — 캡션은 있으나 본문이 표를 `\ref`로 가리키지 않는다.
- **저장소 공개 방식** (`UNKNOWN`). 부록 D의 신규 `[NEEDS-EVIDENCE]`.

## 실패 / 무효 시도

없다. 이송기를 네 번 고쳤다 — 부록 heading 층 이동, 인용 표식, 표 캡션 표식, `…` 이스케이프. 모두 생성물 검사로 잡았고 측정과 무관하다.

**`Section~⑦`처럼 tilde를 넣어 쓴 상호참조가 이송기 규칙과 어긋나 이중 접두어를 만들 뻔했다.** 생성물에서 발견해 마크다운을 `Section ⑦`로 고쳤다 — [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md)의 "생성물을 검사한다"가 또 한 번 작동한 사례다.

## 연구 원칙에 미치는 영향

1. **논문에 싣는 자기 비판은 scope를 앞에, 미해결을 뒤에 배치한다.**
2. **"선등록했다"는 주장에는 commit hash 목록을 첨부한다.**
3. **저자·소속 정보는 확인되지 않으면 지어내지 않고 TODO로 남긴다.** 정정 비용이 서지보다 크다.
4. **초고가 source of truth인 이송 구조에서는 LaTeX 전용 요소도 마크다운 표식으로 표현한다.**

## 다음 작업

1. **첫 Overleaf 빌드** — `bash paper/latex/make_package.sh` → zip → 업로드 → pdfLaTeX 2회.
2. **그림 육안 검수** — 겹침·잘림.
3. 소속 영문 명칭·기관 preprint 규정 확인, `refs.bib` `TODO` 보완.
4. **제출은 저자 계정 작업이며 이 저장소의 범위 밖이다.** 순서는 [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `6ef9d7a`
- 이송: `env -u PYTHONPATH python3 paper/latex/md2tex.py` → `sections/` 12파일
- 초고 검증: `env -u PYTHONPATH python3 paper/draft/check_claims.py` → **47/47, 미존재 0, 미인용 0, NEEDS-EVIDENCE 1**(부록 D)
- 그림 검수: `env -u PYTHONPATH python3 paper/figures/verify_figures.py` → 177 checks, 0 mismatches
- 패키징: `bash paper/latex/make_package.sh` → `figures/` 9 PDF (6.4 MB, gitignored)
- 예산: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
