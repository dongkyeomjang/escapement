# TASK38 — 논문 자료 정정과 공개 준비: 서지 3건·그림 검수·명칭 확정·arXiv 점검표

## 상태

DONE

측정 없음. [TASK37](TASK37.md)이 `UNKNOWN`/`PARTIAL`로 남긴 서지 2건이 해소되고 **그중 하나는 오류로 판명돼 정정**했다. 그림 8종의 데이터 상수 138개를 원 TASK 문서와 자동 대조해 **불일치 0**을 확인했다. 시스템 명칭이 **`Escapement`** 로 확정돼 반영했고, arXiv 공개 점검표를 만들었다.

## 판정

측정이 없으므로 선등록·판정 기준이 없다. 산출물 확인 결과는 다음과 같다.

| 항목 | 결과 |
|---|---|
| 서지 정정 | **3건.** `LENS` 특정, `KV-RM` 특정(**철회 상태 발견**), `KV-RM ≈ CacheScout` 잠정 동일시 **오류 정정** |
| 그림 수치 자동 대조 | **138개 항목, 불일치 0.** 8개 그림 전부 |
| 그림 텍스트 목록 | 8개 그림의 문자열 전부를 위치와 함께 추출 ([INSPECTION.md](../../paper/figures/INSPECTION.md)) |
| 명칭 반영 | `Escapement` — [ABSTRACT.md](../../paper/ABSTRACT.md)·[OUTLINE.md](../../paper/OUTLINE.md)·[CLAIMS.md](../../paper/CLAIMS.md), [결정 5](INDEX.md#결정-5--시스템-명칭-충돌) `해소됨` |
| arXiv 점검표 | [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) — 카테고리·라이선스·저자·초록 형식·LaTeX 판단·최종 목록 |
| 일관성 확인 | [CLAIMS.md](../../paper/CLAIMS.md)·[OUTLINE.md](../../paper/OUTLINE.md)에 세 논문 참조 문장이 **없었으므로** 정정 대상 없음. 대신 정정된 배치와 맞물리는 **선행 대비 2줄을 [OUTLINE.md](../../paper/OUTLINE.md)에 추가**했다 |

## 날짜

2026-08-25

## 목적

[TASK37](TASK37.md)이 남긴 서지 미특정 2건을 Advisor 제공 서지로 닫고, 그 결과가 [RELATED.md](../../paper/RELATED.md)의 배치를 바꾸므로 정정한다. 아울러 래스터라이저 부재로 사람 눈 확인이 되지 않은 그림 8종에 대해 **눈을 대신할 수 있는 부분**(수치·텍스트)을 자동화하고, 확정된 시스템 명칭을 반영하며, 승인된 arXiv 선행 공개의 준비 항목을 정리한다.

## 배경

관련 TASK: [TASK37](TASK37.md)(논문 조립, 이 TASK가 정정하는 대상), [TASK32](TASK32.md)(선행 연구 차용), [TASK14](TASK14.md)(층 2 FIFO 하드코딩 — CacheScout 대비의 근거), [TASK23](TASK23.md)(격자 개입 — LENS 대비의 근거), [TASK36](TASK36.md)(그림 ④·⑧의 N=6 원본).

사용자 판정 2건이 이 TASK에 전달됐다: **[결정 5](INDEX.md#결정-5--시스템-명칭-충돌) = `Escapement`**, **arXiv 선행 공개 = 승인**.

## 시작 상태

- Base commit: `3f8308e` ([TASK36](TASK36.md)+[TASK37](TASK37.md))
- 측정 없음. serving 기동 0회, 재compile 0회, device 접근 0회, 설치 0건

## 수행 내용

1. Advisor가 제공한 arXiv id 3건을 **직접 조회해 검증**했다(제목·저자·날짜·초록, 그리고 철회 여부).
2. [RELATED.md](../../paper/RELATED.md)를 정정했다 — §4 신설(LENS·KV-RM), CacheScout를 §3에서 §2로 이동, §2의 공통 전제 문단 추가, §7 서지 상태표 갱신.
3. [OUTLINE.md](../../paper/OUTLINE.md)에 정정된 배치와 맞물리는 선행 대비 2줄을 넣었다.
4. 그림 검수 도구 [verify_figures.py](../../paper/figures/verify_figures.py)를 작성해 [INSPECTION.md](../../paper/figures/INSPECTION.md)를 생성했다.
5. 시스템 명칭 `Escapement`를 반영하고 [결정 5](INDEX.md#결정-5--시스템-명칭-충돌)를 해소로 갱신했다.
6. [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md)를 작성했다. **제출은 하지 않았다.**

## 변경된 파일

- `paper/RELATED.md`, `paper/OUTLINE.md`, `paper/CLAIMS.md`, `paper/ABSTRACT.md` (정정·명칭 반영)
- `paper/figures/verify_figures.py`, `paper/figures/INSPECTION.md` (신규)
- `paper/ARXIV_CHECKLIST.md` (신규)
- `docs/research/TASK38.md` (신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음.

- **서지**: arXiv abs 페이지를 id별로 직접 조회했다. KV-RM은 v1 페이지를 별도로 조회해 철회 시점·주체를 확인했다.
- **그림 수치**: [verify_figures.py](../../paper/figures/verify_figures.py)가 `make_figures.py`의 데이터 상수를 import하고, 같은 값을 원 TASK 마크다운의 표에서 **다시 파싱해** 비교한다. 표가 아니라 문장으로 기술된 값(그림 ①의 문턱)은 해당 문장의 존재로 확인한다.
- **그림 텍스트**: SVG의 `<text>` 요소를 전부 추출해 위치와 함께 나열한다.
- **링크**: 새·수정 문서의 상대 링크가 전부 실재 파일을 가리키는지 확인했다.

## 결과

### 관측 1 — `KV-RM`은 CacheScout가 아니었고, 게다가 철회됐다

| 항목 | 내용 |
|---|---|
| 서지 | **arXiv:2605.09735**, *KV-RM: Regularizing KV-Cache Movement for Static-Graph LLM Serving*. Zhiqing Zhong, Zhijing Ye, Jian Zhang, Weijian Zheng, Bolun Sun, Xiaodong Yu. v1 2026-05-10 |
| 내용 | 정적 그래프 decoder 아래에서 KV-cache 이동을 정규화한다. 논리 KV 이력과 물리 저장을 분리하고 block pager로 활성 상태를 추적해, 파편화된 사상을 transfer group으로 합쳐 **고정 shape attention kernel**에 넣는다. 평가 A100 2장 |
| **상태** | **v2가 2026-06-30에 저자(Zhiqing Zhong)에 의해 철회됐다.** 사유는 결과 해석과 주요 결론의 근거에 영향을 주는 **실질적 오류** |

**[TASK37](TASK37.md)이 `KV-RM`을 CacheScout(arXiv:2608.14624)로 잠정 동일시한 것은 오류였다.** 둘은 서로 다른 논문이고, 다루는 층도 다르다 — KV-RM은 정적 그래프 substrate의 KV 이동, CacheScout는 agentic 워크로드의 학습 기반 eviction이다.

**정정 방침**: KV-RM은 [RELATED.md §4](../../paper/RELATED.md)에 배치하되 **수치·성능 주장을 인용하지 않고 문제 설정만 인용**한다. "고정 shape 커널 위에서 가변 길이와 비동기 완료를 어떻게 흡수하는가"는 이 연구가 마주한 것과 같은 문제이며, KV-RM은 runtime의 KV 이동 정규화로, 이 연구는 compile 시점의 격자·pool 선택으로 답한다. **철회된 결과를 "runtime 정규화가 실패한다"는 근거로 쓰지 않는다** — 어느 방향으로 틀렸는지 알 수 없기 때문이며, 이 연구의 근거는 자기 자신의 [TASK27](TASK27.md)·[TASK28](TASK28.md)·[TASK33](TASK33.md)이다.

### 관측 2 — `LENS`는 같은 substrate 계열의 상보 결과다

| 항목 | 내용 |
|---|---|
| 서지 | **arXiv:2606.18042**, *Latency Prediction for LLM Inference on NPU Systems*. Juhyun Park, Seungwoo Jeong, Jingyu Lee, Kyungyong Lee. 2026-06-16 (v2 06-17) |
| 내용 | LENS = Latency Estimator for NPU Systems. microarchitecture·compiler 정보 없이 NPU 추론 지연을 예측하며, **bucketing이 유발하는 비선형 지연을 명시적으로 포착**한다. bucket당 end-to-end 측정 2회로 프로파일해 입력·출력 길이 조합 전체를 합성. 여러 NPU 벤더·LLM에서 평균 오차 2.15 % |

**이 연구와 가장 가까운 substrate 계열 선행 결과다** — 같은 NPU 격자 구조를 다룬다. 그러나 축이 다르다.

| 축 | LENS | 이 연구 |
|---|---|---|
| 대상 | **단일 요청의 latency** | **시스템 거동** (여러 세션의 device time) |
| 입력 | 요청의 길이 | 동시 요청 **수**의 시간 전개(반환 도착 과정) |
| bucket의 역할 | 예측할 **비선형성의 원인** | 워크로드와 정렬되거나 어긋나는 **격자**이며 그 정렬이 gap 효과의 **부호**를 정한다 |
| 개입 | 없음(예측기) | **격자를 재compile로 바꾸는 개입**으로 인과 확정, 그 격자를 처방으로 되돌림 |

**주의로 기록한 것**: LENS의 2.15 %는 단일 요청 latency 오차이고 이 연구의 0.0040은 pooled ratio 오차다. **같은 양이 아니므로 나란히 비교하지 않는다.**

### 관측 3 — CacheScout 재배치가 이 연구의 위치를 더 정확히 만든다

CacheScout를 GPU agentic KV 관리 계열(§2: MORI·KVFlow·SAGA·ThunderAgent·Leyline)로 옮기면서 **그 계열 전체가 공유하는 전제**가 드러났다.

> 이들은 모두 **회수·배치 정책을 바꿀 수 있다**고 전제한다. KVFlow는 eviction 점수를, CacheScout는 학습된 전이를, MORI는 tier 경계를, Leyline은 응용의 directive를 쓴다.

**이 연구의 substrate는 그 전제를 주지 않는다.** 층 2 회수가 시퀀스 단위 FIFO로 하드코딩돼 있고 `LRUEvictionPolicy` 클래스는 존재하나 사용되지 않는다([TASK14](TASK14.md)). **그 제약이 이 연구를 정책 축에서 밀어내 구성 축으로 보냈다.**

### 관측 4 — 그림 데이터 상수 138개, 불일치 0

| 그림 | 대조 항목 | 일치 | 출처 |
|---|---|---|---|
| ① | 5 | 5 | TASK14, TASK29 |
| ② | 11 | 11 | TASK24 |
| ③ | 24 | 24 | TASK22 |
| ④ | 22 | 22 | TASK25, TASK28, TASK35, TASK36 |
| ⑤ | 45 | 45 | TASK33 |
| ⑥ | 8 | 8 | TASK32 |
| ⑦ | 20 | 20 | TASK35 |
| ⑧ | 3 | 3 | TASK35 |
| **합** | **138** | **138** | — |

**검수 도구를 만드는 과정에서 잡힌 것은 그림의 오류가 아니라 파서의 오류 2건이었다** — TASK24 표의 굵게 표기(`**(1,2,4,6,8)**`)를 벗기지 않아 개입 격자 N=6 행을 못 찾은 것, 그리고 TASK35 X 표의 열이 이미 백분율인데 비율로 오해해 `100 − x`를 계산한 것. 둘 다 고친 뒤 138/138이다. **자동 대조의 첫 산출물이 대조 대상의 오류가 아니라 대조기의 오류였다는 사실 자체가 기록할 값어치가 있다.**

### 관측 5 — arXiv 초록 길이가 실측으로 1,109자 초과다

arXiv 초록 필드는 **공백 포함 1,920자 하드 캡**이다. 현재 [ABSTRACT.md](../../paper/ABSTRACT.md)의 영문 초록은 마크다운 제거 후 **3,029자**로 **1,109자(약 37 %) 초과**한다. 국문 초록은 1,511자다.

**문장 몇 개 다듬는 수준이 아니라 재작성에 가깝다.** 압축 우선순위와 함께, **[CLAIMS.md](../../paper/CLAIMS.md)의 조건 병기 규칙을 압축 후에도 지킨다**는 원칙을 점검표에 명시했다 — 압축의 첫 희생자가 조건이 되면 오독 위험이 그대로 살아난다.

## 핵심 발견

1. **`universal` — 특정하지 못한 서지를 "가장 비슷한 것"으로 잠정 동일시하면 틀린다.** [TASK37](TASK37.md)은 `KV-RM`을 이름이 겹치는 CacheScout로 배치했는데 실제로는 다른 논문이고 다루는 층도 달랐다. **`UNKNOWN`을 `UNKNOWN`으로 두는 편이 잠정 배치보다 낫다** — 잠정 배치는 후속 작업에서 확정으로 굳는다.
2. **`universal` — 인용 대상의 철회 여부를 확인하는 것이 서지 확인의 일부다.** KV-RM은 v1만 보면 정상적인 선행 연구로 읽힌다. **철회 사실을 놓쳤다면 철회된 결과 위에 대비를 세울 뻔했다.**
3. **`universal` — 그림 검수 자동화가 잡는 것은 그림의 오류만이 아니다.** 이번에 잡힌 2건은 전부 대조기 자신의 파서 오류였다. **원본과 사본을 독립적으로 읽어 비교하면 어느 쪽이 틀렸든 드러난다.**
4. **`universal` — 선행 연구 배치는 "무엇을 하는가"보다 "무엇을 전제하는가"로 나누는 편이 정확하다.** GPU agentic KV 관리 계열의 공통 전제(회수 정책 조정 가능)가 이 substrate에서 성립하지 않는다는 것이, 이 연구가 왜 compile-time에 도달했는지에 대한 가장 짧은 설명이다.

## 해석

- **(해석)** 발견 4를 [TASK37](TASK37.md)의 문제 분류학(분포로 충분한 레버 대 개별 draw가 필요한 레버)과 합치면 **전제 두 개**가 이 연구의 자리를 정한다. (1) §2 계열은 회수 정책을 바꿀 수 있다고 전제하는데 이 substrate는 FIFO 고정이다. (2) §1의 TTL 계열은 분포 추정으로 충분한 레버를 쓰는데 이 연구가 겨눈 반환 재배치는 개별 draw를 요구한다. **두 전제가 모두 없을 때 남는 것이 compile-time 구성이다.** 이 진술은 논문 서론의 위치 설정으로 그대로 쓸 수 있다.
- **(해석)** LENS의 존재는 위협이 아니라 지반이다. **NPU bucketing의 비선형성이 독립적으로 확인되고 예측 가능해졌다는 것**은 이 연구의 기전 ①이 이 인스턴스의 특이성이 아니라는 방증이다. 다만 LENS는 여러 벤더에서 재는 예측기이고 이 연구는 한 인스턴스에서 개입하는 실험이므로 **일반성 주장을 LENS에 기대어 강화하지 않는다** — 그것은 인용으로 얻을 수 있는 것이 아니다.
- **(해석)** 그림 검수표는 사람 눈을 **대체하지 못한다.** 수치가 맞고 텍스트가 캔버스 안에 있어도 요소가 겹칠 수 있다. 그 한계를 [INSPECTION.md](../../paper/figures/INSPECTION.md) 머리에 명시했다.

## 확인되지 않은 사항

- **그림의 시각적 품질** (`UNKNOWN`). 요소 겹침은 여전히 확인되지 않았다. 래스터라이저 설치는 [CLAUDE.md](../../CLAUDE.md) 원칙 11의 승인 대상이다.
- **SVG → PDF 변환 경로** (`UNKNOWN`). LaTeX 제출에 필요하나 이 host에 변환기가 없다. `make_figures.py`에 PDF 백엔드를 추가하는 대안이 있으며 **사용자 판정이 필요**하다.
- **저자 표기·소속·라이선스·AI 사용 고지** (`UNKNOWN`). [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §3·§6.
- **MLSys 2027 분량 규정** (`UNKNOWN`, CFP 미발표. [TASK37](TASK37.md)에서 이월).
- **SAGA 저자 전체 목록** (`PARTIAL`, [TASK37](TASK37.md)에서 이월).
- KV-RM 철회의 **구체적 오류 내용** (`UNKNOWN`). arXiv 철회 공지에 상세가 없다. 이 연구는 그 논문의 결과에 기대지 않으므로 영향이 없다.

## 실패 / 무효 시도

**[TASK37](TASK37.md)의 `KV-RM ≈ CacheScout` 잠정 동일시가 오류로 판명됐다.** 이 TASK가 정정했다. [TASK37](TASK37.md) 자체는 그 배치를 `PARTIAL`로 표시하고 "Advisor 확인 필요"를 달아 두었으므로 기록 규칙은 지켜졌으나, **잠정 배치를 만든 것 자체가 불필요한 위험이었다** — 발견 1에 그렇게 적었다.

검수 도구 작성 중 파서 오류 2건이 있었고 둘 다 수정했다.

## 연구 원칙에 미치는 영향

1. **특정하지 못한 서지는 잠정 배치하지 않고 `UNKNOWN`으로 둔다.** 이름이나 설명이 비슷하다는 것은 동일성의 증거가 아니다.
2. **인용 전에 철회·개정 여부를 확인한다.** 버전이 여럿인 preprint는 최신 버전의 상태를 본다.
3. **선행 연구는 "무엇을 하는가"가 아니라 "무엇을 전제하는가"로 배치한다.** 전제가 다르면 경쟁이 아니라 상보다.
4. **자동 대조는 원본과 사본을 독립 경로로 읽어야 의미가 있다.** 같은 상수를 두 번 읽으면 아무것도 검증하지 못한다.

## 다음 작업

1. **논문 본문 집필** — [OUTLINE.md](../../paper/OUTLINE.md)를 따라 마크다운 초고. 착수를 막는 사용자 판정은 없다.
2. 사용자 확인 항목: [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6 (저자·라이선스·AI 고지·SVG→PDF 변환 도구 승인).
3. 그림 육안 검수 — 브라우저로 열어 [INSPECTION.md](../../paper/figures/INSPECTION.md) §2와 대조.
4. `paper/abstract_arxiv.txt` 압축본 작성 (본문 집필 후).
5. 후속 연구 항목은 [INDEX.md 후속 연구](INDEX.md#후속-연구) 절 — **사용자 지시 없이 착수하지 않는다.**

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `3f8308e`
- 그림 검수: `env -u PYTHONPATH python3 paper/figures/verify_figures.py` → `paper/figures/INSPECTION.md` (138 checks, 0 mismatches)
- 그림 재생성: `env -u PYTHONPATH python3 paper/figures/make_figures.py`
- 서지 조회: arXiv abs/html — 2605.09735(및 v1), 2606.18042, 2608.14624. 조회 시각 2026-08-25
- 초록 길이 실측: 영문 3,029자 / 국문 1,511자 (마크다운 제거 후). arXiv 상한 1,920자
- 예산 사용: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
