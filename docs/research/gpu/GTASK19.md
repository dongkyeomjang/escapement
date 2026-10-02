# GTASK19 — 정정 기록: GTASK11·12의 N24 BASE sim LRU 값(0.752 / 0.753)

## 상태

DONE

## 날짜

2026-10-02

## 목적

GPU 지시문 G-07 작업 D. NPU [TASK94](../TASK94.md) 대조에서 GTASK11 N24 BASE sim LRU 재사용 예측이 문장에서는 0.752, 표와 예측 파일에서는 0.753으로 적힌 것이 발견됐다. 산출 파일을 확인하고 **GTASK11·12 본문은 고치지 않고** 정정 기록을 남긴다. **측정 0, 계산은 기존 산출 파일 읽기뿐.**

## 시작 상태

- HEAD `b64eff3`(GTASK18 선등록), branch `gpu-a6000`

## 수행 내용

1. 예측 파일 `experiments/gpu/multiturn/plans/PREDICTIONS.json`(`2bef619` 측정 전 commit, SHA256 `1be9a99129d24564…`)의 N24 BASE를 읽었다.
2. 판정 산출 `results/gpu/multiturn/main/20260930T1411Z/verdict.json`(비추적, SHA256 `12af692b185e73d0…`)의 §5.5 cell 값을 읽었다.
3. 두 값을 만드는 코드 `main_judge.py`를 확인했다.

## 변경된 파일

- `docs/research/gpu/GTASK19.md`(신규), `docs/research/gpu/GPU_INDEX.md`

## 결과

| 출처 | 값 | 정의 |
|---|---|---|
| `PREDICTIONS.json` `sim_lru/lo` | 0.75318(1,361/1,807) | `lo` bound |
| `PREDICTIONS.json` `sim_lru/hi` | 0.75125(1,347/1,793) | `hi` bound |
| `verdict.json` §5.5 `24/BASE.sim_lru` | 0.75222 | `lo`·`hi` 평균(`main_judge.py` §5.5: `statistics.mean(... for b in BOUNDS)`) |

9 cell 모두 §5.5 값이 `lo`·`hi` 평균과 4자리까지 같다(예: N22 BASE 0.8485 = (0.8492 + 0.8478)/2).

문서별 사용:

| 위치 | 적힌 값 | 해당 정의 | 판단 |
|---|---|---|---|
| GTASK11 §5.1 표(`lo` 명시) | 0.753 | `lo` | 맞음 |
| GTASK11 §5.5 문장 "(관측 0.669, LRU 0.752, FIFO 0.611)" | 0.752 | §5.5 판정 값(bound 평균) | 값은 판정 산출과 맞다. 정의 표기가 빠졌다. FIFO 0.611도 평균(0.6097)의 반올림이다 |
| GTASK11 발견 4 "sim LRU 예측은 0.849, 0.752, 0.657" | 0.752 | **정의 혼용**. N26 0.657은 `lo`(평균은 0.647), N24 0.752는 평균이다 | `lo`로 통일하면 0.849, **0.753**, 0.657 |
| GTASK12 배경 "0.752 대 0.669, 0.657 대 0.450" | 0.752 | 발견 4를 그대로 옮긴 혼용 | `lo`로 통일하면 **0.753** 대 0.669 |
| GTASK13 표, GTASK09, `GPU_MULTITURN_PREREG.md` | 0.753 | `lo` | 맞음 |

## 정정

- **기준값**: GPU 기록의 sim LRU 예측 재사용은 선등록 기준대로 `lo` bound를 쓴다. N24 BASE는 **0.753**(0.75318)이다.
- **GTASK11 발견 4와 GTASK12 배경의 "0.752"는 "0.753"으로 읽는다.** 같은 문장의 다른 값(0.849, 0.657)은 `lo`이므로 그대로다.
- **GTASK11 §5.5 문장의 0.752·0.611은 §5.5 판정이 쓰는 bound 평균 값**이다. 틀린 값은 아니고 정의 표기가 빠진 것이다.
- 판정 영향: 없음. §5.5에서 N24 BASE는 어느 정의로도 예외 cell이다(|0.669 − 0.752| = 0.083, |0.669 − 0.753| = 0.084, FIFO 0.059). `LRU_SUPPORTED`(8/9, Σd_L 0.148 대 Σd_F 0.937), §5.1 MAE(`lo` 사용)도 바뀌지 않는다.
- GTASK11·12 본문은 고치지 않는다(G-07 §6).

## 핵심 발견

1. 0.752와 0.753은 둘 다 산출 파일에 있는 값이다. 다른 정의(bound 평균 대 `lo`)에서 나왔다. 불일치의 원인은 문장 하나(GTASK11 발견 4)가 두 정의를 섞은 것이다. GTASK12는 그 문장을 옮겼다.

## 해석

- 예측 bound가 둘인 기록에서는 수치마다 bound(또는 평균)를 적어야 한다.

## 확인되지 않은 사항

- 없음

## 실패 / 무효 시도

- 없음

## 연구 원칙에 미치는 영향

- 판정 코드가 bound 평균을 쓰는 항목(§5.5)의 수치를 문장에 옮길 때는 정의를 함께 적는다.

## 다음 작업

- 없음

## 재현 정보

```bash
python3 -c "import json;p=json.load(open('experiments/gpu/multiturn/plans/PREDICTIONS.json'))['cells']['24']['BASE'];print(p['sim_lru/lo']['reuse_rate'],p['sim_lru/hi']['reuse_rate'])"
python3 -c "import json;print(json.load(open('results/gpu/multiturn/main/20260930T1411Z/verdict.json'))['5.5']['cells']['24/BASE']['sim_lru'])"
```
