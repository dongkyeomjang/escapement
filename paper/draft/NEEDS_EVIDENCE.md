# `[NEEDS-EVIDENCE]` 잔존 목록

`env -u PYTHONPATH python3 paper/draft/check_claims.py`가 생성 근거를 다시 뽑는다. **해소는 강제가 아니며 Advisor 첨삭에서 판정한다.**

**현재 3건.** 셋 다 "근거가 없다"가 아니라 **"근거는 있는데 어디에 둘지가 미정"** 이다. 지어낸 문장은 없다.

| # | 절 | 내용 | 근거의 현재 위치 | 판정이 필요한 것 |
|---|---|---|---|---|
| 1 | ② Background | observation-only patch의 정당화 — `patches/README.md`의 7개 항목 | [patches/vllm_rbln-0.11.1/README.md](../../patches/vllm_rbln-0.11.1/README.md), [TASK12](../../docs/research/TASK12.md) | 본문에 한 문단으로 요약할지, 부록 C로 뺄지. **재현성 심사에서 물어볼 항목**이라 어딘가에는 있어야 한다 |
| 2 | ④ Simulator | "재현 품질이 admission ceiling에서 꺾인다"(N ≤ 8 오차 0.004 이내, N ≥ 10 0.011–0.023) | [TASK24](../../docs/research/TASK24.md) 핵심 발견 5 | [CLAIMS.md](../CLAIMS.md)에 항목이 없다. **주장으로 세울지**(그러면 층 태그와 조건 병기 필요), 아니면 한계 절로만 보낼지 |
| 3 | ④ Simulator | 계통적 양의 예측 오차 — 5개 device 확증에서 전부 같은 부호 | [TASK28](../../docs/research/TASK28.md)·[TASK35](../../docs/research/TASK35.md)·[TASK36](../../docs/research/TASK36.md)·[TASK40](../../docs/research/TASK40.md) | 이것을 **주장**으로 세우면 "모형에 빠진 항이 있다"를 논문이 스스로 말하는 것이 된다. 정직하지만 리뷰어가 물고 늘어질 지점이라 **Advisor 판정이 필요**하다. 현재는 ④와 ⑨ 양쪽에 서술만 있고 CLAIMS 항목은 없다 |

## 판정하면 이렇게 반영한다

- **1번을 부록으로** → ②의 marker를 지우고 부록 C 참조로 바꾼다.
- **2·3번을 주장으로** → [CLAIMS.md](../CLAIMS.md)에 항목을 먼저 추가하고(층 태그·조건 병기 포함) 본문 marker를 `<!-- CLAIMS x.y -->`로 교체한다. **본문이 먼저 주장을 만들지 않는다**는 규칙 때문에 순서가 이렇다.
- **2·3번을 한계로만** → marker를 지우고 ⑨에만 남긴다. ⑨에는 이미 두 항목 다 서술돼 있다.
