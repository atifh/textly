# Passphrase Auth Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the broken Basic Auth (credentials hardcoded in HTML) with a secure passphrase gate backed by HMAC-signed tokens stored in localStorage.

**Architecture:** The Worker gains two new routes: `POST /api/auth` validates a passphrase and issues a signed token, and the existing `POST /api/process` validates that token. The frontend shows a full-screen passphrase form on first visit; on success, the token is stored in localStorage with a 24-hour expiry and subsequent requests send it as a Bearer header.

**Tech Stack:** TypeScript (Cloudflare Worker), Web Crypto API (HMAC-SHA256), vanilla JS (frontend), localStorage

---

## Task 1: Update Worker Env interface and remove Basic Auth

**Files:**
- Modify: `worker/src/index.ts:1-6` (Env interface)
- Modify: `worker/src/index.ts:154-168` (Basic Auth block)

**Step 1: Replace the `Env` interface**

Change:
```typescript
interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
  BASIC_AUTH_USERNAME: string;
  BASIC_AUTH_PASSWORD: string;
}
```

To:
```typescript
interface Env {
  OPENAI_API_KEY: string;
  ANTHROPIC_API_KEY: string;
  PASSPHRASE: string;
  TOKEN_SECRET: string;
}
```

**Step 2: Remove the entire Basic Auth block**

Delete these lines (currently lines 154-168):
```typescript
    // Basic Auth
    const authHeader = request.headers.get("Authorization");
    if (!authHeader || !authHeader.startsWith("Basic ")) {
      return new Response("Unauthorized", {
        status: 401,
        headers: { "WWW-Authenticate": 'Basic realm="Textly"' },
      });
    }
    const [username, password] = atob(authHeader.slice(6)).split(":");
    if (username !== env.BASIC_AUTH_USERNAME || password !== env.BASIC_AUTH_PASSWORD) {
      return new Response("Unauthorized", {
        status: 401,
        headers: { "WWW-Authenticate": 'Basic realm="Textly"' },
      });
    }
```

**Step 3: Verify TypeScript compiles**

```bash
cd worker && node_modules/.bin/tsc --noEmit
```

Expected: no errors.

**Step 4: Commit**

```bash
git add worker/src/index.ts
git commit -m "refactor: replace Basic Auth env vars with PASSPHRASE and TOKEN_SECRET"
```

---

## Task 2: Add token helper functions to Worker

**Files:**
- Modify: `worker/src/index.ts` — add two functions before `export default`

**Step 1: Add `generateToken` and `verifyToken` functions**

Insert these two functions after `callAnthropic` and before `export default`:

```typescript
const TOKEN_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

async function generateToken(secret: string): Promise<{ token: string; expiresAt: number }> {
  const expiresAt = Date.now() + TOKEN_EXPIRY_MS;
  const payload = String(expiresAt);
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  const token = btoa(String.fromCharCode(...new Uint8Array(signature))) + "." + payload;
  return { token, expiresAt };
}

async function verifyToken(token: string, secret: string): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [sigB64, payload] = parts;
  const expiresAt = Number(payload);
  if (isNaN(expiresAt) || Date.now() > expiresAt) return false;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );
  let sigBytes: Uint8Array;
  try {
    sigBytes = Uint8Array.from(atob(sigB64), (c) => c.charCodeAt(0));
  } catch {
    return false;
  }
  return crypto.subtle.verify("HMAC", key, sigBytes, new TextEncoder().encode(payload));
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd worker && node_modules/.bin/tsc --noEmit
```

Expected: no errors.

**Step 3: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: add HMAC token generate/verify helpers to Worker"
```

---

## Task 3: Add `/api/auth` route and token check on `/api/process`

**Files:**
- Modify: `worker/src/index.ts` — update the fetch handler

**Step 1: Add `/api/auth` route inside the fetch handler**

After the CORS preflight block (after line `return new Response(null, { headers: corsHeaders });`) and before the `const url = new URL(request.url);` line, add nothing — instead add the auth route as a new `if` block after the `pathname` check. Replace the handler routing section:

Find:
```typescript
    const url = new URL(request.url);
    const pathname = url.pathname.replace(/\/+/g, "/");

    if (pathname === "/api/process" && request.method === "POST") {
```

Replace with:
```typescript
    const url = new URL(request.url);
    const pathname = url.pathname.replace(/\/+/g, "/");

    if (pathname === "/api/auth" && request.method === "POST") {
      let body: { passphrase?: string };
      try {
        body = (await request.json()) as { passphrase?: string };
      } catch {
        return Response.json(
          { error: "Invalid JSON body." },
          { status: 400, headers: corsHeaders }
        );
      }
      if (!body.passphrase || body.passphrase !== env.PASSPHRASE) {
        return Response.json(
          { error: "Invalid passphrase." },
          { status: 401, headers: corsHeaders }
        );
      }
      const { token, expiresAt } = await generateToken(env.TOKEN_SECRET);
      return Response.json({ token, expiresAt }, { headers: corsHeaders });
    }

    if (pathname === "/api/process" && request.method === "POST") {
      // Verify token
      const authHeader = request.headers.get("Authorization");
      if (!authHeader || !authHeader.startsWith("Bearer ")) {
        return Response.json(
          { error: "Session expired." },
          { status: 401, headers: corsHeaders }
        );
      }
      const token = authHeader.slice(7);
      const valid = await verifyToken(token, env.TOKEN_SECRET);
      if (!valid) {
        return Response.json(
          { error: "Session expired." },
          { status: 401, headers: corsHeaders }
        );
      }
```

Note: the existing `if (pathname === "/api/process" ...)` block already has its closing `}` — you are only adding the token check lines inside the existing block's opening, not replacing the whole block.

**Step 2: Verify TypeScript compiles**

```bash
cd worker && node_modules/.bin/tsc --noEmit
```

Expected: no errors.

**Step 3: Commit**

```bash
git add worker/src/index.ts
git commit -m "feat: add /api/auth route and Bearer token check on /api/process"
```

---

## Task 4: Replace frontend HTML with passphrase gate

**Files:**
- Modify: `frontend/index.html`

**Step 1: Replace the entire `frontend/index.html` with this**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Textly - AI Text Correction</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <!-- Passphrase Gate -->
    <div id="gate" class="container" style="display:none;">
        <header>
            <h1>✍️ Textly</h1>
            <p>Enter passphrase to continue</p>
        </header>
        <main>
            <form id="passphraseForm">
                <div class="form-group">
                    <label for="passphrase">Passphrase:</label>
                    <input type="password" id="passphrase" placeholder="Enter passphrase..." required style="width:100%;padding:10px;font-size:1rem;border:2px solid #e1e5e9;border-radius:8px;box-sizing:border-box;">
                </div>
                <div class="form-group">
                    <button type="submit" class="btn-primary" id="passphraseButton">🔑 Enter</button>
                </div>
                <div id="passphraseError" style="color:#e74c3c;display:none;margin-top:8px;"></div>
            </form>
        </main>
    </div>

    <!-- Main App -->
    <div id="app" class="container" style="display:none;">
        <header>
            <h1>✍️ Textly</h1>
            <p>AI-powered text processing: fix, rewrite, summarize, expand & analyze</p>
        </header>

        <main>
            <form id="grammarForm">
                <div class="form-group">
                    <label for="text">Enter your text:</label>
                    <textarea
                        id="text"
                        name="text"
                        rows="8"
                        placeholder="Type or paste your text here..."
                        required></textarea>
                </div>

                <div class="form-group">
                    <label for="mode">Processing Mode:</label>
                    <select id="mode" name="mode" onchange="updateButtonText()">
                        <option value="fix">🔧 Grammar & Spelling Fix</option>
                        <option value="rewrite_formal">👔 Make Formal</option>
                        <option value="rewrite_casual">💬 Make Casual</option>
                        <option value="summarize">📝 Summarize</option>
                        <option value="expand">📈 Expand & Detail</option>
                        <option value="sentiment">😊 Sentiment Analysis</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="provider">Choose AI Provider:</label>
                    <select id="provider" name="provider">
                        <option value="openai">OpenAI GPT</option>
                        <option value="claude">Anthropic Claude</option>
                    </select>
                </div>

                <div class="form-group">
                    <button type="submit" class="btn-primary" id="processButton">
                        <span class="button-text" id="buttonText">✨ Process Text</span>
                        <span class="loader" style="display: none;">⏳ Processing...</span>
                    </button>
                </div>
            </form>
        </main>

        <footer>
            <p>Powered by AI • Textly</p>
        </footer>
    </div>

    <script>
        const WORKER_URL = 'https://textly-worker.YOUR-SUBDOMAIN.workers.dev';
        const AUTH_KEY = 'textly_auth';

        function escapeHTML(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function getStoredAuth() {
            try {
                const raw = localStorage.getItem(AUTH_KEY);
                if (!raw) return null;
                const auth = JSON.parse(raw);
                if (!auth.token || !auth.expiresAt) return null;
                if (Date.now() > auth.expiresAt) {
                    localStorage.removeItem(AUTH_KEY);
                    return null;
                }
                return auth;
            } catch {
                return null;
            }
        }

        function storeAuth(token, expiresAt) {
            localStorage.setItem(AUTH_KEY, JSON.stringify({ token, expiresAt }));
        }

        function clearAuth() {
            localStorage.removeItem(AUTH_KEY);
            document.getElementById('app').style.display = 'none';
            document.getElementById('gate').style.display = 'block';
        }

        function showApp() {
            document.getElementById('gate').style.display = 'none';
            document.getElementById('app').style.display = 'block';
        }

        // On page load: check stored token
        document.addEventListener('DOMContentLoaded', function () {
            const auth = getStoredAuth();
            if (auth) {
                showApp();
            } else {
                document.getElementById('gate').style.display = 'block';
            }

            // Passphrase form
            document.getElementById('passphraseForm').addEventListener('submit', function (e) {
                e.preventDefault();
                const passphrase = document.getElementById('passphrase').value;
                const errorEl = document.getElementById('passphraseError');
                const button = document.getElementById('passphraseButton');
                button.disabled = true;
                button.textContent = '⏳ Checking...';
                errorEl.style.display = 'none';

                fetch(WORKER_URL.replace(/\/$/, '') + '/api/auth', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ passphrase })
                })
                .then(r => r.json())
                .then(data => {
                    button.disabled = false;
                    button.textContent = '🔑 Enter';
                    if (data.token) {
                        storeAuth(data.token, data.expiresAt);
                        showApp();
                    } else {
                        errorEl.textContent = data.error || 'Invalid passphrase.';
                        errorEl.style.display = 'block';
                    }
                })
                .catch(() => {
                    button.disabled = false;
                    button.textContent = '🔑 Enter';
                    errorEl.textContent = 'Connection error. Please try again.';
                    errorEl.style.display = 'block';
                });
            });

            // Main app form
            const form = document.getElementById('grammarForm');
            const processButton = document.getElementById('processButton');
            const buttonText = processButton.querySelector('.button-text');
            const loader = processButton.querySelector('.loader');
            const resultsContainer = document.querySelector('#app main');

            updateButtonText();

            form.addEventListener('submit', function (e) {
                e.preventDefault();

                const auth = getStoredAuth();
                if (!auth) { clearAuth(); return; }

                buttonText.style.display = 'none';
                loader.style.display = 'inline';
                processButton.disabled = true;
                processButton.style.opacity = '0.7';
                processButton.style.cursor = 'not-allowed';

                const formData = new FormData(form);

                fetch(WORKER_URL.replace(/\/$/, '') + '/api/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + auth.token
                    },
                    body: JSON.stringify({
                        text: formData.get('text'),
                        mode: formData.get('mode'),
                        provider: formData.get('provider')
                    })
                })
                .then(response => {
                    if (response.status === 401) {
                        clearAuth();
                        throw new Error('Session expired. Please enter the passphrase again.');
                    }
                    return response.json();
                })
                .then(data => {
                    buttonText.style.display = 'inline';
                    loader.style.display = 'none';
                    processButton.disabled = false;
                    processButton.style.opacity = '1';
                    processButton.style.cursor = 'pointer';

                    if (data.success) {
                        displayResults(data.original_text, data.processed_text, data.provider, data.mode_label);
                    } else {
                        showError(data.error);
                    }
                })
                .catch(error => {
                    buttonText.style.display = 'inline';
                    loader.style.display = 'none';
                    processButton.disabled = false;
                    processButton.style.opacity = '1';
                    processButton.style.cursor = 'pointer';
                    showError(error.message || 'An error occurred.');
                });
            });

            function displayResults(originalText, processedText, provider, modeLabel) {
                const existingResults = resultsContainer.querySelector('.results');
                if (existingResults) existingResults.remove();

                const resultsHTML = `
                    <div class="results">
                        <h2>✅ ${escapeHTML(modeLabel)}</h2>
                        <div class="result-box">
                            <div class="result-content">${escapeHTML(processedText)}</div>
                            <button onclick="copyToClipboard()" class="btn-copy">📋 Copy</button>
                        </div>
                        ${originalText !== processedText ? `
                        <div class="comparison">
                            <h3>📝 Original vs ${escapeHTML(modeLabel)}</h3>
                            <div class="comparison-grid">
                                <div class="original">
                                    <h4>Original:</h4>
                                    <div class="text-box">${escapeHTML(originalText)}</div>
                                </div>
                                <div class="processed">
                                    <h4>${escapeHTML(modeLabel)}:</h4>
                                    <div class="text-box">${escapeHTML(processedText)}</div>
                                </div>
                            </div>
                        </div>` : ''}
                    </div>
                `;
                resultsContainer.insertAdjacentHTML('beforeend', resultsHTML);
                const footer = document.querySelector('footer p');
                footer.textContent = `Powered by ${escapeHTML(provider.charAt(0).toUpperCase() + provider.slice(1))} • Textly`;
            }

            function showError(message) {
                const existingMessages = resultsContainer.querySelector('.messages');
                if (existingMessages) existingMessages.remove();
                resultsContainer.insertAdjacentHTML('afterbegin', `
                    <div class="messages">
                        <div class="message error">${escapeHTML(message)}</div>
                    </div>
                `);
            }
        });

        function copyToClipboard() {
            const resultContent = document.querySelector('.result-content');
            navigator.clipboard.writeText(resultContent.textContent).then(() => {
                const button = document.querySelector('.btn-copy');
                const orig = button.textContent;
                button.textContent = '✅ Copied!';
                setTimeout(() => { button.textContent = orig; }, 2000);
            });
        }

        function updateButtonText() {
            const mode = document.getElementById('mode').value;
            const buttonText = document.getElementById('buttonText');
            const buttonTexts = {
                'fix': '🔧 Fix Grammar',
                'rewrite_formal': '👔 Make Formal',
                'rewrite_casual': '💬 Make Casual',
                'summarize': '📝 Summarize',
                'expand': '📈 Expand Text',
                'sentiment': '😊 Analyze Sentiment'
            };
            buttonText.textContent = buttonTexts[mode] || '✨ Process Text';
        }
    </script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add passphrase gate to frontend with token-based auth"
```

---

## Task 5: Update deploy-pages.yml — remove Basic Auth sed injections

**Files:**
- Modify: `.github/workflows/deploy-pages.yml`

**Step 1: Replace the inject step**

Change:
```yaml
      - name: Inject Worker URL and credentials
        run: |
          sed -i "s|https://textly-worker.YOUR-SUBDOMAIN.workers.dev|${{ secrets.WORKER_URL }}|g" frontend/index.html
          sed -i "s|__BASIC_AUTH_USERNAME__|${{ secrets.BASIC_AUTH_USERNAME }}|g" frontend/index.html
          sed -i "s|__BASIC_AUTH_PASSWORD__|${{ secrets.BASIC_AUTH_PASSWORD }}|g" frontend/index.html
```

To:
```yaml
      - name: Inject Worker URL
        run: sed -i "s|https://textly-worker.YOUR-SUBDOMAIN.workers.dev|${{ secrets.WORKER_URL }}|g" frontend/index.html
```

**Step 2: Commit**

```bash
git add .github/workflows/deploy-pages.yml
git commit -m "ci: remove Basic Auth credential injection from Pages workflow"
```

---

## Task 6: Set new Worker secrets and push

**Step 1: Set Worker secrets via Wrangler (run locally in `worker/` directory)**

```bash
cd worker
npx wrangler secret put PASSPHRASE
# (enter your chosen passphrase when prompted)

npx wrangler secret put TOKEN_SECRET
# (enter a long random string, e.g. output of: openssl rand -hex 32)
```

**Step 2: Delete old Worker secrets**

```bash
npx wrangler secret delete BASIC_AUTH_USERNAME
npx wrangler secret delete BASIC_AUTH_PASSWORD
```

**Step 3: Push to trigger both workflows**

```bash
git push origin-atifh master
```

Expected: both `Deploy Worker` and `Deploy Pages` workflows trigger and succeed.
