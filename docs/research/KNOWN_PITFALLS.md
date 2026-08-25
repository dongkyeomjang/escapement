# 알려진 함정 — 재발한 실수와 올바른 방식

이 문서는 **이 저장소에서 실제로 두 번 이상 일어났거나, 한 번이라도 측정을 무너뜨린** 실수를 모은다. 각 항목은 **발생 TASK**와 **올바른 방식 한 줄**을 갖는다.

**목적은 반성이 아니라 예방이다.** [CLAUDE.md](../../CLAUDE.md) 원칙 15가 "과거에 실패한 접근을 관련 TASK 확인 없이 반복하지 않는다"고 요구하는데, 실패가 36개 TASK에 흩어져 있으면 그 확인이 실질적으로 불가능하다. **새 script를 쓰기 전, 새 실행 경로를 만들기 전에 이 목록을 본다.**

---

## 1. 상대 경로 × 임시 디렉터리로 `cd`하는 실행기 — **2회**

| | |
|---|---|
| 발생 | [TASK06](TASK06.md)(첫 발생), [TASK40](TASK40.md)(재발, serving lifecycle 2회 낭비 후 재시도로 총 4회) |
| 증상 | `FileNotFoundError`. 또는 출력 artifact가 임시 디렉터리에 쓰여 run 종료와 함께 사라진다 |
| 원인 | [`experiments/npu/launch/run_isolated_python.sh`](../../experiments/npu/launch/run_isolated_python.sh)가 `mktemp -d`로 만든 디렉터리로 `cd`한 뒤 script를 실행한다. 호출자가 넘긴 상대 경로는 그 임시 디렉터리 기준으로 해석된다 |
| **올바른 방식** | **`run_isolated_python.sh`에 넘기는 모든 경로는 절대 경로로 만든다** (`"$REPO/$RUN/..."`). [`run_sweep.sh`](../../experiments/npu/stage2/run_sweep.sh)가 이미 그렇게 하고 있으므로 새 script는 그 인자 관례를 그대로 따른다 |

**[TASK40](TASK40.md)의 교훈**: 기존 script가 이미 푼 문제를 새 script에서 다시 만들었다. **같은 실행기를 쓰는 기존 script를 먼저 읽는다.**

## 2. process를 pattern으로 죽이거나 확인하기 — **3회**

| | |
|---|---|
| 발생 | [TASK09](TASK09.md)(pattern kill이 shell을 죽임), [TASK10](TASK10.md)(생존 오탐 3회), [TASK23](TASK23.md)(**6개 조합 연쇄 붕괴**) |
| 증상 | wrapper shell이 같은 pattern에 매칭돼 자기 자신을 죽이거나, 누수된 남의 server를 죽여 실패가 연쇄한다 |
| 원인 | `pgrep -f`·`ps \| grep \| head -1`의 pattern에 그 명령을 실행한 shell의 command line도 걸린다 |
| **올바른 방식** | **자기가 기동한 process는 자기가 받은 PID로 종료한다.** `SRV=$!` → `kill -TERM "$SRV"` → 유예 후 `kill -KILL`. 생존 확인은 PID·port·device memory·exit code로 교차 확인한다 |

**[TASK23](TASK23.md)의 교훈**: pattern 정리는 실패가 국소에 머물지 않고 **연쇄한다.**

## 3. 동시 실행 중 counter 증분으로 per-request 귀속하기 — **1회, 그러나 결과를 무효화**

| | |
|---|---|
| 발생 | [TASK17](TASK17.md) |
| 증상 | 층 2 `cached` 증분이 5,760·9,600처럼 **단일 요청이 낼 수 없는 값**을 보였고, 실제 성공 4건이 증분 기준으로 5건으로 보였다 |
| 원인 | 요청 전후로 `/metrics`를 긁는 사이에 **다른 요청이 진행**한다. 증분에 남의 기여가 섞인다 |
| **올바른 방식** | **동시 workload의 per-request 채널은 request id를 담은 로그다** — `[PFX]`·`[BUCKET]` 로그, 또는 응답에 실려 오는 `usage.prompt_tokens_details.cached_tokens`([TASK18](TASK18.md)에서 게이트 통과). counter 증분은 **집계 지표로만** 쓴다 |

## 4. 따옴표 없는 heredoc 안에서 문자열 치환 — **1회**

| | |
|---|---|
| 발생 | [TASK40](TASK40.md) (serving lifecycle 2회 추가 낭비) |
| 증상 | 파일을 고치는 script가 **아무것도 바꾸지 않고** "고쳤다"고 출력한다 |
| 원인 | `python3 - <<PYEOF`(따옴표 없음)에서 bash가 Python 소스 안의 `$RUN`·`$REPO`를 **먼저 확장**한다. 치환 대상 문자열이 파일 내용과 달라져 매칭에 실패한다 |
| **올바른 방식** | **파일을 고치는 heredoc은 `<<'PYEOF'`(따옴표)로 연다.** 경로는 `os.environ`으로 넘긴다. 그리고 **치환마다 `assert old in s`를 넣는다** — "고쳤다"는 출력은 증거가 아니다 |

## 5. 실행 중인 실험의 script 편집 — **2회**

| | |
|---|---|
| 발생 | [TASK23](TASK23.md)(bash가 부분 기록된 파일을 읽어 syntax error → server 누수 → 연쇄 붕괴), [TASK34](TASK34.md) |
| 증상 | 진행 중이던 조합이 중간에 죽고 server가 누수된다 |
| 원인 | bash는 script를 **실행 도중에 다시 읽는다.** 편집 중인 파일을 읽으면 부분 내용을 실행한다 |
| **올바른 방식** | **실행 중인 실험의 script를 편집하지 않는다.** 고칠 것이 있으면 run을 끝내고 고치거나, 새 파일로 만들어 다음 run부터 쓴다. 이 규칙은 이후 모든 선등록 문서의 "실행 절차" 절에 명시돼 있다 |

---

## 이 목록을 쓰는 법

1. **새 실행 script를 쓰기 전** — 항목 1·2·5를 본다.
2. **파일을 고치는 자동화를 쓰기 전** — 항목 4를 본다.
3. **새 관측 채널을 정의하기 전** — 항목 3을 본다.
4. **새 함정이 발생하면** — 해당 TASK의 "실패 / 무효 시도"에 먼저 기록하고, **재발했거나 측정을 무효화했으면** 이 문서에 항목을 추가한다.

**추가 기준**: 두 번 이상 발생했거나, 한 번이라도 측정 결과를 무효화·낭비시킨 것. 단순 오타나 일회성 실수는 넣지 않는다 — 목록이 길어지면 아무도 읽지 않는다.
