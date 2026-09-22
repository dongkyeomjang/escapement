# TASK66 — 재사용 실패의 추가 비용: `T(C)` 대 `T(L) − T(L−C)`의 L 의존성

## 상태

DONE

## 날짜

2026-09-22

## 목적

외부 검토 지적에 답한다. 지적의 요지는 "재사용 실패의 추가 비용을
`ΔT̂ = T̂_prefill(L) − T̂_prefill(L−C)`로 정의했다면 그 값은 C만이 아니라 재도착
prompt 전체 길이 L에도 의존하는데, 본문은 C만 적어 두었다"는 것이다. 비용식에
`ceil(q/128)` 올림 항과 길이 drift 선형 항이 있으므로 같은 C라도 L이 다르면 값이
달라진다는 지적 자체는 식에서 옳다.

검토자는 원 자료에서 "약 131 ms"와 "약 272 ms"를 계산할 때 쓴 L을 확인하라고
요구했다. 이 TASK는 **그 계산이 저장소의 어느 코드에서 나오는지 찾고, 관측된
재도착 요청 전체에 대해 두 정의의 값을 실제로 계산해 표로 고정**한다.

## 배경

관련 TASK:

- [TASK22](TASK22.md) — `PrefillCostModel` 적합. `prefill_s(n) = ceil(n/128) × (0.021206 + 6.399e-07 × n)`, 4점 적합 최대 잔차 2.4 ms, **적합 구간 [500, 6000] token**
- [TASK24](TASK24.md) — 재사용 범위 규칙(`floor(min(shared, query−1)/128)×128`), 층 2 캐시는 prefill 계산분만 담는다 (271/271)
- [TASK54](TASK54.md) — `mb`/`mb6` × `AGENTIC`/`CONVENTIONAL` 짝 실행. 이 TASK가 쓰는 재도착 요청 자료의 출처
- [TASK57](TASK57.md) — 그 배치에서 재사용 범위 규칙 95/95 확인, turn-1 168건 중 73건이 `cached_tokens = 0`
- [TASK59](TASK59.md) §2-5 — **기존 코드가 독립형 `T(C)`를 쓴다**는 점과 두 형태의 차이를 구성한 (L, C) 쌍에서 최대 27.8 ms로 기록
- [TASK65](TASK65.md) — 논문 텍스트를 저장소에서 제거. 원고는 사용자가 저장소 밖에서 관리한다

근거표: `PROVENANCE_3_2.md` 3.2.6행(직전 prefill 범위 800–1,600, 재사용 가능분
768–1,536), `EVIDENCE_3_3.md` 주장 8·11.

## 시작 상태

- 시작 commit `7a64166`(TASK65 후속 정정), `git status --short`는 `?? .idea/`만
- `main`은 `origin/main`과 같음
- 새 측정 없음. 기존 artifact `results/npu/stage2/20260908-133635-grid-paired/` 재집계
- 저장소에 논문 텍스트가 없으므로 검토 대상 문장(3.2.5·3.3.4)은 직접 읽지 못했다

## 수행 내용

1. **두 수치의 출처 추적.** `131`·`272`를 현재 작업트리 전체(`docs/`, `paper/`,
   `src/`, `experiments/`)와 **모든 commit의 `*.md`·`*.tex`·`*.py`** 에서 찾았다
   (`git log --all` 순회 + `git grep`). 제거된 원고 34개 파일도 `bf30461` 시점
   내용으로 검색했다.
2. **비용식 소비처 확인.** `prefill_s`를 호출하는 코드를 전수 확인했다 —
   `experiments/npu/analysis/config_device.py:84`, `src/continuum/sim/engine.py:465`.
   둘 다 요청의 실계산량에 대한 **독립형 `T(C)`** 이며, 증분형 `T(L) − T(L−C)`를
   계산하는 코드는 **저장소에 없다.**
3. **관측 자료에서 두 정의를 계산.** `experiments/npu/analysis/reuse_cost.py`를
   새로 만들어 TASK54 배치의 turn-1 요청 168건을 turn-0에 join하고, C는
   `SubstrateDescriptor.hit_formula`로, 시간은 `prefill_cost_model`로 계산했다.
   두 모형 모두 코드에서 import하며 상수를 다시 적지 않는다.
4. **검토자 예시의 관측 가능성 확인.** 이 워크로드에서 L과 C가 독립으로 움직이는지
   `L − C` 분포로 확인했다.

## 변경된 파일

- `experiments/npu/analysis/reuse_cost.py` (신규)
- `docs/research/TASK66.md` (신규), `docs/research/INDEX.md` (갱신)

원고는 저장소 밖에 있으므로 수정하지 않았다. 기존 TASK·근거표·코드는 수정하지
않았다.

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/reuse_cost.py \
    --json results/npu/stage2/reuse_cost.json
```

새 측정 없음. `requested_condition` / `observed_condition` / `condition_reached`는
해당 없음(재집계).

- population: TASK54 배치 `mb`·`mb6` × `AGENTIC`·`CONVENTIONAL` × n∈{6,8} × 3반복의
  **turn-1 요청 168건**. hit 95 / miss 73
- unit: ms (device 점유시간 1회분. 동시 decoder 수를 곱하지 않은 값)
- source: `probe/requests.*.jsonl`의 `prompt_tokens`·`cached_tokens`
- device scope: 요청 1건의 prefill 1회

## 결과

### 1. "131 ms"와 "272 ms"는 이 저장소에서 재현되지 않는다

`131`·`272`를 담은 문자열은 **작업트리에도, 전체 commit 이력에도 없다**(제거된
원고 34개 포함). 두 수치를 만든 코드 경로도 없다. 따라서 **그 계산에 쓴 L을
저장소에서 확인할 수 없다.**

### 2. 기존 코드가 쓰는 정의는 증분형이 아니라 독립형이다

| 호출 지점 | 인자 | 형태 |
|---|---|---|
| `experiments/npu/analysis/config_device.py:84` | `max(prompt_tokens − cached_tokens, 0)` | `T(C)` |
| `src/continuum/sim/engine.py:465` | `computed` | `T(C)` |

`T(C)`는 정의상 **L에 의존하지 않는다.** [TASK59](TASK59.md) §2-5에 이미 등록된
사실이다.

### 3. 관측된 168건에서 계산한 두 정의의 값

`C`는 [TASK24](TASK24.md) 규칙으로 얻은 재사용 가능분이며, 168건 전부에서
`cached_tokens`가 0이거나 정확히 C였다(168/168).

| C (token) | 요청 수 | hit | L 범위 | `T(C)` (ms) | `T(L) − T(L−C)` (ms) | 같은 C 안의 폭 (ms) |
|---:|---:|---:|---|---:|---|---:|
| 768 | 8 | 4 | 1,004–1,044 | 130.18 | 132.07–132.72 | 0.65 |
| 896 | 28 | 17 | 1,013–1,191 | 152.46 | 153.55–155.50 | 1.94 |
| 1,024 | 44 | 20 | 1,093–1,408 | 174.89 | 175.90–178.82 | 2.92 |
| 1,152 | 20 | 12 | 1,361–1,490 | 197.49 | 200.17–201.65 | 1.48 |
| 1,280 | 20 | 12 | 1,345–1,561 | 220.25 | 221.49–224.51 | 3.02 |
| 1,408 | 28 | 17 | 1,526–1,694 | 243.18 | 244.91–247.89 | 2.98 |
| 1,536 | 20 | 13 | 1,653–1,757 | 266.27 | 268.15–269.93 | 1.78 |

- 독립형 전체 범위: **130.18 – 266.27 ms**
- 증분형 전체 범위: **132.07 – 269.93 ms**
- 증분형 − 독립형: **+1.01 – +4.72 ms**
- **어느 정의로도 272 ms가 나오지 않는다.** 이 population에서 가능한 최대값은
  269.93 ms다. 131 ms는 증분형 아래에서 L ≈ 852(C=768) 또는 L ≈ 1,899(C=1,536)
  에서 나오지만, **그 (L, C) 조합은 이 자료에 없다.**

### 4. 이 워크로드에서 L과 C는 독립이 아니다

| 항목 | 값 |
|---|---|
| 직전 prompt L₀ | 803–1,576 token |
| 재도착 prompt L | 1,004–1,757 token |
| L − C | **65–384 token** (중앙값 212) |

C는 L₀를 128로 내린 값이고 L은 L₀에 그 turn이 덧붙인 만큼이다. 따라서 C가 정해지면
L의 가용 범위가 좁게 따라온다. 검토자가 든 반례 "C=768, L=1,700"은 `L − C = 932`
로 **관측 범위(65–384) 밖이며 이 워크로드에서 발생하지 않는다.**

### 5. [TASK59](TASK59.md)의 "최대 27.8 ms" 차이는 구성된 쌍의 값이다

[TASK59](TASK59.md) §2-5의 27.84 ms는 `L = 6,000, C = 500`에서 나온 값이다.
**관측된 population에서 두 정의의 차이는 1.01–4.72 ms**로 한 자릿수 ms다. 27.8 ms는
상한 예시이지 이 자료의 값이 아니다.

## 핵심 발견

1. **`universal`** — **증분형 `T(L) − T(L−C)`는 L에 의존하므로 C만으로 수치를
   보고할 수 없다.** 검토 지적은 식 수준에서 옳다. 올림 항이 있는 어떤 비용식에도
   해당하며 substrate와 무관하다.
2. **`stack`** — **이 저장소의 모든 소비처는 독립형 `T(C)`를 쓴다**
   (`config_device.py:84`, `sim/engine.py:465`). 이 형태는 L에 의존하지 않으므로
   같은 지적이 적용되지 않는다. 형태의 선택은 구현 결정이고, 그 값(130–266 ms)은
   이 substrate의 상수다.
3. **`stack`** — **관측된 168건에서 두 정의의 차이는 1.01–4.72 ms**이며, 같은 C
   안에서 L 때문에 생기는 폭은 **최대 3.02 ms**(C=1,024·1,280 구간)다. 지적된
   L 의존성은 이 자료에서 존재하되 한 자릿수 ms다.
4. **`class`** — **대화형 재도착 워크로드에서 L과 C는 독립 변수가 아니다.**
   재사용 가능분은 직전 prompt에서 파생되고 재도착 prompt는 그 prompt의 확장이므로
   `L − C`가 "그 turn이 덧붙인 양"으로 묶인다. 기전이 자료구조가 아니라 대화
   구조에서 나오므로 다른 stack에서도 같은 결합이 예상된다. **다만 결합의 폭
   (여기서 65–384 token)은 워크로드 상수다.**
5. **`universal`** — **저장소에 없는 수치는 provenance를 갖지 못한다.** 131·272는
   전체 commit 이력에 없고 재현 경로도 없다. 원고 텍스트를 저장소 밖으로 옮긴
   [TASK65](TASK65.md) 이후, 원고의 수치가 저장소 산출물과 어긋나도 저장소 쪽에서
   탐지되지 않는다는 점이 이번에 드러났다.

## 해석

- **(관찰)** 두 정의의 값, 그 차이, L−C 분포는 위 표 그대로다.
- **(파생 해석)** 원고의 131·272는 (a) 다른 cost model 상수, (b) 이 자료가 아닌
   다른 population, (c) 위 표의 132/270을 반올림·전사하는 과정의 오기, 셋 중
   하나로 보인다. **어느 쪽인지 저장소 자료만으로는 가를 수 없다(`UNKNOWN`).**
   다만 269.93 ms가 이 population의 상한이므로 272는 (c)의 단순 반올림으로는
   설명되지 않는다.
- **(제언)** 검토자가 제시한 A(L 명시)·B(범위로 한정) 중에서는 **B가 이 자료에
   맞고**, 더 나은 세 번째 선택지는 **본문의 정의를 코드가 실제로 쓰는 독립형
   `T(C)`로 바꾸는 것**이다. 그러면 L 의존성이 원리적으로 사라져 지적이 닫히고,
   본문과 `config_device.py`·`sim/engine.py`의 계산이 같은 식이 된다. 어느 쪽이든
   수치는 위 표의 값으로 바꿔야 한다. **이 판단은 원고 소관이므로 이 TASK에서
   원고를 고치지 않았다.**

## 확인되지 않은 사항

- 원고의 131 ms·272 ms가 어떤 계산에서 나왔는지 (`UNKNOWN`). 저장소에 경로가 없다
- C < 500 token 구간의 비용 (`UNKNOWN`, [TASK22](TASK22.md) 적합 구간 밖). 이 표의
  C는 전부 768 이상이라 이번 값들은 적합 구간 안이다
- 두 정의 중 어느 쪽이 실제 device 거동에 더 가까운지 (`UNKNOWN`). 부분 재계산의
  prefill 시간을 직접 잰 관측점이 없다 — [TASK22](TASK22.md)의 4점은 전부
  `cached_tokens = 0`인 전량 계산이다

## 실패 / 무효 시도

없음. 다만 `131`·`272`의 출처 추적은 **찾지 못하고 종료**했다(위 결과 1).

## 연구 원칙에 미치는 영향

원칙 9(관찰·파생 해석·hypothesis 분리, metric의 population·unit·source·device scope
기록)와 원칙 14(관측 불가 항목을 임의 값으로 채우지 않는다)를 그대로 적용했다.
[TASK65](TASK65.md) 이후 **원고 수치와 저장소 산출물의 정합을 저장소 쪽에서 보증할
수 없다**는 점이 새로 드러났다. 원고에 들어가는 수치는 저장소의 재집계 script가
출력한 값을 그대로 쓰는 편이 안전하다.

## 다음 작업

사용자 지시가 있을 때만 착수한다.

1. 원고 3.2.5·3.3.4의 정의와 수치를 위 표로 정정 (원고는 저장소 밖)
2. 원고에 들어간 다른 수치들도 같은 방식으로 저장소 산출물과 대조

## 재현 정보

- 실행 script: `experiments/npu/analysis/reuse_cost.py`
- 명령: `env -u PYTHONPATH python3 experiments/npu/analysis/reuse_cost.py --json results/npu/stage2/reuse_cost.json`
- 입력 artifact: `results/npu/stage2/20260908-133635-grid-paired/{mb,mb6}/probe/requests.{AGENTIC,CONVENTIONAL}.n{6,8}.b{0,1,2}.jsonl`
- 출력: `results/npu/stage2/reuse_cost.json` (ignored artifact, commit하지 않음)
- 비용 모형: `experiments/npu/substrate/rbln_ca25_vllm_rbln_0111.py`의 `PREFILL_COST`·`HIT_FORMULA` ([TASK22](TASK22.md), [TASK24](TASK24.md))
- 시작 commit: `7a64166`
- 선등록 commit: **해당 없음** (새 측정이 없는 재집계 TASK)
