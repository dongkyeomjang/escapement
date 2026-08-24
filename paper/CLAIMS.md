# 주장–증거 매핑표

시스템 명칭: **`Escapement`** ([결정 5](../docs/research/INDEX.md#결정-5--시스템-명칭-충돌), 사용자 판정 2026-08-25). 아래 막 3의 주장들이 그 시스템의 주장이다.

논문의 모든 주장을 **주장 → 근거 TASK → 층 태그 → 그림**으로 잇는다. 층 태그 규칙은 [TASK16](../docs/research/TASK16.md)의 것을 그대로 쓴다.

| 태그 | 뜻 |
|---|---|
| `silicon` | 이 가속기 고유의 값 |
| `stack` | 이 software stack·이 compile 구성 고유의 값 |
| `class` | 이 설계 범주(이산 batch 격자 / 고정 slot pool / 배타 prefill 등) 일반의 **형태** |
| `universal` | 방법론적 사실. substrate와 무관 |

**본문 표기 규칙**: `stack` 주장은 본문에서 반드시 **구성 조건을 함께** 적는다(예: "이 artifact(`batch_size=8`, 격자 `(1,2,4,8)`, `max_num_seqs=8`)에서 문턱은 배경 요청 7개다"). 조건 없이 서술하면 `class`로 읽히기 때문이다. `class` 주장은 형태만 진술하고 **수치를 붙이지 않는다.**

---

## 막 1 — 진단

| # | 주장 | 근거 TASK | 층 | 그림 | 값을 붙일 때 반드시 함께 적을 조건 |
|---|---|---|---|---|---|
| 1.1 | 고정 개수의 시퀀스 단위 slot pool에서 완료 prefix의 생존은 **부분 생존 없는 절벽**이 되고, 문턱은 token 총량이 아니라 **요청 개수**의 함수다 | [TASK14](../docs/research/TASK14.md), [TASK15](../docs/research/TASK15.md), [TASK29](../docs/research/TASK29.md) | **`class`** (형태) | ① | — (수치 금지) |
| 1.2 | 이 구성에서 그 문턱은 **배경 요청 7개**이고 12/12 결정적으로 재현된다 | [TASK14](../docs/research/TASK14.md), [TASK15](../docs/research/TASK15.md) | **`stack`** | ① | b8 artifact, outer slot 8개 × 8,192 token, FIFO, 2,000 token 요청 |
| 1.3 | 회수 정책을 LRU·block 단위로 바꾸면 **개수 문턱이 사라지고** 문턱이 요청 크기에 반비례한다 | [TASK29](../docs/research/TASK29.md) | **`stack`** (모형 진술) | ① | 절제 계산이며 실측 아님. 값 61/31/16은 500/1,000/2,000 token 배경 요청 |
| 1.4 | `prefix_cache_hits_total`류의 상위 층 metric은 하위 층이 evict된 뒤에도 hit을 보고하므로 **실제 재사용의 지표가 아니다** | [TASK14](../docs/research/TASK14.md), [TASK15](../docs/research/TASK15.md) | **`stack`** | ① | vllm-rbln의 2층 장부(inner 128 token LRU / outer 8,192 token FIFO). **층이 하나인 stack에서는 발생하지 않는다** |
| 1.5 | 이산 batch 격자에 실제 batch를 올림하는 substrate에서 **`N`과 격자의 정렬이 gap 효과의 부호를 정한다** | [TASK20](../docs/research/TASK20.md), [TASK23](../docs/research/TASK23.md) | **`class`** (형태) | ② | — (수치 금지) |
| 1.6 | 그 인과는 **격자만 바꾸는 재compile 개입**으로 확정됐다: N=6 pooled ratio 1.1504 → 0.9717 | [TASK23](../docs/research/TASK23.md) | **`stack`** (값) | ② | 격자 `(1,2,4,8)` → `(1,2,4,6,8)`, `max_num_seqs=8`, 워크로드·seed 고정 |
| 1.7 | 연속 격자(모든 정수 width)에서 법칙은 **정확히 1.0000으로 소멸**한다 | [TASK29](../docs/research/TASK29.md) | **`class`** (항등에 가까움) | ② | — |
| 1.8 | 배타 prefill substrate에서 prefill은 요청 자신의 지연이 아니라 **시스템 비용**이며, 동시 decoder 수만큼 배증된다 | [TASK22](../docs/research/TASK22.md) | **`class`** (형태) | ③ | — (수치 금지) |
| 1.9 | 이 stack에서 정지 시간은 `ceil(n/128) × (0.0212 + 6.4e-7 n)` 초로 500–6,000 token에서 최대 잔차 2.4 ms | [TASK22](../docs/research/TASK22.md) | **`silicon`** + **`stack`** | ③ | CA25 4-device, Qwen3-4B, `max_seq_len=8192`. **절대 시간은 이 하드웨어·모델 고유** |
| 1.10 | 비용 모형 v2(decode + prefill 직렬화)가 [TASK20](../docs/research/TASK20.md)의 N 의존 편향을 87–120 % 설명해 0.97–1.04로 모은다 | [TASK22](../docs/research/TASK22.md) | **`stack`** | ③ | 위와 같은 구성, N ∈ {3…12} × 2 arm |
| 1.11 | chunked prefill로 바꾸면 정지 항이 0이 되지만 **device time이 3–10 % 늘어난다** — 배타 실행의 일부는 batching 보조금이었다 | [TASK29](../docs/research/TASK29.md) | **`stack`** (모형 진술) | ③ | 시뮬레이터 절제이며 실측 아님. 승격 조건은 chunked prefill 스택에서의 device time 실측 |
| 1.12 | 층 2 캐시는 **prefill이 계산한 token만** 담고 decode가 생성한 token은 담지 않는다 — 생성이 길수록 재사용률 상한이 내려간다 | [TASK24](../docs/research/TASK24.md) | **`stack`** | ① | 실측 271/271. `cached = floor(min(직전 prompt, 현재 prompt − 1)/128) × 128` |
| 1.13 | 즉시 돌아오는 세션은 **자기 캐시를 자기가 축출하지 않는다** — 완료 block이 evictable이 되는 시점이 다음 admission의 victim 선택보다 뒤이기 때문이다 | [TASK24](../docs/research/TASK24.md) | **`class`** (형태) | — | — (순서 문제는 완료 처리와 스케줄링을 분리한 어느 엔진에서나 가능) |
| 1.14 | 부호와 크기를 함께 만드는 것은 닫힌 식이 아니라 **상태 기계**다 — 보정 파라미터 0개로 80조합 재현(utilization MAE 0.0066, 방향 11/11) | [TASK24](../docs/research/TASK24.md) | **`universal`** (방법) + **`stack`**(값) | ④ | 재현 대상은 [TASK19](../docs/research/TASK19.md)–[TASK23](../docs/research/TASK23.md)의 80조합 |
| 1.15 | 그 모형의 **out-of-sample 예측**이 선등록 게이트를 통과한다 (최대 오차 0.0040, 허용치 ±0.05) | [TASK25](../docs/research/TASK25.md) | **`universal`** (방법) | ④ | 검증 격자는 N ≤ 7 |
| 1.16 | 그 예측은 **제어 개입이 들어간 조건**까지 성립한다 (device time ratio 오차 +0.018·+0.021) | [TASK28](../docs/research/TASK28.md) | **`universal`** (방법) | ④ | 확증 구간 N ∈ {6,8} |
| 1.17 | 그 예측은 **gap 법칙 전환**을 넘어 전이된다 (중앙값 22배·std 7배 다른 분포에서 utilization 오차 −0.019~0.000) | [TASK31](../docs/research/TASK31.md) | **`universal`** (방법) | ④ | 합성 `uniform:1:5` → 실측 tool latency 혼합(43 도구, 60 s cap) |

## 막 2 — 불가능성

| # | 주장 | 근거 TASK | 층 | 그림 | 함께 적을 조건 |
|---|---|---|---|---|---|
| 2.1 | 작업량이 보존되는 재배치에서 **slot 점유율과 device time은 반대로 움직인다** — utilization은 비용 지표가 아니다 | [TASK26](../docs/research/TASK26.md), [TASK27](../docs/research/TASK27.md) | **`class`** (형태) + **`stack`**(값) | ⑤ | 값 "11–37 % 더 씀", "방향 5/11 어긋남"은 이 격자·이 워크로드 |
| 2.2 | 반환 시점 재배치에 **실질적 headroom이 있다** (합성 gap: ε=0.5 s 1.2–4.4 %, ε=5 s 9.7–27.2 %) | [TASK26](../docs/research/TASK26.md) | **`stack`** | ⑤ | 국소 탐색 결과이므로 **하한**. 합성 `uniform:1:5` |
| 2.3 | headroom은 현실 tool latency 분포에서도 같은 자릿수로 남는다 (ε=2 s에 5.0–6.9 %) | [TASK31](../docs/research/TASK31.md) | **`stack`** | ⑤ | 실측 trace 1종(코드 agent류), 43 도구, 60 s cap |
| 2.4 | **이 headroom은 조정이 아니라 예지에서 나온다** — 현재 상태만 보는 causal 정책은 전부 평균 절감이 음수다 | [TASK27](../docs/research/TASK27.md), [TASK28](../docs/research/TASK28.md) | **`class`** (형태) + **`stack`**(값) | ⑤ | 값 X = −105 %·−70 %는 device 확증 구간 N ∈ {6,8} |
| 2.5 | **headroom의 중앙 60 %(49–73 %)는 조율의 몫이며 지식으로 살 수 없다** — 전지적 지식을 주고도 세션별 독립 결정이면 그만큼 사라진다 | [TASK33](../docs/research/TASK33.md) | **`class`** (형태) + **`stack`**(값) | ⑤ | 값 60 %는 현실 워크로드 9칸(N ∈ {6,8,10} × 3블록) |
| 2.6 | 따라서 **per-session runtime 정책은 그 부분에 원리적으로 닿을 수 없고**, 조율 가능한 위치는 server scheduler이거나 compile-time 구성이다 | [TASK33](../docs/research/TASK33.md) | **`class`** (형태) | ⑤ | — (수치 금지) |
| 2.7 | 예지의 가치는 **워크로드에 종속이며 이식되지 않는다** — 합성 gap에서 86–88 %를 회수하던 반환 시각 정보가 실측 분포에서는 −1.20 %~+0.99 %다 | [TASK30](../docs/research/TASK30.md), [TASK31](../docs/research/TASK31.md) | **`stack`** | ⑤, ⑥ | 두 워크로드 모두 명시. 동료 도착 **기회**는 비슷(73.6 대 81.9 %) |
| 2.8 | tool 지속시간의 예측 오차는 **줄일 수 없는 분산이 지배**한다 — 표본을 4자릿수 늘려도 std가 8.4 → 10.5 s로 개선되지 않는다 | [TASK32](../docs/research/TASK32.md) | **`universal`** | ⑥ | 이 trace의 도구 population. **"어느 워크로드에서나"가 아니라 "도구 이름이 명령을 담지 않는 워크로드에서"** |
| 2.9 | 상한 `B(δ)`와 점추정 `μ̂`의 오차 std가 같다(10.196 대 10.185) — **더 나은 추정자가 아니라 더 나은 조건화**가 필요하다 | [TASK32](../docs/research/TASK32.md) | **`universal`** | ⑥ | 차용 대상은 [Continuum](RELATED.md#continuum-arxiv-251102230) §4.2의 추정자 |
| 2.10 | **자유 파라미터 2개와 20조합 탐색만으로 5 %에 가까운 허구 이득이 만들어진다** (탐색 +4.32 % → 평가 −0.14 %) | [TASK33](../docs/research/TASK33.md), [TASK27](../docs/research/TASK27.md) | **`universal`** | ⑤ | [TASK27](../docs/research/TASK27.md)의 앞선 사례는 12 plan × 96칸에서 최대 34 % → 부호 반전 |

## 막 3 — 처방

| # | 주장 | 근거 TASK | 층 | 그림 | 함께 적을 조건 |
|---|---|---|---|---|---|
| 3.1 | 사전 정의된 분기에 따라 **compile-time이 유일 회수 경로**로 확정됐다 | [TASK33](../docs/research/TASK33.md) | **`stack`** (이 substrate의 판정) | — | 분기 정의는 측정 전 선등록. **"어느 시스템에서나 compile-time이 답"이 아니다** |
| 3.2 | 구성은 **워크로드 통계만으로** 고를 수 있다 — 선택에 device 실측을 쓰지 않는다 | [TASK34](../docs/research/TASK34.md) | **`universal`** (방법) | ⑦, ⑧ | 탐색/평가 seed 분리, 무보정 시뮬레이터 |
| 3.3 | 재compile 비용은 bucket 수에 선형이며 **관측점 5개**에서 유지된다 (마지막 점 시간 −0.7 %, 크기 +0.6 %) | [TASK10](../docs/research/TASK10.md), [TASK23](../docs/research/TASK23.md), [TASK34](../docs/research/TASK34.md), [TASK35](../docs/research/TASK35.md) | **`stack`** | ⑦ | Qwen3-4B, `max_seq_len=8192`, `num_devices=4`, optimum-rbln 0.11.1 |
| 3.4 | **compile 구성 선택이 device time을 회수한다: X = +9.72 % / +10.07 %** (두 채널 합치 0.0035) | [TASK35](../docs/research/TASK35.md) | **`stack`** | ⑧ | N=8 확증 구간, seed `20261000`, `TUNED` = `(1,4,6,8,10,16)` batch 16 |
| 3.5 | 그 확증이 **신규 seed의 N=6에서도 성립**한다 (적용 범위 N ∈ {6,8}) | [TASK36](../docs/research/TASK36.md) | **`stack`** | ⑧ | seed `20261100`, 교정된 채널 요건 `τ = max(0.02, r_BASE/B_BASE)` |
| 3.6 | **지배 인자는 bucket 격자가 아니라 `batch_size`(= KV pool 크기)** — batch만 +8.25 %, 격자 정합이 +1.3–1.5 %p | [TASK35](../docs/research/TASK35.md) | **`stack`** | ⑧ | device 절제. 순서 `③ < ② < 1`과 크기 예측(±3 %p) 둘 다 통과 |
| 3.7 | 두 arm의 **prefill비가 실측에서도 동일**(0.678/0.678)해 차이를 decode 항 하나로 귀속할 수 있다 | [TASK35](../docs/research/TASK35.md) | **`stack`** | ⑧ | 절제 설계가 실제로 한 축만 바꿨다는 **결과에 의한 확인** |
| 3.8 | 인과 사슬: `batch_size` → `kvcache_num_blocks` → 캐시 생존 → prefill 재계산 | [TASK08](../docs/research/TASK08.md), [TASK14](../docs/research/TASK14.md), [TASK35](../docs/research/TASK35.md) | **`stack`** | ⑧ | `attn_impl=eager`에서 `kvcache_num_blocks = batch_size`. **다른 attention 구현에서는 성립을 확인해야 한다** |
| 3.9 | 구성 선택은 **gap 분포에 둔감하고 동시 세션 수 상한에만 반응**한다 — 재구성 판단에 다시 잴 통계는 그것 하나다 | [TASK34](../docs/research/TASK34.md) | **`stack`** | ⑦ | 민감도 분석 범위 안에서 |

## 일반성 절

| # | 주장 | 근거 TASK | 층 | 그림 | 함께 적을 조건 |
|---|---|---|---|---|---|
| 4.1 | **격자 정렬 법칙은 GPU에서 소멸하지 않는다** — vLLM cudagraph capture size 기본 목록이 `max_num_seqs=8`에서 `[1,2,4,8,16]`이고 유효 구간이 NPU 격자와 같다 | [TASK29](../docs/research/TASK29.md) | **`class`** (형태) + **source-read** | ② | `vllm/config/compilation.py:676–690`. **모형 진술이며 GPU 실측 아님.** 승격 조건: `max_num_seqs=8` GPU 실측 1건 |
| 4.2 | GPU 대비에서 재야 할 축은 **accelerator가 아니라 `max_num_seqs`** 다 | [TASK29](../docs/research/TASK29.md) | **`class`** | ② | — |
| 4.3 | **절제는 기전의 *존재*가 아니라 *귀속*을 검사한다** | [TASK29](../docs/research/TASK29.md) | **`universal`** | — | 방법론 |
| 4.4 | 관측 신호는 "무엇을 세는지"가 아니라 **"어느 층에서 세는지"** 로 검증해야 한다 | [TASK15](../docs/research/TASK15.md) | **`universal`** | ① | — |
| 4.5 | 모형 기반 채널과 모형 무의존 채널의 허용차는 **비만이 아니라 절대 잔차의 크기도 함께** 봐야 한다 | [TASK35](../docs/research/TASK35.md), [TASK36](../docs/research/TASK36.md) | **`universal`** | — | 총량이 작은 조건에서 고정 오버헤드가 비를 지배한다 |

---

## 전수 점검 — `stack` 주장이 `class`처럼 읽히지 않는가

각 `stack` 항목에 대해 "조건 없이 읽으면 일반 법칙으로 오독되는가"를 물었다. **오독 위험이 있는 항목과 본문에서의 처리**는 다음과 같다.

| 항목 | 오독 위험 | 본문 처리 |
|---|---|---|
| 1.2 문턱 = 7 | **높음.** "cache는 7개 요청까지 산다"로 읽히기 쉽다 | 문장 안에 `outer slot 8개`를 **먼저** 쓰고 `7 = 8 − 1`의 산술을 노출한다. 절대 수치는 항상 slot 수와 짝으로만 등장시킨다 |
| 1.4 metric 과대보고 | **높음.** "vLLM metric은 못 믿는다"로 일반화되기 쉽다 | "**2층 장부를 가진 stack에서**"를 조건절로 고정하고, 층이 하나인 stack에서는 발생하지 않음을 같은 문단에 명시한다 |
| 1.6 개입 1.1504 → 0.9717 | 중간. 개입의 **방향**은 `class`, 크기는 `stack` | 방향과 크기를 다른 문장으로 나눈다 |
| 1.9 prefill 시간 상수 | 낮음(단위가 이미 절대 시간) | `silicon` 태그를 표에 노출하고 하드웨어명을 병기한다 |
| 2.2·2.3 headroom % | **높음.** "agentic 서빙에 5–27 % 여유가 있다"로 읽히기 쉽다 | ε(예산)과 gap 분포를 항상 병기한다. **하한**임을 매번 붙인다 |
| 2.5 조율 60 % | **높음.** 형태(`class`)와 값(`stack`)이 한 문장에 있다 | "지식으로 살 수 없는 부분이 있다"(형태)와 "이 워크로드에서 그것이 중앙 60 %"(값)를 분리한다 |
| 3.4 X = +10 % | **가장 높음.** 논문의 헤드라인 숫자다 | 초록·서론·결론 **전부**에서 `N=8`, `이 substrate`, `이 워크로드`를 붙인다. [TASK36](../docs/research/TASK36.md)의 N=6 값과 함께 **구간**으로 제시하고 단일 값으로 쓰지 않는다 |
| 3.6 `batch_size` 지배 | **높음.** "batch를 키워라"로 읽히기 쉽다 | `attn_impl=eager`에서 `kvcache_num_blocks = batch_size`라는 이 stack의 회계를 조건으로 명시한다. 다른 stack에서는 KV pool과 batch가 분리될 수 있음을 같은 문단에 쓴다 |
| 3.1 compile-time 유일 경로 | **높음.** "runtime 정책은 쓸모없다"로 읽히기 쉽다 | "**이 substrate에서, 사전 정의된 분기에 따라**"를 조건으로 고정하고, server-side scheduler는 **닫히지 않은 경로**임을 명시한다([TASK33](../docs/research/TASK33.md)이 조율 가능한 위치로 지목했으나 patch 정책 대상이라 실행하지 않았다) |
| 4.1 GPU 소멸 안 함 | **높음.** source-read 기반 **모형 진술**인데 실측처럼 읽히기 쉽다 | 절 제목에 "계산"을 넣고, 인용 줄 번호를 본문에 노출하며, 승격 조건(GPU 실측 1건)을 같은 문단에 쓴다 |

`class` 항목(1.1, 1.5, 1.7, 1.8, 1.13, 2.1, 2.4, 2.5, 2.6, 4.1, 4.2)은 전부 **수치를 붙이지 않은 형태 진술**로만 본문에 등장시키고, 대응하는 값은 별도 `stack` 항목에서 조건과 함께 낸다.

---

## 한계 (본문 한계 절의 원본)

1. **단일 substrate.** RBLN CA25 + `vllm-rbln 0.11.1` + `optimum-rbln 0.11.1` 하나. 모든 절대 상수는 `silicon`/`stack`이며 이식하지 않는다.
2. **단일 스택 버전.** patch는 observation-only이고 hash guard가 걸려 있으나, 버전이 바뀌면 격자·회계·metric 층 구조가 함께 바뀔 수 있다.
3. **단일 모델.** Qwen3-4B, `max_seq_len=8192`, `num_devices=4`, 36 layer 전부 full attention. hybrid·sliding-window·MLA 계열에서 KV 회계가 다르다.
4. **trace 1종.** 실측 tool latency는 코드 agent류 trace 하나(43 도구)에서 왔다. [TASK31](../docs/research/TASK31.md)이 보인 대로 **워크로드가 바뀌면 예지의 가치가 뒤집힌다** — 이 한계는 이 연구가 스스로 실증한 것이다.
5. **N > 10 미검증.** 시뮬레이터 재현 품질이 `max_num_seqs`에서 꺾이고([TASK24](../docs/research/TASK24.md)) N=10은 탐색 구간으로만 다뤘다.
6. **batch > 16 미검증.** `batch_size` 지배가 어디서 포화하는지, KV 한계가 어디인지 `UNKNOWN`이다.
7. **GPU 실측 이연.** 일반성 절의 세 축 중 ①(생존 곡선의 문턱이 개수인가 크기인가)만 실측 없이 값을 말할 수 없다. 최소 범위는 생존 곡선 1건으로 좁혀져 있다.
8. **server-side scheduler 경로 미실행.** [TASK33](../docs/research/TASK33.md)이 조율 가능한 유일한 runtime 위치로 지목했으나 이 연구의 patch 정책 밖이라 열지 않았다. **"runtime은 불가능"이 아니라 "per-session runtime은 불가능하고 server-side는 미검증"이다.**
9. **bucket 6·10·16의 step 비용이 `PARTIAL`.** 채널 A′는 그 구간을 선형 보간하며, 알려진 편향(bucket 10에서 −10.9 %)을 선등록에 명시했다.
