# 계산 전 정의 — compile 구성 탐색의 재실행과 provenance 복원

## 문서 성격

[CLAUDE.md](../../CLAUDE.md) 실행 원칙 16에 따라 **대조 기준과 산출물 정의를 계산 전에 commit**한다. 이 문서와 `experiments/npu/analysis/config_search_rerun.py`를 담은 commit **이후에** 탐색을 재실행한다. 계산 후 대조 기준을 바꾸지 않는다.

성격은 **시뮬레이터 재실행**이다. 실측 0, compile 0, serving 기동 0, device 접근 0. 목적은 새 결과가 아니라 **기존 선정을 독립적으로 대조할 수 있게 만드는 것**이다(Advisor 지시, 2026-09-11).

## 공백

[COMPILE_CONFIG_PREREG.md](COMPILE_CONFIG_PREREG.md)(commit `4e12b30`)와 [TASK34](TASK34.md)은 후보 2,077개를 탐색 seed로 순위화하고 평가 seed로 채점해 `decoder_batch_sizes = (1,4,6,8,10,16)`, `batch_size = 16`, 평가 ratio **0.9066**을 얻었다고 적었다. **탐색 실행 명령과 후보별 결과 파일은 남아 있지 않다.** `results/`는 `.gitignore` 대상이고, [TASK34](TASK34.md)의 raw artifact 목록(`results/npu/stage2/20260823-170201-compile-config/`)에도 탐색 출력이 없다.

## 계산 전 이미 확인한 사실 (공시)

이 commit 전에 아래 두 가지를 확인했다. 둘 다 후보 순위나 선정 대조에 쓰이는 값이 아니다.

1. **후보 수 산술.** 선등록 정의(총 bucket 수 ≤ 6)로 세면 8/10/12/16별 57/163/386/1,471, 합계 **2,077**이다. **commit된 `config_search.py`의 loop를 기본값(`--max-buckets 6`)으로 돌리면 4,393개**가 나온다. loop가 `range(0, max_buckets)`를 **중간 bucket 수**로 쓰기 때문에 기본값이 총 bucket 7개까지 허용하는 것이다. `--max-buckets 5`면 2,077개이고, 선등록 정의와 **순서까지 같은 목록**이다. **원래 탐색이 어느 인자로 실행됐는지는 기록이 없어 `UNKNOWN`이다.**
2. **시간 측정 1회.** 기준 구성 `(1,2,4,8)`·batch 8의 평가 seed 27칸 busy 합을 한 번 계산했다(277.10318 s, 0.04 s 소요, 같은 process에서 두 번 계산해 bit 동일). 후보는 하나도 채점하지 않았다.

또한 `config_search.py`, `src/continuum/sim/`, `experiments/npu/substrate/`, `foresight.py`는 `4e12b30` 이후 **변경 이력이 없다**(`git log 4e12b30..HEAD` 빈 출력). plan seed는 `hashlib.sha256` 기반 `derive_block_seed`에서 나오고 Python `hash()`를 쓰지 않는다.

## 재실행 정의

| 항목 | 값 |
|---|---|
| 후보 | `batch_size` ∈ {8,10,12,16}. bucket 집합은 1과 `batch_size`를 포함하고 중간 bucket은 그 사이 정수, **총 bucket 수 ≤ 6**, 예상 compile 시간 `42.3 + 61.33 × (bucket 수 + 1)` ≤ 1,800 s |
| 탐색 seed | 20260910, 20260921, 20260932 |
| 평가 seed | 20260943, 20260954, 20260965 |
| 셀 | N ∈ {6,8,10} × block {0,1,2} × seed 3개 = 27칸/seed군 |
| gap | `toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60` (read-only) |
| 채점 | `config_search.score`·`descriptor_for`·`compile_cost`를 **그대로 import**. 후보 `max_running = batch_size`, 기준 `max_running = 8` |
| ratio | `config_search.main`과 **같은 합산 순서**로 `Σ 후보 busy / Σ 기준 busy` |
| 순위 | 탐색 ratio 오름차순 **stable sort**(동률은 열거 순서 유지 — `config_search.main`과 같은 규칙) |
| 시뮬레이터·계수 | 현재 HEAD 그대로. descriptor 미변경 |

## 실행 (4회)

`<RUN>` = `results/npu/stage2/<timestamp>-config-search-rerun`

| id | 명령 | 목적 |
|---|---|---|
| A | `PYTHONHASHSEED=0 python3 experiments/npu/analysis/config_search_rerun.py --output-dir <RUN>/run-a` | 본 재실행, 후보별 전표 |
| B | 같은 명령, `PYTHONHASHSEED=1`, `--output-dir <RUN>/run-b` | 별도 process에서 결정성 확인 |
| C | `python3 experiments/npu/analysis/config_search.py --max-buckets 5 --output <RUN>/committed-mb5.json` | commit된 harness 자체의 출력과 bit 대조(기준 구성을 후보마다 다시 시뮬레이션한다) |
| D | `python3 experiments/npu/analysis/config_search.py --output <RUN>/committed-default.json` | **보조.** commit된 기본값(4,393개)의 최솟값 — 보고만 한다 |

## 대조 기준

| 질문 | `일치` | 그 외 |
|---|---|---|
| **Q1 후보 수** | 재구성 집합 크기 = 2,077 | 크기와 차이의 원인을 보고 |
| **Q2 선정** | 탐색 ratio 최솟값이 **유일**하고 그 구성이 `(1,4,6,8,10,16)`·batch 16 | 최솟값이 bit 동률이면 `동률` — 동률 집합, 기록 구성의 포함 여부, stable sort가 고르는 구성을 보고. 기록 구성이 최솟값이 아니면 `불일치` — 그 순위와 최솟값과의 차를 보고 |
| **Q3 평가 ratio** | 기록 구성의 평가 ratio를 소수 넷째 자리로 반올림한 값 = 0.9066 | 차이의 크기를 보고 |
| **Q4 결정성** | A·B의 `ledger.json`이 byte 동일, **그리고** C의 후보별 `explore_ratio`·`eval_ratio`가 A와 2,077개 전부 bit 동일 | 다른 후보 수와 최대 절대차를 보고 |

- **Q3의 분해능 한계**: 기록값이 넷째 자리까지라 **±0.00005 안의 차이는 판별할 수 없다.** 재실행 값은 전 자릿수로 함께 적는다.
- **Q3 보조**: 선등록 문서의 축별 귀속 표도 같은 방식으로 대조한다 — batch만 `(1,2,4,8,16)`·16 = 0.9279, bucket만 `(1,4,6,8)`·8 = 0.9929.
- **해석 금지**: "선정이 옳았다"류 평가를 하지 않는다. 불일치가 나오면 원인을 추정하지 않고 **어느 단계에서 갈라지는지**(열거 / 탐색 순위 / 평가 채점)만 좁힌다.

## 산출물

- `<RUN>/run-{a,b}/ledger.json` — 후보별 구성, compile 예상, 탐색·평가 busy 합(s)·ratio·N별 ratio. 계산값만 담아 byte 대조가 가능하다
- `<RUN>/run-{a,b}/ledger.csv` — 같은 내용의 평면 표(float는 `repr`)
- `<RUN>/run-{a,b}/comparison.json` — Q1–Q3 대조값
- `<RUN>/run-{a,b}/meta.json` — 명령, 시작·종료 시각, 소요 시간, HEAD, 입력 파일 SHA256, gap 파일 SHA256, Python 버전
- `<RUN>/committed-{mb5,default}.json` — commit된 harness의 출력

`results/`는 git이 추적하지 않으므로 **TASK 문서에 산출물 SHA256과 상위 20 순위표를 옮겨 적는다.**
