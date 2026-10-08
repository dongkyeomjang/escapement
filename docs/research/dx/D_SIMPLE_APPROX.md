# 작업 D — 단순 생존 근사 대 전체 규칙 (기존 검증 집합, 사후 기전 분석)

상태 표지: **`post_hoc` (사후 기전 분석)**. 선등록 없음, blind 결과 아님, 새 장치 측정 0, 튜닝 0.
관측 사건(server `[PFX] [ALLOC]`·`[FREE-REQUEST]`·`[BUCKET]` 순서)을 규칙의 입력으로 쓰므로 1부는 예측이 아니라 기전 대조다. 2부의 요청별 확률도 직전 turn의 관측 token을 입력으로 읽으므로(아래 §2.1) 사후다. **이 문서의 어떤 수치도 선등록된 새 blind 결과로 인용하지 않는다.**

## 0. 입력 manifest

| 항목 | 값 |
|---|---|
| 작업 시작 HEAD | `40d2c75f31760f4b9689863878368a75b434c4e8` |
| 계산 시점 HEAD (JSON `git_head`) | `983f7e68cca511398f39c10dbd4540b8458eb470` — 실행 중 다른 작업의 commit 2개(`983f7e6`, `cc10e53`, 선등록·chain 문서/스크립트)가 들어왔다. `40d2c75..HEAD`에서 `src/`, `experiments/npu/analysis/`, `mt_predict.py`, `mt_measure.py`, `experiments/npu/substrate/` 변경 0(`git diff --stat` 빈 출력) |
| 계산 시각 | 2026-10-08T21:57:19+0900, 284.4 s, Python 3.10.12, CPU만(`taskset -c 64-95`, `nice 19`, 2부만 8 worker) |
| 스크립트 | `experiments/npu/analysis/dx_simple_approx.py` SHA256 `1b5e59bd8c735c88…` |
| 산출 | `results/npu/stage3/dx_simple_approx/dx_simple_approx.json` SHA256 `4505f6521fb38b78…` (비추적), 표 `docs/research/dx/D_SIMPLE_APPROX.csv` |
| 입력 파일 hash | JSON `manifest_sha256`에 530개 파일 전부. 정렬 `"path sha\n"` 연결의 SHA256 = `ac00647e37bf7967…` |
| 집합별 묶음 hash | simblind 135 파일 `6eb1c561…`, ctxblind 90 `bfa1ef82…`, main 195 `5ac2c37d…`, hiload 90 `e246cad2…` |

핵심 코드·입력 SHA256(앞 16자리):

| 파일 | SHA256 | 마지막 변경 |
|---|---|---|
| `src/continuum/model/reference.py` (`FifoReplay`) | `a5bf9faa2b670c8d` | `c58daaf` 2026-09-30 |
| `src/continuum/model/survival.py` (`survives`, `survival_probability`) | `4b935caabc062996` | `8c107a0` 2026-09-29 |
| `src/continuum/model/survival_v1.py` | `832fb1bd720e1e0b` | `c9a526c` 2026-10-01 (LRU underflow만) |
| `src/continuum/substrate/descriptor.py` (`survives_gap`) | `4d942792a425f665` | 함수 본문은 `4c4683c` 2026-08-19 이후 변경 없음(`git log -L`) |
| `experiments/npu/stage3/mt_predict.py` | `9bb90f39145e8af4` | `0a94406` 2026-09-29 |
| `experiments/npu/stage3/v11_dev.py` | `7f40894537e05521` | `ffd716f` 2026-10-01 |
| `experiments/npu/analysis/model_v0_retro.py` | `805abae195fbe4f4` | `a2d6f1f` 2026-09-29 |
| `plans/main/PREDICTIONS_SIM.json` | `6867e9efe8fbdc4c` (TASK93 기록과 같음) | |
| `plans/main/PREDICTIONS_CTX.json` | `06349354fa6d5f5c` | |
| `plans/main/INDEX_SIM.json` / `INDEX_CTX.json` | `395d034ddf319128` / `02cd4fb133e379f8` | |

재현:

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH taskset -c 64-95 nice -n 19 \
  python3 -u experiments/npu/analysis/dx_simple_approx.py --workers 8 --csv docs/research/dx/D_SIMPLE_APPROX.csv
```

## 1. 찾은 구현과 계수 (고정, 재적합 없음)

| 이름 | 구현 위치 | 규칙 | 계수 | 개발 데이터에서의 기존 비교 |
|---|---|---|---|---|
| **full** (전체 규칙) | `continuum.model.reference.FifoReplay.for_descriptor(RBLN_CA25_V2.with_config(...))` | 축출 = 가장 오래된 inactive 항목, 즉시 release, `pre_evict` dummy, 할당 후 조회 | capacity = batch(8 또는 16), 의미론 3종은 descriptor provenance(TASK72·63·15) | [TASK72](../TASK72.md) R5′ 1,298/1,298, [TASK73](../TASK73.md) |
| **A1_gap** (도구 대기 중 할당 수만 세는 근사) | `SubstrateDescriptor.survives_gap` ([TASK15](../TASK15.md) 법칙 후보, [TASK16](../TASK16.md) 코드) | `outer_slots(T) + B + outer_slots(R) ≤ outer_slot_count`, `B` = T의 `FREE-REQUEST`와 R의 `ALLOC` 사이 ALLOC 수 | `outer_slot_count` = batch(`config_search.descriptor_for`), `outer_slots_for(≤8,192 token)` = 1 | TASK14·15 순차 trial(9/9, 12/12). 동시 부하 개발 집합에서는 계산된 적 없음 → 이번에 같은 코드로 기준값 계산(§3.4) |
| **A2_cf** (lookup 시점 닫힌 형태) | `model_v0_retro.r5prime`의 등록 보조 계산, `survival.survives(C, Window(1, (1,)*A, K_pin))` | `A` = (T ALLOC, R ALLOC] 의 ALLOC 수, `K_pin` = 재생의 `pinned_older_at_lookup` | 위와 같음 | **개발 집합 1,298건 0.8328**([TASK72](../TASK72.md) R5′ "닫힌 형태 보조") |
| **A2w_cnt** (할당 창 개수만) | 같은 함수, `K_pin` 없음 — TASK72 실패 원인 분류의 "창 안 할당 수 초과" 판정 | `1 + A ≤ C` | 같음 | TASK72에서 원인 분류로만 사용 |
| **v0_poi** (Poisson 생존 근사) | `survival.survival_probability(..., law="poisson")` + `fifo_window_samples` | `P(Poisson((N−1)·W/cycle) ≤ C − 2)` | `W` = 체류 + gap, `cycle` = think 평균 + B2 응답시간 | **개발 집합 998건 Brier 0.1433**([TASK73](../TASK73.md) M06) |
| **v0_bin** | 같은 함수, `law="binomial"` | | | 개발 Brier 0.1629 |
| **v1_ss** (전체 해석 모형, 요청별) | `survival_v1.steady_state_survival`, 요청 자신의 gap을 idle 표본 1개로 | B2 점유 + `(f,a,d)` 흡수 연쇄 | `mt_predict.analytic` 고정점(λ, μ, 도착 분포) | 개발 Brier 0.1335(TASK73), 다회 turn 개발 집합 N=12(`v11_dev.py`, TASK85) |
| **v1_prereg** (선등록 cell 값) | `PREDICTIONS_SIM/CTX.json`의 `v1.reuse_rate` = `mt_predict.analytic` | cell 하나에 확률 하나 | 같음 | TASK95·102 판정표의 "v1 참고" |

두 근사와 전체 규칙이 서로 다른 튜닝 기회를 갖지 않도록: 1부는 같은 로그 사건 열·같은 client↔server join·같은 capacity를 세 규칙에 동시에 넣었고, 2부는 같은 cell 고정점(`cell_params`, `v11_dev.py`를 N 인자만 일반화해 복사)·같은 요청별 체류시간·같은 gap을 v1과 v0에 넣었다. 계수는 모두 코드에 이미 있던 값이다. 검증: A2_cf를 같은 경로로 개발 집합에 다시 돌려 **1,081/1,298 = 0.8328**(TASK72와 일치), `cell_params`의 `p_s`가 선등록 v1 값을 4 cell 모두 소수 넷째 자리까지 재현(0.8111, 0.8141, 0.7834, 0.7741).

`survives_gap`의 `B`는 "도구 대기 중"을 T의 `FREE-REQUEST`(응답 완료)부터 R의 `ALLOC` 직전까지로 읽었다. TASK15 순차 protocol에서는 이 구간이 곧 배경 요청 구간이므로 정의가 겹친다. 동시 부하에 대한 다른 해석(예: client `done_s`–`sent_s`)은 client–server 시계 정렬이 필요해 쓰지 않았다(KNOWN_PITFALLS 3: per-request 채널은 request id 로그).

## 2. 집합 선택

### 2.1 주 집합: 개발에 사용하지 않은 기존 검증 집합

| 집합 | 경로 | lifecycle | 왜 개발에 쓰이지 않았나 |
|---|---|---|---|
| [TASK95](../TASK95.md) simblind N = 13·17·20 | `results/npu/stage3/20261002-simblind` | 45 | 선등록 `cc29e76`(TASK93) 이후 측정(00:49:42). SIMBLIND_PREREG가 개발 집합을 N ≤ 16(TASK82·87)으로 선언하고 새 seed·새 N을 blind로 둠. 생존 규칙(full·A1·A2·v0·v1) 코드는 모두 측정 전에 동결(위 표). 이후 [TASK98](../TASK98.md)이 이 집합을 **시뮬레이터 비용 항** 사후 재예측에 썼으나(TASK101이 그 사실을 명시) 생존 규칙은 바꾸지 않았다 — 이 문서의 비교 대상과 무관한 사용이라 주 집합에 둔다 |
| [TASK102](../TASK102.md) ctxblind N = 15·18 | `results/npu/stage3/20261002-ctxblind` | 30 | 선등록 `cb1eec4`(TASK101) 이후 측정(18:02:44). 이후 사용은 TASK109–111의 사후 집계뿐이고 모형 변경 없음 |

### 2.2 참고 집합 (개발 집합, 합산하지 않음)

[TASK82](../TASK82.md)(N 6·8·10·12, BASE·BATCHONLY·TUNED, N=8 TUNED r5–r9 포함 65 lifecycle, DP arm 제외)와 [TASK87](../TASK87.md)(N 14·16, 30). 생존 규칙의 개발 집합은 아니지만 v1.1([TASK85](../TASK85.md), N=12)·시뮬레이터([TASK89](../TASK89.md)–[TASK92](../TASK92.md)) 개발에 쓰였다. 별도 표로만 보인다.

### 2.3 저부하 검증 집합 (2부)

[결정 10](../INDEX.md#결정-10--지시문-08-결정-해석-모형-범위-투고-일정)-1: 해석 모형 v1의 적용 범위 = N ≤ 동시 실행 상한. 주 집합에서 범위 안 cell은 **TASK95 BATCHONLY·TUNED N13, TASK102 BATCHONLY·TUNED N15**(batch 16) 4 cell × 5 rep = 20 lifecycle, 평가 창 요청 4,408건이다(선등록 파일의 `in_scope`와 같다). BASE N13·N15, N17·18·20은 범위 밖이라 2부에서 제외(1부에는 포함, 범위 안/밖 분리 표 §3.2).

## 3. 1부 — 요청별 사건 재현 (사후 기전 분석)

모집단: turn ≥ 1이고 자신과 직전 turn T가 모두 server id로 join되는 요청. 관측 = client `cached_tokens`(없으면 server `[CACHE-HIT]` IB_COUNT×128 / `[CACHE-PARTIAL]` REUSED, 둘 다 없으면 0 — 모든 server 로그에 `enable_prompt_tokens_details: True` 확인 방식은 mt_measure와 같음). client 값이 있고 server 조회와 hit 여부가 다르면 `UNKNOWN`, OB_COUNT ≠ 1이면 `UNDECIDABLE`. 단위: 요청. 범위: 전 run(warm-up 포함, "all")과 평가 창(`warmup_end_s ≤ sent_s < eval_end_s`) 두 가지.

### 3.1 hit/miss 일치 (주 집합)

| 범위 | 판정 가능 | UNDECIDABLE / UNKNOWN | 관측 hit | full = 관측 | A1_gap = full | A2_cf = full | A2w_cnt = full |
|---|---|---|---|---|---|---|---|
| TASK95 all | 13,892 | 0 / 0 | 7,652 | **13,892 (1.000)** | 10,507 (0.756) | 12,234 (0.881) | 12,432 (0.895) |
| TASK102 all | 8,720 | 0 / 0 | 4,918 | **8,720 (1.000)** | 6,400 (0.734) | 7,900 (0.906) | 7,987 (0.916) |
| **주 집합 all** | **22,612** | 0 / 0 | 12,570 | **22,612 (1.000)** | **16,907 (0.748)** | **20,134 (0.890)** | **20,419 (0.903)** |
| 주 집합 평가 창 | 16,434 | 0 / 0 | 9,346 | 16,434 (1.000) | 12,554 (0.764) | 14,864 (0.904) | 15,007 (0.913) |

full이 관측과 100 % 일치하므로 "근사 = full" 비율과 "근사 = 관측" 비율은 같다(CSV `*_vs_obs` 열).

### 3.2 범위 안/밖과 cell별 (주 집합, all)

| 부분집합 | 판정 가능 | A1_gap | A2_cf | A2w_cnt |
|---|---|---|---|---|
| N ≤ batch (in-scope 4 cell 유형) | 5,895 | 0.936 | 0.972 | 0.978 |
| N > batch (out-of-scope) | 16,717 | 0.681 | 0.862 | 0.877 |

| cell (5 rep 합) | 판정 | 관측 hit | A1_gap | A2_cf | A2w_cnt |
|---|---|---|---|---|---|
| TASK95 BASE N13 | 1,275 | 465 | 0.540 | 0.793 | 0.805 |
| TASK95 BASE N17 | 1,252 | 60 | 0.365 | 0.881 | 0.885 |
| TASK95 BASE N20 | 1,341 | 4 | 0.694 | 0.972 | 0.972 |
| TASK95 BATCHONLY N13 | 1,453 | 1,213 | 0.955 | 0.990 | 0.990 |
| TASK95 BATCHONLY N17 | 1,676 | 1,243 | 0.866 | 0.897 | 0.914 |
| TASK95 BATCHONLY N20 | 1,842 | 1,064 | 0.720 | 0.768 | 0.800 |
| TASK95 TUNED N13 | 1,471 | 1,226 | 0.955 | 0.990 | 0.990 |
| TASK95 TUNED N17 | 1,719 | 1,286 | 0.877 | 0.905 | 0.921 |
| TASK95 TUNED N20 | 1,863 | 1,091 | 0.726 | 0.776 | 0.810 |
| TASK102 BASE N15 | 1,143 | 115 | 0.307 | 0.812 | 0.821 |
| TASK102 BASE N18 | 1,234 | 26 | 0.379 | 0.912 | 0.912 |
| TASK102 BATCHONLY N15 | 1,470 | 1,162 | 0.913 | 0.950 | 0.964 |
| TASK102 BATCHONLY N18 | 1,670 | 1,200 | 0.844 | 0.892 | 0.903 |
| TASK102 TUNED N15 | 1,501 | 1,190 | 0.921 | 0.959 | 0.968 |
| TASK102 TUNED N18 | 1,702 | 1,225 | 0.850 | 0.894 | 0.908 |

full은 15 cell 모두 1.000.

### 3.3 혼동표와 실패 유형 (주 집합 all, 기준 = full)

| 근사 | 근사 hit·full hit | 근사 hit·full miss (과대 생존) | 근사 miss·full hit (과소 생존) | 둘 다 miss |
|---|---|---|---|---|
| A1_gap | 12,570 | **5,705** | **0** | 4,337 |
| A2_cf | 11,063 | 971 | 1,507 | 9,071 |
| A2w_cnt | 11,348 | 971 | 1,222 | 9,071 |

실패 유형 분류(`classify`, 위에서부터 첫 해당 항목; 모두 재생 부산물로 판정, 관측 결과 줄은 쓰지 않음):

| 유형 | 정의 | A1_gap | A2_cf | A2w_cnt |
|---|---|---|---|---|
| over: 할당 창 초과 | `1 + A > C` — T 자신의 체류(prefill·decode) 중 할당을 FIFO 창은 세고 gap 계수는 세지 않음 | **4,734** | — | — |
| over: 축출 순간의 older pinned | 창 개수는 맞는데 T가 admission 경로로 축출(더 오래된 항목이 active라 victim이 T로 내려옴) | 702 | 702 | 702 |
| over: dummy 선축출 | T가 `pre_evict` dummy 경로로 축출 | 269 | 269 | 269 |
| under: T active 중 보호 | 창 안 축출 중 T의 FREE 이전에 T보다 새 항목이 victim이 된 것이 있음(T active라 건너뜀) | 0 | 1,507 | 1,222 |
| under/over 기타 | 위 어디에도 해당 없음 / 다른 turn 항목으로 hit / 빈 slot | 0 | 0 | 0 |

- A1_gap은 **과소 생존 0건**이다. `1 + B + 1 > C`이면 A ≥ B + 1이라 할당 창도 넘치고, 그때 T가 살아남으려면 보호가 필요한데 보호는 T active 중에만 일어나며 그 축출은 B가 아니라 A 쪽에 들어간다 — 즉 A1은 할당 창의 하한만 세므로 한쪽으로만 틀린다(파생 해석, 산술).
- A2_cf의 `K_pin`(lookup 시점)은 over 오류를 하나도 줄이지 못하고 under만 285건 늘렸다(A2w_cnt 대비). TASK72 발견 4("`K_pin`은 축출 순간에 세야 한다")와 같은 방향이다.
- 범위 안 4 cell 유형: A1 over 377(할당 창 368, dummy 9), A2_cf under 155·over 9, A2w under 121·over 9. 범위 밖이 오류의 대부분이다(A1 5,328/5,705).

### 3.4 재사용 token 차이

예측 token = 예측 hit이면 `floor(min(T prompt, R prompt − 1)/128)·128`(`mt_predict.plan_stats`의 hit 식), 아니면 0. 관측 hit 12,570건 전부에서 이 식 = 관측 cached token(full 규칙의 token 차 0). 단위: token, 모집단 주 집합 all 22,612 요청.

| 규칙 | 예측 token 합 − 관측 (signed) | Σ\|차\| | Σ\|차\| / 관측 합 19,501,568 | 요청당 \|차\| |
|---|---|---|---|---|
| full | 0 | 0 | 0 | 0 |
| A1_gap | **+8,623,488** | 8,623,488 | **44.2 %** | 381.4 |
| A2_cf | −769,664 | 3,711,616 | 19.0 % | 164.1 |
| A2w_cnt | −357,760 | 3,299,712 | 16.9 % | 145.9 |

평가 창만: 관측 14,836,736, A1 +6,133,504(41.3 %), A2_cf Σ\|차\| 2,467,456(16.6 %), A2w 2,243,840(15.1 %). 범위 안 4 cell 유형: 관측 7,399,552, A1 +567,040(7.7 %), A2_cf 226,048(3.1 %), A2w 183,424(2.5 %).

### 3.5 참고: 개발 집합에서 같은 코드의 값

| 집합 | 판정 | full | A1_gap | A2_cf | A2w_cnt |
|---|---|---|---|---|---|
| TASK72 2-turn 7 run (개발 집합, 1,298) | 1,298 | 1.000 | 0.723 (939) | **0.833 (1,081, TASK72 재현)** | 0.854 (1,109) |
| TASK82 + TASK87 multi-turn (참고, all) | 21,207 | 1.000 | 0.859 | 0.946 | 0.951 |

참고 집합의 실패 유형 구성도 같다(A1: 할당 창 2,469·pinned 351·dummy 174, under 0; A2_cf: under 611·over 525). 순서(full > A2w_cnt > A2_cf > A1_gap)는 개발 집합 두 종류와 주 집합에서 같다.

## 4. 2부 — Poisson 생존 근사 대 해석 모형 (저부하 주 집합, 사후)

### 4.1 입력 정의

- cell 고정점: `cell_params(N, grid, batch, plan_stats(cell의 5 plan))` — `mt_predict.analytic`의 내부값(λ = X·(N−1)/N, μ, 도착 시 running 분포, t_run, φ, cycle = think 평균 + 응답시간). v0와 v1이 같은 값을 받는다.
- 요청별: `s_act = prefill_s(T prompt − T cached) + (T completion − 1)·t_run/φ`, gap = T의 계획 `gap_after_s`. `v11_dev.py`(TASK85)의 정의 그대로이며 **T의 관측 cached·completion token을 읽는다** — 그래서 2부도 blind 예측이 아니다.
- 모집단: 평가 창 안 turn ≥ 1 요청 4,408건(20 lifecycle).
- `v1_prereg`는 cell당 값 하나라 **Brier를 부여하지 않았다**(지시 2). A1/A2/full은 관측 사건을 쓰는 결정 규칙이라 2부 비교 대상이 아니다.

### 4.2 결과

| 방법 | 재사용 MAE (4 cell, rep 합산) | 재사용 MAE (20 lifecycle) | Brier (요청 4,408 합산) |
|---|---|---|---|
| v1_prereg (선등록 cell 값) | 0.0152 | 0.0191 | 부여 안 함 |
| v1_ss (요청별 v1) | 0.0278 | 0.0279 | 0.0312 |
| **v0_poi (Poisson)** | **0.0088** | **0.0122** | **0.0295** |
| v0_bin | 0.0106 | 0.0133 | 0.0354 |
| 참고: cell 내 관측률 상수 (oracle 기후값) | — | — | 0.1536 |

v1_prereg MAE는 TASK95·102 판정 JSON `v1_in_scope_reference.reuse_abs_err` 4개(0.0188, 0.0144, 0.0086, 0.0191)의 평균과 같다.

cell별 (관측 재사용 / 예측 재사용 / Brier):

| cell | n | 관측 | v1_prereg | v1_ss | v0_poi | v0_bin |
|---|---|---|---|---|---|---|
| TASK95 BATCHONLY N13 | 1,035 | 0.830 | 0.811 | 0.815 / 0.0210 | 0.824 / 0.0205 | 0.835 / 0.0243 |
| TASK95 TUNED N13 | 1,044 | 0.829 | 0.814 | 0.818 / 0.0211 | 0.825 / 0.0209 | 0.834 / 0.0267 |
| TASK102 BATCHONLY N15 | 1,149 | 0.792 | 0.783 | 0.757 / 0.0406 | 0.785 / 0.0385 | 0.811 / 0.0462 |
| TASK102 TUNED N15 | 1,180 | 0.793 | 0.774 | 0.744 / 0.0401 | 0.774 / 0.0363 | 0.806 / 0.0422 |

참고(개발 집합 TASK82 N6–12 + TASK87 N14·16 범위 안 14 cell, 12,694 요청): MAE v1_prereg 0.0109, v1_ss 0.0145, v0_poi 0.0069, v0_bin 0.0091; Brier v1_ss 0.0320, v0_poi 0.0314, v0_bin 0.0369.

### 4.3 해석 (관찰과 파생 해석 분리)

- 관찰: 이 4 cell에서 Poisson 근사(v0_poi)의 재사용 MAE와 Brier가 요청별 v1보다 작다. Brier 차는 0.0017(0.0295 대 0.0312)로 작고, 불확실성 구간은 계산하지 않았다(§6).
- 관찰: 요청별 v1(v1_ss)은 TASK102 N15에서 재사용을 0.035–0.050 과소 예측한다. 같은 모형의 선등록 cell 값(v1_prereg, gap 분포 40 bin 압축)은 0.009–0.019 과소다. 차이는 idle 표본을 요청 자신의 gap 하나로 바꾼 데서 온다(입력 정의 차, 모형 차 아님).
- 파생 해석: TASK73의 개발 집합(998건)에서는 순서가 반대였다(v1 0.1335 < v0_poi 0.1433). 이번 집합에서 v1의 상태 변수 `d`가 Poisson 계수 법칙보다 이득을 주지 않았다는 것은 "저부하 영역에서 v1 생존 오차가 할당 과정 가정(Poisson, λ 일정)에 지배된다"는 TASK73 hypothesis와 모순되지 않지만, 그것을 확인한 것도 아니다.

## 5. 핵심 요약

1. 전체 규칙(`FifoReplay`)은 개발에 쓰이지 않은 두 검증 집합의 22,612 재도착 전부를 hit/miss와 재사용 token까지 재현했다(UNDECIDABLE·UNKNOWN 0).
2. 도구 대기 중 할당 수만 세는 근사(`survives_gap`)는 0.748이고 오류 5,705건이 모두 과대 생존이다. 그중 4,734건은 FIFO-by-allocation 창이 T의 할당 시점부터 시작한다는 것(T 자신의 체류 중 할당) 때문이다. 재사용 token을 관측 대비 +44 % 과대 계상한다. 범위 안(N ≤ batch)에서는 0.936, +7.7 %.
3. 할당 창으로 센 닫힌 형태(A2_cf 0.890, A2w_cnt 0.903)는 dummy 선축출(269)·축출 순간의 pinned(702)·T active 보호(1,222–1,507)를 놓친다. TASK72 개발 집합 값 0.833과 순서가 같다.
4. 저부하 4 cell에서 Poisson 근사의 재사용 MAE 0.0088·Brier 0.0295, 요청별 v1 0.0278·0.0312, 선등록 v1 cell MAE 0.0152(Brier 없음). **사후 비교다.**

## 6. 한계와 하지 못한 것

- **사후성**: 1부는 관측 ALLOC/FREE/BUCKET 순서를 입력으로 쓴다. 2부 요청별 입력도 직전 turn 관측 token을 읽는다. 어느 것도 blind 예측 성적이 아니며 선등록 판정을 바꾸지 않는다.
- **불확실성 구간 없음**: Brier·MAE 차의 bootstrap CI를 계산하지 않았다(지시 범위 밖, 사전 등록한 폭 상한도 없음). 따라서 v0_poi 대 v1 순서를 "차이 있음"이나 동치로 판정하지 않는다.
- **A1의 "도구 대기" 경계**: server `FREE-REQUEST` → 재도착 `ALLOC`으로 정의했다. client 시각 기반 정의는 시계 정렬이 필요해 계산하지 않았다. 다른 경계를 택하면 A1 수치가 달라질 수 있으나, 할당 창 초과 4,734건은 어떤 gap-only 정의로도 셀 수 없는 T 체류 중 할당이라 결론의 방향은 같다(파생 해석).
- **유효 범위**: 2부는 N ≤ batch 4 cell(모두 batch 16)뿐이다. BASE(batch 8) 저부하 cell은 주 집합에 없다(TASK82 BASE N6·8은 개발 집합 참고값에만 있음).
- **TASK95의 다른 사용**: TASK98이 이 집합을 시뮬레이터 비용 항의 사후 재예측에 썼다. 이 문서가 비교하는 생존 규칙과 무관해 주 집합에 두었으나, "어떤 개발에도 전혀 쓰이지 않은 집합"을 엄격히 원하면 TASK102 단독 값(§3.1 행, §4.2 TASK102 두 cell)을 본다.
- **새 근사를 만들지 않았다**: gap-only 계수에 K_pin·dummy 항을 더한 변형 등은 설계하지 않았다(지시 3). 실패 유형 분류는 기존 재생의 부산물만 쓴 서술용 분류이며 규칙이 아니다.
- **TASK82 DP arm**은 `mt_predict.CONFIGS`에 없어 참고 집합에서도 제외했다.
- GPU 데이터는 다루지 않았다.
