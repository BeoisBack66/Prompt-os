# Prompt OS — MVP Spec

---

## 1. Product Overview

**Prompt OS** is a personal tool that automatically captures, analyzes, and improves prompts entered by ChatGPT and Claude users.
Without any manual action, a browser extension captures prompts in the background, and a local server evaluates their quality and returns feedback to the user.

---

## 2. Problems Solved

| Problem | Description |
|---------|-------------|
| Prompt loss | Good prompts disappear if not saved manually |
| No quality awareness | No standard for what makes a good prompt |
| No pattern visibility | No way to reflect on how you're using AI |
| Reuse friction | Turning good prompts into templates is tedious |

---

## 3. Core Features (Implemented)

### 3-1. Auto Capture
- Supports ChatGPT (`chatgpt.com`) and Claude (`claude.ai`)
- Detects both Enter key submission and button click submission
- SPA navigation support — automatically reconnects when a new conversation starts
- 2-second cooldown to prevent duplicate saves

### 3-2. Sensitive Data Filtering
Automatically blocks prompts containing:
- Passwords
- API keys, Bearer tokens, private keys
- Card numbers, national ID numbers, SSN

### 3-3. Automatic Category Classification
| Category | Examples |
|----------|---------|
| coding | writing code, implementing algorithms |
| debugging | fixing errors, analyzing bugs |
| writing | drafting emails, essays, articles |
| summarization | summarizing, extracting key points |
| translation | translating between languages |
| research | explanations, concept exploration |
| learning | tutorials, requesting examples |
| math | calculations, equations, probability |
| brainstorming | ideas, planning, creative thinking |

### 3-4. Quality Scoring System (100 pts)

Redesigned from a raw length-based score to 5 criteria that reflect actual prompt quality:

| Criterion | Points | Evaluated By |
|-----------|--------|--------------|
| Clear action verb | 20 | Contains a specific action verb (explain, write, analyze, etc.) |
| Context / background | 20 | Includes current situation, background info, or examples |
| Constraints | 20 | Includes scope or style limits (without X, in simple terms, under N lines) |
| Output format | 20 | Specifies desired format (JSON, list, step-by-step, code block) |
| Specificity | 20 | Includes tech names, version numbers, code references, or numbers |

**Grades:** A (80+) / B (60+) / C (40+) / D (below 40)

**Good prompt example (Grade A):**
> "I'm getting an encoding error when reading a CSV file with pandas in Python 3.11. Explain how to fix it step by step, without using any external libraries."

**Bad prompt example (Grade D):**
> "Explain this."

### 3-5. Analysis Features
- **Overall summary**: distribution by platform and category, average score, repeated phrase extraction
- **Weekly report**: this week vs last week comparison, top 3 highest-rated prompts
- **Similar prompt search**: Jaccard similarity-based matching
- **Template auto-suggestion**: extracts repeating patterns into `{{variable}}` format

### 3-6. Popup UI
- **Recent tab**: last 15 prompts, star rating (1–5), individual delete
- **Analytics tab**: category breakdown, average score, improvement suggestions
- **Templates tab**: saved template list, new template registration

---

## 4. Architecture

```
[ChatGPT / Claude browser tab]
        ↓  (MutationObserver detects textarea changes)
[content.js — Chrome Extension]
        ↓  (chrome.runtime.sendMessage)
[background.js — Service Worker]
        ↓  (HTTP POST)
[FastAPI server — localhost:8000]
        ↓
[SQLite DB — prompts.db]
```

| Layer | Technology |
|-------|------------|
| Browser extension | Chrome Manifest V3, Vanilla JS |
| Backend server | Python FastAPI, uvicorn |
| Database | SQLite (aiosqlite) |
| Analysis engine | Python (regex, collections) |
| Popup UI | HTML / CSS / JS |

---

## 5. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Server health check |
| POST | /prompts | Store a prompt |
| GET | /prompts | List prompts |
| GET | /prompts/{id} | Get a single prompt |
| PATCH | /prompts/{id}/rating | Update star rating |
| DELETE | /prompts/{id} | Delete a prompt |
| DELETE | /prompts | Delete all prompts |
| GET | /search?q= | Search prompts |
| GET | /templates | List templates |
| POST | /templates | Save a template |
| DELETE | /templates/{id} | Delete a template |
| GET | /analysis/summary | Overall analysis summary |
| GET | /analysis/weekly | Weekly report |
| GET | /analysis/score/{id} | Score a single prompt |
| GET | /analysis/similar/{id} | Find similar prompts |
| GET | /analysis/template-suggest/{id} | Auto-suggest a template |

---

## 6. How to Run

```bash
# 1. Start the server
cd prompt-os/server
python -m uvicorn main:app --reload --port 8000

# 2. Load the extension
# chrome://extensions/ → Enable Developer mode → Load unpacked → select extension/ folder

# 3. View API docs
# http://localhost:8000/docs
```

---

## 7. Roadmap

| Priority | Item | Description |
|----------|------|-------------|
| High | Claude Code / API capture | Support interfaces beyond the browser |
| High | Score-based improvement suggestions | "Change this to get an A grade" |
| Medium | LLM-based classification and scoring | AI judges quality instead of keyword matching |
| Medium | Prompt export | Export to CSV / JSON |
| Low | Dark / light theme | Popup UI polish |
| Low | Team sharing | Share good prompts with teammates |

---

*Last updated: 2026-03-16*
