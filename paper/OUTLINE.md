# 논문 서사 — 최종 3막 구조

시스템 명칭: **`Escapement`** ([결정 5](../docs/research/INDEX.md#결정-5--시스템-명칭-충돌), 사용자 판정 2026-08-25). 본문·figure 라벨·arXiv 제목에 이 이름을 쓰고 저장소 경로와 package 이름은 그대로 둔다.

이 문서는 논문 본문의 **서사 설계**다. 각 절이 무엇을 주장하고 어느 TASK가 그것을 지지하는지는 [CLAIMS.md](CLAIMS.md)가, 그림은 [figures/](figures/)가, 선행 연구 배치는 [RELATED.md](RELATED.md)가 맡는다. 측정은 [TASK35](../docs/research/TASK35.md)로 종료됐고 [TASK36](../docs/research/TASK36.md)이 N=6 확증을 더했다.

## 한 문장

**Agentic 워크로드의 반환 도착 과정이 만드는 세 기전을 실기기에서 분해하고, 그 기전이 남긴 headroom의 대부분이 runtime 정책으로는 원리적으로 닿을 수 없음을 보인 뒤, 닿을 수 있는 유일한 지점 — compile 시점의 구성 — 에서 실제로 device time을 회수한다.**

## 왜 이 순서인가

이 연구는 정책을 만들려다 세 번 실패했고([TASK27](../docs/research/TASK27.md)·[TASK31](../docs/research/TASK31.md)·[TASK32](../docs/research/TASK32.md)), 그 실패가 **어디에 레버가 없는지**를 정확히 말해 준 덕분에 남은 한 곳을 찾았다. 논문이 그 순서를 그대로 따르는 것은 서사적 장식이 아니라 **음성 결과 셋이 양성 결과의 근거**이기 때문이다. 처방을 먼저 놓으면 "왜 하필 compile-time인가"에 답할 수 없다.

---

## 막 1 — 진단: 반환 도착 과정이 세 기전을 만든다

**주장**: agentic 세션이 tool gap 뒤에 *언제* 돌아오는가가, 서로 독립인 세 기전을 통해 device time을 정한다. 셋 다 개별 요청의 속성이 아니라 **도착의 집합적 성질**에 반응한다.

### 1.1 기전 ① — 격자 정렬 (bucket grid alignment)

- 동시 요청 수 `N`이 compiled decode batch 격자의 어디에 떨어지는가가 gap의 효과 **부호**를 바꾼다. `N`이 bucket 사이에 끼면 gap이 오히려 이롭다 ([TASK20](../docs/research/TASK20.md): N=6에서 pooled 1.15, N=10–12에서 0.91).
- **상관이 아니라 인과다.** 워크로드·seed·모델·slot 수를 고정하고 **격자에 bucket 6만 추가하는 재compile 개입**으로 N=6의 역전이 1.1504 → 0.9717로 소멸했다 ([TASK23](../docs/research/TASK23.md)).
- 절제: 연속 격자에서 법칙이 정확히 1.0000으로 소멸한다 ([TASK29](../docs/research/TASK29.md)).
- **선행 대비 (상보)**: LENS([RELATED.md §4](RELATED.md#lens-arxiv260618042--상보-배치))는 같은 bucket 구조가 **한 요청의 지연**에 만드는 비선형성을 예측 가능하게 만들었다. 이 절이 묻는 것은 그 구조가 **여러 세션의 도착 과정과 만날 때**의 시스템 거동이며, 두 결과는 어느 쪽도 다른 쪽을 함의하지 않는다.
- **그림 ②**.

### 1.2 기전 ② — FIFO slot 생존 (cache survival cliff)

- 완료된 prefix의 실제 재사용은 배경 요청 6개까지 살고 **7개째에 절벽처럼 사라진다** ([TASK14](../docs/research/TASK14.md), [TASK15](../docs/research/TASK15.md)에서 12/12 결정적 재현).
- **문턱은 token 총량이 아니라 요청 개수다.** 8,192 token 이하 요청은 길이와 무관하게 outer slot 1개를 쓴다(149/149).
- 절제로 귀속을 확인했다: LRU로 바꾸면 "개수 문턱"이 사라지고 문턱이 크기에 반비례한다(61/31/16) ([TASK29](../docs/research/TASK29.md)).
- **선행 대비**: GPU agentic KV 관리 계열(KVFlow·CacheScout·MORI·Leyline, [RELATED.md §2](RELATED.md#2-gpu-agentic-kv-관리-계열--도구-유휴-구간을-자원-문제로-다룬다))은 **회수 정책을 바꿀 수 있다**고 전제한다. 이 substrate의 층 2 회수는 시퀀스 단위 FIFO로 하드코딩돼 있어 **그 전제가 성립하지 않으며**, 그것이 이 연구를 정책 축에서 구성 축으로 민 제약이다.
- 부수 결과이지만 실무적으로 큰 것: **`prefix_cache_hits_total`이 실제 재사용을 100 % 과대보고**한다 (층 1과 층 2의 장부 분리, [TASK14](../docs/research/TASK14.md)·[TASK15](../docs/research/TASK15.md)).
- **그림 ①**.

### 1.3 기전 ③ — prefill 직렬화 (exclusive prefill)

- prefill이 실행 중인 **모든** 세션의 decode를 그 길이만큼 정지시킨다. bystander 4개의 스파이크가 1 ms 이내로 겹치고 스파이크/prefill 비가 1.01–1.14 ([TASK22](../docs/research/TASK22.md)).
- 비용 모형 v2 = decode 항 + prefill 직렬화 항. [TASK20](../docs/research/TASK20.md)의 N 의존 편향(0.57–0.86)이 이 항으로 87–120 % 설명되고 0.97–1.04로 모인다.
- **캐시 실패의 비용은 재계산 시간 × 동시 decoder 수**다 — 기전 ②와 ③이 여기서 곱해진다.
- 절제의 반전: chunked prefill로 바꾸면 정지는 0이 되지만 device time이 **3–10 % 늘어난다**. 배타 실행의 일부는 강제 동기화를 통한 **batching 보조금**이었다 ([TASK29](../docs/research/TASK29.md)).
- **그림 ③**.

### 1.4 세 기전을 하나로 — 실행 가능한 substrate 모형

- 닫힌 식은 부호와 크기를 함께 만들지 못한다. **step 수준 시뮬레이터**가 보정 파라미터 없이 80조합을 재현하고(utilization 평균절대오차 0.0066, 방향 11/11, [TASK24](../docs/research/TASK24.md)) **out-of-sample 예측**이 선등록 게이트를 통과했다(최대 오차 0.0040, 허용치 ±0.05, [TASK25](../docs/research/TASK25.md)).
- 이후의 정책 질문은 실측이 아니라 **계산으로** 답한다. 이것이 막 2를 가능하게 한 도구다.
- **그림 ④**.

---

## 막 2 — 불가능성: headroom은 있는데 runtime 정책이 닿을 수 없다

**주장**: 재배치 headroom은 실재한다. 그런데 그 headroom은 세 겹의 이유로 **per-session runtime 정책의 사정거리 밖**이다. 이 막의 결론은 음성이지만, 그 음성이 막 3의 유일한 근거다.

### 2.1 headroom은 실재하고, utilization은 그것을 재는 자가 아니다

- offline oracle: ε=0.5 s에 1.2–4.4 %, ε=5 s에 9.7–27.2 % ([TASK26](../docs/research/TASK26.md)). 현실 tool latency 분포에서도 ε=2 s에 5.0–6.9 %가 남는다 ([TASK31](../docs/research/TASK31.md)).
- **utilization은 비용 지표가 아니다.** 작업량이 보존되는 재배치에서 slot 점유율과 device time은 반대로 움직이고, utilization을 최대화한 일정이 device time을 11–37 % 더 쓴다 ([TASK26](../docs/research/TASK26.md)). 이 연구 자신의 [TASK19](../docs/research/TASK19.md)–[TASK25](../docs/research/TASK25.md) 판정축을 스스로 격하시킨 결과다.

### 2.2 첫째 벽 — 60 %는 조율의 몫이라 원리적으로 닿지 않는다

- 정보 축 분해: **전지적 지식을 주고도 세션별로 독립 결정을 내리면 headroom의 27–51 %만 회수**되고 나머지 **중앙 60 %(49–73 %)가 사라진다** ([TASK33](../docs/research/TASK33.md)).
- 이 부분은 지식의 부족이 아니라 **결정 구조**의 문제다. 이득이 "여럿이 같은 batch에 타는 것"에서 나오는 이상 누가 어느 무리에 들지는 세션 하나가 자기 정보만으로 정할 수 없다. **per-session client 정책은 이 부분에 원리적으로 닿을 수 없다.**
- 조율이 가능한 위치는 둘뿐이다: 전 세션을 보는 server scheduler, 또는 **조율을 설계 시점에 굳히는 compile-time 구성**.
- **그림 ⑤**.

### 2.3 둘째 벽 — 반환 시각은 현실 워크로드에서 값이 없다

- 합성 gap에서는 반환 시각만 알아도 headroom의 86–88 %가 회수되고 정확도 문턱 σ\* = 0.74–1.27 × gap 표준편차였다 ([TASK30](../docs/research/TASK30.md)).
- **그 결론은 워크로드 특유였다.** 실측 tool latency 분포로 바꾸면 반환 시각을 정확히 알아도 이득이 −1.20 % ~ +0.99 %이고 σ\*가 정의되지 않는다 ([TASK31](../docs/research/TASK31.md)).
- 동료 도착 **기회**는 두 워크로드가 비슷하다(ε=2 s에서 73.6 대 81.9 %). **기회가 없는 것이 아니라 그 기회의 값이 없다.**
- 이 절은 이 연구가 자기 결과를 스스로 뒤집은 지점이며, **워크로드 전환이 결론의 이식성을 시험하는 방법**이라는 방법론 주장을 함께 싣는다.

### 2.4 셋째 벽 — 개별 draw는 환원 불가 분산이라 예측되지 않는다

- 선행 연구([Continuum](RELATED.md#continuum-arxiv-251102230) §4.2)의 추정자를 그대로 차용해 실측했다. 오차가 문턱을 **5.6–9.7배 초과**하고, 도구별 표본을 10 → 100,000으로 **4자릿수 늘려도 std가 8.4 → 10.5 s로 개선되지 않는다** ([TASK32](../docs/research/TASK32.md)).
- 상한 `B(δ)`와 점추정 `μ̂`의 오차 std가 같다(10.196 대 10.185). **더 나은 추정자가 아니라 더 나은 조건화가 필요하며, 도구 이름은 그 조건을 담지 않는다** — `Bash`가 27 ms일지 300 s일지는 명령이 정한다.
- **그림 ⑥**.

### 2.5 넷째 벽 (방법론) — 자유 파라미터 2개가 5 % 허구 이득을 만든다

- **시연**: 자유 파라미터 2개, 20조합 탐색만으로 탐색 seed에서 **+4.32 %**가 보이고 평가 seed에서 **−0.14 %**가 된다 ([TASK33](../docs/research/TASK33.md) 발견 4). [TASK27](../docs/research/TASK27.md)에서는 12 plan × 96칸 탐색이 최대 34 % 회수로 보였다가 신규 seed에서 부호가 뒤집혔다.
- 이 절은 **이 논문 자신의 양성 결과가 왜 그 함정에 빠지지 않았는지**를 말하는 자리이기도 하다: 탐색/평가 seed 분리, 선등록, 측정 seed의 3중 격리([TASK35](../docs/research/TASK35.md) `20261000`, [TASK36](../docs/research/TASK36.md) `20261100`).

---

## 막 3 — 처방(`Escapement`): 분포 통계만으로 고른 구성이 실기기에서 +10 %를 낸다

**주장**: 개별 draw를 못 맞혀도, **분포**만 알면 compile 시점에 조율을 굳혀 device time을 회수할 수 있다. 그리고 그 회수는 선등록된 채널에서 실기기로 확증된다.

### 3.1 왜 compile-time인가 — 사전 정의된 분기의 결과

[TASK33](../docs/research/TASK33.md)이 측정 전에 정의한 분기가 `compile-time이 유일 회수 경로`로 확정됐다. 이것은 사후 해석이 아니라 **선등록된 판정**이다.

### 3.2 구성 선택 — 분포 통계 → 무보정 시뮬레이터 탐색

- 후보 구성을 탐색 seed에서 점수화하고 **평가 seed에서 확인**한다. 워크로드에서 쓰는 정보는 **gap 분포와 동시 세션 수 상한**뿐이며, 실측 device 시간은 선택에 쓰이지 않는다 ([TASK34](../docs/research/TASK34.md)).
- **민감도**: 구성 선택은 gap 분포에 둔감하고 **동시 세션 수 상한에만 반응**한다. 재구성 판단에 다시 재야 할 통계는 그것 하나다.

### 3.3 비용 — 재compile은 7분이다

- [TASK10](../docs/research/TASK10.md)의 비용 모형 `시간 ≈ 42.3 + 61.3 × compiled model 수`, `크기 ≈ 8.276 + 0.806 × bucket 수` GiB가 **관측점 5개**에서 유지된다(마지막 점 오차 시간 −0.7 %, 크기 +0.6 %).
- **그림 ⑦**.

### 3.4 확증 — 선등록 채널, 실기기, 절제

- **X = +9.72 % / +10.07 %** (N=8, `TUNED`, 두 채널 합치 0.0035, [TASK35](../docs/research/TASK35.md)). [TASK36](../docs/research/TASK36.md)이 N=6을 신규 seed로 재측정해 적용 범위를 확장한다.
- **지배 인자는 bucket 격자가 아니라 `batch_size`(= KV pool 크기)**다. arm 절제에서 `batch_size`만 바꾼 구성이 +8.25 %, bucket 격자 정합이 +1.5 %p를 더한다. 두 arm의 **prefill비가 실측에서도 동일**(0.678/0.678)해 차이를 decode 항 하나로 귀속할 수 있다.
- 인과 사슬이 닫힌다: `batch_size` → `kvcache_num_blocks`([TASK08](../docs/research/TASK08.md)) → 캐시 생존(기전 ②) → prefill 재계산(기전 ③).
- **그림 ⑧**.

---

## 일반성 절 (막 3 뒤, 한계 절 앞)

이 연구의 상수는 전부 한 인스턴스의 값이다. 그래서 **어느 주장이 형태이고 어느 것이 값인지**를 절제와 source 검증으로 분리한다 ([TASK29](../docs/research/TASK29.md), [TASK16](../docs/research/TASK16.md)의 층 태깅).

1. **격자 정렬 법칙은 GPU에서 소멸하지 않는다** — vLLM의 cudagraph capture size 기본 목록은 `max_num_seqs=8`에서 `[1,2,4,8,16]`(`vllm/config/compilation.py:676–690`)이고 유효 구간이 NPU 격자와 같아 pooled ratio가 소수 넷째 자리까지 같다. **이 연구의 사전 기대를 뒤집은 결과이며, GPU 대비에서 재야 할 축은 accelerator가 아니라 `max_num_seqs`다.**
2. **생존 법칙의 "개수 문턱"은 시퀀스 단위 FIFO의 산물**이며, LRU·block 단위 회수에서는 문턱이 크기에 반비례한다. **세 축 중 실측 없이 값을 말할 수 없는 유일한 축**이므로 GPU 실측의 최소 범위가 생존 곡선 1건으로 좁혀진다.
3. **prefill 직렬화 세금은 순수 비용이 아니다** — chunked에서 정지는 사라지지만 device time은 3–10 % 는다.
4. **절제는 기전의 *존재*가 아니라 *귀속*을 검사한다**는 한계를 명시한다.

## 한계 절

[CLAIMS.md](CLAIMS.md) 말미의 한계 목록을 본문 절로 옮긴다. 요약: 단일 substrate·단일 스택 버전·단일 모델·trace 1종(코드 agent류), N > 10 미검증, batch > 16 미검증, GPU 실측 이연.

## 부록

- A. substrate descriptor와 층 태깅 규칙 ([TASK16](../docs/research/TASK16.md))
- B. 선등록 문서 전문과 commit hash·측정 시각의 선후 관계
- C. observation-only patch 정책과 hash guard ([TASK12](../docs/research/TASK12.md), `patches/`)
- D. 시뮬레이터 검증 표 전문 ([TASK24](../docs/research/TASK24.md), [TASK25](../docs/research/TASK25.md), [TASK28](../docs/research/TASK28.md), [TASK31](../docs/research/TASK31.md))
