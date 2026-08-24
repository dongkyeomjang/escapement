# 초록 (국문·영문)

시스템 명칭은 미확정이다 — [결정 5](../docs/research/INDEX.md#결정-5--시스템-명칭-충돌)의 후보 중 사용자가 판정한다. 아래에서는 `<SYSTEM>`으로 둔다.

---

## 국문 초록

Agentic 워크로드는 LLM 호출 사이에 도구 실행 구간을 끼워 넣고, 그 구간이 끝난 뒤 세션이 **언제 돌아오는가**가 서빙 비용을 정한다. 우리는 RBLN CA25 NPU 위의 vLLM 스택에서 그 반환 도착 과정을 실기기로 분해해, 서로 독립인 세 기전이 device time을 만든다는 것을 보인다: (i) 동시 요청 수와 compiled decode batch 격자의 **정렬**, (ii) 시퀀스 단위 FIFO slot pool의 **재사용 절벽**, (iii) 배타 실행 prefill의 **직렬화 세금**. 셋 모두 개별 요청의 속성이 아니라 도착의 집합적 성질에 반응한다. (i)의 인과는 격자만 바꾸는 재compile 개입으로 확정했고(pooled ratio 1.1504 → 0.9717), (ii)의 문턱이 token 총량이 아니라 요청 개수의 함수임을 12/12 결정적 재현으로, (iii)이 실행 중인 모든 세션을 정지시킴을 시간 단위로 관측했다. 세 기전을 담은 보정 파라미터 0개의 step 수준 시뮬레이터는 선등록된 out-of-sample 예측 게이트를 통과한다(최대 오차 0.0040, 허용치 ±0.05).

그 모형 위에서 우리는 **부정적 결과**를 얻는다. 반환 시점을 재배치하면 offline headroom이 실재하지만(현실 tool latency 분포에서 ε=2 s에 5.0–6.9 %), 그 headroom의 중앙 **60 %(49–73 %)** 는 *조율*의 몫이어서 전지적 지식을 주고도 세션별로 독립 결정을 내리면 사라진다. 즉 **per-session runtime 정책은 그 부분에 원리적으로 닿을 수 없다.** 남은 부분도 닿지 않는다: 반환 시각 정보의 값은 워크로드에 종속이라 실측 도구 지연 분포에서 −1.20 % ~ +0.99 %로 소멸하고, 선행 연구의 지속시간 추정자를 그대로 차용해 재면 오차가 정확도 문턱을 5.6–9.7배 초과하며 표본을 네 자릿수 늘려도 줄지 않는다. 이 음성 결과들은 방법론적 함정과 짝을 이룬다 — 자유 파라미터 2개와 20조합 탐색만으로 탐색 seed에서 +4.32 %의 이득이 보이고 평가 seed에서 −0.14 %가 된다.

닿을 수 있는 지점은 **조율을 설계 시점에 굳히는 compile-time 구성** 하나로 남는다. 우리는 device 실측을 전혀 쓰지 않고 워크로드 **분포 통계**와 무보정 시뮬레이터만으로 구성을 고르고, 7분의 재compile로 실기기에 적용해, 측정 전에 등록한 두 개의 독립 채널에서 device time 회수를 확증한다: N=8에서 **+9.72 % / +10.07 %**, 신규 seed의 N=6에서 **+2.11 % / +2.74 %**. Device 절제는 이득의 출처가 조건부임을 보인다 — 기준 구성이 캐시를 많이 잃을 때는 KV pool 크기(`batch_size`)가 이득의 대부분을 내고(+8.25 %), 이미 대부분 재사용하고 있을 때는 남는 것이 bucket 격자 정합뿐이다(+1.52 %p). 개별 draw를 못 맞혀도 분포만 알면 살 수 있는 레버가 있다는 것이 이 논문의 답이다.

---

## English abstract

Agentic workloads interleave LLM calls with tool execution, and *when* a session comes back after a tool call is what sets its serving cost. On an RBLN CA25 NPU running the vLLM stack, we decompose that return-arrival process on real hardware and show that three independent mechanisms produce device time: (i) the **alignment** between the number of concurrent requests and the compiled decode-batch grid, (ii) the **reuse cliff** of a sequence-granular FIFO slot pool, and (iii) the **serialisation tax** of exclusively executed prefill. None of the three responds to a property of an individual request; all three respond to a collective property of arrivals. We establish (i) causally through a recompile intervention that changes only the grid (pooled ratio 1.1504 → 0.9717), show that the threshold in (ii) is a function of request *count* rather than total tokens and reproduces 12/12 deterministically, and observe (iii) stalling every concurrent session for the full prefill duration. A step-level simulator carrying all three, with zero fitted parameters, passes a preregistered out-of-sample prediction gate (worst error 0.0040 against a ±0.05 tolerance).

On top of that model we obtain a **negative result**. Rescheduling return times leaves real offline headroom (5.0–6.9 % at a 2 s budget under a measured tool-latency distribution), but a median **60 % (49–73 %)** of that headroom is *coordination*: hand every session omniscient knowledge and let it decide independently, and that share disappears. **No per-session runtime policy can reach it, in principle.** The remainder is not reachable either: the value of return-time information is workload-specific and vanishes (−1.20 % to +0.99 %) under measured tool latencies, and borrowing a published duration estimator verbatim yields errors 5.6–9.7× above the accuracy threshold that do not shrink when per-tool samples grow by four orders of magnitude. These negatives come paired with a methodological trap: two free parameters and a 20-configuration search manufacture a +4.32 % gain on exploration seeds that becomes −0.14 % on held-out seeds.

That leaves exactly one reachable lever — a **compile-time configuration**, which is coordination decided once, in advance, for everybody. Using only workload *distribution* statistics and the uncalibrated simulator, with no device measurement in the selection loop, we choose a configuration, apply it with a seven-minute recompile, and confirm the device-time recovery on two independent channels registered before measurement: **+9.72 % / +10.07 %** at N=8 and **+2.11 % / +2.74 %** at N=6 on a fresh seed. A device-side ablation shows the gain's source is conditional: when the baseline loses much of its cache, KV pool size (`batch_size`) supplies most of the gain (+8.25 %); when the baseline already reuses nearly everything, all that remains is bucket-grid alignment (+1.52 pp). The answer this paper offers is that some levers can be bought with a distribution even when no one can predict the individual draw.

---

## 초록 작성 시 지킨 조건 병기 (오독 방지)

[CLAIMS.md](CLAIMS.md)의 전수 점검 표를 초록에도 적용했다.

| 수치 | 병기한 조건 |
|---|---|
| +9.72 / +10.07 % | `N=8`, 두 채널, 이 substrate |
| +2.11 / +2.74 % | `N=6`, **신규 seed**, 두 채널 |
| +8.25 %, +1.52 %p | 절제 결과이며 **조건부**임을 같은 문장에 명시 |
| 60 % | "중앙"과 범위 49–73 %를 함께. 형태(조율은 살 수 없다)와 값(60 %)을 다른 절에 배치 |
| 5.0–6.9 % | ε=2 s 예산과 "현실 tool latency 분포"를 병기 |
| 1.1504 → 0.9717 | "격자만 바꾸는 개입"을 같은 절에 |
| 12/12 | "문턱은 요청 개수의 함수"라는 형태 진술과 함께. **절대 문턱값 7은 초록에 넣지 않았다** |

**초록에 넣지 않은 수치**: outer slot 8개, 문턱 B=7, prefill 상수 `0.0212 + 6.4e-7 n`. 전부 `stack`/`silicon`이고 조건 없이 읽히면 클래스 사실로 오독되기 때문에 본문에서 조건과 함께만 낸다.
