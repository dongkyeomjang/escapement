# ④ A step-level model with zero fitted parameters

## 4.1 Why not a closed form

A closed-form account of padding predicts the *sign* of the grid effect but not its size, and it breaks where the steady state is not the whole story: a session set that decays from N to 1 passes through widths the steady-state count never visits, so steady-state padding is a **lower bound** on real padding. <!-- CLAIMS 1.14 --> We therefore keep the three mechanisms as a state machine over decode steps rather than as an equation.

The model carries only constants already measured for this substrate — per-width step cost, prefill cost, slot count, block sizes, eviction order, hit formula. **It has no fitted parameters**: nothing in it was tuned to make an output match. <!-- CLAIMS 1.14 -->

## 4.2 Four gates, each harder than the last

| Gate | What it tests | Result |
|---|---|---|
| Reproduction | 80 previously measured combinations | utilization MAE 0.0066, direction 11/11 <!-- CLAIMS 1.14 --> |
| Out-of-sample | 3 pooled ratios on fresh seeds, **committed before measurement** | worst error 0.0040 against a ±0.05 tolerance <!-- CLAIMS 1.15 --> |
| Intervention | device cells with a control policy applied, committed before measurement | within tolerance 2/2 <!-- CLAIMS 1.16 --> |
| Workload transfer | gap law replaced by a measured tool-latency population | utilization error −0.019 to 0.000 <!-- CLAIMS 1.17 --> |

The progression matters more than any single number. Reproducing measurements one has already seen is compatible with overfitting; predicting cells committed in advance is not; predicting cells in which a *control* has been applied tests whether the model knows the mechanism rather than the workload; and surviving a change of the gap distribution tests whether it knows the substrate rather than the workload's shape.

**Figure ④.**

## 4.3 What the model is not good at

Aggregate accuracy exceeds per-session accuracy. Hit *counts* are reproduced exactly while the attribution of which session hit is 92.9 % — the aggregate is right partly through cancellation, and **session-level conclusions must not be drawn from this model**. <!-- CLAIMS 1.15 -->

Reproduction quality also degrades above the scheduler's admission ceiling: below it the utilization error stays within 0.004, above it 0.011–0.023. Cells above the ceiling are reported as exploratory throughout the paper and never used for confirmation. <!-- NEEDS-EVIDENCE: 이 문장의 근거는 TASK24 핵심 발견 5인데 CLAIMS.md에 별도 항목이 없다. 항목 추가 여부 판정 필요 -->

A systematic residual remains: in every device confirmation where the model predicted the effect of an intervention, the measured ratio came out **above** the prediction — four device tasks, same sign, and a fifth in §⑥. The magnitudes never overturned a verdict, but the sign is systematic and the term responsible is not identified. <!-- NEEDS-EVIDENCE: 계통 편향을 CLAIMS 항목으로 세울지, 한계 절에만 둘지 판정 필요 -->

## 4.4 What it buys

Once the model predicts rather than reproduces, policy questions can be answered by computation instead of by occupying the device. Sections ⑤ and ⑥ are both consequences of that: an information decomposition that no measurement could produce, and a configuration search whose selection loop never touches hardware. <!-- CLAIMS 3.2 -->
