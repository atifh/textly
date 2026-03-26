# Cloudflare Deployment Design

**Date:** 2026-03-26
**Project:** Textly
**Goal:** Migrate Flask app to Cloudflare Workers + Pages, deployed via GitHub Actions

---

## Overview

Rewrite the Python/Flask app as a TypeScript Cloudflare Worker (API) paired with a static Cloudflare Pages site (frontend). Access restricted via Cloudflare Access (zero-trust). Deployed automatically on push to `master` via GitHub Actions.

---

## Architecture

```
User → Cloudflare Access → Cloudflare Pages (frontend)
                                    ↓ fetch POST /api/process
                        Cloudflare Worker (API)
                                    ↓
                        OpenAI API / Anthropic API
```

**Three Cloudflare components:**

1. **Pages** — hosts the static frontend (HTML/CSS/JS). Existing Flask templates converted by removing Jinja2 syntax and moving logic to vanilla JS.
2. **Worker** — single `POST /api/process` endpoint. Stateless. API keys stored as Worker Secrets.
3. **Cloudflare Access** — wraps both Pages and Worker. Email allowlist policy. Free tier (up to 50 users).

---

## Cloudflare Worker (API)

**Route:** `POST /api/process`
**Request body:** `{ text: string, mode: string, provider: "openai" | "anthropic" }`
**Response:** `{ result: string }` or `{ error: string }`

**Modes (unchanged from current app):**
- Grammar & Spelling Fix
- Make Formal
- Make Casual
- Summarize
- Expand & Detail
- Sentiment Analysis

**Provider routing:**
- `openai` → `https://api.openai.com/v1/chat/completions` using `gpt-4o-mini`
- `anthropic` → `https://api.anthropic.com/v1/messages` using `claude-haiku-4-5`

Uses native `fetch()` — no SDKs, minimal bundle size.

**Worker Secrets (set once via Wrangler CLI):**
```
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

**CORS:** Worker sets `Access-Control-Allow-Origin` to the Pages domain.

---

## Repository Structure

```
textly/
├── worker/                    # Cloudflare Worker (TypeScript)
│   ├── src/
│   │   └── index.ts
│   └── wrangler.toml
├── frontend/                  # Static site for Cloudflare Pages
│   ├── index.html
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── wrangler.toml
├── .github/
│   └── workflows/
│       ├── deploy-worker.yml
│       └── deploy-pages.yml
├── docs/
│   └── plans/
│       └── 2026-03-26-cloudflare-deployment-design.md
└── (existing Flask files — removed in cleanup commit after migration)
```

---

## GitHub Actions Deployment

**`deploy-worker.yml`** — triggers on push to `master` when `worker/` changes:
```
worker/ change → wrangler deploy → Cloudflare Worker live
```

**`deploy-pages.yml`** — triggers on push to `master` when `frontend/` changes:
```
frontend/ change → wrangler pages deploy → Cloudflare Pages live
```

**GitHub repo secrets required:**
```
CLOUDFLARE_API_TOKEN     # scoped to Workers + Pages deploy
CLOUDFLARE_ACCOUNT_ID
```

`OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are never stored in GitHub — set directly as Cloudflare Worker Secrets via Wrangler CLI.

---

## Cloudflare Access Setup (dashboard only)

1. Enable Access on Cloudflare account (free for ≤50 users)
2. Create Application for Pages domain → email allowlist policy
3. Create Application for Worker route (`/api/*`) → same policy
4. Unauthorized users hit a Cloudflare-hosted login page

---

## Migration Steps

1. Create `worker/` — port `ai_service.py` + Flask route to TypeScript
2. Create `frontend/` — strip Jinja2 from templates, point `fetch` at Worker URL
3. Add `wrangler.toml` for both Worker and Pages
4. Add GitHub Actions workflows
5. Set GitHub secrets (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`)
6. Set Worker secrets via Wrangler CLI (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
7. Push to `master` — both workflows deploy
8. Configure Cloudflare Access in dashboard
9. Cleanup commit removing Flask files (`app.py`, `ai_service.py`, `requirements.txt`, `templates/`)

---

## Constraints

- Cloudflare Workers free plan: 100,000 requests/day, 10ms CPU time per request
- No persistent state — Textly is stateless so this is a perfect fit
- No filesystem access in Workers — all prompts hardcoded in TypeScript
