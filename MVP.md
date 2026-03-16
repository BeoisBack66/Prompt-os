# Prompt OS — MVP 기획서

---

## 1. 제품 개요

**Prompt OS**는 ChatGPT·Claude 사용자가 입력하는 프롬프트를 자동으로 수집·분석·개선하는 개인용 도구다.
별도의 조작 없이 브라우저 확장 프로그램이 백그라운드에서 프롬프트를 캡처하고, 로컬 서버가 품질을 평가해 사용자에게 피드백을 돌려준다.

---

## 2. 해결하는 문제

| 문제 | 설명 |
|------|------|
| 프롬프트 유실 | 좋은 프롬프트를 따로 저장하지 않으면 사라짐 |
| 품질 인식 부재 | 어떤 프롬프트가 좋은지 기준이 없음 |
| 패턴 파악 불가 | 내가 AI를 어떻게 쓰는지 돌아볼 수단이 없음 |
| 재사용 불편 | 좋은 프롬프트를 템플릿화하는 과정이 번거로움 |

---

## 3. 핵심 기능 (현재 구현 완료)

### 3-1. 자동 캡처
- ChatGPT(`chatgpt.com`), Claude(`claude.ai`) 지원
- Enter 키 전송 + 버튼 클릭 전송 모두 감지
- SPA 네비게이션 대응 (새 대화 시작 시 자동 재연결)
- 2초 쿨다운으로 중복 저장 방지

### 3-2. 민감 정보 필터링
자동으로 아래 항목 포함 프롬프트를 차단:
- 비밀번호·패스워드
- API 키, Bearer 토큰, 개인키
- 카드번호, 주민등록번호, SSN

### 3-3. 카테고리 자동 분류
| 카테고리 | 예시 |
|----------|------|
| coding | 코드 작성, 알고리즘 구현 |
| debugging | 오류 수정, 버그 분석 |
| writing | 글 작성, 이메일, 에세이 |
| summarization | 요약, 핵심 정리 |
| translation | 번역 |
| research | 설명, 개념 학습 |
| learning | 튜토리얼, 예시 요청 |
| math | 계산, 수식, 확률 |
| brainstorming | 아이디어, 기획 |

### 3-4. 품질 점수 시스템 (100점 만점)

기존 "길이" 기준을 폐기하고, 실제 프롬프트 품질을 반영하는 5개 기준으로 재설계:

| 항목 | 배점 | 판단 기준 |
|------|------|-----------|
| 명확한 요청 동사 | 20점 | 설명해줘, explain, analyze 등 명확한 행위 동사 포함 여부 |
| 맥락/배경 | 20점 | 현재 상황, 배경 정보, 예시 포함 여부 |
| 제약 조건 | 20점 | "단,", "~없이", "쉽게", "이내로" 등 범위·방식 제한 여부 |
| 출력 형식 | 20점 | JSON, 리스트, 단계별, 코드 블록 등 형식 지정 여부 |
| 구체성 | 20점 | 기술명, 버전, 숫자, 코드 인용 등 구체적 세부 사항 포함 여부 |

**등급:** A(80+) / B(60+) / C(40+) / D(40 미만)

**좋은 프롬프트 예시 (A등급):**
> "Python 3.11에서 pandas로 CSV 파일을 읽을 때 인코딩 오류가 발생해. 단 외부 라이브러리 없이 해결 방법을 단계별로 설명해줘."

**나쁜 프롬프트 예시 (D등급):**
> "이거 설명해줘"

### 3-5. 분석 기능
- **전체 요약**: 플랫폼별·카테고리별 분포, 평균 점수, 반복 표현 추출
- **주간 리포트**: 이번 주 vs 지난 주 비교, 최고 평점 프롬프트 Top3
- **유사 프롬프트 찾기**: Jaccard 유사도 기반
- **템플릿 자동 제안**: 반복 패턴 → `{{변수}}` 형태로 추출

### 3-6. 팝업 UI
- **최근 탭**: 최근 15개 프롬프트, 별점 평가(1~5), 개별 삭제
- **분석 탭**: 카테고리 분포, 평균 점수, 개선 제안
- **템플릿 탭**: 저장된 템플릿 목록, 신규 템플릿 등록

---

## 4. 기술 구조

```
[ChatGPT / Claude 브라우저]
        ↓  (MutationObserver로 textarea 감지)
[content.js — Chrome Extension]
        ↓  (chrome.runtime.sendMessage)
[background.js — Service Worker]
        ↓  (HTTP POST)
[FastAPI 서버 — localhost:8000]
        ↓
[SQLite DB — prompts.db]
```

| 레이어 | 기술 |
|--------|------|
| 브라우저 확장 | Chrome Manifest V3, Vanilla JS |
| 백엔드 서버 | Python FastAPI, uvicorn |
| 데이터베이스 | SQLite (aiosqlite) |
| 분석 엔진 | Python (regex, collections) |
| 팝업 UI | HTML/CSS/JS |

---

## 5. API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | /health | 서버 상태 확인 |
| POST | /prompts | 프롬프트 저장 |
| GET | /prompts | 프롬프트 목록 조회 |
| GET | /prompts/{id} | 단일 프롬프트 조회 |
| PATCH | /prompts/{id}/rating | 별점 업데이트 |
| DELETE | /prompts/{id} | 프롬프트 삭제 |
| GET | /search?q= | 프롬프트 검색 |
| GET | /templates | 템플릿 목록 |
| POST | /templates | 템플릿 저장 |
| DELETE | /templates/{id} | 템플릿 삭제 |
| GET | /analysis/summary | 전체 분석 요약 |
| GET | /analysis/weekly | 주간 리포트 |
| GET | /analysis/score/{id} | 단일 프롬프트 점수 |
| GET | /analysis/similar/{id} | 유사 프롬프트 |
| GET | /analysis/template-suggest/{id} | 템플릿 자동 제안 |

---

## 6. 실행 방법

```bash
# 1. 서버 실행
cd prompt-os/server
python -m uvicorn main:app --reload --port 8000

# 2. 확장 프로그램 설치
# chrome://extensions/ → 개발자 모드 ON → 폴더 로드 → extension/ 선택

# 3. API 문서 확인
# http://localhost:8000/docs
```

---

## 7. 향후 개선 방향

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 높음 | Claude Code / API 캡처 | 브라우저 외 인터페이스 지원 |
| 높음 | 점수 기반 개선 제안 자동화 | "이 프롬프트를 이렇게 바꾸면 A등급" |
| 중간 | LLM 기반 분류·채점 | 키워드 대신 AI가 직접 판단 |
| 중간 | 프롬프트 내보내기 | CSV / JSON 내보내기 |
| 낮음 | 다크/라이트 테마 | 팝업 UI 개선 |
| 낮음 | 팀 공유 기능 | 좋은 프롬프트를 팀원과 공유 |

---

*Last updated: 2026-03-16*
