# Textly

AI-powered text processing that transforms your writing. Deployed as a Cloudflare Worker (API) + Cloudflare Pages (frontend). Supports both OpenAI GPT and Anthropic Claude.

## Screenshots
![Main Interface](screenshots/main-interface.png)
![Sample Usage](screenshots/usage.png)

## Features

### Text Processing Modes
- **Grammar & Spelling Fix**: Correct errors while preserving your style
- **Make Formal**: Convert text to professional, business-appropriate tone
- **Make Casual**: Transform text to friendly, conversational style
- **Summarize**: Condense long texts while maintaining key points
- **Expand & Detail**: Make text more comprehensive and professional
- **Sentiment Analysis**: Detect emotional tone (positive/negative/neutral)

### Core Features
- Switch between OpenAI GPT (`gpt-4o-mini`) and Anthropic Claude (`claude-haiku-4-5`)
- Passphrase-protected access with 24-hour HMAC-signed token sessions
- Responsive web interface with side-by-side comparison of original vs processed text
- Copy processed text to clipboard with one click

## Architecture

```
Browser → Cloudflare Pages (frontend)
              ↓ POST /api/auth or /api/process
          Cloudflare Worker (API)
              ↓
          OpenAI API / Anthropic API
```

```
textly/
├── worker/                        # Cloudflare Worker (TypeScript)
│   ├── src/index.ts               # API routes: /api/auth, /api/process
│   ├── wrangler.toml
│   └── package.json
├── frontend/                      # Static site (Cloudflare Pages)
│   ├── index.html                 # Passphrase gate + main UI
│   ├── static/css/style.css
│   └── wrangler.toml
├── .github/workflows/
│   ├── deploy-worker.yml          # Deploys Worker on worker/** changes
│   └── deploy-pages.yml          # Deploys Pages on frontend/** changes
├── docs/plans/                    # Design and implementation docs
├── app.py                         # Original Flask app (reference only)
└── ai_service.py                  # Original AI service (reference only)
```

## Deployment

### Prerequisites

- Cloudflare account
- GitHub repository with Actions enabled

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token with Workers + Pages permissions |
| `CLOUDFLARE_ACCOUNT_ID` | Found on Workers & Pages overview page |
| `WORKER_URL` | Full Worker URL e.g. `https://textly-worker.<your-subdomain>.workers.dev` |

### Cloudflare Worker Secrets

Set these once via Wrangler CLI:

```bash
cd worker
npx wrangler secret put OPENAI_API_KEY
npx wrangler secret put ANTHROPIC_API_KEY
npx wrangler secret put PASSPHRASE
npx wrangler secret put TOKEN_SECRET   # openssl rand -hex 32
```

### Deploy

Push to `master` — GitHub Actions deploys automatically:
- Changes to `worker/**` trigger the Worker deploy
- Changes to `frontend/**` trigger the Pages deploy

Both workflows can also be triggered manually from the Actions tab.

## Usage

1. Visit your Cloudflare Pages URL
2. Enter the passphrase — valid for 24 hours
3. Enter your text, select a processing mode and AI provider
4. Click the process button and review results
