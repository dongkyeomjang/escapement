# 선등록 — 개입 격자의 step 비용 실측과 device time 검증

이 문서는 측정 **시작 전에** commit한다. 아래의 실험 격자, 산출 정의, 판정 기준,
예측, 무효 규칙은 측정 후에 바꾸지 않는다. 결과를 보고 완화하지 않으며, 완화가
불가피하면 원 기준의 실패를 함께 보고한다.

## 목적

[TASK54](TASK54.md)가 격자 → padding의 인과를 동일 trace로 확정했으나 세 가지가
열려 있다.

1. **개입 격자의 `C(6)`은 보간값이다.** `config_search.descriptor_for`가 `C(4)`와
   `C(8)` 사이를 선형 보간해 **11.8975 ms**를 쓴다([TASK52](TASK52.md)·
   [TASK26](TASK26.md)이 같은 성질을 `확인되지 않은 사항`으로 기록).
2. **재compile이 기존 bucket의 실행 비용을 바꾸지 않았다는 통제 확인이 없다.**
   두 artifact는 `prefill.rbln` 바이트도 다르다([TASK54](TASK54.md) `확인되지 않은
   사항`). `C(1)`·`C(2)`·`C(4)`·`C(8)`이 같은지 잰 적이 없다.
3. **개입 배치에서 padding → device time 환산이 실측과 맞는지 검증되지 않았다.**

**이 TASK는 기존 판정을 재산출하지 않는다.** [TASK13](TASK13.md)의 `C(1,2,4,8)`,
[TASK54](TASK54.md)의 P1–P3, [TASK23](TASK23.md)·[TASK52](TASK52.md)의 수치는 그대로
둔다. 새 값은 병치하고, 바뀌는 것이 있으면 그 사실을 별도로 보고한다.

## 승인 범위 (Advisor 지시문, 사용자 전달)

승인: serving 기동·종료(예상 10회 내외), `experiments/npu/` script 추가,
`docs/research/` 문서 작성.
금지: **compile, patch 변경, 기존 판정 수정.**

집행 예정 lifecycle: **9회** (mb 4 level + mb6 5 level). 승인 범위 안이다.

## Substrate 상태 (측정 전 확인)

`bash patches/vllm_rbln-0.11.1/apply.sh status`가 `patched`
(SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`)가
아니면 시작하지 않는다. 측정 전후로 덤프해 무차이를 확인한다.

## Model artifact (재compile 없음)

[TASK54](TASK54.md)와 **같은 2종, 같은 manifest hash**여야 한다. 측정 전 재산출해
대조하고 어긋나면 시작하지 않는다.

| 격자 | 경로 | manifest sha256 |
|---|---|---|
| `(1,2,4,8)` `mb` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb` | `b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f` |
| `(1,2,4,6,8)` `mb6` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb6` | `348f2863eb5f8ee6b12da4ec7b73e2e7bb5227cb610fa4e610310a7032cd24bf` |

## 파트 1·2 — `C(bucket)` 실측 (신규 측정)

### 방법은 [TASK13](TASK13.md)과 **동일**하다

바꾸는 것은 artifact와 level 집합뿐이다.

| 항목 | 값 |
|---|---|
| probe | [`decode_cost_probe.py`](../../experiments/npu/stage2/decode_cost_probe.py) (수정 없음) |
| prompt | `experiments/npu/stage1/prompt.txt` (59 B, 20 token) |
| `--max-tokens` | **512** (level당 511 decode step) |
| `--seed` | **20260819** ([TASK13](TASK13.md)과 동일) |
| server | level마다 fresh. `vllm serve <artifact> --host 127.0.0.1 --port 8000`. **prefix caching flag 없음**([TASK13](TASK13.md)과 동일) |
| env | `VLLM_LOGGING_LEVEL=DEBUG`, `VLLM_RBLN_METRICS=1` |
| 종료 | `SIGTERM` (이때 `FINAL PERFORMANCE STATISTICS [MODEL]`·`[SAMPLER]`가 로그에 남는다) |

### level 격자

| artifact | level | 기대 bucket |
|---|---|---|
| `mb` | 1, 2, 4, 8 | 1, 2, 4, 8 |
| `mb6` | 1, 2, 4, **6**, 8 | 1, 2, 4, **6**, 8 |

**level = 실제 동시 요청 수**이고 두 artifact에서 level 1·2·4·8은 같은 bucket으로
간다. 따라서 통제 비교는 `actual`까지 같은 짝이며 `g(actual)` 항이 상쇄된다.

총 **9 serving lifecycle**.

### 실행 순서 (측정 전 고정)

`balanced_arm_orders(configs, rounds=1, base_seed=20260955, block_id="task55-order")`
의 반환값. `configs`는 `["mb.L1","mb.L2","mb.L4","mb.L8","mb6.L1","mb6.L2","mb6.L4","mb6.L6","mb6.L8"]`
순서로 만든다. 산출된 순서:

```
mb.L8 → mb6.L2 → mb.L4 → mb6.L1 → mb.L2 → mb6.L8 → mb6.L6 → mb6.L4 → mb.L1
```

두 artifact가 섞이므로 시간 표류가 한쪽에 실리지 않는다.

### 산출 정의

[TASK13](TASK13.md)과 같은 세 채널을 쓰고 이름을 그대로 쓴다.

- **채널 B(model span)** — 서버 종료 로그 `[MODEL]` 절의 `DECODE METRICS` p50.
  `C_model(b)`라 부른다
- **채널 B(sampler span)** — `[SAMPLER]` 절의 `DECODE METRICS` p50
- **`C_fixed(b) = C_model(b) + C_sampler(b)`** — 이것이 descriptor의
  `fixed_s_by_bucket`에 들어가는 양이다
- **채널 C(end-to-end ITL)** — client chunk 간격 raw 표본. level당 `511 × level` 개.
  **판정에 raw 표본이 필요한 유일한 채널**
- **채널 D(server mean ITL)** — `/metrics` 증분. 채널 C 오염 확인용

### 예측 = 판정 기준 (측정 전 고정)

| # | 예측 | 판정 방법 |
|---|---|---|
| **P1** | `mb6`에서 `C_model(1) < C_model(2) < C_model(4) < C_model(6) < C_model(8)` (단조 증가) | 네 부등식 전부 성립하면 `PASS` |
| **P2a** | 재compile은 기존 bucket의 실행 비용을 바꾸지 않는다 — `b ∈ {1,2,4,8}`에서 **`|C_model,mb6(b) − C_model,mb(b)| ≤ 0.03 ms`** | 4개 전부 만족하면 `PASS` |
| **P2b** | 같은 조건으로 `C_fixed`에서 **`|Δ| ≤ 0.06 ms`** | 4개 전부 만족하면 `PASS` |
| **P2c** | 채널 C 중앙 ITL의 `mb6/mb` 비가 **1 ± 0.005** 안 | 4 level 전부 만족하면 `PASS` |

**변동 기준의 유도 (측정 전).** [TASK13](TASK13.md)이 같은 bucket을 여러 level에서
관측해 남긴 **bucket 내 범위**를 그대로 쓴다.

| bucket | 관측 level | `C_model` 범위 | `C_fixed` 범위 |
|---|---|---|---|
| 4 | L3, L4 | 10.36 / 10.35 → **0.01 ms** | 10.83 / 10.82 → **0.01 ms** |
| 8 | L5–L8 | 12.39–12.42 → **0.03 ms** | 12.95–13.01 → **0.06 ms** |

관측된 최대 범위가 `C_model` **0.03 ms**, `C_fixed` **0.06 ms**이므로 그 값을
그대로 밴드로 등록한다. **관례값이 아니라 [TASK13](TASK13.md) 자료에서 온 수치이며,
측정 후에 넓히지 않는다.**

P2c의 `±0.005`(0.5 %)는 [TASK13](TASK13.md)이 관측한 **가장 작은 bucket 경계 효과**
`2→4`의 `+4.6 %`의 약 1/10이다. 실행 비용이 바뀌었다고 말하려면 최소한 실재하는
bucket 효과와 같은 자릿수여야 한다는 뜻이며, 그보다 한 자릿수 작은 차이는 bucket
비용의 변화로 읽지 않는다.

**보조 검정 (연구 원칙 17).** 채널 C는 raw 표본이 있으므로 level별로
[`bootstrap_ratio.py`](../../experiments/npu/analysis/bootstrap_ratio.py)의
`median_ratio_ci`(resamples 2000, base seed `20260955`, CI 폭 상한 **0.10** —
[TASK13](TASK13.md)과 동일)로 `mb6/mb` 중앙 비의 CI를 낸다.

**[TASK13](TASK13.md)이 이미 보인 대로, 표본이 수천이면 0.1 % 차이도 CI가 1을
배제한다.** 따라서 **`DIFFERENT`가 나오는 것은 예상 범위이고 그것만으로 P2a–P2c를
기각하지 않는다.** 판정은 **효과 크기**(P2a·P2b의 밴드, P2c의 ±0.5 %)로 하고 CI는
크기의 불확실성을 함께 보고하는 용도로 쓴다. 이 방침을 **측정 전에** 고정한다.

**`C_measured(6)` 대 보간값 `11.8975 ms`의 차이는 판정 없이 보고만 한다.**
[TASK13](TASK13.md)이 배수당 증가율의 비선형성(+5.7 %, +4.6 %, +17.8 %)의 원인을
`UNKNOWN`으로 남겼으므로 `[4, 8]` 구간의 곡률에 방향을 걸 근거가 없다. **방향을
예측하지 않는다.**

### 게이트 (fail-loud)

| # | 검사 | 위반 시 |
|---|---|---|
| G1 | level마다 전 요청 status 200, chunk 수 512 단일값 | 해당 level `INVALID` |
| G2 | level마다 `[BUCKET]` 줄 **511개**, `request_nums` 단일값 = level, `padded_batch_size` 단일값 = 기대 bucket | 해당 level `INVALID` |
| G3 | artifact manifest hash가 [TASK54](TASK54.md) 기록과 동일 | **시작하지 않는다** |
| G4 | patch SHA256 측정 전후 동일 | TASK `INVALID` |
| G5 | 채널 D ≈ 채널 C (평균이 같은 자릿수) | 보고. 어긋나면 채널 C 오염을 의심하고 그 사실을 기록 |

`INVALID` level은 **같은 선등록 칸을 1회 재실행**하고, 재실행도 실패하면 그 level을
`INVALID`로 보고한다([TASK23](TASK23.md) 원칙 3).

## 파트 3 — device time 검증 (기존 자료 + 실측 `C`)

### 대상

[TASK54](TASK54.md)의 저장 run `results/npu/stage2/20260908-133635-grid-paired/`
**24칸 전부**(이미 `VALID`). 새 serving 없음.

### 채널

[`config_device.py`](../../experiments/npu/analysis/config_device.py)의 함수를
**그대로 import**한다.

- **채널 A′(모형)** = `channel_a_prime` — `[BUCKET]` step 열 × step 비용 +
  실제 계산 prefill token × [TASK22](TASK22.md) `PrefillCostModel`.
  **step 비용만 이번 실측값으로 갈아끼운다**(`fixed_s_by_bucket`).
  `marginal_s_per_request`·`intercept_s`·prefill 모형은 [TASK13](TASK13.md)·
  [TASK22](TASK22.md) 값 그대로 둔다 — 이번에 재적합하지 않는다
- **채널 B(무모형)** = `channel_b` — client `sent_s`/`done_s`의 in-flight 구간 합집합

### 조건 짝과 허용차

`τ(N) = max(0.02, r_BASE / B_BASE)`, `r = B − A′` ([TASK36](TASK36.md) 유도,
[TASK40](TASK40.md)·[TASK50](TASK50.md)과 같은 형태). 채널 간 차이는
`gap = |A′_x/A′_y − B_x/B_y|`.

짝은 **8개**이며 `BASE`(분모)를 다음과 같이 고정한다.

| 짝 종류 | 개수 | 분자 | 분모(`BASE`) |
|---|---|---|---|
| arm 짝 | 4 (격자 2 × N 2) | AGENTIC | **CONVENTIONAL** |
| 격자 짝 | 4 (N 2 × arm 2) | `mb6` | **`mb`** |

3반복 합산(pooled)으로 판정하고 반복별 값도 보고한다.

| # | 예측 | 판정 방법 |
|---|---|---|
| **P3** | 8개 짝 전부 `gap ≤ τ(N)` | 8/8 만족하면 `PASS`. 하나라도 넘으면 그 짝을 명시해 `FAIL` |

고정 하한 `0.02`만으로 본 결과도 함께 보고한다(판정 아님, [TASK35](TASK35.md)·
[TASK36](TASK36.md)과 같은 관행). `τ`가 커서 검정력이 낮으면 **그 사실을 결과와 함께
보고**하고 `τ`를 사후에 조이지 않는다.

## 파트 4 — 표

리뷰어가 지정한 형식 그대로 낸다.

1. **`C(bucket)` 전후 비교표** — bucket × {`mb` 실측, `mb6` 실측, 차이, 밴드 통과,
   [TASK13](TASK13.md) 기록값, 보간값(bucket 6만)}
2. **격자 × {Δpadding, Δdevice time} 2×2 요약표** — N마다 하나씩. `Δpadding`은
   [TASK54](TASK54.md)의 `Δp = p_CONV − p_AGENTIC`(재산출 아님, 인용),
   `Δdevice time`은 이번 실측 `C`로 만든 **decode device time 비
   `A/C`** 다([TASK26](TASK26.md)·[TASK52](TASK52.md)·[TASK53](TASK53.md)의 `busy 비`와
   같은 정의). 보간 `C`로 만든 값도 같은 표에 병기해 **실측이 결론을 바꾸는지**
   보인다

## 필수 기록 항목

level별: `server-*.log`(METRICS·`[BUCKET]` 전문), `probe/decode_cost.level*.json`
(ITL raw 표본 전체), `probe-*.log`. 전체: patch status 전후, `rbln-smi` 전후,
artifact manifest hash 대조, 측정 시작·종료 시각, 선등록 commit hash, 실제 실행 순서,
disk 사용량.

## 관련 문서

- [TASK13](TASK13.md) / [DECODE_COST_PREREG.md](DECODE_COST_PREREG.md) — 방법과 변동 기준의 출처
- [TASK54](TASK54.md) / [GRID_PAIRED_PREREG.md](GRID_PAIRED_PREREG.md) — 검증 대상 배치
- [TASK52](TASK52.md) / [PADDING_RATIO.md](PADDING_RATIO.md) — `Δp`와 보간 `C`의 한계 기록
- [TASK36](TASK36.md) / [TASK40](TASK40.md) — `τ(N)` 형태의 유도와 사용례
- [TASK22](TASK22.md) — prefill 비용 모형
- [TASK26](TASK26.md) — device time 관측 4
