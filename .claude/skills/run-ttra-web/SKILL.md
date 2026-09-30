---
name: run-ttra-web
description: Build, run, and drive the TTRA web app (FastAPI chat/catalog site for THE TECH ROOM ARG). Use when asked to start the web app, run its tests, take a screenshot, or confirm a change works in the real app.
---

FastAPI + vanilla-JS site served by uvicorn. Start the dev server, then
drive it headlessly with `.claude/skills/run-ttra-web/driver.py`
(Playwright/Chromium — `chromium-cli` isn't installed here, so this
project uses the Python `playwright` package already vendored in
`.venv`).

All paths below are relative to the repo root (`TTRA Project/`).

## Prerequisites

Nothing to install — `.venv` already has `fastapi`, `uvicorn`, and
`playwright` with Chromium downloaded (`~/Library/Caches/ms-playwright`).
If starting from a fresh clone:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

`web/.env` must exist with `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` (and
optionally `ANTHROPIC_API_KEY`) — the app raises at request time (not at
import time) if they're missing. Copy `web/.env.example` and fill it in
if `web/.env` doesn't exist yet.

## Run (agent path)

Start the server in the background, wait for it to actually serve, then
drive it:

```bash
lsof -ti:8000 -sTCP:LISTEN | xargs -r kill   # free the port if a prior run is still up
nohup .venv/bin/uvicorn web.app:app --host 127.0.0.1 --port 8000 > /tmp/ttra-uvicorn.log 2>&1 &
for i in $(seq 1 20); do curl -sf http://127.0.0.1:8000 >/dev/null 2>&1 && break; sleep 1; done

.venv/bin/python .claude/skills/run-ttra-web/driver.py
```

The driver walks an anonymous flow — `/` (landing), `/catalogo`
(confirms the redirect to `/login.html` for a logged-out session), and
`/login` — screenshotting each step to `/tmp/ttra-shots/` and printing
the page title, final URL, any console errors, and any HTTP responses
≥400 (it ignores the expected `401` on `/api/me`, which is just the
"am I logged in" check every page fires for guests).

```bash
# override target / output dir:
.venv/bin/python .claude/skills/run-ttra-web/driver.py http://127.0.0.1:8000 /tmp/ttra-shots
```

Stop the server when done: `lsof -ti:8000 -sTCP:LISTEN | xargs -r kill`.

## Run (human path)

```bash
.venv/bin/uvicorn web.app:app --reload --port 8000
```
Open http://localhost:8000 in a browser. Ctrl-C to stop.

## Test

```bash
.venv/bin/python -m pytest tests/ -q
```
Tests fake out Supabase (`tests/fakes_supabase.py`) — no real network or
`.env` needed to run them.

## Gotchas

- **macOS has no `timeout` command.** Don't use `timeout N bash -c '...'`
  to poll for server readiness (as the generic web-app pattern suggests)
  — it errors with "command not found." Poll with a plain `for`/`sleep`
  loop instead (see above).
- **The two `401 /api/me` console errors on every page are expected**,
  not a bug — every page checks session status on load and gets 401 when
  logged out. The driver filters these out of its "failed requests"
  summary; don't chase them.
- **`web/supabase_client.get_client()` only raises at call time**, not at
  import, so `uvicorn web.app:app` can boot successfully even with a
  broken/missing `.env` — failures only surface when a route that needs
  Supabase is actually hit.
