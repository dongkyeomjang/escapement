# TASK116 — 독립 step 시간 계측 patch와 지시문(2026-10-08) 작업 A·B·C·E 선등록

## 상태

DONE

## 날짜

2026-10-08

## 목적

Advisor 지시문(2026-10-08, "독립 시간 계측, 대기시간 민감도, 동일 자원 구성 선택")의 측정 전 단계: 비용 함수와 독립인 step 실행 시간 채널(DIRECT_EXEC)을 만드는 observation-only patch, 입력 manifest, plan·순서표·예측·판정 기준·판정 스크립트를 측정 전에 commit한다. **측정 0**(smoke 1 lifecycle은 개발 확인이며 판정에 쓰지 않음).

## 배경

- [결정 13](INDEX.md#결정-13--지시문-12-결정-시뮬레이터-위치와-통합) — 통합 시뮬레이터 + context decode 비용, 운영 prefill 미채택. 이번 지시문이 측정을 다시 연다.
- [TASK102](TASK102.md) — N18 TUNED 0.671(최대 절감 후보), [TASK110](TASK110.md) — 비용 모형 없는 활동 시간 비(대리값), [TASK111](TASK111.md) — 경계 보정, [TASK87](TASK87.md) — N14, [TASK81](TASK81.md) — DP_N8 artifact.
- [TASK12](TASK12.md) — `[BUCKET]` patch(patch 정책 첫 적용).

## 시작 상태

- HEAD `40d2c75`, `?? .idea/`만. 장치 rbln0–3 비어 있음. `[BUCKET]` patch `patched`, dummy-lifecycle patch `pristine`.

## 수행 내용

1. **계측 범위 확인(코드)**: 기존 `VLLM_RBLN_METRICS=1`은 호출별 forward·sampler `perf_counter`를 재지만 run 끝 평균만 남기고, server 로그 timestamp는 초 단위다. `rebel.capture_reports()` device 시간은 `RBLN_RUNTIME_TIMER=1`일 때만 생긴다. runtime은 `PyRblnSyncRuntime.run()`(동기)이라 호출 반환 = 완료다. RECON(A′) decode 비용은 model span p50 + sampler p50 + engine overhead 회귀(종단 ITL)다.
2. **patch `steptime`**(`patches/vllm_rbln-0.11.1/steptime_observe.patch`, `apply_steptime.sh`, `STEPTIME.md`): `optimum_model_runner.py`에 추가 줄만, `CONTINUUM_OBS_STEPTIME=1`일 때 step당 `[STEPTIME]` 1줄(6개 시각, phase, 요청 수, 계산·재사용 token, 요청 id). 사용자 승인 후 사용자가 sudo로 적용(적용 전 `365ba136…` → 후 `bd93cc04…`).
3. smoke(개발): TUNED N6 30 s, 귀속 누락 0, decode 1,905 step 전부 `[BUCKET]`과 짝, step 사이 간격 중앙 0.49 ms.
4. plan 50개(`make_dx_plans.py`, 새 seed 20268xxx), 순서표 5개, PRED(`dx_predict.py`), C 대기 통계, E 선택, 판정 스크립트, manifest. 선등록 문서 [DX_PREREG.md](DX_PREREG.md).
5. 진행 중 발견·수정(측정 전): (i) session seed가 `plan_id`에서 파생되므로 C의 두 상한 plan이 같은 내부 `plan_id`를 쓰도록 고침(처음 생성분은 폐기, 측정 전). (ii) 직렬 plan 생성이 plan당 약 2.5 분이라 cycle 계산만 병렬화(규칙 불변). (iii) `pkill -f`가 자기 셸을 죽인 함정(KNOWN_PITFALLS 2) — 이후 PID로만 종료. (iv) commit 전 `git diff --check`가 patch의 빈 context 줄(공백 1칸)·EOF 빈 줄을 지적해 빈 줄로 바꾸고 마지막 hunk의 context를 앞뒤 2줄로 줄였다(fuzz 0). 적용·역적용 결과 hash는 그대로(`365ba136…` ↔ `bd93cc04…`)이고, 설치된 파일(바꾸기 전 patch로 적용)은 의도한 patched 파일과 byte 동일하며, 새 patch로 역적용 dry-run이 통과한다.

## 변경된 파일

- `patches/vllm_rbln-0.11.1/{steptime_observe.patch, apply_steptime.sh, STEPTIME.md}`
- `experiments/npu/stage3/{make_dx_plans.py, make_dx_order.py, dx_predict.py, dx_steps.py, dx_check.py, dx_analyze.py, dx_manifest.py, run_dx.sh, run_dx_lifecycle.sh}`, `experiments/npu/stage3/plans/dx/*`
- `docs/research/DX_PREREG.md`, `docs/research/dx/INPUT_MANIFEST.json`, `docs/research/TASK116.md`, `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
bash patches/vllm_rbln-0.11.1/apply_steptime.sh status
cd experiments/npu/stage3
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 make_dx_plans.py --workers 56
env -u PYTHONPATH python3 make_dx_order.py
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 dx_predict.py --workers 48 --output plans/dx/PREDICTIONS_DX.json
env -u PYTHONPATH python3 dx_manifest.py
```

## 결과

- PRED(측정 전): B N18 `R` median 0.6774, N8 0.9838; C cap60 TUNED/BASE 0.7869, cap120 0.8275, BASE 재사용 0.301 → 0.407; E TUNED 0.9696 < BATCHONLY 1 < DP_N8 1.0225 → **선택 TUNED**.
- 예측 경로 재현: 같은 코드로 TASK101 plan을 돌려 `sim_ctx` 6 cell이 차이 0으로 일치.
- C 대기: 상한 60 s가 잘라내는 대기는 2.63 %이지만 원래 대기 합의 37.8 %(120 s: 1.42 %, 21.1 %).

## 핵심 발견

- `[stack]` 이 serving 경로에서 step 실행 시간은 기존 관측 채널(초 단위 로그, run 끝 평균)로는 step별로 얻을 수 없었고, 동기 runtime 덕에 반환 시각만으로 완료 기반 계측이 된다.
- `[class]` 대기시간 상한의 영향은 잘린 표본 비율(2.6 %)이 아니라 잘린 대기 합(38 %)으로 봐야 한다 — 꼬리가 무거운 분포의 일반적 성질이며, 값은 이 trace의 인스턴스 값이다.

## 해석

- 없음(측정 전).

## 확인되지 않은 사항

- 계측 영향(작업 A에서 측정), HW_ACTIVE(측정 안 함).

## 실패 / 무효 시도

- C plan 첫 생성분(상한별 다른 내부 `plan_id`) — 측정 전 폐기.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- [DX_PREREG.md](DX_PREREG.md) 순서대로 A → B → C → (B 확장, E) 측정과 판정(TASK117).

## 재현 정보

- 이 TASK의 commit이 선등록이다. 측정 시작은 그 뒤(TASK117에 시각 기록). package: vllm 0.22.0+cpu, vllm-rbln 0.11.1(`[BUCKET]`·`steptime` patch), rebel-compiler 0.11.1.post1, Qwen3-4B artifact 4종(새 compile 없음), device RBLN CA25 rbln0–3.
