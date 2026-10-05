# 해석적 모형 v1 — 수식·변수 정의·출처

범위: 논문의 "analytical model" = 모형 v1 (B2 점유 + B1 v1 생존 + B3 격자 DP). v1.1은 blind FAIL([TASK87](../docs/research/TASK87.md)) — 본 문서에서 제외, 필요한 곳에만 `[v1.1]` 표시.
기준: **문서와 코드가 다르면 코드**. 차이는 §6 표.
코드 기준 commit: `63b4bcc` (main).

경로 약어

| 약어 | 경로 |
|---|---|
| `SV1` | `src/continuum/model/survival_v1.py` |
| `OCC` | `src/continuum/model/occupancy.py` |
| `GRD` | `src/continuum/model/grid.py` |
| `INT` | `src/continuum/model/interference.py` |
| `DSC` | `src/continuum/substrate/descriptor.py` |
| `MTP` | `experiments/npu/stage3/mt_predict.py` |
| `SEL` | `experiments/npu/stage3/select_grids.py` |
| `CFS` | `experiments/npu/analysis/config_search.py` |
| `GMM` | `experiments/gpu/multiturn/gpu_mt_model.py` |
| `V0` / `V1` / `V11` | `docs/research/MODEL_V0.md` / `MODEL_V1.md` / `MODEL_V1_1.md` |
| `RP` | `docs/research/MODEL_V0_RETRO_PREREG.md` |

---

## 0. 공통 입력

### 0.1 변수

| 기호 | 정의 | 단위 | 코드 이름 | 출처 |
|---|---|---|---|---|
| $N$ | 세션 수(고정, 세션 갱신) | 개 | `n`, `sessions` | `MTP:analytic` |
| $M$ | 동시 running 상한 | 개 | `max_running` = `batch` | `MTP:analytic` |
| $C$ | slot pool 용량 | slot | `capacity` = `batch` | `MTP:analytic`, `CFS:descriptor_for` |
| $\mathcal G$ | compiled decode 폭 격자 | — | `grid` | `MTP:descriptor` |
| $b_{\mathcal G}(r)$ | $r$을 담는 최소 폭 | — | `bucket_for` | `DSC:SubstrateDescriptor.bucket_for` |
| $t(r)$ | running $r$에서 decode step 시간 | s | `step_time_s` | `DSC:StepCostModel.step_time_s` |
| $F(b)$ | 폭 $b$의 고정비(미측정 폭은 보간·외삽) | s | `fixed_s_by_bucket` | `CFS:descriptor_for`, `GRD:interpolated_fixed_costs` |
| $c_0,\ c_1$ | step 절편, 요청당 기울기 | s, s/req | `intercept_s`, `marginal_s_per_request` | `DSC:StepCostModel` |
| $P(q)$ | 계산 token $q$의 배타 prefill 시간 | s | `prefill_s` | `DSC:PrefillCostModel.prefill_s` |
| $\kappa,\ p_c,\ \delta$ | chunk 크기, chunk당 시간, token당 drift | token, s, s/token | `chunk_tokens`, `per_chunk_s`, `drift_s_per_token` | 같음 |
| $B$ | inner block 크기 | token | `inner_block_tokens` | `MTP:plan_stats` |
| $\bar g$ | 요청당 평균 생성 token | token | `gen_mean` | `MTP:plan_stats` |
| $D$ | 요청당 decode step 수 $=\bar g-1$ | step | `decode_steps_per_request` | `MTP:analytic` |
| $Z$ | 평균 think 시간 = 모든 turn의 `gap_after_s` 평균(마지막 turn 0 포함) | s | `think_mean_s` | `MTP:plan_stats` |
| $s_1$ | 첫 turn 비중 | — | `share_first` | `MTP:plan_stats` |
| $\bar P_{\text{first}},\ \bar P_{\text{hit}},\ \bar P_{\text{miss}}$ | plan 요청 평균 prefill 시간 | s | `p_first_s`, `p_hit_s`, `p_miss_s` | `MTP:plan_stats` |
| $\{(g_i, w_i)\}$ | 양의 gap 표본의 분위 압축(≤ 40 bin, bin 평균·개수) | s, — | `idle_samples` → `_compress` | `MTP:plan_stats`, `MTP:_compress` |

### 0.2 비용 식

```latex
t(r) = F\!\left(b_{\mathcal G}(r)\right) + c_0 + c_1\, r,
\qquad b_{\mathcal G}(r)=\min\{b\in\mathcal G : b\ge r\}
```
출처: `DSC:StepCostModel.step_time_s`, `DSC:SubstrateDescriptor.step_time_s`, `DSC:SubstrateDescriptor.bucket_for`. (context 항 없음 — v1 해석 경로는 `context_cost`를 읽지 않는다.)

```latex
P(q) = \left\lceil q/\kappa \right\rceil \left(p_c + \delta\, q\right),\qquad P(0)=0
```
출처: `DSC:PrefillCostModel.prefill_s`.

```latex
F(b) = F(\ell) + \frac{b-\ell}{h-\ell}\,\bigl(F(h)-F(\ell)\bigr),\quad
(\ell,h)=\begin{cases}
(\max\{x<b\},\ \min\{x>b\}) & \text{범위 안}\\
(x_{(1)},x_{(2)}) & b<\min\\
(x_{(m-1)},x_{(m)}) & b>\max
\end{cases}
```
$x$ = 측정 폭. 출처: `CFS:descriptor_for`, `GRD:interpolated_fixed_costs`; `V0` B3 (i) "미측정 버킷 비용".

### 0.3 hit query와 평균 prefill

```latex
q^{\text{hit}}_j = L_j - B\left\lfloor \frac{\min(L_{j-1},\ L_j-1)}{B}\right\rfloor,
\qquad q^{\text{miss}}_j = L_j
```
$L_j$ = turn $j$의 prompt 길이(이전 context + 새 segment). 캐시는 이전 **prompt**만(생성 token 제외). 출처: `MTP:plan_stats`.

```latex
\mathbb E[P](p_s) = s_1\,\bar P_{\text{first}} + (1-s_1)\left[p_s\,\bar P_{\text{hit}} + (1-p_s)\,\bar P_{\text{miss}}\right]
```
출처: `MTP:analytic` (루프 첫 줄), 단일 요청형 `INT:expected_prefill_s`; `V0` B4 (i).

---

## 1. 점유 모형 (B2)

### 1.1 변수

| 기호 | 정의 | 코드 | 출처 |
|---|---|---|---|
| $n$ | 엔진 안 세션 수(대기 + running), $0..N$ | `n` | `OCC:_distribution` |
| $r(n)$ | running 수 $=\min(n,M)$ | `r` | 같음 |
| $\lambda_n$ | gap station 이탈률 $(N-n)/Z$ | `lam` | 같음 |
| $\mu(n)$ | 엔진 완료율 | `mu` | 같음 |
| $\varphi$ | 배타 prefill 뒤 decode에 남은 시간 몫 | `phi` | `OCC:solve_occupancy` |
| $X$ | 처리율(엔진 도착률) | `throughput_per_s` | `OCC:_throughput` |
| $\tau(r)$ | 시간 가중 running 분포 | `time_share` | `OCC:solve_occupancy` |
| $h(r)$ | step 가중 running 분포 | `step_share` | 같음 |
| $P_{\text{arr}}(k)$ | 도착 요청이 보는 running 수 분포 | `arrival_running_distribution` | `OCC:arrival_running_distribution` |

### 1.2 서비스율

```latex
\mu(n) = \frac{\varphi\, r(n)}{D\; t\!\left(r(n)\right)},\qquad r(n)=\min(n,M),\quad n\ge 1
```
출처: `OCC:_distribution`; `V0` B2 (i).

### 1.3 정상 분포 (birth–death 곱 형태)

```latex
\frac{\pi(n+1)}{\pi(n)} = \frac{(N-n)/Z}{\mu(n+1)},\qquad
\pi(n) = \frac{\prod_{m=0}^{n-1}\frac{(N-m)/Z}{\mu(m+1)}}{\sum_{n'=0}^{N}\prod_{m=0}^{n'-1}\frac{(N-m)/Z}{\mu(m+1)}}
```
로그 공간 누적 후 최대값 이동으로 정규화. 출처: `OCC:_distribution`; `V0` B2 (i).

```latex
X = \frac{1}{Z}\sum_{n=0}^{N}\pi(n)\,(N-n)
```
출처: `OCC:_throughput`.

```latex
\tau(r)=\sum_{n:\ \min(n,M)=r}\pi(n),\qquad
h(r)=\frac{\tau(r)\,\varphi/t(r)}{\sum_{r'\ge1}\tau(r')\,\varphi/t(r')},\ r\ge 1
```
```latex
\text{steps/s} = \sum_{r\ge1}\tau(r)\,\frac{\varphi}{t(r)},\qquad
\bar n = \sum_r r\,\tau(r)\ \ (\text{시간 가중}),\qquad
\bar R = \frac{\sum_n n\,\pi(n)}{X}\ \ (\text{Little})
```
출처: `OCC:solve_occupancy`, `OCC:Occupancy.mean_running`, `OCC:Occupancy.mean_response_s`.

### 1.4 배타 prefill 보정항 φ

```latex
\varphi = 1 - X(\varphi)\,\mathbb E[P]
```
출처: `OCC:solve_occupancy`; `V0` B2 (i). $1 - X\,\mathbb E[P]\le 0$ → 예외("prefill alone saturates").

### 1.5 고정점 반복

```latex
\varphi^{(0)}=1,\qquad
\varphi^{(i+1)} = \tfrac12\left(\varphi^{(i)} + 1 - X\!\left(\pi(\cdot\,;\varphi^{(i)})\right)\mathbb E[P]\right)
```
```latex
\text{정지: } \left|\varphi^{(i+1)}-\varphi^{(i)}\right| < 10^{-12}\quad\text{또는}\quad i = 10^4\ (\texttt{converged=False})
```
정지 후 $\pi,\ X$를 최종 $\varphi$로 재계산. 출처: `OCC:solve_occupancy` (`tol=1e-12`, `max_iter=10_000`). 문서 self-check 잔차 5.5e-13 (`V0` B2 (i)).

### 1.6 도착 정리 (arrival theorem)

```latex
P_{\text{arr}}(k) = \sum_{n:\ \min(n,M)=k}\pi^{(N-1)}\!\left(n;\ \varphi^{(N)}\right),\quad k=0..\min(N-1,M);\qquad N\le1\Rightarrow P_{\text{arr}}(0)=1
```
$\varphi^{(N)}$ = $N$ 모집단 해의 $\varphi$, 모집단만 $N-1$. 출처: `OCC:arrival_running_distribution`; `V0` B2 (i).

### 1.7 동시 실행 상한 $M$ 초과

```latex
n>M:\quad r(n)=M,\ \ \mu(n)=\mu(M)=\frac{\varphi M}{D\,t(M)}\quad(\text{나머지 } n-M \text{ 은 FCFS 대기})
```
- 같은 곱 형태 식을 그대로 사용 — 근사.
- $N>M$이면 `notes`에 "FCFS waiting breaks insensitivity" 기록.
- 대기 시간 자체는 B1 v1에 전달되지 않음(§3, §6 D2). `[v1.1]`만 전달(`V11` §2).

출처: `OCC:solve_occupancy` (`notes`), `OCC:_distribution`; `V0` B2 (ii)1.

---

## 2. 생존 모형 (B1 v1)

### 2.1 변수

| 기호 | 정의 | 범위 | 코드 | 출처 |
|---|---|---|---|---|
| $T$ | 대상 항목(이전 turn의 slot) | — | — | `SV1` docstring |
| $f$ | 빈 slot 수 | $0..f_0$ | `f` | `SV1:_step` |
| $a$ | $T$보다 오래된 **active** 항목 수(감소만) | $0..a_0$ | `a` | 같음 |
| $d$ | $T$보다 오래된 pool 내 **inactive** 항목 수 | $0..C-1$ | `d` | 같음 |
| $\dagger$ | 흡수 상태($T$ 축출) | — | `_DEAD` | 같음 |
| $\lambda$ | 다른 세션의 할당률(Poisson) | s⁻¹ | `lam` | `SV1:V1Inputs` |
| $\mu$ | 오래된 active 항목 1개의 완료율 | s⁻¹ | `mu` | 같음 |
| $s_{\text{act}}$ | $T$ active 구간 길이 | s | `s_active` | 같음 |
| $s_{\text{idle}}$ | $T$ inactive 구간 길이 | s | `s_idle` | 같음 |
| $\omega$ | 재도착의 조회 전 자기 할당 여부 | {0,1} | `own_alloc` (기본 True) | 같음 |

제약: $f+a+d\le C-1$, $f,a,d\ge0$. 상태 수 $\le (f_0+1)(a_0+1)(C+1)+1$ (`V1` §3).

### 2.2 초기 상태 ($T$ 할당 직후)

일반형:
```latex
f_0 = f_{\text{after}},\qquad a_0 = k,\qquad d_0 = (C - f_0 - 1) - k
```
출처: `SV1:initial_state`; `V1` §2.

해석 경로(가득 찬 pool, 코드):
```latex
f_0 = 0,\qquad a_0 = \min(k,\ C-1),\qquad d_0 = C-1-a_0,\qquad k\sim P_{\text{arr}}
```
출처: `SV1:steady_state_survival` (`k_eff`). 문서와 차이 → §6 D4.

### 2.3 전이율 (생성자 $Q_\sigma$, $\sigma\in\{\text{act},\text{idle}\}$)

| 전이 | 조건 | 율 | 출처 |
|---|---|---|---|
| $(f,a,d)\to(f-1,a,d)$ | $f>0$ | $\lambda$ | `SV1:_step` |
| $(f,a,d)\to(f,a,d-1)$ | $f=0,\ d>0$ | $\lambda$ | 같음 |
| $(f,a,d)\to(f,a,d)$ (보호) | $f=0,\ d=0,\ \sigma=\text{act}$ | $\lambda$ | 같음 |
| $(f,a,d)\to\dagger$ | $f=0,\ d=0,\ \sigma=\text{idle}$ | $\lambda$ | 같음 |
| $(f,a,d)\to(f,a-1,d+1)$ | $a>0$ | $a\,\mu$ | 같음 |
| $\dagger\to\dagger$ | — | 흡수 | 같음 |

`V1` §2 전이표, §3 "수식".

### 2.4 구간 처리 (running / 대기)

```latex
\mathbf p(s_{\text{act}}) = \mathbf e_{(f_0,a_0,d_0)}^{\top}\, e^{Q_{\text{act}}\, s_{\text{act}}},\qquad
\mathbf p(s_{\text{act}}+s_{\text{idle}}) = \mathbf p(s_{\text{act}})\, e^{Q_{\text{idle}}\, s_{\text{idle}}}
```
- 구간 1 = $T$ active(자기 prefill + decode): 보호.
- 구간 2 = $T$ inactive: 흡수 가능.
- $T$의 admission 전 대기: 창 밖(창은 $T$의 slot 할당에서 시작, `V0` B1 창 정의표).
- 재도착 $R$의 admission 전 대기: NPU v1 코드에서 **미포함**($s_{\text{idle}}$ = gap만, §6 D2).

출처: `SV1:survival_probability_v1`.

### 2.5 흡수 확률 계산 — 균일화(uniformization)

```latex
\Lambda = \lambda + a_0\,\mu,\qquad
\mathbf P_\sigma = I + Q_\sigma/\Lambda
```
```latex
\mathbf p(t) = \sum_{j=0}^{J}\ e^{-\Lambda t}\frac{(\Lambda t)^j}{j!}\ \mathbf p(0)\,\mathbf P_\sigma^{\,j},\qquad
J=\min\Bigl\{J:\ 1-\textstyle\sum_{j\le J} e^{-\Lambda t}\frac{(\Lambda t)^j}{j!}\le 10^{-13}\Bigr\}\ \ (\le 10^5)
```
```latex
\Lambda t \ge 700\ \Rightarrow\ \mathbf p(t) = \mathbf p(t/2)\big|_{\text{재귀}}\ \text{를 두 번 적용}
```
행렬 지수 직접 계산 없음(sparse 사전 갱신). 출처: `SV1:_evolve`, `SV1:_step`; `V1` §3 "균일화 급수".

### 2.6 생존 확률

```latex
S(f_0,a_0,d_0;\ s_{\text{act}},s_{\text{idle}}) =
\sum_{x=(f,a,d)\neq\dagger} p_x(s_{\text{act}}+s_{\text{idle}})\ \bigl(1 - \omega\,\mathbb 1[f=0 \wedge d=0]\bigr),
\quad S\in[0,1]\ (\text{clip})
```
마지막 항 = 재도착의 조회 전 자기 할당(`resume_allocates_first=True`). 출처: `SV1:survival_probability_v1`; `V1` §3 "끝".

### 2.7 재사용률

```latex
\hat p_s = \frac{\sum_{k} P_{\text{arr}}(k)\sum_i w_i\ S\!\left(0,\ \min(k,C-1),\ C-1-\min(k,C-1);\ s_{\text{act}},\ g_i\right)}
{\left(\sum_i w_i\right)\left(\sum_k P_{\text{arr}}(k)\right)}
```
$(g_i,w_i)$ = 양의 gap 분위 압축 표본(0.1 표). 출처: `SV1:steady_state_survival`, `MTP:_compress`; `V1` §3 "steady state 형태".

### 2.8 정확 추적기(검증용, 예측 아님)

사건열 $e\in\{\texttt{alloc},\texttt{own\_alloc},\texttt{evict},\texttt{older\_release},\texttt{target\_release}\}$에 2.3의 결정론적 전이 적용. 출처: `SV1:track_target`; `V1` §2 (합성 5,133/5,133, 실제 1,298/1,298).

### 2.9 퇴화 경우

```latex
s_{\text{act}}=0,\ a_0=0,\ f_0=0,\ d_0=C-1:\qquad S = \Pr\!\left[\mathrm{Pois}(\lambda s_{\text{idle}}) + 1 \le C-1\right]\quad(\text{v0 } 1+A\le C)
```
출처: `SV1` docstring "Degenerate case"; `V1` §3 퇴화 self-check (최대 차 2.2e-16).

### 2.10 GPU 경우 ($a\equiv0$, free-queue LRU, block 단위)

구조: 창 = $T$ release → $R$ lookup; running block은 queue 밖 → $a\equiv0$, 보호 구간 없음; lookup이 할당보다 먼저 → $\omega=0$; $d$는 순수 사멸 과정. `V1` §4.

| 기호 | 정의 | 코드 | 출처 |
|---|---|---|---|
| $u$ | $T$의 hit 가능 선두 block 수 $=\min(\lfloor F_{j-1}/B_g\rfloor,\lfloor (L_j-1)/B_g\rfloor)$, $F_{j-1}=L_{j-1}+g_{j-1}-1$ | `u` | `GMM:plan_samples` |
| $B_g$ | block 크기(16) | `BLOCK` | `GMM` (import `gpu_mt_sim`) |
| $d_0$ | queue에서 $T$ 앞의 block 수 | `d0` | `GMM:analytic` |
| $\lambda_b$ | block 소비율 | `lam` | `GMM:analytic` |
| $N_{\text{ev}}$ | 창 안 소비 block 수 | — | `SV1:lru_block_survival` |

```latex
N_{\text{ev}}\sim\mathrm{Pois}(\lambda_b\, s),\qquad
\text{lost}=\min\!\bigl(u,\ \max(0,\ N_{\text{ev}}-d_0)\bigr)
```
```latex
\Pr[K=u]=\Pr[N_{\text{ev}}\le d_0],\quad
\Pr[K=u-j]=\Pr[N_{\text{ev}}=d_0+j]\ (1\le j<u),\quad
\Pr[K=0]=\Pr[N_{\text{ev}}\ge d_0+u]
```
평균 $\ge 600$이면 log 공간 pmf. 출처: `SV1:lru_block_survival` (`_LOG_SPACE_MEAN`), `GMM:lru_survival`.

입력(GPU wrapper):
```latex
\lambda_b = X\left[s_1\,\overline{\tfrac{L+g-1}{B_g}}\Big|_{\text{first}} + (1-s_1)\,\overline{\tfrac{L+g-1}{B_g}-\rho_{\text{tok}}\,u}\Big|_{\text{later}}\right]
```
```latex
\text{free}=\max\!\bigl(0,\ (C_b-1) - \bar n\,\bar r_b\bigr),\quad \bar r_b=\overline{(L+g/2)/B_g},\quad C_b=\texttt{num\_gpu\_blocks}
```
```latex
d_0=\max\!\Bigl(0,\ \mathrm{round}\bigl(\text{free}-u-I\,F_{\text{res}}(s)\,p_{\text{hit}}\,\bar u\bigr)\Bigr),\quad
I=\max\!\bigl(0,(N-1)-\bar n\tfrac{N-1}{N}\bigr),\quad
F_{\text{res}}(s)=\frac{\sum_i\min(g_i,s)}{n_g\,\bar g_{\text{gap}}}
```
```latex
s = g + W,\qquad W=\max(0,\ \bar R - \bar S)
```
```latex
p_{\text{hit}} = \frac{1}{|\mathcal L|}\sum_{\ell\in\mathcal L}\bigl(1-\Pr[K_\ell=0]\bigr),\qquad
\rho_{\text{tok}} = \frac{1}{|\mathcal L|}\sum_{\ell}\frac{\mathbb E[K_\ell]}{u_\ell}
```
$\mathcal L$ = 첫 turn 외 요청, $(u,g)$를 (4 block, gap 2 % 양자화)로 묶어 가중. 출처: `GMM:analytic`, `GMM:_residual_cdf`, `GMM:plan_samples`.

GPU $\mathbb E[P]$ = 혼합 chunked prefill의 step 증분(배타 아님), budget 2048 token chunk:
```latex
\mathbb E[P] = s_1\,\overline{P_{\text{inc}}(L)} + (1-s_1)\,\overline{\rho_{\text{tok}}P_{\text{inc}}(L-uB_g)+(1-\rho_{\text{tok}})P_{\text{inc}}(L)}
```
출처: `GMM:analytic`, `GMM:_chunks_inc`, `gpu_cost.py:prefill_increment_ms`.

---

## 3. 두 모형의 연결

### 3.1 B2 → B1 (NPU, `MTP:analytic`)

```latex
\bar S = \mathbb E[P] + D\,\frac{t\!\left(\max(1,\mathrm{round}(\bar n))\right)}{\varphi}
```
```latex
\mu = 1/\bar S,\qquad \lambda = X\,\frac{N-1}{N},\qquad s_{\text{act}}=\bar S,\qquad s_{\text{idle}}\in\{g_i\},\qquad k\sim P_{\text{arr}}
```
출처: `MTP:analytic`; `V1` §3 입력 파라미터 표(차이 §6 D1–D3).

### 3.2 B1 → B2 (재사용 → prefill 작업량)

```latex
p_s \ \longrightarrow\ \mathbb E[P](p_s)\ (\S0.3)\ \longrightarrow\ \varphi=1-X\,\mathbb E[P],\ \ \bar S
```
- 반영 경로: $\mathbb E[P]$ → $\varphi$ → $\mu(n)$, $\pi$, $X$, $h$; 또 $\bar S$ → $\mu$, $s_{\text{act}}$.
- 반영 안 됨: prefill 시간 분포(평균만), 재사용과 $K$의 상관.

### 3.3 결합 고정점 (NPU)

```latex
p^{(0)}=0.9,\qquad
p^{(i+1)} = \begin{cases}
\hat p_s\!\left(p^{(i)}\right) & \left|\hat p_s(p^{(i)})-p^{(i)}\right|<10^{-7}\ (\text{정지})\\[2pt]
\tfrac12\left(p^{(i)}+\hat p_s(p^{(i)})\right) & \text{그 외}
\end{cases},\qquad i<30
```
$\hat p_s(p)$ = §1(입력 $\mathbb E[P](p)$) → §3.1 → §2.7. 수렴 여부 플래그 없음(30회 후 그대로 반환). 출력: `reuse_rate` $=p$, `prefill_per_turn_s` $=\mathbb E[P](p)$(최종 $p$), `h`·`throughput`·`phi`·`mean_running` = 마지막 반복의 B2 해(§6 D6). 출처: `MTP:analytic` (`iters=30`).

### 3.4 결합 고정점 (GPU)

```latex
(p^{(0)}_{\text{hit}},\rho^{(0)}_{\text{tok}},\bar n^{(0)})=(0.9,\ 0.9,\ 1),\qquad
\text{정지: } |\Delta p_{\text{hit}}|<10^{-7}\wedge|\Delta\rho_{\text{tok}}|<10^{-7},\ \ \text{감쇠 } \tfrac12,\ \ \le 60\text{회}
```
출처: `GMM:analytic` (`iters=60`).

### 3.5 파생 출력 (참고)

```latex
\text{decode/turn} = \frac{\text{steps/s}\cdot\sum_r h(r)\,t(r)}{X},\qquad
\text{pad} = \frac{\sum_r h(r)\,(b_{\mathcal G}(r)-r)}{\sum_r h(r)\,b_{\mathcal G}(r)},\qquad
W/\text{turn} = \mathbb E[P]\sum_k k\,P_{\text{arr}}(k),\qquad
\text{cycle}=Z+\bar R
```
출처: `MTP:analytic`; B4 `V0` B4 (i), `INT:interference`.

---

## 4. 격자 최적화 (B3)

### 4.1 변수

| 기호 | 정의 | 코드 | 출처 |
|---|---|---|---|
| $h(n)$ | step 가중 running 분포(§1.3), $1\le n\le \text{top}$, $h>0$만 | `hh` | `MTP:dp_grid` |
| $\text{top}$ | 최대 폭 = `batch_size` (NPU 16) | `top` | 같음 |
| $k$ | 격자 전체 크기 상한(1·top 포함; NPU 6, GPU 4) | `max_buckets`, `k` | `MTP:dp_grid`, `GMM:dp_grid` 호출부 |
| $F(b)$ | §0.2 고정비 | `fixed` | `GRD:interpolated_fixed_costs` |
| $H(a,b]$ | $\sum_{a<n\le b}h(n)$ (prefix 합) | `seg` | `GRD:optimal_grid` |

### 4.2 목적함수·제약

```latex
\min_{\mathcal G}\ \mathrm{cost}(\mathcal G;h)=\sum_{n=1}^{\text{top}} h(n)\,t\bigl(b_{\mathcal G}(n),n\bigr)
=\underbrace{\sum_n h(n)\,F\bigl(b_{\mathcal G}(n)\bigr)}_{\mathcal G\text{ 의존}}+\underbrace{\sum_n h(n)(c_0+c_1 n)}_{\mathcal G\text{ 무관}}
```
```latex
\text{s.t.}\quad \{1,\ \text{top}\}\subseteq\mathcal G\subseteq\{1,\dots,\text{top}\},\qquad |\mathcal G|\le k
```
후보 수 $\sum_{j=0}^{k-2}\binom{\text{top}-2}{j}$ ($\text{top}=16,k=6$: 1,471). 출처: `GRD` docstring, `GRD:grid_fixed_cost`, `GRD:grid_total_cost`, `GRD:count_grids`; `V0` B3 (i).

### 4.3 DP 점화식

```latex
\mathcal F[1][1] = h(1)\,F(1)
```
```latex
\mathcal F[j][b] = \min_{1\le b'<b,\ \mathcal F[j-1][b']\ \text{정의됨}}\Bigl(\mathcal F[j-1][b'] + F(b)\,H(b',b]\Bigr),\qquad 2\le j\le k,\ 2\le b\le\text{top}
```
```latex
\mathcal F^\star = \min_{2\le j\le k}\mathcal F[j][\text{top}]
```
동률($|\Delta|\le10^{-12}\max(1,|\cdot|)$): 사전식 최소 격자. 출처: `GRD:optimal_grid`, `GRD:_better`; `V0` B3 (i).

GPU: $\mathcal G_{\text{GPU}} = \mathrm{DP}(h;\ \text{top}=\texttt{max\_num\_seqs},\ k=4,\ F=F_{\text{GTASK05}})\cup\{16\}$. 출처: `GMM:dp_grid`, `experiments/gpu/multiturn/predict_blind.py:main`.

### 4.4 복잡도

```latex
\text{시간 } O(k\cdot \text{top}^2),\qquad \text{공간 } O(k\cdot\text{top})\ \text{(값)}\ +\ O(k^2\cdot\text{top})\ \text{(격자 tuple 저장)}
```
전수 열거 대조 $O\!\left(\text{top}\sum_{j\le k-2}\binom{\text{top}-2}{j}\right)$. self-check: DP = 전수 1,200/1,200, 0.043 s 대 0.417 s (`V0` B3 self-check). 출처: `GRD` docstring.

### 4.5 조건부 최적화 (점유 분포 고정)

```latex
\mathcal G^{\text{DP}}(\mathcal G_0) = \arg\min_{\mathcal G}\ \mathrm{cost}\bigl(\mathcal G;\ h_{\mathcal G_0}\bigr),\qquad
h_{\mathcal G_0}=h\bigl(\cdot\,;\ t_{\mathcal G_0}\bigr)\ \text{(§1, §3.3을 } \mathcal G_0 \text{에서 계산)}
```
되먹임 미포함: $h_{\mathcal G}$는 $t_{\mathcal G}$ → $\mu(n)$ → $\pi$로 $\mathcal G$에 의존(`GRD` docstring "What this does not model"; `V0` B3 (ii)1).

최선 응답 반복(확인 절차):
```latex
\mathcal G_{i+1} = \mathrm{DP}\bigl(h_{\mathcal G_i}\bigr),\quad i=0..4;\qquad
\begin{cases}
\mathcal G_{i+1}=\mathcal G_i & \texttt{fixed\_point}\\
\mathcal G_{i+1}\in\{\mathcal G_0..\mathcal G_{i-1}\} & \texttt{cycle}\\
\text{그 외 5회} & \texttt{no\_convergence}
\end{cases}
```
고정점 조건: $\mathcal G^\star = \mathrm{DP}(h_{\mathcal G^\star})$ (필요조건, 충분조건 아님 — `RP` §R3 설계 원칙). 출처: `MTP:best_response_chain`, `SEL:main`.

### 4.6 재계산 확인 기록

regret 정의:
```latex
\mathrm{regret}_{\text{rel}}(h)=\frac{\mathrm{cost}(\mathcal G^\star;h)-\mathrm{cost}(\mathcal G^{\text{DP}};h)}{\mathrm{cost}(\mathcal G^\star;h)}\quad(c_0,c_1\text{ 포함})
```
출처: `RP` §R3 계산 방법.

| 기록 | $h$의 출처 | 시작 격자 | 결과 | 출처 |
|---|---|---|---|---|
| R3a | 시뮬레이터 $h$ (config_search 입력 27칸) | $\mathcal G^\star=(1,4,6,8,10,16)$ | DP = $\mathcal G^\star$, regret 0, $E(h)=0.02851$ — `PASS (EXACT)` | `docs/research/TASK72.md` §R3; `RP` §R3, §8.2 |
| R3b | 관측 `[BUCKET]` (TUNED 12 파일 합) | $\mathcal G^\star$ | DP = $\mathcal G^\star$, regret 0, $E(h)=0.02978$ — `PASS (EXACT)` | 같음 |
| R3b N별(보고만) | 관측, N=10/6/8 | $\mathcal G^\star$ | (1,3,5,8,10,16) 0.00059; (1,2,4,5,6,16) 0.01399; (1,3,5,6,8,16) 0.00743 | 같음 |
| R3c | R3a $h$ | $\mathcal G^\star$ | 시작점이 고정점(반복 0, 순환 없음) | `docs/research/TASK72.md` §R3 |
| 해석 경로 (B2+v1 $h$) | §1–§3, N=6 | TUNED | (1,2,3,4,5,16), `fixed_point` 1회 | `docs/research/TASK78.md` 결과표; `SEL:main` |
| 〃 | N=8 | TUNED | (1,2,3,4,6,16), `fixed_point` 1회 | 같음 |
| 〃 | N=10 | TUNED | (1,3,4,5,7,16), `fixed_point` 1회 | 같음 |
| 〃 | N=12 | TUNED | (1,4,5,6,8,16), `fixed_point` 1회 | 같음 |
| 시뮬레이터 경로 | sim $h$, N=6/8/10/12 | TUNED | 고정점 2/1/1회, N=12 `cycle`(3격자) | 같음 |

주: R3c는 **시뮬레이터 $h$**에서의 확인. B2 해석 $h$에서의 확인은 TASK78(선정용 plan, seed `20261200+10N+r`).

---

## 5. "대기시간 분포의 평균에만 의존" — 성립 가정

근거 문헌: F. Baskett, K. M. Chandy, R. R. Muntz, F. G. Palacios, "Open, Closed, and Mixed Networks of Queues with Different Classes of Customers," *J. ACM* 22(2):248–260, 1975 (BCMP).

### 5.1 BCMP 곱 형태·무감응 조건

- 망: open/closed/mixed, Markov routing, 다중 class 허용.
- 곱 형태 정상 분포 $\pi(\mathbf n)\propto\prod_i f_i(n_i)$.
- 허용 station 4종:
  - Type 1: **FCFS** — 서비스 **지수분포**, 모든 class 같은 율(대기열 길이 의존 율 허용).
  - Type 2: **PS** (processor sharing) — 일반 서비스 분포(Coxian/유리 Laplace 변환).
  - Type 3: **IS** (infinite server, delay station) — 일반 분포.
  - Type 4: **LCFS-PR** — 일반 분포.
- 무감응성: Type 2–4에서 $\pi$는 서비스 시간 분포의 **평균에만** 의존.
- 상태 의존 율: station 내 고객 수에 의존하는 율 허용(load-dependent).

### 5.2 이 연구의 대응 (B2)

| 구성 요소 | 모형 처리 | BCMP 유형 | 출처 |
|---|---|---|---|
| tool gap | delay station, 평균 $Z$ | Type 3 (IS) ✓ | `OCC` docstring; `V0` B2 (ii)1 |
| 엔진, $n\le M$ | PS, 율 $r(n)/(D\,t(r(n)))\cdot\varphi$ | Type 2 (PS, load-dependent) ✓ | 같음 |
| 엔진, $n>M$ | $M$개 PS + FCFS 대기 | 비 BCMP (FCFS인데 서비스 비지수) ✗ → 근사 | `OCC:solve_occupancy` `notes`; `V0` B2 (ii)1 |
| 배타 prefill | 평균장 감속 $\varphi=1-X\,\mathbb E[P]$ | 비 BCMP (모든 decoder 동시 정지 = 비대칭 서비스) ✗ → 근사 | `OCC` docstring "Limits"; `V0` B2 (ii)2 |
| 요청당 decode 길이 | 평균 $D$만 | $n\le M$에서 PS 무감응으로 정확 | `V0` B2 (ii)3 |
| class 구조 | 단일 class(첫 turn·hit·miss를 $\mathbb E[P]$로 평균) | 근사 | `MTP:analytic` |
| $\varphi$와 $X$ | 상태 무관 상수의 고정점 | 근사(평균장) | `OCC:solve_occupancy` |

### 5.3 이탈의 관측 크기 (TASK90 발견 1)

step 가중 평균 running, 개발 집합. D = 지수 gap·배타 prefill, E = plan gap(heavy-tailed)·배타 prefill, C′−C = 비배타에서의 같은 gap 변경. 출처: `docs/research/TASK90.md` 결과 "B2 진단 분해", 핵심 발견 1; `experiments/npu/stage3/b2_diag.py`.

| cell | B2 (A) | D | E | gap 모양 효과 (E−D), 배타 | gap 모양 효과 (C′−C), 비배타 | 관측 (O) |
|---|---|---|---|---|---|---|
| BASE N12 | 5.404 | 5.361 | 5.437 | +0.077 | +0.401 | 5.316 |
| BASE N14 | 6.678 | 6.615 | 6.220 | **−0.395** | +0.663 | 6.283 |
| BASE N16 | 7.305 | 7.500 | 7.051 | **−0.450** | −0.001 | 6.875 |
| TUNED N16 | 6.693 | 7.339 | 6.604 | −0.735 | −0.018 | 6.812 |
| BATCHONLY N16 | 6.851 | 7.597 | 6.800 | −0.797 | −0.015 | 6.900 |

- 지수 gap(D): B2와 근접(BASE N14 6.615 대 6.678, N16 7.500 대 7.305).
- heavy-tailed gap + 배타 prefill: 무감응성 붕괴(부호가 실행 방식에 의존).
- 배타 prefill 명시 Markov 연쇄(`src/continuum/model/occupancy_v12.py`, 미채택): gap 모양에 무감응(BASE N14 6.647, N16 7.370) — 원인 후보 = 결정적 prefill 시간·turn 구조(가설).

---

## 6. 문서 대 코드 차이

| # | 항목 | 문서 | 코드 | 사용 |
|---|---|---|---|---|
| D1 | $s_{\text{act}}$ | `V1` §3 표: $T$ 고유 $P(q_T)+(g_T-1)\,t(\bar n)/\varphi$ | 평균 $\bar S=\mathbb E[P]+D\,t(\cdot)/\varphi$ (= $1/\mu$), 모든 $T$ 공통 (`MTP:analytic`) | 코드 |
| D2 | $s_{\text{idle}}$ | `V1` §3 표: tool gap + 재입장 대기; `V0` B1 (B1-3) $W_{\text{FIFO}}$에 재입장 대기 포함 | NPU: 양의 gap 표본만, 대기 0 (`MTP:analytic`, `MTP:plan_stats`). GPU: $g+\max(0,\bar R-\bar S)$ (`GMM:analytic`) | 코드 |
| D3 | $t(\bar n)$의 $\bar n$ | `V1` §3: $\bar n$ (가중 미지정) | 시간 가중 평균 running, $\max(1,\mathrm{round}(\cdot))$ (`OCC:Occupancy.mean_running`, `MTP:analytic`) | 코드 |
| D4 | 초기 상태 | `V1` §2·§3: $a_0=k,\ d_0=C-1-k$ | $a_0=\min(k,C-1)$, $d_0=C-1-a_0$ ($k=M=C$일 때 절단) (`SV1:steady_state_survival`) | 코드 |
| D5 | B1–B2 결합 고정점 | `V0` B2 (ii)4·(iv): v0는 결합 고정점 미실행; `V1`: "B2·B3·B4는 v0 그대로", 결합 고정점 서술 없음 | $p^{(0)}=0.9$, 감쇠 ½, tol $10^{-7}$, ≤ 30회 (`MTP:analytic`). 언급: `MTP` docstring, `docs/research/TASK78.md` 수행 2 | 코드 |
| D6 | 결합 후 출력의 일관성 | 문서 없음 | `h`·$X$·$\varphi$·$\bar n$ = 마지막 반복 B2 해(이전 $p$ 기반 $\mathbb E[P]$); `prefill_per_turn_s` = 최종 $p$로 재계산 (`MTP:analytic`) | 코드 |
| D7 | $G$ 기호 | `V0` B2: $G$ = 요청당 decode step 수; `V1` §3: $(G-1)$, $G$ = 생성 길이 | $D=\bar g-1$ (`MTP:analytic` `decode_steps_per_request`) | 코드 ($D$) |
| D8 | $Z$ 정의 | `OCC:ClosedWorkload` docstring: tool gap + client overhead | plan `gap_after_s` 평균, 마지막 turn 0 포함, client overhead 없음 (`MTP:plan_stats`) | 코드 |
| D9 | DP 최종 min 범위 | `V0` B3·`GRD` docstring: $\min_{j\le k}$ | $\min_{2\le j\le k}$ (top ≥ 2에서 동치) (`GRD:optimal_grid`) | 코드 (동치) |
| D10 | LRU 형태의 미반영 항 | `V1` §4: hit block touch 미반영, $\lambda_{\text{blocks}}$ 유도 없음 | touch를 $d_0$에서 차감, $\lambda_b=X\cdot$(새 block 수) 정의 (`GMM:analytic`) | 코드 |
| D11 | neutral LRU underflow | `docs/research/gpu/GPU_MULTITURN_DESIGN.md` §4, `GMM:lru_survival` docstring: neutral 함수가 평균 ≈ 745 초과 시 underflow | neutral `SV1:lru_block_survival`에 평균 ≥ 600 log 공간 분기 존재 | 코드 |
| D12 | B1 입력 $K_{\text{pin}}$ | `V0` B1 (B1-1)·(ii)4: $K_{\text{pin}}$ 입력(기본 0) | v1은 $K_{\text{pin}}$ 대신 상태 $a$ (`SV1`) — v0→v1 교체, `V1` §2 서술과 일치 | 코드 (v1) |

---

## 7. 코드·문서로 확정하지 못한 항목

- §3.3 결합 고정점이 보고된 예측에서 30회 안에 수렴했는지: 코드가 수렴 플래그를 반환·기록하지 않음.
- $p^{(0)}=0.9$, 감쇠 ½, 분위 압축 40 bin, tol $10^{-7}$의 선택 근거: 문서 없음.
- $\varphi$ 반복의 수렴 보장: 코드 주석 "map is monotone decreasing in φ"만, 증명·문서 없음.
- GPU 격자(§4.3 GPU)의 최선 응답 반복·고정점 확인 기록: 찾지 못함(코드상 단일 DP).
- B2 해석 $h$에서의 고정점 확인(TASK78)은 선정용 plan에서만; 본 실험 plan에서의 재확인 기록 없음.
- BCMP 서지: 코드에는 "(BCMP)" 표기만, 전체 서지는 본 문서에서 추가.
