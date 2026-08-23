# 선등록 — 워크로드 통계 기반 compile 구성 정책의 실기기 검증

## 문서 성격

[CLAUDE.md](../../CLAUDE.md) 실행 원칙 16과 [TASK_GUIDE.md](TASK_GUIDE.md)가 요구하는 **선등록(preregistration)** 이다. 이 문서를 담은 commit 이후에 compile과 측정을 시작한다. **측정 후 판정 기준을 완화하지 않는다.**

## 왜 compile-time인가

[TASK33](TASK33.md)이 사전 정의된 분기에 따라 **compile-time이 유일한 회수 경로**임을 확정했다. 현실 워크로드 headroom의 중앙 60 %가 *조율*의 몫이고 per-session runtime 정책은 원리적으로 거기 닿을 수 없는데, **compile 구성은 조율을 설계 시점에 모두에게 한 번에 굳히는 방법**이다.

## 승인 범위 (사용자 판정, 2026-08-23)

serving 기동·종료(약 30회), 기존 관측 스택, `src/continuum/` 코드, **재compile 최대 3회**(구성 1–2개 + 진단 1회, 회당 30분·`models/` 80 GiB 상한).

범위 밖: download, patch 변경, RSD 변경, legacy 수정, GPU 서버 작업, remote push 자동 수행.

## 구성 공간과 탐색

**축**: `decoder_batch_sizes`(bucket 격자)와 `batch_size`. `max_seq_len = 8192`·`num_devices = 4`는 고정한다. `batch_size`는 [TASK08](TASK08.md)에 따라 `kvcache_num_blocks`와 같으므로 **outer slot 수이자 `max_num_seqs`**다.

**제약**: bucket은 1과 `batch_size`를 반드시 포함하고 최대 6개. compile 예상 시간은 [TASK10](TASK10.md) 모형([TASK23](TASK23.md)에서 3번째 점으로 확인)으로 `42.3 + 61.33 × (bucket 수 + 1)` s, artifact는 `8.276 + 0.806 × bucket 수` GiB로 표기하고 1800 s 예산 안의 후보만 남긴다.

**탐색**: 후보 **2,077개**를 현실 워크로드 N ∈ {6, 8, 10} × 3블록으로 평가. **탐색 seed `20260910/20260921/20260932`에서 고르고 평가 seed `20260943/20260954/20260965`에서 채점**했다([TASK27](TASK27.md)·[TASK33](TASK33.md)의 선택 편향 교훈).

**선정**: `decoder_batch_sizes = (1, 4, 6, 8, 10, 16)`, `batch_size = 16`. 평가 seed ratio **0.9066**(절감 9.34 %).

### 이득의 축별 귀속 (평가 seed)

| 구성 | buckets | batch | 평가 ratio | 절감 |
|---|---|---|---|---|
| 기본 (현행) | (1,2,4,8) | 8 | 1.0000 | — |
| **batch만** | (1,2,4,8,16) | 16 | 0.9279 | **+7.21 %** |
| **bucket만** | (1,4,6,8) | 8 | 0.9929 | +0.71 % |
| **선정** | (1,4,6,8,10,16) | 16 | **0.9066** | **+9.34 %** |

**`batch_size`가 지배 인자이고 bucket 정제가 그 위에 2.1 %p를 더한다.**

### 실행 가능성 점검

Qwen3-4B는 36 layer · KV head 8 · head_dim 128이므로 token당 KV가 144 KiB다. `batch_size = 16`이면 KV pool이 `16 × 8192 × 144 KiB = 18.00 GiB`, device 4개 분할 시 **4.50 GiB/device**(가용 15.7 GiB). weight 약 1.9 GiB/device를 더해도 여유가 있다.

## Substrate 상태

compile·측정 전 `apply.sh status`가 `patched`(SHA256 `70942d16…`)가 아니면 시작하지 않는다.

## Compile

```bash
timeout 1800 optimum-rbln-cli --model-id Qwen/Qwen3-4B \
  --output-dir /home/rebel/continuum-npu/models/Qwen3-4B-rbln-b16-s8192-d4-mb16 \
  --batch_size 16 --decoder_batch_sizes 1,4,6,8,10,16 \
  --max_seq_len 8192 --num_devices 4
```

**예상**: compile 472 s, artifact 13.11 GiB. `models/`는 33 → 46 GiB(상한 80 GiB).

승인된 파라미터로 실패하면 **파라미터를 바꿔 재시도하지 않고** 실패 증거를 기록한 뒤 진단 재시도 1회만 쓴다.

### 사상표 재검증 (본 실행 전, [TASK23](TASK23.md) 축약판)

새 artifact에서 `[BUCKET]` 로그로 사상을 확인한다. 동시성 **3, 5, 7, 9, 11**을 각각 1회 보낸다.

**기대**: 3 → 4, 5 → 6, 7 → 8, 9 → 10, 11 → 16.

**사상이 기대와 다르면 그 자체를 기록하고 판정 설계를 조정한다.**

## 실험 격자

| 항목 | 값 |
|---|---|
| N | **6, 8** (확증 구간) + **10** (탐색 구간) |
| arm | `BASE`(기존 b8 artifact) / `TUNED`(신규 b16 artifact) |
| block | b0, b1, b2 |
| 총 조합 | 3 × 2 × 3 = **18** |
| plan seed | `base_seed = 20260980` — **탐색·평가 어느 쪽에도 쓰지 않은 신규 seed** |
| gap | `toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60` |
| 그 외 | [TASK31](TASK31.md)과 동일 |

**짝 설계(P1)**: 두 arm은 `(base_seed, block_id)`만으로 생성되는 **같은 plan**을 쓴다. 차이는 compile 구성뿐이다.

블록 랜덤화: b0 `BASE`→`TUNED`, b1 `TUNED`→`BASE`, b2 `BASE`→`TUNED`.

## 선등록 예측 — 이 문서의 본체

[TASK33](TASK33.md)의 시뮬레이터(commit `924d6e8`)로 계산했다. `busy ratio` = device time(`TUNED`) / device time(`BASE`). **1보다 작으면 개선이다.**

| N | 구간 | **예측 busy ratio** | 예측 절감 | 블록별 (b0/b1/b2) | 예측 재사용 | decode비 / prefill비 |
|---|---|---|---|---|---|---|
| 6 | **확증** | **0.9614** | +3.86 % | 0.9635 / 0.9698 / 0.9501 | 16 → 18 / 18 | 0.965 / 0.946 |
| 8 | **확증** | **0.9198** | +8.02 % | 0.8807 / 0.9265 / 0.9438 | 12 → 24 / 24 | 0.999 / 0.730 |
| 10 | 탐색 | 0.8703 | +12.97 % | 0.9532 / 0.8863 / 0.7622 | 9 → 29 / 30 | 0.957 / 0.669 |

**예측된 기전**: 이득은 decode가 아니라 **prefill**에서 온다(prefill비 0.67–0.95, decode비 0.96–1.00). outer slot이 8 → 16이 되어 캐시 축출이 거의 사라지고 재계산이 줄어든다.

## 판정 기준

### 확증 구간 (N ∈ {6, 8})

두 조건을 **모두** 만족해야 `PASS`다.

1. **오차**: `|예측 busy ratio − 실측 busy ratio| ≤ 0.03`
2. **방향**: 예측과 실측이 1을 기준으로 같은 쪽에 있거나, **둘 다 동치 밴드 `[0.98, 1.02]` 안**에 있다

밴드 예외는 [TASK25](TASK25.md)·[TASK28](TASK28.md)과 같은 이유로 **측정 전에 고정한다.**

| 결과 | 판정 |
|---|---|
| N=6·N=8 둘 다 만족 | **PASS** |
| 하나만 | **PARTIAL** |
| 둘 다 실패 | **FAIL** |

### 탐색 구간 (N = 10)

**판정하지 않는다.** [TASK24](TASK24.md)가 N ≥ 10에서 시뮬레이터 오차가 5–6배 커진다고 기록했고, 이 구성 비교에서는 기본 arm이 대기열에 걸리는 구간이라 특히 불확실하다. 예측 대비 오차를 **보고만** 한다.

### 채널 일치 요건 (모든 구간에 선행)

[TASK28](TASK28.md)과 동일하게 device time을 두 채널로 잰다 — **A**: `[BUCKET]` step 열 × [TASK13](TASK13.md) 비용 모형(새 bucket은 선형 보간), **B**: client `sent_s`/`done_s`의 in-flight 구간 합집합(모형 무의존). **두 채널의 ratio 차가 0.02를 넘으면 그 N의 판정을 보류한다.**

### X의 정의

**X = 워크로드 통계 기반 compile 구성 선택이 device에서 회수한 device time 비율** = `1 − 실측 busy ratio`(확증 구간).

## 불변식 (fail-loud, 위반 조합은 `INVALID`)

- **P1**: 두 arm의 plan(세션 수, turn 수, segment 길이, 생성 길이, gap)이 동일
- **P2**: 두 arm의 decode 작업량 `Σ(completion_tokens − 1)`이 동일
- **P3**: `TUNED` arm의 `[BUCKET]` padded 값이 `{1,4,6,8,10,16}` 안에만 있다
- I1–I5: [NSLOTS_SWEEP_PREREG.md](NSLOTS_SWEEP_PREREG.md)와 동일. bucket 집합은 arm별로 다르다

## 부속 산출 — 구성 선택의 민감도

**어떤 워크로드 통계가 선택을 바꾸는가**를 sim으로 보고한다. 이것이 "무엇을 다시 재면 재구성해야 하는가"라는 운영 지침이 된다. 판정 대상이 아니다.

## 실행 절차 (측정 전 고정)

`<RUN>` = `results/npu/stage2/<timestamp>-compile-config`

1. `apply.sh status` → `patched` 확인
2. compile → 비용 실측 기록 → 사상표 재검증
3. N 6 → 8 → 10 순서, 블록별 arm 순서표대로. background + 완료 표식 + PID 기준 server 종료
4. 조합마다 `utilization.py --cost-model`(arm별 `--buckets`)
5. P1–P3·I1–I5 → 채널 일치 → 확증 구간 판정 → 탐색 구간 보고 → 민감도

**실행 중인 실험의 script를 편집하지 않는다** ([TASK23](TASK23.md)의 연쇄 실패 원인).

## 관련 문서

- [TASK33](TASK33.md) — compile-time이 유일 경로임을 확정한 분기
- [TASK31](TASK31.md) — 현실 워크로드
- [TASK28](TASK28.md) — 2채널 관측과 확증/탐색 구간 패턴
- [TASK23](TASK23.md) — 사상표 재검증, 재compile 개입의 선례
- [TASK10](TASK10.md) — compile 비용 모형
- [TASK08](TASK08.md) — `batch_size` ↔ `decoder_batch_sizes` ↔ `kvcache_num_blocks`
