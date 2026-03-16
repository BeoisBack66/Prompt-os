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
    async with get_db() as db:
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
    async with get_db() as db:
        async with db.execute(
            f"SELECT * FROM prompts WHERE {' AND '.join(conds)} ORDER BY id DESC LIMIT ? OFFSET ?",
            params,
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

@app.get("/prompts/{pid}")
async def get_prompt(pid: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM prompts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
    if not row: raise HTTPException(404, "Prompt not found.")
    return dict(row)

@app.patch("/prompts/{pid}/rating")
async def update_rating(pid: int, body: RatingUpdate):
    async with get_db() as db:
        await db.execute("UPDATE prompts SET rating=?,rating_note=? WHERE id=?",
                         (body.rating, body.rating_note, pid))
        await db.commit()
    return {"id": pid, "rating": body.rating}

@app.delete("/prompts/{pid}")
async def delete_prompt(pid: int):
    async with get_db() as db:
        await db.execute("DELETE FROM prompts WHERE id=?", (pid,))
        await db.commit()
    return {"status": "deleted"}

@app.delete("/prompts")
async def delete_all_prompts():
    async with get_db() as db:
        await db.execute("DELETE FROM prompts")
        await db.commit()
    return {"status": "all deleted"}

@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    async with get_db() as db:
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
    async with get_db() as db:
        async with db.execute(q, p) as cur:
            return [dict(r) for r in await cur.fetchall()]

@app.post("/templates", status_code=201)
async def create_template(body: TemplateCreate):
    now = datetime.utcnow().isoformat()
    async with get_db() as db:
        cur = await db.execute(
            "INSERT INTO templates (title,category,template,variables,source_id,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (body.title, body.category, body.template, body.variables, body.source_id, now),
        )
        await db.commit()
    return {"id": cur.lastrowid, "status": "created"}

@app.delete("/templates/{tid}")
async def delete_template(tid: int):
    async with get_db() as db:
        await db.execute("DELETE FROM templates WHERE id=?", (tid,))
        await db.commit()
    return {"status": "deleted"}

@app.get("/analysis/summary")
async def analysis_summary():
    async with get_db() as db:
        async with db.execute(
            "SELECT id,prompt,platform,category,rating,score,captured_at"
            " FROM prompts WHERE was_filtered=0"
        ) as cur:
            return summarize([dict(r) for r in await cur.fetchall()])

@app.get("/analysis/weekly")
async def analysis_weekly():
    async with get_db() as db:
        async with db.execute("SELECT * FROM prompts WHERE was_filtered=0") as cur:
            return weekly_report([dict(r) for r in await cur.fetchall()])

@app.get("/analysis/score/{pid}")
async def analysis_score(pid: int):
    async with get_db() as db:
        async with db.execute("SELECT prompt FROM prompts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
    if not row: raise HTTPException(404, "Prompt not found.")
    return score_prompt(row["prompt"])

@app.get("/analysis/similar/{pid}")
async def analysis_similar(pid: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM prompts WHERE was_filtered=0") as cur:
            all_rows = [dict(r) for r in await cur.fetchall()]
    target = next((r for r in all_rows if r["id"] == pid), None)
    if not target: raise HTTPException(404, "Prompt not found.")
    return find_similar(target, all_rows)

@app.get("/analysis/template-suggest/{pid}")
async def analysis_template_suggest(pid: int):
    async with get_db() as db:
        async with db.execute("SELECT prompt FROM prompts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()
    if not row: raise HTTPException(404, "Prompt not found.")
    return suggest_template(row["prompt"])
