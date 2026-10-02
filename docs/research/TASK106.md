# TASK106 — P04 대조를 GTASK19 정정값으로, GPU 출처 표기를 main 경로로

## 상태

DONE

## 날짜

2026-10-02

## 목적

[TASK105](TASK105.md) 결정 요청에 대한 사용자 결정(2026-10-02)을 집행한다.

1. GTASK11 `BASE.n24` sim LRU 0.752 대 0.753 대조를 GPU 쪽 정정 기록(GTASK19: `lo` 0.753, 0.752는 lo·hi 평균) 기준으로 바꾼다 — 원인이 밝혀진 표기 차이다.
2. 결과 색인·표·그림의 GPU 출처 표기를 `origin/gpu-a6000:<path>`에서 main 경로 `<path> @ <commit>`으로 바꾼다 — 익명 공개 자료는 main에서 만들어지므로 branch 경로로는 출처를 찾을 수 없다.
3. 원격 `gpu-a6000` branch는 지우지 않는다(내용은 main에 모두 있으나 지워서 얻는 것이 없고 되돌리기 어렵다; 논문 채택 이후 정리 가능).

**측정 0.**

## 배경

- [TASK104](TASK104.md) — merge `af3dfe3`(GPU commit 이력 보존), [TASK105](TASK105.md) — 결과 색인 병합, P04 불일치 보고

## 시작 상태

- HEAD `86f6ba1`(= `origin/main`), `?? .idea/`만

## 수행 내용

1. `make_paper_tables.py`: GPU 파일을 `git show HEAD:<path>`로 읽고, 출처를 `<path> @ <git log -1 commit>`으로 표기. manifest의 `gpu_branch*` 항목을 `gpu_source`("main (gpu-a6000 merged in af3dfe3)")로 바꿨다. P04 대조 "BASE.n24 sim LRU 재사용"의 기록값을 0.752 → **0.753**(출처 GTASK19 정정 기록)으로 바꿨다. GTASK19 5자리 대조 2건은 그대로.
2. `paper/RESULTS_INDEX.md`: GPU 출처 130곳의 `origin/gpu-a6000:` 접두를 지웠다(경로·commit 그대로). 머리말의 출처 규칙 갱신. `g11_collapse_curve` 값을 sim LRU(`lo`) 0.849 / **0.753** / 0.657로, GTASK11 문장의 0.752는 lo·hi 평균이라는 GTASK19 정정을 비고로, 출처에 GTASK19(`a99f23c`)를 추가했다.
3. 출처 검사: 색인의 GPU `<path> @ <commit>` 20쌍이 모두 main 이력에서 존재(`git cat-file -e`).
4. 표·그림 재생성.

## 변경된 파일

- `experiments/npu/analysis/make_paper_tables.py`, `paper/RESULTS_INDEX.md`
- `results/tables/`(P01·P04–P09·P12·P14 출처 표기, figures 출처 열, `README.md`, `paper_manifest.json`)
- `docs/research/TASK106.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

```bash
OMP_NUM_THREADS=1 env -u PYTHONPATH python3 experiments/npu/analysis/make_paper_tables.py --all
git grep -l "origin/gpu-a6000:" -- paper results/tables experiments/npu tools     # 비어 있어야 함
```

## 결과

- 표 14/14, 대조 380건, **불일치 3건**(TASK105의 4건에서 P04 1건 해소): P12 GTASK18 "설명 몫" d = 1(90 대 89)·d = 5(89 대 90) — 반올림, P14 GTASK20 `BASE.n28` TTFT(3.11 대 3.12).
- 결과 색인·표·그림·analysis 코드에 `origin/gpu-a6000:` 표기 0건. 색인 행 수와 종류별 개수는 TASK105와 같다(315행).
- 원격 `gpu-a6000` branch 유지.

## 핵심 발견

- 없음(기록·표기 정리).

## 해석

- 없음.

## 확인되지 않은 사항

- 없음.

## 실패 / 무효 시도

- 없음.

## 연구 원칙에 미치는 영향

- 공개 자료가 만들어질 branch의 경로로 출처를 적는다.

## 다음 작업

- 없음(사용자 지시 대기).

## 재현 정보

- 위 명령, HEAD `86f6ba1` 기준.
