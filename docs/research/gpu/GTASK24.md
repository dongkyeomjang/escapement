# GTASK24 — 포화 구간 비용 비의 독립 시간 검증, N = 28·25 (G-10 작업 B)

## 상태

PARTIAL — 선등록 판정은 `NA`(DIRECT 판정 셀 0). 원인은 겹침 검사의 허용치가 float32 시각 간격보다 작았던 것이다. 보정 규칙 아래 사후 진단은 모든 기준을 통과했지만 선등록 판정을 대신하지 않는다.

## 날짜

2026-10-08

## 목적

GPU 지시문 G-10 §4. 포화 구간의 비용 비 R = 비용(GPU_KV) / 비용(GPU_BASE)을 세 채널로 비교한다.
- PRED_lo/hi: 동결 시뮬레이터
- RECON_lo/hi: 관측 step에 원고 가격을 매긴 값
- DIRECT_EXEC: [GTASK23](GTASK23.md)의 device event 구간

원고 비용 비가 원고 가격 함수와 독립인 시간으로도 성립하는지 확인한다.

## 배경

- [GTASK20](GTASK20.md): 문맥 인지 예측기 (1) ctx가 N25·28에서 RECON 비 기준을 통과했다. 그러나 RECON과 PRED가 같은 가격 함수를 쓰므로 독립 검증이 아니었다.
- [GTASK23](GTASK23.md): DIRECT 계측의 영향은 |중앙| ≤ 0.12 %로 `OK`였다.
- 선등록 [G10_B_PREREG.md](G10_B_PREREG.md)

## 시작 상태

- HEAD `0812f85`(A→B→C 연결 driver), branch `gpu-a6000`. site-packages: 관측 patch + exec 층.

## 수행 내용

1. plan 20개(N28·N25 × r0–9, seed `20264100 + 10k + r`)와 동결 예측 `PREDICTIONS_B.json`, 순서, driver, 판정 script를 측정 전에 commit했다(`8bfeee8`).
2. `run_chain.sh`가 A `overall = OK`를 확인한 뒤 B를 시작했다(13:46:25 UTC). 본 측정 40 lifecycle은 모두 유효였고 preemption은 0이었다.
3. **본 측정 40개 모두 DIRECT 겹침 검사(> 0.01 ms)에 걸렸다.** 선등록 규칙대로 40개 모두 한 번씩 다시 쟀다(`.retry1`, 16:15–18:43). 재측정 40개도 모두 같은 검사에 걸렸다.
4. `judge_b.py` 1회(18:44:01) 결과 판정 셀 0, `required`·`all_B` 모두 `NA`였다. driver가 `b_result/verdict.json`을 자동 commit했다(`935d9d6`).
5. 사후 진단(선등록 아님): 겹침이 float32 시각 양자화임을 확인하고, 보정 허용치로 판정을 다시 계산했다(`posthoc_f32.py`, `0b2fa48`). 관측 사건 재현도 했다(`replay_c.py`를 B에 적용).

## 변경된 파일

- 선등록 commit `8bfeee8`: `docs/research/gpu/G10_B_PREREG.md`, `experiments/gpu/g10/{predict_b.py, make_b_order.py, run_b.sh, judge_b.py, g10_common.py}`, `plans_b/*`
- 연결 driver `0812f85`: `experiments/gpu/g10/run_chain.sh`
- 자동 commit `935d9d6`: `experiments/gpu/g10/b_result/verdict.json`
- 사후 진단 `0b2fa48`: `experiments/gpu/g10/posthoc_f32.py`, `b_result/posthoc_f32.json`
- 사후 진단 산출물 `fc10373`: `experiments/gpu/g10/{replay_c.py, b_result/posthoc_replay.json}`
- 기록 commit: `docs/research/gpu/GTASK24.md`, `GPU_INDEX.md`, `GPU_RESULTS_SUMMARY.md`

## 실험 또는 검증 방법

- 구성: GPU_BASE(1,900 block) / GPU_KV(2,300 block), 격자 (1,2,4,8,16), `max_num_seqs` 8, budget 2,048. runner `--stream --exec-timing`, 120 s 평가창, lifecycle마다 서버 재기동.
- Population: N28·N25 × 2 구성 × 10 replicate = 40 lifecycle(+ 재측정 40). 창 요청 268–374개/lifecycle.
- Unit: 호출당 비용 비의 replicate별 R, 그 중앙값. bootstrap 95 % CI(10,000, seed 20264150), 정확 sign test.
- Source: `[GSTEP]`·`[GPFX]`·`[GEXEC]` 로그, client `cached_tokens`
- Device: A6000 `4485e769…`

```bash
R=<abs>/results/gpu/g10/b/chain_20261008T1232Z
experiments/gpu/g10/run_chain.sh <A dir> $R <C dir>    # A OK → run_b.sh $R → run_c.sh
env -u PYTHONPATH <venv>/python experiments/gpu/g10/posthoc_f32.py --judge b --run-dir $R --out <json>
```

## 결과

### 선등록 판정 (`b_result/verdict.json`)

| 항목 | N28 (필수) | N25 (확장) |
|---|---|---|
| 유효 lifecycle | 20/20, 재측정 20/20 | 20/20, 재측정 20/20 |
| preemption | 0 | 0 |
| `[GEXEC]` 누락 (window) | 0 | 0 |
| 겹침 > 0.01 ms가 있는 lifecycle | 40/40 | 40/40 |
| 판정 replicate | 0 | 0 |
| 1 재구성·2 예측·3 skill·4 감소 | **`NA`** | **`NA`** |

DIRECT가 필요 없는 값(유효 replicate 10개 전부, 보고용):

| N | R_RECON lo / hi | R_PRED lo / hi (10개) |
|---|---|---|
| 28 | 0.8819 / 0.8779 | 0.8866 / 0.8795 |
| 25 | 0.8590 / 0.8545 | 0.8698 / 0.8672 |

### 사후 진단 1: 겹침의 원인

- `[GEXEC]`의 `s`는 process 기준 event에서 잰 `cudaEventElapsedTime`(float32, ms)이다. s ≥ 2¹⁷ ms = 131,072 ms부터 float32 간격은 0.015625 ms로, 허용치 0.01 ms보다 크다.
- 80개 lifecycle 모두에서 첫 겹침은 s ≥ 131,095 ms에서 나왔다. 그 앞에서는 겹침이 0이었다.
- 겹침 최대 폭은 0.0146 ms로 한 양자 이하다. 겹침은 lifecycle당 18–91건이다.
- 허용치를 0.01 ms + float32 간격(s)으로 바꾸면 **80/80 겹침 0**이다. 판정 script의 원래 겹침 수와 재계산 결과는 80/80 일치했다.
- prep·run은 가까운 event 사이의 짧은 구간이라 이 양자화와 관계없다.
- 이 실패는 A 점검 run이 60 s 창, 약 75 s 길이라 2¹⁷ ms에 닿지 않아서 드러나지 않았다.

### 사후 진단 2: 보정 규칙으로 다시 계산한 판정 (`b_result/posthoc_f32.json`, 선등록 판정 아님)

| 항목 | N28 | N25 |
|---|---|---|
| 판정 replicate | 10 (본 측정 전부) | 10 |
| median R_DIRECT | **0.8957** | **0.8751** |
| median R_DIRECT prep / run | 0.990 / 0.8956 | 0.990 / 0.8750 |
| median R_RECON lo / hi | 0.8819 / 0.8779 | 0.8590 / 0.8545 |
| median R_PRED lo / hi | 0.8866 / 0.8795 | 0.8698 / 0.8672 |
| 1 RECON − DIRECT (≤ 0.03) | −0.014 / −0.018 PASS | −0.016 / −0.021 PASS |
| 2 PRED − DIRECT (≤ 0.03, lo·hi 둘 다) | −0.009 / −0.016 PASS | −0.005 / −0.008 PASS |
| 4 감소 CI | [0.856, 0.929] `CONFIRMED` | [0.836, 0.947] `CONFIRMED` |
| sign test | 10/0, p = 0.002 | 10/0, p = 0.002 |

- 3 skill(`required` = N28): lo Σ오차 0.0091, hi 0.0162, 기준선 0.104 → 둘 다 PASS.
- 3 skill(`all_B`): lo 0.0144, hi 0.0241, 기준선 0.229 → 둘 다 PASS.

replicate별 R (DIRECT, RECON lo, PRED lo):

| N | r0 | r1 | r2 | r3 | r4 | r5 | r6 | r7 | r8 | r9 |
|---|---|---|---|---|---|---|---|---|---|---|
| 28 DIRECT | 0.898 | 0.893 | 0.959 | 0.832 | 0.917 | 0.937 | 0.879 | 0.856 | 0.853 | 0.929 |
| 28 RECON lo | 0.887 | 0.877 | 0.952 | 0.815 | 0.908 | 0.933 | 0.863 | 0.844 | 0.839 | 0.922 |
| 28 PRED lo | 0.902 | 0.871 | 0.928 | 0.834 | 0.903 | 0.957 | 0.844 | 0.860 | 0.839 | 0.927 |
| 25 DIRECT | 0.961 | 0.815 | 0.881 | 0.907 | 0.947 | 0.857 | 0.976 | 0.869 | 0.787 | 0.851 |
| 25 RECON lo | 0.956 | 0.796 | 0.869 | 0.896 | 0.942 | 0.844 | 0.974 | 0.849 | 0.766 | 0.835 |
| 25 PRED lo | 0.963 | 0.824 | 0.876 | 0.895 | 0.950 | 0.853 | 0.985 | 0.863 | 0.795 | 0.852 |

### 절대 호출당 시간 (유효 replicate 중앙, s)

| N / 구성 | RECON lo | RECON hi | DIRECT | DIRECT prep | PRED lo | PRED hi |
|---|---|---|---|---|---|---|
| 28 BASE | 0.3496 | 0.3549 | 0.4149 | 0.0004 | 0.3426 | 0.3524 |
| 28 KV | 0.3035 | 0.3065 | 0.3652 | 0.0004 | 0.2987 | 0.3010 |
| 25 BASE | 0.3303 | 0.3352 | 0.3928 | 0.0004 | 0.3288 | 0.3369 |
| 25 KV | 0.2776 | 0.2794 | 0.3361 | 0.0004 | 0.2782 | 0.2803 |

step 종류별 (10 replicate 합, ms/step: DIRECT 대 가격 lo). 순수 prefill step은 0개였고 prefill은 모두 decode와 함께 든 mixed step이었다.

| N / 구성 | decode step | decode DIRECT / 가격 | mixed step | mixed DIRECT / 가격 lo |
|---|---|---|---|---|
| 28 BASE | 49,534 | 16.58 / 13.62 | 3,413 | 109.7 / 97.1 |
| 28 KV | 55,767 | 16.58 / 13.62 | 3,490 | 77.7 / 66.9 |
| 25 BASE | 52,746 | 16.53 / 13.62 | 3,468 | 93.8 / 82.3 |
| 25 KV | 59,580 | 16.53 / 13.62 | 3,592 | 57.9 / 48.5 |

### 재사용·대기 (보고, 판정 아님)

| cell | 요청 재사용 관측 / 예측 lo / hi | token 재사용 관측 / 예측 lo | h TVD lo | 대기 관측 proxy / 예측 lo (s) |
|---|---|---|---|---|
| N28 BASE | 0.215 / 0.243 / 0.236 | 0.188 / 0.215 | 0.050 | 4.60 / 4.26 |
| N28 KV | 0.608 / 0.628 / 0.633 | 0.569 / 0.592 | 0.047 | 3.77 / 3.48 |
| N25 BASE | 0.425 / 0.466 / 0.457 | 0.385 / 0.422 | 0.052 | 3.38 / 3.08 |
| N25 KV | 0.788 / 0.799 / 0.796 | 0.764 / 0.773 | 0.051 | 2.57 / 2.38 |

- 관측 대기 proxy는 첫 ALLOC wall − client 송신 wall이며 HTTP 지연을 포함한다.

### 사후 진단 3: 사건 재현 (`b_result/posthoc_replay.json`)

- GTASK12 replay(무수정)를 본 측정 40 lifecycle에 적용했다. 창 안 turn ≥ 1 요청 **11,194/11,194 일치**, 결정 불가 0, free 수 분기 0, KV 축출 순서 1,202,315/1,202,315 일치.
- 재사용 과대 예측(+0.01 – +0.04)은 block 규칙 오류가 아니다. 사건 생성(도착·대기·시간 입력) 쪽 오차다. GTASK20의 계통 편향(+0.005 – +0.049)과 같은 방향이다.

### 경계 보정 (Appendix G 규칙, 모든 채널 같은 규칙, 보조)

| N | R lo raw → 보정 | R hi | R DIRECT | R PRED lo | R PRED hi |
|---|---|---|---|---|---|
| 28 | 0.8819 → 0.8772 | 0.8779 → 0.8730 | 0.8957 → 0.8898 | 0.8866 → 0.8797 | 0.8795 → 0.8756 |
| 25 | 0.8590 → 0.8590 | 0.8545 → 0.8546 | 0.8751 → 0.8742 | 0.8698 → 0.8769 | 0.8672 → 0.8650 |

보정으로 각 채널이 0.007 이하로 움직였고 기준 통과 여부는 바뀌지 않는다.

### 사전 예측 대조

| 예측 | 결과 |
|---|---|
| 2 예측 일치 FAIL 쪽, DIRECT 비 0.90–0.92, 차 0.02–0.04 | 빗나감(사후): DIRECT 0.896 / 0.875, 차 0.005–0.016 |
| 1 재구성 문턱 근처 0.01–0.04 | 적중(사후): 0.014–0.021 |
| 3 skill PASS | 적중(사후) |
| 4 감소 두 N `CONFIRMED` | 적중(사후) |
| DIRECT가 RECON보다 15–25 % 큼 | 적중: 18.7–21.1 % |
| 선등록 판정이 계산 가능 | **빗나감: 겹침 검사 결함으로 `NA`** |

## 핵심 발견

1. 선등록 판정은 `NA`다. 원인은 실행이 아니라 판정 규칙의 결함이다(겹침 허용 0.01 ms < float32 간격 0.0156 ms, s ≥ 2¹⁷ ms에서). 재측정으로는 고칠 수 없는 계통 결함이라 재측정 40회는 모두 같은 결과였다.
2. 보정 규칙(사후)에서는 DIRECT 비가 RECON 비보다 1에 가깝다(0.014–0.021). 하지만 PRED는 DIRECT와 0.016 안에서 맞고, 비용 감소는 두 N 모두 CI 상한 < 1로 확인된다.
3. DIRECT 절대값은 RECON lo보다 18.7–21.1 % 크다. 대부분은 decode step이 가격(13.62 ms)보다 21.4–21.7 % 큰 데서 온다(16.5–16.6 ms, context 비용). mixed step 초과는 12.9–19.4 %다.
4. 재사용 과대 예측은 사건 재현이 완전히 맞으므로 사건 생성·시간 입력 쪽이다.

## 해석

- 사후 진단에 따르면, 원고 비용 비(가격 기반)는 실제 device 실행 시간 비보다 1에서 0.01–0.02 더 멀다. context 비용이 두 구성에 공통으로 더해지기 때문이다(G-08 결정 1의 원인 후보와 같은 방향). 같은 의미에서 "KV pool 확대가 호출당 비용을 줄인다"는 결론은 독립 시간 채널에서도 유지된다. 다만 이것은 사후 진단이며 판정 근거로 쓰려면 Advisor 결정이 필요하다.

## 확인되지 않은 사항

- 보정 규칙(0.01 ms + float32 간격)은 측정 후 만든 것이다. 선등록 규칙의 대체로 인정할지는 Advisor 결정 사항이다.
- HW_ACTIVE `NA`. mixed step의 prefill·decode 몫은 분리하지 않았다.
- 대기 proxy는 HTTP 지연을 포함한다.

## 실패 / 무효 시도

- INVALID lifecycle 0. preemption 0.
- DIRECT 계측 결함 판정 80/80(본 측정과 재측정 모두). 재측정은 이 결함을 고치지 못했다(같은 길이의 run이므로).
- 사후 진단 script의 첫 실행에서 내 재계산 겹침 수가 판정 script와 2–5건 달랐다(비교식 `pe − s > 0.01` 대 `s < pe − 0.01`의 부동소수점 경계). 이 차이 때문에 대부분 lifecycle이 load 오류로 빠졌다. 판정 script와 같은 비교식으로 바꾸고 일치 여부를 기록하도록 고쳐 다시 실행했다(80/80 일치). 첫 실행 출력은 덮어썼다.

## 연구 원칙에 미치는 영향

- 측정 후 판정 기준을 완화하지 않았다. 선등록 결과(`NA`)를 그대로 두고 보정 결과는 사후 진단으로 따로 표시했다(CLAUDE.md 원칙 16).
- 새 규칙: 장시간 run의 device 시각은 float32 분해능(2¹⁷ ms 이후 15.6 µs)을 허용치에 넣거나, 기준 event를 주기적으로 다시 잡아 s를 작게 유지해야 한다. 짧은 점검 run으로 긴 run의 검사를 검증하지 않는다.

## 다음 작업

- Advisor 결정: 사후 보정 판정을 B의 DIRECT 결과로 쓸지, 아니면 새 seed와 고친 계측(기준 event 재설정 또는 float64 host 누적)으로 다시 선등록해 측정할지.

## 재현 정보

- **선등록 commit `8bfeee8df5f65b68737c24a55797bddaf15dde28`(2026-10-08 12:30:30 UTC) → 측정 시작 13:46:25 UTC**(driver `start_commit.txt` = `0812f85`, 연결 driver만 추가). 측정 종료·판정 18:44:01, 자동 commit `935d9d6`.
- 사후 진단 commit `0b2fa48`(18:49:01, 판정 뒤)
- 예측 `plans_b/PREDICTIONS_B.json` SHA256 `0d1abec1…`, 순서 `plans_b/ORDER_B.json` `ff87ee69…`(seed 20264160)
- run dir(비추적): `results/gpu/g10/b/chain_20261008T1232Z/`(`sequence.log`, `retry_list.txt`, lifecycle 80개, `verdict.json`, `judge.stdout`). 사후 진단 원본: `results/gpu/g10/b/posthoc/`
- 환경: [GTASK23](GTASK23.md)와 같다(exec 층 적용).
