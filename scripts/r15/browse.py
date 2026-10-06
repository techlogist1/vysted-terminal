#!/usr/bin/env python3
"""Headless browser harness for the Vysted frontend (R15). No GUI, no repo deps.

Opens the app in headless Chromium against YOUR isolated sidecar, dismisses the
first-run overlays, optionally opens panels (command palette) / clicks toolbar
controls, waits for the sidecar traffic to go quiet, then saves:

    <out>/<name>.png           viewport screenshot (registered in CAPTURES.jsonl)
    <out>/<name>.txt           document.body.innerText
    <out>/<name>.report.json   console errors/warnings, page errors, failed requests,
                               HTTP >= 400, blocked requests, origins contacted, timings

    python3 scripts/r15/browse.py --port 52243 --name cockpit-1920
    python3 scripts/r15/browse.py --port 52243 --viewport 960x600 --name cockpit-960
    python3 scripts/r15/browse.py --port 52243 --panel Screener --wait-text "Market cap"
    python3 scripts/r15/browse.py --port 52243 --click '[aria-label="Open settings"]'
    python3 scripts/r15/browse.py --selftest

Setup (once; scratch venv, never the repo's deps). Playwright 1.58.0 pairs with the
chromium-1208 build already in ~/Library/Caches/ms-playwright, so nothing downloads:

    python3 -m venv /tmp/claude-501/r15-browser/venv
    /tmp/claude-501/r15-browser/venv/bin/pip install playwright==1.58.0

Safety: the vite dev server on :5173 is the operator's — a page load is GET-only, and
this harness ABORTS any non-GET request that is not addressed to --port, so a wiring
mistake can never write to his session. Exit 0 = captured (console errors are data,
not failure); 2 = app shell never mounted / panel or control not found.
"""

import argparse
import collections
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.parse

VENV_PY = "/tmp/claude-501/r15-browser/venv/bin/python"
ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "docs/redesign/verification/r15/surface/browser-harness"
SHELL_READY = '[aria-label="Open command palette"]'  # src/app/page.tsx:246
TOS_ACCEPT = '[data-testid="first-launch-tos-accept"]'  # DisclaimerFlow.tsx
ONBOARDING = '[data-testid="onboarding-flow"]'  # OnboardingFlow.tsx:158
PALETTE_INPUT = "[cmdk-input]"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
LOOPBACK = {"127.0.0.1", "localhost", "[::1]", "::1"}


def parse_viewport(text):
    w, _, h = text.lower().partition("x")
    w, h = int(w), int(h)
    if w < 200 or h < 200:
        raise ValueError("viewport too small: %s" % text)
    return w, h


def request_allowed(method, url, sidecar_port):
    """Non-GET traffic may only reach the isolated sidecar on `sidecar_port`."""
    if method.upper() in SAFE_METHODS:
        return True
    u = urllib.parse.urlsplit(url)
    return u.hostname in LOOPBACK and u.port == sidecar_port


def selftest():
    assert parse_viewport("1920x1080") == (1920, 1080)
    assert parse_viewport("960X600") == (960, 600)
    for bad in ("960", "10x10", "axb"):
        try:
            parse_viewport(bad)
        except ValueError:
            continue
        raise AssertionError("accepted bad viewport %r" % bad)
    assert request_allowed("GET", "http://localhost:5173/src/app/page.tsx", 52243)
    assert request_allowed("POST", "http://127.0.0.1:52243/workspace/autosave", 52243)
    assert not request_allowed(
        "POST", "http://127.0.0.1:52052/workspace/autosave", 52243
    )
    assert not request_allowed("PUT", "http://localhost:5173/x", 52243)
    assert not request_allowed("POST", "https://example.com/t", 52243)
    assert not request_allowed("DELETE", "http://127.0.0.1/x", 52243)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--port", type=int, help="YOUR isolated sidecar port (required)")
    ap.add_argument("--base", default="http://localhost:5173/", help="frontend URL")
    ap.add_argument(
        "--viewport", default="1920x1080", help="WxH (app minimum is 960x600)"
    )
    ap.add_argument(
        "--panel", action="append", default=[], help="open via palette (repeatable)"
    )
    ap.add_argument(
        "--click", action="append", default=[], help="CSS/text selector to click"
    )
    ap.add_argument("--wait-text", help="also wait for this text to be visible")
    ap.add_argument(
        "--settle", type=float, default=45, help="max seconds to wait for data"
    )
    ap.add_argument(
        "--quiet", type=float, default=2.0, help="seconds of no sidecar traffic"
    )
    ap.add_argument(
        "--keep-overlays", action="store_true", help="do not dismiss TOS/onboarding"
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--name", default=None, help="file stem (default: derived)")
    ap.add_argument("--no-register", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.port:
        ap.error("--port is required")

    from playwright.sync_api import TimeoutError as PwTimeout
    from playwright.sync_api import sync_playwright

    width, height = parse_viewport(args.viewport)
    stem = args.name or "-".join(
        [p.lower().replace(" ", "_") for p in args.panel] or ["cockpit"]
    ) + "-%dx%d" % (width, height)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    url = "%s?sidecar-port=%d" % (args.base, args.port)
    sidecar_prefix = (
        "http://127.0.0.1:%d" % args.port,
        "http://localhost:%d" % args.port,
    )

    events = collections.OrderedDict()  # (kind, method, url/text) -> entry with count
    origins = collections.Counter()
    inflight = {}
    last_activity = [time.monotonic()]
    t0 = time.monotonic()

    def note(kind, text, **extra):
        key = (kind, extra.get("method", ""), extra.get("url", ""), text)
        if key in events:
            events[key]["count"] += 1
            return
        events[key] = dict(
            kind=kind, text=text, count=1, t=round(time.monotonic() - t0, 2), **extra
        )

    def on_request(req):
        u = urllib.parse.urlsplit(req.url)
        if u.scheme in ("http", "https", "ws", "wss"):
            origins["%s://%s" % (u.scheme, u.netloc)] += 1
        if req.url.startswith(sidecar_prefix):
            inflight[req] = time.monotonic()
            last_activity[0] = time.monotonic()

    def on_done(req):
        if inflight.pop(req, None) is not None:
            last_activity[0] = time.monotonic()

    def on_failed(req):
        on_done(req)
        note("requestfailed", req.failure or "failed", method=req.method, url=req.url)

    def on_response(resp):
        if resp.status >= 400:
            note("http", str(resp.status), method=resp.request.method, url=resp.url)

    def on_console(msg):
        if msg.type in ("error", "warning"):
            loc = msg.location or {}
            where = "%s:%s" % (loc.get("url", ""), loc.get("lineNumber", ""))
            note("console." + msg.type, msg.text, where=where)

    def guard(route):
        req = route.request
        if request_allowed(req.method, req.url, args.port):
            return route.continue_()
        note(
            "blocked",
            "non-GET outside the isolated sidecar",
            method=req.method,
            url=req.url,
        )
        return route.abort()

    def settle(page, cap):
        """Wait until the sidecar has been quiet for --quiet seconds (or `cap`)."""
        deadline = time.monotonic() + cap
        while time.monotonic() < deadline:
            page.wait_for_timeout(250)  # pumps Playwright events
            if not inflight and time.monotonic() - last_activity[0] >= args.quiet:
                return True
        return False

    status, problems = 0, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            color_scheme="dark",
        )
        page = ctx.new_page()
        page.route("**/*", guard)
        page.on("request", on_request)
        page.on("requestfinished", on_done)
        page.on("requestfailed", on_failed)
        page.on("response", on_response)
        page.on("console", on_console)
        page.on("pageerror", lambda err: note("pageerror", str(err)))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector(SHELL_READY, state="attached", timeout=60000)
            shell_ms = round((time.monotonic() - t0) * 1000)

            overlays = []
            if not args.keep_overlays:
                # Both overlays mount after an async probe; give them a moment, then
                # dismiss whichever is up. Neither closes on Escape by design.
                for _ in range(40):
                    page.wait_for_timeout(250)
                    tos = page.locator(TOS_ACCEPT)
                    onb = page.locator(ONBOARDING)
                    if tos.count() and tos.first.is_visible():
                        tos.first.click()
                        overlays.append("tos")
                    elif onb.count() and onb.first.is_visible():
                        onb.get_by_role("button", name="Skip").first.click()
                        overlays.append("onboarding")
                    elif overlays or _ >= 16:  # dismissed, or 4 s with nothing up
                        break
                if page.locator("%s, %s" % (TOS_ACCEPT, ONBOARDING)).count():
                    problems.append(
                        "overlay still mounted after dismiss: %s" % overlays
                    )

            for name in args.panel:
                page.click(SHELL_READY)
                page.fill(PALETTE_INPUT, name)
                rows = page.locator('[cmdk-item][data-value^="panel:" i]')
                hit = rows.filter(has_text=name).first
                try:
                    hit.click(timeout=5000)
                except PwTimeout:
                    problems.append(
                        "panel %r not in palette; rows=%s"
                        % (name, rows.all_inner_texts())
                    )
                    page.keyboard.press("Escape")
                    status = 2
            for sel in args.click:
                try:
                    page.locator(sel).first.click(timeout=5000)
                except PwTimeout:
                    problems.append("click target not found: %s" % sel)
                    status = 2

            settled = settle(page, args.settle)
            if args.wait_text:
                try:
                    page.get_by_text(args.wait_text).first.wait_for(
                        timeout=args.settle * 1000
                    )
                except PwTimeout:
                    problems.append("wait-text never appeared: %r" % args.wait_text)
            stuck = sorted({r.url for r in inflight})
        except PwTimeout as exc:
            problems.append("app shell never mounted: %s" % str(exc).splitlines()[0])
            status, shell_ms, overlays, settled, stuck = 2, None, [], False, []

        png = out / (stem + ".png")
        page.screenshot(path=str(png))
        text = page.evaluate("document.body.innerText")
        (out / (stem + ".txt")).write_text(text, encoding="utf-8")
        title = page.title()
        browser_version = browser.version
        browser.close()

    report = {
        "url": url,
        "viewport": [width, height],
        "browser": "chromium " + browser_version,
        "title": title,
        "shell_ready_ms": shell_ms,
        "overlays_dismissed": overlays,
        "panels": args.panel,
        "clicks": args.click,
        "settled": settled,
        "still_in_flight_at_cap": stuck,
        "problems": problems,
        "origins_contacted": dict(origins.most_common()),
        "events": list(events.values()),
        "dom_text_chars": len(text),
    }
    (out / (stem + ".report.json")).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    if not args.no_register:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/rig/register_capture.py"),
                str(png),
                "--tool",
                "browse.py",
            ],
            check=False,
        )
    kinds = collections.Counter(e["kind"] for e in events.values())
    print(
        "%s  shell=%sms settled=%s overlays=%s events=%s"
        % (png, shell_ms, settled, overlays, dict(kinds))
    )
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    return status


if __name__ == "__main__":
    try:
        import playwright  # noqa: F401
    except ImportError:
        venv = os.path.realpath(os.path.dirname(os.path.dirname(VENV_PY)))
        if os.path.exists(VENV_PY) and os.path.realpath(sys.prefix) != venv:
            os.execv(VENV_PY, [VENV_PY] + sys.argv)  # re-run under the scratch venv
        sys.exit("playwright missing — see Setup in this file's docstring")
    sys.exit(main())
