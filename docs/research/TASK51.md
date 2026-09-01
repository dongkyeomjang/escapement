# TASK51 — 실행 모델 명칭의 문헌 조사

## 상태

DONE

## 날짜

2026-09-01

## 목적

compile 시점에 그래프·shape·자원이 고정되는 가속기 실행 모델을 **기존 문헌이 어떤
용어로 부르는지** 조사하고, 우리 용어 `compile-time-static serving substrate`에 가장
가까운 기존 용어와 그 차이를 특정한다. `static batching`과의 충돌 여부도 확인한다.

read-only 조사. 측정·코드 변경 없음.

## 배경

관련 TASK:

- [TASK37](TASK37.md)·[TASK38](TASK38.md)·[TASK42](TASK42.md) — related work와 서지
  정리. 이 조사는 그 위에 **용어** 축을 추가한다
- [TASK08](TASK08.md) — `kvcache_num_blocks = batch_size`. 우리 용어가 담아야 할
  자원 축의 근거
- [TASK12](TASK12.md)·[TASK13](TASK13.md) — `[BUCKET]` step 관측. §3의 "iteration
  단위로 계속 batching한다"의 직접 증거
- [TASK48](TASK48.md) — 자료 출처를 확인하지 않고 그럴듯하게 채운 실패(F-1). 이
  조사에서 인용 문장을 전부 1차 출처에서 직접 가져온 이유다

## 시작 상태

- Git commit: `b7eb0eb`
- `git status --short`: `?? .idea/`만
- device 접근·측정·설치 없음

## 수행 내용

1. 후보 용어 7종(`static-graph`, `AOT-compiled`, `fixed-shape`, `static-shape`,
   `compiled inference`, `graph-captured`, `compiler-scheduled`)으로 web 검색했다.
2. **채택한 정의 문장은 전부 1차 출처에서 직접 가져왔다** — arXiv abs/HTML, 벤더
   공식 문서, 이 host의 `site-packages` 소스. 검색 요약에만 나오고 1차 출처에서
   확인하지 못한 문장은 표에 넣지 않았다.
3. 각 용어가 **그래프 실행만** 가리키는지 **자원 배분까지** 포함하는지 분류했다.
4. `static batching`의 유통되는 두 뜻을 확인하고 우리 substrate에 적용했을 때의
   오독을 특정했다.
5. 결과를 [EXECUTION_MODEL_TERMS.md](EXECUTION_MODEL_TERMS.md)에 정리했다.

## 변경된 파일

- `docs/research/EXECUTION_MODEL_TERMS.md` (신규)
- `docs/research/TASK51.md` (신규)
- `docs/research/INDEX.md` (갱신)

논문 원고(`paper/`)는 이번에 고치지 않았다 — 용어 반영 여부는 Advisor 판단 사항이다.

## 실험 또는 검증 방법

측정 없음. 검증은 **1차 출처 확인 하나**다. 표에 넣은 정의 문장 5건을 전부 원문
페이지에서 직접 받아 확인했고, 확인하지 못한 것은 `UNKNOWN`으로 남겼다.

## 결과

- `requested_condition` — 6개 학회(OSDI/SOSP/MLSys/ASPLOS/ATC/EuroSys) 최근 3년의
  용어 조사
- `observed_condition` — **그 6개 학회에서 1차 출처로 확인한 논문은 1편**(llm.npu,
  ASPLOS '25)뿐이다. 나머지 근거는 arXiv 프리프린트 3편과 벤더 공식 문서 4건,
  구현 소스 1건이다. keyword 검색이지 proceedings 전수 조사가 아니다
- `condition_reached` — **`PARTIAL`**. 용어 표·범위 구분·충돌 확인·근접 용어 판정은
  모두 산출했으나, "6개 학회 최근 3년"이라는 모집단은 충족하지 못했다

### 용어와 범위 (요약 — 전체 표는 [EXECUTION_MODEL_TERMS.md](EXECUTION_MODEL_TERMS.md))

| 용어 | 출처 | 발표처 | 그래프·shape | 자원 배분 |
|---|---|---|---|---|
| `static shapes` | llm.npu, arXiv:2407.05858 | **ASPLOS '25** | ○ | ✕ |
| `fixed at compile time` / `bucketing` | AWS Neuron | 벤더 문서 | ○ | ✕ |
| `static input shape` | AWS Neuron autobucketing | 벤더 문서 | ○ | ✕ |
| `static model` | AWS Neuron `trace()` | 벤더 문서 | ○ | **△** |
| `dynamicity` / recompilation | Intel Gaudi | 벤더 문서 | ○ | ✕ |
| `bucketing` | LENS, arXiv:2606.18042 | arXiv | ○ | ✕ |
| `cudagraph capture sizes` | vLLM `config/compilation.py` | 구현 소스 | ○ | **△** |
| `static pre-allocation` | ODMA, arXiv:2512.09427 | arXiv | ✕ | **○** |

**확인된 용어들은 그래프·shape 축과 자원 축으로 갈리며, 둘을 하나로 묶어 부르는
확립된 명칭을 찾지 못했다.**

후보 4종(`AOT-compiled`, `compiled inference`, `graph-captured`, `compiler-scheduled`)은
6개 학회 최근 3년에서 이 실행 모델의 *명칭*으로 쓰인 1차 출처를 찾지 못했다.
`UNKNOWN`. (Groq TSP 계열의 `statically scheduled`는 **명령 타이밍**의 정적 스케줄링
이고 ISCA 2020으로 지정 범위 밖이다.)

### `static batching` 충돌 — 실재한다

두 뜻이 동시에 유통된다.

- **(가) 주류** — batch 구성이 그 batch의 수명 동안 고정. continuous batching의
  반대말. Orca(OSDI '22)는 이를 `request-level scheduling`, 자신의 대안을
  `iteration-level scheduling`이라 부른다
- **(나) 느슨한 용법** — batch 크기 hyper-parameter가 고정(arXiv:2503.05248).
  이쪽이 우리 용법에 가깝다

**우리 substrate를 `static batching`이라 부르면 (가)로 읽혀 사실과 반대가 된다.**
이 substrate는 compile 시점에 고정된 상한 `batch_size` *안에서* **iteration 단위로
계속 batching한다** — `[BUCKET]` 로그의 `request_nums`가 step마다 달라지는 것이 그
직접 증거다([TASK12](TASK12.md), [TASK13](TASK13.md)). 고정된 것은 batch **구성**이
아니라 batch **상한과 그에 묶인 KV pool**이다.

### 근접 용어 판정

**가장 가까운 기존 용어는 `static shapes`** (llm.npu, ASPLOS '25 — 6개 학회에서 1차
출처로 확인한 유일한 용례).

**차이 (한 줄)**: `static shapes`는 텐서 shape만 고정한다고 말하는 반면, 우리의
`compile-time-static serving substrate`는 그 위에 **서빙 수준 자원 배분** — compile
인자 `batch_size`가 `kvcache_num_blocks`를 정하고([TASK08](TASK08.md)) 그것이 동시
상주 세션 수와 캐시 생존을 정하는 사슬 — 까지 compile 시점에 고정된다는 것을 담는다.

## 핵심 발견

1. **`universal` — 이 실행 모델을 그래프와 자원 양쪽으로 부르는 확립된 명칭이
   문헌에 없다.** 확인된 용어는 shape 축(다수)과 자원 축(`static pre-allocation`)으로
   갈린다. 명칭 부재 자체가 이 연구가 선 자리의 방증이며, 논문에서 용어를 정의하고
   쓸 근거가 된다.
2. **`universal` — `static batching`은 우리 실행 모델의 이름으로 쓸 수 없다.**
   주류 뜻(batch 수명 동안 구성 고정)으로 읽히면 사실과 반대가 된다. 이 substrate는
   compile 고정 상한 안에서 iteration 단위 batching을 한다.
3. **`class` — compile 시점 고정을 자원까지 확장해 말하는 벤더 문장이 이미 존재한다.**
   AWS Neuron의 "static model … will consume a predictable amount of Neuron device
   memory"가 그것이다. 형태가 클래스인 이유: shape 고정이 곧 버퍼 배치 고정으로
   이어지는 것은 특정 구현이 아니라 AOT 컴파일 범주의 성질이다. **다만 그 문장의
   자원 축은 "모형 하나의 메모리 발자국"이지 서빙 수준 pool 크기가 아니므로, 우리가
   담는 범위와 같지 않다.**

## 해석

- 발견 1은 **용어를 새로 만들 근거**이지 **새 기여의 근거는 아니다.** 명칭이 없다는
  것과 현상이 연구되지 않았다는 것은 다르며, 후자는 [RELATED.md](../../paper/RELATED.md)가
  이미 다룬다.
- `static shapes`를 근접 용어로 고른 것은 **의미의 근접**이 아니라 **범위의 포함
  관계** 때문이다. 우리 용어가 그것의 상위 개념이므로, 논문에서는 `static shapes`를
  인용해 정의하고 그 위에 자원 축을 명시적으로 얹는 형태가 자연스럽다.

## 확인되지 않은 사항

- Orca(OSDI '22) 본문의 `static batching` 사용 여부 — USENIX가 403으로 차단. `UNKNOWN`
- 6개 학회 최근 3년의 **전수** 조사는 하지 않았다. 확인된 학회 논문 1편은 "그 용어가
  드물다"의 증거가 아니라 "이 검색으로는 하나만 나왔다"의 기록이다
- `AOT-compiled` / `compiled inference` / `graph-captured` / `compiler-scheduled`의
  학회 용례 — `UNKNOWN`
- LENS(arXiv:2606.18042)·ODMA(arXiv:2512.09427)의 학회 게재 여부 — comments에 기재
  없음. `UNKNOWN`

## 실패 / 무효 시도

- USENIX 페이지(Orca abstract, PDF) 자동 조회가 **403**으로 두 번 실패했다. 우회하지
  않고 `UNKNOWN`으로 남겼다.
- vLLM 공식 docs 페이지가 **429**로 실패해, 대신 이 host의 `site-packages` 소스에서
  같은 사실을 확인했다(더 나은 1차 출처다).

## 연구 원칙에 미치는 영향

없음. 다만 [TASK48](TASK48.md)의 교훈을 이 조사에 그대로 적용했다 — **인용 문장은
1차 출처에서 직접 가져오고, 확인하지 못한 것은 문장 대신 `UNKNOWN`으로 남긴다.**
검색 요약이 그럴듯하게 만들어 준 문장을 표에 넣지 않았다.

## 다음 작업

제안만 한다. 사용자 지시 없이 실행하지 않는다.

1. **결정 항목(Advisor·사용자 몫): 논문에서 실행 모델을 무엇이라 부를지.** 근접
   용어와 차이는 이 TASK가 특정했으나 명칭 채택은 판단 사항이다.
2. 채택하면 §I·§II의 용어를 통일하고 `refs.bib`에 llm.npu·ODMA 서지를 추가한다
   (현재 `refs.bib`에 없다).
3. 6개 학회 전수 조사가 필요하다면 proceedings 목록 기반으로 다시 해야 한다.

## 재현 정보

- 선등록 commit: **해당 없음** — 측정이 없는 문헌 조사다
- 시작 commit: `b7eb0eb`
- 조사 일자: 2026-09-01. web 검색 결과는 시점 의존적이다
- 1차 출처 URL 전체와 확인한 인용 문장은
  [EXECUTION_MODEL_TERMS.md](EXECUTION_MODEL_TERMS.md)에 있다
- 로컬 1차 출처: `/usr/local/lib/python3.10/dist-packages/vllm/config/compilation.py`
  (`vllm 0.22.0+cpu`)
- 예산: 측정 0, serving lifecycle 0, 재compile 0, 설치 0
