# TASK48 — TASK47 불일치 정정: trace 출처를 사실로 되돌림

## 상태

DONE

측정 없음. [TASK47](TASK47.md)이 찾은 불일치 5건을 전부 정정했다. **F-1은 내가 [TASK46](TASK46.md)에서 확인 없이 채워 넣은 사실 오류였고**, 이 TASK는 그것을 고치면서 어떻게 들어왔는지도 함께 기록한다.

## 판정

| 항목 | 결과 |
|---|---|
| F-1 (trace 출처) | **정정.** 원 데이터셋을 특정·검증해 서지로 인용. "저자 수집"·프라이버시 사유 문장 삭제 |
| F-2 (규모 표기) | **정정.** 665,453 스텝 / 743,819 도구호출 / 8,058 세션을 구분해 병기 |
| F-3 (vllm 버전) | **정정.** `0.22.0+cpu`로 통일 |
| F-4 (`num_devices`) | **정정.** 해석어 제거, 키 이름과 뜻만 |
| F-5 (43종) | **정정.** "채택된 43종"으로 조건화 |
| 전수 동기화 | `paper/draft`·`paper/latex`·`CLAIMS.md`·`ENVIRONMENT.md` |
| 검증 | `check_claims` **50/50**, `[NEEDS-EVIDENCE]` **0**, 그림 177/177, 패키지 청결 4/4 |

## 날짜

2026-08-28

## 목적

[TASK47](TASK47.md)의 정합 점검이 논문 §II-D의 trace 출처 서술이 사실과 다름을 드러냈다. 지시문이 그 TASK를 보고 전용으로 한정했으므로 정정은 이 TASK가 한다.

## 배경

관련 TASK: [TASK47](TASK47.md)(불일치 발견), [TASK46](TASK46.md)(오류가 들어온 곳), [TASK31](TASK31.md)(워크로드 전환과 원 출처 기록), [TASK38](TASK38.md)(서지 1차 출처 확인 원칙).

## 시작 상태

- Base commit: `1234349` ([TASK47](TASK47.md))
- 측정 없음. serving 기동 0회, device 접근 0회, 설치 0건

## 수행 내용

1. legacy 저장소를 read-only로 읽어 **원 공개 trace의 정체·릴리스·라이선스**를 확인했다.
2. arXiv에서 서지를 1차 출처로 재확인했다.
3. §II-D를 사실대로 다시 쓰고, 실제 제약을 §IX 한계로 옮겼다.
4. F-2–F-5를 일괄 정정했다.
5. `CLAIMS.md`와 `ENVIRONMENT.md`를 동기화하고 상호 링크했다.

## 변경된 파일

- `paper/draft/02_background.md`, `09_limitations.md`, `01_introduction.md`
- `paper/CLAIMS.md`, `paper/latex/refs.bib`, `paper/latex/sections/*.tex`(재생성)
- `docs/research/ENVIRONMENT.md`
- `docs/research/TASK48.md`(신규), `docs/research/INDEX.md`

## 결과

### 관측 1 — 원 trace가 특정됐고 인용 가능하다

legacy `tasks/TASK31.md`의 후보 판정 표와 `experiments/analyze_tracelab.py`가 전부 기록하고 있었다.

| 항목 | 값 | 출처 |
|---|---|---|
| 데이터셋 | **TraceLab** (`uw-syfi/TraceLab`) | legacy TASK31 §1-1 |
| 논문 | **arXiv:2606.30560** — *TraceLab: Characterizing Coding Agent Workloads for LLM Serving*, Zhu, Jacob, Ma, Pan, Wang, Krishnamurthy, Kasikci (2026-06-29) | **arXiv abs 재확인** |
| 라이선스 | **CC BY 4.0**(데이터) / Apache-2.0(코드) | legacy TASK31 §1-1 |
| 사용 릴리스 | **v0.0.2** — 665,453 스텝 / 743,819 도구호출 / 8,058 세션 / 52명, Claude Code + Codex 실사용, 2025-09~2026-07 | legacy TASK31 §1-1·§7 |
| 무결성 | 다운로드 시 SHA256 `11ce51ec…`가 공표값과 일치함을 legacy가 기록 | legacy TASK31 §7 |
| 원 경로 | `/mnt/ssd/tracelab/syfi_coding_trace.jsonl.gz` — **현재 접근 불가** | `analyze_tracelab.py:28` |

**인용 가능하므로 서지 항목으로 넣었다**(`tracelab2026`). 라이선스가 CC BY 4.0이라 파생 분포를 공개하는 데 제약이 없고, 귀속 표시가 요구되는데 그것이 곧 인용이다.

### 관측 2 — arXiv 초록과 우리가 쓴 릴리스의 규모가 다르다

arXiv 초록은 **약 4,300 세션 / 35만 스텝 / 43만 도구호출**로 적는다. 우리가 쓴 **v0.0.2는 8,058 세션 / 665,453 스텝 / 743,819 도구호출**로 그보다 크다. 릴리스가 논문 이후 커진 것으로 보인다.

**그래서 논문에 버전을 명시했다** — "We use release v0.0.2, which contains …". 버전 없이 초록의 수를 인용했다면 우리 수치와 어긋났을 것이다. [ENVIRONMENT.md](ENVIRONMENT.md) §E에도 이 차이를 항목으로 남겼다.

### 관측 3 — latency 우선순위도 반대로 적혀 있었다

[TASK46](TASK46.md)의 문장은 "client's own wall clock where the front-end reports it and from the front-end's internal timing otherwise"였다. legacy `analyze_tracelab.py` 주석 ③은 **"effective = internal 있으면 internal, 없으면 wall"** 이다 — **우선순위가 반대**다. 새 문장은 "a runner-reported internal latency where present, and otherwise the wall-clock difference"로 고쳤다.

**F-1을 확인하지 않았다면 이것도 남았을 것이다.** 한 문단에 확인한 값과 채운 값이 섞이면 오류가 하나로 끝나지 않는다.

### 관측 4 — 정정 전후

**§II-D (before)**

> The population is a trace of coding-agent sessions **collected by the authors from their own use** of two agent front-ends, **instrumented at the client** … We do not release the raw records: they contain **the prompts and outputs of the authors' working sessions**, which cannot be published without disclosing unrelated third-party material.

**§II-D (after)**

> The population is derived from **TraceLab**, a public trace of day-to-day coding-agent usage released under CC BY 4.0. We use release v0.0.2, which contains 665,453 LLM steps, 743,819 tool calls and 8,058 sessions. … **We did not collect this trace**, and we do not recompute from the released archive: the gap sampler consumes a set of per-tool duration quantiles that an earlier stage of this project produced from the archive, and **the archive itself is no longer accessible to us**. … Section IX states the limitation this leaves.

**§IX에 실제 제약을 넣었다** — 프라이버시가 아니라 **원 아카이브 접근 불가로 분위수 산출을 재현할 수 없다**는 것이 진짜 한계다. 재현 가능한 것은 분위수 아래 전부이며 그것이 이 논문의 모든 측정이다.

### 관측 5 — F-2–F-5

| # | 정정 |
|---|---|
| F-2 | "665,453 records" → **"665,453 LLM steps, 743,819 tool calls and 8,058 sessions"** — 세 수를 구분해 병기 |
| F-3 | §I의 `vllm 0.22.0` → **`vllm 0.22.0+cpu`** (§II와 통일, 실측과 일치) |
| F-4 | "(four devices per model instance)" → **"built with `num_devices = 4`, the compile-time setting that fixes how many devices one model instance occupies"** — tensor parallel이라는 해석어를 쓰지 않고 키 이름과 그 뜻만 적었다 |
| F-5 | "a single code-agent trace of 43 tools" → **"reduced to the 43 tools that survive a human-in-the-loop exclusion and a 60 s cap — not to the trace's full tool vocabulary"** |

[CLAIMS.md](../../paper/CLAIMS.md)의 주장 2.3과 한계 1·3·4를 같은 내용으로 동기화하고 **[ENVIRONMENT.md](ENVIRONMENT.md)로 상호 링크**했다. `[NEEDS-EVIDENCE]`가 0이 됐다 — 배포 형식을 묻던 항목이 "분위수를 공개한다"는 확정 서술로 바뀌었기 때문이다.

### 관측 6 — F-1이 어떻게 들어왔는가

**은폐 없이 적는다.**

| 축 | 내용 |
|---|---|
| **발생** | [TASK46](TASK46.md). 지시는 "trace 출처 문단 신설: 수집 주체·환경·기간·규모"였다. **규모(665k / 8,058 / 43)는 자료에서 확인했고, 수집 주체는 확인하지 않고 그럴듯하게 채웠다.** legacy에 답이 있었고 한 번만 열어보면 됐다 |
| **왜 그럴듯했나** | `summary.json`의 `lat` 키가 `claude`·`codex`였다. 두 front-end 이름을 보고 **"저자가 두 도구를 쓰며 계측했다"는 서사가 자연스럽게 맞아떨어졌다.** 실제로는 TraceLab이 52명의 사용을 수집한 것이고, 두 이름은 그 데이터셋의 provider 구분이었다 |
| **왜 눈에 안 띄었나** | 같은 문단의 다른 값이 전부 맞았다. **확인한 값과 채운 값이 한 문단에 섞이면 독자도 저자도 구별하지 못한다** |
| **발견 경로** | [TASK47](TASK47.md)의 §F 정합 점검. "기록을 전사하지 말고 현물에서 다시 재라"는 지시가 없었다면 남았을 것이다 |
| **교훈** | **자료 출처는 규모보다 먼저 확인한다. 확인하지 못한 항목은 문장을 쓰지 말고 `UNKNOWN`으로 남긴다** — 빈칸은 눈에 띄지만 그럴듯한 채움은 띄지 않는다 |

파급 범위는 §II-D 한 문단과 그 문단이 근거를 대던 비공개 사유 문장이었고, **측정·수치·판정에는 영향이 없다.** 도구 지연 분포 자체는 처음부터 같은 자료에서 왔다.

## 핵심 발견

1. **`universal` — 확인한 값과 채운 값을 한 문단에 섞으면 오류가 국소에 머물지 않는다.** F-1에 딸려 latency 우선순위(관측 3)까지 반대로 적혀 있었고, 비공개 사유 문장은 틀린 전제 위에 세워져 있었다. **문단 단위로 출처를 대는 습관이 필요하다.**
2. **`universal` — 그럴듯한 채움은 빈칸보다 위험하다.** `UNKNOWN`은 검토에서 눈에 띄지만 매끄러운 서사는 띄지 않는다. 이번에는 데이터의 부수적 특징(`claude`·`codex` 키)이 틀린 서사를 **지지하는 것처럼** 보이기까지 했다.
3. **`universal` — 데이터셋은 버전으로 인용한다.** arXiv 초록의 규모와 우리가 쓴 릴리스가 다르다(관측 2). 버전 없이 인용했다면 우리 수치가 논문의 수치와 어긋나 보였을 것이다.
4. **`universal` — 정정은 원 진술과 함께 남긴다.** [ENVIRONMENT.md](ENVIRONMENT.md) §F의 F-1 항목을 지우지 않고 "정정됨" 행을 덧붙였다. 무엇이 틀렸었는지가 지워지면 같은 실수를 막을 수 없다.

## 해석

- **(해석)** 이 오류가 **측정을 건드리지 않았다**는 점은 다행이지만 위안으로 삼을 것은 아니다. 자료 출처 진술은 독자가 검증할 수 없는 종류의 주장이고, 그래서 신뢰로만 지탱된다. **검증 불가능한 진술일수록 저자가 스스로 검증해야 한다.**
- **(해석)** legacy를 read-only로 읽는 것이 [TASK31](TASK31.md) 이래 규칙이었는데, 그 규칙이 "읽지 않는다"로 잘못 작동한 면이 있다. **수정 금지와 열람 금지는 다르다.** 이번에 legacy TASK31 한 파일에 필요한 것이 전부 있었다.
- **(해석)** CC BY 4.0이라 파생 분포 공개에 제약이 없다는 것은 정정의 부수 소득이다. 틀린 서술 아래에서는 "저자 세션이라 공개 불가"였는데, 사실은 **공개해도 되고 귀속만 하면 된다.**

## 확인되지 않은 사항

- **원 아카이브 재접근** (`UNKNOWN`) — `/mnt/ssd/tracelab/…`는 이 host에서 접근할 수 없다. 분위수 산출을 재현하려면 다시 받아야 한다.
- **trace 전체의 도구 종수** (`UNKNOWN`, 이월) — 논문은 "채택된 43종"으로 조건화했다.
- **v0.0.2와 arXiv 초록 규모 차이의 사유** (`UNKNOWN`) — 릴리스가 커진 것으로 보이나 확인하지 못했다.
- 이월: 첫 Overleaf 빌드, 그림 육안 검수, 소속 영문 명칭.

## 실패 / 무효 시도

**이 TASK 자체의 실패는 없다.** 다만 이 TASK가 고친 것이 [TASK46](TASK46.md)의 실패이며, 그 성격을 관측 6에 적었다.

## 연구 원칙에 미치는 영향

1. **자료 출처는 규모·형식보다 먼저 확인한다.** 확인 못 하면 문장을 쓰지 않고 `UNKNOWN`으로 남긴다.
2. **한 문단 안에서 확인한 값과 미확인 값을 섞지 않는다.** 섞였다면 미확인 부분을 표시한다.
3. **데이터셋은 릴리스 버전과 함께 인용한다.**
4. **legacy 수정 금지는 열람 금지가 아니다.** 필요한 provenance가 거기 있으면 읽는다.
5. **정정할 때 원 진술을 지우지 않는다.**

## 다음 작업

1. 첫 Overleaf 빌드와 그림 육안 검수 (이월).
2. 소속 영문 명칭, IEEE AI 고지 규정 대조 (이월).
3. 분위수 공개 형식 결정 — 논문이 "We release the quantiles"라고 적었으므로 실물이 필요하다.

## 재현 정보

- 선등록 commit: **해당 없음** (측정 없는 TASK)
- Base commit: `1234349`
- legacy 조회(read-only): `tasks/TASK31.md`, `experiments/analyze_tracelab.py`, `notes/*.md`
- 서지 재확인: arXiv abs 2606.30560 (2026-08-28)
- 검증: `check_claims.py` 50/50·NEEDS-EVIDENCE 0, `verify_figures.py` 177/177, `make_package.sh` 4/4
- 예산: serving 기동 **0회**, 재compile **0회**, device 접근 **0회**, 설치 **0건**
