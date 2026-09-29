# multi-turn steady-state 실험 설계 초안 (선등록 아님)

작성: 2026-09-29, [TASK75](TASK75.md) (Advisor 지시문 03 작업 D). **예측과 판정 기준은 이 문서에 쓰지 않는다.** Advisor 검토 후 별도 선등록에서 확정한다. 측정·compile은 하지 않았다.

**목적**: 모형 v1([MODEL_V1.md](MODEL_V1.md))과 시뮬레이터의 **blind 예측**을 선등록하고 검증할 steady-state 부하를 만든다. 원고 workload(세션당 2요청·동시 시작)는 steady state가 아니어서 B2·v1의 가정이 깨졌다([TASK72](TASK72.md) R4·R5, [TASK73](TASK73.md) A4).

---

## 1. steady state 확보 — 세션 갱신(renewal)

- **N을 일정하게 유지한다.** 세션 하나는 K turn을 보낸 뒤 끝나고, 끝나는 즉시 **새 세션**(새 초기 prompt, 새 seed)이 같은 자리에서 시작한다. 활성 세션 수는 늘 N이다.
- **시작 시각을 엇갈린다.** 세션 i의 첫 turn은 `i · Δ`에 보낸다. `Δ = c_pred / N`(c_pred = B2가 예측한 turn 주기). 또 세션별 초기 turn 번호를 `0..K−1`에서 고르게 흩어(첫 세션들을 "중간 turn부터" 시작시키는 대신, 첫 세대 세션의 K를 `1..K`에서 고르게 뽑아) 세대 교체가 동기화되지 않게 한다.
- **warm-up 제외**([TASK72](TASK72.md) R4 제안): `max(3·c_pred, 모든 활성 자리에서 2 turn 이상 완료된 시각)` 이전은 평가에서 뺀다. 원고 조건의 모형 주기가 4.5–7.9 s였으므로 대략 15–25 s다.
- **drain 제외**: 새 세션 발행을 멈춘 시각(= 평가 구간 끝) 이후의 모든 step·요청은 평가에서 뺀다. 발행을 멈춘 뒤 남은 요청은 끝까지 돌리되(서버 상태 정리) 집계하지 않는다.
- **평가 구간 길이**: 주기 10개 이상 — `T_eval ≥ 10 · c_pred`. c_pred ≈ 6–8 s면 **T_eval = 120 s**를 제안한다(15–20 주기).
- **정상성 점검(판정 전 게이트 후보)**: 평가 구간 전반·후반의 step 가중 running 분포 TVD, 재사용률 차.

## 2. context 길이 상한

turn t의 prompt = 초기 prompt + Σ_{i<t}(segment_i + 생성_i) + segment_t. 마지막 요청의 prompt + 생성이 `max_seq_len` 8,192 이하여야 한다:

```
init + K·(seg + gen) ≤ 8,192         (최악: 각 항 최댓값)
```

| 설계 | init | 이후 segment | 생성 | K 상한(최악) | K=8일 때 최대 context | 평균 context(K=8) |
|---|---|---|---|---|---|---|
| **A. 원고 분포 유지** | U(800,1600) | 8 (원고 `LATER`) | U(32,256) | **24** | 1600 + 8·264 = 3,712 | 1200 + 8·152 ≈ 2,416 |
| B. tool 출력 크기 segment | U(800,1600) | U(64,512) | U(32,256) | **8** | 1600 + 8·768 = 7,744 | 1200 + 8·432 ≈ 4,656 |
| C. 초기 prompt 축소 | U(256,512) | U(64,256) | U(32,128) | **20** | 512 + 8·384 = 3,584 | 384 + 8·240 ≈ 2,304 |
| D. 짧은 세션 + renewal | U(800,1600) | 8 | U(32,256) | 제한 없음(K=3) | 1600 + 3·264 = 2,392 | ≈ 1,656 |

**관찰**: 원고처럼 이후 segment가 8 token이면 상한이 느슨하다(최악 24 turn). **상한이 구속하는 것은 tool 출력을 segment로 넣을 때다**(설계 B, 8 turn). TraceLab에는 tool 지연만 있고 **출력 token 수가 없다**([TASK48](TASK48.md): 원 아카이브 접근 불가, 분위수만) — 설계 B의 segment 분포는 근거 없는 가정이 된다.

**함께 볼 비용**: context가 길수록 재사용 실패의 prefill 비용이 커진다 — `T̂_prefill(3,700) ≈ 29 × (0.0212 + 0.0024) ≈ 0.68 s`, 원고 규모(≈1,200 token)의 약 3배. 결과가 원고보다 재사용에 민감해진다. 또 layer 1(inner LRU)의 용량은 `batch_size × 8,192` token이라 설계 B에서는 layer 1 축출이 생길 수 있다(원고 조건에서는 한 번도 구속하지 않았다).

**권고: 설계 A, K = 8.** 원고 분포를 그대로 유지해 기존 결과와 비교 가능하고, 최대 context 3,712로 상한과 layer 1 모두에서 여유가 크다. 세대 교체는 renewal이 맡으므로 K를 크게 할 이유가 없다. 설계 B는 결정 사항 D1로 올린다.

## 3. tool gap

- turn마다 TraceLab `toolmix`에서 **새로 뽑는다**(현재 `foresight`와 같은 sampler, `summary.json` SHA256 `25bb1b0f…`).
- 상한 60 s의 영향: 상한 60 s에서 평균 4.23 s, 중앙값 0.16 s, 70.5 %가 1 s 미만, **2.5 %가 상한에 걸린다**. 상한이 없으면 평균 6.99 s, 최대 961 s(표본 200,000, seed 1).
- **권고: 60 s 유지.** 원고와 비교 가능하고, 상한이 없으면 한 세션이 수백 초 비어 N이 사실상 줄어 steady state가 흔들린다. 상한 효과는 v1·B2가 입력 분포로 받으므로 예측에서 일관되게 다룰 수 있다.

## 4. 격자

| 축 | 제안 | 비고 |
|---|---|---|
| N | 6, 8, 10 (+ 12 선택) | 원고와 같음. 12는 BASE(`max_num_seqs` 8)에서 대기열이 생겨 B2 가정(n ≤ M)이 깨지는 구간 — 모형의 한계를 재는 용도 |
| 구성 | BASE `(1,2,4,8)`/b8, BATCHONLY `(1,2,4,8,16)`/b16, TUNED `(1,4,6,8,10,16)`/b16 | **기존 artifact로 가능**(`models/`에 존재) |
| N별 격자 | DP 최적 격자(예: [TASK72](TASK72.md) R3의 N=6 `(1,2,4,5,6,16)`, N=8 `(1,3,5,6,8,16)` — multi-turn h로 다시 계산) | **새 compile 필요**(구성당 ≈ 42 + 61·7 ≈ 470 s, ≈ 13 GiB). 원고 수정 후보 M2의 직접 검증 |
| replicate | **5** (원고 3) | 독립 plan 5개. 같은 plan을 구성 간 공유(짝 설계, [TASK19](TASK19.md) 원칙: 한 plan에서 파생). 5회면 부트스트랩 CI(원칙 17)와 run 간 분산 추정이 가능 |
| run 길이 | warm-up ≈ 25 s + 평가 120 s + drain | 발행 시간 ≈ 145 s, drain 포함 ≈ 170 s |
| 순서 | 블록 안에서 구성 순서 무작위 | 시간 추세와 구성 효과의 교락 방지 |

## 5. 지표

| 지표 | 정의 | 원천 |
|---|---|---|
| device time 채널 A′ | `[BUCKET]` × step 비용 + 계산 token × prefill 모형 | server 로그([TASK35](TASK35.md) 정의 그대로) |
| device time 채널 B | 요청 in-flight 구간의 합집합(client `sent_s`–`done_s`, tool gap 제외; `config_device.channel_b`) | client. **주의**: steady state에서 N개 세션이 늘 돌면 합집합이 평가 구간 전체에 가까워져 구성 간 변별력이 떨어진다 — 평가 구간 안에서 처리량으로 정규화한 "turn당 B"를 병기할 것을 제안 |
| 세션 완료 시간 | 한 세션의 첫 turn 발행 → 마지막 turn 완료 | client |
| turn ≥ 1 요청의 TTFT | 발행 → 첫 token | client, **streaming 필요** |
| 처리량 | 평가 구간 안에서 완료된 turn 수 / 구간 길이 | client |
| 재사용 | `cached_tokens > 0`, server `[CACHE-HIT]` 교차 | client + server |
| 사건 재생 입력 | `[PFX] ALLOC/FREE-REQUEST`, `[BUCKET]` | server — v1·재생의 blind 대조용 |
| prefill 간섭 W | 원고 식 (6) `∫K_j(t)dt` — 다른 세션의 token 흐름에서 prefill 구간의 정지를 직접 잰다 | client token timestamp, **streaming 필요** |

**streaming 결정**: 원고 III-D의 slot 개입은 non-streaming이라 W를 재지 못했다. streaming이면 token 시각에서 정지를 직접 볼 수 있다. 다만 streaming은 host 쪽 작업을 늘려 device time을 바꿀 수 있다(관찰자 효과). **제안: 본 측정 전 짝 파일럿**(N=8, BASE·TUNED, 3 replicate, streaming 대 non-streaming)으로 채널 A′ 비의 동치를 원칙 17(부트스트랩 CI가 1을 포함하고 폭이 상한 이내)로 확인하고, 동치면 streaming으로 본 측정. 동치가 아니면 non-streaming 본 측정 + streaming 보조 run. (결정 D3)

## 6. runner

새 runner(`experiments/npu/stage3/multiturn_runner.py`, 이 초안에서는 작성하지 않음) 요구사항:

1. `prompt_tokens_details`가 없으면 `cached_tokens = null`(KNOWN_PITFALLS 6).
2. run 디렉터리에 **runner commit hash**(`git rev-parse HEAD`와 `git status --porcelain`), server 인자 전체, patch 상태, 모델 `rbln_config.json` hash를 남긴다([TASK72](TASK72.md)의 `PARTIAL` 해소).
3. 세션 갱신·엇갈린 시작·세대별 seed를 plan 파일로 미리 생성해 저장하고, 구성 간 같은 plan을 쓴다.
4. streaming이면 요청별 token timestamp를 저장한다(압축 jsonl).
5. KNOWN_PITFALLS 1·2·5: 절대 경로, 자기 PID로 종료, 실행 중 script 편집 금지.

## 7. 예산

기존 run의 lifecycle(서버 기동 + run + 종료): final-confirm 27회 51분(≈ 113 s/회), null-channel 20회 35분(≈ 106 s/회). run 자체가 20–40 s였으므로 **고정 오버헤드 ≈ 80–90 s/회**로 본다.

| 묶음 | lifecycle 수 | 회당 | device 시간 |
|---|---|---|---|
| streaming 파일럿 (N8 × 2 구성 × 3 rep × 2 모드) | 12 | ≈ 255 s | ≈ 0.9 h |
| 본 측정 (3 N × 3 구성 × 5 rep) | 45 | ≈ 255 s (170 + 85) | ≈ 3.2 h |
| N=12 추가 (3 구성 × 5 rep) | 15 | ≈ 255 s | ≈ 1.1 h |
| N별 DP 격자 (compile 2회 + 2 구성 × 5 rep) | 10 + compile | ≈ 255 s + 2 × 8 분 | ≈ 1.0 h |
| **합** | **82** | | **≈ 6.2 h** (재시도 여유 ×1.5 → ≈ 9 h) |

**10월 말까지 가능**: 하루 한 묶음씩이면 4일, 여유를 두어도 1–2주 안에 끝난다. 병목은 device 시간이 아니라 **선등록 → 검토 → 측정 → 분석**의 절차 시간이다. compile 2회는 승인 대상이다(원칙 11).

## 8. 결정이 필요한 선택지

> **확정 (Advisor 지시문 04, 2026-09-29, [TASK76](TASK76.md))**: D1 (a) 원고 8 token — (b)는 본 실험에서 제외하고 GPU 단계에서 재검토 / D2 K = 8 / D3 파일럿 후 결정 / D4 포함하되 **격자는 측정 h가 아니라 모형 예측 h로 선정**(blind) / D5 N = 12 포함(모형 적용 범위 경계 cell, 탐색) / D6 60 s / D7 5회.

| # | 질문 | 선택지 | 권고 |
|---|---|---|---|
| D1 | 이후 turn segment 크기 | (a) 원고 8 token (b) tool 출력 크기 U(64,512) — 근거 자료 없음 | **(a)**. (b)는 근거 없는 분포를 도입한다 |
| D2 | 세션당 turn 수 K | 3 / 8 / 16 | **8** (context 최대 3,712, 세대 교체는 renewal) |
| D3 | streaming | 파일럿 후 결정 / 처음부터 streaming / non-streaming | **파일럿 후 결정** |
| D4 | N별 DP 격자 포함(새 compile 2회) | 포함 / 제외 | **포함** — 원고 수정 후보 M2의 직접 검증 |
| D5 | N=12 포함 | 포함 / 제외 | 포함 (모형 한계 구간) |
| D6 | gap 상한 | 60 s / 없음 | **60 s** |
| D7 | replicate | 5 / 8 | 5 (예산 여유가 크면 8) |

## 9. 선등록 때 정할 것 (이 초안에서는 쓰지 않음)

v1·시뮬레이터·B2의 예측 대상(재사용률, step 가중 h, device time 비, W), 판정 기준, 동치 CI 상한, 정상성 게이트, INVALID 조건.
