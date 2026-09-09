# 감사 계획 — 계층 표기·회수 사건·용량 개입

이 문서는 **계산 전에** commit한다. 아래의 감사 질문과 재집계 정의는 계산 후에
바꾸지 않는다.

## 성격 — 선등록이 아니다

**새 측정이 없다.** compile 0, serving lifecycle 0, 신규 측정 0. 따라서 이 문서는
[CLAUDE.md](../../CLAUDE.md) 원칙 16이 뜻하는 **선등록이 아니며 그렇게 주장하지
않는다.** 과거 결과에 대한 사후 선등록은 성립하지 않는다.

이 문서가 하는 일은 하나다 — **재집계의 정의를 결과를 보기 전에 고정**해, 숫자를
보고 정의를 고르는 일이 없게 한다.

**기준을 바꿔 과거 판정을 개선하지 않는다.** [TASK14](TASK14.md)·[TASK15](TASK15.md)·
[TASK21](TASK21.md)·[TASK35](TASK35.md)·[TASK40](TASK40.md)의 판정과 수치는 그대로
둔다. 어긋나는 것이 나오면 **새 문서의 정정표**에 적고 과거 문서를 덮어쓰지 않는다.

## 기준 commit

`a4e643320bf5645f8e6e6c17730edbaf16fbbf4f` (Advisor가 읽은 public main과 동일함을
확인). 이 문서 작성 시점의 `git status --short`는 `?? .idea/`뿐이다.

## 사전 조사 고지

정의를 쓰기 위해 다음을 **먼저 열어 보았다.** 결과 집계가 아니라 형식 확인이다.

- `[PFX]` 로그의 이벤트 어휘 7종과 각 줄의 field 이름
  (`ALLOC` 251, `FREE-REQUEST` 251, `EVICTION` 111, `MAPPING-REMOVE` 111,
  `MAPPING-SEARCH` 19, `CACHE-PARTIAL` 10, `CACHE-HIT` 9 — 두 run 합)
- `[TASK14](TASK14.md)` B6 로그의 사건 열 1개 (형식 예시로 열람)
- [TASK35](TASK35.md) run의 파일 종류와 artifact `rbln_config.json`의 존재

## 쟁점 1 — 계층 표기와 요청별 신호

### 감사 질문

- Q1-1. 설치 소스와 로그에서 두 계층의 **canonical** 이름·크기·역할은 무엇인가
- Q1-2. [TASK57](TASK57.md) §4의 "층 1 / 층 2" 표기가 [TASK14](TASK14.md)·
  [TASK15](TASK15.md)와 어긋나는가. 어긋난다면 **표기만**인가, **설명 내용**에도
  영향이 있는가
- Q1-3. 네 신호(`prefix_cache_hits_total`, `prompt_tokens_cached_total`,
  응답의 `usage.prompt_tokens_details.cached_tokens`, `[PFX]`)는 각각 어느 계층의
  무엇을 세는가. 요청별인가 누적인가

### 판별 규칙 (계산 전 고정)

- **표기 역전만**으로 판정하는 조건: [TASK57](TASK57.md)의 각 문장에서 계층 이름을
  서로 맞바꿨을 때 **수식·수치·결론이 그대로 성립**한다
- **내용 오류**로 판정하는 조건: 맞바꿔도 성립하지 않는 문장이 하나라도 있다
- 두 판정은 **문장 단위**로 낸다. 문서 전체를 한 덩어리로 판정하지 않는다

### 근거의 우선순위

설치 소스 > `[PFX]` 원로그 > 기존 TASK 서술. 셋이 어긋나면 앞의 것을 채택하고
차이를 정정표에 적는다.

## 쟁점 2 — 회수 건수의 한 건 차이

### 감사 질문

- Q2-1. `m − 5`(실측)는 **run 전체의 `[EVICTION]` 줄 수**인가, 다른 population인가
- Q2-2. `m − 6`(산술 예상)은 **같은 시간 구간·같은 이벤트**를 세는가
- Q2-3. m=6에서 대상 KV의 회수는 재사용 **뒤에** 일어났는가
- Q2-4. m=7에서 대상 KV는 조회 **전에** 이미 없었는가
- Q2-5. dummy block·요청 종료 처리·재개 요청 자체의 할당에 대한 **기존 증거**가
  로그에 있는가

### 재집계 정의 (계산 전 고정)

| 이름 | 정의 |
|---|---|
| **할당 세대** | 같은 `OB` ID가 `[ALLOC]`으로 다시 잡히면 **새 세대**다. `OB<id>#<세대>`로 표기하고, **ID가 같다는 이유로 같은 KV의 연속 생존으로 읽지 않는다** |
| **대상 KV** | trial의 **첫 `[ALLOC]`** 이 잡은 `OB`의 **그 세대**. 이후 같은 ID가 재할당되면 다른 KV다 |
| **회수 건수(실측)** | 해당 trial server 로그의 **`[PFX] [EVICTION]` 줄 수** |
| **산술 예상** | `max(0, 총 [ALLOC] 줄 수 − 8)`. pool 8은 [TASK14](TASK14.md) source 조사값 |
| **사건 순서표** | trial 로그의 `[PFX]` 줄을 **파일 등장 순서 그대로** 나열하고, 각 줄이 대상 KV와 관련되는지 표시한다. 시각 재정렬을 하지 않는다 |

### 무엇을 결론으로 쓰지 않는가

- 로그로 설명되지 않으면 **`UNKNOWN`을 유지**한다
- "`decode`가 추가 slot을 요구했을 것" 같은 [TASK14](TASK14.md)의 **hypothesis를
  확인 사실로 승격하지 않는다**
- 소스에서 확인되지 않은 원인을 추정으로 채우지 않는다

## 쟁점 3 — 용량 개입의 논문용 표

### 고정 범위

**[TASK35](TASK35.md)의 N=8, `BASE` → `BATCHONLY`만** 쓴다.
[TASK40](TASK40.md)의 `10/24`는 **다른 실험**(격자 `(1,4,6,8,10,B)`)이므로 이 표에
섞지 않는다. [TASK40](TASK40.md)이 B8→B16을 **"통제되지 않은 인접쌍"** 으로 이미
분류했으므로 그것을 "slot만 바꾼 통제 실험"으로 재해석하지 않는다.

### 재집계 정의 (계산 전 고정)

| 열 | 정의 | source |
|---|---|---|
| 반복 번호 | `b0`, `b1`, `b2` | 파일명 |
| 재도착 요청 수 | client row 중 `turn > 0` | `probe/requests.*.jsonl` |
| 재사용 성공 수 | 그중 `cached_tokens > 0` | 같음 |
| cached token 합 | `Σ cached_tokens` (`turn > 0`) | 같음 |
| 실제 prefill 계산 token 합 | `Σ (prompt_tokens − cached_tokens)` — **전 요청**과 **`turn > 0`** 둘 다 낸다 | 같음 |
| 선택 bucket별 step 수 | `util.*.json`의 `pair_histogram`을 **bucket으로** 집계 | `util.*.json` |
| 최대 actual batch | `pair_histogram` key의 `actual` 최댓값 | 같음 |
| 입력 계획 동일성 근거 | `meta.*.json`의 `plan` SHA256, `total_gap_s`, 그리고 client row의 `requested_segment_tokens`·`requested_generation_tokens` 열 대조 | `probe/meta.*.json` |

**요청별 값은 client 응답 row에서만 가져온다** — [TASK18](TASK18.md)이 확정한 귀속
경로다. **동시 실행의 누적 counter 차분을 개별 요청 값으로 쓰지 않는다**
([KNOWN_PITFALLS.md](KNOWN_PITFALLS.md) 항목 3).

### 별개로 보고할 것

1. **추가 bucket 16의 실제 사용이 0인가** — `pair_histogram`에 bucket 16이 있는가
2. **공통 bucket(1·2·4·8)의 사용 분포가 같은가** — 위와 **별개 항목**으로 낸다.
   1번이 0이어도 2번이 같다는 뜻은 아니다

### artifact config 병기

두 artifact의 `rbln_config.json`에서 `batch_size`, `kvcache_num_blocks`,
`decoder_batch_sizes`, `max_seq_len`을 읽어 병기한다.

## 산출물

| # | 파일 | 내용 |
|---|---|---|
| 1 | `TASK58.md` | 계층 대응표, 사건 순서표와 판정, 용량 개입 표, 정정표, `UNKNOWN` |
| 2 | `PAPER_3_2.md` | 논문 3.2용 문장·표·주석. **TASK 번호·내부 작업명·원로그 경로를 넣지 않는다** |
| 3 | `PROVENANCE_3_2.md` | 주장별 근거 경로·원자료·재집계 명령 (내부 전용) |
| 4 | `experiments/npu/analysis/layer_audit.py` | 재집계 script |

## 금지 사항 재확인

compile, serving 기동·종료, 신규 측정, patch·package 변경, 원자료 덮어쓰기,
기존 판정·수치의 소급 변경, 원격 push를 하지 않는다.
