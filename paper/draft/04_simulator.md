# ④ A step-level model with zero fitted parameters

## 4.1 Why not a closed form

A closed-form account of padding predicts the *sign* of the grid effect but not its size, and it breaks where the steady state is not the whole story: a session set that decays from N to 1 passes through widths the steady-state count never visits, so steady-state padding is a **lower bound** on real padding. <!-- CLAIMS 1.14 --> We therefore keep the three mechanisms as a state machine over decode steps rather than as an equation.

The model carries only constants already measured for this substrate — per-width step cost, prefill cost, slot count, block sizes, eviction order, hit formula. **It has no fitted parameters**: nothing in it was tuned to make an output match. <!-- CLAIMS 1.14 -->

## 4.2 Four gates, each harder than the last

<!-- TABLECOLS: p{1.55cm}p{3.35cm}p{2.6cm} -->
<!-- TABLE: Four validation gates, in increasing order of what they rule out. Reproduction is compatible with overfitting; prediction committed in advance is not; predicting cells under a control tests the mechanism; and changing the gap law tests the substrate rather than the workload's shape. -->

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

## 4.3.1 The validated envelope

Because every use of the model in this paper rests on the gates above, it is worth stating exactly what they covered. The reproduction gate spans eighty combinations over two compiled grids and concurrencies from three to sixteen. <!-- CLAIMS 1.14 --> The out-of-sample gate covers three concurrencies at or below seven. <!-- CLAIMS 1.15 --> The intervention and configuration gates cover concurrencies of six and eight, with ten reported as exploratory. <!-- CLAIMS 1.16 --> The workload-transfer gate holds the grid fixed and changes the gap law. <!-- CLAIMS 1.17 -->

**Confirmation in this paper is therefore claimed at concurrencies at or below eight, on this one grid family and this one workload.** Cells above the scheduler's admission ceiling are reported as exploratory throughout and never used for confirmation, because reproduction quality degrades there: utilization error stays within 0.004 below the ceiling and runs 0.011–0.023 above it.

## 4.3.2 A known error structure

One residual is regular enough to state rather than to leave implicit. In **every** device confirmation where the model predicted the effect of an intervention, the measured ratio came out **above** the prediction — five occasions, same sign, across two different kinds of intervention (a return-holding policy and a compile configuration). <!-- CLAIMS 1.18 -->

Three things bound what this means. Each of those errors fell **inside the tolerance registered before measurement**, so no verdict in this paper turns on the residual. The errors concentrate at the higher concurrencies, in the same region where §4.3.1 already withholds confirmation. And the direction is interpretable: the model **overestimates the benefit** of an intervention, which is the conservative direction for a paper whose positive result is an intervention — the device delivered slightly less than predicted, never more.

What it does mean is that a term is missing. The model does not know something that makes interventions marginally less effective on hardware than in simulation, and this work did not isolate it; candidates include client-side overhead, queueing serialisation, and the model's known weakness at attributing reuse to particular sessions. **We report it as an open input to the next model revision rather than as noise.**

## 4.4 What it buys

Once the model predicts rather than reproduces, policy questions can be answered by computation instead of by occupying the device. Sections ⑤ and ⑥ are both consequences of that: an information decomposition that no measurement could produce, and a configuration search whose selection loop never touches hardware. <!-- CLAIMS 3.2 -->
