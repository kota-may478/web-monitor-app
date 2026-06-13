# Security Review — Web Monitor App

> Reviewed: 2026-06-13  
> Scope: backend/, scheduler/, frontend/

---

## Summary

| Severity | Finding | Status |
|----------|---------|--------|
| Critical | No API authentication — public endpoint accepts job registration | **Fixed** |
| High | HTML injection in email via unescaped scraped content | **Fixed** |
| High | SSRF via test-scrape endpoint (any URL accepted) | **Fixed** |
| Medium | No cron expression validation (YAML injection risk) | **Fixed** |
| Medium | No email/URL format validation in Pydantic models | **Fixed** |
| Medium | No rate limiting — Gemini quota can be exhausted | Accepted |
| Medium | Partial failure leaves orphan Secrets (secret saved, workflow push fails) | Accepted |
| Low | `allow_credentials=True` without cookie auth is unnecessary | Accepted |
| Low | GitHub Actions Node.js 20 deprecation on checkout/setup-python | Out of scope |
| Low | npm audit warnings on dev deps (vite/esbuild) | Out of scope |

---

## Fixed Issues

### Critical — API Authentication (`backend/services/auth.py`)

**Problem:** All endpoints (`/api/agent/propose`, `/api/jobs/confirm`, `/api/jobs/{id}`) were publicly accessible on the Render URL with no auth. Anyone could register monitoring jobs or delete existing ones, consuming GitHub API quota and approaching the 48-job limit.

**Fix:** Added `verify_api_key` FastAPI dependency that checks the `X-Api-Key` request header against the `API_KEY` environment variable. Applied to all routers via `dependencies=[Depends(verify_api_key)]`. If `API_KEY` is unset (local dev), auth is skipped.

**Deploy steps:**
1. Generate a random key: `openssl rand -hex 32`
2. Add `API_KEY=<key>` to Render backend service environment variables
3. Add `VITE_API_KEY=<key>` to Render frontend static site environment variables (used at build time)

**Known limitation:** `VITE_API_KEY` is bundled into the frontend JS and visible to anyone who inspects source. This is a standard SPA limitation — it prevents casual abuse but not a determined attacker who inspects the bundle. For a hobby app with a non-publicised URL this is an acceptable trade-off.

---

### High — HTML Injection in Email (`scheduler/mailer.py`)

**Problem:** `format_items_as_html()` inserted scraped `text` and `url` fields directly into HTML string literals without escaping. A malicious website could serve content containing `<script>` tags or crafted anchor hrefs that would appear verbatim in outbound emails.

**Fix:** Applied `html.escape()` to `text` and `url` before string interpolation in `format_items_as_html()`. Also applied `html.escape()` to scalar values (topic, date) substituted via `render_template()`.

---

### High — SSRF via Test-Scrape Endpoint (`backend/services/scraper.py`)

**Problem:** `POST /api/agent/test-scrape` accepted any URL including `http://localhost`, `http://169.254.169.254` (cloud metadata), and private IP ranges.

**Fix:** Added `_is_safe_url()` guard that resolves the hostname via `socket.getaddrinfo()` and rejects addresses that are loopback, private, or link-local. Applied before any HTTP fetch in `scrape_site()`.

**Note:** DNS rebinding attacks are not fully defended — full protection would require binding the resolved IP at connection time.

---

### Medium — Input Validation (`backend/models/schemas.py`)

**Fixes:** Added Pydantic `field_validator` for:
- `schedule_cron`: must match 5-field cron pattern `[0-9*,\-/]+` (no shell metacharacters)
- `email`: basic format regex
- `url` (SiteProposal, TestScrapeRequest): must be `http://` or `https://` scheme
- `max_length` on `query` (500), `schedule_label` (100), `name` (200), `description` (500), `body_template` (5000)

---

## Accepted / Not Fixed

### Medium — No Rate Limiting

**Risk:** `/api/agent/propose` calls Gemini (1,500 req/day free tier). API key auth reduces exposure. If abuse occurs, add `slowapi` or Render's built-in DDoS protection.

### Medium — Orphan Secrets on Partial Failure

**Risk:** If `push_workflow` fails after Secrets are saved, orphan Secrets accumulate. The frontend generates a new UUID on each retry, so orphans are never cleaned automatically.

**Suggested follow-up:** Use idempotent upsert — accept the UUID from the frontend, and roll back Secret saves on workflow push failure.

### Low — `allow_credentials=True` Without Cookie Auth

CORS `allow_credentials=True` is harmless now (no cookies used) but unnecessarily permissive. Remove if cookies are never added.

---

## Secrets in Logs

`GITHUB_TOKEN` is never logged. Email addresses exist only in `JobDefinition` stored in GitHub Secrets (not in git). The scheduler only logs `query` (user-controlled topic text).

## CORS

`FRONTEND_URL` is the sole allowed CORS origin. Correct for production — only the configured Render static site can make cross-origin requests.
