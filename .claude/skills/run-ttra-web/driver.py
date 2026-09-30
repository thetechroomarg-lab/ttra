#!/usr/bin/env python3
"""Drive the TTRA FastAPI web app with headless Chromium (Playwright).

Usage:
    .venv/bin/python .claude/skills/run-ttra-web/driver.py [base_url] [out_dir]

Defaults: base_url=http://127.0.0.1:8000, out_dir=/tmp/ttra-shots

Requires the server already running (see SKILL.md "Run"). Walks a
representative anonymous flow — landing page, catalog redirect-to-login,
login form — screenshots each step, and prints any console/network errors
so a failure is obvious instead of a blank screenshot.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/ttra-shots")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def visit(browser, path, shot_name, expect_url_contains=None):
    page = browser.new_page()
    errors = []
    failed_requests = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("response", lambda r: failed_requests.append((r.status, r.url)) if r.status >= 400 else None)

    page.goto(BASE_URL + path, wait_until="networkidle")
    shot = OUT_DIR / shot_name
    page.screenshot(path=str(shot), full_page=True)

    print(f"== {path} ==")
    print("  title:", page.title())
    print("  final url:", page.url)
    if expect_url_contains and expect_url_contains not in page.url:
        print(f"  WARNING: expected '{expect_url_contains}' in final URL")
    if errors:
        print("  console errors:", errors)
    non_expected_fails = [f for f in failed_requests if "/api/me" not in f[1]]
    if non_expected_fails:
        print("  failed requests:", non_expected_fails)
    print("  screenshot:", shot)
    page.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        visit(browser, "/", "01-home.png")
        visit(browser, "/catalogo", "02-catalogo-redirect.png", expect_url_contains="/login")
        visit(browser, "/login", "03-login.png")

        browser.close()
    print(f"\nDone. Screenshots in {OUT_DIR}")


if __name__ == "__main__":
    main()
