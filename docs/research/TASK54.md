# TASK54 — 격자 개입의 동일 trace 재측정

## 상태

DONE

## 판정

선등록 문서: [GRID_PAIRED_PREREG.md](GRID_PAIRED_PREREG.md) (commit `fa53007`,
2026-09-08T13:36:22+09:00). **측정 시작 13:36:35 — 선등록 이후 13초.**

무효 밴드 `X = 0.004` (선등록, [TASK50](TASK50.md) 무처치 반복에서 유도).
`Δp = p_CONVENTIONAL − p_AGENTIC`, 3반복 합산(step 가중).

| # | 예측 | 결과 | 판정 |
|---|---|---|---|
| **P1** | N=6에서 `BASE` `Δp` > 0 **그리고** `MB6` `Δp` < 0 또는 `|Δp| ≤ X` | `BASE` **+0.0650**(양수), `MB6` **−0.0400**(음수) | **`PASS`** |
| **P2** | N=8에서 두 격자 모두 `Δp` < 0 | `BASE` **−0.0570**, `MB6` **−0.0554** | **`PASS`** |
| **P3** | `MB6` 격자 N=6 CONVENTIONAL의 bucket 8행 step = 0 | **0 step** (AGENTIC도 0) | **`PASS`** |

**3/3 적중이며 반복별 부호도 4셀 전부 3/3 일치**했다. 게이트 G1–G3·G5 전부 `PASS`,
24/24 칸 `VALID`(불변식 위반 0, 재실행 0), patch SHA256 측정 전후 무차이.

**이 TASK의 요점은 값이 아니라 통제다.** [TASK23](TASK23.md)의 개입 짝은 배치 사이
seed가 달라 `Δp` 이동에 격자 효과와 trace 차이가 섞여 있었다. 이번에는 **같은 (N,
반복) plan을 두 격자와 두 arm이 전부 재사용**했고 그 사실을 plan SHA256으로 검사했다
(G1, 12칸 전부 격자 간 해시 동일). **부호 역전의 소멸은 동일 trace에서 재현된다.**

## 날짜

2026-09-08

## 목적

[TASK23](TASK23.md) 2b의 격자 개입이 **trace 차이가 아니라 격자 때문**임을 같은
trace의 짝 비교로 확인한다. 논문에 자백으로 들어가 있는 seed 불일치 한계를 제거한다.

## 배경

관련 TASK:

- [TASK23](TASK23.md) — 원 개입. 2a(`BASE`, seed `20260841`)와 2b(`MB6`, seed
  `20260842`)가 다른 배치이고 N=6의 `BASE` 기준선은 [TASK20](TASK20.md)(seed
  `20260830`)에서 왔다
- [TASK52](TASK52.md) / [PADDING_RATIO.md](PADDING_RATIO.md) — `Δp` 정의와 계산 경로.
  "개입 짝은 plan seed가 다른 두 run이므로 격자 외 차이가 `Δp`에 얼마나 실렸는지
  분리되지 않는다"를 `확인되지 않은 사항`으로 기록했다
- [TASK50](TASK50.md) — 무처치 반복 20회. 무효 밴드 `X`의 자료
- [TASK20](TASK20.md) — `BASE` 격자 N=6 원 관측(pooled 1.1504)
- [TASK13](TASK13.md) — 사상표와 step 비용 모형

## 시작 상태

- 선등록 commit `fa53007`, 직전 `347e733`
- `git status --short`: `?? .idea/`만
- Substrate: `patched`, SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`
  — 측정 전후 덤프 무차이
- Model artifact 2종, **재compile 없음**. 파일별 SHA256 목록의 manifest hash:

| 격자 | 경로 | manifest sha256 |
|---|---|---|
| `(1,2,4,8)` `BASE` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb` | `b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f` |
| `(1,2,4,6,8)` `MB6` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb6` | `348f2863eb5f8ee6b12da4ec7b73e2e7bb5227cb610fa4e610310a7032cd24bf` |

- `models/` 증가 0 GiB, `/` 사용률 17 % (측정 전후 동일)

## 수행 내용

1. [TASK52](TASK52.md)의 `padding_ratio.py`, [TASK50](TASK50.md)의 `SWEEP_BLOCK_ID`,
   [TASK23](TASK23.md)의 `run_sweep.sh`를 그대로 재사용할 수 있음을 확인했다.
2. [TASK50](TASK50.md)의 저장 artifact 20칸에서 `p`를 산출해 **무처치 반복의 `p`
   재현 오차**를 구하고, 그것에서 무효 밴드 `X = 0.004`를 유도했다(측정 전).
3. artifact 2종의 파일별 SHA256과 manifest hash를 냈다(측정 전).
4. 선등록 문서·구동 script·판정 script를 **측정 전에 같은 commit**(`fa53007`)으로
   고정했다.
5. 8 구성 × 3 반복 = **24 lifecycle**을 반복마다 회전한 순서로 실행했다.
6. 칸마다 `utilization.py --cost-model`(격자에 맞는 `--buckets`)로 불변식을 검사하고,
   `grid_paired.py`로 게이트·`Δp`·히스토그램·판정을 산출했다.

## 변경된 파일

- `docs/research/GRID_PAIRED_PREREG.md` (선등록, 측정 전 commit)
- `experiments/npu/stage2/run_grid_paired.sh` (구동, 측정 전 commit)
- `experiments/npu/analysis/grid_paired.py` (판정, 측정 전 commit)
- `docs/research/TASK54.md` (신규)
- `docs/research/INDEX.md` (갱신)

[TASK23](TASK23.md)·[TASK52](TASK52.md) 문서와 그 수치는 **고치지 않았다.** 기존
script도 수정하지 않았다.

## 실험 또는 검증 방법

```bash
RUN=results/npu/stage2/20260908-133635-grid-paired
bash experiments/npu/stage2/run_grid_paired.sh "$RUN"        # 24 lifecycle
env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py \
    --run "$RUN" --output "$RUN/grid_paired.json"
```

구성 순서는 `balanced_arm_orders(8구성, rounds=3, base_seed=20260954,
block_id="task54-order")`의 반환값이며 선등록 문서의 표와 실제 `order.txt`가 일치한다.

`requested_condition` / `observed_condition` / `condition_reached`:

| 항목 | requested | observed | reached |
|---|---|---|---|
| 구성 수 | 8 | 8 | `YES` |
| 반복 | 3 | 3 | `YES` |
| serving lifecycle | 24 | **24** (재실행 0) | `YES` |
| 재compile | **0** | 0 | `YES` |
| 격자 간 plan 동일 | 12칸 | **12칸 해시 동일** | `YES` |
| 칸 유효성 | 24/24 `VALID` | **24/24** | `YES` |
| patch 상태 | 측정 전후 동일 | 동일 | `YES` |

## 결과

### 관측 1 — 게이트

| 게이트 | 내용 | 결과 |
|---|---|---|
| G1 | 같은 `(N, 반복, arm)`의 `meta["plan"]` SHA256이 두 격자에서 동일 | **12/12 동일** (예: N=6 r0 AGENTIC `10cbff85…`, CONVENTIONAL `ef5065b0…`) |
| G2 | CONVENTIONAL plan == AGENTIC plan의 gap 0화 (짝 동일성) | **12/12 `True`**. `total_gap_s`는 AGENTIC 19/24/23 s(N=6), 21/25/25 s(N=8)이고 CONVENTIONAL은 전부 0 |
| G3 | 세 반복이 서로 다른 trace | **전부 서로 다름** (반복이 블록으로 작동) |
| G5 | 24칸 완료 표식 | **누락 없음** |

**G1이 이 TASK의 핵심 관측이다.** 격자는 `generate_sessions`의 인자가 아니고
`--buckets`는 `return-policy=immediate`에서 읽히지 않으므로 trace에 닿지 않는다는
것이, 주장이 아니라 해시 대조로 확인됐다.

### 관측 2 — 반복별 `p`와 `Δp` (원시값)

| 격자 | N | 반복 | `p_A` | `p_C` | `Δp` | 부호 | `u_A/u_C` | step A/C |
|---|---|---|---|---|---|---|---|---|
| `BASE` | 6 | 0 | 0.1422 | 0.2367 | **+0.0946** | 양수 | 1.1239 | 759/413 |
| `BASE` | 6 | 1 | 0.1509 | 0.1888 | **+0.0379** | 양수 | 1.0467 | 577/468 |
| `BASE` | 6 | 2 | 0.1994 | 0.2592 | **+0.0598** | 양수 | 1.0808 | 665/407 |
| `BASE` | 8 | 0 | 0.1824 | 0.1230 | −0.0594 | 음수 | 0.9323 | 708/416 |
| `BASE` | 8 | 1 | 0.1256 | 0.0421 | −0.0835 | 음수 | 0.9128 | 725/425 |
| `BASE` | 8 | 2 | 0.1347 | 0.1087 | −0.0260 | 음수 | 0.9708 | 606/361 |
| `MB6` | 6 | 0 | 0.0786 | 0.0739 | **−0.0047** | 음수 | 0.9949 | 748/413 |
| `MB6` | 6 | 1 | 0.0805 | 0.0385 | **−0.0420** | 음수 | 0.9563 | 560/468 |
| `MB6` | 6 | 2 | 0.1251 | 0.0574 | **−0.0678** | 음수 | 0.9281 | 662/407 |
| `MB6` | 8 | 0 | 0.1035 | 0.0378 | −0.0657 | 음수 | 0.9317 | 744/416 |
| `MB6` | 8 | 1 | 0.1048 | 0.0321 | −0.0727 | 음수 | 0.9249 | 680/425 |
| `MB6` | 8 | 2 | 0.0841 | 0.0597 | −0.0245 | 음수 | 0.9740 | 579/361 |

`MB6` N=6 반복 0의 `Δp` = −0.0047은 밴드 `X` 밖이지만 그 폭이 좁다(밴드의 1.2배).

### 관측 3 — 3반복 합산과 [TASK23](TASK23.md) 병치

| 격자 | N | `p_A` | `p_C` | **`Δp`** | 부호 | 반복 부호 | `u_A/u_C` | TASK23 `Δp` | TASK23 비 |
|---|---|---|---|---|---|---|---|---|---|
| `BASE` | 6 | 0.1674 | 0.2324 | **+0.0650** | 양수 | 3/3 | 1.0846 | +0.1150 | 1.1504 |
| `BASE` | 8 | 0.1481 | 0.0911 | **−0.0570** | 음수 | 3/3 | 0.9373 | −0.0791 | 0.9132 |
| `MB6` | 6 | 0.0975 | 0.0574 | **−0.0400** | 음수 | 3/3 | 0.9575 | −0.0268 | 0.9717 |
| `MB6` | 8 | 0.0981 | 0.0427 | **−0.0554** | 음수 | 3/3 | 0.9422 | −0.0479 | 0.9508 |

**이동량** `shift(N) = Δp(BASE) − Δp(MB6)` (부수 산출, 판정 아님):

| N | 이번 (동일 trace) | [TASK23](TASK23.md) (다른 seed) |
|---|---|---|
| 6 | **+0.1050** | +0.1418 |
| 8 | **−0.0016** | −0.0312 |

### 관측 4 — bucket 8행 step 수 (`*→8`)

| 격자 | N | AGENTIC | CONVENTIONAL | A step 계 | C step 계 |
|---|---|---|---|---|---|
| `BASE` | 6 | 245 | **609** | 2,001 | 1,288 |
| `BASE` | 8 | 563 | 890 | 2,039 | 1,202 |
| `MB6` | 6 | **0** | **0** | 1,970 | 1,288 |
| `MB6` | 8 | 343 | 688 | 2,003 | 1,202 |

### 관측 5 — CONVENTIONAL의 step 수는 격자에 불변, AGENTIC은 아니다

같은 (N, 반복)에서 CONVENTIONAL의 decode step 총수가 **두 격자에서 정확히 같다**
(N=6 1,288 / N=8 1,202, 반복별로도 413·468·407 / 416·425·361로 일치). AGENTIC은
다르다(N=6 2,001 대 1,970, N=8 2,039 대 2,003).

### 관측 6 — 재사용률 (부수)

| 격자 | N | AGENTIC | CONVENTIONAL |
|---|---|---|---|
| `BASE` | 6 | 14/18 | 18/18 |
| `MB6` | 6 | 12/18 | 18/18 |
| `BASE` | 8 | 11/24 | 7/24 |
| `MB6` | 8 | 8/24 | 7/24 |

### 관측 7 — 보조 bootstrap CI (표본 3, 선등록 폭 상한 0.06)

| 격자 | N | 중앙 `u_A/u_C` | CI | 폭 | 판정 |
|---|---|---|---|---|---|
| `BASE` | 6 | 1.0808 | [1.0467, 1.1239] | 0.0772 | `DIFFERENT` |
| `BASE` | 8 | 0.9323 | [0.9128, 0.9708] | 0.0580 | `DIFFERENT` |
| `MB6` | 6 | 0.9563 | [0.9281, 0.9949] | 0.0668 | `DIFFERENT` |
| `MB6` | 8 | 0.9317 | [0.9249, 0.9740] | 0.0491 | `DIFFERENT` |

네 셀 모두 CI가 1을 포함하지 않는다. 표본이 3이라 폭 상한은 3셀에서 넘겼지만
`DIFFERENT` 판정은 폭 상한에 의존하지 않는다. **선등록대로 보조 정보로만 쓴다.**

## 핵심 발견

1. **`class`(형태) + `stack`(값) — 격자 정렬 법칙의 부호 역전 소멸이 동일 trace의
   짝 비교에서 재현됐다.** 같은 (N, 반복) plan을 두 격자가 재사용했고(plan SHA256
   12/12 동일) N=6의 `Δp`가 **+0.0650 → −0.0400**으로 부호를 바꿨으며 반복 3개
   전부 같은 방향이다. [TASK23](TASK23.md)이 seed 차이와 섞어 관측한 것을 이번에는
   **격자 하나만 바꿔** 얻었다. *형태*가 `class`인 근거는 [TASK23](TASK23.md) 발견
   1과 같다 — 기전이 "고정된 이산 batch 크기 집합에 실제 batch를 올림한다"는 설계
   범주에서 나온다. 값(+0.065, −0.040, 격자 `(1,2,4,8)`)은 `stack`이다.

2. **`universal` — `Δp` 이동량의 *크기*는 trace에 실린다.** N=6 이동량이 이번에
   **+0.1050**, [TASK23](TASK23.md)에서 **+0.1418**이다. 부호와 기전은 trace를
   통제해도 살아남지만 크기는 27 % 줄었다. [TASK52](TASK52.md)가 `UNKNOWN`으로 남긴
   "격자 외 차이가 `Δp`에 얼마나 실렸는가"의 답이 **N=6에서 약 0.037(이동량의 26 %)
   까지**라는 뜻이다 — 다만 이것은 두 run의 차이이지 trace 분산의 추정치가 아니다.

3. **`stack` — N=8에서 격자 변경은 절대 padding을 크게 줄이면서 `Δp`는 거의 바꾸지
   않는다.** `p_A` 0.1481 → 0.0981, `p_C` 0.0911 → 0.0427로 양 arm 모두 내려가지만
   `Δp`는 −0.0570 → −0.0554로 이동량이 **−0.0016**, 선등록 밴드 `X = 0.004` 안이다.
   [TASK23](TASK23.md) 발견 4가 "N=8도 격자에 닿는다"를 보고했는데, **닿는 것은 두
   arm의 절대값이고 짝 차이는 닿지 않는다**는 것이 동일 trace에서 분리됐다.
   [TASK23](TASK23.md)의 N=8 이동량 −0.0312는 그 대부분이 seed 차이였다고 읽힌다.

4. **`stack` — 격자에 bucket 6이 있으면 N=6에서 bucket 8행이 두 arm 모두 0이 된다.**
   `BASE`에서 CONVENTIONAL 609 step(전체의 47 %)·AGENTIC 245 step이던 `*→8`이
   `MB6`에서 **정확히 0**이다. [TASK52](TASK52.md)가 [TASK23](TASK23.md) 자료에서
   본 것과 같은 현상이 신규 trace에서 재현됐다.

5. **`stack` — CONVENTIONAL의 decode step 총수는 격자에 완전히 불변이고 AGENTIC은
   아니다.** gap이 없으면 도착이 결정적이라 batch 구성이 격자와 무관하게 같은 열을
   만든다. gap이 있으면 step 시간이 bucket에 따라 달라지고(f(bucket),
   [TASK13](TASK13.md)) 그것이 다음 도착과의 겹침을 바꿔 step 열 자체가 달라진다.
   **격자는 AGENTIC에서만 실행 궤적을 되먹임으로 바꾼다.**

6. **`universal` — 무처치 반복은 판정 밴드의 자료가 된다.** [TASK50](TASK50.md)이
   다른 목적으로 남긴 20칸에서 `p`의 실행 간 재현 오차(최대 쌍 차 0.00281)를 얻어
   `X = 0.004`를 유도했다. 관례값을 쓰지 않고 밴드를 자료에서 정할 수 있었다.

## 해석

- **(해석)** [TASK23](TASK23.md)의 인과 주장은 **강화된다.** 그 TASK의 개입은 seed가
  섞여 있었는데, trace를 완전히 통제하고 격자만 바꿔도 N=6의 부호가 뒤집힌다. 논문의
  해당 한계 문장은 이제 "동일 trace 짝 비교에서 재현됨"으로 대체할 수 있다.
- **(해석)** 동시에 **크기 모형이 없다는 [TASK23](TASK23.md) 발견 3은 그대로다.**
  같은 격자·같은 N에서도 반복에 따라 `Δp`가 +0.038~+0.095로 2.5배 흔들린다. 부호는
  격자가, 크기는 trace가 정한다.
- **(해석)** 발견 3은 설계 함의가 있다. `batch_size`나 격자를 바꿔 **절대 padding을
  줄이는 것**과 **agentic/conventional 사이의 상대 이득을 바꾸는 것**은 다른 일이다.
  N=8처럼 정상 상태가 이미 격자 위에 있으면 전자만 일어난다.
- **(해석)** 발견 5는 관측 설계에 쓸 수 있다. CONVENTIONAL arm의 step 열이 격자에
  불변이므로, 두 격자의 CONVENTIONAL 자료는 **같은 요청 열에 다른 가격표를 붙인 것**
  으로 읽어도 된다. AGENTIC은 그렇지 않으므로 같은 취급을 하면 안 된다.

## 확인되지 않은 사항

- **반복 3회는 `Δp`의 분포를 말하기에 적다** (`UNKNOWN`). 보조 bootstrap CI는 표본
  3에서 폭 상한을 3셀에서 넘겼다. 크기의 신뢰구간이 필요하면 반복을 늘려야 한다.
- **두 artifact는 `decoder_batch_6.rbln` 외에 `prefill.rbln`의 바이트도 다르다**
  (`402a117d…` 대 `84389a32…`). 개입은 "decoder 격자만 바꾼 바이트 수준 교체"가
  아니라 재compile된 artifact로의 교체다. prefill 경로의 차이가 `Δp`에 기여했는지는
  이 설계로 **분리되지 않는다**. 두 artifact의 prefill 크기는 같고
  ([TASK23](TASK23.md) 관측 6) 두 arm이 같은 prefill을 쓰므로 짝 차이에서는 상쇄될
  것으로 보이나, **확인하지 않았다**.
- **`X = 0.004`의 population 차이** — [TASK50](TASK50.md)의 null은 gap 법칙이
  `toolmix`이고 arm이 하나다. 이번 `Δp`는 `uniform:1:5` gap의 두 arm 차이다. `X`는
  보수적 방향이지만 정확히 같은 population은 아니다.
- **`p`는 step 가중이지 시간 가중이 아니다** ([TASK52](TASK52.md)와 동일).
- N ∈ {6, 8} 밖의 N, 그리고 다른 격자에서의 재현 (`UNKNOWN`, 이번 범위 밖).
- 발견 5의 기전(격자 → step 시간 → 도착 겹침 → step 열)은 **해석이며 직접 측정하지
  않았다.**

## 실패 / 무효 시도

없다. 24칸 전부 1회에 `VALID`였고 재실행·server 기동 실패·device 누수가 없었다.
측정 전후 `rbln-smi`에서 32 device 전부 `0.0B`이고 잔여 context가 없다.

**예산 표기 불일치 1건을 기록한다.** Advisor 지시문의 「승인 범위」는 "serving
기동·종료(예상 12회 내외)"라 적었고 「설계」 4항은 "총 lifecycle 24회"라 적었다.
8구성 × 3반복 = 24가 산술적으로 확정된 수이므로 24회로 집행했고, 이 불일치를
선등록 문서에 **측정 전에** 기록한 뒤 완료 보고에 명시한다.

## 연구 원칙에 미치는 영향

1. **짝 비교의 "짝"은 arm 사이에만이 아니라 처치 사이에도 필요하다.** 두 처치를
   비교할 때 각 처치 안에서만 trace를 공유하면 처치 간 비교에 trace 차이가 실린다.
   처치를 가로질러 trace를 공유시키고 **그 사실을 해시로 검사**한다.
2. **밴드는 자료에서 만든다.** 무처치 반복이 이미 있으면 그것으로 판정 밴드를
   유도하고 유도 과정을 선등록에 적는다([TASK49](TASK49.md)가 지적한 관례값 문제).
3. **"절대값이 움직였다"와 "짝 차이가 움직였다"를 분리해 보고한다**(발견 3).

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **논문 3.1절의 seed 한계 문장 갱신** — [TASK52](TASK52.md)의 `UNKNOWN`과 논문의
   자백을 이 TASK의 동일 trace 결과로 대체할지 판단한다. 문서 작업이며 측정 불필요.
2. **`Δp` 크기의 신뢰구간** — 반복을 3 → 6 이상으로 늘려 크기를 구간으로 말한다.
   재compile 불필요, lifecycle 24회 추가.
3. **prefill 바이트 차이의 절제** — 같은 `decoder_batch_sizes`로 두 번 compile해
   prefill 재현성을 확인한다. 재compile 승인이 필요하다.
4. **발견 5의 직접 검증** — AGENTIC에서 격자가 step 열을 바꾸는 경로를 시뮬레이터
   ([TASK24](TASK24.md))로 재현한다. 측정 불필요.

## 재현 정보

- 선등록 commit: **`fa53007`**, 2026-09-08T13:36:22+09:00.
  **측정 시작 2026-09-08T13:36:35+09:00 — 선등록 이후**
- 측정 종료: 2026-09-08T14:09:43+09:00 (33분 08초, 24 lifecycle)
- Raw artifact: `results/npu/stage2/20260908-133635-grid-paired/`
  (7.5 MiB, `results/`는 `.gitignore` 대상)
  - `order.txt`(실제 실행 순서), `measurement-start.txt`/`measurement-end.txt`
  - `patch-before.txt`/`patch-after.txt`(무차이), `rbln-smi-before.txt`/`-after.txt`,
    `disk-after.txt`, `driver.out`
  - `mb/`·`mb6/` 각각: `util.<ARM>.n<N>.b<REP>.json`, `server-*.log`, `metrics-*.prom`,
    `probe/requests.*.jsonl`, `probe/meta.*.json`, `done.*`
  - 판정 산출: `grid_paired.json`
- 실행: `bash experiments/npu/stage2/run_grid_paired.sh <RUN>`
- 판정: `env -u PYTHONPATH python3 experiments/npu/analysis/grid_paired.py --run <RUN> --output <RUN>/grid_paired.json`
- plan seed `20260954`, `block_id` `task54-n<N>-r<rep>`, sampling seed `20260819`,
  gap `uniform:1:5`, `--turns 2 --first-segment uniform:800:1600 --later-segment fixed:8
  --generation uniform:32:256`, return policy `immediate`
- Model artifact: 위 「시작 상태」의 manifest sha256 2종 (gitignored)
- Package: `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`, `optimum-rbln 0.11.1`
- Substrate: `patched`, SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`
- 예산 사용: serving lifecycle **24/24**, 재compile **0**, `models/` 증가 **0 GiB**,
  `/` 사용률 17 %, device 접근은 serving 24회뿐
- 측정 후 device 상태: 32 ID 전부 `0.0B / 15.7GiB`, 잔여 context 없음, 누수 server 없음
