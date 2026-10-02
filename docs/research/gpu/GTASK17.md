# GTASK17 — 운영 조건 step 비용 재측정 (요인 분해)

## 상태

DONE

## 날짜

2026-10-01(측정), 2026-10-02(기록, G-07 §1 승인)

## 목적

GPU 지시문 G-06 작업 A. FULL decode step 비용을 streaming × KV events × admission log 2³ 조건에서 다시 재서, GTASK15의 운영 초과(약 22 %, 요청당 약 0.35 ms)의 출처와 관찰자 효과 여부를 가린다. **파라미터 측정이며 판정은 없다.**

## 배경

- [GTASK15](GTASK15.md): 운영 부하(GTASK11)의 FULL decode step은 GTASK05 가격보다 d = 1에서 1.03배, d = 8에서 1.22배 길었다. 후보로 streaming 출력, KV events, 관측 log를 들었으나 확인하지 않았다.
- 설계: [GPU_STEPCOST_OP_PREREG.md](GPU_STEPCOST_OP_PREREG.md)

## 시작 상태

- HEAD `b59287c`(설계 선등록 commit), branch `gpu-a6000`

## 수행 내용

1. 설계와 측정·분석 코드를 측정 전에 commit했다(`b59287c`).
2. `run_stepcost_op.sh`를 세션과 분리해 실행했다(2026-10-01 07:32:42–08:08:00 UTC). 16 lifecycle 모두 유효였고 재실행은 0이었다.
3. **자동 commit 실패(경위)**:
   - driver는 분석 뒤 `op_result/{summary.json, summary.md, sequence.log}` 세 파일을 `git add … && git commit …`으로 commit하도록 짜여 있었다.
   - `sequence.log`는 `.gitignore`의 `*.log`에 걸린다. 그래서 `git add`가 "The following paths are ignored" 오류로 실패했다(나머지 두 파일은 stage됨). `&&` 때문에 `git commit`은 실행되지 않았다.
   - log의 `commit rc=0 b59287c`는 잘못된 보고다. `rc=$?`는 git 명령이 아니라 그 앞 줄의 종료 코드를 읽었고, 표시된 hash는 움직이지 않은 HEAD(선등록 commit)였다.
   - 다음 세션(2026-10-02)에서 HEAD가 `b59287c` 그대로이고 두 요약이 stage만 된 상태임을 확인했다.
4. driver를 고쳤다. `sequence.log`는 stage하지 않는다. git 명령의 종료 코드를 직접 받는다. HEAD가 움직이지 않으면 `rc=99`로 실패를 보고한다. 요약 두 파일(stage 이후 수정 없음, 기계 생성 그대로)은 이 기록과 같은 commit에 넣는다. `sequence.log`는 run dir 원본으로만 남긴다.

## 변경된 파일

- `experiments/gpu/stepcost/op_result/summary.json`, `summary.md`(기계 생성, 측정 직후 내용 그대로)
- `experiments/gpu/stepcost/run_stepcost_op.sh`(자동 commit 버그 수정)
- `docs/research/gpu/GTASK17.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
setsid nohup experiments/gpu/stepcost/run_stepcost_op.sh <abs>/results/gpu/stepcost_op/20261001T0732Z \
  > <abs>/results/gpu/stepcost_op/20261001T0732Z/driver.log 2>&1 &
```

- Population: 8 조건 × r0·r1 = 16 lifecycle. 조건마다 n = 1–8, n마다 3 batch × n 요청(prompt 64 token random id, 생성 256, `ignore_eos`)
- Unit: ms, 연속 두 `[GSTEP]`(`maxq = 1, reqs = n, mode FULL`)의 dispatch 간격. batch마다 앞뒤 3개를 버린다.
- Source: server `[GSTEP]`(v2 runner, `ESCAPEMENT_OBS=1`), Prometheus delta
- Device: A6000 uuid `4485e769…`, server 인자 GTASK11 BASE(`--num-gpu-blocks-override 1900`, `--max-num-seqs 8`, `--max-num-batched-tokens 2048`, capture `[1,2,4,8,16]`)
- **context 길이**: 요청마다 64 + 생성 0–256 token(64–320). 짧은 context다.

## 결과

조건 곡선(ms, 두 lifecycle 중앙값):

| 조건 | n=1 | n=2 | n=3 | n=4 | n=5 | n=6 | n=7 | n=8 | 기울기 ms/요청 |
|---|---|---|---|---|---|---|---|---|---|
| s0k0a0 | 13.436 | 13.315 | 13.357 | 13.414 | 13.563 | 13.660 | 13.709 | 13.756 | 0.0627 |
| s0k0a1 | 13.440 | 13.313 | 13.357 | 13.414 | 13.561 | 13.659 | 13.703 | 13.754 | 0.0619 |
| s0k1a0 | 13.440 | 13.315 | 13.357 | 13.411 | 13.560 | 13.656 | 13.704 | 13.752 | 0.0616 |
| s0k1a1 | 13.438 | 13.314 | 13.359 | 13.413 | 13.563 | 13.659 | 13.702 | 13.750 | 0.0616 |
| s1k0a0 | 13.442 | 13.319 | 13.360 | 13.411 | 13.557 | 13.654 | 13.705 | 13.751 | 0.0610 |
| s1k0a1 | 13.438 | 13.318 | 13.359 | 13.415 | 13.564 | 13.657 | 13.709 | 13.751 | 0.0619 |
| s1k1a0 | 13.439 | 13.315 | 13.356 | 13.414 | 13.562 | 13.653 | 13.701 | 13.749 | 0.0612 |
| **s1k1a1**(GTASK11 조건) | 13.425 | 13.313 | 13.354 | 13.407 | 13.558 | 13.651 | 13.696 | 13.740 | 0.0615 |
| GTASK05 가격 | 13.407 | 13.285 | 13.311 | 13.352 | 13.498 | 13.538 | 13.579 | 13.619 | (`g` 0.041) |

- 재현성: 같은 조건 두 lifecycle의 차이는 최대 0.019 ms(0.14 %)다.
- 요인 효과(log step 시간 2³ 분석, n 평균 비): stream 0.9999, kv 0.9998, admlog 0.9999, 2요인 상호작용 0.9999–0.9999, 3요인 0.9998. n별로도 0.9996–1.0002 범위다.

GTASK11 조건 재현:

| | n=1 | n=2 | n=3 | n=4 | n=5 | n=6 | n=7 | n=8 |
|---|---|---|---|---|---|---|---|---|
| `s1k1a1` / 가격 | 1.001 | 1.002 | 1.003 | 1.004 | 1.004 | 1.008 | 1.009 | 1.009 |
| GTASK15 운영 비율 | 1.034 | 1.064 | 1.100 | 1.123 | 1.147 | 1.172 | 1.227 | 1.219 |

## 핵심 발견

1. **`stack`** — **관측 수단에 의한 관찰자 효과는 없다.** KV events와 admission log의 주효과는 비 0.9998·0.9999로, 보고 규칙(비 ≥ 1.02이고 반복 간 차이보다 큼)에 한참 못 미친다. streaming도 0.9999다. GTASK11 이후 GPU 기록이 관측 수단 때문에 왜곡되지 않았다는 근거다.
2. **`stack`** — **GTASK11 조건(`s1k1a1`)의 통제 부하 step은 가격과 같다**(n = 8에서 1.009, 운영 1.219). 기울기 0.0615 ms/요청은 가격 `g` 0.041보다 조금 크지만, GTASK15 추정 약 0.35와는 자릿수가 다르다. 따라서 **22 % 초과는 이 세 요인에서 오지 않는다.** 이 부하에 없는 운영 부하의 특성에서 온다.
3. **`stack`** — 사전 예상("n = 8에서 약 1.2, 가장 큰 요인은 streaming, 다음은 KV events")은 **빗나갔다.** 세 요인 모두 효과가 없었다.

## 해석

- 통제 부하와 운영 부하의 차이 중 이 측정이 고정하지 않은 것: (1) 요청당 context 길이(이 부하 64–320 token, multi-turn은 훨씬 김), (2) prefill 혼합 step과 잦은 admission, (3) prefix cache hit와 block 할당 패턴. 어느 것이 원인인지는 이 측정으로 알 수 없다(가설).
- NPU [TASK92](../TASK92.md)의 관찰(짧은 context는 통제와 같고 긴 context에서 1.03–1.15배)은 (1)을 가리킨다. G-07 작업 B에서 잰다.

## 확인되지 않은 사항

- 22 % 초과의 실제 원인
- admission log 효과의 상한(이 부하는 admission이 batch 시작에만 있다. 설계 §5 한계)

## 실패 / 무효 시도

- 자동 local commit 실패(수행 내용 3). 측정 자체는 유효했다.

## 연구 원칙에 미치는 영향

- 자동 commit driver는 git 명령의 종료 코드와 HEAD 이동을 직접 확인해야 한다. 로그의 `rc`만 믿지 않는다.

## 다음 작업

- G-07 작업 B(context 길이 step 비용), 작업 C(붕괴 영역 blind)

## 재현 정보

- **선등록 commit `b59287c93b067f7d67902a1506f6f11616ff560c`(2026-10-01 07:32:42 UTC) → 측정 시작 07:32:42 UTC**. 같은 초이나 driver가 시작 시 기록한 `start_commit.txt`가 `b59287c`이므로 commit이 먼저다.
- run dir(비추적): `results/gpu/stepcost_op/20261001T0732Z/`(`sequence.log`, `driver.log`, lifecycle별 `summary.json`, `analyze.stdout`)
- 분석: `experiments/gpu/stepcost/stepcost_op_analyze.py`(측정 전 commit), 순서표 `op_order.json`(seed 20262700)
- 환경: venv `/home/csdc/kyeom/envs/vllm-0.22.0`, `vllm 0.22.0`, `Qwen/Qwen3-4B@1cfa9a72…`
