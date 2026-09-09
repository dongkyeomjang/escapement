# 내부 provenance — 논문 3.2의 주장별 근거

[PAPER_3_2.md](PAPER_3_2.md)의 각 주장을 원자료·소스·재집계 명령에 연결한다.
**이 문서는 내부 전용**이며 논문 본문·표·캡션에는 들어가지 않는다.

감사 기록: [TASK58](TASK58.md). 감사 계획: [LAYER_AUDIT_PLAN.md](LAYER_AUDIT_PLAN.md)
(commit `a1826b7`, 재집계보다 앞섬). 기준 commit `a4e6433`.

공통 재집계 명령:

```bash
env -u PYTHONPATH python3 experiments/npu/analysis/layer_audit.py \
    --output results/npu/stage2/layer_audit.json
```

`results/`는 `.gitignore` 대상이므로 산출 JSON은 commit되지 않는다.

## 약어

| 약어 | 경로 |
|---|---|
| `PILOT` | `results/npu/stage2/20260819-200800-gap-turnover/` |
| `REPRO` | `results/npu/stage2/20260819-204900-cliff-repro/` |
| `CAP` | `results/npu/stage2/20260823-183505-final-confirm/` |
| `AGENTIC54` | `results/npu/stage2/20260908-133635-grid-paired/` |
| `PCM` | `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/prefix_cache_manager/optimum_prefix_cache_manager.py` |
| `SCHED` | `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/optimum_scheduler.py` |
| `KVM` | `/usr/local/lib/python3.10/dist-packages/vllm_rbln/v1/core/optimum_kv_cache_manager.py` |

## 주장별 표

| 3.2 위치 | 주장 | 1차 근거 | 원자료 / 소스 | 재집계 | 원 TASK |
|---|---|---|---|---|---|
| 3.2.1 | 두 관리 단위의 크기 128 / 8,192 | 설치 소스 | `PCM:32-45` (`BlockConfiguration`, `block_ratio`) | — | [TASK11](TASK11.md), [TASK14](TASK14.md) |
| 3.2.1 | 기준 구성의 slot 8개, `batch_size`가 정함 | artifact config | `models/Qwen3-4B-rbln-b8-s8192-d4-mb/rbln_config.json` (`batch_size=8`, `kvcache_num_blocks=8`) | 직접 읽기 | [TASK08](TASK08.md) |
| 3.2.1 | slot 회수는 FIFO, 재접근이 순위를 갱신하지 않음 | 설치 소스 | `PCM:258` (`FIFOEvictionPolicy()` 하드코딩) | — | [TASK14](TASK14.md) 발견 5 |
| 3.2.1 | 성립은 slot이, 양은 128 단위가 정함 | 실측 + 소스 | `AGENTIC54` turn-1 168건 (hit 95, 0 73건) | [TASK57](TASK57.md) §4 | [TASK24](TASK24.md) 관측 2 |
| 3.2.1 | 누적 hit counter는 slot 회수 뒤에도 hit 보고 | 실측 | `PILOT`·`REPRO` 채널 대조 | — | [TASK14](TASK14.md) 발견 3, [TASK15](TASK15.md) 판정 2 |
| 3.2.1 | 요청별 값은 응답 cached token에서만 취함 | 방법 | — | — | [TASK18](TASK18.md), [KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 항목 3 |
| 3.2.2 | 재사용 범위 = 직전 prefill 범위를 128로 내림 | 실측 | `REPRO`(1,920 token), `AGENTIC54`(95/95) | [TASK57](TASK57.md) §4 표 | [TASK24](TASK24.md) 관측 2 (271/271) |
| 3.2.2 | 생성 token은 범위에 없음 | 실측 | 같음. 판별력 있는 건 71/95 | 같음 | [TASK24](TASK24.md) 발견 1 |
| 3.2.3 | 배경 요청 구성·순서 (2,000 token, 동시성 1 순차) | 실험 조건 | `PILOT`/`REPRO`의 `gap_prompts.json`·`cliff_prompts.json` | — | [TASK14](TASK14.md), [TASK15](TASK15.md) |
| 3.2.3 | m ≤ 6 전량 생존 / m ≥ 7 전량 소멸 | 실측 | `PILOT/server-B{0,3,6,7,8,9,16}.log` | `layer_audit.py` §2 | [TASK14](TASK14.md) 판정 |
| 3.2.3 | 12개 실행 일치 (m ∈ {5,6,7,8} × 3) | 실측 | `REPRO/server-B{5,6,7,8}r{0,1,2}.log` | 같음 | [TASK15](TASK15.md) 판정 1 |
| 3.2.3 | 부분 생존 구간 없음 | 실측 | 같음 (1,920 또는 0) | 같음 | [TASK14](TASK14.md) 발견 6 |
| 3.2.3 | 무처치 반복 10회 중 3회에서 5/8, 7회에서 6/8 | 실측 | `results/npu/stage2/20260901-020342-null-channel/util.NULL.n8.b{0..9}.json` | — | [TASK50](TASK50.md) 실행별 표 |
| 3.2.4 | 회수 건수 = `max(0, 요청 수 + 1 − slot 수)`, 21/21 | 실측 | `PILOT` 9 + `REPRO` 12 로그 | `layer_audit.py` §2 | **[TASK58](TASK58.md) 신규** ([TASK14](TASK14.md)·[TASK15](TASK15.md)의 `UNKNOWN`을 닫음) |
| 3.2.4 | `+1`은 padding scratch slot | 소스 + 소거법 | `SCHED:594-597` (요청 조건), `PCM:508-529` (`get_dummy_block`), `PCM:108-112` (`peek_dummy_block`, 할당 없음), `PCM:462-484` (`can_allocate`의 회수 부작용), `PCM:260-263` (`is_full_block_available`) | `layer_audit.py` §2 (선점 0/21, 미재할당 회수 1건/실행) | **[TASK58](TASK58.md) 신규** |
| 3.2.4 | m=6은 조회·재사용 뒤 회수 | 실측 | `PILOT/server-B6.log` 사건 열 | `layer_audit.py` §2 사건 순서표 | [TASK24](TASK24.md) 관측 3과 일관 |
| 3.2.4 | m=7은 조회 전 회수 (`MATCHED_OB=None`) | 실측 | `PILOT/server-B7.log` | 같음 | 같음 |
| 3.2.4 | 도착 순서 서명 6개 중 5개 | 실측 | `results/npu/stage2/20260820-180000-gap-dispersion/` | — | [TASK21](TASK21.md) 관측치 2 (1차 판정 `INCONCLUSIVE`) |
| 3.2.5 | `batch_size` 8 → 16, slot 8 → 16 | artifact config | 두 `rbln_config.json` (`batch_size`, `kvcache_num_blocks`, `decoder_batch_sizes`, `max_seq_len`) | 직접 읽기 | [TASK08](TASK08.md), [TASK35](TASK35.md) |
| 3.2.5 | 재사용 9/24 → 24/24 | 실측 | `CAP/probe/requests.{BASE,BATCHONLY}.n8.b{0,1,2}.jsonl` | `layer_audit.py` §3 | [TASK35](TASK35.md) 관측 3 |
| 3.2.5 | prefill 재계산 22,103 → 5,079 (재도착분) | 재집계 | 같음 | 같음 | **[TASK58](TASK58.md) 신규 집계** |
| 3.2.5 | 폭 16이 0 step | 실측 | `CAP/util.BATCHONLY.n8.b{0,1,2}.json`의 `pair_histogram` | 같음 | [TASK35](TASK35.md)과 일관 |
| 3.2.5 | 공통 폭 분포가 완전히 같지는 않음 | 재집계 | 같음 (b1 891→936, b2 136→121, b4·b8 동일) | 같음 | **[TASK58](TASK58.md) 신규** |
| 3.2.5 | 입력 계획 동일 | 재집계 | `CAP/probe/meta.*.n8.b*.json`의 `plan` SHA256·`total_gap_s` | 같음 | [TASK57](TASK57.md) 발견 1의 한계 적용 |
| 3.2.6 | 직전 prefill 범위 800–1,600, 재사용 가능분 768–1,536 | 실측 | `AGENTIC54` turn-0 168건 (803–1,576), hit 95건 (768–1,536) | [TASK57](TASK57.md) 후속 집계 | [TASK24](TASK24.md) 규칙 |
| 3.2.7 | 다른 회수 정책으로의 이식 제한 | 절제(모형) | — | — | [TASK29](TASK29.md) |

## 정정 이력

| 대상 | 내용 | 기록 |
|---|---|---|
| [TASK57](TASK57.md) §4 | 계층 번호 표기 오류 3곳 (내용 오류 0건) | [TASK58](TASK58.md) 쟁점 1 정정표. **원문은 수정하지 않음** |
| [TASK14](TASK14.md)·[TASK15](TASK15.md) | 회수 건수 `m − 5`의 `UNKNOWN`이 닫힘 | [TASK58](TASK58.md) 쟁점 2. **원 판정·수치는 그대로** |
| [TASK14](TASK14.md) 해석 | "resume의 decode가 outer block을 더 요구"라는 hypothesis는 **채택되지 않음** — 실제 경로는 scheduler의 padding scratch | [TASK58](TASK58.md) 쟁점 2 판정 |

## 이 절이 새 측정 없이 닫지 못하는 것

| 항목 | 필요한 것 | 왜 필요한가 |
|---|---|---|
| padding scratch 회수의 **직접 라벨** | `get_dummy_block` 경로에 DEBUG 한 줄 (observation-only patch) + 재측정 | 현재 귀속은 소거법이다. 로그에 유발자 표시가 없다 |
| padding 정도와 KV 생존의 **정량 관계** | 동시성 > 1에서 decode 충전율을 바꾸는 격자 | 3.2.4의 함의를 수치로 말하려면 필요하다 |
| 확대 구성에서의 **문턱 이동** | 확대 구성에서 배경 요청 수별 전환 위치 측정 | 생존율 비교만으로는 문턱이 몇 요청 움직였는지 말할 수 없다 |
| 동시 실행에서의 회수 식 | 동시성 > 1의 `[PFX]` 로그 | 21개 실행이 전부 동시성 1이다 |

**어느 것도 이번 작업에서 실행하지 않았다.** compile 0, serving lifecycle 0,
신규 측정 0.
