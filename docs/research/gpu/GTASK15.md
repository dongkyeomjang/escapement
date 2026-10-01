# GTASK15 — 직접 dispatch 채널과 가격 채널 차이의 분해

## 상태

DONE

## 날짜

2026-10-01

## 목적

GPU 지시문 G-05 작업 D. **보고만 한다.**
- 직접 dispatch 채널이 가격 채널보다 약 13 % 높은 원인을 기존 `[GSTEP]` log로 가른다.
- 후보: (a) small-p eager step의 CPU 지연(GTASK05 발견 3), (b) dispatch 간격에 섞인 idle 조각
- step mode별, 요청 수별로 분해한다.

## 배경

- [GTASK05](GTASK05.md): `[GSTEP]`은 dispatch(CPU) 시각이다. lag `L = 1`, small-p eager의 lag 1 귀속 부족
- [GTASK10](GTASK10.md)·[GTASK11](GTASK11.md): 직접/가격 lifecycle 중앙 1.131(0.973–1.156). 직접 채널 정의 = 창 step마다 `min(다음 dispatch까지 간격, 2·price_hi + 5 ms)`

## 시작 상태

- HEAD `3ddbba8`

## 수행 내용

1. `obs_dynamics.py`의 창 step 기록(55 lifecycle, step 354,083개)을 썼다. 각 step의 기록은 mode, `reqs`, decoder `d`·prefill `p`(가격 채널 규칙), 가격, dispatch 간격이다.
2. `channel_report.py`로 두 귀속을 비교했다.
   - **lag 0**(GTASK11 직접 채널): step k의 시간 = dispatch k → k+1 간격, cap 적용
   - **lag 1**: step k의 시간 = dispatch k+1 → k+2 간격. async scheduling(batch queue 2)은 한 step 앞서 dispatch하므로 GPU가 step k를 실행하는 시간은 그다음 간격에 나타난다.
   - **초과분** = 귀속 시간 − 가격(`lo`). 계급별·decode 폭별·대기열 길이별로 나눴다.
   - **idle 조각** = lag 1 간격이 cap을 넘는 부분

## 변경된 파일

- `experiments/gpu/multiturn/channel_report.py`(신규)
- `docs/research/gpu/GTASK15.md`, `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

```bash
D=<abs>/results/gpu/multiturn/main/20260930T1411Z/dynamics
python3 experiments/gpu/multiturn/channel_report.py --obs $D/obs.json --out $D/channel_report.json
```

- Population: 55 lifecycle 창 step 중 다음·다다음 dispatch가 있는 것
- Source: server `[GSTEP]` `t`(perf_counter, dispatch 시각)
- Unit: ms, 가격 대비 비
- Device scope: GTASK11 카드 1장

## 결과

### 두 귀속의 합계 (55 lifecycle 합산; 괄호는 lifecycle 중앙)

| | 합 / 가격 |
|---|---|
| lag 0, cap 적용(GTASK11 직접 채널) | 1.116 (1.131) |
| **lag 1** (cap 적용 여부 무관) | **1.210** (1.211) |

- lag 1에서 cap을 넘는 간격은 **4개, 합 3.3 ms**다. 초과분의 0.0003 %에 해당한다. 창 안에서 engine은 사실상 쉬지 않았다.

### 계급별 (lag 1)

| 계급 | step 수 | 가격 합 (s) | lag 1 / 가격 | lag 0 cap / 가격 | lag 1 초과분 비중 |
|---|---|---|---|---|---|
| **FULL decode** | 334,576 | 4,551 | **1.224** | 1.238 | **89.4 %** |
| eager 혼합 p ≤ 128 | 12,129 | 164 | 1.334 | 1.416 | 4.8 % |
| eager 혼합 p > 1024 | 4,949 | 613 | 1.081 | **0.181** | 4.3 % |
| PIECEWISE 혼합 | 948 | 13 | 1.500 | 1.179 | 0.6 % |
| eager 혼합 p ≤ 256 / ≤ 512 / ≤ 1024 | 238 / 326 / 917 | 5 / 11 / 69 | 1.53 / 1.42 / 1.04 | 2.24 / 1.93 / 0.43 | 0.2 / 0.4 / 0.2 % |

### FULL decode: decode 폭별·대기열 길이별 (lag 1 / 가격 중앙)

| decode 폭 d | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 비 | 1.034 | 1.064 | 1.100 | 1.123 | 1.147 | 1.172 | 1.227 | 1.219 |
| step 수 | 18 | 95 | 885 | 3,250 | 6,847 | 12,678 | 33,488 | 277,315 |

- 대기열 길이별로는 거의 평평하다. 대기 0에서 1.193, 대기 1–12에서 1.215–1.224다.

## 핵심 발견

1. **`stack`** — **두 후보 모두 주원인이 아니다.**
   - (a) small-p eager CPU 지연은 lag 1 초과분의 4.8 %다.
   - (b) idle 조각은 0.0003 %다.
   - **초과분의 89 %는 FULL decode step 자체가 GTASK05 가격보다 22 % 긴 데서 나온다**(16.5 ms 대 13.3–13.6 ms).
2. **`stack`** — **FULL decode의 초과는 decode 폭에 비례해 커지고 대기열 길이와는 무관하다.** d = 1에서 1.03, d = 8에서 1.22이며, 요청당 약 0.35 ms다(가설: (1.22 − 1.03) × 13.3 ms / 7). per-request CPU 작업이 GPU step보다 길어 CPU 쪽이 step을 정하는 경우와 맞는다. 후보는 streaming 출력 처리, KV events 발행, 관측 log이며 GTASK05에는 이 중 일부가 없었을 수 있다. 이 원인은 확인하지 않았다.
3. **`stack`** — **GTASK11의 직접 채널 1.131은 실제 시간 척도의 과소 추정이다.** lag 0 귀속에서는 큰 eager prefill(p > 1024)이 가격의 0.18배로 보인다. 그 GPU 시간은 다음 decode step의 간격에 나타나는데, cap(약 32 ms)이 그것을 잘라낸다. lag 1 귀속에서는 그 계급도 1.08이고, 총합 1.21이 창의 실제 wall 시간/가격이다.
4. **`universal`** — **async dispatch 기판에서 dispatch 간격을 step 시간으로 쓸 때는 귀속 lag를 맞춰야 한다.** lag가 틀리면 긴 step의 시간이 다음 짧은 step으로 넘어가고, 상한 cap이 그 시간을 지운다.

## 해석

- 13 %(실제는 21 %) 차는 "가격 채널이 이 운영 부하의 step을 싸게 매긴다"는 뜻이다. 가격 채널은 GTASK05의 격리 측정에서 왔고, 운영 부하(streaming 8요청, KV events, 대기열)에서는 FULL decode가 더 길다.
- 구성 간 비교(비용 비)는 같은 가격으로 매기므로 이 차이의 영향이 작다(GTASK10: 두 채널에서 구성 비 방향 같음). 그러나 시간이 흐르는 속도에 의존하는 양(대기, idle, 재사용)은 이 차이를 그대로 받는다([GTASK13](GTASK13.md)).

## 확인되지 않은 사항

- FULL decode 22 % 초과의 원인(CPU 바운드 여부, 어떤 per-request 작업인지)
- **새 계측 제안(승인 대상, 실행하지 않음)**
  1. CUDA event로 step의 device 시간을 재는 observation-only patch(v2 runner `execute_model` 앞뒤). device 시간과 dispatch 간격을 바로 가른다.
  2. GTASK05 프로토콜을 KV events on/off × streaming on/off로 다시 재서 FULL decode 차이를 구성 요인별로 분해(측정, 선등록 필요)
  3. EngineCore loop의 schedule·update_from_output CPU 시간을 `[GSTEP]`에 덧붙이는 log field(patch 확장)

## 실패 / 무효 시도

- 없음

## 연구 원칙에 미치는 영향

- 직접 채널의 정의(lag 0 + cap)는 이 부하에서 시간 척도로 쓰면 안 된다. 시간 척도에는 lag 1 귀속을 쓴다. 비용 지표로서의 기존 직접 채널 정의는 GTASK10·11 기록대로 둔다(정정은 이 TASK에 둔다).

## 다음 작업

- (Advisor 결정) 위 계측 제안 1–3 중 무엇을 할지

## 재현 정보

- 산출(비추적): `results/gpu/multiturn/main/20260930T1411Z/dynamics/channel_report.json`
- 입력: `dynamics/obs.json`(GTASK13 `obs_dynamics.py`)
