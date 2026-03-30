# Passphrase Auth Design

**Date:** 2026-03-30
**Goal:** Replace broken Basic Auth (credentials hardcoded in HTML) with a secure passphrase gate backed by HMAC-signed tokens.

---

## Overview

A full-screen passphrase gate replaces the entire UI until authenticated. On success, a signed token is stored in `localStorage` with a 24-hour expiry. Every API request includes the token. The passphrase is never in the HTML.

---

## Auth Flow

1. User visits the page → sees only the passphrase gate (main UI hidden)
2. On page load, check `localStorage` for `{ token, expiresAt }` — if valid and not expired, skip gate and show main UI
3. User enters passphrase → frontend sends `POST /api/auth` with `{ passphrase }`
4. Worker compares passphrase against `PASSPHRASE` secret
5. If correct → Worker HMAC-signs the current timestamp with `TOKEN_SECRET`, returns `{ token, expiresAt }`
6. Frontend stores `{ token, expiresAt }` in `localStorage`, shows main UI
7. Every `POST /api/process` request sends `Authorization: Bearer <token>`
8. Worker verifies token signature and expiry on each request
9. If token invalid/expired → Worker returns 401, frontend clears `localStorage` and shows gate again

---

## Worker Changes

### New route: `POST /api/auth`
- Body: `{ passphrase: string }`
- Compares against `env.PASSPHRASE`
- Success: HMAC-sign `timestamp` with `env.TOKEN_SECRET` (Web Crypto API), return `{ token, expiresAt }`
- Failure: `401 { error: "Invalid passphrase" }`

### Updated route: `POST /api/process`
- Reads `Authorization: Bearer <token>` header
- Verifies HMAC signature and checks `expiresAt` not in the past
- Invalid/expired: `401 { error: "Session expired" }`
- Valid: proceed as before

### New Worker secrets
- `PASSPHRASE` — shared secret users type in
- `TOKEN_SECRET` — random string for signing tokens (never exposed)

### Removed Worker secrets
- `BASIC_AUTH_USERNAME`
- `BASIC_AUTH_PASSWORD`

---

## Frontend Changes

### Passphrase gate (new)
- Full-screen centered form shown on load if not authenticated
- Fields: password input, submit button, error message area
- On submit: POST to `/api/auth`, store token on success, show error on failure

### Token management
- Store `{ token, expiresAt }` in `localStorage` on successful auth
- Check on every page load — skip gate if valid
- Clear on 401 response from Worker — show gate again

### API requests (updated)
- Send `Authorization: Bearer <token>` on every `/api/process` request
- Handle 401 by clearing localStorage and showing gate

### deploy-pages.yml (updated)
- Remove `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` sed injections
- Keep only `WORKER_URL` injection
- Passphrase is never in the HTML

---

## Secrets Summary

| Secret | Where | Purpose |
|--------|-------|---------|
| `PASSPHRASE` | Cloudflare Worker | Validates user entry |
| `TOKEN_SECRET` | Cloudflare Worker | Signs/verifies tokens |
| `WORKER_URL` | GitHub Actions | Injected into frontend at deploy |
| `OPENAI_API_KEY` | Cloudflare Worker | OpenAI API calls |
| `ANTHROPIC_API_KEY` | Cloudflare Worker | Anthropic API calls |
