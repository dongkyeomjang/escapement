# 선등록 — 재compile 효과와 회차 간 변동의 분리

이 문서는 compile과 측정 **시작 전에** commit한다. 아래의 artifact, 회차 정의, 실행 순서, 귀무 분포, 판정 통계량, 판정 규칙, 무효 규칙은 측정 후에 바꾸지 않는다. 결과를 보고 완화하지 않으며, 완화가 불가피하면 원 기준의 실패를 함께 보고한다.

## 목적

[TASK55](TASK55.md)가 판정하지 못한 질문을 가른다: **공통 bucket 비용 차이(bucket 2의 `C_model` 0.29 ms)가 재compile의 효과인가, 측정 회차 간 변동인가.** [TASK55](TASK55.md)는 artifact당 1회씩만 재어 두 성분이 섞였고, 선등록 밴드를 **어느 분산 성분에서 유도하는지** 잘못 골랐다(발견 2). 이번에는 **같은 조건의 반복에서 귀무 분포를 먼저 얻고** 그 분포에 대해 artifact 차이를 판정한다.

**예측은 등록하지 않는다.** 방향 예측이 아니라 분산 분리가 목적이므로 판정 규칙만 등록한다(Advisor 지시).

## 승인 범위 (Advisor 지시문, 사용자 전달, 2026-09-11)

- 승인: **compile 1회**(A3), bucket 비용 측정을 위한 serving 기동, 분석 script, 선등록 문서, TASK 문서
- 금지: 기존 artifact(`mb`, `mb6`)의 재compile·삭제, 기존 TASK 문서 수정, descriptor·시뮬레이터 계수 변경. **이 실험은 논문 판정용이며 모형 갱신용이 아니다**
- **회차 재정의(사용자 승인)**: `VLLM_RBLN_METRICS`는 서버 종료 시 lifetime 누적 요약 1개만 내고 bucket별 구분이 없다(`vllm_rbln/v1/worker/metrics.py`의 `PerformanceTracker`는 `decode_metrics`·`padded_decode_metrics` 두 개뿐이고 `VLLM_RBLN_METRICS_FILE`은 같은 요약의 사본이다). 서버 1회 기동으로는 bucket 1개의 `C_model`만 얻는다. 따라서 **회차 = 같은 artifact의 bucket 1·2·4·8을 각각 fresh server lifecycle로 잰 한 벌(4 lifecycle)** 이다. 총 **3 artifact × 5 회차 × 4 bucket = 60 lifecycle**

## Substrate 상태

`bash patches/vllm_rbln-0.11.1/apply.sh status`가 `patched`(SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01`)가 아니면 시작하지 않는다. 측정 전후로 덤프해 무차이를 확인한다.

## Artifact 3종

| id | 구성 | 경로 | 동일성 기준 |
|---|---|---|---|
| **A1** | `(1,2,4,8)`, batch 8 — 기존 `mb` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb` | manifest `b4f5cbf1634a8c4c1b0a4ca5cbda05272511007fdcbe3edb4756c3257b651f5f` ([TASK54](TASK54.md)·[TASK55](TASK55.md)) |
| **A2** | `(1,2,4,6,8)`, batch 8 — 기존 `mb6` | `models/Qwen3-4B-rbln-b8-s8192-d4-mb6` | manifest `348f2863eb5f8ee6b12da4ec7b73e2e7bb5227cb610fa4e610310a7032cd24bf` |
| **A3** | `(1,2,4,8)`, batch 8 — **A1과 같은 구성을 새로 compile** | `models/Qwen3-4B-rbln-b8-s8192-d4-mb-rc` | compile 직후 산출한 manifest(`<RUN>/manifest-A3.sha256`) |

manifest는 [`run_step_cost.sh`](../../experiments/npu/stage2/run_step_cost.sh)와 같은 형식(파일별 SHA256 목록의 SHA256)이다. **측정 전에 세 manifest가 기준과 다르면 시작하지 않는다**(G3). 측정 후에도 다시 산출해 기록한다.

### A3 compile (유일한 신규 compile)

```bash
bash experiments/npu/stage2/compile_recompile_a3.sh <RUN>
```

명령은 [TASK10](TASK10.md)의 A1 compile과 **출력 경로만 다르다**:

```bash
env -u PYTHONPATH HF_HUB_OFFLINE=1 /usr/bin/time -v timeout 1800 optimum-rbln-cli \
  --model-id Qwen/Qwen3-4B \
  --output-dir /home/rebel/continuum-npu/models/Qwen3-4B-rbln-b8-s8192-d4-mb-rc \
  --batch_size 8 --decoder_batch_sizes 1,2,4,8 \
  --max_seq_len 8192 --num_devices 4
```

- **알려진 환경 차이 1건: `HF_HUB_OFFLINE=1`.** [TASK10](TASK10.md)은 이 변수 없이 실행했다. 이번에는 weight를 cache된 snapshot `1cfa9a7208912126459214e8b04321603b3df60c`([TASK06](TASK06.md)이 download한 revision, cache에 있는 유일한 snapshot)로 고정하고 **승인되지 않은 download를 불가능하게** 하려고 켠다. hub 해석 외의 compile 경로에는 관여하지 않는 변수로 알고 있으나 **그 무관성은 확인하지 않았다**(`UNKNOWN`으로 기록)
- **1회만 시도한다.** 실패하면 파라미터를 바꿔 재시도하지 않고 실패 증거를 기록한 뒤 중단·보고한다
- compile 성공 조건: exit 0, `rbln_config.json`의 `batch_size = 8`, `decoder_batch_sizes = [8,4,2,1]`, `kvcache_num_blocks = 8`
- `models/` 증가 예상 약 11.5 GiB([TASK10](TASK10.md) 실측 11.501 GiB). 현재 `models/` 약 89 GiB, `/` 여유 693 GiB

### A3 compile 기록 대조표 (결과 보고 항목)

아래 항목을 A1 생성 기록과 나란히 적는다. **동일 보장이 불가능한 항목은 `UNKNOWN`으로 적는다.** 대조는 보고이며 판정 조건이 아니다(compile 성공 조건만 위와 같다).

| 항목 | A1 기록 출처 |
|---|---|
| 명령·인자 | [TASK10](TASK10.md) 「실험 또는 검증 방법」 |
| 환경 변수 | 명령에 드러난 `env -u PYTHONPATH`만 기록됨 — 그 외 `UNKNOWN` |
| `optimum-rbln`, `rebel-compiler`, `torch`, `transformers`, `huggingface_hub` 버전 | [TASK10](TASK10.md)·[TASK06](TASK06.md) 시작 상태 |
| 그 외 package 전체 | A1 시점 `pip freeze` 기록 없음 — `UNKNOWN`. 이번에는 `pip freeze`를 남긴다 |
| KMD(driver) 버전 | A1 시점 `rbln-smi-before-compile.txt` (`KMD ver: 3.2.2`) |
| host, kernel | host는 [TASK10](TASK10.md) 기록(`atom-max8`), kernel은 A1 시점 기록 없음 — `UNKNOWN` |
| HF weight revision | [TASK06](TASK06.md) `1cfa9a72…` |
| `rbln_config.json` | A1 compile 기록 `compile/rbln_config-b8.json`과 artifact의 파일 — `diff` |
| 파일별 바이트 | A1 artifact 파일별 SHA256과 A3 비교 — 같음/다름을 파일마다 적는다 |
| compile wall-clock, peak RSS | [TASK10](TASK10.md) 349.0 s, 35.9 GiB |

**A3의 `.rbln` 바이트가 A1과 같은지 다른지는 보고만 하며 R1의 규칙을 바꾸지 않는다.**

## 측정 — [TASK13](TASK13.md)·[TASK55](TASK55.md)과 같은 방법

| 항목 | 값 |
|---|---|
| probe | [`decode_cost_probe.py`](../../experiments/npu/stage2/decode_cost_probe.py) (수정 없음) |
| prompt | `experiments/npu/stage1/prompt.txt` (20 token) |
| `--max-tokens` | **512** (lifecycle당 511 decode step) |
| `--seed` | **20260819** |
| level | bucket과 같다 — **1, 2, 4, 8** (세 artifact 모두 level b → bucket b) |
| server | lifecycle마다 fresh. `vllm serve <artifact> --host 127.0.0.1 --port 8000`, prefix caching flag 없음 |
| env | `VLLM_LOGGING_LEVEL=DEBUG`, `VLLM_RBLN_METRICS=1` |
| 종료 | 자기 pid에 `SIGTERM`(이때 `FINAL PERFORMANCE STATISTICS [MODEL]`·`[SAMPLER]`가 남는다) |
| 구동 | [`run_recompile_variance.sh`](../../experiments/npu/stage2/run_recompile_variance.sh) |

### 산출 정의

- **`C_model(a, r, b)`** — artifact `a`, 회차 `r`, bucket `b` lifecycle의 서버 종료 로그 `[MODEL]` 절 `DECODE METRICS` **p50**(ms, 로그 해상도 0.01 ms). "회차당 bucket별 중앙값"이 이 p50이다. **판정에 쓰는 유일한 양**
- 보조(보고만): `C_sampler` p50, `C_fixed = C_model + C_sampler`, 채널 C(client ITL 중앙값), 채널 D(server mean ITL)

### 실행 순서 (두 겹 회전, 측정 전 고정)

| 라운드 | artifact 순서 | 회차 안 bucket 순서 |
|---|---|---|
| r0 | A1 → A2 → A3 | 1 → 2 → 4 → 8 |
| r1 | A2 → A3 → A1 | 2 → 4 → 8 → 1 |
| r2 | A3 → A1 → A2 | 4 → 8 → 1 → 2 |
| r3 | A1 → A2 → A3 | 8 → 1 → 2 → 4 |
| r4 | A2 → A3 → A1 | 1 → 2 → 4 → 8 |

라운드 `r`의 artifact `a` 한 벌이 `a`의 `r`번째 회차다. 한 라운드의 세 artifact는 같은 bucket 순서를 쓴다. 60줄 순서는 driver가 이 표에서 만들어 `<RUN>/order.txt`에 쓴다. 시간대 효과가 특정 artifact에 몰리지 않게 하는 장치이며 **시간대를 통제 변수로 쓰지는 않는다.**

### 회차 조건 기록 (판정에 사용 금지)

lifecycle마다 기동 요청 시각(`<TAG>-launch.txt`), health 통과 시각, 종료 시각, 기동 직전 `rbln-smi`(온도·전력)를 남긴다. **사후 검토용이며 판정에 쓰지 않는다.**

## 귀무 분포 (측정 전 고정)

**bucket `b`의 귀무 표본 = 같은 artifact·같은 bucket의 회차 쌍 `|C_model(a, i, b) − C_model(a, j, b)|`**, `i < j`. (artifact, bucket) 칸마다 C(5,2) = 10쌍, **bucket별 30쌍**(세 artifact 합동). q95·q90은 **bucket별 30쌍에서** 취한다(bucket마다 변동 크기가 다를 수 있으므로 bucket 간 합동하지 않는다). 분위는 `numpy.percentile(..., method="linear")`로 계산한다.

**[TASK55](TASK55.md)과의 대응.** 이 쌍은 [TASK55](TASK55.md) 관측 4의 **0.32 ms와 같은 종류의 비교**다 — 같은 artifact(`mb`), 같은 bucket(2), 다른 lifecycle. **다른 점은 시간 간격 하나**다: 0.32 ms는 08-19와 09-08의 두 측정(약 3주, 다른 측정 세션) 사이이고, 이번 귀무 쌍은 **한 측정 세션(약 80분) 안**의 lifecycle 사이다. 따라서 이번 귀무 분포는 **세션 안 lifecycle 간 변동**을 담고 **날짜 간 변동은 담지 않는다.** [TASK55](TASK55.md) P2a의 0.29 ms(`mb` 대 `mb6`, bucket 2, 같은 날 다른 lifecycle)는 판정 통계량 쪽의 비교(다른 artifact)에 해당한다.

## 판정 통계량

**`M(a, b)` = artifact `a`, bucket `b`의 5회차 `C_model`의 중앙값.** bucket별로

- `|Δ(A1, A3)|(b) = |M(A1, b) − M(A3, b)|`
- `|Δ(A1, A2)|(b)`, `|Δ(A2, A3)|(b)` 같은 방식

## 판정 규칙

bucket별 판정: `|Δ|(b) ≤ q95(b)`이면 `WITHIN`, 넘으면 `OUTSIDE`. 부동소수 비교에 `1e-9` 여유를 둔다(입력 해상도 0.01 ms).

| 규칙 | 비교 | 종합 판정 |
|---|---|---|
| **R1** (동일 구성 재compile 효과) | `|Δ(A1, A3)|` | bucket **4개 전부** `WITHIN`이면 **"동일 구성 재compile 효과는 회차 간 변동과 구별되지 않음"**. 하나라도 `OUTSIDE`면 **"구별됨"**(해당 bucket 명시) |
| **R2** (격자 변경 재compile의 공통 bucket) | `|Δ(A1, A2)|`, `|Δ(A2, A3)|` **각각** | 같은 기준. 두 비교를 따로 판정·보고한다 |

- 판정은 bucket별로 보고하고 종합은 **"4개 전부"** 를 요구한다
- **q90 기준 결과를 병기**한다(판정 아님)

## 게이트와 무효 규칙 (fail-loud)

| # | 검사 | 위반 시 |
|---|---|---|
| G1 | lifecycle마다 전 요청 status 200, chunk 수 512 단일값 | 그 lifecycle 무효 |
| G2 | lifecycle마다 `[BUCKET]` **511줄**, `request_nums` 단일값 = level, `padded_batch_size` 단일값 = level | 그 lifecycle 무효 |
| G2′ | `[MODEL]`·`[SAMPLER]` `DECODE METRICS` p50이 파싱된다 | 그 lifecycle 무효 |
| G3 | 측정 전 세 artifact의 manifest가 기준과 같다 | **시작하지 않는다** |
| G4 | patch SHA256 측정 전후 동일 | TASK `INVALID` |
| G5 | 채널 D ≈ 채널 C | 보고만 |

- **무효 lifecycle은 그 자리에서 즉시 1회 재실행**한다(실패 시도는 `failed/`에 보존, `reruns.txt`에 기록). 재실행도 실패하면 그 칸은 **`INVALID`**
- `INVALID` 칸이 있는 bucket은 해당 비교의 bucket 판정을 **`INCOMPLETE`** 로 보고한다(값은 남은 회차로 함께 보고). 종합 판정은 `OUTSIDE`가 하나라도 있으면 "구별됨", 그렇지 않고 `INCOMPLETE`가 있으면 **"판정 불가"** 다
- driver의 즉시 게이트와 분석의 게이트는 같은 함수(`recompile_variance.py`의 `gate`)다

## 해석 한계 (측정 전 등록)

1. **표본이 얇다.** (artifact, bucket) 칸당 회차 5개, 귀무 쌍은 bucket당 30개다. 30개의 q95는 `linear` 방식에서 정렬 28·29번째 값 사이의 보간이라 **사실상 최댓값 근처**이고, 한 칸의 10쌍은 같은 5개 값에서 나와 **서로 독립이 아니다.** 그래서 q90을 병기한다
2. **집계 단위가 다르다.** 판정 통계량은 **5회차 중앙값의 차**인데 귀무 표본은 **단일 lifecycle 쌍의 차**다. [TASK50](TASK50.md) 발견 4("허용차를 검증하려면 판정과 같은 집계 단위에서 null을 재야 한다")가 지적한 것과 같은 불일치다. 회차 값이 독립·동일 정규분포라고 가정해 계산하면 5개 중앙값 차의 표준편차는 단일 쌍 차의 약 0.54배다. 즉 **이 규칙은 "구별되지 않음" 쪽으로 관대하다.** 이 계산은 가정에 기댄 참고값이며 판정에 쓰지 않는다. 규칙은 지시문대로 둔다
3. **귀무 분포는 한 측정 세션 안의 변동이다.** 날짜 간 변동([TASK55](TASK55.md) 관측 4의 0.32 ms 종류)은 담지 않는다
4. **시간대·온도 등 회차 조건은 기록만 하고 통제 변수로 쓰지 않는다**
5. **`C_model`의 로그 해상도는 0.01 ms**라 귀무 쌍에 0과 동률이 많을 수 있다
6. 판정 결과에 **"재compile은 안전하다"류 해석을 붙이지 않는다** — 판정 결과만 보고한다

## 사전 검증 (선등록 전 실행)

`recompile_variance.py selftest`가 [TASK55](TASK55.md)의 저장 로그 9개에서 `C_model`을 다시 읽어 [TASK55](TASK55.md) 관측 2의 표와 대조한다. 9/9 일치와 게이트 통과가 선등록 commit의 전제다.

## 실행 절차 (측정 전 고정)

`<RUN>` = `results/npu/stage2/<timestamp>-recompile-variance`

1. 이 문서와 script 3개를 commit한다(선등록)
2. `apply.sh status` → `patched` 확인, 32 device idle 확인
3. `compile_recompile_a3.sh <RUN>` — A3 compile, 기록 대조 자료 생성
4. `run_recompile_variance.sh <RUN>` — 60 lifecycle (예상 약 80분, [TASK55](TASK55.md) 실측 77 s/lifecycle 기준)
5. `recompile_variance.py analyze --run <RUN> --output <RUN>/recompile_variance.json`

**실행 중인 script를 편집하지 않는다**([TASK23](TASK23.md)).

## 필수 기록 항목

lifecycle별 `server-<TAG>.log`, `probe/decode_cost.<TAG>.json`, `probe-<TAG>.log`, `check-<TAG>.json`, `<TAG>-launch.txt`·`-server-start.txt`·`-server-stop.txt`, `smi/<TAG>.txt`. 전체: `order.txt`, manifest 전후(`manifest-gate-{before,after}.txt`), patch 전후, `rbln-smi` 전후, 측정 시작·종료 시각, `reruns.txt`, disk 사용량, compile 기록 일체(`compile/`).

## 관련 문서

- [TASK55](TASK55.md) / [GRID_STEP_COST_PREREG.md](GRID_STEP_COST_PREREG.md) — 이 질문을 남긴 TASK
- [TASK13](TASK13.md) / [DECODE_COST_PREREG.md](DECODE_COST_PREREG.md) — 측정 방법
- [TASK50](TASK50.md) — 귀무 분포와 집계 단위의 교훈
- [TASK10](TASK10.md) / [TASK06](TASK06.md) — A1 compile·weight 기록
- [TASK23](TASK23.md) / [TASK54](TASK54.md) — A2 compile과 manifest
