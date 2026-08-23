# 선등록 — compile-time 구성 이득의 최종 확증 측정

## 문서 성격

[CLAUDE.md](../../CLAUDE.md) 실행 원칙 16과 [TASK_GUIDE.md](TASK_GUIDE.md)가 요구하는 **선등록(preregistration)** 이다. 이 문서를 담은 commit 이후에 compile과 측정을 시작한다. **이것이 이 연구 프로그램의 마지막 측정이며 확증 요건을 어느 것도 사후 조정하지 않는다.**

## 무엇을 고치는가

[TASK34](TASK34.md)는 X = 7.4 %를 관측했으나 **확증 판정을 보류**했다. 선등록한 채널 A가 decode step만 세는데 그 개입의 주효과는 prefill이었기 때문이다. 사후에 정의한 채널 A′는 예측과 맞았지만 **결과를 보고 정의한 채널은 판정이 될 수 없다.**

이번에는 **채널 A′를 측정 전에 고정한다.** 아울러 "지배 인자는 `batch_size`"라는 sim 주장을 device에서 절제로 확인한다.

## 승인 범위 (사용자 판정, 2026-08-23)

serving 기동·종료(약 30회), 기존 관측 스택, **재compile 1회**(batch-only 대조) + 진단 1회 예비. 기존 artifact 재사용.

범위 밖: download, patch 변경, RSD 변경, legacy 수정, GPU 서버 작업, remote push 자동 수행.

## Substrate 상태

compile·측정 전 `apply.sh status`가 `patched`(SHA256 `70942d16…`)가 아니면 시작하지 않는다.

## 실험 격자

| 항목 | 값 |
|---|---|
| arm | ① `BASE` `(1,2,4,8)` batch 8 (기존) · ② `BATCHONLY` `(1,2,4,8,16)` batch 16 (**신규 compile**) · ③ `TUNED` `(1,4,6,8,10,16)` batch 16 (기존, [TASK34](TASK34.md)) |
| N | **6, 8** (확증 구간) + **10** (탐색 구간) |
| block | b0, b1, b2 |
| 총 조합 | 3 × 3 × 3 = **27** |
| plan seed | **`base_seed = 20261000`** |
| gap | `toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60` ([TASK31](TASK31.md) 현실 워크로드) |
| 그 외 | [TASK31](TASK31.md)·[TASK34](TASK34.md)와 동일 |

**seed 격리**: `20261000`은 구성 선정에 쓰인 어떤 자료와도 겹치지 않는다. 탐색 `20260910/20260921/20260932`, 평가 `20260943/20260954/20260965`, [TASK34](TASK34.md) 측정 `20260980` 어느 것도 아니다.

**짝 설계(P1)**: 세 arm은 `(base_seed, block_id)`만으로 생성되는 **같은 plan**을 쓴다. 차이는 compile 구성뿐이다.

블록 랜덤화: b0 ①→②→③, b1 ③→①→②, b2 ②→③→①.

## Compile (arm ②)

```bash
timeout 1800 optimum-rbln-cli --model-id Qwen/Qwen3-4B \
  --output-dir /home/rebel/continuum-npu/models/Qwen3-4B-rbln-b16-s8192-d4-batchonly \
  --batch_size 16 --decoder_batch_sizes 1,2,4,8,16 \
  --max_seq_len 8192 --num_devices 4
```

**예상**([TASK10](TASK10.md) 모형): compile **410 s**, artifact **12.31 GiB**. `models/` 47 → 59 GiB(상한 80 GiB). **bucket 5개·compiled model 6개로 그 모형의 5번째 관측점이 된다.**

승인된 파라미터로 실패하면 파라미터를 바꿔 재시도하지 않고 실패 증거를 기록한 뒤 진단 재시도 1회만 쓴다.

### 사상표 재검증 (본 실행 전, 축약판)

동시성 **3, 5, 9, 11**을 각각 1회. **기대**: 3 → 4, 5 → 8, 9 → 16, 11 → 16.

사상이 기대와 다르면 그 자체를 기록하고 판정 설계를 조정한다.

## 선등록 채널 (핵심 교정)

| 채널 | 정의 | 모형 의존 |
|---|---|---|
| **A′** | `[BUCKET]` step 열의 `(actual, bucket)`마다 [TASK13](TASK13.md) step 비용을 합산한 **decode** + per-request `prompt_tokens − cached_tokens`에 [TASK22](TASK22.md) `PrefillCostModel`을 적용한 **prefill** | 두 비용 모형에 의존. 미측정 bucket(6·10·16)은 **선형 보간** |
| **B** | client `sent_s`/`done_s`의 **in-flight 구간 합집합** | **무의존** |

**허용차 `|A′ − B| ≤ 0.02`.** [TASK28](TASK28.md)·[TASK34](TASK34.md)와 **같은 값이며 완화가 아니다.** 이 정의를 [TASK34](TASK34.md) 자료에 소급 적용하면 실제 차이가 0.0029 / 0.0104 / 0.0011이므로 달성 가능한 값임을 측정 전에 확인했다.

**알려진 편향을 명시한다**: [TASK34](TASK34.md) 관측 4에서 bucket 10의 보간 비용이 실측 적합보다 10.9 % 낮았다. 그럼에도 **보간을 쓴다** — 그 적합 자체가 측정된 bucket에서도 ±11 % 산포를 보여 [TASK13](TASK13.md)만큼 정밀하지 않기 때문이다. 적합값을 쓴 민감도는 부속으로 보고한다.

## 선등록 예측

[TASK33](TASK33.md)의 시뮬레이터(commit `924d6e8`)로 계산했다. `busy ratio` = device time(arm) / device time(`BASE`). **1보다 작으면 개선이다.**

| N | arm | **예측 busy ratio** | 예측 절감 | prefill비 | decode비 | 블록별 (b0/b1/b2) |
|---|---|---|---|---|---|---|
| 6 | ② `BATCHONLY` | **0.9610** | +3.90 % | 0.8366 | 1.0000 | 1.0000 / 0.9340 / 0.9486 |
| 6 | ③ `TUNED` | **0.9466** | +5.34 % | 0.8366 | 0.9810 | 0.9770 / 0.9277 / 0.9350 |
| 8 | ② `BATCHONLY` | **0.9101** | +8.99 % | 0.6732 | 1.0045 | 0.9273 / 0.9165 / 0.8710 |
| 8 | ③ `TUNED` | **0.8971** | +10.29 % | 0.6732 | 0.9863 | 0.9127 / 0.9043 / 0.8596 |
| 10 | ② `BATCHONLY` | 0.9213 | +7.87 % | 0.6521 | 1.0393 | 0.9126 / 0.9160 / 0.9349 |
| 10 | ③ `TUNED` | 0.8899 | +11.01 % | 0.6521 | 0.9942 | 0.8653 / 0.8955 / 0.9079 |

재사용 예측(세 N 공통 방향): `BASE` 14/9/7 → 두 arm 모두 18/24/29 (분모 18/24/30).

**예측된 기전**: 이득은 **prefill**에서 온다(prefill비 0.65–0.84, decode비 0.98–1.04). 두 arm의 prefill비가 **동일**한 것이 핵심이다 — `batch_size`가 같으면 KV pool이 같고 캐시 생존이 같다. **arm ②와 ③의 차이는 오직 decode 쪽 bucket 정합에서 온다.**

## 판정 기준

### 채널 일치 요건 (모든 판정에 선행)

`|A′ − B| ≤ 0.02`. 넘으면 그 (N, arm)의 판정을 **보류**한다.

### 확증 구간 (N ∈ {6, 8}) — arm ②·③ 각각

두 조건을 **모두** 만족해야 `PASS`다.

1. **오차**: `|예측 busy ratio − 실측 busy ratio| ≤ 0.03` (채널 A′ 기준)
2. **방향**: 예측과 실측이 1을 기준으로 같은 쪽에 있거나, 둘 다 동치 밴드 `[0.98, 1.02]` 안

| 결과 | 판정 |
|---|---|
| 4칸(2 N × 2 arm) 전부 만족 | **PASS** |
| 일부만 | **PARTIAL** — 어느 칸이 왜 빗나갔는지 기록 |
| 전부 실패 | **FAIL** |

### 탐색 구간 (N = 10)

**판정하지 않는다.** 예측 대비 오차를 보고만 한다.

### 부속 판정 — 지배 인자 절제 (확증 구간)

**sim은 arm ②가 이득의 대부분을 내고 arm ③이 1.30–1.45 %p를 더한다고 예측한다.** device에서 다음 둘을 확인한다.

1. **순서**: `busy_ratio(③) < busy_ratio(②) < 1` (③이 가장 좋고 둘 다 개선)
2. **크기**: ③과 ②의 차이가 예측(N=6 1.45 %p, N=8 1.30 %p)과 **부호가 같고 절대 오차 ≤ 3 %p**

둘 다 만족하면 **"지배 인자는 `batch_size`, bucket 집합은 부가 이득"이 device에서 확인됨**으로 기록한다.

### X의 정의

**X = compile 구성 선택이 device에서 회수한 device time 비율** = `1 − 실측 busy ratio`. 확증 구간(N ∈ {6,8}) 합산을 **두 채널 모두**로 보고하고, 두 값이 허용차 안일 때만 확정치로 쓴다.

## 불변식 (fail-loud, 위반 조합은 `INVALID`)

- **P1**: 세 arm의 plan이 동일
- **P2**: 세 arm의 decode 작업량 `Σ(completion_tokens − 1)`이 동일
- **P3**: 각 arm의 `[BUCKET]` padded 값이 그 arm의 bucket 집합 안에만 있다
- I1–I5: [NSLOTS_SWEEP_PREREG.md](NSLOTS_SWEEP_PREREG.md)와 동일

## 필수 측정 항목

조합별: per-request JSONL, plan summary, `[BUCKET]`·`[PFX]` 로그 전문, `/metrics` 덤프, utilization JSON. arm ② 추가: compile 로그·wall-clock·artifact 크기·`rbln_config.json`·사상표. 전체: patch state, `rbln-smi`, provenance, 측정 시작·종료 시각, 선등록 commit.

## 실행 절차 (측정 전 고정)

`<RUN>` = `results/npu/stage2/<timestamp>-final-confirm`

1. `apply.sh status` → `patched` 확인
2. arm ② compile → 비용 실측 → 사상표 재검증
3. N 6 → 8 → 10 순서, 블록별 arm 순서표대로. background + 완료 표식 + PID 기준 server 종료
4. 조합마다 `utilization.py`(arm별 `--buckets`, `--cost-model` 없이)
5. P1–P3·I1–I5 → 채널 일치 → 확증 구간 판정 → 부속 절제 판정 → 탐색 구간 보고

**실행 중인 실험의 script를 편집하지 않으며, 진행 중인 run을 감사하지 않는다** ([TASK23](TASK23.md)·[TASK34](TASK34.md)의 실패 원인).

## 관련 문서

- [TASK34](TASK34.md) — 보류된 확증. 이 문서가 고치는 대상
- [TASK33](TASK33.md) — compile-time이 유일 경로임을 확정한 분기
- [TASK31](TASK31.md) — 현실 워크로드
- [TASK28](TASK28.md) — 2채널·확증/탐색 구간 패턴
- [TASK22](TASK22.md), [TASK13](TASK13.md) — 채널 A′의 두 비용 모형
- [TASK10](TASK10.md) — compile 비용 모형(5번째 점)
