# TASK68 — 되먹임 절제 스위치: 재도착 재계산의 추가 효용

## 상태

DONE

## 날짜

2026-09-22

## 목적

시뮬레이터는 세션의 재도착 시각을 입력으로 받지 않는다. turn이 끝나면 그 시점에서
tool gap이 시작되고 다음 turn이 `완료 + gap`에 도착하므로, 배치를 빨리 비우는 구성은
다음 turn도 빨리 받는다 — **도착 열이 입력이 아니라 출력**이다. 그 설계가 예측 정확도에
무엇을 보태는지는 지금까지 재 본 적이 없다.

`--fix-arrivals`로 그 되먹임을 끄고, 같은 실측 자료에 대해 두 모드의 예측 오차를
나란히 놓는다. 목적은 기전 기여 분리가 아니라 **재도착 재계산 설계의 추가 효용
정량화**다.

## 배경

관련 TASK:

- [TASK67](TASK67.md) — 이 작업의 앞 묶음. `prefill_s` 인자 확인과 집계 파일 신설
- [TASK35](TASK35.md) — 확증 4건·탐색 2건, 선등록 예측 `0.9610`·`0.9466`·`0.9101`·`0.8971`·`0.9213`·`0.8899`
- [TASK36](TASK36.md) — N=6 재측정. 선등록 예측 `0.9874`·`0.9713`
- [TASK24](TASK24.md), [TASK25](TASK25.md) — 시뮬레이터 구축과 out-of-sample 검증
- [TASK29](TASK29.md) — 기존 `ablation.py`. **목적이 다르다**(아래 참조)

**`ablation.py`와의 구분.** 그 파일은 이 substrate가 측정된 의미론 하나를 다른 stack이
문서화한 의미론으로 바꿔 넣고, 그 기전이 책임지던 결과가 어떻게 달라지는지 계산한다 —
substrate에 대한 반사실이다. 이 TASK는 substrate를 건드리지 않는다. 질문이 **시뮬레이터
자신의 구성**에 대한 것이다. 그 구분을 `arrival_feedback.py` docstring에 적었다.

## 시작 상태

- 시작 commit `71551bb` ([TASK67](TASK67.md))
- `git status --short`: `?? .idea/`, `M src/continuum/sim/engine.py`(이 TASK의 변경),
  `?? experiments/npu/analysis/arrival_feedback.py`(이 TASK의 신규)
- **새 측정 0, compile 0, serving lifecycle 0, device 접근 0**

## 수행 내용

1. `SimConfig`에 `fixed_arrivals: dict[(session_index, turn) -> arrival_s] | None`을
   추가했다. **기본값 `None` = 기존 동작.**
2. `_finish()`에서 다음 turn의 `arrival_s`·`ready_s`를 만들 때, map이 있으면 완료 시각
   기반 계산 대신 map의 값을 쓴다. **map이 있는데 해당 key가 없으면 `RuntimeError`** —
   절반만 고정된 도착 열은 두 모형 어느 쪽도 아니기 때문이다.
3. `__post_init__`에 검증을 넣었다: turn 0은 재도착이 아니므로 map에 들어올 수 없고,
   음수 도착 시각도 거부한다.
4. `experiments/npu/analysis/arrival_feedback.py`를 만들었다. `--fix-arrivals <RUN>`이
   그 run의 **기준 arm(`BASE`) 실행 로그에서 관측된 재도착 시각**을 읽어 모든 arm에
   같은 열을 고정한다. 두 모드를 모두 돌려 `|e_c|`를 나란히 낸다.
5. `make_tables.py`에 `S07`을 추가했다.

## 변경된 파일

- `src/continuum/sim/engine.py` (`SimConfig.fixed_arrivals` 신설)
- `experiments/npu/analysis/arrival_feedback.py` (신규)
- `experiments/npu/analysis/make_tables.py` (`S07` 추가, markdown cell의 `|` escape)
- `results/tables/S07.{md,csv}` (신규), `results/tables/README.md`·`manifest.json` (갱신)
- `docs/research/TASK68.md` (신규), `docs/research/INDEX.md` (갱신)

## 실험 또는 검증 방법

```bash
R=results/npu/stage2
env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py \
    --run $R/20260823-183505-final-confirm \
    --fix-arrivals $R/20260823-183505-final-confirm \
    --sessions 6,8,10 --output $R/20260823-183505-final-confirm/arrival_feedback.json
env -u PYTHONPATH python3 experiments/npu/analysis/arrival_feedback.py \
    --run $R/20260824-160028-n6-reconfirm \
    --fix-arrivals $R/20260824-160028-n6-reconfirm \
    --sessions 6 --output $R/20260824-160028-n6-reconfirm/arrival_feedback.json
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --table S07
```

`requested_condition` / `observed_condition` / `condition_reached`: **해당 없음** (계산).

- population: [TASK35](TASK35.md) seed `20261000`의 (N, arm) 6칸과
  [TASK36](TASK36.md) seed `20261100`의 N=6 2칸. 각 칸은 반복 3블록 합산
- unit: 무차원 비(device time ratio)와 그 차
- source: 계획은 run의 `probe/meta.*.json`, 고정 도착 열은 `probe/requests.BASE.*.jsonl`의
  `sent_s`(각 블록의 최초 turn-0 전송을 0으로 이동), 실측 비는 `config_device.aggregate`
- device scope: 재집계 대상 run의 원 scope(`rbln0`–`rbln3`)를 승계한다

### 스위치 off에서 기존 동작이 보존되는지

전체 모형(스위치 off)의 비 8건이 **선등록 예측과 소수점 넷째 자리까지 같다.**
이것이 `S07`의 대조 8건이며 전건 일치다. 같은 확인이 [TASK67](TASK67.md)의 `T07`에도
있다(이 변경 뒤에 생성됐고 8/8 일치).

## 결과

### 두 모드의 예측 오차 — [`results/tables/S07.md`](../../results/tables/S07.md)

`e_c` = 시뮬레이터 비 − 실측 A′ 비.

| run | N | 구간 | arm | 실측 A′ 비 | 전체 모형 | \|e_c\| | 고정 모형 | \|e_c\| | 차 | 더 작은 쪽 |
|---|---|---|---|---|---|---|---|---|---|---|
| seed 20261000 | 6 | 확증(채널 보류) | ② | 0.9793 | 0.9610 | 0.0183 | 0.9495 | 0.0298 | +0.0115 | 전체 |
| seed 20261000 | 6 | 확증(채널 보류) | ③ | 0.9660 | 0.9466 | 0.0194 | 0.9513 | 0.0146 | −0.0048 | 고정 |
| seed 20261000 | 8 | 확증 | ② | 0.9175 | 0.9101 | 0.0074 | 0.9329 | 0.0154 | +0.0080 | 전체 |
| seed 20261000 | 8 | 확증 | ③ | 0.9028 | 0.8971 | 0.0058 | 0.9303 | 0.0275 | +0.0217 | 전체 |
| seed 20261000 | 10 | 탐색 | ② | 0.9552 | 0.9213 | 0.0339 | 0.9386 | 0.0166 | −0.0173 | 고정 |
| seed 20261000 | 10 | 탐색 | ③ | 0.9264 | 0.8899 | 0.0364 | 0.9406 | 0.0142 | −0.0222 | 고정 |
| seed 20261100 | 6 | 확증 | ② | 0.9941 | 0.9874 | 0.0066 | 0.9937 | 0.0004 | −0.0063 | 고정 |
| seed 20261100 | 6 | 확증 | ③ | 0.9789 | 0.9713 | 0.0076 | 0.9982 | 0.0193 | +0.0117 | 전체 |

**집계**

| 구간 | 칸 수 | 전체 모형이 더 작음 | 고정 모형이 더 작음 |
|---|---:|---:|---:|
| [TASK35](TASK35.md) 확증 (N ∈ {6, 8}) | 4 | **3** | 1 |
| [TASK36](TASK36.md) 확증 (N = 6) | 2 | 1 | 1 |
| 탐색 (N = 10) | 2 | 0 | **2** |
| 전체 | 8 | 4 | 4 |

`|e_c|` 범위: 전체 모형 0.0058–0.0364, 고정 모형 0.0004–0.0298.
`|e_c|` 평균: 전체 모형 0.0169, 고정 모형 0.0172.

**기준 arm의 sim device time** (두 모드의 분모)

| run | N | 전체 모형 (s) | 고정 모형 (s) | 실측 A′ (s) |
|---|---|---|---|---|
| seed 20261000 | 6 | 23.557 | 24.327 | 22.984 |
| seed 20261000 | 8 | 32.509 | 32.900 | 32.197 |
| seed 20261000 | 10 | 41.402 | 41.464 | 40.040 |
| seed 20261100 | 6 | 26.466 | 26.655 | 26.110 |

## 핵심 발견

1. **`stack` — 되먹임을 끄면 `|e_c|`가 어느 방향으로도 체계적으로 움직이지 않는다.**
   8칸에서 4 대 4, 평균 `|e_c|`는 0.0169 대 0.0172다.
2. **`stack` — 방향이 구간에 따라 갈린다.** [TASK35](TASK35.md) 확증 4건에서는 전체
   모형이 3건 더 작고, 탐색 구간(N=10) 2건에서는 고정 모형이 2건 다 더 작다.
   N=10은 전체 모형의 `|e_c|`가 0.0339·0.0364로 이 표에서 가장 크고, 고정 모형이 그
   절반 이하(0.0166·0.0142)로 내려간다.
3. **`stack` — 고정 모형은 기준 arm의 sim device time을 4칸 전부에서 올린다**
   (23.557→24.327, 32.509→32.900, 41.402→41.464, 26.466→26.655). 비는 분자·분모가 함께
   움직이므로 이 증가가 곧 비의 증가는 아니다.
4. **`universal` — 스위치가 off일 때 기존 결과가 보존됨을 대조로 고정했다.**
   전체 모형 8건이 선등록 예측과 소수점 넷째 자리까지 같다. 구조 변경에 이 대조를
   붙여 두면 이후 변경에서도 같은 확인이 자동으로 돈다.

## 해석

지시에 따라 **§B-3 결과에 해석을 붙이지 않는다.** 위 표와 집계가 결과 그 자체다.
어느 모드가 옳은 모형인지, 4 대 4가 무엇을 뜻하는지는 이 TASK가 판정하지 않는다.

한 가지 사실 확인만 적는다 — 표가 재는 것은 **예측 정확도**이지 기전 기여가 아니다.
두 모드는 분모(기준 arm)도 함께 바뀌므로, `|e_c|` 차를 "되먹임이 device time에 기여한
양"으로 읽을 수 없다.

## 확인되지 않은 사항

- 8칸은 판정 표본이 아니다 (`UNKNOWN`). 4 대 4가 무작위인지 구간 의존인지 가를 표본이 없다
- 고정 도착 열이 `BASE` arm에서 온다는 선택의 영향 (`UNKNOWN`). 각 arm 자신의 관측 도착
   열로 고정하면 되먹임이 절반만 꺼지므로 이 TASK는 하지 않았다
- N=10에서 전체 모형의 오차가 큰 이유 (`UNKNOWN`). N=10은 [TASK35](TASK35.md)에서도
  탐색 구간이며 판정 대상이 아니었다

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

원칙 14(관측 불가 항목을 임의 값으로 채우지 않는다)를 스위치 설계에 적용했다 —
`fixed_arrivals`에 key가 없으면 계산된 값으로 조용히 되돌아가지 않고 `RuntimeError`다.
원칙 6(eviction/release를 recomputation으로 해석하지 않는다)과 무관하나, **모형 변경
스위치는 기본값 off이고 off에서 기존 수치가 재현됨을 대조로 고정한다**는 실무 규칙을
여기서 세운다.

## 다음 작업

사용자 지시가 있을 때만 착수한다.

1. §B-4 dummy block 모형 반영 스위치 (`--dummy-block`) — [TASK69](TASK69.md)

## 재현 정보

- 시작 commit: `71551bb`
- 선등록 commit: **해당 없음** — 새 측정이 없는 계산이다
- 실행 명령: 위 「실험 또는 검증 방법」
- 입력 artifact: `results/npu/stage2/20260823-183505-final-confirm/`,
  `results/npu/stage2/20260824-160028-n6-reconfirm/` (둘 다 `results/`는 gitignore 대상)
- 산출: 각 run의 `arrival_feedback.json`(미추적), `results/tables/S07.{md,csv}`(추적)
- 예산: 측정 0, serving lifecycle 0, 재compile 0, device 접근 0
