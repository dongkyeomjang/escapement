# TASK59 — 3.3 관측 의미와 부록 판정 기준 감사

## 상태

DONE

## 판정

감사 계획: [OBSERVATION_AUDIT_PLAN.md](OBSERVATION_AUDIT_PLAN.md) (commit `bd9b5ec`,
재집계 전). 기준 main `2fffa5e`와 **차이 없음**.
**신규 측정 0, compile 0, serving lifecycle 0, 신규 요청 0.**
patch 상태 감사 전후 **`patched`, SHA256 `70942d16…`, 무변화**.

| 감사 | 결과 |
|---|---|
| **1. 도착 간격의 의미** | `arrivals_s`는 **비어 있지 않은 SSE 조각의 client 수신 시각**이다. **조각 1개 = token 1개는 검증되지 않았다** — 저장 자료에 조각별 token 수가 없다. **논문 명칭을 "streaming 응답 도착 간격"으로 유지**한다. 수준별 수치는 재현됐고, **"1 ms 이내 동시"는 경계 시각 일치**(시작 차 0.082–0.241 ms, 종료 차 0.101–0.432 ms)이지 교집합 폭이 아니다 |
| **2. prefill 지표** | `first_token_ts − scheduled_ts`이며 **완료 시점에만** histogram에 반영되고 **prefill 중 선점을 포함**한다. 부를 수 있는 가장 좁은 이름은 **"서버 측 prefill 경과시간"**이다. 비용 모형 4점 재현(최대 잔차 2.4 ms). **기존 코드는 `T(C)` 독립형을 쓰며**, hit 잔여분 88 token 등은 적합 구간 `[500, 6000]` **밖의 외삽**이다. v2 보정의 ITL 합은 **서버 집계 counter**이지 client streaming 실측이 아니다 |
| **3. 용량 개입의 간섭** | **직접 측정 불가.** 병행 세션 streaming 시계열·요청별 prefill 시각·prefill 시점 대기 세션 수가 **모두 저장되지 않았고**, 서버 로그 시각은 **1초 해상도**다 |
| **4. 부록 1** | N=7 6블록의 방향 집계는 **위 2 / 밴드 안 4 / 아래 0**으로 5/6 요건 미충족 → `INCONCLUSIVE`가 재확인된다. **"측정 변동 수준"이라 쓸 직접 근거가 없다** → **"사전 판정 기준에서 차이를 확정하지 못함"** 으로 수정안을 제시한다 |
| **5. 부록 2** | 반올림 전 하락분 `0.17492639163881424`, Shapley 잔차 **정확히 0.0**. 두 분해는 **같은 자료의 서로 다른 분해이며 독립 실험이 아니다** |

**기존 TASK의 판정·수치를 하나도 바꾸지 않았다.**

## 날짜

2026-09-09

## 배경

관련 TASK: [TASK15](TASK15.md), [TASK18](TASK18.md), [TASK20](TASK20.md),
[TASK22](TASK22.md), [TASK25](TASK25.md), [TASK35](TASK35.md), [TASK50](TASK50.md),
[TASK56](TASK56.md), [TASK58](TASK58.md).

3.3은 **세 개의 서로 다른 실험**을 연결한다 — 재사용 실패와 재계산량, prefill 주입 중
병행 세션의 도착 간격, 용량 개입의 재사용·계산량 변화. **단일 사건 추적이 아니다.**
[TASK44](TASK44.md)는 원고 교정 작업이므로 지연의 측정 근거로 쓰지 않았다.

## 시작 상태

- 기준 public main `2fffa5eb1a80460db33adc13843984ddbb129f79` — **현재 main과 동일**
- 감사 계획 commit `bd9b5ec` — 모든 재집계보다 앞섬
- `git status --short`: `?? .idea/`만
- patch: `patched`, SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`

## 변경된 파일

- `docs/research/OBSERVATION_AUDIT_PLAN.md` (재집계 전 commit `bd9b5ec`)
- `experiments/npu/analysis/observation_audit.py` (신규)
- `docs/research/TASK59.md`, `docs/research/EVIDENCE_3_3.md`,
  `docs/research/PAPER_3_3.md` (신규)
- `docs/research/INDEX.md` (갱신)

**기존 TASK 문서·원자료·설치 package를 수정하지 않았다.**

## 결과

### 감사 1 — 응답 도착 간격의 측정 의미

#### 1-1. `arrivals_s`가 기록하는 사건

```python
# prefill_tax_probe.py:111-112
if obj.get("choices", [{}])[0].get("text", ""):
    arrivals.append(time.perf_counter() - origin)
```

**비어 있지 않은 `choices[0].text`를 가진 SSE 조각의 client 수신 시각**이다.
server가 token을 낸 시각도, device가 step을 끝낸 시각도 아니다.

#### 1-2. 조각 1개 = token 1개인가 — **검증되지 않았다**

저장 레코드의 stream field는 `bystander`, `status`, `arrival_count`, `arrivals_s`
**4개뿐**이며 **조각별 token 수가 없다.**

전 12 run에서 `arrival_count`가 4개 bystander 모두 **800**이고 `bystander_max_tokens`가
**800**이다. 이는 1:1과 **일관**되지만, 계획에 고정한 판정 규칙("조각별 token 수를
직접 확인한 자료")을 충족하지 못한다.

→ **논문 명칭을 "streaming 응답 도착 간격"으로 유지하고 "token 간 간격"이라 쓰지
않는다.**

#### 1-3. 정의

| 이름 | 정의 (`prefill_tax.py`) |
|---|---|
| injection window | `[injection.sent_s, injection.done_s]` — **client 측** 전송·수신 시각 |
| in-window interval | `end > sent_s and start < done_s` (**중첩**) |
| baseline | in-window가 **아닌** interval gap의 중앙값 (bystander별) |
| spike | in-window interval 중 gap 최대 (bystander별) |
| 동시성 **판정 기준** | `max(spike_start) < min(spike_end)` — **공통 교집합이 비어 있지 않음** |

#### 1-4. 수준별 재현 — 중앙값 적용 순서를 명시한다

**순서 ①(고정): bystander 4개의 중앙값(run 내) → 반복 3개의 중앙값(수준 내).**

| 수준 | 중앙 prefill (ms) | 중앙 spike ① (ms) | 순서 ②(반복→bystander) | spike/prefill |
|---|---|---|---|---|
| 500 | **88.52** | **100.87** | 100.84 | 1.140 |
| 2000 | **359.57** | **372.57** | 372.57 | 1.036 |
| 6000 | **1177.20** | **1191.68** | 1191.68 | 1.012 |

지시문의 `88.5 / 359.6 / 1177.2`와 `100.9 / 372.6 / 1191.7`이 **그대로 재현**된다.
**두 순서는 수준 500에서만 0.03 ms 다르고 나머지는 같다.**

#### 1-5. "1 ms 이내 동시"의 정체 — **경계 시각 일치**

전 9 run에서 세 값을 각각 냈다.

| tag | 시작 시각 차 (ms) | 종료 시각 차 (ms) | 공통 교집합 폭 (ms) |
|---|---|---|---|
| inj500.r0 / r1 / r2 | 0.170 / 0.134 / 0.082 | 0.275 / 0.253 / 0.101 | 100.4 / 100.7 / 100.8 |
| inj2000.r0 / r1 / r2 | 0.161 / 0.181 / 0.215 | 0.407 / 0.328 / 0.432 | 372.2 / 373.7 / 371.1 |
| inj6000.r0 / r1 / r2 | 0.160 / 0.097 / 0.241 | 0.210 / 0.205 / 0.194 | 1189.8 / 1191.6 / 1194.6 |

- **시작 차 0.082–0.241 ms, 종료 차 0.101–0.432 ms** — 둘 다 1 ms 미만
- **공통 교집합 폭은 100–1195 ms**로 spike 길이 자체다

→ **"1 ms 이내"는 시작·종료 시각의 일치를 뜻하며 교집합 폭이 아니다.**
그리고 **판정 기준은 그보다 훨씬 약한 "교집합이 비어 있지 않음"** 이었다.
**관측된 일치가 기준보다 강하다** — 이 둘을 구분해 써야 한다.

#### 1-6. 대조 3 run — 원 `PARTIAL` 판정을 보존한다

| tag | bystander별 최대 간격 (ms) | 그 간격의 종료 시각 (s) |
|---|---|---|
| inj0.r0 | 148.3 / 214.6 / 81.0 / **16.7** | 0.308 / 0.308 / 0.308 / **2.927** |
| inj0.r1 | 217.5 / 80.7 / **17.6** / 148.5 | 0.321 / 0.321 / **8.427** / 0.321 |
| inj0.r2 | 217.1 / 149.7 / **18.7** / 81.8 | 0.324 / 0.324 / **8.215** / 0.324 |

**큰 간격(81–218 ms)은 전부 t ≈ 0.31–0.32 s에서 끝난다** — bystander 자신들의 시작
prefill이 직렬화된 서명이며, 주입 창 `[3.01, 4.22] s`와 분리된다.

**원 판정 `PARTIAL`을 그대로 보존한다. warm-up 제외 재판정을 새 확증으로 만들지
않는다.**

작은 정정 1건: [TASK22](TASK22.md) 본문은 "2건은 t ≈ 8.2–8.4 s"라 적었으나 실제로는
**inj0.r0의 작은 간격이 2.927 s**이고 8.2–8.4 s는 r1·r2 두 건이다. **큰 간격이 모두
t < 0.33 s라는 논지는 영향받지 않는다.**

### 감사 2 — prefill 시간 지표와 비용 모형

#### 2-1. 지표의 시작·종료와 반영 시점 (설치 소스)

```python
# vllm/v1/metrics/stats.py:442-444
# Prefill interval is from first SCHEDULED to first NEW_TOKEN
# Any preemptions during prefill is included in the interval
prefill_time = req_stats.first_token_ts - req_stats.scheduled_ts
```

```python
# vllm/v1/metrics/loggers.py:1178-1189
for finished_request in iteration_stats.finished_requests:
    ...
    self.histogram_prefill_time_request[engine_idx].observe(
        finished_request.prefill_time)
```

| 항목 | 값 |
|---|---|
| 시작 | 첫 `SCHEDULED` 이벤트 시각 (`stats.py:421-422`) |
| 종료 | 첫 `NEW_TOKEN` 시각 (`stats.py:397`) |
| counter 반영 | **요청이 완료될 때만** |
| 포함되는 것 | scheduling 이후의 host·scheduler 처리, **prefill 중 선점**(upstream 주석) |
| 제외되는 것 | queue 대기(`queued_ts → scheduled_ts`는 별도 지표) |

#### 2-2. 창에서 완료되는 요청이 주입뿐인가 — **원자료로 확인**

| 검사 | 결과 |
|---|---|
| `request_prefill_time_seconds_count` 증분 | **9/9 run에서 1** |
| 창 종료 전에 끝난 bystander | **9/9 run에서 0/4** (전 bystander가 `arrival_count = 800 = max_tokens`이고 마지막 도착이 `done_s` 이후) |

**두 조건이 모두 만족되므로 `sum` 증분을 주입 요청 하나의 값으로 읽는 것이 정당하다.**

#### 2-3. 어디까지 부를 수 있는가 — **"서버 측 prefill 경과시간"**

| 등급 | 판정 | 근거 |
|---|---|---|
| 순수 device 실행시간 | **아니다** | 시작이 device 호출이 아니라 **scheduling 이벤트**이고, 선점이 포함된다 |
| **서버 측 prefill 경과시간** | **예 — 이것이 정확한 이름** | `first_token_ts − scheduled_ts`의 정의 그대로 |
| 배타 점유시간의 근사 | **조건부** | [TASK22](TASK22.md)의 **별도 관측**(bystander 도착 간격, 9/9 교집합, spike/prefill 1.012–1.140)이 있을 때만. 그 비가 **1을 넘는 몫은 미분해**(`UNKNOWN`)다 |

#### 2-4. `PrefillCostModel` 재현

```
prefill_s(n) = ceil(n / 128) × (0.021206 + 6.399e-07 × n)
```

**지시문의 `q`에 해당하는 이름의 파라미터는 코드에 없다.** field는
`chunk_tokens = 128`, `per_chunk_s = 0.021206`, `drift_s_per_token = 6.399e-07`다.

| n | 관측 (s) | 모형 (s) | 잔차 (ms) | chunk 수 | chunk당 (ms) |
|---|---|---|---|---|---|
| 500 | 0.0885 | 0.0861 | **−2.4** | 4 | 21.53 |
| 2000 | 0.3596 | 0.3598 | +0.2 | 16 | 22.49 |
| 2008 | 0.3592 | 0.3599 | +0.7 | 16 | 22.49 |
| 6000 | 1.1772 | 1.1771 | −0.1 | 47 | 25.05 |

**최대 잔차 2.4 ms** 재현. 적합 4점 중 2,008은 [TASK15](TASK15.md)에서 왔다.

**128의 의미를 구분해 둔다.** 128은 scheduler의 chunk 예산
(`max_num_batched_tokens`)이며, **backend 내부의 device 호출 분할이 아니다** —
[TASK15](TASK15.md)가 `PREFILL Total call counts = 요청 수`를 관측해 **요청 1건당
device forward 1회**임을 확정했다. 따라서 **128은 적합 단위이지 관측된 실행 분할이
아니다.** 또한 [TASK24](TASK24.md)가 확정한 대로 이 스택은 한 step에서 prefill과
decode를 섞지 않으므로 **decode 교차 실행도 이 시간 안에 없다.**

#### 2-5. `T(L) − T(L−C)` 대 `T(C)` — 기존 코드는 **독립형**을 쓴다

`ceil(·)`과 drift 항 때문에 두 값이 다르다.

| L | C | `T(L) − T(L−C)` (s) | `T(C)` (s) | 차 (ms) |
|---|---|---|---|---|
| 2008 | 88 | 0.0233 | 0.0213 | **2.07** |
| 2008 | 1920 | 0.3386 | 0.3365 | 2.07 |
| 1490 | 338 | 0.0684 | 0.0643 | **4.16** |
| 6000 | 500 | 0.1139 | 0.0861 | **27.84** |
| 600 | 100 | 0.0218 | 0.0213 | 0.58 |

**기존 코드는 전부 `T(C)` 독립형이다.**

- `config_device.py:84` — `pm.prefill_s(max(prompt_tokens − cached_tokens, 0))`
- `sim/engine.py:465` — `prefill_model.prefill_s(computed)`

**적합 구간은 `[500, 6000]` token이다.** hit이 난 재도착 요청의 잔여 계산량은
[TASK15](TASK15.md)에서 **88 token**, [TASK54](TASK54.md) 배치에서 수백 token
수준이므로 **500 미만 구간은 외삽**이다. 이 구간에서 모형은 `ceil(n/128) = 1`의
평평한 값(약 21.3 ms)을 주며 **관측점이 없다.**

#### 2-6. v2 보정의 ITL 합 — **서버 집계 counter**

```python
# utilization.py:28, 141
ITL_SUM_RE = re.compile(r"^vllm:inter_token_latency_seconds_sum(?:\{[^}]*\})? (\S+)$")
"measured_itl_sum_s": itl_sum_measured,
```

- **분모(measured)** = `/metrics` 덤프의 `vllm:inter_token_latency_seconds_sum`
  — **서버 측 누적 counter**다. **client streaming 실측이 아니고, 요청 길이·시간으로
  만든 대용 지표도 아니다**
- **분자(predicted v1)** = `Σ actual × step_time_s(actual)` — [TASK13](TASK13.md)
  step 비용 모형에서 나온 **모형값**
- **v2** = `v1 + (run의 prefill 시간 합) × (평균 running)`.
  prefill 시간 합은 같은 `/metrics` 덤프에서, 평균 running은
  `Σ(request_nums)/decode_steps`에서 온다

집계 경로: **모형 예측 / 서버 counter**의 비가 12칸에서 0.565–0.855(N 단조 의존)였고,
prefill 항을 더한 뒤 0.973–1.039로 모인다. **평균 running으로 prefill 시점의 running을
대체한 근사**이며 [TASK22](TASK22.md)가 그 잔차(±3.9 %)를 `UNKNOWN`으로 남겼다.

### 감사 3 — 용량 개입에서 간섭의 직접 확인 — **불가**

#### 3-1. 목록화 (먼저 수행)

| 필요한 것 | 저장 여부 |
|---|---|
| 병행 세션별 streaming 시계열 | **없음** — 이 실험의 요청은 `stream: False`다 |
| 요청별 prefill 시작·종료 시각 | **없음** |
| prefill 시점의 decode 대기 세션 수 | **없음** |
| client row의 시각 | `sent_s`, `done_s` (**요청 단위**, `perf_counter`) |
| 서버 로그 시각 | **1초 해상도** (예: `08-23 23:13:14`) |
| `[PFX]` 66줄, `[BUCKET]` 891줄 | **자체 timestamp 없음** |

#### 3-2. 판정

**1초 해상도 로그에서 ms 수준 동시성을 복원하지 않는다**는 계획의 규칙에 따라
**"직접 측정 불가"로 마감한다.** 요청별 prefill 시간과 병행 세션 중첩을 집계하지
않았다.

**전체 N이나 decode step 전체의 평균 running을 prefill 시점의 세션 수로 대체한 값은
직접 관측으로 보고하지 않는다.** [TASK22](TASK22.md) 사후 대조가 그 대체를 썼고
그 잔차가 `UNKNOWN`으로 남아 있다.

#### 3-3. 단위 확인 — 중복 합산 경로 없음

```python
# sim/engine.py:183-193
busy_s     = decode_busy_s + prefill_busy_s      # 단위 s   — prefill을 1회만 센다
stall_s    = Σ duration_s × running (prefill)     # 단위 session·s — 별도 property
```

`channel_a_prime`(`config_device.py:76-88`)도 `decode + prefill`만 더하며
**`stall_s`를 device time에 합산하지 않는다.** `stall_s` 호출부는 oracle·ablation·
sim_compare의 **보고 경로뿐**이다.

→ **장치 점유시간(`s`)과 누적 대기시간(`session·s`)이 분리돼 있고 중복 합산 경로가
없다.**

### 감사 4 — 부록 1의 판정 기준과 반복별 Δp

#### 4-1. 두 기준은 다르다

| 기준 | 값 | 대상 |
|---|---|---|
| **예측 오차 허용치** | `|sim pooled − measured pooled| ≤ 0.05` | 신규 3블록 pooled에 대한 **out-of-sample 게이트** |
| **방향 판정 밴드** | `[0.97, 1.03]` + **6블록 중 5블록 이상 동방향 그리고 pooled가 밴드 밖** | **6블록 합산 재판정** |

**전자는 모형 예측력의 게이트, 후자는 조건 간 차이의 판정이다. 섞지 않는다.**
5/6 요건의 근거는 부호검정 한쪽 꼬리 `P(X≥5) = 7/64 = 0.109 ≤ 0.125`
([SIM_OOS_PREREG.md](SIM_OOS_PREREG.md), 측정 전 고정).

#### 4-2. N=7의 6블록 — `[BUCKET]` 합계에서 직접 산출

`p`는 각 블록의 `Σ(b−n)/Σb`에서 직접 만들었다. **반올림된 `R`로 역산하지 않았다.**

| 배치 | 블록 | `u_A` | `u_C` | `R = u_A/u_C` | 밴드 | `p_A` | `p_C` | `Δp = p_C − p_A` |
|---|---|---|---|---|---|---|---|---|
| 기존 | b0 | 0.8313 | 0.8373 | 0.9928 | 안 | 0.1687 | 0.1627 | **−0.0060** |
| 기존 | b1 | 0.8344 | 0.8157 | 1.0229 | 안 | 0.1656 | 0.1843 | **+0.0187** |
| 기존 | b2 | 0.8764 | 0.8362 | 1.0481 | **위** | 0.1236 | 0.1638 | **+0.0402** |
| 신규 | b3 | 0.7820 | 0.7882 | 0.9922 | 안 | 0.2180 | 0.2118 | **−0.0062** |
| 신규 | b4 | 0.8677 | 0.7865 | 1.1032 | **위** | 0.1323 | 0.2135 | **+0.0811** |
| 신규 | b5 | 0.8748 | 0.8627 | 1.0140 | 안 | 0.1252 | 0.1373 | **+0.0121** |

**방향 집계: 위 2 / 밴드 안 4 / 아래 0.** 5/6 요건 미충족 →
**`INCONCLUSIVE`가 재확인된다.** [TASK25](TASK25.md)의 "위 2, 아래 0, 밴드 안 4"와
일치한다.

#### 4-3. 합산 — 전체와 배치별을 구분한다

| 집계 | `u_A` | `u_C` | `R` | `p_A` | `p_C` | `Δp` |
|---|---|---|---|---|---|---|
| **6블록 전체** | 0.8422 | 0.8198 | **1.0273** | 0.1578 | 0.1802 | **+0.0223** |
| 기존 3블록 | 0.8472 | 0.8290 | 1.0220 | 0.1528 | 0.1710 | +0.0183 |
| 신규 3블록 | 0.8374 | 0.8113 | 1.0322 | 0.1626 | 0.1887 | +0.0261 |

6블록 pooled `1.0273`이 [TASK25](TASK25.md)의 `1.0273`과 일치한다. 기존 3블록
`1.0220`은 [TASK23](TASK23.md) 2a의 `1.0220`과, 신규 3블록 `1.0322`는
[TASK25](TASK25.md) 게이트의 `1.0322`와 일치한다. **출처·seed는 기존이
`base_seed=20260841`(b0–b2), 신규가 `base_seed=20260850`(b3–b5)이다.**

#### 4-4. `Δp`의 블록 간 산포

최소 **−0.0062**, 최대 **+0.0811**, 범위 **0.0873**, 중앙 **+0.0154**.

**이 산포는 블록 간 trace 차이를 포함한다. 같은 trace를 반복했을 때의 변동이
아니다.**

#### 4-5. [TASK50](TASK50.md)의 채널 비 차이 분포 — **별개의 양**

| 집계 단위 | N | 최솟값 | 중앙값 | 95 분위 | 최댓값 |
|---|---|---|---|---|---|
| 단일 실행 쌍 (45쌍) | 6 | 0.0002 | 0.0184 | 0.0604 | 0.0656 |
| 단일 실행 쌍 (45쌍) | 8 | 0.0002 | 0.0062 | 0.0320 | 0.0343 |
| 3실행 합산 쌍 (2,100쌍) | 6 | 0.0000 | 0.0134 | 0.0326 | 0.0436 |
| 3실행 합산 쌍 (2,100쌍) | 8 | 0.0000 | 0.0068 | 0.0167 | 0.0208 |

**이것은 `|A′_i/A′_j − B_i/B_j|`, 곧 두 device-time 채널의 비가 얼마나 어긋나는가다.**

- **N=7의 원 판정 기준이 아니다** — 그 판정은 `u_A/u_C`의 밴드와 5/6 요건이다
- **`Δp`의 변동 밴드도 아니다** — 세는 양이 다르다
- N도 다르다(6·8 대 7)

#### 4-6. "측정 변동 수준"이라 쓸 근거가 있는가 — **없다**

계획에 고정한 규칙은 "`Δp`(또는 `R`)의 반복 간 변동을 **같은 조건에서 직접 잰**
자료"였다.

| 후보 | 왜 안 되는가 |
|---|---|
| N=7 6블록의 `Δp` 산포 | **블록마다 trace가 다르다.** 처치 없는 반복이 아니다 |
| [TASK50](TASK50.md)의 채널 비 분포 | **다른 양**(device-time 채널 일치도), 다른 N |
| [TASK54](TASK54.md)의 `X = 0.004` | [TASK50](TASK50.md)의 `p` 재현 오차에서 왔고 **N ∈ {6,8}·다른 격자**다 |

→ **수정안**: "측정 변동 수준" 대신
**"사전에 정한 판정 기준에서는 차이를 확정하지 못했다"** 로 쓴다.

### 감사 5 — 부록 2의 계산 정의

- **`h(n)` 동일성**: 해당 conventional 짝에서 두 격자의 `actual` 히스토그램이 통째로
  같음이 게이트로 확인된다([TASK56](TASK56.md) 전제, `padding_decompose.py`가
  다르면 종료).
- **반올림 전 값**

| 항목 | 값 |
|---|---|
| `p` | `0.2323632485143989` → `0.05743685687558466` |
| 하락분 | **`0.17492639163881424`** |
| Shapley `n=6` | `0.14154398411673785` (80.9 %) |
| Shapley `n=5` | `0.0333824075220764` (19.1 %) |
| 합 − 하락분 (잔차) | **`0.0`** (정확히 0) |
| 분자 항 | `0.18558586012494285` (106.1 %) |
| 분모 항 | `−0.010659468486128622` (−6.1 %) |
| 소멸 slot | `1218 = 1525 − 307` |
| `Σbucket` | `6563 → 5345` |

- **두 분해는 같은 자료의 서로 다른 분해이며 독립 실험이 아니다.** 소멸 slot 몫
  (81.1 / 18.9)과 Shapley 몫(80.9 / 19.1)이 0.2 %p 안에서 일치하는 것은 **재현이
  아니라 분모 상호작용의 크기**를 보여주는 것이다.
- **step 기준 기여이지 device time 기여가 아니다.** `p`는 무차원 slot 점유이며
  step 비용이 bucket마다 다르다([TASK13](TASK13.md)). 시간 기준 분해는 하지 않았다.
- **다른 workload에서 `h(n)`이 보존된다고 일반화하지 않는다.** `h(n)`은 이 trace의
  성질이고, gap이 0인 조건에서 도착이 결정적이기 때문에 격자에 불변이었다.

## 핵심 발견

1. **`universal` — 관측 채널의 이름이 그 채널이 세는 것을 넘어설 수 있다.** 도착
   간격은 "token 간 간격"이 아니라 "SSE 조각 간 간격"이고, prefill 지표는 "device
   실행시간"이 아니라 "scheduling부터 첫 token까지의 서버 측 경과시간"이다. 둘 다
   **더 좁은 이름이 정확하다.**

2. **`universal` — 판정 기준보다 관측이 강할 때 둘을 구분해 써야 한다.** 동시성의
   **기준**은 "교집합이 비어 있지 않음"이었고 **관측**은 시작·종료 시각이 0.1–0.4 ms
   안에 모인 것이다. 기준을 인용하면 약하고, 관측을 기준인 양 쓰면 사후 강화다.

3. **`stack` — 비용 모형의 128은 적합 단위이지 관측된 device 분할이 아니다.**
   요청 1건당 device forward는 1회다([TASK15](TASK15.md)). `ceil(n/128)`은 그
   실행 구조가 아니라 시간이 그렇게 계단을 이루더라는 적합이다.

4. **`stack` — 기존 비용 코드는 잔여 계산량에 독립형 `T(C)`를 쓰며, 그 입력이
   적합 구간 아래인 경우가 실제로 있다.** hit 뒤 잔여 88 token은 `[500, 6000]`
   밖이고 그 구간에 관측점이 없다. 두 형태의 차이는 최대 27.8 ms다.

5. **`universal` — 세 실험은 같은 사건의 세 관점이 아니라 서로 다른 run이다.**
   용량 개입 run은 병행 세션 간섭을 **직접 관측할 자료를 애초에 담고 있지 않다**.

6. **`universal` — "측정 변동 수준"은 그 변동을 잰 자료가 있을 때만 쓸 수 있는
   말이다.** 이 저장소에는 N=7 `Δp`의 무처치 반복 자료가 없다.

## 해석

- **(해석)** 감사 2-3의 결론은 3.3의 서술을 좁히지만 [TASK22](TASK22.md)의 판정을
  약화시키지 않는다. 지표가 "서버 측 경과시간"이어도, **그 시간 동안 다른 세션이
  실제로 멈춘다는 것은 bystander 도착 간격이 독립적으로 보여준다.** 두 근거를
  **분리해 인용**하면 주장이 더 강해진다.
- **(해석)** 감사 4의 결론은 부록 1의 논지를 바꾸지 않는다. N=7이 `INCONCLUSIVE`인
  것은 변함없고, 바뀌는 것은 **그 미결을 뭐라고 부르는가**다. "측정 변동 수준"은
  자료가 뒷받침하지 않는 강한 말이다.
- **(hypothesis)** 감사 2-5의 외삽 구간(잔여 < 500 token)이 실제로 얼마나 틀리는지는
  **작은 prompt의 prefill을 재는 것으로만** 알 수 있다. [TASK22](TASK22.md)의 격자가
  500에서 시작한 것이 이 공백의 원인이다.

## 확인되지 않은 사항

- **조각 1개 = token 1개** (`UNKNOWN`). 조각별 token 수를 담은 자료가 없다.
  확인하려면 probe가 조각의 `text`를 tokenize해 기록해야 하며 **재측정이 필요**하다.
- **적합 구간 아래(< 500 token) prefill 시간** (`UNKNOWN`). 관측점이 없다.
- **spike가 prefill 시간을 넘는 몫의 분해** (`UNKNOWN`, [TASK22](TASK22.md) 이월).
- **용량 개입에서 병행 세션 간섭** (`UNKNOWN` — 직접 측정 불가). 필요한 것은
  streaming bystander가 있는 조건에서의 재측정이다.
- **v2 보정 잔차 ±3.9 %의 출처** (`UNKNOWN`, [TASK22](TASK22.md) 이월).
- **N=7 `Δp`의 무처치 반복 변동** (`UNKNOWN`). 같은 trace를 반복한 자료가 없다.

**어느 것도 이번 작업에서 측정하지 않았다.**

## 실패 / 무효 시도

없다. 모든 수치가 원 TASK 기록과 일치했다.

## 정정표 (원문 미수정)

| 대상 | 내용 | 영향 |
|---|---|---|
| [TASK22](TASK22.md) 판정 1 서술 | "2건은 t ≈ 8.2–8.4 s" — 실제로는 inj0.r0의 작은 간격이 **2.927 s**, 나머지 둘이 8.427·8.215 s | **없음.** 큰 간격이 전부 t < 0.33 s라는 논지는 그대로 |
| [TASK22](TASK22.md) 판정 2 서술 | "1 ms 이내로 겹친다" — **경계 시각 차**를 뜻하며 판정 **기준**은 교집합 존재였다 | 서술을 구분하면 더 정확하다 |

## 연구 원칙에 미치는 영향

1. **채널의 이름은 그 채널이 세는 것보다 넓어지기 쉽다.** 지표를 인용할 때 소스의
   시작·종료 정의를 함께 적는다.
2. **판정 기준과 관측의 강도를 구분해 쓴다.** 관측이 기준보다 강하면 둘 다 적고,
   기준을 사후에 관측 수준으로 올리지 않는다.
3. **모형의 적합 구간을 코드가 쓰는 입력 범위와 대조한다.** 적합 밖 입력이 실제로
   들어가면 외삽으로 표시한다.
4. **"측정 변동"이라는 말은 그 변동을 잰 자료를 가리켜야 한다.**

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **조각–token 대응 확인** — probe가 조각 `text`의 token 수를 기록하도록 고치고
   재측정. script 변경과 선등록이 필요하다.
2. **작은 prompt prefill 격자** — 100·200·300·400 token을 추가해 `[500, 6000]`
   아래를 관측점으로 채운다.
3. **용량 개입의 간섭 직접 관측** — bystander를 streaming으로 두는 조건에서 재측정.
4. **N=7 `Δp`의 무처치 반복** — 같은 trace를 반복해 변동을 재면 "측정 변동 수준"이라는
   표현의 근거가 생긴다.

## 재현 정보

- 선등록: **해당 없음** — 신규 측정이 없는 감사다. 감사 계획 commit `bd9b5ec`가
  모든 재집계보다 앞선다
- 기준 commit: `2fffa5eb1a80460db33adc13843984ddbb129f79` (현재 main과 동일)
- 재집계: `env -u PYTHONPATH python3 experiments/npu/analysis/observation_audit.py --output results/npu/stage2/observation_audit.json`
- 입력 (읽기 전용)
  - `results/npu/stage2/20260821-220100-prefill-tax/probe/prefill_tax.*.json` (12)
  - `results/npu/stage2/20260821-222000-grid-observe/util.*.n7.b{0,1,2}.json`
  - `results/npu/stage2/20260822-160532-sim-oos/util.*.n7.b{3,4,5}.json`
  - `results/npu/stage2/20260823-183505-final-confirm/{probe/requests,server-}*.n8.b0.*`
  - `results/npu/stage2/20260908-133635-grid-paired/` ([TASK56](TASK56.md) 경로)
- 설치 소스 (읽기 전용)
  - `vllm/v1/metrics/stats.py:397, 421-422, 442-444`
  - `vllm/v1/metrics/loggers.py:900-907, 1178-1189`
- 저장소 코드 (읽기 전용)
  - `experiments/npu/stage2/prefill_tax_probe.py:111-112, 172-213`
  - `experiments/npu/analysis/prefill_tax.py`
  - `experiments/npu/analysis/utilization.py:28, 141`
  - `experiments/npu/analysis/config_device.py:76-88`
  - `src/continuum/substrate/descriptor.py:119-136`
  - `src/continuum/sim/engine.py:174-193, 460-472`
- patch 상태: 감사 **전후 동일** — `patched`, SHA256 `70942d16…`
- 예산: **compile 0, serving lifecycle 0, 신규 측정 0, 신규 요청 0, device 접근 0**
