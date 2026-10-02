# GPU multi-turn 파일럿 — 선등록

작성: 2026-09-29, GPU 지시문 G-03 작업 D ([GTASK09](GTASK09.md) 선등록, 파일럿 결과는 GTASK10).

**측정 전 상태**
- 이 문서를 commit하기 전에는 파일럿 측정을 한 건도 하지 않았다.
- 본 실험 예측([GPU_MULTITURN_PREREG.md](GPU_MULTITURN_PREREG.md))은 이 문서와 같은 commit에 들어가며, 파일럿보다 먼저 계산됐다.
- 파일럿 전에 한 것은 **계기 점검 lifecycle 2개**뿐이다(`results/gpu/multiturn/instrument_check/`). 별도 plan `gcheck-n3`(seed 20262900, N=3, gap U(0.2,1.0) s, 평가 20 s)로 runner와 측정 모듈을 점검했고, 그 값은 어디에도 쓰지 않는다. 이 점검에서 측정 모듈의 id join 오류를 고쳤다(GTASK09 기록).

## 목적 (G-03 §6)

- (a) runner 동작: token id prompt, 세션 갱신, 구간, uuid·preemption 검사
- (b) streaming 관찰자 효과(GPU에서 따로 확인)
- (c) run 간 산포 추정

## 격자

- **N = 22**(확증 N의 가운데)
- 구성: **BASE**(pool 1,900, (1,2,4,8,16)), **POOL**(pool 2,300, (1,2,4,8,16)), `max_num_seqs` 8, budget 2,048(GTASK08)
- 모드: streaming · non-streaming
- replicate 3 → **12 lifecycle**
- plan: `experiments/gpu/multiturn/plans/pilot/gpilot-n22-r{0,1,2}.json`
  - seed `20262500 + r`로, 본 실험·선정과 겹치지 않는다.
  - `cycle_s`는 해석 모형 POOL 예측이다.
  - 같은 replicate의 네 lifecycle은 같은 plan을 쓴다(짝 설계).
  - 내용·파일 SHA256은 `plans/pilot/INDEX.json`에 있다(이 commit).
- 순서(고정, `plans/pilot/SCHEDULE.json`)는 NPU TASK79와 같은 교대 순서다.
  - r0: BASE-ns, BASE-st, POOL-st, POOL-ns
  - r1: POOL-ns, POOL-st, BASE-st, BASE-ns
  - r2: BASE-st, BASE-ns, POOL-ns, POOL-st
- lifecycle마다 server를 새로 띄운다(`run_schedule.py` → `gpu_mt_runner.py`).
  - 관측 patch와 KV events는 켠다.
  - 평가 구간은 120 s다.
  - 카드 uuid `GPU-4485e769…`만 쓴다.

## 지표

- **turn당 A′-GPU device time**(`gpu_mt_measure.py`, [GPU_MULTITURN_DESIGN.md](GPU_MULTITURN_DESIGN.md) §5)
  - server 창 안 `[GSTEP]` step마다 GTASK05 비용 모형으로 가격을 매긴다.
  - 하한(`lo`)·상한(`hi`) 두 값을 쓴다.
- **짝 ratio**: 같은 (구성, replicate)의 streaming / non-streaming, 6개

## 판정 기준 (원칙 17, NPU TASK79와 같은 형식)

- 중앙 ratio = 6개 짝 ratio의 중앙값이다.
- 95 % percentile bootstrap CI는 짝을 복원 추출(10,000회, seed `20262510`)해 구한다.
- **CI 폭 상한 0.04**. 근거는 NPU 파일럿과 같다. 가르려는 구성 효과가 이 부하에서 2–5 %(GTASK08)이므로, 관찰자 효과가 ±1 %를 넘지 않아야 한다.
- **`EQUIVALENT` ⇔ `lo`와 `hi` 두 bound 모두에서 CI가 1을 포함하고 폭 ≤ 0.04** → 본 실험 streaming
- 그 밖(`NOT_EQUIVALENT`) → 본 실험 non-streaming + streaming 보조 run
- 보고만 하는 항목
  - 직접 dispatch 채널의 짝 ratio와 CI(탐색 채널)
  - 짝별 재사용 수 차
  - h(n) TVD
  - 처리량 비
- **사전 예측**: `EQUIVALENT`, 중앙 ratio 0.995–1.005
  - 근거: A′-GPU는 step 모양에 가격을 매기므로 host 부하가 step 모양(h)을 바꾸지 않는 한 움직이지 않는다.
  - 직접 채널은 host 부하에 더 민감할 수 있다. async scheduling의 CPU 쪽 dispatch가 늦어질 수 있기 때문이다.

## run 간 산포 (보고, 판정 아님)

- 모드별 replicate 3개의 POOL/BASE 짝 ratio(A′-GPU `lo`)와 그 범위를 보고한다. 본 실험 CI 폭을 가늠하는 값이다.
- 예측(시뮬레이터 LRU, 선정 plan 기준): N=22 POOL/BASE 약 0.99로, 효과가 산포와 같은 자릿수일 것이다.

## runner 동작 확인 (판정과 별개, 전건 기록)

- lifecycle마다 다음을 확인한다.
  - runner 유효(`windows.json` `valid`): `stopped_by = window`, 고갈 slot 0, 카드 uuid 일치, `vllm:num_preemptions_total` 증분 0, GPU 외부 process 없음
  - 구간 온라인 = 사후 재계산, 평가 끝 이후 발행 0, HTTP 오류 0, 생성 id 수 = 요청 값
  - client–server join 누락 0, step mode 예측 불일치 수, client·server `cached` 불일치 수
- 하나라도 어긋나면 그 lifecycle은 `INVALID`다. 재실행하지 않고 남은 짝으로 판정하며, 그 사실을 적는다.

## 파일럿 데이터 사용 제한

- 파일럿 측정값으로 모형·시뮬레이터 파라미터와 본 실험 예측을 바꾸지 않는다.
- streaming 결정, runner 동작 확인, 산포 추정에만 쓴다.

## 실행 절차

```bash
setsid nohup env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python \
  experiments/gpu/multiturn/run_schedule.py \
  --schedule <abs>/experiments/gpu/multiturn/plans/pilot/SCHEDULE.json \
  --run-dir <abs>/results/gpu/multiturn/pilot/<UTC> &
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/pilot_analyze.py \
  --run-dir <RUN> --out <RUN>/pilot_verdict.json
```

- 실행 전 GPU가 비어 있고 patch 상태가 `patched`(`d75d04d8…`)인지 확인한다.
- 실행 중 script를 편집하지 않는다.

## 개정 이력

- 2026-09-29 초판 (측정 전)
