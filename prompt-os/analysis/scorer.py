import re
from typing import Dict, Any

# Clear action verbs that indicate a well-formed request
ACTION_KO = [
    "작성","설명","요약","번역","분석","비교","구현","수정","고쳐","만들어",
    "짜줘","알려","정리","제안","추천","생성","검토","리뷰","평가","개선",
    "찾아","구해","계산","풀어","변환","정의","나열","예시","보여",
]
ACTION_EN = [
    "write","explain","summarize","translate","analyze","compare",
    "implement","fix","create","generate","review","evaluate",
    "suggest","improve","describe","list","outline","find","solve",
    "convert","define","show","calculate",
]

# Output format indicators
FORMAT_PATTERNS = [
    r"json", r"markdown", r"bullet", r"표로", r"리스트로", r"목록으로",
    r"단계별", r"step by step", r"numbered", r"번호를 붙여",
    r"\d+줄", r"\d+자", r"\d+ words", r"형식으로", r"format",
    r"코드 블록", r"code block", r"한 문단", r"문단으로",
]

# Context and background indicators
CONTEXT_PATTERNS = [
    r"조건", r"단[,\s]", r"제약", r"예를 들어", r"예시",
    r"예:\s", r"ex\.", r"for example", r"given", r"assuming",
    r"배경", r"상황", r"context", r"현재\s", r"지금\s",
    r"이번에", r"이 코드", r"아래\s", r"다음\s",
]

# Constraint indicators — limits on how the response should be shaped
CONSTRAINT_PATTERNS = [
    r"하지\s*말", r"빼고", r"없이", r"제외", r"금지",
    r"이내로", r"이하로", r"이상으로", r"한\s*\d+",
    r"반드시", r"꼭\s", r"only", r"without", r"must",
    r"don't", r"no\s+\w+", r"초등|중학|고등|비개발자|비전문가",
    r"쉽게|어렵게|간단히|자세히|상세히|짧게|길게",
    r"한국어로|영어로|존댓말로|반말로",
]

# Specificity indicators — concrete details that make a prompt more precise
SPECIFIC_PATTERNS = [
    r"\d+",                             # contains numbers
    r'"[^"]{2,}"',                      # quoted terms
    r"'[^']{2,}'",
    r"「[^」]{2,}」",
    r"python|javascript|typescript|java|kotlin|swift|react|vue|angular",
    r"django|fastapi|spring|sql|html|css|rust|go\b|ruby|node",
    r"파이썬|자바스크립트|타입스크립트|리액트|장고|스프링",
    r"이\s*코드|아래\s*코드|위\s*코드|이\s*함수|이\s*오류",
    r"버전\s*\d|v\d+\.\d+",            # version number specified
]


def score_prompt(prompt: str) -> Dict[str, Any]:
    lower = prompt.lower()
    words = prompt.split()
    b = {}

    # 1. Clear action verb (20 pts)
    has_act = any(v in lower for v in ACTION_KO) or any(v in lower for v in ACTION_EN)
    b["action"] = {
        "score": 20 if has_act else 0, "max": 20,
        "label": "Clear action verb", "passed": has_act,
        "tip": "Use a clear action verb. (e.g. explain, write, analyze, fix)",
    }

    # 2. Context / background (20 pts)
    has_ctx = any(re.search(p, lower) for p in CONTEXT_PATTERNS)
    b["context"] = {
        "score": 20 if has_ctx else 0, "max": 20,
        "label": "Context / background", "passed": has_ctx,
        "tip": "Add background or current situation. (e.g. I am currently working on...)",
    }

    # 3. Constraints (20 pts)
    has_cst = any(re.search(p, lower) for p in CONSTRAINT_PATTERNS)
    b["constraint"] = {
        "score": 20 if has_cst else 0, "max": 20,
        "label": "Constraints", "passed": has_cst,
        "tip": "Add constraints. (e.g. without external libraries, in simple terms, under 3 lines)",
    }

    # 4. Output format (20 pts)
    has_fmt = any(re.search(p, lower) for p in FORMAT_PATTERNS)
    b["format"] = {
        "score": 20 if has_fmt else 0, "max": 20,
        "label": "Output format", "passed": has_fmt,
        "tip": "Specify desired output format. (e.g. as JSON, step by step, as a list)",
    }

    # 5. Specificity (20 pts) — replaces raw length check
    has_spc = len(words) >= 3 and any(re.search(p, lower) for p in SPECIFIC_PATTERNS)
    b["specificity"] = {
        "score": 20 if has_spc else (10 if len(words) >= 5 else 0), "max": 20,
        "label": "Specificity", "passed": has_spc,
        "tip": "Be more specific. (e.g. include tech name, version, code snippet, or numbers)",
    }

    total = sum(v["score"] for v in b.values())
    grade = "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D"
    tips = [v["tip"] for v in b.values() if v.get("tip") and not v["passed"]]
    return {"total": total, "grade": grade, "breakdown": b, "improvement_tips": tips}
