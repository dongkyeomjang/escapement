# TASK70 — Stage 3 개시: arXiv 기준점 tag, 결정 4 개정, 결정 6(투고 타깃) 신설

## 상태

DONE

## 날짜

2026-09-29

## 목적

Advisor 지시문 01(2026-09-29) 작업 A를 집행한다. arXiv 제출본이 참조하는 저장소 상태에 기준점을 남기고, 연구 단계를 **Stage 3: 해석적 모형과 교차 기판 검증**으로 연다. 그에 맞춰 GPU(A6000)의 위치를 "리뷰 요구 시 1실험"에서 **논문의 두 번째 기판**으로 격상하고(결정 4 개정), 투고 타깃을 **ACM SIGMETRICS 2027**로 기록한다(결정 6 신설).

**측정 0, device 접근 0, compile 0, 코드 변경 0.** 문서와 local tag만 바꿨다.

## 배경

관련 TASK:

- [TASK29](TASK29.md) — 기전 3개 절제와 결정 4의 1차 개정(조건부 이연). GPU 측 예측(격자 법칙이 `max_num_seqs=8`의 cudagraph 격자 `[1,2,4,8,16]`에서 소멸하지 않음, LRU·block 단위 회수에서 생존 문턱이 token 총량의 함수가 됨, chunked prefill에서 정지 0·device time +3–10 %)을 **GPU 측정 전에** commit `d67b19d`(2026-08-22 17:58:48 +0900)로 기록했다. 이 저장소에는 그 뒤로도 GPU 측정이 없다
- [TASK37](TASK37.md) — `paper/VENUES.md`에 MLSys 2027을 주 타깃으로 권고했다
- [TASK65](TASK65.md) — 논문 원고를 저장소에서 제거했다. 원고는 사용자 소관이다
- [TASK69](TASK69.md) — `3e195aa`, arXiv 원고가 기준으로 삼는 commit

## 시작 상태

- branch `main`, HEAD `3e195aa66ae79458031e1c0c92709b1858f427b5`(TASK69), `git status --short`: `?? .idea/`만
- 기존 tag 없음(`git tag -l` 빈 출력)

## 수행 내용

1. **local annotated tag `arxiv-v1`** 을 `3e195aa`에 붙였다. 메시지: "arxiv-v1: arXiv 제출본 원고가 참조하는 저장소 상태 (Escapement, 3e195aa, TASK69 시점). 원고 텍스트는 저장소 밖에서 관리된다. Stage 3 개시 직전 기준점 (TASK70)." **push하지 않았다.**
2. INDEX "현재 상태"에 **Stage 3** 단락을 열었다(목적·범위·선행 조건).
3. **결정 4를 개정**했다 — GPU(A6000)를 논문의 두 번째 기판으로 격상, 예정 범위 (a) 생존 곡선(LRU·block 단위 회수), (b) `max_num_seqs` 축의 격자 정렬, (c) 설정 선택 예측. **GPU 서버 작업은 여전히 별도 지시문 발행 전까지 시작하지 않는다.** [TASK29](TASK29.md)의 GPU 측 예측이 측정 전 commit된 기록(`d67b19d`)임을 명시했다. 개정 전 조항은 지우지 않고 남겼다.
4. **결정 6(투고 타깃)을 신설**했다 — SIGMETRICS 2027 winter 마감. 마감일 2027-01-11 AoE·초록 2027-01-04는 **제3자 집계 사이트 기준이며 공식 CFP 재확인 전까지 `UNKNOWN`**. double-anonymous 심사라 제출 시 익명 artifact 스냅샷이 필요하다.
5. `paper/VENUES.md` 머리와 "권고" 절 제목에 **대체 표시**만 붙였다. 기존 조사 내용은 지우지 않았다.

## 변경된 파일

- `docs/research/TASK70.md` (신규)
- `docs/research/INDEX.md` (현재 상태 Stage 3 단락, 가장 최근 TASK, Task Index 행, 사용자 결정 대기 절 머리, 결정 4 개정, 결정 6 신설, 후속 연구 6번 행)
- `paper/VENUES.md` (대체 표시 2곳, 내용 삭제 없음)
- git tag `arxiv-v1` (local, annotated, 파일 아님)

## 실험 또는 검증 방법

```bash
git tag -l                                  # 작업 전 빈 출력
git tag -a arxiv-v1 3e195aa -m "..."
git cat-file -t arxiv-v1                    # tag (annotated)
git rev-parse arxiv-v1^{commit}             # 3e195aa66ae79458031e1c0c92709b1858f427b5
```

## 결과

- `arxiv-v1` → `3e195aa66ae79458031e1c0c92709b1858f427b5`, 객체 종류 `tag`(annotated). remote에는 없다.
- `paper/VENUES.md`의 `대체됨` 표시 2곳, 기존 28행 본문 보존.

## 핵심 발견

없음. 측정·계산이 없는 기록 작업이다.

## 해석

- **GPU 격상의 의미**: 이 연구의 주장 가운데 `class` 태그가 붙은 것들(개수 문턱의 *형태*, 격자 정렬의 *형태*, 배타 prefill의 부호)은 지금까지 단일 기판에서 source 인용과 시뮬레이터 절제로만 뒷받침됐다. 두 번째 기판에서 **파라미터만 재고 결과를 사전 예측**하는 것이 그 태그를 검증하는 유일한 경로다. [TASK29](TASK29.md)의 예측이 측정 전에 commit돼 있다는 점은 그 검증이 사후 설명이 되지 않게 하는 자산이다.
- **SIGMETRICS와 Stage 3의 관계**: 측정 논문에서 모형 논문으로 넘어가려면 모형이 descriptor 파라미터만으로 계산돼야 한다. 결정 6이 Stage 3의 방향을 정한다.

## 확인되지 않은 사항

- SIGMETRICS 2027 winter 마감의 공식 일자·분량·artifact 규정: `UNKNOWN`(공식 CFP 미확인).
- A6000 서버의 소프트웨어 구성(vLLM 버전, CUDA, 모델 호환): 이 TASK 범위 밖, `UNKNOWN`.

## 실패 / 무효 시도

없음.

## 연구 원칙에 미치는 영향

- 원칙 4(CUDA semantics를 RBLN에 적용하지 않는다)는 역방향에도 적용된다 — **RBLN 상수를 GPU 예측에 옮기지 않는다.** GPU 예측은 GPU에서 잰 descriptor 파라미터로만 한다.
- 원칙 16(선등록)은 교차 기판 예측에서 특히 중요하다 — GPU 측 예측은 GPU 측정 전에 commit한다.

## 다음 작업

- 다음 번호 TASK — 해석적 모형 v0 정식화와 대조 계획 선등록(지시문 01 작업 B–D). 별도 TASK로 기록한다.
- GPU 서버 작업은 **별도 지시문 발행 전까지 시작하지 않는다.**

## 재현 정보

- tag: `git show arxiv-v1` (local)
- 선등록 commit: 해당 없음(측정·판정 없음)
