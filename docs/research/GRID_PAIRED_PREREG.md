# 선등록 — 격자 개입의 동일 trace 재측정

이 문서는 측정 **시작 전에** commit한다. 아래의 실험 격자, 산출 정의, 판정 기준,
예측, 무효 규칙은 측정 후에 바꾸지 않는다. 결과를 보고 완화하지 않으며, 완화가
불가피하면 원 기준의 실패를 함께 보고한다.

## 목적

[TASK23](TASK23.md)의 격자 개입은 배치 **안에서는** 두 arm이 trace를 공유했으나
배치 **사이에서는** seed가 달랐다 — 2a·[TASK20](TASK20.md)이 `20260841`/`20260830`
계열, 2b가 `20260842`다. 그래서 개입 전후의 `Δp` 이동(**+0.1150 → −0.0268**,
[PADDING_RATIO.md](PADDING_RATIO.md) §1 개입 짝)에는 **격자 효과와 trace 차이가
섞여 있다.** [TASK52](TASK52.md)가 그 한계를 `확인되지 않은 사항`으로 명시했고
논문에도 자백으로 들어가 있다.

이 TASK는 **같은 trace로 두 격자를 직접 짝지어** 그 한계를 제거한다.

**이 TASK는 [TASK23](TASK23.md)의 판정과 수치를 재산출하지도 수정하지도 않는다.**
새 측정의 결과를 그 옆에 병치할 뿐이다.

## 승인 범위 (Advisor 지시문, 사용자 전달)

승인: serving 기동·종료, 기존 관측 스택, `experiments/npu/` script 추가,
`docs/research/` 문서 작성.
금지: **compile, patch 변경, [TASK23](TASK23.md) 판정·수치의 수정.**

**예산 표기의 불일치를 측정 전에 기록해 둔다.** 지시문 「승인 범위」는
"serving 기동·종료(예상 12회 내외)"라 적었고 「설계」 4항은 "총 lifecycle 24회"라
적었다. 설계의 8구성 × 3반복 = 24가 산술적으로 확정된 수이므로 **24회로 집행**하고,
이 불일치를 완료 보고에 명시한다. 24회를 넘기지 않는다(재실행분 제외, 아래 무효 규칙).

## Substrate 상태 (측정 전 확인)

`bash patches/vllm_rbln-0.11.1/apply.sh status`가 `patched`
(SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`)가
아니면 시작하지 않는다. 측정 전후로 덤프해 무차이를 확인한다.

## Model artifact (재compile 없음)

기존 2종만 쓴다. **파일별 SHA256을 `<상대경로> <sha256>` 목록으로 만들고 그 목록의
SHA256을 manifest hash로 기록**한다(측정 전 산출).

| 격자 | 경로 | manifest sha256 |
|---|---|---|
| `(1,2,4,8)` = `BASE` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb` | `b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f` |
| `(1,2,4,6,8)` = `MB6` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb6` | `348f2863eb5f8ee6b12da4ec7b73e2e7bb5227cb610fa4e610310a7032cd24bf` |

두 artifact는 `decoder_batch_6.rbln`의 유무 외에 **`prefill.rbln`의 바이트도 다르다**
(`402a117d…` 대 `84389a32…`, 크기는 [TASK23](TASK23.md) 관측 6에서 동일). 개입은
"decoder 격자만 바꾼 바이트 수준 교체"가 아니라 **"bucket을 하나 더 넣어 다시
compile한 artifact로의 교체"** 다. 이 사실을 측정 전에 기록해 둔다.

## 실험 격자

| 항목 | 값 |
|---|---|
| 구성 | 격자 2 × N ∈ {6, 8} × arm ∈ {AGENTIC, CONVENTIONAL} = **8 구성** |
| 반복 | **3회** (`r0`, `r1`, `r2`). 반복마다 fresh server |
| 총 serving lifecycle | **24회** |
| plan seed | **`20260954`** (기존 사용 seed 전부와 겹치지 않음: 20260819·21·22·23·30·31·40·41·42·50·60, 20260910, 20261100·1200·1300·1400) |
| `block_id` (고정) | `task54-n<N>-r<rep>` |
| sampling seed | `20260819` (기존과 동일) |
| turns / 세그먼트 / 생성 | `--turns 2`, `--first-segment uniform:800:1600`, `--later-segment fixed:8`, `--generation uniform:32:256` ([TASK20](TASK20.md)·[TASK23](TASK23.md)과 동일) |
| gap | `uniform:1:5` (합성 gap. [TASK23](TASK23.md)과 동일 — 병치 대상이 그 run이므로 [TASK31](TASK31.md)의 toolmix를 쓰지 않는다) |
| CONVENTIONAL의 정의 | 같은 plan의 `zero_gaps()` 파생 (`--zero-gaps`) |
| return policy | `immediate`, budget 0 |
| server 옵션 | `--enable-prefix-caching --enable-prompt-tokens-details` |

### trace 공유가 이 TASK의 요점

`generate_sessions`는 `(base_seed, block_id)`에서 `derive_block_seed`로 세션 계획을
만든다. **격자는 그 경로에 들어가지 않는다.** `--buckets`는 return policy가
`immediate`일 때 아무 것도 읽지 않고 `meta`에 기록만 된다.

`SWEEP_BLOCK_ID`로 `block_id`를 `task54-n<N>-r<rep>`에 고정하면 **같은 (N, 반복)의
plan이 격자 2종과 arm 2종 전부에서 같아진다.** 이것을 주장이 아니라 **검사**로
확인한다(아래 G1·G2).

반복마다 plan은 달라진다(`r0`/`r1`/`r2`가 서로 다른 trace). 이것이 블록 역할을 한다.
N=6과 N=8은 세션 수가 다르므로 필연적으로 다른 trace이며, **N 사이의 비교는 하지
않는다** — 비교는 언제나 같은 (N, 반복) 안에서 격자끼리 한다.

### 실행 순서 (측정 전 고정)

`balanced_arm_orders(configs, rounds=3, base_seed=20260954, block_id="task54-order")`
의 반환값을 그대로 쓴다. `configs`는
`["mb.n6.AGENTIC","mb.n6.CONVENTIONAL","mb.n8.AGENTIC","mb.n8.CONVENTIONAL","mb6.n6.AGENTIC","mb6.n6.CONVENTIONAL","mb6.n8.AGENTIC","mb6.n8.CONVENTIONAL"]`
순서로 만든다. 산출된 순서(순환 회전 3개):

```
r0: mb6.n8.A  mb.n8.C   mb6.n6.A  mb.n8.A   mb.n6.A   mb.n6.C   mb6.n6.C  mb6.n8.C
r1: mb6.n6.C  mb6.n8.C  mb6.n8.A  mb.n8.C   mb6.n6.A  mb.n8.A   mb.n6.A   mb.n6.C
r2: mb6.n8.C  mb6.n8.A  mb.n8.C   mb6.n6.A  mb.n8.A   mb.n6.A   mb.n6.C   mb6.n6.C
```

## 산출 정의

[TASK52](TASK52.md)와 **같은 계산 경로**를 쓴다 —
[`padding_ratio.py`](../../experiments/npu/analysis/padding_ratio.py)의 `arm_totals`를
그대로 import한다.

- `p = Σ(b_t − n_t) / Σ b_t` — 한 셀의 `[BUCKET]` step 열에서 합산. 무차원 slot 점유
  비율이며 **시간 몫이 아니다**
- **`Δp = p_CONVENTIONAL − p_AGENTIC`** (양수 = CONVENTIONAL이 더 많이 pad)
- `u = Σn/Σb = 1 − p`, arm 비 `u_A/u_C`는 [TASK23](TASK23.md) 병치용으로만 병기
- **이동량** `shift(N) = Δp(BASE, N) − Δp(MB6, N)`
- bucket 8행 step 수 = `pair_histogram`에서 `*→8` 항의 합

반복별(`r0`,`r1`,`r2`) 값과 3반복 합산(pooled, step 가중) 값을 **모두** 낸다.
판정은 pooled로 하고 반복별 부호 일치(3/3 여부)를 함께 보고한다.

## 무효 밴드 `X` — 자료 기반 (측정 전 산출)

`Δp`가 "0과 구별되지 않는다"를 판정하려면 **처치 없이 같은 trace를 반복했을 때 `p`가
얼마나 흔들리는가**가 필요하다. [TASK50](TASK50.md)의 무처치 반복 20회(같은 trace,
같은 구성, 매회 fresh server)의 저장 artifact에서 `p`를 산출했다.

| N | `p` 범위 | `p` 표준편차 | 45쌍 `|p_i − p_j|` 중앙값 | 95분위(nearest rank) | 최댓값 |
|---|---|---|---|---|---|
| 6 | 0.2324 – 0.2333 | 0.00038 | 0.00030 | 0.00091 | 0.00091 |
| 8 | 0.1423 – 0.1451 | 0.00091 | 0.00056 | 0.00281 | 0.00281 |

`Δp`는 **서로 다른 두 실행의 `p` 차이**이므로 null 폭은 한 실행 쌍의 `√2`배로 본다.

```
X = ceil( √2 × max(|p_i − p_j|) × 1000 ) / 1000
  = ceil( 1.41421 × 0.00281 × 1000 ) / 1000
  = ceil( 3.97 ) / 1000
  = 0.004
```

**`X = 0.004`로 고정한다.** 부호 판정은 세 갈래다.

| 조건 | 판정 |
|---|---|
| `Δp > +X` | **양수** (CONVENTIONAL이 더 pad — AGENTIC 유리) |
| `Δp < −X` | **음수** (AGENTIC이 더 pad) |
| `|Δp| ≤ X` | **null** (0과 구별되지 않음) |

`X`의 한계를 미리 적어 둔다. [TASK50](TASK50.md)의 null은 (i) gap 법칙이
`toolmix`이고 (ii) arm이 하나이며 (iii) 같은 trace의 반복이다. 이번 `Δp`는 같은
trace에서 arm만 다른 두 실행의 차이이므로 **정확히 같은 population이 아니다.**
그래도 `X`는 관측된 실행 간 재현 오차의 상한에서 나온 값이며 **완화가 아니라 하한
쪽으로 보수적**이다(0.004는 [TASK23](TASK23.md) 개입 짝의 `Δp` 크기 0.027–0.115보다
한 자릿수 작다).

## 예측 = 판정 기준 (측정 전 고정)

| # | 예측 | 판정 방법 |
|---|---|---|
| **P1** | **N=6**: `BASE` 격자의 `Δp` > 0 **그리고** `MB6` 격자의 `Δp` < 0 또는 `|Δp| ≤ X` | pooled `Δp`에 위 3갈래 규칙 적용. `BASE`가 **양수** 그리고 `MB6`가 **음수 또는 null**이면 `PASS` |
| **P2** | **N=8**: 두 격자 모두 `Δp` < 0 (방향 유지) | 두 pooled `Δp`가 모두 **음수**이면 `PASS` |
| **P3** | `MB6` 격자 **N=6 CONVENTIONAL**의 bucket 8행 step 수 = **0** | 정확히 0이면 `PASS`. 하나라도 있으면 `FAIL` |

P3의 범위를 명시한다. `MB6` 격자에서 **N=8**은 정상 상태 동시성이 8이라 bucket 8이
당연히 쓰인다. 따라서 P3은 **N=6 CONVENTIONAL 한 칸**의 예측이다. N=6 AGENTIC과
N=8 두 arm의 bucket 8행 수는 **판정 없이 보고만** 한다.

### 부수 산출 (판정 아님)

- `shift(6) = Δp(BASE,6) − Δp(MB6,6)`를 [TASK23](TASK23.md) 짝의 `0.1150 − (−0.0268)
  = 0.1418`과 병치한다. **다른 seed·다른 run의 값이므로 일치·불일치에 판정을 걸지
  않는다.**
- `u_A/u_C`를 [TASK23](TASK23.md) 표와 병치한다.
- 반복별 `Δp` 3개의 부호 일치 수(3/3, 2/3, …).
- `p` 자체의 절대값, step 수, 재사용률, `(actual→bucket)` 히스토그램 전문.

### 보조 검정 — 중앙 ratio의 bootstrap CI (연구 원칙 17)

`u_A/u_C`의 반복 3개를 표본으로
[`bootstrap_ratio.py`](../../experiments/npu/analysis/bootstrap_ratio.py)의
`median_ratio_ci`를 그대로 써서 CI를 낸다(resamples 2000, base seed `20260954`).
**CI 폭 상한은 0.06으로 사전 등록한다** — [TASK23](TASK23.md) 2b의 블록별 ratio
산포(N=6에서 0.9488–1.0029, 폭 0.0541)를 올림한 값이다.

- CI가 1을 포함하고 폭 ≤ 0.06 → `EQUIVALENT`
- CI가 1을 포함하지 않음 → `DIFFERENT`
- CI가 1을 포함하나 폭 > 0.06 → `INCONCLUSIVE`

**표본이 3이므로 이 검정은 보조이며 P1–P3의 판정을 대체하지 않는다.** 반복 3회에서
`EQUIVALENT`가 나오지 않는 것은 예상 범위이고, 그것을 P1–P3의 실패로 읽지 않는다.

## 게이트와 무효 규칙 (fail-loud)

| # | 검사 | 위반 시 |
|---|---|---|
| **G1** | 같은 `(N, 반복, arm)`의 `meta["plan"]` SHA256이 **두 격자에서 동일** | **TASK 전체 `INVALID`.** 이 TASK의 전제가 깨진 것이다 |
| **G2** | 같은 `(N, 반복)`에서 CONVENTIONAL의 plan == AGENTIC plan의 `gap_after_s`를 0으로 둔 것 (P1 짝 동일성) | 해당 칸 `INVALID` |
| **G3** | 같은 `(N, arm, 격자)`의 세 반복 plan이 **서로 다름** (반복이 블록으로 작동) | 보고만 한다. 같으면 설계 오류이므로 `INVALID` |
| **I1–I5** | [`utilization.py`](../../experiments/npu/analysis/utilization.py)의 불변식. `MB6`는 `--buckets 1,2,4,6,8` | 해당 칸 **같은 선등록 칸을 1회 재실행**([TASK23](TASK23.md) 원칙 3). 재실행도 실패하면 그 칸 `INVALID` |
| **G4** | 측정 전후 patch SHA256 동일 | TASK `INVALID` |
| **G5** | 24칸 전부 `done` 표식 존재 | 미완칸을 `UNKNOWN`으로 보고 |

`p` 산출은 **`VALID`인 칸만** 쓴다. 관측 불가 field를 0으로 채우지 않는다.

## 필수 기록 항목

칸별: `server-*.log`(BUCKET·PFX 전문), `probe/requests.*.jsonl`, `probe/meta.*.json`,
`metrics-*.prom`, `util.*.json`. 전체: patch status 전후, `rbln-smi` 전후, artifact
manifest sha256, 측정 시작·종료 시각, 선등록 commit hash, 실행 순서 실제 기록,
disk 사용량.

## 관련 문서

- [TASK23](TASK23.md) — 원 개입. 병치 대상
- [TASK52](TASK52.md) / [PADDING_RATIO.md](PADDING_RATIO.md) — `Δp` 정의와 계산 경로
- [TASK50](TASK50.md) / [NULL_CHANNEL_PREREG.md](NULL_CHANNEL_PREREG.md) — 무처치 반복, `X`의 자료
- [TASK20](TASK20.md) — `BASE` 격자 N=6 원 관측
- [TASK13](TASK13.md) — 사상표와 step 비용 모형
