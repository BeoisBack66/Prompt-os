"""
Prompt OS — 자동 설치 스크립트
Windows / Mac / Linux 모두 동일하게 사용:
    python setup.py
"""
import os, subprocess, sys

BASE = "prompt-os"

# ── 파일 내용 정의 ─────────────────────────────────────────────────────────────

FILES = {}

# ── requirements.txt ──────────────────────────────────────────────────────────
FILES["requirements.txt"] = """\
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
aiosqlite==0.20.0
python-dotenv==1.0.1
"""

# ── server/__init__.py ────────────────────────────────────────────────────────
FILES["server/__init__.py"] = ""

# ── analysis/__init__.py ──────────────────────────────────────────────────────
FILES["analysis/__init__.py"] = ""

# ── server/database.py ────────────────────────────────────────────────────────
FILES["server/database.py"] = '''\
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "prompts.db")

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt        TEXT    NOT NULL,
                platform      TEXT    NOT NULL,
                url           TEXT,
                captured_at   TEXT    NOT NULL,
                was_filtered  INTEGER DEFAULT 0,
                filter_reason TEXT,
                category      TEXT,
                rating        INTEGER DEFAULT 0,
                rating_note   TEXT,
                score         INTEGER DEFAULT 0,
                session_id    TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                category    TEXT NOT NULL,
                template    TEXT NOT NULL,
                variables   TEXT,
                source_id   INTEGER,
                use_count   INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            )
        """)
        await db.commit()
'''

# ── server/models.py ──────────────────────────────────────────────────────────
FILES["server/models.py"] = '''\
from pydantic import BaseModel, Field
from typing import Optional

class PromptCreate(BaseModel):
    prompt:      str
    platform:    str
    url:         Optional[str] = None
    captured_at: str
    session_id:  Optional[str] = None

class RatingUpdate(BaseModel):
    rating:      int = Field(..., ge=1, le=5)
    rating_note: Optional[str] = None

class TemplateCreate(BaseModel):
    title:     str
    category:  str
    template:  str
    variables: Optional[str] = None
    source_id: Optional[int] = None
'''

# ── analysis/classifier.py ────────────────────────────────────────────────────
FILES["analysis/classifier.py"] = '''\
import re
from typing import Tuple, Optional

SENSITIVE_PATTERNS = [
    (r"password",                                  "비밀번호 포함"),
    (r"비밀번호|패스워드",                          "비밀번호 포함"),
    (r"api[_\\s]?key",                             "API 키 포함"),
    (r"\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b", "카드번호 가능성"),
    (r"\\b\\d{3}-\\d{2}-\\d{4}\\b",               "SSN 가능성"),
    (r"\\b\\d{6}-\\d{7}\\b",                       "주민등록번호 가능성"),
    (r"private[_\\s]?key",                         "개인키 포함"),
    (r"개인키|비공개키",                            "개인키 포함"),
    (r"secret",                                    "시크릿 포함"),
    (r"bearer\\s+[a-z0-9\\-._~+/]+=*",            "Bearer 토큰 포함"),
]

def filter_sensitive(prompt: str) -> Tuple[bool, Optional[str]]:
    lower = prompt.lower()
    for pattern, reason in SENSITIVE_PATTERNS:
        if re.search(pattern, lower):
            return True, reason
    return False, None

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
'''

# ── analysis/scorer.py ────────────────────────────────────────────────────────
FILES["analysis/scorer.py"] = '''\
import re
from typing import Dict, Any

ROLE_PATTERNS = [
    r"너는\\s+.+야", r"당신은\\s+.+입니다", r"act as", r"you are a",
    r"as a\\s+\\w+", r"역할", r"전문가로서", r"시니어", r"expert",
]
FORMAT_PATTERNS = [
    r"json", r"markdown", r"bullet", r"표로", r"리스트로", r"목록으로",
    r"단계별", r"step by step", r"numbered", r"번호를 붙여",
    r"\\d+줄", r"\\d+자", r"\\d+ words", r"형식으로", r"format", r"코드 블록", r"code block",
]
CONTEXT_PATTERNS = [
    r"조건", r"단,\\s", r"단\\s", r"제약", r"단계", r"예를 들어", r"예시",
    r"예:\\s", r"ex\\.", r"for example", r"given", r"assuming",
    r"배경", r"상황", r"context", r"constraint",
]
ACTION_KO = [
    "작성","설명","요약","번역","분석","비교","구현","수정","고쳐","만들어",
    "짜줘","알려","정리","제안","추천","생성","검토","리뷰","평가","개선",
]
ACTION_EN = [
    "write","explain","summarize","translate","analyze","compare",
    "implement","fix","create","generate","review","evaluate",
    "suggest","improve","describe","list","outline",
]

def score_prompt(prompt: str) -> Dict[str, Any]:
    lower = prompt.lower()
    words = prompt.split()
    length = len(words)
    b = {}

    has_role = any(re.search(p, lower) for p in ROLE_PATTERNS)
    b["role"] = {
        "score": 20 if has_role else 0, "max": 20, "label": "역할 지정", "passed": has_role,
        "tip": "역할을 지정하면 더 전문적인 답변을 얻을 수 있어요. (예: 시니어 개발자로서)",
    }
    has_fmt = any(re.search(p, lower) for p in FORMAT_PATTERNS)
    b["format"] = {
        "score": 20 if has_fmt else 0, "max": 20, "label": "출력 형식", "passed": has_fmt,
        "tip": "출력 형식을 지정해보세요. (예: JSON으로, 단계별로, 3줄 이내로)",
    }
    has_ctx = any(re.search(p, lower) for p in CONTEXT_PATTERNS)
    b["context"] = {
        "score": 20 if has_ctx else 0, "max": 20, "label": "맥락/조건", "passed": has_ctx,
        "tip": "조건이나 배경을 추가하면 훨씬 정확한 답을 얻을 수 있어요. (예: 단, 외부 라이브러리 없이)",
    }
    if 10 <= length <= 80:
        ls, lp, lt = 20, True, None
    elif length < 10:
        ls, lp, lt = max(0, length * 2), False, f"프롬프트가 너무 짧습니다 ({length}단어). 맥락을 더 추가해보세요."
    else:
        ls, lp, lt = 10, False, f"프롬프트가 다소 깁니다 ({length}단어). 핵심만 남겨보세요."
    b["length"] = {"score": ls, "max": 20, "label": "적정 길이", "passed": lp, "tip": lt}

    has_act = any(v in lower for v in ACTION_KO) or any(v in lower for v in ACTION_EN)
    b["action"] = {
        "score": 20 if has_act else 0, "max": 20, "label": "명확한 동사", "passed": has_act,
        "tip": "명확한 동사로 시작하세요. (예: 설명해줘, 작성해줘, 비교해줘)",
    }

    total = sum(v["score"] for v in b.values())
    grade = "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D"
    tips = [v["tip"] for v in b.values() if v.get("tip") and not v["passed"]]
    return {"total": total, "grade": grade, "breakdown": b, "improvement_tips": tips}
'''

# ── analysis/analyzer.py ──────────────────────────────────────────────────────
FILES["analysis/analyzer.py"] = '''\
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any
from analysis.scorer import score_prompt

def summarize(prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not prompts:
        return {"total": 0, "message": "아직 저장된 프롬프트가 없습니다."}
    total      = len(prompts)
    platforms  = Counter(p["platform"] for p in prompts)
    categories = Counter(p.get("category") or "other" for p in prompts)
    scored     = [p for p in prompts if p.get("score", 0) > 0]
    avg_score  = round(sum(p["score"] for p in scored) / len(scored), 1) if scored else 0
    rated      = sorted([p for p in prompts if p.get("rating", 0) >= 4],
                        key=lambda x: x["rating"], reverse=True)[:5]
    pc: Counter = Counter()
    for p in prompts:
        words = re.findall(r"\\b\\w+\\b", p["prompt"].lower())
        for i in range(len(words) - 2):
            pc[" ".join(words[i:i+3])] += 1
    top_phrases = [{"phrase": ph, "count": c} for ph, c in pc.most_common(10) if c > 1]
    return {
        "total": total,
        "by_platform": dict(platforms),
        "by_category": dict(categories),
        "avg_quality_score": avg_score,
        "top_rated_prompts": [{"id": p["id"], "snippet": p["prompt"][:80], "rating": p["rating"]} for p in rated],
        "top_repeated_phrases": top_phrases,
        "weak_prompts": _find_weak(prompts)[:5],
        "suggestions": _suggestions(prompts, categories, total),
    }

def weekly_report(prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
    now  = datetime.utcnow()
    week = now - timedelta(days=7)
    prev = now - timedelta(days=14)
    this = [p for p in prompts if _dt(p["captured_at"]) >= week]
    last = [p for p in prompts if prev <= _dt(p["captured_at"]) < week]
    if not this:
        return {"message": "이번 주 프롬프트가 없습니다."}
    cat_this = Counter(p.get("category") or "other" for p in this)
    al = _avg_len(this)
    ld = round(al - _avg_len(last), 1)
    as1 = _avg_score(this)
    as2 = _avg_score(last)
    top3  = sorted([p for p in this if p.get("rating", 0) > 0],
                   key=lambda x: x["rating"], reverse=True)[:3]
    needs = [p for p in this if len(p["prompt"].split()) < 8 and p.get("rating", 0) <= 2]
    return {
        "period": f"{week.strftime(\'%Y-%m-%d\')} ~ {now.strftime(\'%Y-%m-%d\')}",
        "this_week_total": len(this), "last_week_total": len(last),
        "by_category": dict(cat_this),
        "top_category": cat_this.most_common(1)[0][0] if cat_this else "-",
        "avg_prompt_length": al,
        "length_vs_last_week": f"{\'+\' if ld >= 0 else \'\'}{ld}단어",
        "avg_quality_score": as1,
        "score_vs_last_week": f"{\'+\' if as1-as2 >= 0 else \'\'}{round(as1-as2, 1)}점",
        "top3_prompts": [{"snippet": p["prompt"][:80], "rating": p["rating"],
                          "category": p.get("category")} for p in top3],
        "needs_improvement": [{"snippet": p["prompt"][:60],
                                "issues": ["너무 짧음", "낮은 평점"]} for p in needs[:3]],
        "weekly_insight": _insight(this, cat_this),
    }

def find_similar(target: Dict, all_prompts: List[Dict], top_n: int = 5) -> List[Dict]:
    tw = set(re.findall(r"\\b\\w+\\b", target["prompt"].lower()))
    results = []
    for p in all_prompts:
        if p["id"] == target["id"]:
            continue
        w = set(re.findall(r"\\b\\w+\\b", p["prompt"].lower()))
        u = tw | w
        if not u:
            continue
        sim = len(tw & w) / len(u)
        if sim > 0.2:
            results.append({"id": p["id"], "snippet": p["prompt"][:80],
                            "similarity": round(sim, 2), "rating": p.get("rating", 0),
                            "category": p.get("category")})
    return sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_n]

def suggest_template(prompt: str) -> Dict[str, Any]:
    tpl = prompt
    tpl = re.sub(r\'"\[^"\]{3,}"\', \'{{내용}}\', tpl)
    tpl = re.sub(r"\'[^\']{3,}\'", \'{{내용}}\', tpl)
    tpl = re.sub(r"「[^」]{3,}」", \'{{내용}}\', tpl)
    for lang in ["python","javascript","typescript","java","kotlin","swift",
                 "c\\\\+\\\\+","rust","go","ruby","파이썬","자바스크립트"]:
        tpl = re.sub(lang, "{{언어}}", tpl, flags=re.IGNORECASE)
    tpl = re.sub(r"\\b\\d+\\b", "{{N}}", tpl)
    variables = list(set(re.findall(r"\\{\\{([^}]+)\\}\\}", tpl)))
    return {"original": prompt, "suggested_template": tpl,
            "variables": variables, "is_useful": tpl != prompt}

def _find_weak(prompts):
    weak = []
    for p in prompts:
        issues = []
        text = p["prompt"]
        if len(text.split()) < 5:
            issues.append("너무 짧음 — 맥락을 추가하세요")
        if not any(c in text for c in ["?", ".", "!", "줘", "요"]):
            issues.append("불명확한 요청")
        if issues:
            weak.append({"id": p["id"], "snippet": text[:80], "issues": issues})
    return weak

def _suggestions(prompts, categories, total):
    s = []
    if categories.get("other", 0) / total > 0.3:
        s.append("30% 이상이 미분류입니다. \'설명해줘\', \'작성해줘\' 같은 명확한 동사로 시작해보세요.")
    if categories.get("coding", 0) > 5:
        s.append("코딩 프롬프트가 많습니다. 언어와 버전 정보를 추가해보세요.")
    avg = sum(len(p["prompt"].split()) for p in prompts) / total
    if avg < 10:
        s.append(f"평균 길이 {avg:.0f}단어로 짧습니다. 조건과 맥락을 추가해보세요.")
    return s or ["프롬프트 품질이 좋습니다! 계속 유지하세요 🎉"]

def _dt(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()

def _avg_len(p):
    return round(sum(len(x["prompt"].split()) for x in p) / len(p), 1) if p else 0

def _avg_score(p):
    s = [x for x in p if x.get("score", 0) > 0]
    return round(sum(x["score"] for x in s) / len(s), 1) if s else 0

def _insight(prompts, categories):
    top = categories.most_common(1)[0][0] if categories else "other"
    ins = [f"이번 주 가장 많이 쓴 카테고리는 \'{top}\'입니다."]
    hr  = [p for p in prompts if p.get("rating", 0) >= 4]
    if hr:
        ins.append(f"총 {len(hr)}개의 프롬프트가 ⭐4 이상을 받았습니다. 템플릿화를 추천합니다.")
    if len(prompts) >= 20:
        ins.append("이번 주 활동량이 높습니다. 패턴 분석을 돌려보세요.")
    return " ".join(ins)
'''

# ── server/main.py ────────────────────────────────────────────────────────────
FILES["server/main.py"] = '''\
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from server.database import init_db, get_db
from server.models import PromptCreate, RatingUpdate, TemplateCreate
from analysis.classifier import filter_sensitive, classify
from analysis.scorer import score_prompt
from analysis.analyzer import summarize, weekly_report, find_similar, suggest_template

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Prompt OS", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/prompts", status_code=201)
async def store_prompt(payload: PromptCreate):
    filtered, reason = filter_sensitive(payload.prompt)
    category = quality = None
    if not filtered:
        category = classify(payload.prompt)
        quality  = score_prompt(payload.prompt)
    async with await get_db() as db:
        cur = await db.execute(
            "INSERT INTO prompts (prompt,platform,url,captured_at,was_filtered,"
            "filter_reason,category,score,session_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (payload.prompt, payload.platform, payload.url, payload.captured_at,
             1 if filtered else 0, reason, category,
             quality.get("total", 0) if quality else 0, payload.session_id),
        )
        await db.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "status": "filtered" if filtered else "stored",
            "category": category, "filter_reason": reason, "quality": quality}

@app.get("/prompts")
async def get_prompts(limit: int = 50, offset: int = 0,
                      platform: Optional[str] = None,
                      category: Optional[str] = None,
                      min_rating: Optional[int] = None):
    conds = ["was_filtered=0"]; params = []
    if platform:   conds.append("platform=?");  params.append(platform)
    if category:   conds.append("category=?");  params.append(category)
    if min_rating: conds.append("rating>=?");   params.append(min_rating)
    params += [limit, offset]
    async with await get_db() as db:
        async with db.execute(
            f"SELECT * FROM prompts WHERE {\' AND \'.join(conds)} ORDER BY id DESC LIMIT ? OFFSET ?",
            params,
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

@app.get("/prompts/{pid}")
async def get_prompt(pid: int):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM prompts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
    if not row: raise HTTPException(404, "프롬프트를 찾을 수 없습니다.")
    return dict(row)

@app.patch("/prompts/{pid}/rating")
async def update_rating(pid: int, body: RatingUpdate):
    async with await get_db() as db:
        await db.execute("UPDATE prompts SET rating=?,rating_note=? WHERE id=?",
                         (body.rating, body.rating_note, pid))
        await db.commit()
    return {"id": pid, "rating": body.rating}

@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    async with await get_db() as db:
        async with db.execute(
            "SELECT * FROM prompts WHERE was_filtered=0 AND prompt LIKE ? ORDER BY id DESC",
            (f"%{q}%",),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

@app.get("/templates")
async def get_templates(category: Optional[str] = None):
    if category:
        q, p = "SELECT * FROM templates WHERE category=? ORDER BY use_count DESC", (category,)
    else:
        q, p = "SELECT * FROM templates ORDER BY use_count DESC", ()
    async with await get_db() as db:
        async with db.execute(q, p) as cur:
            return [dict(r) for r in await cur.fetchall()]

@app.post("/templates", status_code=201)
async def create_template(body: TemplateCreate):
    now = datetime.utcnow().isoformat()
    async with await get_db() as db:
        cur = await db.execute(
            "INSERT INTO templates (title,category,template,variables,source_id,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (body.title, body.category, body.template, body.variables, body.source_id, now),
        )
        await db.commit()
    return {"id": cur.lastrowid, "status": "created"}

@app.delete("/templates/{tid}")
async def delete_template(tid: int):
    async with await get_db() as db:
        await db.execute("DELETE FROM templates WHERE id=?", (tid,))
        await db.commit()
    return {"status": "deleted"}

@app.get("/analysis/summary")
async def analysis_summary():
    async with await get_db() as db:
        async with db.execute(
            "SELECT id,prompt,platform,category,rating,score,captured_at"
            " FROM prompts WHERE was_filtered=0"
        ) as cur:
            return summarize([dict(r) for r in await cur.fetchall()])

@app.get("/analysis/weekly")
async def analysis_weekly():
    async with await get_db() as db:
        async with db.execute("SELECT * FROM prompts WHERE was_filtered=0") as cur:
            return weekly_report([dict(r) for r in await cur.fetchall()])

@app.get("/analysis/score/{pid}")
async def analysis_score(pid: int):
    async with await get_db() as db:
        async with db.execute("SELECT prompt FROM prompts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
    if not row: raise HTTPException(404, "프롬프트를 찾을 수 없습니다.")
    return score_prompt(row["prompt"])

@app.get("/analysis/similar/{pid}")
async def analysis_similar(pid: int):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM prompts WHERE was_filtered=0") as cur:
            all_rows = [dict(r) for r in await cur.fetchall()]
    target = next((r for r in all_rows if r["id"] == pid), None)
    if not target: raise HTTPException(404, "프롬프트를 찾을 수 없습니다.")
    return find_similar(target, all_rows)

@app.get("/analysis/template-suggest/{pid}")
async def analysis_template_suggest(pid: int):
    async with await get_db() as db:
        async with db.execute("SELECT prompt FROM prompts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
    if not row: raise HTTPException(404, "프롬프트를 찾을 수 없습니다.")
    return suggest_template(row["prompt"])
'''

# ── extension/manifest.json ───────────────────────────────────────────────────
FILES["extension/manifest.json"] = '''\
{
  "manifest_version": 3,
  "name": "Prompt OS",
  "version": "2.0.0",
  "description": "나의 프롬프트를 자동 수집·분석·템플릿화하는 개인용 도구",
  "permissions": ["storage", "scripting", "activeTab"],
  "host_permissions": ["https://chatgpt.com/*", "https://claude.ai/*"],
  "background": { "service_worker": "background.js" },
  "content_scripts": [{
    "matches": ["https://chatgpt.com/*", "https://claude.ai/*"],
    "js": ["content.js"],
    "run_at": "document_idle"
  }],
  "action": { "default_title": "Prompt OS", "default_popup": "popup.html" }
}
'''

# ── extension/content.js ──────────────────────────────────────────────────────
FILES["extension/content.js"] = """\
(function () {
  "use strict";
  const PLATFORM   = location.hostname.includes("chatgpt") ? "chatgpt" : "claude";
  const SESSION_ID = `${PLATFORM}-${Date.now()}`;
  const SEL = {
    chatgpt: { textarea: "#prompt-textarea",
               sendBtn:  'button[data-testid="send-button"]' },
    claude:  { textarea: 'div[contenteditable="true"].ProseMirror',
               sendBtn:  'button[aria-label="Send message"]' },
  };
  const s = SEL[PLATFORM];
  let lastSent = "";

  function getText() {
    const el = document.querySelector(s.textarea);
    return el ? (el.value || el.innerText || "").trim() : null;
  }
  function send(text) {
    if (!text || text === lastSent) return;
    lastSent = text;
    chrome.runtime.sendMessage({
      type: "PROMPT_CAPTURED",
      payload: {
        prompt: text, platform: PLATFORM,
        url: location.href, captured_at: new Date().toISOString(),
        session_id: SESSION_ID,
      },
    });
  }
  document.addEventListener("click", e => {
    if (e.target.closest(s.sendBtn)) { const t = getText(); if (t) send(t); }
  }, true);
  document.addEventListener("keydown", e => {
    if (e.key !== "Enter" || e.shiftKey) return;
    const a = document.activeElement;
    if (a.matches(s.textarea) || a.closest(s.textarea)) { const t = getText(); if (t) send(t); }
  }, true);
  console.log(`[Prompt OS] Watching ${PLATFORM}`);
})();
"""

# ── extension/background.js ───────────────────────────────────────────────────
FILES["extension/background.js"] = """\
const SERVER = "http://localhost:8000";

chrome.runtime.onMessage.addListener(msg => {
  if (msg.type === "PROMPT_CAPTURED") sendPrompt(msg.payload);
  if (msg.type === "RATE_PROMPT")     ratePrompt(msg.id, msg.rating, msg.note);
});

async function sendPrompt(payload) {
  try {
    const res = await fetch(`${SERVER}/prompts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return;
    const data = await res.json();
    const { recentIds = [] } = await chrome.storage.local.get("recentIds");
    recentIds.unshift({ id: data.id, snippet: payload.prompt.slice(0, 60), score: data.quality?.total ?? 0 });
    if (recentIds.length > 20) recentIds.length = 20;
    await chrome.storage.local.set({ recentIds });
    const score = data.quality?.total ?? 0;
    chrome.action.setBadgeBackgroundColor({ color: score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : "#ef4444" });
    chrome.action.setBadgeText({ text: score ? String(score) : "?" });
    setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
  } catch (err) { console.warn("[POS]", err.message); }
}

async function ratePrompt(id, rating, note = "") {
  await fetch(`${SERVER}/prompts/${id}/rating`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, rating_note: note }),
  }).catch(() => {});
}
"""

# ── extension/popup.html ──────────────────────────────────────────────────────
FILES["extension/popup.html"] = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{width:360px;font-family:-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;font-size:13px}
header{padding:12px 16px;background:#1e293b;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:15px;font-weight:700;color:#7c3aed}
header span{font-size:11px;color:#64748b}
.tabs{display:flex;background:#1e293b;border-bottom:1px solid #334155}
.tab{flex:1;padding:8px;text-align:center;cursor:pointer;color:#64748b;font-size:12px}
.tab.active{color:#7c3aed;border-bottom:2px solid #7c3aed}
.section{padding:12px 16px;display:none;max-height:480px;overflow-y:auto}
.section.active{display:block}
.card{background:#1e293b;border-radius:8px;padding:10px 12px;margin-bottom:8px}
.meta{color:#64748b;font-size:11px;margin-top:4px}
.stars{display:flex;gap:3px;margin-top:6px}
.star{cursor:pointer;font-size:16px;color:#334155;transition:color .15s}
.star.on{color:#f59e0b}
.score-badge{display:inline-block;padding:2px 7px;border-radius:99px;font-size:11px;font-weight:600}
.score-a{background:#166534;color:#bbf7d0}
.score-b{background:#713f12;color:#fef3c7}
.score-c{background:#7f1d1d;color:#fecaca}
.stat-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #334155}
.stat-val{font-weight:600;color:#a78bfa}
.chip{display:inline-block;padding:2px 8px;border-radius:99px;background:#312e81;color:#c7d2fe;font-size:11px;margin:2px}
.tip{background:#172554;border-left:3px solid #3b82f6;padding:6px 10px;border-radius:4px;margin-top:6px;font-size:12px;color:#93c5fd}
.tpl-card{background:#1e293b;border-radius:8px;padding:10px 12px;margin-bottom:8px}
.tpl-text{font-family:monospace;font-size:12px;color:#a78bfa;margin-top:4px}
.btn{padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px;border:none}
.btn-primary{background:#7c3aed;color:#fff}
input,textarea{width:100%;background:#0f172a;border:1px solid #334155;border-radius:6px;padding:6px 8px;color:#e2e8f0;font-size:12px;margin-top:4px;outline:none}
label{color:#94a3b8;font-size:11px}
.empty{color:#475569;text-align:center;padding:24px 0;font-size:12px}
</style>
</head>
<body>
<header><h1>&#x1F9E0; Prompt OS</h1><span id="srv">확인 중...</span></header>
<div class="tabs">
  <div class="tab active" data-tab="recent">최근</div>
  <div class="tab" data-tab="stats">분석</div>
  <div class="tab" data-tab="templates">템플릿</div>
</div>
<div class="section active" id="tab-recent"><div id="recent-list"><p class="empty">로딩 중...</p></div></div>
<div class="section" id="tab-stats"><div id="stats-content"><p class="empty">로딩 중...</p></div></div>
<div class="section" id="tab-templates">
  <div id="tpl-list"><p class="empty">로딩 중...</p></div>
  <hr style="border-color:#334155;margin:10px 0">
  <div class="card">
    <label>제목</label><input id="tpl-title" placeholder="예: 코드 리뷰 요청">
    <label>카테고리</label><input id="tpl-cat" placeholder="coding / writing / research ...">
    <label>템플릿 내용</label>
    <textarea id="tpl-body" rows="3" placeholder="{{언어}}로 {{기능}}을 구현해줘."></textarea>
    <div style="margin-top:8px"><button class="btn btn-primary" id="tpl-save">저장</button></div>
  </div>
</div>
<script>
const S = "http://localhost:8000";
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  document.querySelectorAll(".tab,.section").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  document.getElementById("tab-" + t.dataset.tab).classList.add("active");
}));
async function checkServer() {
  try { await fetch(S + "/health"); document.getElementById("srv").textContent = "✅ 연결됨"; }
  catch { document.getElementById("srv").textContent = "❌ 서버 꺼짐"; }
}
async function loadRecent() {
  const el = document.getElementById("recent-list");
  try {
    const data = await (await fetch(S + "/prompts?limit=15")).json();
    if (!data.length) { el.innerHTML = '<p class="empty">아직 프롬프트가 없습니다.</p>'; return; }
    el.innerHTML = data.map(p =>
      '<div class="card"><div>' + p.prompt.slice(0,80) + (p.prompt.length>80?"…":"") + '</div>' +
      '<div class="meta">' + p.platform + ' · ' + (p.category||"other") +
      ' · <span class="score-badge ' + gc(p.score) + '">' + p.score + '점</span></div>' +
      '<div class="stars" data-id="' + p.id + '">' +
      [1,2,3,4,5].map(n => '<span class="star ' + (n<=(p.rating||0)?"on":"") + '" data-n="'+n+'">★</span>').join("") +
      '</div></div>'
    ).join("");
    el.querySelectorAll(".stars").forEach(row =>
      row.querySelectorAll(".star").forEach(s => s.addEventListener("click", () => {
        const id = +row.dataset.id, n = +s.dataset.n;
        fetch(S+"/prompts/"+id+"/rating", {method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({rating:n})});
        row.querySelectorAll(".star").forEach(x => x.classList.toggle("on", +x.dataset.n <= n));
      }))
    );
  } catch { el.innerHTML = '<p class="empty">서버에 연결할 수 없습니다.</p>'; }
}
async function loadStats() {
  const el = document.getElementById("stats-content");
  try {
    const d = await (await fetch(S + "/analysis/summary")).json();
    if (d.total === 0) { el.innerHTML = '<p class="empty">데이터가 없습니다.</p>'; return; }
    const cats = Object.entries(d.by_category||{}).map(([k,v]) => '<span class="chip">'+k+' '+v+'</span>').join("");
    const tips = (d.suggestions||[]).map(t => '<div class="tip">💡 '+t+'</div>').join("");
    el.innerHTML =
      '<div class="card">' +
        '<div class="stat-row"><span>총 프롬프트</span><span class="stat-val">'+d.total+'개</span></div>' +
        '<div class="stat-row"><span>평균 품질 점수</span><span class="stat-val">'+d.avg_quality_score+'점</span></div>' +
      '</div>' +
      '<div class="card"><div style="margin-bottom:6px;color:#94a3b8;font-size:11px">카테고리 분포</div>'+cats+'</div>' +
      '<div style="color:#94a3b8;font-size:11px;margin-bottom:4px">개선 제안</div>' + tips;
  } catch { el.innerHTML = '<p class="empty">서버에 연결할 수 없습니다.</p>'; }
}
async function loadTemplates() {
  const el = document.getElementById("tpl-list");
  try {
    const data = await (await fetch(S + "/templates")).json();
    if (!data.length) { el.innerHTML = '<p class="empty">저장된 템플릿이 없습니다.</p>'; return; }
    el.innerHTML = data.map(t =>
      '<div class="tpl-card"><div><strong>'+t.title+'</strong> <span class="chip">'+t.category+'</span></div>' +
      '<div class="tpl-text">'+t.template+'</div>' +
      '<div class="meta" style="margin-top:4px">사용 '+t.use_count+'회</div></div>'
    ).join("");
  } catch { el.innerHTML = '<p class="empty">서버에 연결할 수 없습니다.</p>'; }
}
document.getElementById("tpl-save").addEventListener("click", async () => {
  const title = document.getElementById("tpl-title").value.trim();
  const cat   = document.getElementById("tpl-cat").value.trim();
  const body  = document.getElementById("tpl-body").value.trim();
  if (!title || !cat || !body) return alert("모든 필드를 입력해주세요.");
  await fetch(S+"/templates", {method:"POST",headers:{"Content-Type":"application/json"},
    body: JSON.stringify({title, category:cat, template:body})});
  document.getElementById("tpl-title").value =
  document.getElementById("tpl-cat").value   =
  document.getElementById("tpl-body").value  = "";
  loadTemplates();
});
function gc(s) { return s>=80?"score-a":s>=60?"score-b":"score-c"; }
checkServer(); loadRecent(); loadStats(); loadTemplates();
</script>
</body>
</html>
"""

# ── 파일 생성 실행 ─────────────────────────────────────────────────────────────
def write_files():
    for path, content in FILES.items():
        full = os.path.join(BASE, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ {full}")

def install_deps():
    req = os.path.join(BASE, "requirements.txt")
    print("\n📦 Python 의존성 설치 중...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req])
    if result.returncode != 0:
        print("❌ pip 설치 실패. 수동으로 실행해주세요:")
        print(f"   pip install -r {req}")
    else:
        print("✅ 의존성 설치 완료!")

if __name__ == "__main__":
    print("=" * 45)
    print("  🧠 Prompt OS — 파일 생성 시작")
    print("=" * 45)
    write_files()
    install_deps()
    print("\n" + "=" * 45)
    print("  🎉 설치 완료!")
    print("=" * 45)
    print(f"\n▶️  서버 실행:")
    print(f"    cd {BASE}/server")
    print(f"    uvicorn main:app --reload --port 8000")
    print(f"\n🌐 API 문서:  http://localhost:8000/docs")
    print(f"🔌 확장 로드: chrome://extensions/ → 개발자 모드 ON → extension/ 폴더 선택\n")