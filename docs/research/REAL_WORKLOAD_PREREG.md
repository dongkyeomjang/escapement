# 선등록 — 현실 tool latency 워크로드 전환과 headroom 재검증

## 문서 성격

[CLAUDE.md](../../CLAUDE.md) 실행 원칙 16과 [TASK_GUIDE.md](TASK_GUIDE.md)가 요구하는 **선등록(preregistration)** 이다. 이 문서를 담은 commit 이후에 측정을 시작한다. **측정 후 판정 기준을 완화하지 않는다.**

## 왜 워크로드를 바꾸는가

[TASK17](TASK17.md) 이래 모든 실험의 tool gap은 `uniform:1:5` 초였다. **그 분포는 세션을 흩뜨리기 위해 고른 것이지 어떤 도구가 그렇게 행동해서가 아니다.** 이 연구의 모든 결론은 "세션이 언제 돌아오는가"에 대한 주장이므로 gap 법칙은 harness의 세부가 아니라 **독립 변수**다.

[TASK30](TASK30.md)의 정확도 문턱 σ*(0.74–1.27 × gap 표준편차 = 1.06–1.82 s)도 그 합성 분포의 값이라 **예측기 판정의 분모가 되지 못한다.**

## 워크로드의 출처와 재구성

**원자료**: `/home/rebel/vllm-continuum/results/tracelab/summary.json` — legacy 저장소가 공개 coding-agent trace(665,453 rows / 743,819 tool calls / 8,058 sessions)에서 **자체 재계산한 산출물**이다. **read-only로만 읽었고 legacy를 수정하지 않았다.** 원 gz(`/mnt/ssd/tracelab/…`)는 접근 불가이므로 이 산출물이 유일한 근거다.

**재구성 방식** (`src/continuum/workload/tools.py`)

1. 도구별 `(n, p50, p90, p99)`를 읽는다(단위 ms).
2. **human-in-the-loop 4종**(`AskUserQuestion`, `ExitPlanMode`, `request_user_input`, `TaskOutput`, 전체의 0.39 %)을 제외한다. 사람 지연이지 도구 지연이 아니며, 원 분석의 보수적 `δ_tool` 정의와 같은 취지다.
3. 남은 **43종 739,461 호출**로 population을 만든다. 호출 빈도로 도구를 뽑고, 그 도구의 역CDF에서 지연을 뽑는다.
4. 역CDF는 측정 분위수를 **정확히 통과**한다 — `p50`·`p90`·`p99` 사이는 로그 선형 보간, 중앙값 아래만 같은 로그 분산의 log-normal로 채운다. **적합(fitting)이 아니라 보간이다.**
5. **cap 60 s.** 그 위는 미측정 구간이고 serving 실험에서는 이미 떠난 세션이다. **걸린 비율 2.51 %를 보고한다.**

**독립 검증** (이 클래스가 읽지 않는 통계와 대조)

| 항목 | 재구성 | summary가 별도 보고 |
|---|---|---|
| `P(latency < 1 s)` | **70.7 %** | claude 71.31 % / codex 66.89 % |
| p50 | 0.157 s | 0.115 / 0.151 s |
| p90 | 11.08 s | 10.10 / 10.04 s |

유형 혼합비(측정 중앙값 기준 구간): `fast` 56.6 %, `medium` 27.9 %, `slow` 13.0 %, `instant` 2.5 %.

**합성 gap과의 대비**: `uniform:1:5`는 평균 2.88 s·표준편차 1.44 s·범위 1–5 s. 재구성 분포는 평균 4.18 s·표준편차 11.27 s·중앙값 0.157 s. **중앙값이 18배 작고 표준편차가 8배 크다.**

## 승인 범위 (사용자 판정, 2026-08-23)

serving 기동·종료, 기존 관측 스택, `src/continuum/` 코드 추가·수정, legacy의 **read-only 열람**(TraceLab 산출물 한정).

범위 밖: 재compile, download, patch 변경, RSD 변경, legacy 수정, GPU 서버 작업, remote push 자동 수행.

## Substrate 상태

측정 전 `apply.sh status`가 `patched`(SHA256 `70942d16…`)가 아니면 시작하지 않는다. 격자는 `(1, 2, 4, 8)`, artifact는 `models/Qwen3-4B-rbln-b8-s8192-d4-mb`다.

## 실험 격자

| 항목 | 값 |
|---|---|
| N | **6, 8, 10** |
| arm | **`IMMEDIATE`만** (정책 비교가 아니라 baseline 연속성 확인) |
| block | b0, b1, b2 |
| 총 조합 | **9** |
| plan seed | `base_seed = 20260910` |
| gap | `toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60` |
| 그 외 | [TASK20](TASK20.md) 이래와 동일 (`first uniform:800:1600`, `later fixed:8`, `generation uniform:32:256`, turns 2) |
| server | 조합마다 fresh, `--enable-prefix-caching --enable-prompt-tokens-details` |

## 선등록 예측 — 새 gap 법칙에서의 out-of-sample 검사

[TASK30](TASK30.md)의 시뮬레이터(commit `b86b2e6`)로 계산했다. **gap 법칙이 완전히 바뀌었으므로 이것은 시뮬레이터에 대한 새로운 out-of-sample 검사이기도 하다.**

| N | 예측 utilization (step 가중) | 블록별 | 예측 재사용 | 예측 busy (s) |
|---|---|---|---|---|
| 6 | **0.8081** | 0.7718 / 0.7713 / 0.8683 | **15/18 (83.3 %)** | 26.71 |
| 8 | **0.8874** | 0.9015 / 0.8835 / 0.8692 | **13/24 (54.2 %)** | 32.69 |
| 10 | **0.9236** | 0.9221 / 0.9266 / 0.9223 | **7/30 (23.3 %)** | 46.03 |

## 판정 기준

### 연속성 확인 (측정, 확증)

**utilization**: `|예측 − 실측|` step 가중 utilization이 **≤ 0.03** (세 N 전부). [TASK25](TASK25.md)·[TASK28](TASK28.md)에서 관측된 오차(0.002–0.021)를 고려한 값이며, gap 법칙이 새로우므로 기존보다 넉넉히 잡는다.

**재사용**: 실측 재사용률이 예측의 **±20 %p 이내**. [TASK25](TASK25.md)가 "개수는 맞고 귀속은 어긋난다"를 기록했으므로 개수 수준에서만 건다.

| 결과 | 판정 |
|---|---|
| 세 N 전부 두 조건 만족 | `PASS` |
| 일부만 | `PARTIAL` — 어느 N이 왜 빗나갔는지 기록 |
| 전부 실패 | `FAIL` — 시뮬레이터가 새 gap 법칙으로 전이되지 않는다는 뜻이며, 그 자체가 결과 |

### headroom Gate (계산, 다음 작업의 진행 조건)

**지시문이 정한 문턱을 그대로 쓴다: ε = 2 s에서 oracle 절감이 ≥ 5 %.**

| 결과 | 판정 |
|---|---|
| N ∈ {6, 8, 10} 중 **과반(2개 이상)** 에서 ε=2 s oracle 절감 ≥ 5 % | `PASS` → 다음 작업 진행 |
| 그 외 | `FAIL` → **현실 gap에서는 headroom이 없다**는 것이 결과이며 예측기 작업을 하지 않는다 |

**동시에 [TASK30](TASK30.md)의 σ*를 이 워크로드에서 다시 계산한다.** 그 값이 예측기 판정의 분모다.

## 불변식 (fail-loud, 위반 조합은 `INVALID`)

- I1–I5: [NSLOTS_SWEEP_PREREG.md](NSLOTS_SWEEP_PREREG.md)와 동일. bucket 집합 `{1, 2, 4, 8}`
- **W1**: 실측 plan의 gap이 선등록 seed에서 재생성한 gap과 소수 6자리까지 일치 — 워크로드 전환이 재현 가능함을 확인한다
- **W2**: `held_s = 0` 전건 (`IMMEDIATE` arm이므로)

## 필수 측정 항목

조합별: per-request JSONL, plan summary(`tool_mix` 메타 포함), `[BUCKET]`·`[PFX]` 로그 전문, `/metrics` 덤프, utilization JSON. 전체: patch state, `rbln-smi`, provenance, 측정 시작·종료 시각, 선등록 commit.

## 실행 절차 (측정 전 고정)

`<RUN>` = `results/npu/stage2/<timestamp>-real-workload`

```bash
SWEEP_BASE_SEED=20260910 \
SWEEP_GAP='toolmix:/home/rebel/vllm-continuum/results/tracelab/summary.json:60' \
  bash experiments/npu/stage2/run_sweep.sh <RUN> IMMEDIATE <6|8|10> <0|1|2> none
```

**실행 중인 실험의 script를 편집하지 않는다** ([TASK23](TASK23.md)의 연쇄 실패 원인).

## 관련 문서

- [TASK30](TASK30.md) — 예지 가치 곡선과 σ*. 이 워크로드에서 다시 계산할 대상
- [TASK26](TASK26.md) — oracle bound. headroom gate의 정의
- [TASK28](TASK28.md) — 시뮬레이터의 개입 조건 예측력, 2채널 관측
- [TASK20](TASK20.md) — 합성 gap 시절의 baseline. 연속성 대조 상대
