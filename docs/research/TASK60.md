# TASK60 — 3.3 판정 근거 확인, scheduler 소스 확인, chunked prefill 문헌 조사

## 상태

DONE

## 판정

read-only 조사다. **신규 측정 0, compile 0, serving lifecycle 0.**
기존 판정·수치를 하나도 수정하지 않았다.

| 항목 | 결과 |
|---|---|
| **A. 주입 실험 판정 근거** | **선등록 확인.** 문턱 5.0, 동시성 기준(공통 교집합), 대조 초과 시 `PARTIAL` 강등 규칙이 **전부 선등록 문서에 있고** commit `ba6ee2b`(22:00:47)이 측정 시작(22:01:09)보다 **22초 앞선다** |
| **B. scheduler 우선순위** | **배타와 우선순위가 둘 다 소스에서 확인된다.** 다만 **서로 다른 두 줄**에서 나오고, 우선순위는 **`running`에 자리가 있을 때만** 성립하는 조건부다 |
| **C. chunked prefill 문헌** | "prefill이 decode를 지연시킨다"는 문장은 **Sarathi-Serve(OSDI '24)에만 있고 원 Sarathi(arXiv:2308.16369)에는 없다.** 원문 3곳을 절 위치와 함께 인용했다 |
| **D. 9/24 대 10/24** | **[TASK58](TASK58.md)에서 이미 확정됨.** 재작업하지 않고 지목한다 |

## 날짜

2026-09-09

## 시작 상태

- 시작 commit `26d45f60af9cb626ad5f4d2dc18603e09cdb0736`
- `git status --short`: `?? .idea/`만
- 설치 package: `vllm 0.22.0`, `vllm_rbln 0.11.1`(`pip show` 확인)

## 변경된 파일

- `docs/research/TASK60.md` (신규), `docs/research/INDEX.md` (갱신)
- `paper/latex/refs.bib` (**항목 1개 추가**: 원 Sarathi)

**기존 TASK 문서·판정·수치를 수정하지 않았다.**

## 결과

### A. 주입 실험의 판정 근거 — 선등록 확인

선등록 문서: [PREFILL_TAX_PREREG.md](PREFILL_TAX_PREREG.md).
기록 TASK: **[TASK22](TASK22.md)** — "prefill 배타 실행의 직접 검증과 비용 모델 v2".
실험 조건: bystander 4세션 streaming + 주입 1회, 주입 **0(대조)/500/2,000/6,000**
token, 수준마다 3반복(총 12 run).

#### A-1. 선후 관계

```
$ git show -s --format="%H%n%ci%n%s" ba6ee2b
ba6ee2bdee53266e339c7f8b4cb73e7f4f96f7a5
2026-08-21 22:00:47 +0900
docs+exp: prefill 배타 실행 직접 검증 선등록

$ git show --stat --format="" ba6ee2b
 docs/research/PREFILL_TAX_PREREG.md         | 173 +++++
 experiments/npu/analysis/prefill_tax.py     | 130 +++++
 experiments/npu/stage2/prefill_tax_probe.py | 252 +++++++

$ cat results/npu/stage2/20260821-220100-prefill-tax/measurement-start.txt
2026-08-21T22:01:09+09:00
```

**선등록 commit이 측정 시작보다 22초 앞선다.** 그 commit이 선등록 문서와 probe·분석기를
함께 담았다.

#### A-2. 두 기준이 선등록에 있었는가 — **있다**

**문턱 5.0** ([PREFILL_TAX_PREREG.md](PREFILL_TAX_PREREG.md) `### 판정 1 — 스파이크 존재`):

> **사전 등록 문턱: 스파이크 / baseline ≥ 5.0**
>
> | 판정 | 조건 |
> | 존재 | 주입이 있는 9 run **전부**에서, K=4 bystander **전부**가 문턱을 넘는다 |

문턱의 근거도 측정 전에 적혀 있다 — baseline 약 11.5 ms([TASK13](TASK13.md))에
500 token prefill 약 0.09 s를 외삽하면 약 8×이므로 그보다 낮은 5.0을 잡았다는 것이다.

**동시성 기준** (같은 문서 `### 판정 2 — 동시성`):

> 각 bystander의 스파이크 구간 `[start, end]`이 **서로 전부 겹치면** 동시로 본다
> (`max(start) < min(end)`).
>
> | 동시 | 주입이 있는 9 run 전부에서 K개 구간이 공통 교집합을 갖는다 |

**네 구간의 공통 교집합 존재가 선등록된 기준이다.** [TASK59](TASK59.md) 감사 1이
확인한 대로, 실제 관측(시작 시각 차 0.082–0.241 ms, 종료 차 0.101–0.432 ms)은
**이 기준보다 강하다.** 두 문장을 구분해 써야 한다.

#### A-3. 대조 초과 → `PARTIAL` 강등이 선등록 규칙대로였는가 — **그렇다**

같은 문서 `### 대조 구간`:

> 주입이 없는 3 run에서 최대 간격 / baseline이 **문턱 5.0 미만**이어야 한다. 넘으면
> 스파이크가 주입 때문이라는 귀속이 약해지므로 그 사실을 기록하고 판정 1을
> `PARTIAL`로 낮춘다.

[TASK22](TASK22.md)가 대조 3 run에서 초과(최대 18.5×)를 관측하고 판정 1을 `PARTIAL`로
낮췄다. **사후 재량이 아니라 선등록의 집행이다.** 발생 시각은 전부 t < 0.33 s로
주입 창 [3.01, 4.22] s와 분리된다([TASK59](TASK59.md) 감사 1-6).

### B. "scheduler는 prefill을 우선 처리한다" — 소스 확인

파일: `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/optimum_scheduler.py`
(설치 `vllm_rbln 0.11.1`).

**주장 두 개를 구분한다.**

#### B-1. 설계 의도 (주석, `:300-306`)

```python
# NOTE The scheduling process is changed like below.
# (1) vllm-rbln distinguishes
#   between requests in the prefill and decode phases.
#   If a request is in the prefill phase,
#   it is given priority and processed exclusively (only one at a time).
# (2) For (1), vllm-rbln schedules the requests WAITING -> RUNNING.
#   In the vLLM, requests are scheduled RUNNING -> WAITING.
```

주석은 **우선순위와 배타를 함께** 말한다. 아래에서 각각이 어느 코드로 실현되는지
분리한다.

#### B-2. **배타** — 확인됨 (`:335-337`, `:465`)

```python
                # NOTE(eunji): prefill request is allowed only one
                if req_index > 0:
                    break
```

한 step에 prefill은 **최대 1건**만 승인된다.

```python
        # Next, schedule the RUNNING requests.
        if req_index == 0:
            while req_index < len(self.running) and token_budget > 0:
```

decode(RUNNING) loop는 **`req_index == 0`일 때만**, 곧 **그 step에 prefill이 하나도
승인되지 않았을 때만** 실행된다. **같은 step에 prefill과 decode가 섞이지 않는다.**

#### B-3. **우선순위** — 확인됨, 단 조건부 (`:327-329`, `:465`)

```python
            while (self.waiting or self.skipped_waiting) and token_budget > 0:
                if len(self.running) == self.max_num_running_reqs:
                    break
```

WAITING loop가 **프로그램 순서상 먼저**(`:327`) 돌고 RUNNING loop가 **뒤**(`:465`)에
온다. WAITING에서 하나가 승인되면 `req_index`가 1이 되어(`:427`) decode loop가
**그 step에 아예 실행되지 않는다.**

**다만 우선순위는 무조건이 아니다.** `len(self.running) == max_num_running_reqs`이면
WAITING loop가 즉시 `break`하므로(`:328-329`) `req_index`가 0으로 남고 decode가
정상 실행된다. 즉 **"자리가 있을 때 대기 중인 prefill이 그 step을 가져간다"** 이지
"실행 중인 decode를 밀어낸다"가 아니다.

#### B-4. 논문 서술 권고

**논문은 배타만 쓰면 된다** — 3.3의 관측(네 세션이 동시에 멈춤)을 설명하는 데 필요한
것은 배타이고, 그것이 코드에서 명확하다. 우선순위를 함께 쓰려면 **"승인 가능한
자리가 있을 때"** 라는 조건을 붙여야 한다.

### C. chunked prefill 문헌 — 1차 출처 확인

#### C-1. 서지 (arXiv abs에서 확인)

| | 원 Sarathi | Sarathi-Serve |
|---|---|---|
| 제목 | **SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills** | **Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve** |
| 저자 | Amey Agrawal, Ashish Panwar, Jayashree Mohan, Nipun Kwatra, Bhargav S. Gulavani, Ramachandran Ramjee (**6인**) | Amey Agrawal, Nitin Kedia, Ashish Panwar, Jayashree Mohan, Nipun Kwatra, Bhargav S. Gulavani, Alexey Tumanov, Ramachandran Ramjee (**8인**) |
| arXiv | **2308.16369** | **2403.02310** |
| 버전 | **v1만** (2023-08-31) | v1 2024-03-04, v2 2024-06-12, **v3 2024-06-17** |
| 게재 | **없음** (arXiv preprint) | **OSDI '24** (USENIX Symposium on Operating Systems Design and Implementation) |
| DOI | `10.48550/arXiv.2308.16369` | `10.48550/arXiv.2403.02310` |

**v1/v2/v3 사이에 제목 변경은 없다.** 두 논문은 저자 구성이 다르다 — Sarathi-Serve가
Kedia와 Tumanov를 추가한 8인이다.

#### C-2. "prefill이 decode를 지연시킨다"는 문장 — **Sarathi-Serve에만 있다**

**원 Sarathi(2308.16369)에는 없다.** 그 논문의 동기는 **GPU 이용률과 pipeline
bubble**이다. 핵심 목표 문장(§3.3):

> "This observation leads us to our key insight that it is possible to construct
> uniformly compute-intensive batches by (1) slicing a large prefill request into
> smaller compute-efficient and uniform chunks using chunked-prefills and (2)
> creating a hybrid batch of a prefill chunk and piggybacking decodes alongside
> this chunk."

**Sarathi-Serve(2403.02310)에 있다.** 원문 3곳이다.

**§3.2 "Throughput-Latency Trade-off"**:

> "However, eagerly scheduling prefills of requests C and D delays the decodes of
> already running requests A and B because an iteration that computes one or more
> prefills can take several seconds depending on the lengths of input prompts.
> Therefore, prefill-prioritizing schedulers can introduce generation stalls for
> ongoing decodes resulting in latency spikes caused by high TBT."

같은 절의 앞 문장이 용어를 정의한다:

> "Iteration-level batching improves system throughput but we show that it comes
> at the cost of high TBT latency due to a phenomenon we call generation stalls."

**§4.2 "Stall-free batching"**:

> "Unlike Orca and vLLM which stall existing decodes to execute prefills,
> Sarathi-Serve leverages the arithmetic intensity slack in decode iterations to
> execute prefills without delaying the execution of decode requests in the system.
> We call this approach stall-free batching."

> "By restricting the computational load in every iteration, stall-free batching
> ensures that decodes never experience a generation stall due to a co-running
> prefill chunk."

인용 출처는 arXiv HTML 판(`https://arxiv.org/html/2403.02310v3`)이다. **게재본(OSDI)의
절 번호가 arXiv v3와 같은지는 확인하지 못했다**(아래 `UNKNOWN`).

#### C-3. vLLM 공식 문서 (보조 출처)

URL: `https://docs.vllm.ai/en/stable/configuration/optimization/`, 절 제목
**"Chunked Prefill"**.

> "Chunked prefill allows vLLM to process large prefills in smaller chunks and
> batch them together with decode requests."

> "In V1, chunked prefill is enabled by default whenever possible."

> "With chunked prefill enabled, the scheduling policy prioritizes decode requests.
> It batches all pending decode requests before scheduling any prefill operations."

**이 페이지는 vLLM 버전을 명시하지 않는다.** 이 저장소의 설치본은 `vllm 0.22.0`이며
**RBLN 실행 경로는 chunked prefill을 쓰지 않는다** — 이 문서는 [TASK29](TASK29.md)의
반사실 절제를 위한 배경 출처이지 이 substrate의 동작 근거가 아니다.

#### C-4. refs.bib

**`sarathi2024`(Sarathi-Serve)는 이미 있다.** 이번에 1차 출처로 대조한 결과
**제목·저자 8인·순서·booktitle이 일치**한다. `pages = {117--134}`는 이번 조사에서
**독립 확인하지 못했다**(USENIX·DBLP가 403). 기존 항목을 **고치지 않았다.**

**원 Sarathi는 없어서 항목을 추가했다.**

```bibtex
@article{sarathi2023,
  title   = {{SARATHI}: Efficient {LLM} Inference by Piggybacking Decodes with Chunked Prefills},
  author  = {Agrawal, Amey and Panwar, Ashish and Mohan, Jayashree and Kwatra, Nipun and Gulavani, Bhargav S. and Ramjee, Ramachandran},
  journal = {arXiv preprint arXiv:2308.16369},
  year    = {2023}
}
```

**게재본이 없으므로 preprint 형식이다.** 원 Sarathi와 Sarathi-Serve는 **제목·저자
구성이 다른 별개 논문**이며 v1/v2 제목 차이 문제는 **해당 없다**.

### D. 9/24 대 10/24 — [TASK58](TASK58.md)에서 이미 확정

**재작업하지 않는다.** 확정 위치를 지목한다.

| 항목 | 위치 |
|---|---|
| 반복별 3·3·3 = 9/24 | [TASK58](TASK58.md) `#### 반복별 결과` (문서 291–298행) |
| 합산 9/24 → 24/24 | [TASK58](TASK58.md) `#### 합산` (304–305행) |
| 10/24가 다른 실험임 | [TASK58](TASK58.md) `#### TASK40과 섞지 않는다` (338행) |

원 기록도 일치한다.

- **slot 8 기준 구성의 재사용은 반복별 3건, 합 9/24다.** [TASK35](TASK35.md) 관측 3
  (137–138행)이 `9 → 24 / 24`로 기록했고, [TASK58](TASK58.md)이 원자료에서
  `BASE` b0·b1·b2 = **3 / 3 / 3**으로 재집계했다.
- **10/24는 [TASK40](TASK40.md)의 값이다** (문서 58행):
  `| 8 | B8 / B16 / B24 / B32 | 10/24 / 24/24 / 24/24 / 24/24 | …`
  격자가 `(1,4,6,8,10,B)`로 다르고, [TASK40](TASK40.md)이 B8→B16을
  **"통제되지 않은 인접쌍"** 으로 분류했다.

**두 값은 서로 다른 실험의 결과이며 논문 표에서 섞지 않는다.**

## 핵심 발견

1. **`universal` — 설계 의도를 적은 주석 한 줄이 서로 다른 두 주장을 담을 수 있다.**
   `optimum_scheduler.py`의 주석은 "우선순위"와 "배타"를 한 문장에 넣었는데, 코드에서
   둘은 **다른 줄**(`:335-337` 대 `:465`)이고 **적용 조건도 다르다** — 배타는 무조건,
   우선순위는 `running`에 자리가 있을 때만이다. 주석을 근거로 인용할 때는 어느 부분이
   어느 코드로 실현되는지 확인해야 한다.

2. **`universal` — 같은 연구 그룹의 연속된 두 논문이 서로 다른 문제를 동기로 삼을 수
   있다.** 원 Sarathi는 GPU 이용률·pipeline bubble을, Sarathi-Serve는 decode의
   generation stall을 동기로 삼는다. **"chunked prefill 논문"이라고 뭉뚱그려 인용하면
   틀린 쪽을 가리킬 수 있다.**

3. **`universal` — 선등록이 실제로 판정을 낮춘 사례가 기록으로 남아 있다.**
   대조 초과 → `PARTIAL` 강등은 선등록 문서에 미리 쓰인 규칙의 집행이며, commit 시각이
   측정보다 22초 앞선 것이 git으로 검증된다.

## 해석

- **(해석)** B의 결론은 논문 서술을 **좁히는 방향**이다. 3.3의 관측을 설명하는 데
  필요한 것은 배타이고 그것은 무조건 성립한다. 우선순위를 함께 주장하면 조건을 달아야
  하므로, **배타만 쓰는 편이 더 정확하고 더 강하다.**
- **(해석)** C의 결론은 [TASK29](TASK29.md)의 절제와 논문 §7.2의 대비를 더 날카롭게
  한다. Sarathi-Serve가 없애려는 것(`generation stall`)이 이 substrate에서 관측한
  바로 그것이고, 이 연구의 절제는 그것을 없앴을 때 device time이 **늘어난다**고
  계산했다. **같은 현상을 두 방향에서 다루는 대비**로 세울 수 있다.

## 확인되지 않은 사항

- **OSDI 게재본의 절 번호가 arXiv v3와 같은지** (`UNKNOWN`). 인용문은 arXiv HTML v3
  기준이다. USENIX 논문 페이지와 PDF가 fetcher에 **HTTP 403**을 반환했다.
- **`sarathi2024`의 `pages = {117--134}`** (`UNKNOWN` — 이번 조사에서 독립 확인 실패).
  USENIX·DBLP 모두 403이었다. 기존 항목은 [TASK38](TASK38.md)이 검증한 값이며
  **고치지 않았다.**
- **OSDI '24 proceedings의 ISBN·개최 일자·장소** (`UNKNOWN`, 같은 이유).
- **vLLM 문서 페이지의 대상 버전** (`UNKNOWN` — 페이지가 명시하지 않는다).
- 원 Sarathi 인용문의 절 번호(§3.3)는 fetcher가 보고한 값이며 **HTML 원문에서 절
  번호를 직접 대조하지는 않았다** (`PARTIAL`).

## 실패 / 무효 시도

- USENIX 논문 페이지·PDF, DBLP 레코드가 **HTTP 403**을 반환했다. 게재본의 쪽수·ISBN을
  1차 출처로 확인하지 못했고, **추정으로 채우지 않고 `UNKNOWN`으로 남겼다.**
- arXiv PDF를 내려받았으나 `pdftotext`·`pdftoppm`·python PDF 라이브러리가 없어 텍스트를
  추출하지 못했다. **dependency 설치는 승인 범위 밖이므로 하지 않고** arXiv HTML 판으로
  대체했다.

## 연구 원칙에 미치는 영향

1. **주석을 근거로 쓸 때는 그 주석이 담은 주장을 코드 줄 단위로 분리해 확인한다.**
2. **서지는 "어느 논문이 그 문장을 실제로 담고 있는가"까지 확인한다.** 계열 논문은
   제목이 비슷해도 동기가 다를 수 있다.
3. **1차 출처가 막히면 추정으로 채우지 않고 `UNKNOWN`으로 남긴다.**

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **OSDI 게재본 쪽수·절 번호 확인** — 다른 경로(기관 프록시, ACM/USENIX 로그인)가
   필요하다. 현재 bib의 쪽수는 [TASK38](TASK38.md) 검증값을 유지한다.
2. **논문 3.3의 scheduler 서술 확정** — B-4의 권고(배타만 쓰기)를 반영할지 결정한다.
3. **§7.2의 대비 문장에 Sarathi-Serve 인용문 삽입 여부** — C-2의 원문을 직접 인용할지
   결정한다.

## 재현 정보

- 선등록: **해당 없음** — 신규 측정이 없는 read-only 조사다
- 시작 commit: `26d45f60af9cb626ad5f4d2dc18603e09cdb0736`
- A: `docs/research/PREFILL_TAX_PREREG.md`,
  `git show -s ba6ee2bdee53266e339c7f8b4cb73e7f4f96f7a5`,
  `results/npu/stage2/20260821-220100-prefill-tax/measurement-start.txt`
- B: `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/optimum_scheduler.py`
  `:300-306`(주석), `:327-329`(WAITING loop 진입), `:335-337`(prefill 1건 제한),
  `:427`(`req_index += 1`), `:464-465`(decode loop 게이트). `vllm_rbln 0.11.1`
- C: `https://arxiv.org/abs/2308.16369`, `https://arxiv.org/abs/2403.02310`,
  `https://arxiv.org/html/2403.02310v3`, `https://arxiv.org/html/2308.16369v1`,
  `https://docs.vllm.ai/en/stable/configuration/optimization/`,
  `https://www.microsoft.com/en-us/research/publication/taming-throughput-latency-tradeoff-in-llm-inference-with-sarathi-serve/`
- D: [TASK58](TASK58.md) 291–298·304–305·338행, [TASK35](TASK35.md) 137–138행,
  [TASK40](TASK40.md) 58행
- 예산: **compile 0, serving lifecycle 0, 신규 측정 0, device 접근 0**
