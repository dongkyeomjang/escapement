# 초록 (국문·영문)

시스템 명칭은 **`Escapement`** 로 확정됐다 ([결정 5](../docs/research/INDEX.md#결정-5--시스템-명칭-충돌), 사용자 판정 2026-08-25). 논문 본문·figure 라벨·arXiv 제목에 이 이름을 쓴다. GitHub 저장소도 `escapement`로 개명됐으나, **로컬 디렉터리 경로와 Python package 이름(`src/continuum/`)은 재현 정보 보존을 위해 그대로 둔다.**

**이름의 근거**: escapement(탈진기)는 시계에서 **연속적인 구동력을 이산적인 tick으로 바꾸는 기구**다. 이 논문의 중심이 연속적인 반환 도착 과정과 이산적인 compiled batch 격자의 정렬이므로 은유가 기전과 직접 맞는다.

---

## 용도별 판본

| 판본 | 용도 | 길이 | 위치 |
|---|---|---|---|
| **영문 압축본** | **arXiv 초록 필드** (하드 캡 1,920자) | **1,876자** | 아래 §1, 그리고 평문 파일 [`abstract_arxiv.txt`](abstract_arxiv.txt) |
| 영문 전체판 | **논문 본문**(학회 원고)의 초록 | 3,029자 | 아래 §3 |
| 국문 초록 | 국문 배포·발표 자료 | 1,511자 | 아래 §2. **자수 제약이 없으므로 압축하지 않는다** |

압축본에서 **본문으로 이관한 것**: 격자 개입 전후 pooled ratio(1.1504 → 0.9717), 재사용 절벽의 12/12 재현, 예측기 오차의 문턱 초과 배수(5.6–9.7배), N=6 확증 수치, 자유 파라미터 함정의 수치(+4.32 % → −0.14 %), 절제의 항별 크기(+8.25 % / +1.52 %p).

압축본에서 **지킨 것**: 세 기전의 명명과 인과 확정 방식, 무보정 시뮬레이터와 선등록 out-of-sample 게이트, "headroom의 중앙 60 %는 조율의 몫이며 per-session runtime 정책은 원리적으로 닿을 수 없다", compile-time 처방과 N=8 확증(두 채널), 그리고 폐지 문장.

**조건 병기는 남은 수치에만 적용했다** — `60 %`에는 "median"을, `9.7–10.1 %`에는 "at N=8 concurrent sessions"와 "on two channels registered before measurement"를 붙였다. **압축의 첫 희생자가 조건이 되지 않게 하는 것이 이 판본의 제약이었다.**

---

## 1. 영문 압축본 — arXiv 초록 필드용 (1,876자)

평문·ASCII·마크다운 없음. 그대로 복사해 붙일 수 있다. 원본 파일은 [`abstract_arxiv.txt`](abstract_arxiv.txt)다.

```text
Agentic workloads interleave LLM calls with tool execution, and when a session returns from a tool call sets its serving cost. On an RBLN CA25 NPU running vLLM, we decompose that return-arrival process on real hardware into three independent mechanisms: alignment between the concurrent request count and the compiled decode-batch grid, the reuse cliff of a sequence-granular FIFO slot pool, and the serialisation tax of exclusively executed prefill. None responds to a property of an individual request; all three respond to a collective property of arrivals. We establish the first causally, with a recompile intervention that changes only the grid. A step-level simulator carrying all three, with zero fitted parameters, passes a preregistered out-of-sample gate.

On that model we obtain a negative result. Rescheduling returns leaves real offline headroom, but a median 60% of it is coordination: hand every session omniscient knowledge and let it decide independently, and that share disappears. No per-session runtime policy can reach it, in principle. Nor is the remainder reachable: the value of return-time information is workload-specific and vanishes under measured tool latencies, and a published duration estimator, borrowed verbatim, misses the accuracy threshold by a margin four more orders of sample magnitude do not close.

That leaves one reachable lever: a compile-time configuration, which is coordination decided once, in advance, for everybody. Escapement chooses one from workload distribution statistics and the uncalibrated simulator alone, with no device measurement in the selection loop, applies it with a seven-minute recompile, and confirms a 9.7-10.1% device-time recovery at N=8 concurrent sessions, on two channels registered before measurement. Some levers can be bought with a distribution even when no one can predict the individual draw.
```

길이 확인:

```bash
python3 -c "t=open('paper/abstract_arxiv.txt').read().strip(); \
print(len(t), 'chars', 'OK' if len(t)<=1920 else 'OVER by '+str(len(t)-1920))"
```

---

## 2. 국문 초록

Agentic 워크로드는 LLM 호출 사이에 도구 실행 구간을 끼워 넣고, 그 구간이 끝난 뒤 세션이 **언제 돌아오는가**가 서빙 비용을 정한다. 우리는 RBLN CA25 NPU 위의 vLLM 스택에서 그 반환 도착 과정을 실기기로 분해해, 서로 독립인 세 기전이 device time을 만든다는 것을 보인다: (i) 동시 요청 수와 compiled decode batch 격자의 **정렬**, (ii) 시퀀스 단위 FIFO slot pool의 **재사용 절벽**, (iii) 배타 실행 prefill의 **직렬화 세금**. 셋 모두 개별 요청의 속성이 아니라 도착의 집합적 성질에 반응한다. (i)의 인과는 격자만 바꾸는 재compile 개입으로 확정했고(pooled ratio 1.1504 → 0.9717), (ii)의 문턱이 token 총량이 아니라 요청 개수의 함수임을 12/12 결정적 재현으로, (iii)이 실행 중인 모든 세션을 정지시킴을 시간 단위로 관측했다. 세 기전을 담은 보정 파라미터 0개의 step 수준 시뮬레이터는 선등록된 out-of-sample 예측 게이트를 통과한다(최대 오차 0.0040, 허용치 ±0.05).

그 모형 위에서 우리는 **부정적 결과**를 얻는다. 반환 시점을 재배치하면 offline headroom이 실재하지만(현실 tool latency 분포에서 ε=2 s에 5.0–6.9 %), 그 headroom의 중앙 **60 %(49–73 %)** 는 *조율*의 몫이어서 전지적 지식을 주고도 세션별로 독립 결정을 내리면 사라진다. 즉 **per-session runtime 정책은 그 부분에 원리적으로 닿을 수 없다.** 남은 부분도 닿지 않는다: 반환 시각 정보의 값은 워크로드에 종속이라 실측 도구 지연 분포에서 −1.20 % ~ +0.99 %로 소멸하고, 선행 연구의 지속시간 추정자를 그대로 차용해 재면 오차가 정확도 문턱을 5.6–9.7배 초과하며 표본을 네 자릿수 늘려도 줄지 않는다. 이 음성 결과들은 방법론적 함정과 짝을 이룬다 — 자유 파라미터 2개와 20조합 탐색만으로 탐색 seed에서 +4.32 %의 이득이 보이고 평가 seed에서 −0.14 %가 된다.

닿을 수 있는 지점은 **조율을 설계 시점에 굳히는 compile-time 구성** 하나로 남는다. `Escapement`는 그 하나를 집행한다 — device 실측을 전혀 쓰지 않고 워크로드 **분포 통계**와 무보정 시뮬레이터만으로 구성을 고르고, 7분의 재compile로 실기기에 적용해, 측정 전에 등록한 두 개의 독립 채널에서 device time 회수를 확증한다: N=8에서 **+9.72 % / +10.07 %**, 신규 seed의 N=6에서 **+2.11 % / +2.74 %**. Device 절제는 이득의 출처가 조건부임을 보인다 — 기준 구성이 캐시를 많이 잃을 때는 KV pool 크기(`batch_size`)가 이득의 대부분을 내고(+8.25 %), 이미 대부분 재사용하고 있을 때는 남는 것이 bucket 격자 정합뿐이다(+1.52 %p). 개별 draw를 못 맞혀도 분포만 알면 살 수 있는 레버가 있다는 것이 이 논문의 답이다.

---

## 3. 영문 전체판 — 논문 본문용 (3,029자)

**arXiv 초록 필드에는 들어가지 않는다** — 상한을 1,109자 초과한다. 학회 원고의 초록으로 쓴다.

Agentic workloads interleave LLM calls with tool execution, and *when* a session comes back after a tool call is what sets its serving cost. On an RBLN CA25 NPU running the vLLM stack, we decompose that return-arrival process on real hardware and show that three independent mechanisms produce device time: (i) the **alignment** between the number of concurrent requests and the compiled decode-batch grid, (ii) the **reuse cliff** of a sequence-granular FIFO slot pool, and (iii) the **serialisation tax** of exclusively executed prefill. None of the three responds to a property of an individual request; all three respond to a collective property of arrivals. We establish (i) causally through a recompile intervention that changes only the grid (pooled ratio 1.1504 → 0.9717), show that the threshold in (ii) is a function of request *count* rather than total tokens and reproduces 12/12 deterministically, and observe (iii) stalling every concurrent session for the full prefill duration. A step-level simulator carrying all three, with zero fitted parameters, passes a preregistered out-of-sample prediction gate (worst error 0.0040 against a ±0.05 tolerance).

On top of that model we obtain a **negative result**. Rescheduling return times leaves real offline headroom (5.0–6.9 % at a 2 s budget under a measured tool-latency distribution), but a median **60 % (49–73 %)** of that headroom is *coordination*: hand every session omniscient knowledge and let it decide independently, and that share disappears. **No per-session runtime policy can reach it, in principle.** The remainder is not reachable either: the value of return-time information is workload-specific and vanishes (−1.20 % to +0.99 %) under measured tool latencies, and borrowing a published duration estimator verbatim yields errors 5.6–9.7× above the accuracy threshold that do not shrink when per-tool samples grow by four orders of magnitude. These negatives come paired with a methodological trap: two free parameters and a 20-configuration search manufacture a +4.32 % gain on exploration seeds that becomes −0.14 % on held-out seeds.

That leaves exactly one reachable lever — a **compile-time configuration**, which is coordination decided once, in advance, for everybody. `Escapement` exercises exactly that lever. Using only workload *distribution* statistics and the uncalibrated simulator, with no device measurement in the selection loop, we choose a configuration, apply it with a seven-minute recompile, and confirm the device-time recovery on two independent channels registered before measurement: **+9.72 % / +10.07 %** at N=8 and **+2.11 % / +2.74 %** at N=6 on a fresh seed. A device-side ablation shows the gain's source is conditional: when the baseline loses much of its cache, KV pool size (`batch_size`) supplies most of the gain (+8.25 %); when the baseline already reuses nearly everything, all that remains is bucket-grid alignment (+1.52 pp). The answer this paper offers is that some levers can be bought with a distribution even when no one can predict the individual draw.

---

## 4. 조건 병기 점검 (오독 방지)

[CLAIMS.md](CLAIMS.md)의 전수 점검 표를 **세 판본 모두**에 적용했다. 아래는 전체판 기준이며, 압축본에 남은 수치(`60 %`, `9.7–10.1 %`)의 병기는 위 §용도별 판본에 적었다.

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
