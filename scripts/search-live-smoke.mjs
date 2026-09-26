#!/usr/bin/env node
/**
 * R15-DATA-111 opt-in live drift smoke test for the keyless T1 search engines.
 *
 * Every ddg/brave/mojeek parser is pinned only against FROZEN fixtures
 * (sidecar/tests/test_*_backend.py) — nothing catches the live markup moving
 * out from under them. This script runs ONE fixed, known-good query directly
 * against each engine's real HTTP endpoint and fails if the page's own markers
 * (the anchor classes the Python parsers key on) are missing — the same
 * "zero rows from a real page" signature keyless.py's canary_check() now
 * benches an engine for.
 *
 * NOT part of CI (no engine SLA there to keep, and a live 429 must never fail
 * a build): run it manually, or from an operator's own cron.
 *
 * Usage: node scripts/search-live-smoke.mjs
 * Exit: 0 if every engine's page still carries a real result; 1 otherwise.
 */

const CANARY_QUERY = "apple inc stock price";
const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36";
const TIMEOUT_MS = 15_000;

async function fetchText(url, options) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, { ...options, signal: controller.signal });
    return { status: resp.status, text: await resp.text() };
  } finally {
    clearTimeout(timer);
  }
}

// Each check: fetch the real page, then look for the SAME markup marker the
// Python parser's primary selector keys on plus a plausible href/title —
// "missing url/title" per the register's fix_shape.
const CHECKS = [
  {
    engine: "ddg",
    async run() {
      const { status, text } = await fetchText("https://html.duckduckgo.com/html/", {
        method: "POST",
        headers: {
          "User-Agent": USER_AGENT,
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ q: CANARY_QUERY }).toString(),
      });
      const match = /class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)<\/a>/s.exec(text);
      return { status, hasRow: Boolean(match && match[1] && match[2]) };
    },
  },
  {
    engine: "brave",
    async run() {
      const url = `https://search.brave.com/search?${new URLSearchParams({
        q: CANARY_QUERY,
        source: "web",
      })}`;
      const { status, text } = await fetchText(url, {
        headers: { "User-Agent": USER_AGENT, Accept: "text/html" },
      });
      const hasContainer = /class="snippet"[^>]*data-type="web"/.test(text);
      const hasLink = /<a\s+href="https?:\/\/[^"]+"/.test(text);
      return { status, hasRow: hasContainer && hasLink };
    },
  },
  {
    engine: "mojeek",
    async run() {
      const url = `https://www.mojeek.com/search?${new URLSearchParams({ q: CANARY_QUERY })}`;
      const { status, text } = await fetchText(url, {
        headers: { "User-Agent": USER_AGENT, Accept: "text/html" },
      });
      const hasContainer = /class="results-standard"/.test(text);
      const hasLink = /class="title"\s+href="https?:\/\/[^"]+"/.test(text);
      return { status, hasRow: hasContainer && hasLink };
    },
  },
];

let failed = false;
for (const check of CHECKS) {
  try {
    const { status, hasRow } = await check.run();
    if (status >= 200 && status < 300 && hasRow) {
      console.log(`ok   ${check.engine}: HTTP ${status}, canary row found`);
    } else {
      failed = true;
      console.error(
        `FAIL ${check.engine}: HTTP ${status}, ${hasRow ? "" : "no canary row (url/title) parsed — possible markup drift"}`,
      );
    }
  } catch (err) {
    failed = true;
    console.error(`FAIL ${check.engine}: ${err.message}`);
  }
}

process.exit(failed ? 1 : 0);
