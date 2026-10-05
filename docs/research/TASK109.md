# TASK109 — 원고 보완용 자료 추출과 대기열 계산 (지시문 15)

## 상태

DONE

## 날짜

2026-10-05

## 목적

Advisor 지시문 15. 외부 검토의 "재현할 수 없다" 지적에 대해 원고 재료만 만든다: 해석 모형 수식(A), 정의·집계 방식(B), 통계 방법(C), 실험별 선등록 대조표(D), 예측 대 관측 대기열 계산(E), 특성표 입력 범주(F). **측정·새 예측·모형 수정·원고 문장 없음.**

**측정 0.**

## 배경

- 모형 v1([MODEL_V1.md](MODEL_V1.md)), 시뮬레이터(TASK89·103), 판정 절차(MULTITURN_MAIN_PREREG 개정 2), 관측 대기열(TASK96·105)

## 시작 상태

- HEAD `63b4bcc`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. 작업 A·B+C·D+F는 background subagent 3개가 병행 작성했고, 주 agent가 검토했다. 작업 E는 주 agent가 계산했다.
2. 작업 E: 측정 전 commit된 예측 파일에 대기열 길이가 없어, 같은 plan·descriptor·비용 파일·코드로 시뮬레이터를 다시 돌려 decode step마다 대기 요청 수(#arrival ≤ t − #admit ≤ t)를 셌다(`experiments/npu/analysis/queue_pred_vs_obs.py`). 해석 모형은 고정점 마지막 반복의 점유 분포로 Σπ(n)·max(0, n − M). **33 cell 전부 재계산 재사용률이 선등록 예측 파일과 정확히 같았다.** GPU는 GTASK14 표의 관측·원래 sim LRU 대기열을 출처로 썼다.

## 변경된 파일

- `paper/{MODEL_EQUATIONS, DEFINITIONS, STATISTICS, PREREG_TABLE, PROFILE_INPUTS, QUEUE_PRED_VS_OBS}.md`(신규), `paper/RESULTS_INDEX.md`(§20)
- `experiments/npu/analysis/queue_pred_vs_obs.py`(신규)
- `docs/research/TASK109.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/queue_pred_vs_obs.py --output results/npu/stage3/queue_obs/queue_pred_vs_obs.json
```

## 결과

- **A — 문서와 코드가 다른 곳 12건**(`MODEL_EQUATIONS.md` §6, 코드 기준으로 씀): s_active가 문서는 대상별 P(q_T) + (g_T − 1)t/φ, 코드는 평균 서비스 시간 S̄(D1); s_idle 정의(D2); t(n̄)의 n̄ 가중(D3); 초기 a0 clip(D4); 재사용–prefill 고정점이 문서에 없음(D5); 반환 h·X·φ가 이전 반복 값(D6); 기호 G(D7); Z(D8); DP 최소 범위(D9, 동치); LRU 형태(D10); underflow 문턱(D11); K_pin 대체(D12, 충돌 아님). 생존 흡수 확률은 행렬 지수가 아니라 uniformization.
- **B — 채널 B**: 정상 상태 실험(TASK82·87·95·102, GTASK11·20)에서는 정의·계산·판정에 쓰지 않았다(TASK75: 정상 상태에서 client in-flight 합집합이 wall time으로 수렴 — 확인 시 창 점유 중앙 0.974–1.000). Stage 2 일치: TASK35 N8 0.0008·0.0035, N6 0.0205·0.0236(보류), TASK36 N6 0.0001·0.0063, TASK50 무처치 q95 0.0604·0.0320. 사후 계산: 정상 상태 21 cell |m_A′ − m_B| 중앙 0.0137. GPU는 직접 dispatch 채널(GTASK10 ≤ 0.005).
- **B — "최대 33 %"**: 저장소에 문자 그대로는 없다. 가장 가까운 값은 TASK102 TUNED N = 18, 채널 A′ turn당, 반복 짝 비 중앙 0.6710 [0.6506, 0.7248](−32.9 %). 다른 집계·cell 후보도 표에 있다. **원고 문장이 무엇을 가리키는지 사용자 확인 필요.**
- **C**: k = 5에서 percentile bootstrap 95 % CI = 짝 비 5개의 [min, max](NPU 23·GPU 8 cell 확인) → "해소" = 5개가 모두 1의 한쪽(귀무에서 확률 0.0625). 재사용률에는 CI가 없다(0.10 허용치는 이항 근거). 순위: NPU 해소 26쌍 전부 일치(미해소 7), GPU 10쌍 일치(미해소 5).
- **D**: 10행(확증·탐색) + 사후 대조 + 파라미터 측정. 모든 예측 파일은 commit 1회 뒤 바뀌지 않았다. GPU 측정 시작은 문서 기록만 있다(raw 없음).
- **E**: 예측 대 관측 대기열 NPU 33 cell — 주 sim Pearson 0.999·Spearman 0.820·MAE 0.058, 해석 모형 0.999·0.911·0.220. BASE N ≥ 12에서 예측/관측 중앙 주 sim 0.876, 해석 0.656(과소). 문턱 Q = 0.1(관측을 보고 정한 값, 사후): 주 sim 33/33 같은 쪽, 해석 모형 32/33(N12 BASE). GPU 8 cell은 모두 같은 쪽(Pearson 0.996, 예측/관측 중앙 0.608).
- **F**: KV 규칙 7, 구성·실행 규칙, 성능 입력의 NPU·GPU 값과 출처. NPU의 미확정 field 6개(엔진이 읽지 않음), GPU 인스턴스 descriptor는 없고 테스트 descriptor 값.

## 핵심 발견

1. 측정 전 예측의 대기열로도 관측 기준과 같은 cell 분류가 나온다(시뮬레이터 33/33). 즉 "측정 전에 대기열 발생 여부를 판단해 예측 방법을 고르는" 절차가 이 데이터에서는 가능했다 — 단 문턱은 관측을 보고 정했다.
2. 해석 모형의 대기열은 대기열 영역에서 관측의 약 2/3로 과소하다.

## 해석

- 없음(자료 추출).

## 확인되지 않은 사항

- 원고 수치와의 대조: 원고가 저장소 밖에 있어 하지 못했다. "최대 33 %"만 후보를 찾았다.
- GTASK11 replicate별 값(GPU raw 없음), GPU 채널 B.
- 해석 모형 재사용 고정점(30회)의 수렴 여부 플래그는 코드가 남기지 않는다.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 없음.

## 다음 작업

- 사용자: 원고 수치와 이 자료의 대조.

## 재현 정보

- 위 명령, HEAD `63b4bcc`. 산출 `queue_pred_vs_obs.json`(비추적).
