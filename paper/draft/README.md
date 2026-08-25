# 본문 초고 — 집필 규칙과 절 구성

## 언어

**본문은 영문**이다 — arXiv·TPDS 제출 대상이고 LaTeX로 그대로 옮겨진다. **편집 주석은 한국어**이며 `<!-- -->` 안에 둔다. 이 저장소의 연구 문서가 한국어인 것과 충돌하지 않는다: 여기 있는 것은 연구 기록이 아니라 **원고**다.

## 집필 규칙 (전 절 공통)

1. **CLAIMS id 주석** — 모든 주장 문장 뒤에 `<!-- CLAIMS 3.11 -->`처럼 근거 주장 번호를 단다. [CLAIMS.md](../CLAIMS.md)에 없는 번호를 쓰지 않는다.
2. **신규 주장 금지** — [CLAIMS.md](../CLAIMS.md)에 없는 주장을 본문에서 만들지 않는다. 필요하면 먼저 CLAIMS에 추가하고 근거 TASK를 붙인다.
3. **`stack` 조건 병기** — `stack`/`silicon` 태그 주장의 수치는 조건과 **같은 문장** 안에 둔다. [CLAIMS.md](../CLAIMS.md) 전수 점검 표의 처리 방식을 따른다.
4. **`class` 주장에 수치 금지** — 형태 진술에는 값을 붙이지 않는다. 값은 대응하는 `stack` 항목에서 조건과 함께 낸다.
5. **`[NEEDS-EVIDENCE]`** — 근거가 필요하지만 아직 없는 자리는 그 marker와 무엇이 필요한지를 함께 적는다. 지어내지 않는다. 잔존 목록은 [NEEDS_EVIDENCE.md](NEEDS_EVIDENCE.md)에 모은다.
6. **모형·절제 표기** — 계산에서 나온 값은 문장에서 "model"/"ablation"으로 표시한다.

## 절 구성

| # | 파일 | 제목 | 대응 |
|---|---|---|---|
| ① | [01_introduction.md](01_introduction.md) | Introduction | [OUTLINE.md](../OUTLINE.md) 서두 + [INTRO.md](../INTRO.md) §4 완고 통합 |
| ② | [02_background.md](02_background.md) | Background: the substrate and what it fixes at compile time | 막 1 전제 |
| ③ | [03_mechanisms.md](03_mechanisms.md) | Three mechanisms of the return-arrival process | 막 1 |
| ④ | [04_simulator.md](04_simulator.md) | A step-level model with zero fitted parameters | 막 1.4 |
| ⑤ | [05_impossibility.md](05_impossibility.md) | What runtime policy cannot reach | 막 2 |
| ⑥ | [06_prescription.md](06_prescription.md) | Compile-time configuration | 막 3 (**포화 곡선 포함**) |
| ⑦ | [07_generality.md](07_generality.md) | Generality: ablations and what transfers | 일반성 절 |
| ⑧ | [08_related.md](08_related.md) | Related work | [RELATED.md](../RELATED.md) |
| ⑨ | [09_limitations.md](09_limitations.md) | Limitations | [CLAIMS.md](../CLAIMS.md) 한계 절 |
| ⑩ | [10_conclusion.md](10_conclusion.md) | Conclusion | — |

## 완성 기준

전 절 초고 존재 + `[NEEDS-EVIDENCE]` 잔존 목록 보고. **해소는 강제하지 않는다** — Advisor 첨삭에서 판정한다.
