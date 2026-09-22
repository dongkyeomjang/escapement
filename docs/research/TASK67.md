# TASK67 — 보고된 표의 집계 파일 신설과 구성 선정 민감도

## 상태

DONE

## 날짜

2026-09-22

## 목적

외부 검토 대응의 잔여 분석 세 묶음을 **새 측정 없이** 닫는다.

1. **prefill 추가 비용의 정의·계산 일치 확인.** `config_device.py:84`와
   `sim/engine.py:465`가 `PrefillCostModel`에 무엇을 넣고 있는지 — `C`인지 `L − C`인지
   `L`인지 — 를 코드에서 확정하고, [TASK54](TASK54.md) 배치의 재도착 요청 168건에 대해
   두 정의의 값을 표로 고정한다.
2. **`results/`가 비어 있는 문제.** 보고되는 표에 대응하는 집계 파일이 저장소에 없어
   [TASK66](TASK66.md)이 "저장소에 없는 수치는 provenance를 갖지 못한다"를 실증했다.
   표마다 집계 파일 하나와 생성 명령 하나를 두고, 값이 기록된 곳과 대조한다.
3. **구성 선정의 민감도와 반복별 분해.** N 집합과 score 정의를 바꿔 선정이 움직이는지,
   합산으로 보고된 판정 아래에 반복별로 무엇이 있었는지를 표로 낸다.

## 배경

관련 TASK:

- [TASK66](TASK66.md) — 원고의 두 수치를 저장소에서 재현하지 못했고, 원고 수치와 저장소
  산출물의 정합을 저장소 쪽에서 보증할 수 없다는 점이 드러났다. 이 TASK의 2번 목적이 거기서 나왔다
- [TASK65](TASK65.md) — 논문 텍스트를 저장소 밖으로 옮겼다. 원고는 이 TASK의 대상이 아니다
- [TASK61](TASK61.md) — compile 구성 탐색 재실행과 `--max-buckets`의 한 칸 어긋남
- [TASK35](TASK35.md), [TASK36](TASK36.md) — 채널 A′/B, X, 확증/탐색 구간
- [TASK50](TASK50.md) — 무처치 반복 분포. 반복별 분해를 불확실성으로 읽지 않는 근거
- [TASK52](TASK52.md), [TASK53](TASK53.md), [TASK56](TASK56.md) — padding 표와 분해
- [TASK58](TASK58.md), [TASK62](TASK62.md), [TASK63](TASK63.md) — 용량 개입, 재compile 변동, dummy block

## 시작 상태

- 시작 commit `ac1b7d8`([TASK66](TASK66.md)), `git status --short`는 `?? .idea/`만
- `main`은 `origin/main`과 같음
- **새 측정 0, compile 0, serving lifecycle 0, device 접근 0.** 전부 기존 artifact 재집계와 계산
- 논문 텍스트는 저장소에 없다. 이 TASK는 원고를 읽지도 고치지도 않았다

## 수행 내용

1. `PrefillCostModel`을 부르는 지점을 전수 확인했다(§A-1).
2. 기존 분석 script 13개를 원자료에 다시 돌려 `results/` 아래 분석 산출물을 복원했다.
   `prefill_tax.py`는 `--input-dir`가 run 루트가 아니라 `<RUN>/probe`여야 결과가 나온다
   ([TASK22](TASK22.md)에 명령 전문이 남아 있지 않아 이번에 확정했다).
3. `make_tables.py`를 새로 만들어 표 20개를 `results/tables/`에 냈다. 각 표는 이름 붙은
   함수 하나가 만들고, 기록된 값이 있으면 그 자리에서 대조한다. `.gitignore`에
   `results/tables/`만 예외를 뒀다.
4. `per_repetition.py`를 새로 만들어 두 구성 비교와 포화 격자를 반복별로 분해했다(§B-2).
5. `config_search_rerun.py`에 `--weight {sum-seconds,per-n}`을 추가하고 N 집합 3종 ×
   score 2종 = 6회 재실행했다(§B-1).
6. `README.md`에 `--max-buckets` 어긋남과 `results/tables/` 예외를 적고(§C-1),
   `INDEX.md`에 package 명칭 주의를 한 줄 넣었다(§C-2). `check_claims.py`를 다시 돌렸다(§C-3).

## 변경된 파일

- `experiments/npu/analysis/make_tables.py` (신규)
- `experiments/npu/analysis/per_repetition.py` (신규)
- `experiments/npu/analysis/config_search_rerun.py` (`--weight` 추가)
- `results/tables/` (신규, 표 20개 × `.md`/`.csv` + `README.md` + `manifest.json`)
- `.gitignore` (`results/tables/`만 추적)
- `README.md`, `docs/research/TASK67.md` (신규), `docs/research/INDEX.md` (갱신)

**기존 TASK 문서의 수치는 하나도 고치지 않았다.** 대조 결과는 각 표 파일에만 적었다.

## 실험 또는 검증 방법

측정 없음. 선행 명령 전문은 [`results/tables/README.md`](../../results/tables/README.md)에 있다.

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all
```

`requested_condition` / `observed_condition` / `condition_reached`: **해당 없음** (재집계·계산).

- population: 표마다 다르다. 각 파일의 「입력」 줄이 그 표의 artifact를 명시한다
- unit: 표마다 다르다(ms, s, token, step, 비율). 열 제목에 단위를 적었다
- source: `results/npu/stage2/**` 원자료와 그 위의 분석 산출물. 새 측정 없음
- device scope: 재집계 대상 run들의 원 scope를 그대로 승계한다(`rbln0`–`rbln3`)

## 결과

### A-1. 두 소비처는 `C`가 아니라 `q = L − C`를 넣는다 — 수정 불필요

`prefill_s`를 부르는 지점은 저장소 전체에 **셋**이다.

| 호출 지점 (commit `ac1b7d8` 기준 줄) | 인자 | 정체 | 쓰임 |
|---|---|---|---|
| `experiments/npu/analysis/config_device.py:84` | `max(prompt_tokens − cached_tokens, 0)` | **`q = L − C`** | 채널 A′의 prefill 항 |
| `src/continuum/sim/engine.py:465` | `computed` (`:464`에서 `p.prompt_tokens − cached`) | **`q = L − C`** | prefill step의 소요 시간 |
| `src/continuum/sim/engine.py:329` | `me.prompt_tokens` | **`L`** | `Context.prefill_s` — **정책에 건네는 정보**이며 device 비용이 아니다 |

**앞의 둘은 이미 모형 정의(`q = L − C`)와 일치한다. 따라서 `engine.py` 수정도,
[TASK54](TASK54.md)·[TASK59](TASK59.md) 검증 비교의 재계산도 하지 않았다.**

셋째 지점은 `_context()` 안이며 `return_policy`가 설정된 경우에만 호출된다
(`_release_ready`·`_next_wakeup` 둘 다 `policy is not None` 가드 안에서 부른다).
측정·판정에 쓰인 모든 구성은 `return_policy=None`이므로 **이 값은 어떤 보고 수치에도
들어가지 않는다.** `L`을 넣는 유일한 지점이라 기록해 둔다.

**[TASK66](TASK66.md) §결과 2의 표기 정정**: 그 표는 두 지점의 인자를 `T(C)`로 적었는데,
같은 문서 §결과 3의 `C`는 **재사용 가능분**이다. 두 `C`가 다른 양이다. 지점이 넣는 것은
**요청의 실계산량**이며, 그 양을 `C`로 부르면 §결과 3의 표와 충돌한다.
[TASK66](TASK66.md)은 고치지 않는다(원칙: 기존 TASK 수치·서술을 새 계산에 맞춰 고치지
않는다). 이 절이 정정 기록이다.

### A-1. 168건의 C별 두 정의 — [`results/tables/A01.md`](../../results/tables/A01.md)

[TASK66](TASK66.md) `reuse_cost.py`를 다시 돌려 재현했다. 대조 4건 전건 일치.

| C (token) | 요청 수 | hit | L 범위 | 독립형 `T(C)` (ms) | 증분형 `T(L)−T(L−C)` (ms) | 같은 C 안의 폭 (ms) |
|---:|---:|---:|---|---:|---|---:|
| 768 | 8 | 4 | 1,004–1,044 | 130.18 | 132.07–132.72 | 0.65 |
| 896 | 28 | 17 | 1,013–1,191 | 152.46 | 153.55–155.50 | 1.94 |
| 1,024 | 44 | 20 | 1,093–1,408 | 174.89 | 175.90–178.82 | 2.92 |
| 1,152 | 20 | 12 | 1,361–1,490 | 197.49 | 200.17–201.65 | 1.48 |
| 1,280 | 20 | 12 | 1,345–1,561 | 220.25 | 221.49–224.51 | 3.02 |
| 1,408 | 28 | 17 | 1,526–1,694 | 243.18 | 244.91–247.89 | 2.98 |
| 1,536 | 20 | 13 | 1,653–1,757 | 266.27 | 268.15–269.93 | 1.78 |

**두 열 중 어느 것도 코드가 계산하는 값이 아니다.** 코드는 `T(L − C)`를 계산한다 —
그것은 요청이 실제로 치른 prefill 비용이고, 위 두 열은 "재사용이 실패했을 때 더 드는 양"의
서로 다른 정의다. 증분형 − 독립형은 **+1.01 – +4.72 ms**, 같은 C 안의 최대 폭은 3.02 ms다.

### A-2. 표 ↔ 파일 ↔ 생성 명령 — 20개 전건 대응, 대조 194건 불일치 0건

[`results/tables/README.md`](../../results/tables/README.md)에 대응표가 있다.

| 표 | 내용 | 파일 | 근거 TASK | 대조 | 불일치 |
|---|---|---|---|---:|---:|
| T01 | padding 비율과 decode device time (N별) | `T01.md` | TASK52, TASK53 | 2 | 0 |
| T02 | bucket 6 개입의 짝 비교 | `T02.md` | TASK54 | 4 | 0 |
| T03 | slot 8→16 개입의 재사용과 계산량 | `T03.md` | TASK35, TASK58 | 44 | 0 |
| T04 | prefill 주입과 병행 세션의 정지 | `T04.md` | TASK22 | 36 | 0 |
| T05 | N=6의 seed 간 상충 | `T05.md` | TASK35, TASK36 | 10 | 0 |
| T06 | decode step 비용 계수 | `T06.md` | TASK13, TASK55 | 5 | 0 |
| T07 | 검증 구성의 비용 비 예측 | `T07.md` | TASK33, TASK35, TASK36 | 8 | 0 |
| T08 | 채널별 device time | `T08.md` | TASK35, TASK36 | 18 | 0 |
| T09 | 구성 선택의 절감률 X | `T09.md` | TASK35, TASK36 | 12 | 0 |
| T10 | 추가 slot의 포화 | `T10.md` | TASK40 | 3 | 0 |
| T11 | 컴파일 비용과 artifact 크기 | `T11.md` | TASK06, TASK10, TASK23, TASK40, TASK62 | 6 | 0 |
| T12 | 무처치 반복의 채널 차 분포 (S1) | `T12.md` | TASK50 | 0 | 0 |
| T13 | N ∈ {3,4,7}의 6블록 짝 비교 (S4) | `T13.md` | TASK23, TASK25 | 21 | 0 |
| T14 | 개입의 padding 하락 분해 (S5) | `T14.md` | TASK56 | 5 | 0 |
| A01 | 재사용 실패의 추가 비용: 두 정의 | `A01.md` | TASK66 | 4 | 0 |
| S02 | 재compile 변동과 회차 간 변동 (S2) | `S02.md` | TASK62 | 2 | 0 |
| S03 | dummy block 생애 주기 직접 관측 (S3) | `S03.md` | TASK63 | 5 | 0 |
| S06a | 검증 비교·절감률의 반복별 분해 (S6) | `S06a.md` | TASK35, TASK36 | 6 | 0 |
| S06b | 추가 slot 포화의 N×반복별 분해 (S6) | `S06b.md` | TASK40 | 1 | 0 |
| B01 | 구성 선정의 N 집합·score 민감도 | `B01.md` | TASK61 | 2 | 0 |

생성 명령은 표마다 `make_tables.py --table <ID>`이고, 전체는 `--all`이다. 각 파일이
자기 생성 명령과 입력 artifact 경로를 헤더에 담는다.

**대조에서 두 곳의 정의 차이가 드러났고, 둘 다 표에 병기하는 것으로 닫았다.**

- `T06`: descriptor의 `f(bucket)`은 model p50이 아니라 **model p50 + sampler p50**이다
  ([TASK13](TASK13.md) 표의 `B 합`). 9.51이 아니라 9.87이 들어간다
- `T14`: [TASK56](TASK56.md)의 "80.9 %"는 `p` 하락분의 **Shapley 분해**이고, 제거된 slot
  수의 몫은 **81.1 %** 다. [TASK56](TASK56.md) 핵심 발견 1이 두 값의 0.2 %p 일치로 이미
  기록해 둔 내용이며, 표에 두 열을 모두 실었다

### B-1. N 집합과 score를 바꾼 선정 — [`results/tables/B01.md`](../../results/tables/B01.md)

후보 공간은 세 조건에서 동일한 2,077개다. N 집합은 점수만 바꾼다.

| score | N 집합 | 선정 구성 | batch | 평가 합산비 | 평가 N평균비 | 기록 구성과 일치 | 기록 구성의 순위 |
|---|---|---|---|---|---|---|---|
| `sum-seconds` | 6,8 | (1, 4, 5, 6, 8, 16) | 16 | 0.923708 | 0.924685 | 아니오 | 11 |
| `sum-seconds` | 6,8,10 | (1, 4, 6, 8, 10, 16) | 16 | 0.906644 | 0.910874 | **예** | 1 |
| `sum-seconds` | 8,10 | (1, 4, 6, 8, 10, 16) | 16 | 0.886962 | 0.888356 | **예** | 1 |
| `per-n` | 6,8 | (1, 4, 5, 6, 8, 16) | 16 | 0.923708 | 0.924685 | 아니오 | 12 |
| `per-n` | 6,8,10 | (1, 4, 6, 8, 10, 16) | 16 | 0.906644 | 0.910874 | **예** | 1 |
| `per-n` | 8,10 | (1, 4, 6, 8, 10, 16) | 16 | 0.886962 | 0.888356 | **예** | 1 |

상위 20 집합을 기준 조건(`sum-seconds`, N=6,8,10)과 비교한 결과다.

| score | N 집합 | 교집합 | 기준에만 | 이 조건에만 |
|---|---|---:|---:|---:|
| `sum-seconds` | 6,8 | 4 | 16 | 16 |
| `sum-seconds` | 8,10 | 15 | 5 | 5 |
| `per-n` | 6,8 | 4 | 16 | 16 |
| `per-n` | 8,10 | 14 | 6 | 6 |

### B-2. 반복별 분해 — [`S06a.md`](../../results/tables/S06a.md), [`S06b.md`](../../results/tables/S06b.md)

합산 행이 선등록된 판정 단위이고 반복 행은 그 아래다. **불확실성 판정·CI는 계산하지
않았다** — 무처치 반복 분포는 `T12`(S1)에 있다. 합산 6건은 [TASK35](TASK35.md) 기록과
전건 일치한다.

| N | arm | b0 | b1 | b2 | 합산 (A′ 비) | 합산 X(A′) |
|---|---|---|---|---|---|---|
| 6 | ② | 0.9998 | 0.9672 | 0.9705 | **0.9793** | +2.07 % |
| 6 | ③ | 0.9782 | 0.9642 | 0.9562 | **0.9660** | +3.40 % |
| 8 | ② | 0.9446 | 0.9166 | 0.8723 | **0.9175** | +8.25 % |
| 8 | ③ | 0.9259 | 0.9044 | 0.8611 | **0.9028** | +9.72 % |
| 10 | ② | 0.9434 | 0.9560 | 0.9655 | **0.9552** | +4.48 % |
| 10 | ③ | 0.8833 | 0.9511 | 0.9428 | **0.9264** | +7.36 % |

[TASK36](TASK36.md) seed `20261100`의 N=6: ② 0.9821 / 1.0024 / 1.0000 → 0.9941,
③ 0.9766 / 0.9835 / 0.9767 → 0.9789. **[TASK36](TASK36.md)이 기록한 블록별 실측값과 전건 일치한다.**

포화 격자(`S06b`)는 N × 반복 × arm 27행이며, `B8→B16`의 셀별 ratio 9개가
`batch_curve.json`의 `per_cell_ratios`와 집합으로 일치한다.

### B-5. S2·S3 근거 추출 — [`S02.md`](../../results/tables/S02.md), [`S03.md`](../../results/tables/S03.md)

`S02`(재compile 변동, [TASK62](TASK62.md)):

- **재확인 반복 수**: artifact 3개 × 회차 5회 × bucket 4개 = **60 lifecycle**(전건 성공,
  재실행 1건 `A1.r3.L1`)
- **회차 / 재compile 구분**: 회차는 같은 artifact를 다시 기동해 다시 잰 것(표의 열 안),
  재compile은 artifact 자체를 다시 만든 것(표의 행 사이). A1 = `mb`, A2 = 격자 변경 `mb6`,
  A3 = 같은 구성 재compile `mb-rc`
- **변동 범위 계산법**: 같은 artifact·같은 bucket의 **회차 쌍**(5회차 → 10쌍, artifact
  3개로 bucket당 30쌍)의 `|중앙 차|`로 귀무 분포를 만들고 그 q95를 문턱으로 쓴다.
  판정은 `|중앙(x) − 중앙(y)| ≤ q95`이면 `WITHIN`
- **bucket별 수치**: 표에 artifact × bucket 12행과 귀무 분포(중앙/q90/q95/최대)를 실었다.
  R2(A1 대 A2)에서 `OUTSIDE`인 bucket은 **8 하나**다

`S03`(dummy block, [TASK63](TASK63.md)):

- **직접 관측 실행 수**: 본 측정 **10 trial**(파일럿 1회는 `pilot.json`에 별도)
- **로그 경로**: `results/npu/stage2/20260912-134732-dummy-lifecycle/server-<TAG>.log`
  (저장소 상대경로. `results/`는 git 미추적)
- **회수 14건 라벨**: trial별 `OB<id>#<세대>:dummy`. **14/14가 `dummy` 경로**이고
  `request_alloc` 0건, `preemption` 0건, 미분류 0건이다
- 부분 step(`0 < n < 8`)마다 dummy 호출이 정확히 1회, 상한 step(`n = 8`)에서 0회다

### C. 잔여

- **C-1**: `README.md`에 `config_search.py --max-buckets`의 한 칸 어긋남을 적었다.
  기본값 `6`은 후보 **4,393개**, 선등록 정의에 해당하는 `5`는 **2,077개**다
  ([TASK61](TASK61.md)). 이번 6회 실행 전건에서 재확인됐다
- **C-2**: `INDEX.md`에 `src/continuum/`이 개명 전 명칭이며 arXiv:2511.02230 Continuum과
  무관하다는 한 줄을 넣었다
- **C-3**: `check_claims.py`는 **실행 즉시 실패한다.**

  ```
  FileNotFoundError: [Errno 2] No such file or directory:
      '/home/rebel/continuum-npu/paper/CLAIMS.md'
  ```

  원인은 [TASK65](TASK65.md)가 `paper/CLAIMS.md`와 `paper/draft/[0-9]*.md`를 제거한
  것이다. 이 script는 원고 전용 도구이고 원고는 저장소 밖이므로 **고치지 않았다** —
  [TASK65](TASK65.md)가 남긴 "원고 전용 도구 4건을 남길지" 판단 요청에 해당한다.

## 핵심 발견

1. **`universal` — 보고되는 표에 생성 명령과 집계 파일을 1:1로 붙이면 원고와 저장소의
   정합을 저장소 쪽에서 기계적으로 감시할 수 있다.** 이번에 대조 194건이 자동으로 돌았고
   불일치가 0건이었다. [TASK66](TASK66.md)이 드러낸 구멍은 수치가 틀렸다는 것이 아니라
   **틀렸을 때 탐지할 자리가 없었다**는 것이었고, 그 자리가 생겼다.
2. **`universal` — 같은 기호를 두 뜻으로 쓴 기록은 값이 맞아도 대조를 통과하지 못한다.**
   [TASK66](TASK66.md)의 `C`가 §2에서는 실계산량, §3에서는 재사용 가능분이었다. 값은 둘 다
   맞고 충돌은 표기에만 있다. 대조를 코드로 적을 때 비로소 드러났다.
3. **`stack` — 저장소의 device 비용 경로는 전부 `q = L − C`를 쓴다.** 외부 검토가 지적한
   L 의존성은 `T(L) − T(L−C)`라는 **보고용 정의**에만 있고 계산 경로에는 없다.
   `L`을 넣는 유일한 지점은 정책에 건네는 `Context.prefill_s`이며 측정 구성에서는
   호출되지 않는다.
4. **`stack` — 선정 구성은 N 집합에 민감하고 score 정의에는 둔감하다.** N=10을 빼면
   선정이 `(1,4,5,6,8,16)`으로 바뀌고 상위 20의 교집합이 4/20으로 떨어진다. score를
   합산 초에서 N별 비 평균으로 바꾸면 세 N 집합 전부에서 **argmin이 바뀌지 않는다**.
5. **`stack` — 합산 판정 아래의 블록 분산은 작지 않다.** N=8 ③에서 블록별 A′ 비가
   0.8611–0.9259이고 합산이 0.9028이다. 블록 분산을 불확실성으로 읽으면 안 되는 이유는
   [TASK50](TASK50.md)의 무처치 분포(`T12`)가 따로 있기 때문이다.

## 해석

- **(관찰)** 위 표들의 값과 대조 결과가 관찰이다.
- **(파생 해석)** B-1의 민감도는 "N=10을 뺐을 때 선정이 달라진다"는 사실이며, 어느 쪽이
  옳은 선정인지는 이 계산이 말하지 않는다. 평가 seed의 비용 비는 세 조건 모두에서 1보다
  작으므로 세 선정 전부가 `BASE`보다 낫다고 예측된다.
- **(해석하지 않음)** §B-1·§B-2의 표에는 판정을 붙이지 않았다. 지시가 표만 요구했고,
  반복별 값에 구간을 붙이는 것은 [TASK50](TASK50.md)이 세운 원칙에 어긋난다.

## 확인되지 않은 사항

- 원고의 어떤 문장이 어느 표를 인용하는지 (`UNKNOWN`). 원고가 저장소 밖이라 대응을
  저장소 쪽에서 확인할 수 없다. 표 id는 이 저장소의 것이며 원고 번호가 아니다
- `T11`의 artifact 크기는 **현재 디스크 상태**다. `models/`는 git이 추적하지 않으므로
  측정 시점의 크기와 같다는 보장은 manifest가 있는 artifact에만 있다
- `check_claims.py`를 살릴지 지울지 (사용자 판단, [TASK65](TASK65.md)의 미해결 항목)

## 실패 / 무효 시도

- `prefill_tax.py`를 [TASK22](TASK22.md) run 루트에 대고 돌리면 `runs: []`가 나온다.
  glob 대상이 `<RUN>/probe/prefill_tax.*.json`이기 때문이다. script는 고치지 않고
  올바른 `--input-dir`를 `results/tables/README.md`의 선행 명령에 적었다.

## 연구 원칙에 미치는 영향

원칙 9(관찰·파생 해석 분리, population·unit·source·device scope 기록)와 원칙 10(provenance)
그대로다. 여기에 더해 **보고되는 수치는 저장소의 집계 파일에서 나와야 하고, 그 파일은
생성 명령과 입력 artifact를 자기 안에 적어야 한다**를 실무 규칙으로 세웠다.
`results/`의 git 제외 원칙은 유지하되 `results/tables/`만 예외로 한다 — 원자료가 아니라
원자료에서 나온 산출물이기 때문이다.

## 다음 작업

사용자 지시가 있을 때만 착수한다.

1. §B-3 되먹임 절제 스위치 (`--fix-arrivals`) — [TASK68](TASK68.md)
2. §B-4 dummy block 모형 반영 스위치 (`--dummy-block`) — [TASK69](TASK69.md)
3. `check_claims.py` 등 원고 전용 도구 4건의 처분 ([TASK65](TASK65.md) 판단 요청)

## 재현 정보

- 시작 commit: `ac1b7d8`
- 선등록 commit: **해당 없음** — 새 측정이 없는 재집계·계산이다
- 전체 생성: `env -u PYTHONPATH python3 experiments/npu/analysis/make_tables.py --all`
- 선행 명령 전문: [`results/tables/README.md`](../../results/tables/README.md)
- 민감도 실행: `results/npu/stage2/20260922-config-search-sensitivity/{sum-seconds,per-n}_{6_8,6_8_10,8_10}/`
  (`ledger.json`·`ledger.csv`·`comparison.json`·`meta.json`, `results/`는 gitignore 대상)
- 산출: `results/tables/` (표 20개 × `.md`/`.csv`, `README.md`, `manifest.json`) — **추적됨**
- 예산: 측정 0, serving lifecycle 0, 재compile 0, device 접근 0
