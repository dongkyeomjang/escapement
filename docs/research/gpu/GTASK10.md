# GTASK10 — GPU multi-turn 파일럿: runner 동작, streaming 관찰자 효과, run 간 산포

## 상태

DONE

## 날짜

2026-09-29

## 목적

GPU 지시문 G-03 작업 D. 선등록 [GPU_MT_PILOT_PREREG.md](GPU_MT_PILOT_PREREG.md)(`2bef619`)대로 N=22, BASE·POOL × streaming·non-streaming × replicate 3 = 12 lifecycle을 측정해 다음을 확인한다.
- (a) runner 동작
- (b) streaming 관찰자 효과
- (c) run 간 산포

## 배경

- [GTASK09](GTASK09.md): 선등록, 예측
- NPU [TASK79](../TASK79.md): 같은 형식의 파일럿. NPU 판정은 `EQUIVALENT`였다.

## 시작 상태

- HEAD `2bef619`(GTASK09 선등록 commit, 2026-09-29 17:54:17 UTC)
- GPU 비어 있음, patch `patched`, 카드 uuid `4485e769…`

## 수행 내용

1. `run_schedule.py`를 세션과 분리해 실행했다(`setsid nohup`). 선등록 순서 그대로 12 lifecycle을 돌렸고 재실행은 0이다.
2. `pilot_analyze.py`로 판정했다.

## 변경된 파일

- `docs/research/gpu/GTASK10.md` (신규), `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
setsid nohup env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/run_schedule.py \
  --schedule <abs>/experiments/gpu/multiturn/plans/pilot/SCHEDULE.json \
  --run-dir <abs>/results/gpu/multiturn/pilot/20260929T1754Z &
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/pilot_analyze.py \
  --run-dir <RUN> --out <RUN>/pilot_verdict.json
```

- `requested_condition`: N=22, BASE(pool 1,900)·POOL(pool 2,300), `max_num_seqs` 8, 격자 (1,2,4,8,16), streaming·non-streaming, r0–r2, 평가 120 s
- `observed_condition`: 12/12 lifecycle 유효, 평가 구간 요청 330–379개
- `condition_reached`: `YES`

Population: lifecycle 12개, 평가 구간 요청 합 4,173개.
Source: client 행, server `[GSTEP]`·`[GPFX]`, `/metrics`, `lifecycle.json`.
Device scope: GPU 1장(uuid `4485e769…`).

## 결과

### runner 동작 (12/12 전부)

| 검사 | 결과 |
|---|---|
| runner 유효(`stopped_by = window`, 고갈 slot 0, uuid 일치, 외부 GPU process 없음) | 12/12 |
| `vllm:num_preemptions_total` 증분 | 0 (12/12) |
| 구간: 온라인 = 사후 재계산 | 12/12 |
| 평가 끝 이후 발행 / HTTP 오류 / 생성 id 수 불일치 | 0 / 0 / 0 |
| client–server join 누락 | 0 |
| **step mode 예측 불일치**(비용 모형 대 `[GSTEP]`) | **0** (전 lifecycle) |
| client·server `cached` 불일치 | 0 |
| `cached` 출처 | client 226–298, 부재 = 0(flag 확인) 74–104 per lifecycle |
| warm-up 끝 | r0 30–32 s, r1 35–36 s, **r2 74–75 s**(gap 꼬리) |
| lifecycle 시간 | **3분 13초 – 4분 0초** |

### streaming 관찰자 효과 (판정)

| 채널 | 중앙 ratio | 95 % CI | 폭 | 판정 |
|---|---|---|---|---|
| A′-GPU `lo` | 1.0066 | [0.9942, 1.0094] | 0.0152 | EQUIVALENT |
| A′-GPU `hi` | 1.0066 | [0.9942, 1.0091] | 0.0149 | EQUIVALENT |
| 직접 dispatch(보고) | 1.0053 | [0.9937, 1.0105] | 0.0168 | EQUIVALENT |

**판정 `EQUIVALENT` → 본 실험 streaming.**

| 짝 | ratio lo | 재사용 st / ns | h TVD | 처리량 비 |
|---|---|---|---|---|
| BASE r0 | 1.0057 | 231/287 / 226/286 | 0.009 | 1.003 |
| BASE r1 | 1.0109 | 257/298 / 251/299 | 0.054 | 0.997 |
| BASE r2 | 1.0075 | 277/322 / 280/323 | 0.015 | 1.000 |
| POOL r0 | 0.9926 | 272/301 / 274/302 | 0.021 | 0.997 |
| POOL r1 | 0.9957 | 268/305 / 268/306 | 0.037 | 1.003 |
| POOL r2 | 1.0079 | 295/329 / 298/331 | 0.016 | 0.992 |

### run 간 산포 (보고)

| 모드 | POOL/BASE (A′-GPU lo) r0, r1, r2 | 범위 |
|---|---|---|
| streaming | 0.950, 0.969, 0.988 | 0.038 |
| non-streaming | 0.963, 0.984, 0.988 | 0.025 |

### 관측값 (보고만, 예측과 plan이 달라 판정하지 않음)

- BASE 재사용: 0.79–0.87(lifecycle별)
- POOL 재사용: 0.87–0.91
- 부분 hit: BASE 0.7–4.7 %, POOL 0.3–1.5 %
- A′-GPU: 262–291 ms/turn
- 직접 dispatch 채널: 가격 채널보다 10–13 % 높다(300–327 ms/turn).

## 핵심 발견

1. **`stack`** — **GPU에서도 streaming의 관찰자 효과는 turn당 device time에서 동치 밴드 안이다**(중앙 1.0066, CI 폭 0.015).
   - BASE 짝 3개는 모두 1보다 컸다(+0.6 ~ +1.1 %). 효과가 있다면 이 크기 이하다.
   - 값은 이 host·stack의 것이다.
2. **`stack`** — **GPU 비용 모형의 step mode 판정이 실측 `[GSTEP]` mode와 12 lifecycle 전 step에서 일치했다.** GTASK05 격자 규칙(FULL / PIECEWISE / eager의 token 수 경계)이 multi-turn 부하에서도 그대로 성립한다.
3. **`stack`** — **직접 dispatch 채널은 가격 채널(A′-GPU)보다 10–13 % 높다.**
   - 원인 후보는 두 가지이며 확인하지 않았다(가설).
     - 가격 모형의 eager 증분 하한·상한이 small-p eager step의 CPU 지연(GTASK05 발견 3)을 다 담지 못한다.
     - dispatch 간격에 idle 조각이 섞인다.
   - 구성 간 비는 두 채널에서 거의 같았다(짝 ratio 차 ≤ 0.005).

## 해석

- 본 실험은 streaming으로 한다. W 대응 간섭은 `[GSTEP]`에서 재므로 streaming이 필수는 아니지만, turn ≥ 1 TTFT를 얻는다.
- run 간 산포(범위 0.025–0.038)는 예측 구성 효과(POOL/BASE 1–4 %)와 같은 자릿수다. 비용 비 항목(선등록 §5.2)은 N=20·22에서 `NOT_INFORMATIVE`일 가능성이 크다는 사전 예측과 맞는다.
- 관측 lifecycle 시간(3.2–4.0분)으로 본 실험 45 lifecycle은 **약 2.5–3 h**다. 선등록 추정 3.5–4 h보다 짧다.

## 확인되지 않은 사항

- 직접 채널과 가격 채널 차이의 원인
- r2의 긴 warm-up(74 s)이 본 실험 plan에서도 나타나는지. warm-up 규칙상 문제는 없다.

## 실패 / 무효 시도

없음. 무효 lifecycle 0, 재실행 0.

## 연구 원칙에 미치는 영향

- 세션과 분리한 실행(`setsid nohup` + 완료 표시 파일)으로 장시간 측정이 제어 세션의 연결에 의존하지 않게 했다.

## 다음 작업

- Advisor 검토(G-03 §9 보고) → G-04에서 본 측정
- **파일럿 측정값은 예측과 판정 기준에 쓰지 않는다.**

## 재현 정보

- **선등록 commit `2bef619850953295caafd57f5b900deddc8bdc6c`(17:54:17 UTC) → 측정 시작 17:54:24 UTC → 종료 18:36:31 UTC**
- raw: `results/gpu/multiturn/pilot/20260929T1754Z/`(비추적)
  - `{BASE,POOL}.{stream,nostream}.r{0,1,2}/`(`requests.jsonl`, `token_ids.jsonl.gz`, `windows.json`, `provenance.json`, `server.log`, `kv_events.jsonl`, `lifecycle.json`, `env.txt`)
  - `sequence.log`, `pilot_verdict.json`
- 환경: `vllm 0.22.0`, driver 580.178.04, `Qwen/Qwen3-4B@1cfa9a72…`, patch `d75d04d8…`, 카드 uuid `GPU-4485e769-430a-430d-3383-b9c4ce92a175`
