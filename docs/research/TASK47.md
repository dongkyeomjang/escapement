# TASK47 — 논문 환경 절을 위한 실측 환경 명세

## 상태

DONE

측정 없음(read-only 조사). [ENVIRONMENT.md](ENVIRONMENT.md)를 신설해 하드웨어·소프트웨어·모델·관측·워크로드를 **현물에서 재확인**했다. 기존 서술과의 불일치 **5건**을 찾았고 **그중 1건은 투고 전 반드시 고쳐야 하는 사실 오류**다. 지시대로 수정하지 않고 보고만 한다.

## 판정

| 항목 | 결과 |
|---|---|
| 산출물 | [ENVIRONMENT.md](ENVIRONMENT.md) 단일 문서, 명세표 형식 |
| 재확인 방식 | 전 항목을 **지금 이 서버의 명령 출력**으로 확인. 과거 TASK 전사 없음 |
| 불일치 | **5건** (F-1 중대, F-2–F-5) |
| `UNKNOWN` | **7건** (전부 사유 명시) |
| 부수 효과 | 없음 — serving 기동 0, compile 0, 파일 수정 0(신규 문서 2건 외) |

## 날짜

2026-08-28

## 목적

논문의 환경 절을 사용자가 쓸 수 있도록 **근거를 되짚을 수 있는 형태로** 환경을 명세한다. 원칙은 "기록을 전사하지 않고 현물에서 다시 잰다"이며, 그래야 기록과 현물의 차이 자체가 산출물이 된다.

## 배경

관련 TASK: [TASK05](TASK05.md)(초기 inventory), [TASK06](TASK06.md)·[TASK08](TASK08.md)(compile·KV accounting), [TASK12](TASK12.md)(patch), [TASK31](TASK31.md)(trace 출처), [TASK46](TASK46.md)(§II-D trace 문단을 쓴 TASK — F-1의 대상).

## 시작 상태

- Base commit: `bf6dbd3` ([TASK46](TASK46.md), **미push 상태**)
- read-only 조사. 측정·compile·serving 기동 0

## 수행 내용

A(하드웨어) → B(소프트웨어) → C(모델·compile) → D(관측) → E(워크로드) → F(정합) 순으로 명령을 실행하고 출력 원문과 함께 기록했다. 확인 불가 항목은 추정하지 않고 `UNKNOWN`과 사유를 남겼다.

## 변경된 파일

- `docs/research/ENVIRONMENT.md`(신규)
- `docs/research/TASK47.md`(신규), `docs/research/INDEX.md`

## 실험 또는 검증 방법

측정 없음. 사용한 명령은 `hostname`, `cat /sys/class/dmi/id/*`, `cat /etc/os-release`, `uname -r`, `python3 --version`, `lscpu`, `free -g`, `df -h`, `lsblk`, `rbln-smi`, `rbln-stat`, `modinfo`, `lsmod`, `pip list`, `importlib.metadata.version()`, artifact `config.json`·`rbln_config.json` 읽기, `os.walk` 크기 합산, `apply.sh status`, `sha256sum`, `load_mix()` 재계산, script `grep`.

## 결과

### 관측 1 — 하드웨어가 기록과 일치한다

`rbln-smi` 출력에서 **visible device 32개, 제품명이 붙는 그룹 8개, device당 15.7 GiB**를 재확인했다 — [TASK05](TASK05.md)의 재-inventory와 같다. KMD 3.2.2.

새로 기록된 것: 서버가 **Supermicro AS -4125GS-TNRT2**, host CPU가 **AMD EPYC 9254 24-Core × 2 socket(48 core / 96 thread)**, RAM **1,511 GiB**, 루트 볼륨 876 GB다. 이 넷은 과거 TASK에 없던 값이다.

### 관측 2 — 패키지 표시명과 배포명이 다르다

`pip list`는 **`vllm_rbln`**(밑줄)로 표시하고 `importlib.metadata`는 **`vllm-rbln`**(붙임표)로 조회된다. 처음에 `pip list | grep`로 잡으려다 놓쳤고, 배포명 기준 조회로 다시 확인했다. **명세표에는 배포명과 조회 방법을 함께 적었다.**

`rebel-compiler 0.11.1.post1`이 새로 기록됐다 — compile 도구 패키지이며 과거 TASK가 버전을 남기지 않았다.

### 관측 3 — artifact 7종이 전부 기록과 일치한다

크기를 `os.walk` 바이트 합으로 재계산해 생성 TASK의 기록과 대조했다.

| artifact | 실측 | 기록 | 일치 |
|---|---|---|---|
| b1 | 9.083 GiB | 9.083 ([TASK06](TASK06.md)) | ✓ |
| b8-mb | 11.501 | 11.501 ([TASK10](TASK10.md)) | ✓ |
| b8-mb6 | 12.306 | 12.306 ([TASK23](TASK23.md)) | ✓ |
| b16-batchonly | 12.378 | 12.378 ([TASK35](TASK35.md)) | ✓ |
| b16-mb16 | 13.202 | 13.202 ([TASK34](TASK34.md)) | ✓ |
| b24-mb24 | 13.259 | 13.259 ([TASK40](TASK40.md)) | ✓ |
| b32-mb32 | 13.320 | 13.320 ([TASK40](TASK40.md)) | ✓ |

**`kvcache_num_blocks == batch_size`가 7종 전부에서 성립**한다 — [TASK08](TASK08.md)이 source로 판정한 관계가 실물 artifact 7개에서 확인된 셈이다. `kvcache_block_size`는 전부 8,192(= `max_seq_len`).

### 관측 4 — trace 출처가 논문 서술과 다르다 (F-1)

이 조사의 가장 중요한 산출이다. [TASK46](TASK46.md)이 §II-D에 쓴 문장은

> a trace of coding-agent sessions **collected by the authors from their own use** of two agent front-ends, **instrumented at the client**

인데, [TASK31](TASK31.md)의 기록과 `src/continuum/workload/tools.py`의 docstring은 둘 다

> legacy 저장소가 **공개(public) coding-agent trace**에서 자체 재계산한 산출물. **원 gz는 접근 불가**

라고 적는다. **저자가 수집한 것이 아니다.** 파급이 하나 더 있다 — 같은 문단의 비공개 사유("저자의 작업 세션 prompt·출력이라 제3자 자료 없이는 공개 불가")도 그 전제 위에 서 있어 함께 성립하지 않는다. 실제 제약은 **원자료가 우리에게도 없다**는 것이다.

지시문이 F를 보고 전용으로 한정했으므로 **고치지 않았다.** 다만 이것은 문체가 아니라 **자료 출처 진술**이므로 이 상태로 투고되면 안 된다.

### 관측 5 — 나머지 불일치 4건

| # | 내용 |
|---|---|
| F-2 | "665,453 records"가 rows를 가리키는데 문맥은 도구 호출을 말한다. **tool call은 743,819**로 다른 수다 |
| F-3 | `vllm` 버전이 §I에서는 `0.22.0`, §II에서는 `0.22.0+cpu`. 실측은 **`0.22.0+cpu`** |
| F-4 | `num_devices`를 "tensor parallel 정도"로 부르는 서술이 있으나 artifact 키는 `num_devices`이고 `tensor_parallel_size`는 없다. 두 개념의 동치 여부는 `UNKNOWN` |
| F-5 | "trace of 43 tools"의 43은 **sampler가 cap·제외 후 채택한 수**이며 trace 전체 종수가 아니다. 전체 종수는 `UNKNOWN` |

### 관측 6 — trace 재계산으로 확인한 것

`load_mix(cap_s=60)`을 다시 실행해 **도구 43종**을 재확인했다. `summary.json`에서 rows 665,453 / tool calls 743,819 / sessions 8,058, latency 출처 분할 wall 397,527 · internal 345,523 · none 769(합이 tool call 수와 일치)를 읽었다. 분포 재구성은 **적합이 없고** 측정된 분위수를 정확히 지나며, human-in-the-loop 도구 4종(`AskUserQuestion` 등)은 "도구가 아니라 사람을 기다리는 것"이라 제외돼 있다.

## 핵심 발견

1. **`universal` — "기록을 전사하지 말고 현물에서 다시 재라"는 지시가 실제로 오류를 잡는다.** 전사했다면 F-1은 영원히 남았을 것이다. 그 문장은 두 TASK 전에 내가 썼고, 그때는 근거를 확인하지 않고 그럴듯한 서사를 채웠다.
2. **`universal` — 자료 출처는 다른 사실보다 검증 우선순위가 높다.** 숫자가 틀리면 정오표로 고치지만 출처가 틀리면 연구 윤리 문제가 된다. **환경 명세에서 가장 먼저 확인할 항목이 그것이다.**
3. **`universal` — 같은 대상을 세는 서로 다른 수는 이름이 비슷할수록 위험하다.** rows(665,453) · tool calls(743,819) · sessions(8,058)이 한 문장 안에서 섞였다(F-2). 명세표에 셋을 나란히 둔 이유다.
4. **`stack` — `kvcache_num_blocks == batch_size`가 artifact 7종 전부에서 성립한다.** source 판정([TASK08](TASK08.md))이 `batch_size` 1·8·16·24·32의 실물에서 확인됐다.

## 해석

- **(해석)** F-1이 [TASK46](TASK46.md)에서 들어왔다는 점이 뼈아프다. 그 TASK의 지시는 "trace 출처 문단 신설: 수집 주체·환경·기간·규모"였고, 나는 규모(665k/8,058/43)는 자료에서 확인했지만 **수집 주체는 확인하지 않고 그럴듯하게 채웠다.** 확인한 값과 채운 값이 한 문단에 섞이면 독자는 구별할 수 없다.
- **(해석)** F-4의 `num_devices` 대 tensor parallel은 사소해 보이지만 논문이 "four devices per model instance"라고 쓰는 근거다. **키 이름만 확인됐고 그것이 tensor 분할을 뜻하는지는 확인하지 못했다** — 그대로 `UNKNOWN`으로 뒀다.
- **(해석)** 이 문서는 논문 환경 절의 재료이지 초고가 아니다. 지시대로 산문을 쓰지 않았고, 각 값에 (값, 명령, 출력)을 붙여 사용자가 문장을 쓸 때 근거를 되짚게 했다.

## 확인되지 않은 사항

`UNKNOWN` 7건은 [ENVIRONMENT.md](ENVIRONMENT.md) 말미에 사유와 함께 표로 있다 — NPU 세대명, 커널 모듈, 스토리지 매체, 파라미터 수 재계산, `num_devices` 동치, trace 전체 도구 종수, hostname 이력.

## 실패 / 무효 시도

없다. `pip list | grep`로 `vllm-rbln`을 놓친 것을 배포명 조회로 바로잡았다(관측 2).

## 연구 원칙에 미치는 영향

1. **환경 명세는 기록 전사가 아니라 현물 재확인으로 만든다.** 값·명령·출력 3요소를 함께 남긴다.
2. **자료 출처는 가장 먼저 확인하고, 확인하지 못했으면 문장을 쓰지 않는다.** 규모는 확인하고 출처는 채우는 혼합이 가장 위험하다.
3. **비슷한 이름의 서로 다른 카운트는 나란히 적는다.**

## 다음 작업

1. **F-1 정정** — Advisor·사용자 판정 후. **투고 전 필수.**
2. F-2–F-5 판정 및 반영.
3. 이월: 첫 Overleaf 빌드, 그림 육안 검수, 소속 영문 명칭.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `bf6dbd3`
- 사용 명령: [ENVIRONMENT.md](ENVIRONMENT.md)의 각 표 "확인 명령" 열
- 예산: serving 기동 **0회**, 재compile **0회**, device **조회만**(상태 읽기), 설치 **0건**
