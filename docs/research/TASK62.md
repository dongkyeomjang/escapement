# TASK62 — 재compile 효과와 회차 간 변동의 분리

## 상태

DONE

## 판정

선등록 문서: [RECOMPILE_VARIANCE_PREREG.md](RECOMPILE_VARIANCE_PREREG.md) (commit `8cd2e92`, 2026-09-11T19:12:46+09:00). **A3 compile 시작 19:13:45(선등록 59초 뒤), 측정 시작 19:22:31(선등록 9분 45초 뒤).** 판정 기준을 측정 후에 바꾸지 않았다.

bucket별 `|Δ|`(ms) / 해당 bucket 귀무 30쌍의 q95. `WITHIN` = `|Δ| ≤ q95`.

| 규칙 | 비교 | bucket 1 | bucket 2 | bucket 4 | bucket 8 | 종합 |
|---|---|---|---|---|---|---|
| **R1** | `|Δ(A1, A3)|` | 0.05 / 0.221 `WITHIN` | 0.02 / 0.141 `WITHIN` | 0.02 / 0.3675 `WITHIN` | 0.03 / 0.06 `WITHIN` | **동일 구성 재compile 효과는 회차 간 변동과 구별되지 않음** (4/4) |
| **R2** | `|Δ(A1, A2)|` | 0.02 / 0.221 `WITHIN` | 0.01 / 0.141 `WITHIN` | 0.02 / 0.3675 `WITHIN` | **0.07 / 0.06 `OUTSIDE`** | **구별됨 — bucket 8** (3/4) |
| **R2** | `|Δ(A2, A3)|` | 0.07 / 0.221 `WITHIN` | 0.01 / 0.141 `WITHIN` | 0.04 / 0.3675 `WITHIN` | 0.04 / 0.06 `WITHIN` | **구별되지 않음** (4/4) |

**q90 병기(판정 아님)**: 결과가 q95와 같다 — R1 4/4, `|Δ(A1,A2)|` 3/4(bucket 8 제외), `|Δ(A2,A3)|` 4/4가 q90 이내다.

**R2 `|Δ(A1,A2)|` bucket 8의 수치**: `|Δ|` = 0.07000000000000028, q95 = 0.0600000000000005(부동소수 원값). 선등록의 `1e-9` 여유와 무관하게 **로그 해상도(0.01 ms) 한 단위** 차이로 `OUTSIDE`다. bucket 8 귀무 30쌍은 전부 0–0.06 ms 안이고 그중 4쌍이 0.06이라 **q95 = 최댓값 = 0.06**이다.

## 날짜

2026-09-11

## 목적

[TASK55](TASK55.md)가 판정하지 못한 질문 — **공통 bucket 비용 차이(bucket 2의 `C_model` 0.29 ms)가 재compile의 효과인가, 측정 회차 간 변동인가** — 를 가른다. [TASK55](TASK55.md) 발견 2의 교훈(밴드는 어느 분산 성분인지 명시하고 같은 조건의 반복에서 유도)을 적용해, 같은 artifact·같은 bucket의 반복에서 귀무 분포를 먼저 얻고 artifact 간 차이를 그 분포에 대해 판정한다(Advisor 지시, P2 재설계).

## 배경

관련 TASK:

- [TASK55](TASK55.md) — 이 질문을 남겼다. P2a `FAIL`(bucket 2 −0.29 ms), 관측 4(같은 `mb`의 날짜 간 0.32 ms)
- [TASK13](TASK13.md) — `C_model` 측정 방법(level마다 fresh server, METRICS p50)
- [TASK50](TASK50.md) — 무처치 반복의 null 분포, "판정과 같은 집계 단위에서 null을 재야 한다"(발견 4)
- [TASK10](TASK10.md) / [TASK06](TASK06.md) — A1 compile·weight download 기록
- [TASK23](TASK23.md) / [TASK54](TASK54.md) — A2(`mb6`) compile과 manifest

## 시작 상태

- 시작 commit `27fac98`(TASK61), `git status --short`: `?? .idea/`만
- 선등록 commit `8cd2e9262d9e7bc82ad0344c923e7ef278a5c1f6` (2026-09-11T19:12:46+09:00)
- Substrate: `patched`, SHA256 `70942d16d561d92a8aaf153ea5ce91109863b6d765862c9bcd7e71594301cc01` — compile 전 확인, 측정 전후 덤프 **무차이**
- Package: `vllm 0.22.0+cpu`, `vllm-rbln 0.11.1`, `optimum-rbln 0.11.1`, `rebel-compiler 0.11.1.post1`, `torch 2.11.0+cpu`, `torch-rbln 0.3.0`, `transformers 5.8.1`, `huggingface_hub 1.27.0`
- Host `atom-max8`, kernel `6.8.0-40-generic`, KMD 3.2.2, 32 device idle, 서버 없음·port 8000 비어 있음(`precheck.txt` 19:13:45)
- `models/` 86 GiB → A3 compile 후 97 GiB, `/` 사용률 19 %

## 수행 내용

1. `VLLM_RBLN_METRICS`가 bucket별 구분 없이 lifetime 요약 1개만 낸다는 것을 소스(`vllm_rbln/v1/worker/metrics.py`)에서 확인하고, **회차 = 같은 artifact의 bucket 1·2·4·8을 각각 fresh server로 잰 한 벌(4 lifecycle)** 로 재정의했다(사용자 승인). 총 60 lifecycle.
2. 파서를 [TASK55](TASK55.md) 저장 로그 9개로 검증했다(9/9 일치). 선등록 문서·compile script·구동 script·분석 script를 **compile·측정 전에 commit**했다.
3. A3를 [TASK10](TASK10.md)과 같은 명령으로 1회 compile하고 A1 기록과 대조했다.
4. 60 lifecycle을 두 겹 회전 순서로 실행했다. lifecycle마다 게이트를 즉시 검사해 1건을 그 자리에서 재실행했다.
5. 귀무 분포와 판정 통계량을 계산하고 R1·R2를 판정했다.

## 변경된 파일

- `docs/research/RECOMPILE_VARIANCE_PREREG.md` (선등록, 측정 전 commit `8cd2e92`)
- `experiments/npu/stage2/compile_recompile_a3.sh`, `experiments/npu/stage2/run_recompile_variance.sh`, `experiments/npu/analysis/recompile_variance.py` (측정 전 commit `8cd2e92`)
- `docs/research/TASK62.md` (신규), `docs/research/INDEX.md` (갱신)

기존 artifact(`mb`, `mb6`)는 재compile·삭제하지 않았다(측정 전후 manifest 동일). 기존 TASK 문서, descriptor, 시뮬레이터 계수는 수정하지 않았다. 신규 model artifact `models/Qwen3-4B-rbln-b8-s8192-d4-mb-rc/`(gitignored, 11.5 GiB)가 생겼다.

## 실험 또는 검증 방법

```bash
RUN=results/npu/stage2/20260911-191300-recompile-variance
bash experiments/npu/stage2/compile_recompile_a3.sh "$RUN"
bash experiments/npu/stage2/run_recompile_variance.sh "$RUN"
env -u PYTHONPATH python3 experiments/npu/analysis/recompile_variance.py analyze \
    --run "$RUN" --output "$RUN/recompile_variance.json"
```

`requested_condition` / `observed_condition` / `condition_reached`:

| 항목 | requested | observed | reached |
|---|---|---|---|
| compile | A3 1회, 성공 조건 충족 | 1회 exit 0, `batch_size 8`·`[8,4,2,1]`·`kvcache_num_blocks 8` | `YES` |
| lifecycle | 60 (3 × 5 × 4) | **60/60 유효**(재실행 1건 포함, 총 기동 61회) | `YES` |
| 실행 순서 | 선등록 두 겹 회전표 | `order.txt` 60줄이 표와 일치, `A1.r0.L1` → … → `A1.r4.L8` | `YES` |
| artifact 동일성 | 측정 전 기준과 같음 | **전후 모두 3/3 일치** | `YES` |
| lifecycle당 decode step | 511 | **60/60 전부 511** | `YES` |
| 사상 (level → bucket) | 1→1, 2→2, 4→4, 8→8 | **60/60 기대와 일치** | `YES` |
| patch 상태 | 측정 전후 동일 | 동일 | `YES` |
| 회차 조건(시각·온도) | 기록만 | lifecycle 기동 19:22:31–20:37:26, `rbln0`–`rbln3` 온도 29–59 °C | 기록됨(판정 미사용) |

## 결과

### 관측 1 — A3 compile 기록 대조표

| 항목 | A1 (`mb`, 2026-08-19) | A3 (`mb-rc`, 2026-09-11) | 동일 여부 |
|---|---|---|---|
| 명령·인자 | `optimum-rbln-cli --model-id Qwen/Qwen3-4B --batch_size 8 --decoder_batch_sizes 1,2,4,8 --max_seq_len 8192 --num_devices 4` | 같음(출력 경로만 `-mb-rc`) | 같음 |
| 실행 wrapper | `env -u PYTHONPATH /usr/bin/time -v timeout 1800` | 같음 + **`HF_HUB_OFFLINE=1`** | **다름 1건**(선등록한 차이) |
| 그 외 환경 변수 | 기록 없음 | `RBLN`·`HF_`·`VLLM`·`PYTHON`·`TRANSFORMERS`·`TORCH` 접두 변수 없음 | `UNKNOWN` |
| `optimum-rbln` / `rebel-compiler` | 0.11.1 / 0.11.1.post1 ([TASK10](TASK10.md)) | 0.11.1 / 0.11.1.post1 (compile log의 `RBLN SDK compiler version`도 같음) | 같음 |
| `torch` / `torch-rbln` / `transformers` / `huggingface_hub` | 2.11.0+cpu / 0.3.0 / 5.8.1 / 1.27.0 ([TASK06](TASK06.md)) | 같음 | 같음 |
| 그 외 package 전체 | `pip freeze` 기록 없음 | `compile/pip-freeze.txt`에 기록 | `UNKNOWN` |
| KMD | 3.2.2 (`rbln-smi-before-compile.txt`) | 3.2.2 | 같음 |
| host / kernel | `atom-max8` / 기록 없음 | `atom-max8` / `6.8.0-40-generic` | host 같음, kernel `UNKNOWN` |
| HF weight revision | `1cfa9a72…` ([TASK06](TASK06.md)) | cache의 유일 snapshot `1cfa9a72…`(compile 전후 동일), offline 해석 | 같음(A1이 online에서 같은 snapshot을 썼다는 것은 cache에 다른 snapshot이 없다는 사실로만 뒷받침됨) |
| hub 접근 | compile log에 unauthenticated 경고와 `Fetching 3 files` | 둘 다 없음 | **다름**(offline의 결과) |
| `rbln_config.json` | — | A1 artifact 파일·A1 compile 기록 사본과 **diff 0 byte** | 같음 |
| 컴파일러 `mod_name` | 5개 모델 전부 `fb0c81` | 5개 모델 전부 `9937a5` | **다름** |
| `.rbln` 5개 바이트 | — | **5/5 다름**(`prefill`, `decoder_batch_1/2/4/8`). **파일 크기는 5/5 같음** | **다름** |
| `tokenizer_config.json` | `"local_files_only": false` (694 B) | `"local_files_only": true` (693 B) | **다름**(offline의 흔적) |
| 그 외 파일 5개 | — | `chat_template.jinja`, `config.json`, `generation_config.json`, `rbln_config.json`, `tokenizer.json` 바이트 동일 | 같음 |
| compile wall-clock | 349.18 s (5:49.18) | **343.18 s** (5:43.18) | — |
| host peak RSS | 37,611,180 KiB | 37,480,012 KiB | — |
| user / sys CPU | 790.63 s / 640.62 s (409 %) | 794.22 s / 1045.43 s (536 %) | — |
| exit / 성공 조건 | 0 | **0**, `batch_size 8`, `decoder_batch_sizes [8,4,2,1]`, `kvcache_num_blocks 8` | 성공 |
| artifact manifest | `b4f5cbf1…651f5f` | `2d73b14143e300846b268f7a5aa8b4c2bd41d4169bf3204d33de30934121f1cd` | 다름 |

compile log에서 시각·진행 막대·소요 시간을 지우면 남는 차이는 hub 경고, `Fetching 3 files`, 출력 경로, `mod_name` 네 가지다.

### 관측 2 — 원자료: 회차 × artifact × bucket의 `C_model` p50 (ms)

Population: lifecycle 1개 = 511 decode step. Source: 서버 종료 로그 `FINAL PERFORMANCE STATISTICS [MODEL]`의 `DECODE METRICS` p50(로그 해상도 0.01 ms). Device scope: `rbln0`–`rbln3`.

| artifact | 회차 | b1 | b2 | b4 | b8 |
|---|---|---|---|---|---|
| A1 | r0 | 9.51 | 10.01 | 10.38 | 12.32 |
| A1 | r1 | 9.49 | 10.01 | 10.32 | 12.38 |
| A1 | r2 | 9.60 | 10.11 | 10.37 | 12.33 |
| A1 | r3 | 9.50 (재실행) | 10.07 | 10.27 | 12.35 |
| A1 | r4 | 9.52 | 10.07 | 10.34 | 12.38 |
| A2 | r0 | 9.53 | 10.12 | 10.32 | 12.40 |
| A2 | r1 | 9.49 | 9.94 | 10.32 | 12.42 |
| A2 | r2 | 9.49 | 10.06 | 10.47 | 12.41 |
| A2 | r3 | 9.60 | 9.99 | 10.31 | 12.44 |
| A2 | r4 | 9.47 | 10.09 | 10.32 | 12.46 |
| A3 | r0 | 9.54 | 10.05 | 10.39 | 12.33 |
| A3 | r1 | 9.53 | 10.06 | **10.70** | 12.36 |
| A3 | r2 | 9.56 | 10.13 | 10.31 | 12.38 |
| A3 | r3 | 9.56 | 10.04 | 10.30 | 12.38 |
| A3 | r4 | **9.77** | 10.03 | 10.36 | 12.39 |

굵은 두 값은 각 칸의 최댓값으로 칸 안 다른 값과 0.2 ms 이상 떨어져 있다. 원인은 조사하지 않았고 선등록대로 그대로 포함했다.

### 관측 3 — (artifact, bucket) 칸 요약: 5회차의 중앙값 `M`과 범위 (ms)

| 칸 | `M` | 최소 | 최대 | 범위 |
|---|---|---|---|---|
| A1 b1 | 9.51 | 9.49 | 9.60 | 0.11 |
| A2 b1 | 9.49 | 9.47 | 9.60 | 0.13 |
| A3 b1 | 9.56 | 9.53 | 9.77 | 0.24 |
| A1 b2 | 10.07 | 10.01 | 10.11 | 0.10 |
| A2 b2 | 10.06 | 9.94 | 10.12 | 0.18 |
| A3 b2 | 10.05 | 10.03 | 10.13 | 0.10 |
| A1 b4 | 10.34 | 10.27 | 10.38 | 0.11 |
| A2 b4 | 10.32 | 10.31 | 10.47 | 0.16 |
| A3 b4 | 10.36 | 10.30 | 10.70 | 0.40 |
| A1 b8 | 12.35 | 12.32 | 12.38 | 0.06 |
| A2 b8 | 12.42 | 12.40 | 12.46 | 0.06 |
| A3 b8 | 12.38 | 12.33 | 12.39 | 0.06 |

### 관측 4 — 귀무 분포 (같은 artifact·같은 bucket의 회차 쌍 `|Δ|`, bucket별 30쌍, ms)

| bucket | n | 중앙값 | q90 | **q95** | 최대 | `|Δ|` = 0인 쌍 |
|---|---|---|---|---|---|---|
| 1 | 30 | 0.035 | 0.210 | **0.221** | 0.24 | 2 |
| 2 | 30 | 0.060 | 0.121 | **0.141** | 0.18 | 2 |
| 4 | 30 | 0.055 | 0.313 | **0.3675** | 0.40 | 3 |
| 8 | 30 | 0.030 | 0.060 | **0.060** | 0.06 | 2 |

분위는 `numpy.percentile(method="linear")`. bucket 1·4의 q95는 각 bucket의 극단값 한 개(A3 r4 9.77, A3 r1 10.70)가 만든 쌍들에 걸려 있다. bucket 8은 30쌍 전부 0–0.06이고 0.06이 4쌍이다.

### 관측 5 — [TASK55](TASK55.md) bucket 2와의 병치 (판정 아님)

| 측정 | A1(`mb`) bucket 2 | A2(`mb6`) bucket 2 | 차 |
|---|---|---|---|
| [TASK13](TASK13.md) (08-19, 1 lifecycle) | 10.05 | — | — |
| [TASK55](TASK55.md) (09-08, 각 1 lifecycle) | 10.37 | 10.08 | −0.29 |
| **이번 (09-11, 각 5 lifecycle의 중앙값)** | **10.07** (범위 10.01–10.11) | **10.06** (범위 9.94–10.12) | **−0.01** |

이번 세션의 A1 bucket 2 다섯 값은 [TASK55](TASK55.md)의 `mb.L2` 10.37을 포함하지 않는다. 이번 bucket 2 귀무의 최댓값은 0.18 ms다.

### 관측 6 — 보조 채널 (5회차 중앙값, ms, 판정 아님)

| 칸 | `C_sampler` | `C_fixed` | 채널 C 중앙 ITL | 채널 D 평균 ITL |
|---|---|---|---|---|
| A1 b1 / b2 / b4 / b8 | 0.36 / 0.37 / 0.44 / 0.56 | 9.87 / 10.44 / 10.78 / 12.91 | 10.356 / 11.042 / 11.452 / 13.707 | 10.358 / 11.092 / 11.518 / 13.954 |
| A2 b1 / b2 / b4 / b8 | 0.36 / 0.37 / 0.44 / 0.59 | 9.85 / 10.43 / 10.76 / 13.02 | 10.352 / 10.988 / 11.401 / 13.788 | 10.357 / 11.012 / 11.521 / 14.056 |
| A3 b1 / b2 / b4 / b8 | 0.36 / 0.37 / 0.44 / 0.57 | 9.92 / 10.42 / 10.79 / 12.95 | 10.379 / 11.054 / 11.481 / 13.770 | 10.385 / 11.190 / 11.573 / 13.941 |

G5(채널 D 평균 ≈ 채널 C 평균): 60 lifecycle에서 차이 최대 **0.0076 ms**.

### 관측 7 — 재실행 1건

`A1.r3.L1`(20:08:45 기동)의 첫 시도가 **G1에서 떨어졌다** — client가 받은 content chunk가 **511개**(기대 512)였다. 같은 시도의 G2(`[BUCKET]` 511줄, `request_nums=1`, bucket 1)와 METRICS 파싱은 통과했고 `C_model` p50은 9.51 ms였다. 선등록대로 그 자리에서 1회 재실행해 전 게이트를 통과했고(`C_model` 9.50 ms), **판정에는 재실행 값만 쓴다.** 첫 시도의 파일은 `failed/`에 `.attempt1`로 보존했다.

## 핵심 발견

1. **`stack`** — **동일 구성·동일 명령으로 재compile한 artifact(A3)와 원 artifact(A1)의 공통 bucket `C_model` 차이는 bucket 4개 전부에서 한 세션 안 회차 간 변동의 q95 이내다**(R1, `|Δ|` 0.02–0.05 ms 대 q95 0.06–0.37 ms). 값과 판정은 이 artifact·stack·측정 세션의 것이다.
2. **`stack`** — **격자를 바꾼 재compile(A2)과 A1의 비교는 bucket 8에서 `OUTSIDE`다**(R2, `|Δ|` 0.07 대 q95 0.06 ms, 로그 해상도 한 단위 차이). bucket 1·2·4는 이내다. A2와 A3의 비교는 4/4 이내다. **[TASK55](TASK55.md)가 남긴 bucket 2의 질문에 대해서는 이번 `|Δ(A1,A2)|`(2)가 0.01 ms로 q95 0.141 ms 안이다.**
3. **`stack`** — **한 세션 안 회차 간 변동(같은 artifact·같은 bucket·다른 lifecycle)의 q95는 bucket별로 0.06–0.37 ms로 6배 넘게 다르다.** [TASK55](TASK55.md) P2a가 쓴 밴드 0.03 ms([TASK13](TASK13.md)의 session 안 level 간 범위)는 네 bucket의 q95보다 모두 작다(2–12배).
4. **`stack`** — **같은 명령으로 재compile한 `.rbln` 5개가 바이트 단위로 전부 다르다**(크기는 같음, 컴파일러 `mod_name`이 `fb0c81` → `9937a5`). `rbln_config.json`은 같다. `HF_HUB_OFFLINE=1`이라는 환경 차이 1건이 있어, 바이트 차이의 출처는 이 설계로 가를 수 없다.
5. **`universal`** — **귀무 분위수가 이산 해상도의 소수 값에 걸리면 판정이 해상도 한 단위로 갈릴 수 있다.** bucket 8은 로그가 0.01 ms 단위이고 30쌍 중 4쌍이 최댓값 0.06에 있어 q95 = 최댓값이었으며, R2의 `OUTSIDE` 1건이 그 경계 한 단위 위에서 나왔다. 측정 해상도와 표본 크기의 문제이므로 substrate와 무관하다.

## 해석

지시에 따라 판정 결과에 해석을 붙이지 않는다. 선등록한 해석 한계가 결과에 어떻게 적용되는지만 적는다.

- **표본이 얇다(한계 1).** bucket 8의 q95는 최댓값과 같았고, bucket 1·4의 q95는 극단값 한 개가 만든 쌍들에 걸려 있다(관측 4).
- **집계 단위가 다르다(한계 2).** 판정 통계량은 5회차 중앙값의 차이고 귀무는 단일 lifecycle 쌍의 차다. 선등록에서 계산한 대로 이 규칙은 "구별되지 않음" 쪽으로 관대하다(독립·동일 정규 가정 시 표준편차 비 약 0.54, 시뮬레이션 0.535). 판정 1건(`|Δ(A1,A2)|` bucket 8)은 이 관대한 기준에서도 `OUTSIDE`였다.
- **귀무는 한 세션 안의 변동이다(한계 3).** 날짜 간 변동은 담지 않는다. 관측 5의 [TASK13](TASK13.md)·[TASK55](TASK55.md) 값은 다른 날의 단일 lifecycle이며 이 귀무로 판정하지 않았다.

## 확인되지 않은 사항

- **`HF_HUB_OFFLINE=1`이 compile 결과에 미친 영향** (`UNKNOWN`). `tokenizer_config.json`에 `local_files_only: true`로 흔적이 남았다. `.rbln` 바이트 차이가 이 변수 때문인지, 컴파일러 자체의 비결정성(`mod_name` 차이) 때문인지는 이 설계로 가를 수 없다.
- **A1 시점의 전체 package·환경 변수·kernel** (`UNKNOWN`). 기록이 없다.
- **날짜 간 변동의 크기** (`UNKNOWN`). 이번 귀무는 한 세션(약 76분) 안의 lifecycle 사이다.
- **판정과 같은 집계 단위(5회차 중앙값의 차)의 귀무** (`UNKNOWN`). [TASK50](TASK50.md) 발견 4의 요구를 이번 설계는 충족하지 않는다 — artifact당 회차 5개로는 같은 artifact 안에서 중앙값 차를 만들 수 없다.
- **`A1.r3.L1` 첫 시도에서 chunk가 511개였던 원인** (`UNKNOWN`). decode step은 511로 정상이었다.
- **A3 bucket 4 r1(10.70 ms)과 A3 bucket 1 r4(9.77 ms)가 칸 안 다른 값과 떨어진 원인** (`UNKNOWN`). 조사하지 않았다. 해당 lifecycle의 `smi/` 기록과 서버 로그는 보존돼 있다.

## 실패 / 무효 시도

- **첫 compile 시도가 직전 점검에서 멈췄다.** `pgrep -f "vllm serve"`가 그 문자열을 담은 셸 명령 자신과 일치해 "서버가 떠 있다"로 판정했다. compile은 시작되지 않았고(`compile/` 없음, artifact 없음) 승인된 1회를 쓰지 않았다. 점검을 `pgrep -fc "[v]llm serve"`로 고쳐 같은 RUN 폴더에서 다시 시작했다(19:13:45).
- **`A1.r3.L1` 첫 시도가 G1에서 떨어져 1회 재실행했다**(관측 7). 재실행은 통과했고 무효 lifecycle은 0건이다.

## 연구 원칙에 미치는 영향

1. **귀무 분위수를 판정에 쓸 때는 측정 해상도와 동률 구조를 함께 보고한다.** 분위수가 최댓값과 같거나 해상도 몇 단위에 걸려 있으면 판정 여유가 해상도 한 단위일 수 있다(발견 5).
2. **lifecycle마다 게이트를 즉시 검사하고 그 자리에서 재실행하는 구동이 순서 설계를 지킨다.** 이번 재실행 1건은 선등록 순서의 제자리에서 처리됐다.
3. **process 점검에 `pgrep -f`를 쓸 때는 대괄호 패턴(`[v]llm serve`)으로 자기 일치를 막는다.**

## 다음 작업

제안만 하며 사용자 지시 없이 실행하지 않는다.

1. **판정과 같은 집계 단위의 귀무** — [TASK50](TASK50.md) 발견 4를 충족하려면 artifact당 회차를 늘려(예: 10회차) 같은 artifact 안에서 5회차 중앙값의 차를 만들어야 한다. lifecycle 수가 두 배가 된다.
2. **날짜 간 변동** — 같은 설계를 다른 날 한 번 더 재면 [TASK55](TASK55.md) 관측 4 종류의 변동을 분포로 얻는다.
3. **논문 서술 반영 여부** — [TASK55](TASK55.md) P2 `FAIL`과 이번 R1·R2를 병치할지 결정한다.
4. ~~**A3 artifact(`models/…-mb-rc`, 11.5 GiB)의 보존·삭제 여부**~~ → **보존으로 결정됐다**(사용자 판정, 2026-09-11). 근거: 같은 명령으로 재compile해도 같은 바이트가 나온다는 보장이 없어(이번 재compile에서 `.rbln` 5/5가 달랐다) 지우면 이 artifact를 다시 만들 수 없고, 측정의 증거물이며 심사 단계에서 필요할 수 있다. 판정 재현 자체는 원자료(측정값)로 가능하다. 파일별 SHA256은 「재현 정보」에 옮겨 적었다. 바이트 차이의 출처(컴파일러 비결정 대 `HF_HUB_OFFLINE=1`)는 여전히 `UNKNOWN`이다.
5. **substrate descriptor에 실측 `C(6)`을 반영할지**([TASK55](TASK55.md))는 여전히 미해결 사용자 결정이며, 이번 TASK는 descriptor를 바꾸지 않았다.

## 재현 정보

- 선등록 commit: **`8cd2e92`**, 2026-09-11T19:12:46+09:00. **A3 compile 시작 19:13:45(59초 뒤), 측정 시작 19:22:31(9분 45초 뒤)**
- 측정 종료: 2026-09-11T20:38:39+09:00 (76분 8초, lifecycle 기동 61회)
- Raw artifact: `results/npu/stage2/20260911-191300-recompile-variance/` (gitignored)
  - `precheck.txt`, `compile/`(compile.log, 시각, exit, `rbln_config-rc.json`, diff 2종, `bytes-vs-A1.txt`, 크기 목록, `pip-freeze.txt`, `env-before.txt`, `host.txt`, snapshot 목록, `rbln-smi` 전후, `df`·`du`)
  - `manifest-A3.{txt,sha256}`, `manifest-gate-{before,after}.txt`, `manifest-{before,after}-A{1,2,3}.txt`
  - `order.txt`, `measurement-{start,end}.txt`, `patch-{before,after}.txt`, `rbln-smi-{before,after}.txt`, `disk-after.txt`, `driver.out`, `reruns.txt`, `failed/`(재실행 전 첫 시도)
  - lifecycle별 `server-<TAG>.log`, `probe/decode_cost.<TAG>.json`, `probe-<TAG>.log`, `check-<TAG>.json`, `<TAG>-launch.txt`·`-server-start.txt`·`-server-stop.txt`, `smi/<TAG>.txt`, `done.<TAG>`
  - 판정 산출: `recompile_variance.json` (SHA256 `450fd6a3fa2b2b4e11a7c133e3927015399a447d2fc204d3f2a5f9afedd6f28c`)
- Model artifact: A1 `models/Qwen3-4B-rbln-b8-s8192-d4-mb`(manifest `b4f5cbf1…651f5f`), A2 `…-mb6`(`348f2863…cd24bf`), A3 `…-mb-rc`(`2d73b141…21f1cd`)
- **A3 artifact 파일별 SHA256** (`results/`는 git 미추적이라 여기에 옮긴다. 2026-09-11T20:48 디스크에서 다시 계산한 값이 `manifest-A3.txt`와 byte 동일, manifest `2d73b14143e300846b268f7a5aa8b4c2bd41d4169bf3204d33de30934121f1cd` 일치, 총 12,349,415,920 B):

  | 파일 | 크기 (B) | SHA256 |
  |---|---|---|
  | `chat_template.jinja` | 4,168 | `a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8` |
  | `config.json` | 1,592 | `3833b85a7977a1d0d19c0bebbe62a7e571b54bdfa75a1814508d37a6d6fdda8d` |
  | `decoder_batch_1.rbln` | 841,829,608 | `310c2293a2a201296b805d41e7092dbc5bb349c52a042f248508487b4bd79f7f` |
  | `decoder_batch_2.rbln` | 871,612,781 | `98dd0d314570f8a1f57ded1697b500b92cf058373537f43e6de455c408b99dc9` |
  | `decoder_batch_4.rbln` | 847,605,989 | `5f4f232b42fb52e165c589a06b9015896276f7205898931ead01b3be09d1e6a8` |
  | `decoder_batch_8.rbln` | 877,817,914 | `9e47eb86644c59b08df2b113415cb5e73fd75ad17fe9a016fbfa0ee57936b4e5` |
  | `generation_config.json` | 214 | `81e8e13e77962857509cc06a9960bb68f8b7893096a60357627b2dfaa72d78fe` |
  | `prefill.rbln` | 8,899,037,396 | `3c2fddbcb75b11459ea1ac0f172699c4cde729df2fcf462445b7a1338b7984fe` |
  | `rbln_config.json` | 78,819 | `e855e9b26798b5842d7df9eb513cd53fc6ea61754d62c9ced408d465b89ab898` |
  | `tokenizer_config.json` | 693 | `c4f4c62b741ab2940841480f9942f378d7d3878d47c2babb862af7381c59b952` |
  | `tokenizer.json` | 11,422,650 | `be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506` |

- probe 설정: `--prompt-file experiments/npu/stage1/prompt.txt --max-tokens 512 --seed 20260819`, server는 prefix caching flag 없음
- 예산 사용: compile **1/1**(343 s), serving lifecycle **61회**(60 + 재실행 1), `models/` +11 GiB(86 → 97 GiB)
- 측정 후 device 상태: 32 ID 전부 `0.0B / 15.7GiB`, 잔여 context 없음, 누수 server 없음, port 8000 비어 있음
