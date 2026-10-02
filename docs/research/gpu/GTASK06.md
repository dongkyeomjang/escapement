# GTASK06 — descriptor 구조 요구사항 정리 (두 기판 공통 표현)

## 상태

DONE

## 날짜

2026-09-29

## 목적

GPU 지시문 G-02 작업 E. 현재 `SubstrateDescriptor`로 GPU 기판을 표현할 수 없음([GTASK02](GTASK02.md) FIT_GAPS 11건)을 입력으로, 두 기판을 함께 표현하는 데 필요한 field 목록과 의미를 NPU 값·GPU 값과 함께 [DESCRIPTOR_REQUIREMENTS.md](DESCRIPTOR_REQUIREMENTS.md)로 정리한다. **코드 변경 0**, `src/continuum/` 무수정(개편은 NPU 쪽 담당).

## 배경

관련 TASK:

- [GTASK01](GTASK01.md)–[GTASK05](GTASK05.md) — GPU 쪽 근거
- [TASK16](../TASK16.md) — descriptor 도입, [TASK73](../TASK73.md) — `release_rule`·`dummy_mode`·`resume_allocates_first` 추가
- [TASK08](../TASK08.md), [TASK13](../TASK13.md), [TASK14](../TASK14.md), [TASK22](../TASK22.md), [TASK24](../TASK24.md), [TASK63](../TASK63.md), [TASK69](../TASK69.md), [TASK72](../TASK72.md) — NPU 쪽 근거

## 시작 상태

branch `gpu-a6000`, merge `a48c7b4` 이후. descriptor는 TASK73 판(고정 2층 + 의미론 field 3개).

## 수행 내용

field를 11개 묶음(A 층 구조, B 축출 순서·생존 창, C 조회·할당, D 캐시 대상·hit, E 비요청 소비자, F preemption, G admission 제약, H 격자, I step 비용, J prefill 실행, K 실행 pipeline)으로 나누고, 각 field에 의미·NPU 값·GPU 값·현재 descriptor 대응을 적었다. 모형 부분(B1–B4)별로 어떤 field가 필요한지와, GTASK04에서 wrapper가 대신 넣어야 했던 field를 표시했다.

## 변경된 파일

- `docs/research/gpu/DESCRIPTOR_REQUIREMENTS.md` (신규), `docs/research/gpu/GTASK06.md` (신규), `docs/research/gpu/GPU_INDEX.md`

## 실험 또는 검증 방법

없음(문서). 각 값의 출처 TASK·source 줄을 문서에 인용했다.

## 결과

요약은 [DESCRIPTOR_REQUIREMENTS.md](DESCRIPTOR_REQUIREMENTS.md) §1. 핵심 차이:

- **층 구조**: NPU 2층(재사용은 층 2), GPU 1층 → 층 목록 + `reuse_layer`.
- **축출 순서의 기준**: 할당 순서 FIFO 대 release 순서 LRU, 요청 내부 all-or-nothing 대 tail-first, GPU의 미사용 block 우선.
- **조회·할당**: 할당 후 조회 대 조회 후 할당 + hit 선보호.
- **캐시 대상**: prefill token만 대 계산된 전 token(생성 포함).
- **비요청 소비자**: 시변 dummy(`pre_evict`) 대 상수 null block.
- **preemption**: 없음 대 recompute(끌 수 없음).
- **격자**: 요청 수 사상·compile 고정 대 token 수 사상·server 인자, 최상위 초과는 eager.
- **step 비용**: 곡선 1개 대 FULL·PIECEWISE·eager 3개.
- **prefill**: 배타(정지 비용) 대 혼합(증분 비용).

## 핵심 발견

1. **`class`** — **두 기판의 생존 규칙 차이는 다섯 개의 규칙 field(축출 기준, 창 시작, 요청 내부 손실 순서, 조회·할당 순서, 캐시 대상)로 모두 적힌다.** 근거: GTASK04에서 NPU 데이터로 만든 모형 코드가 이 다섯 값만 wrapper로 바꿔 GPU 순차 생존을 계산했다(결과는 GTASK04). 규칙 field는 가속기가 아니라 serving stack 설계 범주의 선택이다.
2. **`stack`** — **GPU의 pool 크기와 격자는 runtime flag다.** 모형의 "재고 예측"에서 GPU는 재compile 없이 파라미터를 바꿀 수 있다 — `value_source` field가 필요한 이유다.

## 해석

- 현재 descriptor의 `outer_*` 필수 field와 `bucket_for`의 요청 수 가정이 GPU 표현을 막는 두 지점이다. 층 목록과 `grid_unit`만 들어가도 GTASK02의 거부 사례가 풀린다.

## 확인되지 않은 사항

- NPU 쪽 `UNKNOWN` 값 4개(`failed_admission_evicts`, `cache_registration`, `step_token_budget`, `in_flight_batches`)
- GPU async scheduling에서 반납 시점의 step 지연 크기
- GPU `step_cost.*` 값: 문서는 field 구조만 정하고 수치는 [GTASK05](GTASK05.md) 측정에 의존한다. GTASK05 첫 측정(`20260929T1021Z`)은 host 다운으로 중단됐다(GTASK05 참조).

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- "`class` 태그는 형태에만"(TASK_GUIDE)을 descriptor 구조로 옮기면, **규칙 field는 형태(`class` 후보), 수치 field는 인스턴스(`stack`/`silicon`)**로 갈린다.

## 다음 작업

NPU 쪽 descriptor 개편(Advisor 지시 대상). 이 branch에서는 `src/continuum/`을 고치지 않는다.

## 재현 정보

- 선등록 commit: 해당 없음(측정·판정 없음)
