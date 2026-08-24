# TASK37 — 논문 조립: 서사·주장 매핑·그림·related work·초록

## 상태

DONE

측정 없이 논문 조립 산출물 7종을 만들었다. **미해결로 남은 것은 사용자 판정이 필요한 항목 하나(시스템 명칭)와 Advisor 확인이 필요한 서지 2건이다.**

## 판정

측정이 없으므로 판정 기준·선등록이 없다. 산출물의 완결성은 다음으로 확인했다.

| 항목 | 결과 |
|---|---|
| 3막 서사 | [paper/OUTLINE.md](../../paper/OUTLINE.md) — 진단(기전 3개) → 불가능성(벽 4개) → 처방(compile-time), 일반성·한계·부록 포함 |
| 주장–증거 매핑 | [paper/CLAIMS.md](../../paper/CLAIMS.md) — **41개 주장** 전부에 근거 TASK·층 태그·그림 배정 |
| `stack` → `class` 오독 전수 점검 | **10개 항목이 "오독 위험 높음/중간"** 으로 식별되고 각각 본문 처리 방식을 지정 |
| 그림 | [paper/figures/](../../paper/figures/) — **8개 SVG 생성 완료**, 데이터 출처 경로를 [SOURCES.md](../../paper/figures/SOURCES.md)에 기록 |
| Related work | [paper/RELATED.md](../../paper/RELATED.md) — 문제 분류학 배치. 서지 **10건 확인**, 2건 `UNKNOWN`/`PARTIAL` |
| 한계 | [paper/CLAIMS.md](../../paper/CLAIMS.md) 말미 **9개 항목** |
| 초록 | [paper/ABSTRACT.md](../../paper/ABSTRACT.md) — 국·영문 각 3문단 + 조건 병기 점검표 |
| 명칭 후보 | [INDEX.md 결정 5](INDEX.md#결정-5--시스템-명칭-충돌)에 **후보 5개** 기입. **판정은 사용자** |
| 투고 타깃 | [paper/VENUES.md](../../paper/VENUES.md) — **3개**, 마감·분량 조사 완료(2건 확인, 2개 항목 `UNKNOWN`) |

## 날짜

2026-08-24

## 목적

[TASK35](TASK35.md)로 측정 단계가 종료되고 [TASK36](TASK36.md)이 마지막 미해결 확증을 닫았으므로, 축적된 36개 TASK를 **투고 가능한 논문의 뼈대**로 조립한다. 조립의 요건은 서사가 아니라 **추적 가능성**이다 — 모든 주장이 근거 TASK와 층 태그로 이어지고, 인스턴스 상수가 클래스 사실로 새어 나가지 않아야 한다.

## 배경

관련 TASK: 전부. 특히 [TASK16](TASK16.md)(층 태깅 규칙), [TASK29](TASK29.md)(절제·일반성), [TASK32](TASK32.md)(선행 연구 차용), [TASK33](TASK33.md)(분기), [TASK35](TASK35.md)·[TASK36](TASK36.md)(확증).

[결정 5](INDEX.md#결정-5--시스템-명칭-충돌)가 "논문 조립 단계에서 시스템 명칭을 변경한다"로 해소돼 있으므로 이 TASK가 후보 제시를 포함한다.

## 시작 상태

- Base commit: [TASK36](TASK36.md) 작업 트리
- 측정 없음. serving 기동 0회, 재compile 0회, device 접근 0회
- matplotlib 미설치 — 설치는 [CLAUDE.md](../../CLAUDE.md) 원칙 11의 승인 대상이므로 **설치하지 않고** 의존성 없는 SVG 생성기를 작성했다

## 수행 내용

1. **서사 설계**: 3막 구조를 문서화하고 각 절에 근거 TASK와 그림을 배정했다.
2. **주장–증거 매핑**: 41개 주장을 표로 만들고 층 태그를 붙였다. `stack` 주장이 조건 없이 읽힐 때 `class`로 오독되는지 전수 점검하고, 위험 항목마다 본문 처리 규칙을 지정했다.
3. **그림 8종 생성**: 의존성 없는 SVG 플로터([svgplot.py](../../paper/figures/svgplot.py))와 생성 script([make_figures.py](../../paper/figures/make_figures.py))를 작성했다. 값은 상수 표에 두고 출처를 [SOURCES.md](../../paper/figures/SOURCES.md)에 기록했다. **모형·절제에서 나온 값은 그림 안에 그렇게 표시했다.**
4. **Related work**: "분포로 충분한 레버 대 개별 draw가 필요한 레버"라는 문제 분류학으로 배치하고, web으로 서지를 확인했다.
5. **한계 절**: 9개 항목으로 정리했다.
6. **초록**: 국·영문을 쓰고 각 수치에 병기한 조건을 점검표로 남겼다.
7. **명칭 후보·투고 타깃**: 충돌 검색을 거친 후보 5개와 마감·분량을 조사한 타깃 3개를 정리했다.

## 변경된 파일

- `paper/OUTLINE.md`, `paper/CLAIMS.md`, `paper/RELATED.md`, `paper/ABSTRACT.md`, `paper/VENUES.md` (신규)
- `paper/figures/svgplot.py`, `paper/figures/make_figures.py`, `paper/figures/SOURCES.md`, `paper/figures/fig1–fig8*.svg` (신규)
- `docs/research/TASK37.md` (신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음. 검증은 문서 수준이다.

- 그림: 생성 script를 실행해 8개가 전부 만들어지는지, 캔버스 밖으로 나가는 text 요소가 없는지 기계적으로 검사했다(8/8 `OK`).
- 그림 ④·⑧은 [TASK36](TASK36.md)의 `config_device.n6.json`을 **실제로 읽는다**. 파일이 없는 clean checkout에서는 문서 기록값으로 대체되며 그 사실을 script와 [SOURCES.md](../../paper/figures/SOURCES.md)에 명시했다.
- 서지: arXiv abs/html과 학회 CFP를 직접 조회했다.

## 결과

### 관측 1 — 선행 시스템의 명칭이 되돌아왔다

[결정 5](INDEX.md#결정-5--시스템-명칭-충돌)의 근거인 arXiv:2511.02230의 제목을 버전별로 확인했다.

| 버전 | 날짜 | 시스템 이름 |
|---|---|---|
| v1–v3 | 2025-11-04 ~ 2026-01-30 | **Continuum** |
| v4 | 2026-05-04 | **CacheTTL** |
| v5 | 2026-05-11 | **Continuum** |
| **v6 (현재)** | **2026-05-25** | **Continuum** |

**작업 지시문은 이 시스템을 "CacheTTL(구 Continuum)"으로 지칭했으나, 현재 arXiv 최신판(v4가 아니라 v6)의 이름은 다시 `Continuum`이다.** 즉 **명칭 충돌은 해소되지 않았고 여전히 살아 있다.** ICLR 2026 *Lifelong Agents* workshop 포스터로도 `Continuum` 제목으로 등재돼 있다.

### 관측 2 — 2026년 인접 결과 7건, 그러나 겹치는 음성 결과는 없다

| 시스템 | 서지 | 레버 |
|---|---|---|
| ThunderAgent | arXiv:2602.13692, **ICML 2026 Spotlight** | program-aware scheduler + tool resource manager |
| SAGA | arXiv:2605.00528 | workflow-atomic 스케줄링 + tool-aware TTL |
| MORI | arXiv:2606.00866 | 유휴도 순위 기반 GPU↔CPU offload |
| Leyline | arXiv:2606.01065 | 응용이 내리는 KV cache directive |
| **ConServe** | arXiv:2606.01839 | **예측을 쓰지 않도록 스케줄링 단위를 conversation으로 올린다** |
| SMetric | arXiv:2607.08565 | session-centric 스케줄링 |
| CacheScout | arXiv:2608.14624 | agent 실행 전이의 online 학습 |

**어느 것도 "반환 시각 재배치"를 레버로 삼지 않는다.** 전부 배치·회수·offload·스케줄링 단위 축이다. **ConServe만이 이 연구의 음성 결과와 같은 방향의 독립 증거**이고, 그쪽은 "예측을 불필요하게 만든다"로, 이쪽은 "왜 예측이 불가능한지와 예측 없이 살 수 있는 레버가 어디인지"로 답한다.

### 관측 3 — 오독 위험이 높은 주장이 10개다

전수 점검에서 조건 없이 읽으면 `class`로 오독될 `stack` 주장이 10개 나왔다. 그중 **가장 위험한 것은 논문의 헤드라인 숫자 X = +10 %** 이며, 초록·서론·결론 전부에서 `N`, substrate, 워크로드를 병기하고 [TASK36](TASK36.md)의 N=6 값과 함께 **구간**으로 제시하기로 했다.

### 관측 4 — 서지 2건을 특정하지 못했다

작업 지시문이 지목한 `LENS`와 `KV-RM`을 web 검색으로 특정하지 못했다. `KV-RM`은 설명이 가장 가까운 **CacheScout**(arXiv:2608.14624, "Learning Agent Execution for **KV-Cache Management** in Agentic Serving")으로 잠정 배치했고, `LENS`는 `UNKNOWN`으로 남겼다. **둘 다 Advisor 확인이 필요하다.**

## 핵심 발견

1. **`universal` — 주장 표를 층 태그로 전수 점검하면 오독 위험이 국소화된다.** 41개 중 10개가 위험이고 그중 4개가 논문의 주요 수치다. **위험이 어디 있는지 목록으로 나오면 본문 작성이 검토가 아니라 집행이 된다.**
2. **`universal` — 음성 결과의 배치는 "무엇을 반박하는가"가 아니라 "무엇을 설명하는가"로 잡는 것이 정확하다.** 선행 연구의 TTL은 분포의 문제이고 이 연구의 반환 재배치는 draw의 문제다. 같은 추정자가 앞에서는 충분하고 뒤에서는 원리적으로 부족하다는 것이 [TASK32](TASK32.md)의 실측 그 자체다.
3. **`universal` — 명칭 충돌은 선행 논문의 버전을 따라 움직인다.** v4에서 사라졌다가 v6에서 돌아왔다. **개명 판단의 근거는 "그들이 지금 무엇을 쓰는가"이지 어느 시점의 스냅숏이 아니다.**
4. **`universal` — 그림은 값의 출처와 그 값이 측정인지 모형인지를 그림 자체에 담아야 한다.** ①의 LRU 곡선과 ②의 연속 격자 선은 절제 **계산**이며, 표시가 없으면 실측으로 읽힌다.

## 해석

- **(해석)** 이 연구의 투고 위험은 결과가 약해서가 아니라 **결과의 조건이 많아서**다. 단일 substrate·단일 모델·trace 1종이라는 한계 위에서 +10 %를 말하면 리뷰어는 "이 숫자가 어디까지 가는가"를 묻는다. [CLAIMS.md](../../paper/CLAIMS.md)의 층 태깅과 [TASK29](TASK29.md)의 절제가 그 질문에 대한 준비된 답이다.
- **(해석)** [TASK36](TASK36.md)이 논문 서사에 늦게 들어온 수정 하나를 만들었다. "지배 인자는 `batch_size`"는 무조건이 아니라 **회수 가능한 캐시 손실이 남아 있을 때**의 진술이다. 그림 ⑧이 두 N을 나란히 놓아 그 조건부성을 시각으로 보인다.
- **(해석)** ConServe의 존재는 위협이 아니라 기회다. 서로 다른 substrate와 방법으로 같은 방향의 결론에 도달한 독립 결과가 있다는 것은 이 연구의 음성 결과가 이 stack의 특수성이 아니라는 근거다. **본문에서 그것을 명시적으로 인용한다.**

## 확인되지 않은 사항

- **시스템 명칭** — 후보 5개를 제시했고 **판정은 사용자**다. [결정 5](INDEX.md#결정-5--시스템-명칭-충돌)에 기입했다.
- **`LENS`의 정체** (`UNKNOWN`), **`KV-RM`의 정체** (`PARTIAL`, CacheScout로 잠정 배치). Advisor 확인 필요.
- **MLSys 2027 분량 규정** (`UNKNOWN`, CFP 미발표), **EuroMLSys 2027 CFP** (`UNKNOWN`).
- **SAGA 저자 전체 목록** (`PARTIAL`) — arXiv id와 제목만 확인했다.
- 그림의 **시각적** 품질. 이 host에 SVG 래스터라이저가 없어 기계적 경계 검사만 했고 사람 눈으로 보지 못했다.

## 실패 / 무효 시도

없다. 다만 matplotlib이 없어 그림 도구를 새로 써야 했고, 그 결과 **그림의 값이 코드 상수 표로 노출되는** 부수 효과가 생겼다. 추적 가능성 면에서는 오히려 낫다.

## 연구 원칙에 미치는 영향

1. **논문 조립 산출물도 근거 추적 규칙을 따른다.** 그림의 모든 값에 출처 TASK와 artifact 경로를 붙이고, 측정과 모형을 그림 안에서 구분한다.
2. **선행 연구의 명칭·버전은 인용 시점에 다시 확인한다.** 버전마다 시스템 이름이 바뀐 사례를 이미 만났다.
3. **`stack` 주장의 오독 위험 점검을 논문 작성 전 단계의 산출물로 만든다.** 본문을 쓰면서 판단하지 않는다.

## 다음 작업

1. **사용자 판정 대기**: 시스템 명칭([결정 5](INDEX.md#결정-5--시스템-명칭-충돌)).
2. **Advisor 확인 대기**: `LENS`·`KV-RM` 서지.
3. 명칭 확정 후 arXiv preprint 초고 작성 → [paper/VENUES.md](../../paper/VENUES.md)의 1단계.
4. 본 학회 리뷰가 GPU 근거를 요구하면 [결정 4](INDEX.md#결정-4--gpua6000-교차검증-착수-시점)의 조건이 발동한다.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- 그림 생성: `env -u PYTHONPATH python3 paper/figures/make_figures.py`
- 그림 값 출처: [paper/figures/SOURCES.md](../../paper/figures/SOURCES.md)
- 서지 조회: arXiv abs/html (2511.02230 v4·v5·v6, 2502.13965, 2507.07400, 2602.13692, 2605.00528, 2606.00866, 2606.01065, 2606.01839, 2607.08565, 2608.14624, 2403.02310), mlsys.org, 2027.eurosys.org, iclr.cc. 조회 시각 2026-08-24
- 명칭 충돌 검색: 후보별 web 검색. 결과는 [결정 5](INDEX.md#결정-5--시스템-명칭-충돌) 표
- 예산 사용: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
