# TASK69 — dummy block 모형 반영 스위치

## 상태

DONE

## 날짜

2026-09-22

## 목적

[TASK63](TASK63.md)이 직접 관측한 padding용 dummy block을 시뮬레이터의 KV pool 모형에
**스위치로** 넣고, 반영 전후의 차이를 표로 낸다. 규칙은 지시대로 "decode 요청 수가
`0 < n < 실행 상한`이면 slot 1개를 추가 점유"이며 **기본값은 off**다.

## 배경

관련 TASK:

- [TASK63](TASK63.md) — dummy는 `0 < n < 8`인 decode step마다 매번 요청되고(1,084/1,084)
  `n = 8`에서 멈춘다. 할당·반납 없이 free list 머리를 가리킨다. 회수 14건이 전부 이 경로다
- [TASK64](TASK64.md) — admission 경로 회수의 존재 조건. 대상은 dummy 경로와 같이
  할당 순서상 가장 이른 inactive block이다
- [TASK58](TASK58.md) — 회수 건수 `max(0, ALLOC + 1 − 8)`의 `+1`이 이 dummy다
- [TASK08](TASK08.md) — `kvcache_num_blocks = batch_size`. pool 용량과 admission 상한이 같다
- [TASK67](TASK67.md), [TASK68](TASK68.md) — 이 작업의 앞 두 묶음

## 시작 상태

- 시작 commit `22759b3` ([TASK68](TASK68.md))
- `git status --short`: `?? .idea/` 외에 이 TASK의 변경(`engine.py`, `cache.py`,
  `config_search.py`, `config_search_rerun.py`, `dummy_block_effect.py`, `make_tables.py`)
- **새 측정 0, compile 0, serving lifecycle 0, device 접근 0**

## 수행 내용

1. `OuterBlockPool`에 `reserved: int = 0`을 넣고 `free_count`가 그만큼 줄도록 했다.
   `reserved`가 1이면 admission이 자기 몫보다 한 블록을 더 회수해야 하며, 그 여분 블록은
   누구에게도 할당되지 않는다 — [TASK63](TASK63.md)이 본 "회수만 하고 할당하지 않는"
   경로와 같은 모양이다.
2. `SimConfig.dummy_block: bool = False`를 넣었다. inner granularity와는 의미가 맞지
   않으므로 그 조합은 `ValueError`다.
3. `simulate()`의 admission 직전에, 스위치가 켜져 있으면
   `pool.reserved = int(0 < len(running) < max_running_requests)`를 설정한다.
   빈 batch에서도, 상한 batch에서도 0이다.
4. `config_search.score`에 `dummy_block` 키워드를, `config_search_rerun.py`에
   `--dummy-block`을 추가했다. **둘 다 기본값 off**이며 `meta.json`·`comparison.json`에
   설정을 기록한다.
5. `experiments/npu/analysis/dummy_block_effect.py`를 만들어 검증 칸을 off/on 두 모드로
   계산했고, 구성 탐색을 `--dummy-block`으로 한 번 더 돌렸다.
6. `make_tables.py`에 `S08`을 추가했다.

## 변경된 파일

- `src/continuum/sim/cache.py` (`OuterBlockPool.reserved`)
- `src/continuum/sim/engine.py` (`SimConfig.dummy_block`과 admission 직전 설정)
- `experiments/npu/analysis/config_search.py` (`score(..., dummy_block=False)`)
- `experiments/npu/analysis/config_search_rerun.py` (`--dummy-block`)
- `experiments/npu/analysis/dummy_block_effect.py` (신규)
- `experiments/npu/analysis/make_tables.py` (`S08` 추가)
- `results/tables/S08.{md,csv}` (신규), `results/tables/README.md`·`manifest.json` (갱신)
- `docs/research/TASK69.md` (신규), `docs/research/INDEX.md` (갱신)

## 실험 또는 검증 방법

```bash
R=results/npu/stage2
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py \
    --run $R/20260823-183505-final-confirm --sessions 6,8,10 \
    --output $R/20260823-183505-final-confirm/dummy_block_effect.json
env -u PYTHONPATH python3 experiments/npu/analysis/dummy_block_effect.py \
    --run $R/20260824-160028-n6-reconfirm --sessions 6 \
    --output $R/20260824-160028-n6-reconfirm/dummy_block_effect.json
env -u PYTHONPATH python3 experiments/npu/analysis/config_search_rerun.py \
    --sessions 6,8,10 --weight sum-seconds --top 20 --dummy-block \
    --output-dir $R/20260922-dummy-block/search-on
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --table S08
```

`requested_condition` / `observed_condition` / `condition_reached`: **해당 없음** (계산).

- population: [TASK35](TASK35.md) seed `20261000`의 (N, arm) 9칸(기준 arm 포함)과
  [TASK36](TASK36.md) seed `20261100`의 3칸. 각 칸은 반복 3블록 합산. 탐색은 후보 2,077개
- unit: 무차원 비, 건수(재사용·회수)
- source: run의 `probe/meta.*.json`(계획)과 `probe/requests.*.jsonl`(실측 재사용)
- device scope: 재집계 대상 run의 원 scope를 승계한다

### 스위치 off에서 기존 동작이 보존되는지

`S08`의 off 열 8건이 선등록 예측과 소수점 넷째 자리까지 같다(대조 8/8).
[TASK67](TASK67.md)의 `T07`과 [TASK68](TASK68.md)의 `S07`도 이 변경 뒤에 다시 생성했고
각각 8/8 일치다. **표 22개 전체 대조 212건에서 불일치 0건이다.**

## 결과

### 검증 칸의 반영 전후 — [`results/tables/S08.md`](../../results/tables/S08.md)

| run | N | arm | 실측 A′ 비 | off 비 | \|e_c\| off | on 비 | \|e_c\| on | Δ비 | sim 재사용 off→on | sim 회수 off→on |
|---|---|---|---|---|---|---|---|---|---|---|
| seed 20261000 | 6 | ① BASE | 1.0000 | 1.0000 | — | 1.0000 | — | — | 14→13 of 18 (실측 15) | 12→12 |
| seed 20261000 | 6 | ② | 0.9793 | 0.9610 | 0.0183 | 0.9576 | 0.0217 | −0.0034 | 18→18 of 18 | 0→0 |
| seed 20261000 | 6 | ③ | 0.9660 | 0.9466 | 0.0194 | 0.9432 | 0.0228 | −0.0034 | 18→18 of 18 | 0→0 |
| seed 20261000 | 8 | ① BASE | 1.0000 | 1.0000 | — | 1.0000 | — | — | 9→6 of 24 (실측 9) | 24→24 |
| seed 20261000 | 8 | ② | 0.9175 | 0.9101 | 0.0074 | 0.8845 | 0.0330 | −0.0256 | 24→24 of 24 | 0→0 |
| seed 20261000 | 8 | ③ | 0.9028 | 0.8971 | 0.0058 | 0.8718 | 0.0310 | −0.0252 | 24→24 of 24 | 0→0 |
| seed 20261000 | 10 | ① BASE | 1.0000 | 1.0000 | — | 1.0000 | — | — | 7→6 of 30 (실측 9) | 36→36 |
| seed 20261000 | 10 | ② | 0.9552 | 0.9213 | 0.0339 | 0.9037 | 0.0515 | −0.0176 | 29→29 of 30 | 12→13 |
| seed 20261000 | 10 | ③ | 0.9264 | 0.8899 | 0.0364 | 0.8729 | 0.0534 | −0.0170 | 29→29 of 30 | 12→13 |
| seed 20261100 | 6 | ① BASE | 1.0000 | 1.0000 | — | 1.0000 | — | — | 16→16 of 18 (실측 17) | 12→13 |
| seed 20261100 | 6 | ② | 0.9941 | 0.9874 | 0.0066 | 0.9874 | 0.0066 | +0.0000 | 18→18 of 18 | 0→0 |
| seed 20261100 | 6 | ③ | 0.9789 | 0.9713 | 0.0076 | 0.9713 | 0.0076 | +0.0000 | 18→18 of 18 | 0→0 |

**집계**

| 항목 | 값 |
|---|---|
| `\|e_c\|`가 커진 칸 | **6 / 8** |
| `\|e_c\|`가 작아진 칸 | 0 / 8 |
| 변화 없는 칸 | 2 / 8 (seed `20261100` N=6) |
| `\|e_c\|` 증가폭 범위 | +0.0034 – +0.0256 |
| 기준 arm의 sim device time 증가 | 23.557→23.641, 32.509→33.450, 41.402→42.207, 26.466→26.466 s |
| 기준 arm의 sim 재사용 변화 | 14→13, 9→6, 7→6, 16→16 |

**비는 4칸(seed `20261000` 6개 arm 칸)에서 전부 내려간다** — 반영이 기준 arm을 더 많이
벌하기 때문이다. `batch_size 16` arm 두 개는 재사용이 off·on 모두 만점이라 재사용 건수가
움직이지 않는다.

### 구성 탐색 상위 20의 반영 전후

| dummy block | 선정 구성 | batch | 탐색 합산비 | 평가 합산비 | 기록 구성과 일치 | 기록 구성의 순위 | 상위 20 ∩ off |
|---|---|---|---|---|---|---|---|
| off (기록 설정) | (1, 4, 6, 8, 10, 16) | 16 | 0.920931 | 0.906644 | 예 | 1 | 20 |
| on | (1, 4, 6, 8, 10, 16) | 16 | 0.897422 | 0.879757 | 예 | 1 | **20** |

**상위 20 집합이 완전히 같고 선정도 같다.** 예측 비만 내려간다(평가 0.906644 →
0.879757, −0.0269).

## 핵심 발견

1. **`stack` — 반영하면 검증 8칸 중 6칸에서 `|e_c|`가 커지고, 작아지는 칸은 없다.**
   증가폭은 +0.0034 – +0.0256이다. 나머지 2칸(seed `20261100` N=6)은 값이 전혀 움직이지
   않는다.
2. **`stack` — 반영의 효과는 기준 arm에 몰린다.** `batch_size 16` arm은 pool에 여유가
   있어 재사용 건수가 off·on 모두 만점이고, `batch_size 8`인 기준 arm만 재사용을 잃는다
   (14→13, 9→6, 7→6). 비가 내려가는 것은 분모가 커지기 때문이다.
3. **`stack` — sim 재사용 건수는 반영 전이 실측에 더 가깝다.** N=8 기준 arm에서 off는
   실측과 같은 9이고 on은 6이다. N=6은 실측 15에 off 14·on 13, N=10은 실측 9에 off 7·on 6이다.
4. **`stack` — 구성 선정은 이 반영에 둔감하다.** 상위 20 집합이 20/20 같고 argmin도 같다.
   바뀌는 것은 예측 비의 수준뿐이다(평가 −0.0269).
5. **`universal` — 스위치 off에서 기존 수치가 전부 재현된다.** 표 22개, 대조 212건,
   불일치 0건이다.

## 해석

지시에 따라 **§B-4 결과에 해석을 붙이지 않는다.** 위 표와 집계가 결과 그 자체다.
스위치는 기본값 off로 남으며, 이 표는 그 선택을 정당화하려는 것이 아니라 반영 시의
변화를 기록한 것이다.

한 가지 범위 확인만 적는다 — 이 표가 재는 것은 **시뮬레이터의 예측 오차와 건수**이지,
device에서 dummy block이 실제로 무엇을 하는지가 아니다. 그것은
[TASK63](TASK63.md)·[TASK64](TASK64.md)의 직접 관측이며 이 TASK는 그 관측을 바꾸지 않는다.

## 확인되지 않은 사항

- "실행 상한"을 `max_running_requests`로 잡은 것의 타당 범위 (`PARTIAL`).
  [TASK63](TASK63.md)이 관측한 artifact는 `batch_size = 8`이고 최상위 bucket도 8이라
  **두 해석이 같은 값이 된다.** 둘이 갈리는 구성(예: `batch_size 16`, 최상위 bucket 16이
  아닌 격자)에서 어느 쪽인지는 관측되지 않았다
- 반영 규칙이 pool 점유만인지, 회수 대상 선택 순서에도 관여하는지 (`UNKNOWN`).
  [TASK63](TASK63.md)은 dummy가 "free list 머리를 가리킬 뿐"이라고 기록했고
  [TASK64](TASK64.md)는 회수 대상이 할당 순서상 가장 이른 inactive block이라고 기록했다.
  이 구현은 점유만 모형화하고 victim 선택 규칙은 건드리지 않았다
- seed `20261100` N=6에서 값이 전혀 움직이지 않는 이유 (`UNKNOWN`). 그 plan에서 부분
  batch 구간에 pool 압박이 없었을 가능성이 있으나 확인하지 않았다

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

[TASK68](TASK68.md)에서 세운 규칙 — **모형 변경 스위치는 기본값 off이고, off에서 기존
수치가 재현됨을 대조로 고정한다** — 을 두 번째로 적용했다. 이번에는 표 22개 전체를
다시 생성해 대조 212건이 자동으로 돌았다. 원칙 15(과거에 실패한 접근·잘못된 가정을
관련 TASK 확인 없이 반복하지 않는다)에 따라 [TASK63](TASK63.md)의 관측 조건을
「확인되지 않은 사항」에 그대로 적었다 — 관측된 artifact에서는 두 해석이 구별되지 않는다.

## 다음 작업

사용자 지시가 있을 때만 착수한다.

1. dummy block의 "실행 상한"이 `batch_size`인지 최상위 bucket인지 가르는 관측
   (측정 필요, 선등록 대상)
2. 원고 전용 도구 4건의 처분 ([TASK65](TASK65.md) 판단 요청)

## 재현 정보

- 시작 commit: `22759b3`
- 선등록 commit: **해당 없음** — 새 측정이 없는 계산이다
- 실행 명령: 위 「실험 또는 검증 방법」
- 입력 artifact: `results/npu/stage2/20260823-183505-final-confirm/`,
  `results/npu/stage2/20260824-160028-n6-reconfirm/`
- 산출: 각 run의 `dummy_block_effect.json`,
  `results/npu/stage2/20260922-dummy-block/search-on/`(전부 미추적),
  `results/tables/S08.{md,csv}`(추적)
- 예산: 측정 0, serving lifecycle 0, 재compile 0, device 접근 0
