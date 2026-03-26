# Cloudflare Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate Textly from a Flask/Python app to a Cloudflare Worker (API) + Cloudflare Pages (frontend), deployed via GitHub Actions.

**Architecture:** Static HTML/CSS/JS served from Cloudflare Pages calls a TypeScript Cloudflare Worker at `POST /api/process`. The Worker routes requests to OpenAI or Anthropic based on the `provider` field. Cloudflare Access (configured in dashboard) restricts access.

**Tech Stack:** TypeScript, Cloudflare Workers, Cloudflare Pages, Wrangler CLI, GitHub Actions

---

## Task 1: Worker project scaffold

**Files:**
- Create: `worker/wrangler.toml`
- Create: `worker/tsconfig.json`
- Create: `worker/package.json`
- Create: `worker/src/index.ts` (stub only)

**Step 1: Create `worker/` directory structure**

```bash
mkdir -p worker/src
```

**Step 2: Create `worker/package.json`**

```json
{
  "name": "textly-worker",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy"
  },
  "devDependencies": {
    "@cloudflare/workers-types": "^4.0.0",
    "typescript": "^5.0.0",
    "wrangler": "^3.0.0"
  }
}
```

**Step 3: Create `worker/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2021",
    "lib": ["ES2021"],
    "module": "ES2022",
    "moduleResolution": "bundler",
    "types": ["@cloudflare/workers-types"],
    "strict": true,
    "noEmit": true
  },
  "include": ["src/**/*.ts"]
}
```

**Step 4: Create `worker/wrangler.toml`**

```toml
name = "textly-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[vars]
ENVIRONMENT = "production"
```

**Step 5: Create stub `worker/src/index.ts`**

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return new Response("OK");
  },
};

interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
}
```

**Step 6: Install dependencies**

```bash
cd worker && npm install
```

Expected: `node_modules/` created, no errors.

**Step 7: Commit**

```bash
git add worker/
git commit -m "feat: scaffold Cloudflare Worker project"
```

---

## Task 2: Implement prompt definitions in Worker

**Files:**
- Modify: `worker/src/index.ts`

These are the exact prompts ported from `ai_service.py`. Add them as a constant before the default export.

**Step 1: Add prompts constant to `worker/src/index.ts`**

Replace the stub contents with:

```typescript
interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
}

interface ProcessRequest {
  text: string;
  mode: string;
  provider: "openai" | "claude";
}

const MODE_LABELS: Record<string, string> = {
  fix: "Corrected Text",
  rewrite_formal: "Formal Version",
  rewrite_casual: "Casual Version",
  summarize: "Summary",
  expand: "Expanded Text",
  sentiment: "Sentiment Analysis",
};

interface PromptConfig {
  system: string;
  user: string;
  maxTokens: number;
  temperature: number;
}

function getPrompt(text: string, mode: string): PromptConfig {
  const highTemp = 0.3;
  const lowTemp = 0.1;
  const highTokens = 1500;
  const lowTokens = 1000;

  const prompts: Record<string, PromptConfig> = {
    fix: {
      system:
        "You are a helpful grammar correction assistant. Fix only grammar and spelling errors while preserving the original tone, style, and meaning of the text. Return only the corrected text without any additional commentary.",
      user: text,
      maxTokens: lowTokens,
      temperature: lowTemp,
    },
    rewrite_formal: {
      system:
        "You are a professional writing assistant. Convert the given text to a formal, professional tone while maintaining the original meaning and key information. Use proper business language, avoid contractions, and ensure professional vocabulary.",
      user: `Convert this text to formal/professional tone:\n\n${text}`,
      maxTokens: lowTokens,
      temperature: highTemp,
    },
    rewrite_casual: {
      system:
        "You are a friendly writing assistant. Convert the given text to a casual, conversational tone while maintaining the original meaning and key information. Use contractions, informal language, and a friendly approach.",
      user: `Convert this text to casual/conversational tone:\n\n${text}`,
      maxTokens: lowTokens,
      temperature: highTemp,
    },
    summarize: {
      system:
        "You are a summarization expert. Create a concise summary that captures the main points and key information from the original text. Maintain the essential meaning while significantly reducing length.",
      user: `Summarize the following text, keeping the key points:\n\n${text}`,
      maxTokens: lowTokens,
      temperature: lowTemp,
    },
    expand: {
      system:
        "You are a professional writing assistant. Expand the given text to be more detailed, comprehensive, and professional while maintaining the original meaning and tone. Add relevant context, examples, or elaboration where appropriate.",
      user: `Expand this text to be more detailed and professional:\n\n${text}`,
      maxTokens: highTokens,
      temperature: highTemp,
    },
    sentiment: {
      system:
        "You are a sentiment analysis expert. Analyze the emotional tone of the given text and classify it as: Positive, Negative, or Neutral. Also provide a brief explanation of the key emotional indicators you identified. Format your response as: 'Sentiment: [Classification]\\nAnalysis: [Brief explanation]'",
      user: `Analyze the sentiment of this text:\n\n${text}`,
      maxTokens: highTokens,
      temperature: lowTemp,
    },
  };

  if (!prompts[mode]) throw new Error(`Unsupported mode: ${mode}`);
  return prompts[mode];
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return new Response("OK");
  },
};
```

**Step 2: Verify TypeScript compiles**

```bash
cd worker && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: add prompt definitions to Worker"
```

---

## Task 3: Implement OpenAI call in Worker

**Files:**
- Modify: `worker/src/index.ts`

**Step 1: Add `callOpenAI` function after `getPrompt`**

```typescript
async function callOpenAI(env: Env, text: string, mode: string): Promise<string> {
  const prompt = getPrompt(text, mode);

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: prompt.system },
        { role: "user", content: prompt.user },
      ],
      max_tokens: prompt.maxTokens,
      temperature: prompt.temperature,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`OpenAI API error: ${err}`);
  }

  const data = (await response.json()) as { choices: { message: { content: string } }[] };
  return data.choices[0].message.content.trim();
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd worker && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: add OpenAI call to Worker"
```

---

## Task 4: Implement Anthropic call in Worker

**Files:**
- Modify: `worker/src/index.ts`

**Step 1: Add `callAnthropic` function after `callOpenAI`**

```typescript
async function callAnthropic(env: Env, text: string, mode: string): Promise<string> {
  const prompt = getPrompt(text, mode);

  // Anthropic uses a single user message with system passed separately
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-haiku-4-5-20251001",
      max_tokens: prompt.maxTokens,
      system: prompt.system,
      messages: [{ role: "user", content: prompt.user }],
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Anthropic API error: ${err}`);
  }

  const data = (await response.json()) as { content: { text: string }[] };
  return data.content[0].text.trim();
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd worker && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: add Anthropic call to Worker"
```

---

## Task 5: Implement the Worker request handler

**Files:**
- Modify: `worker/src/index.ts`

**Step 1: Replace the stub `fetch` handler**

```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);

    if (url.pathname === "/api/process" && request.method === "POST") {
      try {
        const body = (await request.json()) as ProcessRequest;
        const { text, mode, provider } = body;

        if (!text || !text.trim()) {
          return Response.json(
            { error: "Please enter some text to process." },
            { status: 400, headers: corsHeaders }
          );
        }

        if (!MODE_LABELS[mode]) {
          return Response.json(
            { error: `Unsupported mode: ${mode}` },
            { status: 400, headers: corsHeaders }
          );
        }

        let result: string;
        if (provider === "openai") {
          result = await callOpenAI(env, text.trim(), mode);
        } else if (provider === "claude") {
          result = await callAnthropic(env, text.trim(), mode);
        } else {
          return Response.json(
            { error: `Unsupported provider: ${provider}` },
            { status: 400, headers: corsHeaders }
          );
        }

        return Response.json(
          {
            success: true,
            original_text: text.trim(),
            processed_text: result,
            provider,
            mode,
            mode_label: MODE_LABELS[mode],
          },
          { headers: corsHeaders }
        );
      } catch (err) {
        return Response.json(
          { error: (err as Error).message },
          { status: 500, headers: corsHeaders }
        );
      }
    }

    return new Response("Not Found", { status: 404 });
  },
};
```

**Step 2: Verify TypeScript compiles**

```bash
cd worker && npx tsc --noEmit
```

Expected: No errors.

**Step 3: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: implement Worker request handler"
```

---

## Task 6: Frontend — convert template to static HTML

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/static/css/style.css` (copy from existing)

The existing template already uses AJAX (`fetch('/process', ...)`). We just need to:
1. Remove Jinja2 template syntax
2. Change the fetch URL to point to the Worker
3. Change form `action` attribute (it's ignored by the JS anyway)

**Step 1: Copy the CSS**

```bash
mkdir -p frontend/static/css
cp static/css/style.css frontend/static/css/style.css
```

**Step 2: Create `frontend/index.html`**

Copy `templates/index.html` and make these changes:
- Remove `{% with messages %}...{% endwith %}` block (lines 17-25) — replaced by JS `showError()`
- Change `<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">` to `<link rel="stylesheet" href="/static/css/style.css">`
- Change `<form id="grammarForm" method="POST" action="{{ url_for('process_text') }}">` to `<form id="grammarForm">`
- Remove `{{ 'selected' if mode == 'fix' else '' }}` etc. from `<option>` tags (just remove those attributes — first option is selected by default)
- Change `<textarea ... >{{ original_text or '' }}</textarea>` to `<textarea id="text" name="text" rows="8" placeholder="Type or paste your text here..." required></textarea>`
- Remove `{% if processed_text or corrected_text %}...{% endif %}` block (lines 67-91) — results are injected by JS
- Change `<p>Powered by {{ provider or 'AI' | title }} • Textly</p>` to `<p>Powered by AI • Textly</p>`
- Change the `fetch` URL in the JS from `'/process'` to `'WORKER_URL/api/process'`
- Change `body: formData` to send JSON instead of FormData (Worker reads JSON):

```javascript
fetch(WORKER_URL + '/api/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: formData.get('text'),
    mode: formData.get('mode'),
    provider: formData.get('provider')
  })
})
```

Add `const WORKER_URL = 'https://textly-worker.<your-subdomain>.workers.dev';` near the top of the `<script>` block. This will be updated with the real URL after the Worker is deployed.

**Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: add static frontend for Cloudflare Pages"
```

---

## Task 7: Cloudflare Pages config

**Files:**
- Create: `frontend/wrangler.toml`

**Step 1: Create `frontend/wrangler.toml`**

```toml
name = "textly"
pages_build_output_dir = "."
```

**Step 2: Commit**

```bash
git add frontend/wrangler.toml
git commit -m "feat: add Pages wrangler config"
```

---

## Task 8: GitHub Actions — deploy Worker

**Files:**
- Create: `.github/workflows/deploy-worker.yml`

**Step 1: Create `.github/workflows/deploy-worker.yml`**

```yaml
name: Deploy Worker

on:
  push:
    branches: [master]
    paths:
      - 'worker/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    name: Deploy Cloudflare Worker
    steps:
      - uses: actions/checkout@v4

      - name: Install Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm install
        working-directory: worker

      - name: Deploy Worker
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          workingDirectory: worker
```

**Step 2: Commit**

```bash
git add .github/workflows/deploy-worker.yml
git commit -m "ci: add GitHub Actions workflow to deploy Worker"
```

---

## Task 9: GitHub Actions — deploy Pages

**Files:**
- Create: `.github/workflows/deploy-pages.yml`

**Step 1: Create `.github/workflows/deploy-pages.yml`**

```yaml
name: Deploy Pages

on:
  push:
    branches: [master]
    paths:
      - 'frontend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    name: Deploy Cloudflare Pages
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy . --project-name=textly
          workingDirectory: frontend
```

**Step 2: Commit**

```bash
git add .github/workflows/deploy-pages.yml
git commit -m "ci: add GitHub Actions workflow to deploy Pages"
```

---

## Task 10: Set secrets and deploy

**Step 1: Add GitHub repo secrets**

In GitHub repo → Settings → Secrets and variables → Actions, add:
- `CLOUDFLARE_API_TOKEN` — create at dash.cloudflare.com → My Profile → API Tokens → "Edit Cloudflare Workers" template, also add Pages permission
- `CLOUDFLARE_ACCOUNT_ID` — found on the Workers & Pages overview page in the Cloudflare dashboard

**Step 2: Set Worker secrets via Wrangler CLI (run locally once)**

```bash
cd worker
npx wrangler secret put OPENAI_API_KEY
# (paste key when prompted)
npx wrangler secret put ANTHROPIC_API_KEY
# (paste key when prompted)
```

**Step 3: Push to master to trigger both workflows**

```bash
git push origin feature/cloudflare-deployment
```

Then open a PR to master and merge it.

**Step 4: Get the Worker URL**

After the Worker deploys, go to Cloudflare dashboard → Workers & Pages → textly-worker → copy the URL (e.g. `https://textly-worker.abc123.workers.dev`).

**Step 5: Update `WORKER_URL` in `frontend/index.html`**

Replace `'https://textly-worker.<your-subdomain>.workers.dev'` with the real URL, commit and push.

---

## Task 11: Configure Cloudflare Access (dashboard only)

**Step 1: Enable Zero Trust**

Go to Cloudflare dashboard → Zero Trust → enable (free plan).

**Step 2: Create Application for Pages**

- Access → Applications → Add Application → Self-hosted
- Application name: `Textly`
- Session duration: 24 hours
- Domain: your Pages domain (e.g. `textly.pages.dev`)
- Policy: Allow, rule: Emails → add allowed email addresses
- Save

**Step 3: Create Application for Worker API**

- Same as above but domain: `textly-worker.<subdomain>.workers.dev`
- Same email policy

---

## Task 12: Cleanup Flask files

Only do this after confirming the Cloudflare deployment works end-to-end.

**Step 1: Remove Flask-specific files**

```bash
git rm app.py ai_service.py requirements.txt
git rm -r templates/
```

**Step 2: Commit**

```bash
git commit -m "chore: remove Flask app after Cloudflare migration"
```
