# Escapement Research Task Index

<!-- 저장소가 continuum-npu → escapement로 개명됐다(2026-08-25). 표제만 바꾸고 과거 TASK 기록의 서술과 경로는 당시 사실 그대로 둔다. 결정 5 참조. -->

이 문서는 모든 agent가 작업 전에 읽는 연구 진행 상황의 단일 진입점이다. 상세 작성 규칙은 [TASK_GUIDE.md](TASK_GUIDE.md)를 따른다.

## 현재 상태

현재 연구 단계: Stage 0, Stage 1a, Stage 1b가 모두 `PASS`했고, [TASK11](TASK11.md)에서 prefix cache hit 단위를 **inner block 128 token**으로 확정했다. [TASK12](TASK12.md)에서 결정 3을 집행해 per-step decoder bucket 관측 patch를 적용·검증했고, [TASK13](TASK13.md)에서 decode step 비용을 `f(bucket) + g(actual)`로 분해했다. [TASK14](TASK14.md)에서 prefix-cache 생존 문턱을 실측하고 [TASK15](TASK15.md)에서 12/12 trial로 재현해 실제 재계산까지 확정했다. [TASK16](TASK16.md)에서 substrate descriptor와 층 태깅 규칙으로 "질문은 클래스, 상수는 인스턴스"를 코드·기록 체계에 구조화했고, [TASK17](TASK17.md)에서 agentic workload generator로 bucket 전이를 처음 관측했다. [TASK18](TASK18.md)에서 per-request 귀속 게이트를 통과하고 [TASK19](TASK19.md)에서 첫 짝 비교를, [TASK20](TASK20.md)에서 44 조합 N/slots sweep을 수행했다. **agentic gap의 utilization 효과는 부호가 바뀐다** — N이 compiled bucket 사이에 끼면(N=6) 오히려 15 % 높고, N=10–12에서 9 % 낮다. [TASK21](TASK21.md)에서 총 gap 시간을 고정하고 분산만 바꿔 재사용률이 움직임을 관측했다(DISPERSED 11/24 vs SYNC 7/24, 반대 방향 0블록이나 동률 1블록으로 `INCONCLUSIVE`). [TASK22](TASK22.md)에서 prefill 배타 실행을 직접 관측해 비용 모형 v2를 세웠고, [TASK23](TASK23.md)에서 **bucket 격자를 재compile로 바꾸는 개입으로 부호 역전의 원인을 확정했다** — bucket 6을 추가하자 N=6의 역전(pooled 1.1504)이 소멸했다(0.9717). [TASK24](TASK24.md)에서 **step 수준 시뮬레이터**를 세워 보정 파라미터 없이 기존 80조합을 재현했고(utilization 평균절대오차 0.0066, pooled ratio 방향 11/11), 닫힌 식이 설명하지 못하던 N=4·N=5 이상치의 기전을 감쇠 경로로 밝혔다. [TASK25](TASK25.md)에서 그 시뮬레이터의 **out-of-sample 예측력이 선등록 게이트를 통과했다** — 측정 전에 commit한 pooled ratio 3개가 최대 오차 0.0040으로 맞았다(허용치 ±0.05). [TASK26](TASK26.md)에서 그 위에 offline oracle을 올려 **반환 시점 재배치에 실질적 headroom이 있음**(ε=0.5 s에 1.2–4.4 %, ε=5 s에 9.7–27.2 %)을 계산했고, 동시에 **utilization이 비용 지표가 아니라는 것**을 확인했다. [TASK27](TASK27.md)에서 그 headroom이 **단순 causal 정책으로는 회수되지 않음**을 계산으로 확정했고, [TASK28](TASK28.md)에서 그 계산이 **실기기에서 재현됐다** — 측정 전 commit한 device time ratio가 확증 구간 2/2에서 허용치 안이며(오차 +0.018·+0.021), 회수율 X는 N=6 −105 %, N=8 −70 %다. headroom은 조정이 아니라 **예지**에서 나온다. [TASK34](TASK34.md)에서 워크로드 통계만으로 고른 compile 구성(`batch_size` 8→16)이 device time을 회수함을 관측했고(확증은 채널 정의 결함으로 보류), **[TASK35](TASK35.md)가 채널을 고쳐 다시 재 N=8에서 확증했다 — X = +9.72 % / +10.07 %(두 채널 합치), 지배 인자가 `batch_size`라는 것도 device 절제로 확인**됐다. **이로써 이 연구 프로그램의 측정 단계는 종료됐다.** [TASK36](TASK36.md)이 그 마지막 미해결 항목 — [TASK35](TASK35.md)의 N=6 채널 보류 — 을 닫았다: 채널 허용차를 절대 잔차까지 담도록 교정해 선등록하고 **전부 신규 seed**로 다시 재 **확증 2/2 `PASS`**를 얻었으며, **원 기준 0.02로도 통과**해 완화에 기대지 않았다. **X의 적용 범위가 N ∈ {6, 8}로 확장**되되 값은 단일 값이 아니라 **+2.1 % ~ +10.1 % 구간**이다. [TASK37](TASK37.md)에서 논문 조립 산출물 7종(서사·주장 매핑·그림 8종·related work·한계·초록·타깃)을 만들었고, **[TASK38](TASK38.md)이 서지 3건을 정정하고(`LENS`·`KV-RM`·CacheScout) 그림 8종의 데이터 상수 138개를 원 TASK 표와 자동 대조해 불일치 0을 확인했으며, 시스템 명칭을 `Escapement`로 확정 반영하고 arXiv 공개 점검표를 만들었다. [TASK39](TASK39.md)가 영문 초록을 arXiv 상한 안으로 압축하고(3,029 → 1,876자) **설치 없이** SVG→PDF 경로를 열어 영문 그림을 PDF로 냈다. **[TASK40](TASK40.md)이 측정 단계를 한 번 더 열어 `batch_size` 포화 곡선을 쟀다 — B ∈ {8,16,24,32}에서 **B=16 이후 평평**하고(통제된 인접쌍 2/2 `포화`), 기전은 생존율 포화와 **최상위 눈금 0.0 % 사용**이다. 최적 `batch_size`는 하드웨어 상한이 아니라 워크로드 분포가 정한다. [TASK41](TASK41.md)이 그 결과를 논문에 반영하고 **본문 초고 10절을 완결**했으며 LaTeX 이식 패키지를 만들었다. **[TASK42](TASK42.md)가 Advisor 첨삭과 `[NEEDS-EVIDENCE]` 3건을 집행하고(부록 A–D 신설, CLAIMS 1.18 추가) 캡션 11종·인용 18개로 교정 1차를 마쳤으며, 확정된 저자 3인·감사의 글·AI 사용 고지·CC BY 4.0을 반영해 제출 패키지를 완성했다 — 제출은 하지 않았다.** [TASK33](TASK33.md)에서 남은 headroom을 정보 축으로 분해해 **절반 이상(중앙 60 %)이 지식으로 살 수 없는 *조율*의 몫**임을 확인하고, 사전 정의된 분기에 따라 **compile-time이 유일 회수 경로**로 확정했다. [TASK32](TASK32.md)에서 arXiv:2511.02230 §4.2의 예측기를 차용해 그 오차가 **문턱을 5.6–9.7배 초과**하고 **표본을 4자릿수 늘려도 줄지 않음**(줄일 수 없는 분산)을 확인했다. [TASK31](TASK31.md)에서 **합성 gap을 실측 tool latency 분포로 교체**해 시뮬레이터가 워크로드 전환을 넘어 전이됨을 확인했고(연속성 `PASS` 3/3), headroom은 남지만(ε=2 s에서 5.0–6.9 %) **반환 시각 정보의 값은 사라짐**을 계산했다. [TASK30](TASK30.md)에서 **예지의 가치를 곡선으로 재** 반환 시각만 알아도 ε ≥ 2 s에서 headroom의 86–88 %(N=6·8)가 회수되고 정확도 문턱 σ*가 gap 표준편차와 같은 자릿수(1.0–1.8 s)임을 계산했다. [TASK29](TASK29.md)에서 기전 3개를 절제해 귀속을 확인했다 — 격자 법칙은 연속 격자에서 1.0000으로 소멸하지만 **GPU cudagraph 격자에서는 소멸하지 않고**, 재사용 절벽의 "개수 문턱"은 시퀀스 단위 FIFO의 산물이며, chunked prefill은 정지를 없애면서 device time을 3–10 % **늘린다**.

가장 최근 TASK: [TASK44](TASK44.md) — 원고 교정 배치 1: 빌드 수정과 외부 검토 반영 (`DONE`)

**측정 단계 종료.** [TASK35](TASK35.md)가 이 프로그램의 마지막 본 측정이고 [TASK36](TASK36.md)이 그 미해결 확증 1건을 닫는 후속 측정이었다. **논문 조립은 [TASK37](TASK37.md)–[TASK39](TASK39.md)에서 뼈대·정정·제출 준비까지 완료**됐고 시스템 명칭은 **`Escapement`** 로 확정됐다. [TASK40](TASK40.md)이 후속 연구 3번을 해소했고 [TASK41](TASK41.md)이 **본문 초고 10절과 LaTeX 패키지**까지 만들었다. [TASK42](TASK42.md)가 첨삭·저자 확정까지, [TASK43](TASK43.md)이 repo 개명 정합화를, [TASK44](TASK44.md)가 빌드 수정 4건과 외부 검토 18건 반영·3건 기각을 마쳤다. **남은 것은 첫 Overleaf 빌드와 그림 육안 검수다.** 저자·소속·감사의 글·라이선스는 확정 반영됐고, 제출은 저자 계정 작업이라 이 저장소의 범위 밖이다. 미해결 연구 항목은 아래 [후속 연구](#후속-연구) 절에 정리했다.

"가장 최근 TASK"는 번호가 가장 큰 TASK다. 그 TASK의 상태가 `BLOCKED`, `PARTIAL`, `FAILED`, `INVALID` 중 하나여서 최근 진척을 대표하지 못할 때만 아래에 "최근 완료 TASK"(가장 번호가 큰 `DONE` TASK)를 별도로 한 줄 추가한다. 두 줄이 같은 TASK를 가리키면 한 줄만 남긴다.

현재 주요 blocker: 없다. 미해결 사용자 결정도 없다 — [결정 5](#결정-5--시스템-명칭-충돌)가 해소되어 시스템 명칭은 **`Escapement`** 다. 논문 공개 전 사용자 확인 항목(저자·라이선스·AI 고지·**그림 육안 검수**)은 [paper/ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6에 있다. Stage 2와 Track A는 blocker가 아니라 아직 실행하지 않은 상태다.

**substrate 상태 주의**: 이 host의 `vllm-rbln 0.11.1`은 [TASK12](TASK12.md)의 observation-only patch가 **적용된 상태**다 (`model_base.py` SHA256 `70942d16…`). Git이 추적하지 않으므로 모든 측정 run은 `bash patches/vllm_rbln-0.11.1/apply.sh status` 출력을 artifact에 provenance로 남긴다.

Stage 1 이후 설계에 제약이 되는 관측 (근거 [TASK06](TASK06.md), [TASK08](TASK08.md)):

- `attn_impl=eager` 기본값에서 KV pool 크기는 DRAM이 아니라 `batch_size`가 결정한다. `kvcache_num_blocks = (max_seq_len // kvcache_block_size) × batch_size`이고 기본값에서 `kvcache_block_size = max_seq_len`이므로 결과는 정확히 `batch_size`이며 block 1개가 sequence 1개분이다. 현재 b1 artifact의 KV pool은 sequence 1개분(8,320 token)뿐이므로 동시성 실험은 재compile을 전제로 한다.
- decoder bucket은 자동으로 다단화되지 않는다. `decoder_batch_sizes`를 명시하지 않으면 단일 bucket이고 bucket 선택 자체가 일어나지 않는다.
- per-step `(요청 수, 선택된 bucket)`은 upstream에서 계산만 되고 노출되지 않았으나, [TASK12](TASK12.md)의 observation-only patch가 `[BUCKET] request_nums=<n> padded_batch_size=<b>` DEBUG 로그로 노출시켰다. 사상표는 [TASK13](TASK13.md)에서 완성됐다: 1→1, 2→2, 3→4, 4→4, 5→8, 6→8, 7→8, 8→8. **사상 규칙은 격자에 종속이며 격자를 바꾸면 따라 바뀐다** — [TASK23](TASK23.md)이 `decoder_batch_sizes=1,2,4,6,8`로 재compile한 artifact에서 5→6, 6→6, 7→8을 확인했다.
- **비용 모형 v2 = decode 항 + prefill 직렬화 항** ([TASK22](TASK22.md)). prefill은 실행 중인 **모든** 세션의 decode를 그 길이만큼 정지시킨다. `prefill_s(n) = ceil(n/128) × (0.021206 + 6.399e-7 × n)`이고, 시스템 비용은 `prefill_s × 동시 decoder 수`다. [TASK20](TASK20.md)의 v1 편향(0.57–0.86, N 의존)이 이 항으로 87–120 % 설명되어 v2에서 0.97–1.04로 모인다. **cache 실패의 비용은 재계산 시간 × 동시 decoder 수**다.
- **격자 정렬 법칙이 작동하는 padding의 하한은 1/8과 1/4 사이다** ([TASK25](TASK25.md), 6블록 판정). padding 1/4(N=3)은 "역전" 확정(pooled 1.0994, 5/6), padding 1/8(N=7)은 6블록에서도 4/6이 동치 밴드 안이라 미결이다.
- **bucket 격자 정렬이 gap 효과의 부호를 결정한다** ([TASK23](TASK23.md), 개입으로 확인). `padding_slots(N) = bucket_for(N) − N`이 있으면 AGENTIC이 유리하고 0이면 불리하다. 워크로드·seed·모델·slot 수를 고정하고 격자에 bucket 6만 추가하자 N=6 pooled ratio가 1.1504 → 0.9717로 내려가 역전이 소멸했다. **법칙의 형태는 `class`, 격자·문턱·크기는 `stack`**이다. **크기 모형은 [TASK24](TASK24.md)의 시뮬레이터가 대신하며 [TASK25](TASK25.md)에서 예측력이 검증됐다** — `padding_slots(N)`은 정상 상태만 가격을 매기므로 실제 padding의 **하한**이며, 단조성이 N=4·N=5에서 깨지는 것은 batch가 N→1로 내려가는 **감쇠 경로**의 padding 때문이다.
- **decode step 비용 모형** ([TASK13](TASK13.md), 정상 상태 한정): `step_time ≈ f(bucket) + g(actual)`. `f`는 계단 함수로 model p50이 bucket 1/2/4/8에서 9.51 / 10.05 / 10.355 / 12.4025 ms이고 같은 bucket 내 범위는 0.01–0.03 ms다. `g`는 model·sampler 밖 engine overhead로 요청당 약 0.041 ms다. bucket 효과가 지배 항이므로 slot 낭비율은 시간 의미를 갖되 "bucket 한 단계 비용"으로 읽는다. `VLLM_RBLN_DECODE_BATCH_BUCKET_*`와 `VLLM_RBLN_SUB_BLOCK_CACHE`는 기본 경로에서 무효다.
- `num_gpu_blocks`는 frontend가 EngineCore 보고값을 누적하는 구조(`vllm/v1/engine/core_client.py:712`) 때문에 EngineCore 값의 2배로 나온다([TASK09](TASK09.md)에서 해소). 실제 KV pool은 EngineCore 값이다. `"GPU KV cache size: N tokens"` log는 `num_blocks × block_size`가 아니라 `max_concurrency × max_model_len`이다.
- **격자 정렬 법칙은 GPU에서도 소멸하지 않을 것으로 계산된다** ([TASK29](TASK29.md), **모형 진술**). vLLM의 cudagraph capture size 기본 목록은 `max_num_seqs=8`에서 `[1,2,4,8,16]`(`vllm/config/compilation.py:676–690`)이고 유효 구간이 NPU 격자와 같아 pooled ratio가 동일하다. 연속 격자에서만 1.0000으로 소멸한다. **GPU 대비에서 재야 할 축은 accelerator가 아니라 `max_num_seqs`다.**
- **prefill 배타 실행은 순수 비용이 아니라 일부는 batching 보조금이다** ([TASK29](TASK29.md), **모형 진술**). chunked로 바꾸면 정지 항이 0이 되지만 device time이 3–10 % **늘어난다** — 배타 실행이 decoder를 멈춰 세워 강제 동기화시키고 재개 시 더 넓은 batch를 만들고 있었다.
- **compile 구성 선택이 device time을 9.7–10.1 % 회수하며(N=8 확증, 두 채널 합치), 지배 인자는 bucket 격자가 아니라 `batch_size`(= KV pool 크기)다** ([TASK35](TASK35.md), 선등록 채널로 확증·device 절제로 확인). arm 절제에서 `batch_size`만 바꾼 구성이 +8.25 %를 내고 bucket 격자 정합이 +1.5 %p를 더한다. **두 arm의 prefill비가 실측에서도 동일**해(0.678/0.678) 차이를 decode 항 하나로 귀속할 수 있다. `batch_size`가 `kvcache_num_blocks`를 정하고([TASK08](TASK08.md)) 그것이 캐시 생존을, 캐시 생존이 prefill 재계산을 정한다. sim 귀속에서 batch만 +7.21 %, bucket 정제만 +0.71 %다. **구성 선택은 gap 분포에 둔감하고 동시 세션 수 상한에만 반응하므로, 재구성 판단에 다시 재야 할 통계는 그것 하나다.**
- **`batch_size`의 이득은 B=16에서 포화하며, 최적값은 하드웨어 상한이 아니라 워크로드 분포가 정한다** ([TASK40](TASK40.md), 통제된 인접쌍 2/2 `포화`). 눈금을 `(1,4,6,8,10,B)`로 고정하고 최상위만 바꾼 비교에서 B16→B24 중앙 ratio 0.9999, B24→B32 1.0002(CI 폭 0.0016)다. **기전은 두 겹** — 생존율이 B=16에서 포화해 살릴 캐시가 없고, **최상위 눈금 16·24·32가 전 조합에서 0.0 % 선택**돼 그 큰 step 비용이 부과되지도 않는다. device 메모리는 `2.1 + 0.28125 × B` GiB/device로 KV 한계가 **B ≈ 46**(외삽)인데 **이득은 그 3분의 1에서 끝난다.** 다만 N=10의 2블록에서만 B16→B24가 2 % 더 주는데, 그곳만 생존율이 28/30으로 잔량이 남아 있었다 — [TASK36](TASK36.md)의 잔량 법칙이 세 번째로 재현된 지점이다. **N > 16(최상위 눈금이 실제로 쓰이는 구간)의 반전 여부는 재지 않았다.**
- **`batch_size` 지배는 무조건이 아니라 조건부다** ([TASK36](TASK36.md), 신규 seed N=6). 이득의 크기는 **`BASE`가 잃는 캐시의 양**에 비례한다. `BASE`가 이미 17/18을 재사용하는 plan에서는 `batch_size`만 바꾼 arm의 이득이 **+0.59 %로 동치 밴드 안**이고, 이득의 거의 전부(+1.52 %p)가 bucket 격자에서 온다. **[TASK35](TASK35.md)의 "지배 인자는 `batch_size`"는 "지배 인자는 회수 가능한 캐시 손실이며 그것을 사는 레버가 `batch_size`"로 읽는다.** 시뮬레이터가 이 역전을 측정 전에 예측했다. 또한 격자 정합은 교환이다 — `TUNED`는 `5,6 → 6`으로 padding을 줄이면서 `2 → 4`로 늘린다.
- **현실 headroom의 절반 이상은 지식이 아니라 조율의 몫이다** ([TASK33](TASK33.md), 계산). 전지적 지식으로 세션별 독립 결정을 내리면 headroom의 27–51 %만 회수되고 나머지 49–73 %가 사라진다. **per-session client 정책은 원리적으로 그 부분에 닿을 수 없으며**, 조율이 가능한 위치는 전 세션을 보는 server 측 scheduler이거나 조율을 설계 시점에 굳히는 **compile-time 구성**이다.
- **tool 지속시간의 예측 오차는 줄일 수 없는 분산이 지배한다** ([TASK32](TASK32.md)). 도구별 표본을 10 → 100,000으로 늘려도 오차 std가 8.4 → 10.5 s로 개선되지 않는다. `Bash`가 27 ms일지 300 s일지는 명령이 정하고 **도구 이름은 그것을 담지 않는다.** 평균의 상한(`B(δ)`)과 점추정(`μ̂`)의 오차 std가 같으므로(10.196 대 10.185) 더 나은 추정자가 아니라 **더 나은 조건화**가 필요하다.
- **예지의 가치는 워크로드에 종속이며 이식되지 않는다** ([TASK31](TASK31.md), 계산). 실측 tool latency 분포에서는 반환 시각을 정확히 알아도 이득이 −1.20 %~+0.99 %이고 σ\*가 정의되지 않는다. 동료 도착 기회는 두 워크로드가 비슷하므로(ε=2 s에서 73.6 대 81.9 %) **기회가 아니라 그 기회의 값이 없다.** headroom 자체는 남는다(ε=2 s에서 5.0–6.9 %).
- **합성 `uniform:1:5` gap은 재사용 압박을 과대평가한다** ([TASK31](TASK31.md)). 실측 도구 호출의 71 %가 1초 미만이라 세션이 축출 전에 돌아온다 — 현실 재사용률이 88.9/50.0/26.7 %로 합성의 72.2/37.5/16.7 %보다 모든 N에서 높다. **[TASK14](TASK14.md)–[TASK21](TASK21.md)의 재사용 수치는 이 방향으로 보수적이다.**
- **반환 시각 하나만 알아도 headroom의 대부분이 회수된다 — 단 예산이 충분할 때만이다** ([TASK30](TASK30.md), 계산. **합성 gap 한정** — [TASK31](TASK31.md) 참조). ε=5 s에서 omniscient의 86–88 %(N=6·8), ε=1 s에서는 6.7 %뿐이다. **정확도 문턱 σ\* = 0.74–1.27 × gap 표준편차**이므로 완벽한 예측이 필요 없고, **예산과 정확도가 서로를 대신한다.** σ\*는 gap 분포의 함수이므로 워크로드를 바꾸면 다시 계산해야 한다.
- **offline headroom은 예지에서 나오며 단순 causal 정책으로 회수되지 않는다** ([TASK27](TASK27.md), [TASK28](TASK28.md)에서 실기기 확인, 회수율 X = −105 %·−70 %). oracle은 세션의 47 %를 보류하지 않고 소수만 예산 끝까지 붙드는데, 어느 소수인지는 **동료의 복귀 시점**에 달려 있다. 현재 상태만 보는 정책(`QUANTIZE`/`TOPUP`/`FREESLOT`)은 전부 평균 절감이 음수다. **"조금 기다렸다 같이 보낸다"는 직관은 이 substrate에서 틀렸다.**
- **utilization은 비용 지표가 아니다** ([TASK26](TASK26.md)). 작업량이 보존되는 재배치에서 slot 점유율과 device time은 반대로 움직인다 — utilization을 최대화한 일정이 device time을 11–37 % 더 쓴다. 실측 arm 비교에서도 방향이 5/11 어긋난다(AGENTIC은 11/11에서 device time을 더 쓰는데 utilization ratio는 5개에서 낫다고 말한다). **[TASK19](TASK19.md)–[TASK25](TASK25.md)의 utilization ratio 결과는 그대로 유효하되 정책 목적함수로 쓰지 않는다.**
- 채택 가능한 관측 신호([TASK09](TASK09.md), [TASK11](TASK11.md) 감사): `vllm:num_requests_running`, `vllm:num_requests_waiting`, `vllm:kv_cache_usage_perc`(해상도는 inner block, 분모 `num_gpu_blocks−1`), `vllm:prefix_cache_queries_total`·`hits_total`·`prompt_tokens_cached_total`(전부 단위가 요청이 아니라 **token**. **`hits`는 층 1, `cached`는 층 2를 세며 두 값은 층 2가 evict된 뒤 갈라진다** — [TASK15](TASK15.md)), server 주기 로그의 `Running/Waiting/KV usage`, DEBUG 로그의 `[PFX] [CACHE-HIT]`(outer/inner block ID)와 `Allocated/Freed block(s)`. `/metrics` gauge는 반드시 in-flight로 표집하고 metric 이름은 정확히 일치시킨다.
- **prefix cache hit 단위는 inner block 128 token**이다([TASK11](TASK11.md)). hit 양은 `floor((prompt_tokens − 1) / 128) × 128`이며 10개 조건에서 전건 일치했다. prompt가 129 token 미만이면 hit이 구조적으로 0이다. outer block 8,192은 hit 단위가 아니다.
- **동시 workload에서는 counter 증분으로 per-request 귀속을 하지 않는다** ([TASK17](TASK17.md)). **1차 채널은 응답의 `usage.prompt_tokens_details.cached_tokens`다** — `--enable-prompt-tokens-details`를 켜면 층 2 값이 그 요청의 응답에 실려 와 귀속이 구성상 성립한다([TASK18](TASK18.md), 게이트 G1 8/8·G2 16/16·G3 일치). `[PFX]` 로그는 client id가 server id의 strict prefix라 timestamp 없이 join된다. `[BUCKET]` 로그는 step 단위 집계 전용이다.
- **`prefix_cache_hits_total`은 실제 device 재사용의 지표가 아니다** ([TASK14](TASK14.md), [TASK15](TASK15.md) 12/12 재현). 이 metric은 층 1(vLLM inner block)의 판단이며, 층 2(RBLN outer block)가 evict된 뒤에도 hit을 계속 보고한다.
- **층 2를 세는 Prometheus metric이 있다** ([TASK15](TASK15.md)): `vllm:prompt_tokens_cached_total`(재사용 token)과 `vllm:request_prefill_kv_computed_tokens`(실제 계산 token)가 `prefill_stats`(= `sum(cached_length)`, 층 2)에서 나온다. DEBUG 로그 없이도 층 2를 관측할 수 있다. `vllm:iteration_tokens_total`은 계산량 지표가 **아니다**(제출 prompt token을 센다). `VLLM_RBLN_METRICS` PREFILL `Total call counts`는 chunk 수가 아니라 **요청 수**다.
- **재사용 절벽의 법칙 후보** ([TASK15](TASK15.md), 가설): 생존 ⇔ `(target 1 + gap 중 도착 요청 B + resume 1) ≤ outer_slot_count`. 이 인스턴스는 `outer_slot_count = 8`이라 `B ≤ 6`이다. **법칙의 형태는 `class`, 상수 8은 인스턴스 값**이므로 이식하지 않는다. 층 2 miss 시 resume은 prefix를 실제로 재계산한다(prefill 시간 13.1배).
- **층 2 캐시는 prefill이 계산한 token만 담는다** ([TASK24](TASK24.md), 실측 271/271). `cached_tokens = floor(min(직전 prompt, 현재 prompt − 1)/128) × 128`이며 **decode가 생성한 token은 캐시되지 않는다.** 생성이 길수록 재사용률 상한이 내려간다. 생성분을 공유 prefix로 세는 대안은 271건 중 38건만 맞았다.
- **즉시 돌아오는 세션은 자기 캐시를 자기가 축출하지 않는다** ([TASK24](TASK24.md), `[PFX]` 로그 대조). 완료 block이 evictable로 바뀌는 시점이 다음 admission의 victim 선택보다 **뒤**이기 때문이다. gap을 두고 돌아오면 이 보호가 없다. **gap의 재사용 손해에는 경쟁자 증가뿐 아니라 자기 보호 상실이 들어 있다.**
- **prefix cache 생존 구조** ([TASK14](TASK14.md)): 층 1은 inner block 128 token × 512개 LRU, 층 2는 outer block 8,192 token × **8개 FIFO**다(`LRUEvictionPolicy` 클래스는 존재하나 미사용). 8,192 token 이하 요청은 길이와 무관하게 outer block 1개를 쓰므로 **생존을 결정하는 것은 token 총량이 아니라 요청 개수**다. eviction은 할당 순서대로여서 가장 먼저 만들어진 target이 가장 먼저 희생된다.
- **재사용 성패는 재개 도착 순서에 좌우된다** ([TASK17](TASK17.md), [TASK21](TASK21.md)). 총 gap 시간을 고정하고 분산만 늘려도 재사용률이 달라지며, 분산 arm에서는 가장 이른 두 도착이 3/3 블록에서 성공했다. 다만 arm 간 방향은 N에 의존한다([TASK20](TASK20.md)).
- **APC OFF/ON은 단일 인자 토글이 아니다**([TASK11](TASK11.md)). OFF에서 `block_size`가 128 → 8192, `num_gpu_blocks`가 513 → 9, KV cache size가 65,664 → 73,728 token으로 함께 바뀐다. 비교 시 이 confounder를 함께 기록한다. OFF에서는 `queries`조차 0이므로 `--no-enable-prefix-caching`으로 확실히 끌 수 있다.
- **Compile cost는 bucket 수에 선형**이며 재compile은 실질적 제약이 아니다. 관측점 3개(1/4/5 bucket = 165 s·9.083 GiB / 349 s·11.501 GiB / 416 s·12.306 GiB)에서 `시간 ≈ 42.3 + 61.3 × compiled model 수`, `크기 ≈ 8.276 + 0.806 × bucket 수` GiB가 성립한다([TASK06](TASK06.md), [TASK10](TASK10.md), [TASK23](TASK23.md)에서 오차 시간 +1.4 %, 크기 −0.01 %로 확인).
- `enable_prefix_caching`은 지정하지 않으면 `True`로 resolve되므로 APC OFF/ON은 명시적으로 통제한다.

환경 provenance `UNKNOWN` (`PARTIAL` 해소): 환경 문서 [NPU_ENVIRONMENT.md](../environment/NPU_ENVIRONMENT.md)의 hostname은 `rebel-pcie-0123`이지만 현재 관찰 hostname은 `atom-max8`이다. 두 이름이 같은 host인지, 재설치·rename·다른 장비인지는 여전히 `UNKNOWN`이다. [TASK05](TASK05.md)의 read-only 재-inventory에서 hostname을 제외한 모든 대조 항목(visible ID 수 32, card grouping 4×8, device memory 15.7 GiB, NUMA 분할, topology distance 4/8/12, RSD group 0)이 일치했으므로 해당 문서의 hardware 기술은 현재 host에서 실무상 사용할 수 있다. 다만 값 일치는 장비 동일성의 증거가 아니므로 provenance `UNKNOWN`은 유지한다.

다음 권장 작업: **첫 Overleaf 빌드와 그림 육안 검수**. `bash paper/latex/make_package.sh` → zip → Overleaf 업로드 → pdfLaTeX 2회가 순서이며, **이 host에 TeX가 없어 소스가 한 번도 컴파일되지 않았으므로 첫 빌드가 첫 검증이다.** 그림 겹침·잘림은 자동 검사가 잡지 못하므로 육안 확인이 필요하다. 제출 순서와 잔여 항목은 [ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6에 있다 — **arXiv 업로드는 저자 계정 작업이며 이 저장소에서 수행하지 않는다.** 남은 연구 항목은 [후속 연구](#후속-연구) 절에 정리했으며 **사용자 지시 없이 착수하지 않는다.** GPU 실측은 [결정 4](#결정-4--gpua6000-교차검증-착수-시점) 개정에 따라 **조건부 이연** 상태다. 측정이 포함되는 후속 작업은 선등록 후 진행한다.

## Task Index

| Task | 상태 | 제목 | 간략 설명 |
|---|---|---|---|
| [TASK01](TASK01.md) | DONE | 연구 작업 기록 및 Agent Workflow 구축 | INDEX-first workflow와 TASK 기반 연구 이력을 도입했다. 모든 agent가 관련 과거 결정을 확인하고 TASK와 INDEX를 함께 갱신하도록 규칙을 통합했다. |
| [TASK02](TASK02.md) | SUPERSEDED | Stage 0 CA25 단일 추론 Bring-up 사전 검증 | Source isolation과 8 physical CA25 card/32 visible ID inventory를 재검증했다. 실행 가능한 local model/artifact가 없어 승인 필요한 download/compile 전에 중단했다. 이 `BLOCKED`는 [TASK06](TASK06.md)의 실제 실행으로 해소됐다. |
| [TASK03](TASK03.md) | DONE | 작업 종료 시 main commit Workflow 도입 | 각 작업의 검증된 agent-owned 변경을 local `main`에 commit하고 hash를 보고하도록 종료 규칙을 강화했다. Remote `push`는 별도 지시 대상으로 유지했다. |
| [TASK04](TASK04.md) | DONE | 연구 workflow 문서 개정 | INDEX에 "사용자 결정 대기" 절을 신설하고, 선등록·동치 판정 규칙을 집행 문서의 hard rule로 승격했으며, hostname 불일치를 INDEX 수준 `UNKNOWN`으로 올렸다. |
| [TASK05](TASK05.md) | DONE | Stage 0 후보 model 조사와 atom-max8 재-inventory | 후보 3개의 HF metadata·config·KV bytes/token·설치 source 지원 근거를 read-only로 수집해 결정 2 근거 표를 만들었다. `atom-max8` 재-inventory는 hostname을 제외한 전 항목이 환경 문서와 일치했다. |
| [TASK06](TASK06.md) | DONE | Stage 0 실행: Qwen/Qwen3-4B download·compile·CA25 단일 추론 | 선등록한 7개 PASS 조건을 전부 충족해 Stage 0를 `PASS` 판정했다. Compile 165 s / artifact 9.08 GiB, `num_devices=4`는 단일 physical card(`rbln0`–`rbln3`)에 배치됐고 memory·utilization·context로 NPU 실행을 확인했다. |
| [TASK08](TASK08.md) | DONE | compile 파라미터 공간과 KV accounting source 조사 | `eager`에서 `kvcache_num_blocks = batch_size`임을 source로 확정하고 TASK06의 KV accounting `UNKNOWN`을 대부분 해소했다. 문서화된 bucket 관측 지점이 기본 실행 경로 밖임을 확인하고 Stage 1b compile 파라미터 권고안과 사전 예측표를 만들었다. |
| [TASK09](TASK09.md) | DONE | Stage 1a: b1 artifact serving bring-up과 관측 감사 | 선등록 5개 조건을 전부 충족해 `PASS` 판정했다. `num_gpu_blocks` 2배 anomaly를 frontend 누적 구조로 해소하고 KV·큐 metric의 live 여부를 in-flight 표집으로 감사했다. b1 artifact는 동시 요청을 거부하지 않고 큐에 세운다(`running` 최대 1, `waiting` 최대 2). |
| [TASK10](TASK10.md) | DONE | Stage 1b: multi-bucket compile과 동시성 진입, decoder bucket 관측 판정 | 선등록 3개 조건을 전부 충족해 `PASS` 판정했다. `batch_size=8`에서 `running`이 8에 도달했고 TASK08의 KV accounting 예측 9개가 전부 실측과 일치했다. compile 349 s / artifact 11.50 GiB이며 크기는 decoder bucket 개수에만 비례한다. decoder bucket의 per-step 관측은 4개 수단 모두에서 불가로 판정해 결정 3을 신설했다. |
| [TASK11](TASK11.md) | DONE | prefix cache hit 경계와 KV block 의미론 확정 | hit 단위를 inner block 128 token으로 확정하고 산식 `floor((n−1)/128)×128`이 10개 조건에서 전건 일치함을 확인했다. TASK09·TASK10의 `hits = 0`은 prompt가 129 token 문턱 아래였기 때문이다. 선등록 예측 9개 중 8개 적중. APC OFF가 block 입도까지 바꾸는 confounder를 발견했다. |
| [TASK12](TASK12.md) | DONE | 결정 3 집행: decoder bucket 관측 patch 적용과 검증 | `patches/` 정책의 첫 실전 적용. 검증 관문 3개(의미론 전건 일치, 관찰자 효과, 복구)를 모두 통과해 patch를 적용 상태로 유지했다. `[BUCKET]` 로그 635줄에서 사상 1→1, 2→2, 3→4, 5→8, 8→8이 전건 일치했고 bucket padding 낭비가 정량화됐다. |
| [TASK13](TASK13.md) | DONE | decode step 비용 모델: bucket 결정적인가, actual 결정적인가 | 선등록 H(같은 bucket 내 동치)를 채널 C bootstrap에서 기각했다(동치 요구 7쌍 전부 `DIFFERENT`). 다만 비용이 분해된다: model span은 bucket 결정적(같은 bucket 내 범위 ≤ 0.03 ms), actual 의존은 engine overhead에 있고 요청당 약 0.041 ms다. bucket 효과(+4.6~17.8 %)가 actual 효과(≤ +1.2 %)를 지배한다. `[BUCKET]` 사상표 8개가 전부 채워졌다. |
| [TASK14](TASK14.md) | DONE | prefix-cache block 생존/eviction 파일럿: NPU GapTurnover 첫 실측 | 두 층에서 서로 다른 문턱이 나왔다. 층 2(outer block, FIFO, 8개)는 배경 요청 B=7에서 실제 재사용이 100 %→0 %로 끊기고, 층 1(inner block, LRU, 512개)은 16 < B ≤ 33이다. **7 ≤ B ≤ 16에서 `prefix_cache_hits_total`이 실제 재사용을 100 % 과대평가한다.** 생존을 결정하는 것은 token 총량이 아니라 요청 개수다. |
| [TASK15](TASK15.md) | DONE | B = 7 절벽 재현과 resume attribution 확정 | 절벽과 metric 거짓 양성을 새 seed·12 trial에서 **12/12 결정적으로 재현**했다. 층 2 miss 시 resume이 prefix를 실제로 재계산함을 device-side prefill 시간 13.1배와 `prefill_kv_computed` 88→2,008로 확정했다(TASK14의 `UNKNOWN` 해소). 층 2를 세는 Prometheus metric이 이미 존재함을 확인했다. 선등록 1차 채널의 산술 전제가 깨져 fallback 규칙을 적용했다. |
| [TASK16](TASK16.md) | DONE | substrate descriptor v0와 관찰 층 태깅 규칙 | `SubstrateDescriptor`(accelerator-neutral)를 신설해 모든 상수에 `Provenance`(층·출처 TASK·측정 방식)를 강제했다. RBLN CA25 인스턴스는 실측을 잔차 0.078 ms 이내로 재현하고 생존 예측이 6/6 일치한다. `TASK_GUIDE.md`에 층 태그(`silicon`/`stack`/`class`/`universal`)를 의무화하고 TASK11–15 발견 39개의 일람표를 만들었다 — 20개가 `stack` 단독이다. |
| [TASK17](TASK17.md) | DONE | agentic workload generator v0와 bucket 전이 첫 관측 | 생성 길이를 흩뜨려 `padded_batch_size` **8 → 4 → 2 → 1** 전이를 관측했다(TASK12부터 이월된 `UNKNOWN` 해소). 사상은 TASK13 표와 전건 일치. gap 관측에서 8 세션 중 **4개만** 재사용에 성공했고 성패는 세션의 행동이 아니라 도착 순서에 좌우됐다(예측 0/8은 빗나감). 동시 workload에서 counter 증분의 per-request 귀속이 무효임을 확인했다. |
| [TASK18](TASK18.md) | DONE | per-request/per-session 귀속 채널 구축과 검증 게이트 | `--enable-prompt-tokens-details`로 응답에 층 2 값이 실려 오게 해 **구성상 귀속**을 확보했다. 게이트 G1 8/8, G2 16/16, G3 정확 일치로 통과. client id가 server 로그 id의 strict prefix라 timestamp 정렬 없이 join된다. 8 세션 = 8 slot에서 turn 2 재사용은 2/8이었다. |
| [TASK19](TASK19.md) | DONE | AGENTIC vs CONVENTIONAL 짝 비교 파일럿 | 1차 측정은 불변식 P1 위반으로 `INVALID` 처리하고(원인: CPython `randrange(0,1)`의 가변 비트 소비) 짝 설계를 구성 기반으로 고쳐 재등록·재측정했다. **방향이 부하에 의존한다**: N=8에서 utilization ratio 0.872(AGENTIC 12.8 % 낮음), N=16에서 1.009(저하 없음). 대기 큐가 gap을 흡수한다. 재사용률은 AGENTIC이 오히려 높았다(3/8 vs 1/8). 사전 예측 5개 중 2개만 적중. |
| [TASK20](TASK20.md) | DONE | N/slots sweep 본 측정 | 44 조합 전부 `VALID`(`INVALID` 0). **저하 확정은 N=10·12뿐**(pooled 0.910·0.919). N=6은 3블록 전부 **반대 방향**(pooled 1.150) — gap이 batch를 padding 0인 크기로 쪼개 utilization을 올린다. N=8은 5블록 중 4블록만 저하 방향이라 선등록 기준 미달. 재사용률은 N 증가에 단조 감소해 N≥12에서 0. **TASK13 비용 모델이 다중 세션으로 전이되지 않는다**(예측/실측 0.86→0.57). |
| [TASK21](TASK21.md) | DONE | gap 분산 → 재사용 메커니즘 검증 | 총 gap 시간을 소수점까지 고정하고(P2) 분산만 조작했다. DISPERSED 11/24 vs SYNC 7/24이고 **반대 방향 블록은 0**이나 동률 1블록 때문에 선등록 기준상 `INCONCLUSIVE`다. 도착 순서 서명이 6개 arm-block 중 5개에서 확인됐고 **DISPERSED는 3/3 블록에서 가장 이른 두 도착이 성공**했다. eviction OB 열의 중간 8개가 전 조합에서 FIFO였다. |
| [TASK35](TASK35.md) | PARTIAL | compile-time 구성 이득의 최종 확증 측정 | 채널 A′(`[BUCKET]` × [TASK13](TASK13.md) decode + 계산 token × [TASK22](TASK22.md) prefill)를 **측정 전에 고정**하고 신규 seed·3 arm·27조합으로 다시 쟀다. **N=8 확증 `PASS`** — 선등록 0.9101/0.8971 대 실측 0.9175/0.9028(오차 +0.0074/+0.0058), **X = +8.25 %(batch-only) / +9.72 %(tuned)**, 채널 B와 0.0008–0.0035 합치. **N=6은 채널 차 0.021–0.024로 보류**(원인: A′가 빠뜨리는 고정 오버헤드 1.2–1.7 s가 N=6에서 전체의 6.1 %). **부속 절제 `PASS` 2/2** — `③<②<1`이고 ③−②가 예측 +1.45/+1.30 %p 대 실측 +1.34/+1.47 %p로 맞아 **"지배 인자는 `batch_size`"가 device에서 확인**됐다. 두 arm의 prefill비가 실측에서도 동일(0.898/0.898, 0.678/0.678). compile 5번째 점 −0.7 %/+0.6 %, 사상표 4/4. 27/27 `VALID`. |
| [TASK36](TASK36.md) | DONE | N=6 확증 재측정: 교정된 채널 요건으로 보류 해소 | 채널 허용차를 `τ(N) = max(0.02, r_BASE/B_BASE)`로 교정해 **측정 전에** 선등록하고(상한 유도 포함, [TASK35](TASK35.md) 자료 소급 검증 완료), 전부 신규 seed `20261100`으로 N=6 × 3 arm × 3블록을 다시 쟀다. **확증 `PASS` 2/2** — 선등록 0.9874/0.9713 대 실측 0.9941/0.9789(오차 +0.0067/+0.0076). **채널 차 0.0001/0.0063으로 원 기준 0.02까지 통과해 완화에 기대지 않았다.** **X = +0.59 %(batch-only) / +2.11 %(tuned)**, 채널 B로도 +0.60/+2.74 %. **적용 범위가 N ∈ {6, 8}로 확장되되 X는 +2.1 %~+10.1 % 구간**이다. 부속 절제 `PASS`(③<②<1, ③−② 실측 +1.52 %p 대 예측 +1.61 %p)이나 **두 항의 상대 크기가 뒤집혀** `batch_size` 지배가 **조건부**임이 드러났다 — 이 seed의 `BASE`는 이미 17/18을 재사용한다. 시뮬레이터가 그 역전을 미리 예측했다. 재compile 0회, 9/9 `VALID`. |
| [TASK37](TASK37.md) | DONE | 논문 조립: 서사·주장 매핑·그림·related work·초록 | 측정 없이 [paper/](../../paper/) 산출물 7종을 만들었다. 3막 서사([OUTLINE.md](../../paper/OUTLINE.md)), 주장 41개의 근거 TASK·층 태그·그림 매핑과 **`stack`→`class` 오독 전수 점검(위험 10건 식별·처리 지정)** ([CLAIMS.md](../../paper/CLAIMS.md)), **그림 8종 SVG**와 출처 경로([figures/](../../paper/figures/)), 문제 분류학 기반 related work([RELATED.md](../../paper/RELATED.md)), 한계 9항, 국·영문 초록([ABSTRACT.md](../../paper/ABSTRACT.md)), 투고 타깃 3개([VENUES.md](../../paper/VENUES.md)). **arXiv:2511.02230의 이름이 v4에서 CacheTTL로 바뀌었다가 v6에서 다시 Continuum으로 돌아와 명칭 충돌은 여전히 살아 있다.** 2026 인접 결과 7건을 재확인했고 그중 ConServe만이 같은 방향의 독립 증거다. 명칭 후보 5개는 [결정 5](#결정-5--시스템-명칭-충돌)에 기입, **판정은 사용자**. |
| [TASK38](TASK38.md) | DONE | 논문 자료 정정과 공개 준비: 서지 3건·그림 검수·명칭 확정·arXiv 점검표 | [TASK37](TASK37.md)이 `UNKNOWN`/`PARTIAL`로 남긴 서지 2건을 특정·검증했다. `LENS` = arXiv:2606.18042(NPU 지연 예측, bucketing 비선형성) — §1 최근접 선행으로 승격. `KV-RM` = arXiv:2605.09735 — **[TASK37](TASK37.md)의 `KV-RM ≈ CacheScout` 잠정 동일시는 오류였고**, 게다가 **v2가 2026-06-30에 저자에 의해 철회**돼 수치·성능 주장은 인용하지 않고 문제 설정만 인용한다. CacheScout를 GPU agentic KV 관리 계열로 옮기며 그 계열의 공통 전제(회수 정책 조정 가능)가 이 substrate의 FIFO 하드코딩에서 성립하지 않음을 대비로 세웠다. 그림 검수 자동화 — 데이터 상수 138개를 원 TASK 표에서 독립 파싱해 대조, 불일치 0. 시스템 명칭 `Escapement` 반영, arXiv 공개 점검표 작성. |
| [TASK39](TASK39.md) | DONE | arXiv 초록 압축과 제출 준비 마감: 그림 PDF 백엔드 자체 구현 | 영문 초록을 3,029 → 1,876자로 압축해 arXiv 하드 캡(1,920) 안에 넣고 압축본·전체판·국문을 용도 표기와 함께 병존시켰다. SVG→PDF는 **설치 0건으로 해소** — `cairosvg`는 `libcairo` 부재로 apt가 필요하고 `svglib`는 비-Latin을 잃으므로, `svgplot.py`를 프리미티브 모델로 리팩터링해 PDF 백엔드를 직접 넣었다(DejaVu 임베딩, 폭은 기존 Pillow에서). **이 host에 CJK 폰트가 하나도 없어** 논문용 그림은 번역표(누락 시 생성 중단)로 영문 라벨을 쓴다. 산출물 3종: 국문 SVG(검토)/영문 SVG/영문 PDF(LaTeX). PDF 구조 8/8, 변환 손실 0, 넘침 15 → 0. |
| [TASK40](TASK40.md) | DONE | `batch_size` 포화 곡선: "클수록 좋다" 반론의 실측 검증 | 눈금을 `(1,4,6,8,10,B)`로 고정하고 최상위만 바꿔 B ∈ {8,16,24,32} × N ∈ {6,8,10} × 3블록 36조합을 쟀다. **통제된 인접쌍 2/2 `포화`**(B16→B24 중앙 ratio 0.9999 CI 폭 0.0192, B24→B32 1.0002 CI 폭 0.0016). 선등록 예측 대비 **9/9 통과**이고 N ∈ {6,8} 6칸은 오차 0.0003–0.0026 — **무보정 sim이 "아무 일도 일어나지 않는다"를 미리 맞혔다.** 기전도 닫혔다: 생존율이 B=16에서 포화하고 **최상위 눈금이 0.0 % 선택**된다. B32 **load 성공**, device 메모리 `2.1 + 0.28125 × B` GiB/device로 KV 한계 **B ≈ 46**(외삽). compile 비용 모형 6·7번째 점(+3.0 %/+0.4 %). 36/36 `VALID`. 경쟁 문헌 재조사 병합. lifecycle 43회(4회는 script 버그). |
| [TASK41](TASK41.md) | DONE | TASK40의 논문 반영, 본문 초고 완결, LaTeX 이식 패키지 | 그림 ⑨를 **2패널**(device time / 생존율)로 개편해 "포화점 = 생존율 100 % 도달점"과 KV 한계 외삽선을 배치로 보이게 했다. CLAIMS에 포화 법칙(`class`)·위치(`stack`)·최적 B·음성 예측 4항목 추가. **[KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 신설** — 재발 함정 5종을 발생 TASK·대가와 함께 모으고 [AGENTS.md](../../AGENTS.md)에서 참조. **본문 초고 10절 완결** — CLAIMS 46/46 인용, 미존재 id 0, 미인용 주장 0. **LaTeX 이식 패키지**(IEEEtran, 이송기가 CLAIMS 주석을 원고까지 옮긴다). **TeX 미설치로 컴파일 미검증.** |
| [TASK42](TASK42.md) | DONE | Advisor 첨삭 반영, 교정 1차, 저자 확정과 제출 패키지 완성 | §1 substrate 클래스 선언(Inferentia·Gaudi·cudagraph 격자를 **벤더 문서로 1차 확인**)과 stack 버전 병기, §5.2 제목의 결론 선취 제거. **`[NEEDS-EVIDENCE]` 3건 집행** — 부록 C(patch 정책 7항목) 신설로 부록 A–D를 함께 쓰고(B는 **선등록 commit 10건 표**), §4.3.1 validated envelope("확증은 동시성 8 이하"), §4.3.2 known error structure + **CLAIMS 1.18**(계통 오차, scope 3항). figure 캡션 9종·table 캡션 2종을 **주장 1문장 + 조건 병기**로 작성, `\cite` 18개. **저자 3인 확정 반영**, 리벨리온 장비 감사와 AI 사용 고지 활성화, **CC BY 4.0** 확정, 제출 순서 5단계. **컴파일 미검증·제출 없음.** |
| [TASK43](TASK43.md) | DONE | repository 개명 후 정합화 | GitHub 저장소가 `continuum-npu` → **`escapement`** 로 개명돼 `origin`을 신 URL로 갱신하고 redirect 의존을 없앴다. **구 URL 치환 대상은 0건** — 현행 문서에 GitHub URL이 하드코딩된 곳이 없었고, 유일한 참조는 [TASK07](TASK07.md)의 과거 기록이라 비대상이다. `continuum-npu` 문자열의 나머지도 전부 비대상이며, 특히 **patch 본문의 주석은 고치면 적용 후 SHA256이 달라져 모든 run의 provenance가 소급해 깨진다.** 명칭 통일은 현행 문서 표제 3건으로 한정하고 본문 서술은 손대지 않았다. README 머리에 개명 사실과 **Continuum(arXiv:2511.02230)과 무관한 별개 연구**임을 명시했다. |
| [TASK44](TASK44.md) | DONE | 원고 교정 배치 1: 빌드 수정과 외부 검토 반영 | Advisor가 로컬 컴파일에서 검증한 조판 수정 4건(표 2종 열 폭 + `\footnotesize`, 긴 `\texttt`에 `\allowbreak`, 부록 B commit 칸 축약)을 **손으로 고치지 않고 이송기 기능으로** 넣었다 — `TABLECOLS`·`TABLENOTE`·위첨자 표식과 24자 초과 code span 자동 분절 규칙이라 전 문서에 일관 적용된다. 축약된 부연은 **표 각주로 복원해 축약 전보다 구체적**이 됐다. 외부 검토 수용분 **18건** 반영, **3건 기각** — OCR 잔여 문자열과 하이픈 누락은 소스에 실재하지 않는 **PDF 추출기의 손실**이라 고치면 실재하는 조판이 깨진다. 초록이 1,960자로 상한을 넘겼다가 조건 병기를 건드리지 않고 **1,887자**로 복귀. 서지 3건 1차 출처 완결. **INDEX 표에서 누락돼 있던 TASK38–44 행 7개를 함께 복구했다.** |
| [TASK34](TASK34.md) | SUPERSEDED | 워크로드 통계 기반 compile 구성의 실기기 검증 | 구성 공간 2,077개를 sim으로 탐색해 `(1,4,6,8,10,16)`·`batch_size=16`을 고르고 재compile 후 18조합 짝 비교했다. **X = device time 7.4 % 회수**(확증 구간 N ∈ {6,8}, 모형 무의존 채널), N=10에서 12.6 %. 회수의 지배 인자는 bucket 격자가 아니라 **`batch_size`, 곧 KV pool 크기**다(sim 귀속 +7.21 % 대 +0.71 %). 실측 기전도 예측대로 prefill이다(prefill비 0.71–0.88, decode비 0.94–0.99). **다만 선등록한 채널 A가 decode만 세어 이 개입의 주효과를 볼 수 없었고, 채널 일치 요건에 걸려 확증 판정을 보류했다.** compile 비용은 [TASK10](TASK10.md) 모형과 +1.7 % / +0.7 %로 맞았고 사상표 5/5 일치. 구성 선택은 gap 분포에 둔감하고 **부하 상한에만 반응**한다. |
| [TASK33](TASK33.md) | DONE | 현실 headroom의 정보 분해 | oracle 지식을 5수준(전지 / 반환 시각 / 생성 길이 / 둘 다 / **전지·독립**)으로 제한해 각 축의 도달 이득을 계산했다. **조율의 몫 `(a)−(e)`가 headroom의 중앙 60 %(49–73 %)** — 전지적 지식을 줘도 세션별로 따로 결정하면 잃는 부분이며 **per-session runtime 정책은 원리적으로 닿을 수 없다.** 남은 40 %도 실제 채널로는 안 닿는다(`(b)(c)(d)` 최대 +1.16 %, `(e)` 0.54–4.54 %). 사전 정의 분기에 따라 **compile-time이 유일 회수 경로**(9칸 중 1칸만 절반 초과). 정책 파라미터를 채널에 유리하게 전수 튜닝하고도 그렇다 — 탐색 seed 4.32 %가 평가 seed −0.14 %가 됐다. |
| [TASK32](TASK32.md) | DONE | CacheTTL 예측기 차용과 정확도 실측 | arXiv:2511.02230 §4.2의 online 예측기(전역·도구별 mean/std + empirical Bernstein 상한, 3단 fallback)를 재현해 200,000 호출 열에 돌렸다. **최종 Gate `FAIL`** — 수렴 후 오차 std 10.19 s로 σ\*(1.06–1.82 s)를 **5.6–9.7배 초과**한다. **오차가 관측 수와 함께 줄지 않는다**(표본 10 → 100,000에서 std 8.4 → 10.5 s) — 줄일 수 없는 분산이며 더 나은 추정자로 풀리지 않는다. 논문의 `B(δ)`와 점추정 `μ̂`가 실질적으로 같다(10.196 대 10.185) — **평균을 아무리 잘 추정해도 개별 draw는 못 맞힌다.** 도구별로는 `Read` 0.46 s·`apply_patch` 1.50 s가 문턱 안이나 `Bash`·`write_stdin`(호출의 31 %)이 16–18 s다. |
| [TASK31](TASK31.md) | DONE | 현실 tool latency 워크로드 전환과 headroom 재검증 | legacy TraceLab 산출물(665k rows / 8,058 sessions, read-only)에서 도구 population을 재구성해 `uniform:1:5` 합성 gap을 교체했다(중앙값 22배 작고 표준편차 7배 큼). **연속성 `PASS` 3/3** — 선등록 예측 대비 utilization 오차 −0.019~+0.000, 재사용률 ±5.6 %p. **시뮬레이터가 워크로드 전환을 넘어 전이된다.** **headroom Gate `PASS` 3/3**(ε=2 s에서 5.0–6.9 %). 그러나 **[TASK30](TASK30.md)의 예지 가치가 소멸한다** — 반환 시각만 아는 정책이 −1.20 %~+0.99 %이고 σ\*가 정의되지 않는다. 동료 도착 기회는 두 워크로드가 비슷하므로 기회 부족이 아니다. **합성 gap은 재사용 압박을 과대평가하고 있었다**(현실 재사용률이 모든 N에서 높다). |
| [TASK30](TASK30.md) | DONE | 예지 가치 곡선: 반환 시각 정보의 값과 정확도 문턱 | oracle의 지식을 3수준(전지 / 반환 시각만 / 노이즈 σ)으로 제한해 각각의 도달 이득을 계산했다. **Gate `PASS`** — ε=5 s에서 반환 시각만으로 omniscient의 **86–88 %**(N=6·8) 회수(절감 16.95·20.00 %). **ε이 정보보다 먼저 구속한다**: ε=1 s에서는 회수율 6.7 %뿐이다. 정확도 문턱 **σ\* = 0.74–1.27 × gap std = 1.06–1.82 s** — 완벽한 예측이 필요 없고, **예산과 정확도는 교환 가능**하다. oracle hold는 어느 단일 관측량으로도 설명되지 않는다(\|r\| ≤ 0.18). N ≥ 10에서는 반환 시각 정보의 값이 거의 없다. |
| [TASK29](TASK29.md) | DONE | 기전 절제 분석과 결정 5 기록 | 기전 3개를 시뮬레이터에서 절제해 귀속을 계산했다(**측정 아님, 모형 진술**). ① eviction FIFO·시퀀스 → LRU·index: 문턱의 *성격*이 바뀐다 — 측정은 배경 크기와 무관하게 B=7, 절제는 token 총량에 걸려 61/31/16. ② 격자 → 연속: N=6 1.1523 → **1.0000**으로 완전 소멸. **② ' 격자 → GPU cudagraph `[1,2,4,8,16]`: 소멸하지 않고 소수 넷째 자리까지 동일** — 사전 기대를 뒤집는다. ③ prefill 배타 → chunked: 정지 0이 되지만 device time이 3–10 % **증가** — 배타 실행이 decoder를 강제 동기화해 batch를 넓히고 있었다. GPU 대응 근거는 전부 **설치된 vLLM source**에서 확인했다. |
| [TASK28](TASK28.md) | DONE | causal 반환 정책의 실기기 검증 | 선등록(`980f0c7`) 17초 뒤 측정을 시작해 18조합을 쟀다. **확증 구간(N ∈ {6,8}) `PASS` 2/2** — sim 예측 1.0554·1.0332 대 실측 1.0732·1.0541(오차 +0.018·+0.021, 허용 ±0.03), 블록별 순서까지 재현. device time을 **모형 의존·무의존 두 채널**로 재 차이 0.010–0.011로 일치했다. **X(oracle headroom 회수율) = −105 %(N=6), −70 %(N=8)** — 잘못된 정책은 아무것도 안 하는 것보다 headroom만큼 더 나쁠 수 있다. sim이 보류 손해를 **계통적으로 과소평가**한다(블록 6/6 동방향). 18/18 `VALID`. |
| [TASK27](TASK27.md) | DONE | causal 반환 스케줄링 정책의 시뮬레이터 평가 | 정책 4종(`IMMEDIATE`/`QUANTIZE(τ)`/`TOPUP`/`FREESLOT`)을 시뮬레이터와 실측 client가 **같은 코드**로 쓰도록 구현하고 평가했다. **어느 것도 device time을 평균적으로 개선하지 못한다** — 6 seed × 24칸에서 `FREESLOT`이 −0.44 %로 가장 중립이고 `QUANTIZE`는 ε이 클수록 −10 %까지 나빠진다. [TASK26](TASK26.md) plan만 보면 `FREESLOT`이 34 % 회수로 보였으나 **신규 seed에서 부호가 뒤집혀** 선택 편향이었음이 드러났다. 기전: oracle은 세션의 47 %를 놓아 두고 소수만 붙드는 **선택적** 보류인데 causal 정책은 83 %를 조금씩 붙드는 **무차별** 보류다. 정책 축에서도 utilization은 비용과 반대로 간다. |
| [TASK26](TASK26.md) | DONE | 반환 시점 재배치의 offline oracle bound | 검증된 시뮬레이터 위에서 hold 벡터를 탐색했다. **policy headroom이 있다** — device time이 ε=0.5 s에 1.2–4.4 %, ε=5 s에 9.7–27.2 % 줄어든다(국소 탐색이므로 하한). 이득의 원천은 사전에 지목한 셋(padding·재사용·정지 군집화)이 아니라 **동시성 집중**이며, N=6에서 96 %, N=12에서는 재계산 절감이 57 %다. **utilization을 목적함수로 쓰면 device time이 11–37 % 나빠진다.** 실측 히스토그램으로 다시 읽으면 AGENTIC은 11/11에서 device time을 더 쓰는데 utilization ratio는 5/11에서 반대로 말한다. |
| [TASK25](TASK25.md) | DONE | 선등록 예측에 의한 시뮬레이터 out-of-sample 검증 | 측정 전에 commit한 예측이 신규 seed 18조합의 실측과 맞았다 — pooled ratio 오차 N=3 −0.0022, N=4 +0.0005, N=7 −0.0040으로 **허용치 ±0.05의 12분의 1**. 게이트 **PASS 3/3**. 6블록 합산 판정도 선등록 예상과 3/3 일치했고 **[TASK23](TASK23.md)의 `INCONCLUSIVE` 중 N=3이 "역전"으로 확정**됐다(pooled 1.0994, 5/6). N=4·N=7은 6블록으로도 미결. utilization 절대오차 평균 0.0016, 층 2 재사용 92.9 %. 단 **개수는 맞고 세션 귀속은 어긋나는 사례**가 있다. 18/18 `VALID`, 실패 0. |
| [TASK24](TASK24.md) | DONE | step 수준 시뮬레이터 구축과 in-sample 보정 | descriptor만 입력받는 결정적 discrete-event 시뮬레이터(`src/continuum/sim/`)를 세워 기존 80조합을 **보정 파라미터 없이** 재현했다 — utilization 평균절대오차 0.0066, pooled ratio 11개 방향 11/11(최대 오차 0.0202), 층 2 재사용 hit/miss 93.0 %. [TASK23](TASK23.md)의 N=6 개입(1.1504 → 0.9717)도 재현(1.1523 → 0.9687). **N=4·N=5 이상치가 감쇠 경로로 설명된다.** 신규 발견 2건: 층 2는 prefill 계산분만 캐시(271/271), 즉시 복귀 세션은 자기 캐시를 자기가 축출하지 않음. 틀린 pool 모형 3개를 로그 사건 열로 반증했다. |
| [TASK23](TASK23.md) | DONE | bucket 격자 정렬 법칙: 관측 완성과 재compile 개입 검증 | 재compile로 bucket 6을 추가하는 **개입**을 걸어 N=6 역전이 소멸함을 확인했다(pooled 1.1504 → 0.9717, 역전 방향 블록 3/3 → 0/3). 대조 N=8은 저하 방향 유지(0.9253 → 0.9508). 히스토그램이 기전을 직접 보여준다 — CONVENTIONAL은 decode step의 42.2 %를 `6→8`(padding 2)로 보냈고 AGENTIC은 9.0 %뿐이라 개입 이득이 CONVENTIONAL에 몰렸다(1.241× vs 1.048×). 2a에서 N=5 `역전`(1.1336), N=8 8블록 `저하 존재`(0.9205)를 확정했고 N=3·N=7은 `INCONCLUSIVE`. 사상표 재검증 5→6·6→6·7→8 전건 일치. 실행 중인 script를 편집해 server 누수·연쇄 실패 1건이 났고 1칸을 재실행했다. |
| [TASK22](TASK22.md) | DONE | prefill 배타 실행의 직접 검증과 비용 모델 v2 | prefill이 실행 중인 전 세션의 decode를 **정확히 그 길이만큼 정지**시킴을 시간 단위로 관측했다(4 bystander 스파이크가 1 ms 이내로 겹침, 스파이크/prefill 1.01–1.14). 정지 시간 모형 `ceil(n/128)×(0.0212+6.4e-7n)`이 최대 잔차 2.4 ms로 맞는다. **TASK20 비용 모델 편향이 이 항으로 87–120 % 설명된다**(v1 0.57–0.86 → v2 0.97–1.04, N 의존 소멸). 대조 구간에도 startup prefill 직렬화가 나타나 판정 1은 선등록대로 `PARTIAL`. |
| [TASK07](TASK07.md) | DONE | 작업 종료 시 GitHub push 확인 Workflow 도입 | 모든 작업 종료 시 `origin/main` push 여부를 반드시 사용자에게 묻고, 현재 질문에 대한 명시적 승인 후에만 push하도록 규칙을 추가했다. |

## 사용자 결정 대기

이 절은 agent가 임의로 진행할 수 없고 사용자 판정이 필요한 결정의 단일 출처다. **현재 미해결 결정 항목은 없다.** [결정 5](#결정-5--시스템-명칭-충돌)가 2026-08-25에 해소됐다. 다만 **논문 공개 전에 사용자가 확인해야 하는 항목**이 [paper/ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §6에 별도로 있다 — 저자 표기, 라이선스, AI 사용 고지(초안은 §7), **그림 육안 검수**. SVG → PDF는 [TASK39](TASK39.md)에서 설치 없이 해소됐다. 각 항목은 결정 ID, 질문, 선택지, 선택지별 근거·비용·미지수, 권고안, 관련 TASK를 갖는다. 권고안은 제안일 뿐이며 판정은 사용자가 한다. 결정이 내려지면 항목을 "해소됨"으로 표시하고 근거 TASK를 링크한다.

### 결정 5 — 시스템 명칭 충돌

- 상태: **`해소됨` — 시스템 명칭은 `Escapement`이고 repo도 `escapement`로 개명됐다** (명칭 판정·repo 개명 모두 2026-08-25). 방침(개명한다)은 2026-08-22에, 이름은 2026-08-25에 확정됐다. [TASK38](TASK38.md)에서 [paper/ABSTRACT.md](../../paper/ABSTRACT.md)·[OUTLINE.md](../../paper/OUTLINE.md)·[CLAIMS.md](../../paper/CLAIMS.md)에 반영했다. **로컬 디렉터리 경로와 `src/continuum/` package 이름은 재현 정보 보존을 위해 그대로 둔다.**
- 사유: Berkeley의 동명 시스템 **Continuum**(arXiv:2511.02230)이 존재한다. 이름이 겹친 채로 투고하면 선행 시스템과 혼동되고, 검색·인용에서 이 연구가 그쪽에 묻힌다
- **충돌 재확인 ([TASK37](TASK37.md), 2026-08-24)**: 그 논문의 시스템 이름은 v1–v3 `Continuum` → **v4 `CacheTTL`** → v5·**v6(현재, 2026-05-25) `Continuum`** 으로 되돌아왔다. ICLR 2026 *Lifelong Agents* workshop 등재 제목도 `Continuum`이다. **따라서 충돌은 해소되지 않았고 개명 방침은 유효하다.**
- 적용 범위: **논문 본문·시스템 이름·figure 라벨.** 저장소 경로(`/home/rebel/continuum-npu`), Python package 이름(`src/continuum/`), 기존 TASK 문서의 서술은 **그대로 둔다** — 지금 개명하면 [TASK01](TASK01.md) 이래의 artifact path와 재현 정보가 전부 어긋난다
- 확정 이름의 근거: **escapement(탈진기)** 는 시계에서 **연속적인 구동력을 이산적인 tick으로 바꾸는 기구**다. 이 연구의 중심이 연속적인 반환 도착 과정과 이산적인 compiled batch 격자의 정렬이므로 은유가 기전과 직접 맞고, 충돌 검색에서 LLM serving·ML systems 어디에도 동명 시스템이 없었다
- 후속: 논문 제목 제안은 `Escapement: Compile-Time Coordination for Agentic LLM Serving on NPUs` ([ARXIV_CHECKLIST.md](../../paper/ARXIV_CHECKLIST.md) §4). figure 라벨에는 아직 이름이 들어가지 않았고 본문 집필 때 반영한다
- **repo 개명 실행 (2026-08-25, [TASK43](TASK43.md))**: GitHub 저장소를 `dongkyeomjang/continuum-npu` → **`dongkyeomjang/escapement`** 로 개명하고 local `origin`을 신 URL로 갱신했다. GitHub이 구 URL을 redirect하지만 redirect 의존을 없앴다. [README](../../README.md) 머리에 개명 사실과 **Continuum(arXiv:2511.02230)과 무관한 별개 연구**임을 명시해, 검색으로 유입되는 독자가 두 시스템을 혼동하지 않게 했다
- **바꾸지 않는 것 — 세 가지와 각각의 이유**:
  - **로컬 디렉터리 경로 `/home/rebel/continuum-npu`** — 40여 개 TASK 문서의 재현 command와 artifact 경로가 이 이름에 걸려 있다. 바꾸면 과거 측정의 재현 정보가 전부 어긋난다
  - **Python package 이름 `src/continuum/`** — import 경로가 바뀌면 TASK 재현 command 수십 건이 깨진다. **패키지명은 역사적 명칭으로 유지한다**
  - **`patches/vllm_rbln-0.11.1/decoder_bucket_observe.patch`의 주석 문자열** — patch 본문이 바뀌면 적용 후 SHA256(`70942d16…`)이 달라진다. 그 hash는 **모든 측정 run의 provenance에 기록돼 있으므로**, 문자열 하나를 고치면 과거 run 전체의 substrate 검증이 깨진다
- 과거 TASK 기록의 서술과 경로는 **당시 사실 그대로 둔다.** 표제(README·INDEX·TASK_GUIDE)만 신 명칭으로 통일했다

**후보와 충돌 검색 결과** (검색 시각 2026-08-24. `Continuum` 계열은 배제했다. **채택: 1번**)

| # | 후보 | 이름의 근거 | 충돌 검색 결과 | 위험 |
|---|---|---|---|---|
| **1 ✅ 채택** | **Escapement** | 시계의 탈진기 — **연속적인 도착 과정을 이산 tick으로 바꾸는 기구**다. 이 연구의 중심이 반환 도착 과정과 이산 batch 격자의 정렬이므로 은유가 기전과 정확히 맞는다 | LLM serving·ML systems·데이터 인프라 어디에서도 동명 시스템을 찾지 못했다 | **낮음** |
| 2 | **Formwork** | 거푸집 — **붓기 전에 형태를 정한다.** compile 시점에 조율을 굳힌다는 처방의 은유 | ML/LLM 분야 충돌 없음. 다만 인접 SW에 동명 제품이 있다(의료기기 eQMS `Formwork`, 건설 formwork 설계 SW 다수) | 중간 |
| 3 | **Slipform** | 미끄럼 거푸집 — 위와 같은 은유이고 이름이 더 희소하다 | 충돌을 찾지 못했다 | **낮음** |
| 4 | **Quench** | 담금질 — **구조를 한순간에 굳힌다.** compile-time 고정의 은유 | LLM serving 충돌 없음. 다만 일반 영단어라 검색 변별력이 낮고, ML에서 annealing 계열 용어와 혼동될 수 있다 | 중간 |
| 5 | ~~**Girder**~~ | 거더 — 하중을 한 곳에서 받는 구조재 | **충돌 확인** — Kitware의 데이터 관리 플랫폼 `Girder`(github.com/girder/girder, PyPI `girder`)가 널리 쓰인다 | **높음 · 비권고** |

**검색에서 배제한 이름과 이유**: `Trellis`(Microsoft TRELLIS 3D 생성 모델, Trellis Data, Trellis AI(YC), interlocklabs/trellis LLM DAG — 충돌 다수), `Kiln`(Kiln AI(kiln.tech, github.com/Kiln-AI/Kiln) LLM 툴링, 그리고 `gahingwoo/kiln`은 **NPU에서 LLM을 돌리는 프로젝트**라 이중으로 위험), `Cadence`(Cadence Design Systems), `Bedrock`(Amazon Bedrock), `Lattice`(과포화), `Anneal`(ML 용어와 충돌).

**권고: 1. Escapement.** 충돌이 없고, 이름이 기전을 직접 가리키며(연속 도착 → 이산 격자), 검색에서 이 연구가 유일하게 잡힌다. 다만 발음·철자가 길다는 단점이 있으며 그 점이 걸리면 **3. Slipform**이 같은 위험도의 짧은 대안이다.

권고는 제안일 뿐이며 판정은 사용자가 한다.

### 결정 4 — GPU(A6000) 교차검증 착수 시점

- 상태: `해소됨` — **(b) offline oracle bound 완료 후 착수** (사용자 판정, 2026-08-21)
- **개정 (2026-08-22, [TASK29](TASK29.md)): GPU 실측은 취소가 아니라 조건부 이연이다.** 착수 조건([TASK26](TASK26.md) 완료)은 충족됐으나 그 뒤에 두 가지가 바뀌었다. (1) [TASK25](TASK25.md)·[TASK28](TASK28.md)에서 **검증된 시뮬레이터를 확보**해 반사실 계산이 가능해졌고, (2) GPU 측 대응 사실(LRU·block 단위 회수, chunked prefill 기본, cudagraph capture size 격자)이 **설치된 vLLM source에서 직접 확립**됐다([TASK29](TASK29.md) 인용 목록). 따라서 **본 학회 리뷰가 요구할 때 최소 범위(생존 곡선 1실험)로 재개**한다
- **재개 시 범위가 왜 생존 곡선 1건인가**: [TASK29](TASK29.md) 절제에서 축 ②(격자)는 source 사실로 대부분 닫히고 축 ③(prefill)은 부호 방향이 분명한 반면, **축 ①의 문턱 위치만 실측 없이 값을 말할 수 없다**
- **[TASK29](TASK29.md)가 비교축 ②의 기대를 뒤집었다**: `max_num_seqs = 8`에서 GPU의 cudagraph 격자 `[1,2,4,8,16]`은 유효 구간이 NPU 격자와 **동일**하므로 격자 정렬 법칙이 **소멸하지 않는다**. GPU 실험을 한다면 재야 할 축은 accelerator가 아니라 **`max_num_seqs`** 다
- 질문: 보편성 실증을 위한 GPU 교차검증(read-only 감사 → GPU-Stage 0 → 비교 실험)을 언제 시작하는가?
- 선택지와 판정 근거

| 선택지 | 판정 |
|---|---|
| (a) 즉시 병렬 착수 | Advisor 권고안이었으나 **기각** |
| **(b) oracle bound 이후** | **채택.** NPU 측 비교축(재사용 절벽·격자 정렬 법칙·prefill 직렬화)이 완성된 상태에서 GPU를 **검증 전용으로 압축 진행**한다 |
| (c) 포기하고 시뮬레이터 감도 분석으로 대체 | 기각 |

- 후속: **개정 전 조항** — "`TASK26` 완료 보고 시 Advisor가 GPU read-only 감사 지시문을 갱신해 발행한다". 개정 후에는 **본 학회 리뷰가 GPU 근거를 요구할 때** Advisor가 최소 범위 지시문을 발행한다. **어느 경우든 지시문 발행 전까지 GPU 서버 관련 작업을 시작하지 않는다.**
- 비교축 예정 (참고, hypothesis이며 판정이 아니다)

| # | 축 | NPU 측 기준선 | GPU에서 볼 것 |
|---|---|---|---|
| ① | 생존 함수의 **형태** | FIFO outer-slot 절벽 ([TASK14](TASK14.md), [TASK15](TASK15.md)) | **문턱이 요청 개수가 아니라 token 총량의 함수가 되는가.** [TASK29](TASK29.md) 계산은 그렇다고 말하며, **세 축 중 실측 없이 값을 말할 수 없는 유일한 축**이다 |
| ② | 격자 정렬 법칙 | bucket 격자 ([TASK23](TASK23.md)) | ~~cudagraph capture size 축에서 재현되는가~~ → **[TASK29](TASK29.md) 계산: `max_num_seqs`가 같으면 재현된다.** 재야 할 축은 accelerator가 아니라 `max_num_seqs` |
| ③ | prefill 직렬화 세금 | 배타 실행 ([TASK22](TASK22.md)) | chunked prefill에서 정지가 사라지는가. **[TASK29](TASK29.md) 계산: 정지는 0이 되지만 device time은 3–10 % 늘어난다** — 배타 실행의 일부는 batching 보조금이었다 |

### 결정 3 — decoder bucket 관측용 hash-guarded observation-only patch 승인

- 상태: `해소됨` — **승인 (2026-08-19). 집행 완료: [TASK12](TASK12.md)**
- 집행 결과: patch를 작성·적용하고 검증 관문 3개를 모두 통과해 **적용 상태로 유지**한다. 정책 문서는 [patches/vllm_rbln-0.11.1/README.md](../../patches/vllm_rbln-0.11.1/README.md)다.
- 질문: 기본 실행 경로의 per-step `(실제 요청 수, 선택된 decoder bucket)`을 관측하기 위해, `patches/` 정책을 따르는 hash-guarded **observation-only** patch를 승인할 것인가?
- 관련 TASK: [TASK08](TASK08.md)(source 근거), [TASK10](TASK10.md)(실행 수준 확인)
- 근거: [TASK10](TASK10.md) "핵심 산출". 선등록에서 한정한 4개 수단을 모두 검색했으나 노출 경로가 없었다. Patch는 작성하지도 적용하지도 않았다.

**왜 필요한가**

Track A(decoder bucket characterization)는 "요청 수가 N일 때 어느 bucket이 선택되고 그 padding 낭비가 얼마인가"를 대상으로 한다. 이 값이 관측되지 않으면 Track A는 성립하지 않는다.

**관측 불가의 근거 (4개 수단 전부 검색)**

| 수단 | 결과 |
|---|---|
| `VLLM_LOGGING_LEVEL=DEBUG` server 로그 911줄 | 기동 시점의 정적 목록(`Bucket sizes for RBLN sampler: (1, 2, 4, 8)`)과 warm-up dummy compile 로그만 존재. 서비스 구간에는 request 단위 block 할당·해제 로그만 있고 step 단위 batch 정보 없음 |
| `/metrics` 122개 항목 | `bucket` 매칭은 전부 Prometheus histogram bucket. batch·decoder 관련 항목 없음 |
| `VLLM_RBLN_METRICS=1` | `PREFILL` / `DECODE` / `PADDED DECODE` 절의 latency 통계만. `PADDED DECODE`는 `StepReport.padded_decode`를 `True`로 설정하는 caller가 package 전체에 없어 항상 비어 있음 |
| 기타 read-only 경로 | 기동 시 config dump와 `rbln_config.json`은 정적 bucket 목록 |

**Patch 대상 (제안, 미작성)**

| 항목 | 내용 |
|---|---|
| 대상 package | `vllm-rbln 0.11.1` (site-packages) |
| 대상 파일 | `vllm_rbln/model_executor/models/optimum/model_base.py` |
| 대상 함수 | `RBLNOptimumDecoderMixin.preprocess_for_decoder` (약 361–406줄) |
| 삽입 위치 | `select_bucket_size` 호출 직후, `kwargs` 구성 직전 |
| 변경 내용 | `request_nums`와 `padded_batch_size`를 `logger.debug`로 1줄 emit |
| 예상 diff 규모 | **추가 3–5줄, 기존 줄 수정 0** |
| 대안 지점 | `optimum/decoder_only.py:58–65` `RBLNOptimumForCausalLM.forward` — `request_nums`와 `padded_batch_size`가 모두 지역 변수로 존재. 이쪽도 동일 규모 |

**observation-only인 근거**

- 제어 흐름을 바꾸지 않는다. `padded_batch_size` 계산은 그대로 두고 읽기만 한다.
- scheduler, batch selection, KV allocation semantics를 건드리지 않는다. `select_bucket_size`(`utils/optimum/bucket.py:20`)와 `pad_decoder_items`는 수정 대상이 아니다.
- `select_bucket_size`에 `@cache`가 걸려 있으므로 **함수 자체를 wrapping하면 첫 호출만 잡힌다.** 따라서 caller 쪽에서 읽는 방식이 유일하게 올바르며, 이는 동시에 cache 동작을 건드리지 않는다는 뜻이다.
- log level `DEBUG`이므로 기본 실행에서는 출력되지 않는다.

**`patches/` 정책 준수 방식** ([patches/README.md](../../patches/README.md) 7개 항목)

1. 대상 package와 exact version: `vllm-rbln 0.11.1`
2. upstream file path와 적용 전 SHA256을 patch 파일에 기록
3. semantics 무변경 근거: 위 "observation-only인 근거"
4. observation-only 우선 검토 결과: 위 4개 수단 검색 기록([TASK10](TASK10.md))
5. 적용/복구 명령을 patch 파일에 함께 기록
6. version/hash drift 시 fail-loud 중단: 적용 script가 SHA256 불일치 시 비-0 exit
7. run metadata에 patch 적용 여부와 hash를 기록

**대안**

| 대안 | 평가 |
|---|---|
| bucket을 직접 관측하지 않고 `running` 수로 추론 | `vllm:num_requests_running`은 scheduler 관점의 요청 수이고 bucket은 model runner가 그 뒤에 고르는 값이다. 두 값이 항상 같다는 근거가 없으므로 대리 지표로 쓰면 관측과 추론이 섞인다 |
| `VLLM_RBLN_USE_VLLM_MODEL=True` 경로로 전환 | 이 경로에는 `find_decode_batch_bucket`이 있으나 역시 per-step log는 없고, Stage 0–1b가 전부 기본 경로에서 검증됐으므로 substrate를 바꾸는 큰 변경이다 |
| upstream에 관측 추가를 요청 | 시간 척도가 이 연구와 맞지 않는다 |
| Track A를 보류하고 Stage 2(APC)를 먼저 진행 | 가능하다. Stage 2는 bucket 관측을 요구하지 않는다. 결정 3을 미루면서 연구를 진행하는 경로다 |

**권고**

Track A를 진행할 의사가 있다면 승인을 권고한다. 변경 규모가 log 1줄이고, 계산 자체는 이미 실행 경로에 존재하며, hash guard로 drift를 fail-loud로 잡을 수 있다. Track A를 당장 진행하지 않겠다면 **판정을 미루고 Stage 2를 먼저 진행하는 선택**도 합리적이다 — 결정 3은 Stage 2의 gate가 아니다.

권고는 제안일 뿐이며 판정은 사용자가 한다. 승인 전에는 patch를 작성하지도 적용하지도 않는다.

### 결정 2 — Stage 0 대상 model의 download/compile 승인

- 상태: `해소됨` — **판정 완료 (선택지 A 승인, 2026-08-19)**
- 판정 내용: `Qwen/Qwen3-4B`를 Stage 0 대상 model로 선택하고, weight download와 문서화된 파라미터(`--max_seq_len 8192 --batch_size 1 --num_devices 4`)의 optimum-rbln compile, CA25 단일 inference를 승인했다. Compile artifact 경로는 `/home/rebel/continuum-npu/models/`(gitignore 대상)이며, disk 100 GiB·compile wall-clock 2시간의 예산 상한을 함께 정했다. RSD 변경, device reset, site-packages 수정, `patches/` 적용, Stage 1 이후 작업, remote `push`는 계속 승인 범위 밖이다.
- 질문: Stage 0 single inference의 대상 model로 무엇을 선택하고, 해당 model의 weight download와 RBLN compilation을 승인할 것인가?
- 관련 TASK: [TASK02](TASK02.md), [TASK04](TASK04.md), [TASK05](TASK05.md)
- 승인 범위와 판정 기준의 사전 고정: [STAGE0_PREREG.md](STAGE0_PREREG.md)
- 근거 조사: [TASK05](TASK05.md). 조사 시각 2026-08-19 15:59 KST. Model은 실행하지 않았고 weight도 받지 않았다.

**전제 (세 선택지 공통)**: 기본 vLLM 실행 경로(`VLLM_RBLN_USE_VLLM_MODEL=False`)는 model 디렉터리의 `rbln_config.json`을 요구한다. 따라서 어떤 후보를 고르든 Stage 0는 **weight download + optimum-rbln compile** 두 단계를 모두 승인해야 진행된다.

| 항목 | A. `Qwen/Qwen3-4B` (권고) | B. `Qwen/Qwen3Guard-Gen-0.6B` | C. `Qwen/Qwen3.5-0.8B` |
|---|---|---|---|
| `architectures` | `Qwen3ForCausalLM` | `Qwen3ForCausalLM` | `Qwen3_5ForConditionalGeneration` |
| Download 크기 (safetensors / repo 전체) | 7.492 GiB / 7.507 GiB | 1.400 GiB / 1.415 GiB | 1.627 GiB / 1.648 GiB |
| Parameter 수 | 4.02 B (BF16) | 0.75 B | 0.87 B |
| KV bytes/token (파생) | 147,456 B = **144.0 KiB** (`36×8×128×2×2`) | 114,688 B = **112.0 KiB** (`28×8×128×2×2`) | 12,288 B = **12.0 KiB** (`6×2×256×2×2`, full-attn 6 layer만) + sequence당 linear state 약 9.6 MiB(bf16 가정, dtype `UNKNOWN`) |
| Attention 구조 | 36 layer 전부 full attention | 28 layer 전부 full attention | 24 layer 중 full 6 / GatedDeltaNet linear 18 (**hybrid**) |
| vllm-rbln registry 분류 | `_RBLN_GENERATION_MODELS` (text decoder-only) | `_RBLN_GENERATION_MODELS` (text decoder-only) | `_RBLN_MULTIMODAL_MODELS` (vision-language) |
| 지원 근거 등급 | **A** — CLI quick-start, class docstring 2곳, package README에 end-to-end compile command | **B** — architecture는 A와 동일 entry지만, 이 checkpoint id는 Cosmos guardrail의 `base_model_id` 기본값으로만 등장. decoder-only compile 예시 없음 | **C** — docstring 1곳(`RBLNQwen3_5ForCausalLM`). 단, HF checkpoint의 실제 arch는 registry상 multimodal 경로로 해석됨 |
| 문서화된 device 요구 | `num_devices=4` (`--batch_size 1 --max_seq_len 8192`) | 문서 예시 없음 (`UNKNOWN`) | `num_devices=1, device=0` (`kvcache_partition_len 4096, max_seq_len 8192`) |
| 최소 device 수 | `UNKNOWN` (자동 유도 코드 없음) | `UNKNOWN` | `UNKNOWN` |
| `max_position_embeddings` | 40,960 | 32,768 | 262,144 |
| License / gated | apache-2.0 / `False` | apache-2.0 / `False` | apache-2.0 / `False` |
| Stage 2 APC 자동 비활성 대상 | 아님 (`sliding_window: null`, `use_sliding_window: false`) | 아님 (동일) | 아님 (`layer_types`에 `sliding` 없음) |
| Compile 소요시간 / artifact 크기 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| 주요 미지수·위험 | download 7.5 GiB, device 4개 점유(전 32 ID idle이므로 가용). compile 비용 `UNKNOWN` | compile 예시 부재. safety-classifier tuning이라 생성 출력이 guard 판정 형식 — Stage 0 "valid output" 판정 기준을 따로 정해야 함 | **vision-language checkpoint**이며 text backbone이 hybrid. KV를 갖는 layer가 24개 중 6개뿐이라 KV lifecycle baseline으로 부적합. linear state dtype `UNKNOWN` |

**권고: A. `Qwen/Qwen3-4B`**

이유는 세 가지다. 첫째, 설치된 package에서 **end-to-end compile command가 문서화된 유일한 후보**다 (`optimum-rbln-cli --model-id Qwen/Qwen3-4B -o ./compiled_qwen3 --max_seq_len 8192 --batch_size 1 --num_devices 4`). Stage 0는 bring-up gate이므로 실패 시 원인이 "model 선택"이 아니라 "환경"으로 좁혀지는 후보가 유리하다. 둘째, 36 layer가 전부 full attention이라 KV bytes/token이 단일 산식으로 정의된다. 이 저장소의 연구 대상이 KV lifecycle과 cache attribution이므로 baseline은 KV semantics가 단순해야 한다. 셋째, download 7.5 GiB와 device 4개는 현재 host에서 제약이 아니다 — 32 visible ID가 전부 idle이고 device당 15.7 GiB가 비어 있다.

**권고와 다른 선택 시 고려사항**

- **B를 고르는 경우**: download를 5.4배 줄이지만 KV bytes/token은 144 → 112 KiB로 22%만 줄어든다. 즉 KV 압력 관점의 이득은 작고 절약되는 것은 주로 download/compile 비용이다. 또한 compile 예시가 없어 실패 시 "이 checkpoint가 이 경로에서 검증된 적 있는가"가 `UNKNOWN`으로 남는다. Stage 0 성공 판정 기준에 "생성 출력이 guard 판정 형식임"을 미리 반영해야 한다.
- **C를 고르는 경우**: 이 후보는 소형 text model이 아니라 vision-language model이며 text backbone의 3/4이 KV cache를 갖지 않는다. Stage 0는 통과할 수 있어도 Stage 2 APC characterization과 decoder observation의 baseline으로는 관측 대상이 왜곡된다. hybrid attention을 **연구 대상으로 삼겠다는 별도 결정**이 있을 때만 합리적이다.
- **어느 것도 승인하지 않는 경우**: 검증된 precompiled RBLN artifact path를 제공하면 download/compile 없이 Stage 0를 재개할 수 있다. TASK02의 local 탐색에서는 그런 artifact가 발견되지 않았다.
- **승인 시 함께 정해야 할 것**: `max_seq_len`, `batch_size`, `num_devices`, compile artifact 저장 경로, host disk 예산. compile 소요시간과 artifact 크기는 현재 `UNKNOWN`이므로 첫 compile 자체가 그 값의 측정이 된다.

권고는 제안일 뿐이며 판정은 사용자가 한다.

## 완료된 주요 작업

- Clean-room NPU repository migration 및 source isolation 검증이 초기 repository commit에서 완료됐다. 이는 TASK 체계 도입 전 작업이므로 근거 없이 별도 TASK로 소급 재구성하지 않았다.
- NPU hardware/software 환경, topology, source-resolution 위험, 포팅 준비도를 read-only로 감사했다. 상세 근거는 [NPU 환경](../environment/NPU_ENVIRONMENT.md), [이식 사전 분석](../environment/NPU_PORTING_ANALYSIS.md), [연구 준비도](../environment/NPU_RESEARCH_READINESS.md)에 있다.
- TASK01에서 agent 연구 기록 체계를 구축했다.
- TASK02에서 source isolation을 재검증하고 Stage 0 model gate의 blocker를 최신 환경에서 확인했다.
- TASK03에서 각 작업 종료 시 local `main` commit을 필수 workflow로 도입했다.
- TASK04에서 사용자 결정 대기 절, 선등록·동치 판정 hard rule, hostname `UNKNOWN` 승격으로 연구 workflow 문서를 개정했다.
- TASK05에서 Stage 0 후보 model metadata와 `atom-max8` hardware inventory를 read-only로 조사해 결정 2의 근거 표를 완성했다.
- TASK08에서 optimum-rbln compile 파라미터 공간과 KV accounting을 source로 확정하고 Stage 1b 권고안을 만들었다.
- TASK09에서 Stage 1a serving bring-up을 `PASS` 판정하고 `/metrics` 신호를 감사했다. TASK06의 `num_gpu_blocks` `UNKNOWN`이 해소됐다.
- TASK10에서 multi-bucket artifact로 동시 8 sequence 실행을 확인하고 Stage 1b를 `PASS` 판정했다. decoder bucket 관측이 불가임을 실행 수준에서 확인해 결정 3을 신설했다.
- TASK11에서 prefix cache hit 단위를 inner block 128 token으로 확정하고 APC OFF/ON 통제 방식을 검증했다.
- TASK12에서 결정 3을 집행해 decoder bucket 관측 patch를 적용·검증했다. `patches/` 정책의 첫 실전 적용이다.
- TASK13에서 decode step 비용을 bucket 결정 항과 actual 의존 항으로 분해하고 bucket별 step 시간 상수를 확정했다.
- TASK14에서 prefix-cache 생존 문턱을 두 층에서 각각 실측하고, `prefix_cache_hits_total`이 실제 재사용을 과대평가하는 구간을 발견했다.
- TASK15에서 그 절벽과 거짓 양성을 12/12로 재현하고 실제 재계산을 device-side 증거로 확정했으며, 층 2를 세는 Prometheus metric을 식별했다.
- TASK16에서 substrate descriptor v0와 층 태깅 규칙을 도입해 인스턴스 상수와 클래스 사실의 혼동을 구조적으로 차단했다.
- TASK17에서 agentic workload generator v0를 만들어 bucket 전이를 처음 관측하고, agentic gap에서 세션 절반이 prefix 재사용에 실패함을 확인했다.
- TASK18에서 per-request 귀속 채널을 구축하고 구성상 정답이 알려진 실험으로 검증해 게이트를 통과시켰다.
- TASK19에서 AGENTIC vs CONVENTIONAL 첫 짝 비교를 수행하고, agentic 저하가 부하 수준(N 대 `max_num_seqs`)에 의존함을 관측했다.
- TASK20에서 44 조합 sweep으로 그 의존이 **부호까지 바뀜**을 확인하고, TASK13 비용 모델이 다중 세션으로 전이되지 않음을 발견했다.
- TASK21에서 총 gap 시간을 고정한 채 분산만 조작해 재사용률이 도착 순서에 좌우된다는 서명을 관측했다(판정은 `INCONCLUSIVE`).
- TASK22에서 prefill 배타 실행을 직접 관측하고 비용 모델 v2로 TASK20의 편향을 설명했다.
- TASK23에서 격자를 바꾸는 **개입**으로 부호 역전의 원인을 확정했다 — 상관에서 인과로 넘어간 첫 결과다.
- TASK24에서 관측을 재현하는 시뮬레이터를 세웠다 — 개별 법칙에서 **실행 가능한 substrate 모형**으로 넘어간 결과다.
- TASK25에서 그 모형의 예측력을 선등록 게이트로 확인했다 — 이후 정책 질문을 실측 대신 **계산으로** 답할 수 있게 된 결과다. 다만 검증 격자는 N ≤ 7이다.
- TASK26에서 정책 여지를 계산으로 답하고, **판정치로 써 온 utilization이 비용 지표가 아님**을 확인했다 — 측정 축과 최적화 축을 분리해야 한다는 결과다.
- TASK27에서 그 여지가 **단순 causal 정책의 손이 닿지 않는 곳에 있음**을 확정했다 — headroom의 성격이 조정이 아니라 예지라는 결과이며, 정책 연구의 방향을 바꾼다.
- TASK28에서 그 결론을 실기기로 확인하고, 동시에 **시뮬레이터가 제어 개입이 들어간 조건까지 예측함**을 확인했다 — 정책 후보를 device가 아니라 계산으로 거를 수 있다는 결과다.
- TASK34에서 그 유일 경로를 실제로 열었고, TASK35가 채널을 고쳐 **선등록된 채널로 확증**했다 — 정책 연구의 세 배치가 음성으로 끝난 뒤 나온 양성 결과이며, 이 프로그램의 마지막 측정이다.
- TASK33에서 headroom을 정보 축으로 분해해 그 절반 이상이 조율의 몫임을 밝혔다 — runtime 회수 경로가 닫히고 compile-time이 남는다는 결과다.
- TASK32에서 예측기를 실제로 차용해 예측 기반 정책의 문을 닫았다 — 이 배치의 음성 결과 셋(정책 실패·예지 소멸·예측 불가)이 정책 방향에 대한 답이다.
- TASK31에서 워크로드를 실측 분포로 바꿔 결론의 이식성을 시험했다 — 시뮬레이터는 전이되고 headroom도 남지만 **예지의 가치는 워크로드 특유였다**는 결과이며, 예측기 방향을 재검토하게 만든다.
- TASK30에서 예지의 가치를 곡선으로 만들어 예측기 개발의 판단 근거를 세웠다 — "headroom이 있다"에서 "이만큼 정확한 예측기면 닿는다"로 넘어간 결과다.
- TASK29에서 기전 3개를 절제해 각 결과의 귀속을 확인했다 — 개별 관측에서 **substrate 성질과 결과의 인과 사슬**로 넘어간 결과이며, GPU 실측의 최소 범위를 생존 곡선 1건으로 좁혔다.
- TASK06에서 [STAGE0_PREREG.md](STAGE0_PREREG.md)로 판정 기준을 선등록한 뒤 Stage 0를 실행해 `PASS` 판정했다. `Qwen/Qwen3-4B` revision `1cfa9a72…`를 download(7.507 GiB / 66.8 s)하고 `--batch_size 1 --max_seq_len 8192 --num_devices 4`로 compile(165 s / 9.083 GiB)한 뒤 단일 inference(input 12 token, output 64 token, e2e 0.702 s)를 수행했다.
- TASK07에서 모든 작업 종료 시 GitHub push 여부를 사용자에게 확인하는 workflow를 도입했다.
- TASK36에서 판정 기준을 교정해 선등록하고 신규 seed로 다시 재 마지막 미해결 확증을 닫았다 — **교정된 기준에 기대지 않고 원 기준으로도 통과**했고, 동시에 `batch_size` 지배가 조건부임을 드러낸 결과다.
- TASK42에서 첨삭과 미해결 표식을 집행하고 저자·감사의 글까지 채워 제출 직전 상태를 만들었다 — 자기 비판(계통 오차)을 scope와 함께 논문에 실은 결과이며, 남은 것은 사람이 해야 하는 컴파일과 육안 검수다.
- TASK41에서 근거 추적을 원고까지 잇고 재발 함정을 한 곳에 모았다 — 주장 표와 본문의 관계를 기계적으로 검사할 수 있게 만든 결과이며, 이후 집필에서 "표는 있는데 본문이 안 따른다"가 불가능해진다.
- TASK40에서 지배 인자를 밀어 이득이 멈추는 곳을 쟀다 — 무보정 시뮬레이터가 **효과 없음**을 미리 맞힌 첫 사례이며, "최적 구성은 하드웨어 상한이 아니라 워크로드가 정한다"를 실측으로 세운 결과다.
- TASK39에서 초록을 arXiv 상한 안으로 압축하고 그림 PDF 경로를 설치 없이 열었다 — 환경의 결핍(CJK 폰트 부재)이 영문 그림 세트라는, 어차피 필요했던 작업을 강제한 결과다.
- TASK38에서 서지 3건을 정정하고 그림 수치 대조를 자동화했다 — 잠정 동일시가 오류로 판명된 사례이며, 특정하지 못한 서지는 잠정 배치하지 않는다는 원칙을 세운 결과다.
- TASK37에서 36개 TASK를 논문 뼈대로 조립했다 — 모든 주장을 근거 TASK·층 태그·그림으로 잇고 인스턴스 상수가 클래스 사실로 새어 나갈 지점 10곳을 사전에 식별한 결과다.

## 진행 중 또는 BLOCKED인 작업

- Stage 0 single inference: [TASK06](TASK06.md)에서 `PASS`. 더 이상 진행 중이거나 blocked인 항목이 아니다.
- Stage 1a serving bring-up: [TASK09](TASK09.md)에서 `PASS`. 더 이상 진행 중이거나 blocked인 항목이 아니다.
- Stage 1b multi-bucket compile과 동시성 진입: [TASK10](TASK10.md)에서 `PASS`.
- Track A (decoder bucket characterization): [TASK13](TASK13.md)에서 정상 상태 비용 모형을, [TASK17](TASK17.md)에서 전이 관측 도구를 확보했다. 남은 것은 (a) 블록 반복으로 같은 bucket 내 actual 효과의 재현성 확인, (b) 전이 구간의 실제 시간 비용 측정, (c) agentic vs conventional 본 비교다. 본 실험 전 필수 수정과 미지수 6개는 [TASK17](TASK17.md)의 "본 characterization 격자 설계에 필요한 미지수" 절에 있다.
- Stage 2 준비: [TASK11](TASK11.md)에서 hit 단위와 APC 통제 방식을 확정했다. 설계 제약(prefix ≥ 129 token, 조건 간 prefix 오염 차단, APC OFF/ON의 block 입도 confounder 기록)은 해당 TASK에 있다.
- Stage 2 APC OFF/ON characterization: **`SUPERSEDED`**. 원래 목적이던 prefix cache 특성화는 [TASK11](TASK11.md)(hit 단위 128 token), [TASK14](TASK14.md)(2층 구조·8 slot FIFO), [TASK15](TASK15.md)(절벽 12/12 재현·실제 재계산 확정)이 APC를 끄지 않고 **초과 달성**했다. APC OFF는 이제 특성화 수단이 아니라 **정책 레버**이며, 필요해지면 [TASK11](TASK11.md)이 기록한 confounder(OFF에서 `block_size` 128 → 8192, `num_gpu_blocks` 513 → 9가 함께 바뀜)를 통제한 **별도 설계**로 다룬다.
- Decoder batch observation: source-level observation point는 확인했으나 per-step runtime metric은 `UNKNOWN`이며 runtime 검증 전이다.

## 핵심 연구 흐름

Clean-room migration 및 환경 감사 → TASK01 연구 기록 체계 → TASK02 Stage 0 사전 검증(`BLOCKED`) → TASK03 작업 종료 commit workflow → TASK04 workflow 문서 개정 → TASK05 후보 model 조사·환경 재-inventory → TASK06 Stage 0 single inference(`PASS`) → TASK07 작업 종료 push 확인 workflow → TASK08 compile 파라미터·KV accounting source 조사 → TASK09 Stage 1a serving bring-up(`PASS`) → TASK10 Stage 1b multi-bucket compile·동시성(`PASS`) → TASK11 prefix cache hit 경계 확정 → TASK12 decoder bucket 관측 patch 적용·검증 → TASK13 decode step 비용 모형 분해 → TASK14 prefix-cache 생존 문턱 실측 → TASK15 절벽 재현·재계산 attribution 확정 → TASK16 substrate descriptor·층 태깅 → TASK17 agentic workload generator·bucket 전이 관측 → TASK18 per-request 귀속 게이트 통과 → TASK19 AGENTIC vs CONVENTIONAL 짝 비교 파일럿 → TASK20 N/slots sweep 본 측정 → TASK21 gap 분산 메커니즘 검증 → TASK22 prefill 배타 실행 검증·비용 모델 v2 → TASK23 bucket 격자 정렬 법칙 개입 검증 → TASK24 step 수준 시뮬레이터 구축 → TASK25 시뮬레이터 out-of-sample 검증(`PASS`) → TASK26 offline oracle bound → TASK27 causal 정책 평가 → TASK28 정책 실기기 검증(`PASS`) → TASK29 기전 절제 분석 → TASK30 예지 가치 곡선 → TASK31 현실 워크로드 전환 → TASK32 예측기 차용(`FAIL`) → TASK33 headroom 정보 분해 → TASK34 compile 구성 정책 → TASK35 최종 확증(N=8 `PASS`) → **측정 단계 종료** → TASK36 N=6 재확증(`PASS`) → TASK37 논문 조립 → TASK38 서지 정정·그림 검수 → TASK39 arXiv 준비 → TASK40 `batch_size` 포화 곡선(`포화` 2/2) → TASK41 본문 초고·LaTeX 패키지 → TASK42 첨삭 반영·저자 확정·제출 패키지 → **첫 Overleaf 빌드·육안 검수**

Stage 0–2 observation baseline 전에는 scheduler policy, KEEP/OFFLOAD/RECOMPUTE 또는 host/peer KV parking을 구현하지 않는다.

Legacy GPU 연구 문서는 `docs/legacy/TASK25.md`, `TASK27.md`, `TASK29.md`, `TASK31.md`에 있으며 새 NPU TASK와 다른 namespace다. 새 번호는 오직 이 디렉터리의 `TASKNN.md`만 기준으로 계산한다.

## 현재 유지해야 하는 핵심 원칙

- decision accuracy만 최적화하지 않고 mis-selection cost와 regret을 함께 본다.
- requested condition, observed condition, condition reached를 구분한다.
- eviction/release를 recomputation으로 간주하지 않는다.
- cache source를 latency만으로 판정하지 않는다.
- 증거가 부족하면 `PARTIAL`과 `UNKNOWN`을 허용한다.
- GPU threshold와 CUDA semantics를 NPU에 그대로 적용하지 않는다.
- instantaneous pressure만으로 cache survival을 설명하지 않는다.
- observation과 interpretation/hypothesis를 분리하고 모든 run의 provenance를 남긴다.
- 각 작업의 검증된 agent-owned 변경을 local `main`에 commit하고 commit hash를 보고한다.
- 모든 작업 종료 시 GitHub `origin/main` push 여부를 사용자에게 묻고 현재 질문에 명시적으로 승인받은 경우에만 push한다.
- 측정과 판정이 포함된 TASK는 판정 기준·예측·실험 격자를 측정 전에 commit하고(선등록) 사후에 기준을 완화하지 않는다.
- 짝(paired) 설계는 난수 소비량이 아니라 **구성**으로 보장한다. 두 arm을 각각 생성하지 않고 한 plan에서 파생한다 ([TASK19](TASK19.md)). 난수 소비량 동일성을 단일 seed로 확인하지 않는다 — 확률적 소비를 하는 함수가 있다.
- 핵심 발견에는 층 태그(`silicon` / `stack` / `class` / `universal`)를 붙인다. `class`는 형태에만 붙이고 값에는 붙이지 않으며, 근거 한 줄을 동반한다 ([TASK16](TASK16.md), [TASK_GUIDE.md](TASK_GUIDE.md)).
- 두 조건의 동치 판정은 고정 밴드가 아니라 중앙 ratio bootstrap CI가 1을 포함하는지와 사전 등록한 CI 폭 상한으로 한다.

## 후속 연구

**이 연구 프로그램의 측정 단계는 [TASK35](TASK35.md)로 종료됐고, [TASK36](TASK36.md)이 그 미해결 확증 1건을 닫는 후속 측정이었다.** 아래는 남은 미해결 항목이며 **사용자 지시 없이 착수하지 않는다.**

| # | 항목 | 근거 TASK | 새 측정 필요 | 재compile 필요 |
|---|---|---|---|---|
| 1 | ~~**N=6 확증의 재측정**~~ → **[TASK36](TASK36.md)에서 완료. `PASS` 2/2.** 대신 새 항목이 열렸다: **`BASE` 캐시 손실량 대 X의 함수 형태**. 관측점 3개(N=8 재사용 9/24 → X +9.72 %, N=6 seed `20261000` 15/18 → +3.40 %, N=6 seed `20261100` 17/18 → +2.11 %)가 단조 정렬되나 함수 형태를 말할 표본이 없다 | [TASK36](TASK36.md) | 예 | 아니오 |
| 2 | **bucket 6·10·16의 step 비용 통제 측정** — 시뮬레이터가 쓰는 선형 보간을 실측으로 대체한다. [TASK34](TASK34.md)의 최소자승 적합은 측정된 bucket에서도 **±11 % 산포**가 있어 [TASK13](TASK13.md) 수준이 아니다. bucket 16은 N ≤ 10에서 한 번도 쓰이지 않아 값이 없다 | [TASK34](TASK34.md), [TASK35](TASK35.md) | 예 | 아니오 |
| 3 | ~~**`batch_size > 16`의 이득과 KV 한계**~~ → **[TASK40](TASK40.md)에서 해소.** B=16 포화 확인, KV 한계 B ≈ 46(외삽). 새로 열린 항목: **N > 16에서의 반전 여부**(최상위 눈금이 실제 선택되는 구간)와 **눈금 24·32의 [TASK13](TASK13.md) 방식 통제 측정**(이번에도 0.0 % 선택돼 재지 못했다) | [TASK40](TASK40.md) | 예 | 아마도 |
| 4 | **N > 10 구간** — 시뮬레이터 예측력이 [TASK24](TASK24.md)에서 5–6배 나빠지고 [TASK25](TASK25.md)의 검증 격자에도 없다. [TASK35](TASK35.md)의 탐색 구간 오차도 +0.034/+0.036이었다 | [TASK24](TASK24.md), [TASK35](TASK35.md) | 예 | 아마도 |
| 5 | **server 측 scheduler 정책** — [TASK33](TASK33.md)이 headroom의 60 %가 *조율*의 몫이고 per-session client 정책은 원리적으로 닿을 수 없다고 확정했다. 조율이 가능한 유일한 runtime 위치이나 **patch 정책 대상**이다 | [TASK33](TASK33.md) | 예 | 아니오 |
| 6 | **GPU 교차검증** — [결정 4](#결정-4--gpua6000-교차검증-착수-시점)에 따라 **조건부 이연**. 재개 시 최소 범위는 생존 곡선 1실험이며, [TASK29](TASK29.md) 계산에 따르면 재야 할 축은 accelerator가 아니라 `max_num_seqs`다 | [TASK29](TASK29.md), 결정 4 | 예 | 예 |
| 7 | **도구 인자를 조건으로 삼는 예측 가능성** — [TASK32](TASK32.md)가 도구 *이름*만으로는 지속시간 예측 오차가 줄일 수 없는 분산에 지배됨을 보였다. 현재 trace 산출물에 인자가 없어 **새 자료가 필요하다** | [TASK32](TASK32.md) | 예 (새 trace) | 아니오 |
| 8 | **계통적 양의 예측 오차의 원인** — 시뮬레이터가 개입의 이득을 계통적으로 과대평가한다. [TASK28](TASK28.md)(+0.018·+0.021), [TASK35](TASK35.md)(+0.0074·+0.0058, N=6 +0.0183·+0.0194), [TASK36](TASK36.md)(+0.0067·+0.0076) — **네 TASK에서 같은 부호**다. 정책 개입과 compile 구성 개입 양쪽에서 나타나므로 개입 종류에 무관하다. client overhead인지 큐 직렬화인지 재사용 귀속 오차인지 가르지 못했다 | [TASK28](TASK28.md), [TASK35](TASK35.md), [TASK36](TASK36.md) | 아니오 | 아니오 |
| 10 | ~~**서지 미특정 2건**~~ → **[TASK38](TASK38.md)에서 해소.** `LENS` = arXiv:2606.18042(NPU 지연 예측, bucketing 비선형성), `KV-RM` = arXiv:2605.09735(**저자 철회됨**). [TASK37](TASK37.md)의 `KV-RM ≈ CacheScout` 잠정 동일시는 **오류였고 정정했다**. 남은 항목: **arXiv 제출 직전 서지 재확인** — arXiv:2511.02230은 버전마다 시스템 이름이 바뀐 전례가 있다 | [TASK38](TASK38.md) | 아니오 | 아니오 |
| 9 | **[TASK23](TASK23.md)의 남은 `INCONCLUSIVE`** — N=7(6블록에서도 4/6이 동치 밴드 안), 개입 후 N=6. 효과 크기가 밴드 폭과 비슷해 블록 증가로 닫힌다는 보장이 없다 | [TASK23](TASK23.md), [TASK25](TASK25.md) | 예 | 아니오 |

## 보류 중인 항목

- **[TASK21](TASK21.md) b1(gap 분산) 블록 추가는 보류한다.** 사유: prefill 직렬화 항이 확정되기 전에는 분산 효과와 prefill 정지 효과가 얽혀 있어 표본을 늘려도 해석력이 올라가지 않는다. [TASK22](TASK22.md)에서 항이 확정됐으므로, 그 결과를 반영한 **별도 설계**로 재개한다 (Advisor 지시, 2026-08-21).
- **[TASK23](TASK23.md) batch에서도 [TASK21](TASK21.md) b1 블록을 추가하지 않았다.** 사유: 지시문 수정(Advisor, 2026-08-21)이 2a의 범위를 N=8 신규 3블록으로 확장하는 대신 [TASK21](TASK21.md) 블록 추가를 이번 batch에서 **명시적으로 제외**했다. 승인된 serving lifecycle 예산(약 40회) 중 38회를 [TASK23](TASK23.md)이 사용했다.
- **[TASK23](TASK23.md)의 `INCONCLUSIVE` 중 N=3은 [TASK25](TASK25.md)에서 6블록 "역전"으로 확정됐다.** N=7은 6블록에서도 미결이고(4/6 블록이 밴드 안, pooled 1.0273), 개입 후 N=6은 블록을 늘리지 않았다. 남은 둘은 효과 크기가 밴드 폭과 비슷해 블록 증가로 닫힌다는 보장이 없다.

## 다음 작업 후보

1. **논문 조립** — [결정 5](#결정-5--시스템-명칭-충돌)의 명칭 변경을 포함한다. **측정 단계는 [TASK35](TASK35.md)로 종료됐다.**
2. 아래 [후속 연구](#후속-연구) 절의 항목들 — 전부 사용자 지시가 있을 때만 착수한다.
3. 도구 **인자**를 조건으로 삼는 예측 가능성 — 현재 trace 산출물에 인자가 없어 새 자료가 필요하다.
3. **논문 조립** — [결정 5](#결정-5--시스템-명칭-충돌)에 따라 시스템 명칭을 변경한다.
4. [TASK28](TASK28.md) 발견 3의 계통 편향 원인 규명 — `client_overhead_s`를 실측값으로 넣고 재예측해 설명되는지 확인한다. 새 측정이 필요 없다.
3. `max_num_seqs` 축에서 격자 정렬 법칙의 크기 변화 계산 ([TASK29](TASK29.md) 발견 3의 후속). 새 측정이 필요 없다.
3. N ≥ 10 구간의 예측력 검증 — [TASK25](TASK25.md) 격자가 N ≤ 7이라 그 구간은 검증되지 않았고, [TASK24](TASK24.md)는 그곳에서 오차가 5–6배 커진다고 기록했다.
3. [TASK23](TASK23.md)의 남은 `INCONCLUSIVE` — N=3은 [TASK25](TASK25.md)에서 "역전"으로 확정됐다. N=4·N=7·개입 후 N=6은 효과 크기가 밴드 폭과 비슷해 블록을 늘려 닫힐지 불확실하다.
4. ε 이득이 실제 device에서 재현되는지의 측정 — hold를 실제로 넣은 실험 ([TASK26](TASK26.md)은 계산이며 측정으로 확인하지 않았다).

이 목록은 권고 순서다. 사용자의 지시 없이 다음 작업을 자동 시작하지 않는다.
