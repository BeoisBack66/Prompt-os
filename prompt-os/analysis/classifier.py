import re
from typing import Tuple, Optional

# Patterns that indicate sensitive information — matched prompts are filtered out
SENSITIVE_PATTERNS = [
    (r"password",                                  "contains password"),
    (r"비밀번호|패스워드",                          "contains password"),
    (r"api[_\s]?key",                              "contains API key"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "possible card number"),
    (r"\b\d{3}-\d{2}-\d{4}\b",                    "possible SSN"),
    (r"\b\d{6}-\d{7}\b",                           "possible Korean national ID"),
    (r"private[_\s]?key",                          "contains private key"),
    (r"개인키|비공개키",                            "contains private key"),
    (r"secret",                                    "contains secret"),
    (r"bearer\s+[a-z0-9\-._~+/]+=*",              "contains Bearer token"),
]

def filter_sensitive(prompt: str) -> Tuple[bool, Optional[str]]:
    lower = prompt.lower()
    for pattern, reason in SENSITIVE_PATTERNS:
        if re.search(pattern, lower):
            return True, reason
    return False, None

# Keyword lists include both English and Korean terms for bilingual matching
CATEGORIES = {
    "coding": [
        "code","function","class","bug","implement","script","python",
        "javascript","typescript","sql","algorithm","api",
        "코드","함수","클래스","버그","구현","스크립트","알고리즘","개발","프로그래밍","짜줘","작성해줘",
    ],
    "debugging": [
        "error","exception","traceback","fix","not working","fails","crash","issue","why does",
        "오류","에러","예외","수정","안 됩니다","안됩니다","크래시","왜","문제","고쳐","디버그","안되","실패",
    ],
    "writing": [
        "write","essay","blog","email","letter","draft","paragraph","article","story","edit","proofread",
        "작성","에세이","블로그","이메일","편지","초안","문단","글","이야기","교정","문장",
    ],
    "summarization": [
        "summarize","summary","tldr","key points","brief","shorten",
        "요약","핵심","간단히","짧게","정리","요점",
    ],
    "translation": [
        "translate","in french","in spanish","in korean","in japanese",
        "번역","영어로","한국어로","일본어로","중국어로","프랑스어로","스페인어로",
    ],
    "research": [
        "research","explain","what is","how does","overview","history of","compare","difference between",
        "설명","무엇","어떻게","개요","역사","비교","차이","알려줘","조사","연구","뭐야","뭔가요","란","이란",
    ],
    "learning": [
        "learn","teach","example","tutorial","practice","quiz",
        "배워","가르쳐","예시","튜토리얼","연습","퀴즈","공부","이해","개념","원리","학습",
    ],
    "math": [
        "calculate","solve","equation","integral","derivative","probability","matrix","formula","math",
        "계산","풀어","방정식","적분","미분","확률","행렬","수식","수학",
    ],
    "brainstorming": [
        "idea","brainstorm","suggest","creative","think of","what if",
        "아이디어","브레인스토밍","제안","창의","뭐가 있을까","어떨까","기획","아이템","방법",
    ],
}

def classify(prompt: str) -> str:
    lower = prompt.lower()
    scores = {cat: sum(1 for kw in kws if kw in lower) for cat, kws in CATEGORIES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"
