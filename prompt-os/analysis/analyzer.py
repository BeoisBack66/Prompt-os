import re
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Dict, Any
from analysis.scorer import score_prompt

def summarize(prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not prompts:
        return {"total": 0, "message": "No prompts saved yet."}
    total      = len(prompts)
    platforms  = Counter(p["platform"] for p in prompts)
    categories = Counter(p.get("category") or "other" for p in prompts)
    scored     = [p for p in prompts if p.get("score", 0) > 0]
    avg_score  = round(sum(p["score"] for p in scored) / len(scored), 1) if scored else 0
    rated      = sorted([p for p in prompts if p.get("rating", 0) >= 4],
                        key=lambda x: x["rating"], reverse=True)[:5]
    pc: Counter = Counter()
    for p in prompts:
        words = re.findall(r"\b\w+\b", p["prompt"].lower())
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
        return {"message": "No prompts this week."}
    cat_this = Counter(p.get("category") or "other" for p in this)
    al = _avg_len(this)
    ld = round(al - _avg_len(last), 1)
    as1 = _avg_score(this)
    as2 = _avg_score(last)
    top3  = sorted([p for p in this if p.get("rating", 0) > 0],
                   key=lambda x: x["rating"], reverse=True)[:3]
    needs = [p for p in this if len(p["prompt"].split()) < 8 and p.get("rating", 0) <= 2]
    return {
        "period": f"{week.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}",
        "this_week_total": len(this), "last_week_total": len(last),
        "by_category": dict(cat_this),
        "top_category": cat_this.most_common(1)[0][0] if cat_this else "-",
        "avg_prompt_length": al,
        "length_vs_last_week": f"{'+' if ld >= 0 else ''}{ld} words",
        "avg_quality_score": as1,
        "score_vs_last_week": f"{'+' if as1-as2 >= 0 else ''}{round(as1-as2, 1)} pts",
        "top3_prompts": [{"snippet": p["prompt"][:80], "rating": p["rating"],
                          "category": p.get("category")} for p in top3],
        "needs_improvement": [{"snippet": p["prompt"][:60],
                                "issues": ["too short", "low rating"]} for p in needs[:3]],
        "weekly_insight": _insight(this, cat_this),
    }

def find_similar(target: Dict, all_prompts: List[Dict], top_n: int = 5) -> List[Dict]:
    tw = set(re.findall(r"\b\w+\b", target["prompt"].lower()))
    results = []
    for p in all_prompts:
        if p["id"] == target["id"]:
            continue
        w = set(re.findall(r"\b\w+\b", p["prompt"].lower()))
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
    tpl = re.sub(r'"\[^"\]{3,}"', '{{content}}', tpl)
    tpl = re.sub(r"'[^']{3,}'", '{{content}}', tpl)
    tpl = re.sub(r"「[^」]{3,}」", '{{content}}', tpl)
    for lang in ["python","javascript","typescript","java","kotlin","swift",
                 "c\\+\\+","rust","go","ruby","파이썬","자바스크립트"]:
        tpl = re.sub(lang, "{{language}}", tpl, flags=re.IGNORECASE)
    tpl = re.sub(r"\b\d+\b", "{{N}}", tpl)
    variables = list(set(re.findall(r"\{\{([^}]+)\}\}", tpl)))
    return {"original": prompt, "suggested_template": tpl,
            "variables": variables, "is_useful": tpl != prompt}

def _find_weak(prompts):
    weak = []
    for p in prompts:
        issues = []
        text = p["prompt"]
        if len(text.split()) < 5:
            issues.append("too short — add more context")
        if not any(c in text for c in ["?", ".", "!", "줘", "요"]):
            issues.append("unclear request")
        if issues:
            weak.append({"id": p["id"], "snippet": text[:80], "issues": issues})
    return weak

def _suggestions(prompts, categories, total):
    s = []
    if categories.get("other", 0) / total > 0.3:
        s.append("Over 30% of prompts are uncategorized. Try starting with a clear verb like 'explain' or 'write'.")
    if categories.get("coding", 0) > 5:
        s.append("You have many coding prompts. Try adding the language name and version.")
    avg = sum(len(p["prompt"].split()) for p in prompts) / total
    if avg < 10:
        s.append(f"Average prompt length is {avg:.0f} words — quite short. Try adding constraints and context.")
    return s or ["Prompt quality looks great! Keep it up."]

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
    ins = [f"Most used category this week: '{top}'."]
    hr  = [p for p in prompts if p.get("rating", 0) >= 4]
    if hr:
        ins.append(f"{len(hr)} prompt(s) received a rating of 4+ — consider turning them into templates.")
    if len(prompts) >= 20:
        ins.append("High activity this week. Consider running a pattern analysis.")
    return " ".join(ins)
