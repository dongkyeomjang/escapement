# GTASK09 — GPU multi-turn 본 실험 plan·blind 예측·판정 기준 선등록, 파일럿 선등록

## 상태

DONE

## 날짜

2026-09-29

## 목적

GPU 지시문 G-03 작업 C와 작업 D의 선등록 부분.
- 본 실험 plan 20개(확증 N 20·22·24, 탐색 N 26)와 파일럿 plan 3개를 고정한다.
- 세 예측기(해석 v1 GPU 인스턴스, sim LRU, 반사실 sim FIFO)의 blind 예측과 판정 기준 제안을 **본 측정과 파일럿 전에** commit한다.
- 본 측정은 하지 않는다.

## 배경

- [GTASK07](GTASK07.md): 예측기
- [GTASK08](GTASK08.md): 구성
- NPU [MULTITURN_MAIN_PREREG.md](../MULTITURN_MAIN_PREREG.md) §4–§5, [STREAMING_PILOT_PREREG.md](../STREAMING_PILOT_PREREG.md)
- 본문: [GPU_MULTITURN_PREREG.md](GPU_MULTITURN_PREREG.md), [GPU_MT_PILOT_PREREG.md](GPU_MT_PILOT_PREREG.md)

## 시작 상태

- HEAD `cafbd95`(GTASK08)
- 멀티턴 측정값은 없다. 계기 점검 lifecycle 2개(아래)가 유일한 GPU 실행이다.

## 수행 내용

1. **계기 점검**
   - 별도 plan `gcheck-n3`(seed 20262900, N=3, gap U(0.2,1.0) s, 평가 20 s)로 runner와 측정 모듈을 실제 server에서 돌렸다. streaming·BASE와 non-streaming·POOL+GRID 두 경우다.
   - **측정 모듈의 client–server id join 오류를 찾아 고쳤다.** streaming 응답의 id는 `cmpl-X`이고 server id는 `cmpl-X-0-Y`다. 고친 규칙은 "client id가 server id의 prefix이고 뒤에 `-`가 온다"이다.
   - 고친 뒤 두 경우 모두 다음을 확인했다.
     - 유효
     - join 누락 0
     - **step mode 예측 불일치 0/1,306·0/1,307**(비용 모형의 FULL, PIECEWISE, NONE 판정 = 관측 `[GSTEP]` mode)
     - client–server `cached` 불일치 0
     - POOL+GRID 격자 `[1,5,7,8,16]`가 server에 적용됨
   - 이 값은 어디에도 쓰지 않는다.
2. **plan과 예측**: `predict_mt.py`로 본 실험 plan 20개와 파일럿 plan 3개를 만들었다. `cycle_s`는 해석 POOL 예측이다. 세 예측기 × 두 비용 bound로 계산했다(`PREDICTIONS.json`).
3. **선등록 문서 두 개**와 파일럿 순서(`plans/pilot/SCHEDULE.json`), 본 실험 순서 제안(`plans/main/SCHEDULE_PROPOSED.json`, seed 20262410)을 작성했다.
4. 파일럿 실행기(`run_schedule.py`, 세션과 분리해 실행)와 판정 script(`pilot_analyze.py`)를 작성했다.

## 변경된 파일

- `docs/research/gpu/GPU_MULTITURN_PREREG.md`, `docs/research/gpu/GPU_MT_PILOT_PREREG.md`, `docs/research/gpu/GTASK09.md` (신규)
- `docs/research/gpu/GPU_INDEX.md`
- `experiments/gpu/multiturn/{predict_mt.py, summarize_predictions.py, run_schedule.py, pilot_analyze.py}` (신규)
- `experiments/gpu/multiturn/gpu_mt_measure.py`(id join 수정)
- `experiments/gpu/multiturn/plans/{PREDICTIONS.json, main/*.json, pilot/*.json}` (신규)

## 실험 또는 검증 방법

```bash
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/predict_mt.py \
  --selection <abs>/experiments/gpu/multiturn/selection/selection.json \
  --plan-dir <abs>/experiments/gpu/multiturn/plans --out <abs>/experiments/gpu/multiturn/plans/PREDICTIONS.json
env -u PYTHONPATH /home/csdc/kyeom/envs/vllm-0.22.0/bin/python experiments/gpu/multiturn/summarize_predictions.py \
  <abs>/experiments/gpu/multiturn/plans/PREDICTIONS.json
```

Population: 본 실험 plan 20개(N 4 × 5), 파일럿 plan 3개. 예측은 plan별 시뮬레이션과 N별 해석 계산이다.
Source: 예측기(측정 아님).

## 결과

요약은 [GPU_MULTITURN_PREREG.md](GPU_MULTITURN_PREREG.md) §4에 있다.

- **재사용률(확증 cell)**: 해석 0.81–0.88, sim LRU 0.75–0.90, sim FIFO 0.61–0.83
- **LRU − FIFO 차**: 확증 9 cell 모두 0.079–0.170 → **판별 가능**(`NOT_TESTABLE` 아님)
- **POOL/BASE 비**: 해석 0.986–0.993, sim LRU 0.955–0.992. POOL+GRID/POOL은 0.995–1.002(해석 0.9991–0.9997)다.
- **§2.1 구간의 최대 영향**: turn당 0.05–0.13 ms(비용의 0.02–0.04 %)
  - 확증 cell의 PIECEWISE 혼합 step은 turn당 0.04–0.09개다.
  - 재도착 요청의 계산량 9–24 token에 running 약 7을 더하면 16 token을 넘어 대부분 eager다.
- **세 예측기가 크게 갈리는 cell**
  - N=24 BASE 재사용: 해석 0.807 / LRU 0.753 / FIFO 0.611
  - N=24 POOL 비용 비: 해석 0.986 / LRU 0.958
  - 탐색 N=26 BASE: 해석 0.786 / LRU 0.657 / FIFO 0.552
- **파일럿 사전 예측**: streaming `EQUIVALENT`

`requested_condition` 등: 해당 없음(측정 없음).

## 핵심 발견

1. **`stack`** — **GPU의 multi-turn 재도착 요청은 대부분 eager 혼합 step으로 실행된다.**
   - 재도착 요청은 새 token 9–24개만 계산하지만, running 약 7과 합치면 기본 격자의 최상위(16)를 넘는다.
   - 그래서 G-03 §2.1이 걱정한 PIECEWISE 증분 구간은 turn당 비용에 0.04 % 이하로만 들어간다.
   - 값은 이 격자·부하의 것이다.
2. **`stack`** — **해제 순서 LRU와 할당 순서 FIFO는 이 multi-turn 부하에서 재사용을 0.08–0.17 가르고, hit 모양도 가른다.**
   - FIFO는 부분 hit를 10–14 %, LRU는 1–6 % 예측한다.
   - GTASK04의 순차 프로토콜이 구별하지 못한 것을 이 실험이 구별할 수 있다.

## 해석

- 구성 효과(비용 1–4 %)는 해상도 경계에 있다. 비용 비 항목은 `NOT_INFORMATIVE`가 될 가능성이 크고, 이는 사전에 명시했다.
- 이 실험의 검증력은 재사용률(§5.1)과 LRU 대 FIFO(§5.5)에 있다.

## 확인되지 않은 사항

- 실제 lifecycle 시간(파일럿에서 확인)
- NPU 지시문 05 개정 2 원문(저장소 부재). G-03 본문의 설명대로 적용했다.

## 실패 / 무효 시도

- 계기 점검 1회차에서 측정 모듈이 client–server join에 실패했다(streaming id 형식). 수정 후 재계산했다. 두 계기 점검 lifecycle 자체는 유효했다.

## 연구 원칙에 미치는 영향

- 계기 점검은 선등록 전에 별도 plan으로 한다. 이번 점검은 파일럿 판정에 쓰일 id join 오류를 측정 전에 잡았다.

## 다음 작업

GTASK10(파일럿 실행과 판정). 이 commit 뒤에 시작한다.

## 재현 정보

- 위 명령. `PREDICTIONS.json` SHA256 `1be9a99129d245646b493e95b6fd3e7c71a45f9a64a8dd6fc917da30601e3a56`, `selection.json` SHA256 `11eecd58…c7065c`
- 계기 점검 raw: `results/gpu/multiturn/instrument_check/{gcheck-n3.json, run1, run2_nostream}`(비추적)
- **선등록 commit: 이 commit. 본 측정과 파일럿은 이 commit 이후에 시작한다.**
