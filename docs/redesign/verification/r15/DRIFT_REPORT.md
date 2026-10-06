# R15 Drift Report

Consolidates `stage0/DRIFT_DEPS.md` (dependency drift, JS/Rust/Python), `stage0/DRIFT_WORLD.md`
(model-pin + provider/endpoint world drift), the licence audit under `surface/licence-audit/`,
and what changed vs. the R13 baseline. Full detail lives in the two stage0 source docs; this is
the ranked, cross-cutting view. Read-only throughout — no installs, no builds, no process control,
no secret values read/echoed/logged.

## 1. Dependency drift — top 10 risks (full detail: `stage0/DRIFT_DEPS.md`)

| # | Risk | Ecosystem | Runtime? | Action |
|---|---|---|---|---|
| 1 | `@tiptap/core` 3.25.0 — 1 HIGH ReDoS + 1 MODERATE DOM-attribute injection | JS | yes | bump whole `@tiptap/*` family to >=3.31.3 |
| 2 | Python `cryptography` 48.0.0, 2 majors behind — 3 HIGH (bundled OpenSSL CVEs, Bleichenbacher oracle, cert-chain DoS) | Python | yes | highest-leverage single bump in the tree |
| 3 | `fastmcp` 3.2.4 -> 4.0.5 (major) — only fix path for 3x HIGH `mcp` SDK advisories | Python | yes (loopback-only `/mcp`) | needs a real regression pass on `mcp_capabilities()`/`FunctionTool` projection |
| 4 | `anthropic` 0.100.0->1.7.0 and `openai` 2.36.0->3.16.2, both major | Python | yes | provider SDKs sitting exactly where CLAUDE.md documents existing fragile workarounds |
| 5 | `google-genai` unpinned floor (`>=1.0`) — reproducibility gap, not just drift (2.5.0 tested vs 2.24.0 resolves fresh) | Python | yes | pin exactly before public release |
| 6 | `jugaad-data` 0.33.1 — wraps a live-scraped site, upstream shipped as recently as 2026-08-25, repo's own comment says last verified 2026-06-01 | Python | yes | highest-velocity dependency in the tree by nature |
| 7 | `starlette` 1.0.0 — 2 HIGH, one Windows-specific (`StaticFiles` SSRF/NTLM-credential theft via UNC paths) and this repo explicitly ships on Windows | Python | yes | |
| 8 | Rust `rustls` 0.23.40 — RUSTSEC-2026-0285 on the auto-updater's HTTPS path | Rust | yes | likely resolved by `cargo update` (patch-range) |
| 9 | `keyring` 3.6.3 -> 4.2.0 (major) — this exact crate already bit the repo once on a feature-flag rename (CLAUDE.md Gotchas) | Rust | yes | needs manual cross-platform `keychain_set/get` re-test before bumping |
| 10 | `autobahn` 19.11.2 — abandoned since 2019, 1 moderate open-redirect, no upstream fix path, pulled in via `kiteconnect` | Python | yes (broker path) | accept-the-risk call, paired with `oandapyV20`/`vaderSentiment` (also abandoned upstream) |

**Net runtime security exposure from `pnpm audit`:** exactly 3 items (2 `@tiptap/core`, 1
`dompurify` low/moderate on the PDF-export path) — everything else flagged is dev/build tooling
(`vitest`/`eslint`/`postcss`/the git-pinned `tauri-plugin-mcp` dev-tools feature, compiled out of
release builds per `src-tauri/Cargo.toml:16-19`).

**Not in the top 10 but worth a look:** `dompurify` (low, PDF export), `pypdf` (6 minors behind,
several open advisories, research PDF-extraction path), `ccxt` (25 patch releases behind), `PyJWT`
HS256/JWK algorithm-confusion HIGH (call-site not located this pass, verify before dismissing).

## 2. World drift — model pins, SearXNG, exchange/data endpoints (full detail: `stage0/DRIFT_WORLD.md`)

### Rotted — breaks today, needs a code change

1. **Yahoo API edge blocks plain httpx (HTTP 429), 200s to a Chrome-impersonated TLS
   fingerprint from the same IP seconds apart.** Kills the screener fast path
   (`yahoo_batch_provider.py`, `screener.py:861,1216`), the fundamentals warm cache
   (`fundamentals_warm.py:174`), and the per-symbol Yahoo news feed
   (`news_provider.py:97-99`). Payload shapes are unchanged once the request gets through —
   TLS-fingerprint gate, not an API redesign. Fix is a zero-new-dependency seam: route through
   the already-pinned `curl_cffi==0.15.0` using the existing `nse_provider.py:240-242` pattern.
2. **`perplexity/sonar-reasoning` is retired from OpenRouter.** Listed as routable at
   `sonar.py:52`; not a default anywhere, so the failure mode is "an explicit hint 404s," not a
   broken default. `resolve_model` already falls through to `SONAR_DEEP_MODEL`.

### At risk — works today, will bite

3. SearXNG image is unpinned (`searxng/searxng` -> implicit `:latest`); upstream ships 1,018
   tags with multiple builds/day — reproducibility risk, not a break (the container-absent path
   already degrades silently to the keyless floor, stamped `keyless-fallback`).
4. All three Sonar research depth pins lack `tools` in `supported_parameters` — fine today (one-
   call research model, not the agent loop) but a live trap if ever wired into a tool loop.
5. `perplexity/sonar-pro` is the single most expensive pin in the repo ($3/$15 per M, 5x
   `sonar-deep-research`'s output rate).
6. `openrouter/auto` carries a -1 price sentinel; `BudgetGuard`'s own static `PRICE_TABLE` is
   materially out of step with today's real OpenRouter rates in both directions (e.g.
   `deepseek/deepseek-v4-flash` meters ~13x over real cost; `minimax/minimax-m3` also over;
   `qwen/qwen3.7-max` and `moonshotai/kimi-k2.6` under) — not conservatively safe.
7. BSE bhavcopy comment is stale (claims ZIP, endpoint now serves plain CSV) — code already
   handles both branches, comment-only drift.
8. CLAUDE.md is stale on the deep-research backend: the `GET /system/deepresearch/probe` route
   and the described Tongyi->minimax fallback no longer exist; the frontend enum is now
   `"native" | "perplexity"` with legacy `"tongyi"` blobs coerced to native. Documentation drift.

### Healthy — verified live, no action

All nine OpenRouter chat/known-model pins exist and are tool-capable (default
`deepseek/deepseek-v4-flash` is in the global top-5 cheapest tool-capable models);
`openai/gpt-5.6-luna` confirmed at $0.20/$1.20 per M with tools; NSE direct + archives, all four
BSE endpoints, SEC/EDGAR submissions + XBRL — all 200, shapes matching parsers; `yfinance` 1.3.0
end-to-end works (own impersonating session); `alibaba/tongyi-deepresearch-30b-a3b` still
delisted exactly as the code already asserts.

## 3. Licence audit (`surface/licence-audit/*.json`)

- **pnpm production closure** — 9 licence buckets, all permissive (MIT, Apache-2.0, ISC,
  BSD-3-Clause, MPL-2.0-or-Apache, 0BSD). No GPL/AGPL/SSPL/unlicensed entries found.
- **Cargo runtime closure** (549 crates) — overwhelmingly MIT/Apache-2.0/BSD/ISC/Zlib/MPL-2.0.
  One dual-licence pair worth noting: `r-efi@5.3.0` / `r-efi@6.0.0` offer
  `MIT OR Apache-2.0 OR LGPL-2.1-or-later` — permissive under either of the first two options, not
  a forced copyleft.
- **`sidecar/requirements.txt` main closure** (145 pkgs) — one `LGPL v3` package
  (`frozendict` 2.4.7, weak copyleft, library-linkage use is standard practice); 11 packages carry
  no machine-readable licence metadata (`annotated-types`, `caio`, `exceptiongroup`, `fredapi`,
  `Incremental`, `jaraco.classes`, `markdown-it-py`, `mdurl`, `peewee`, `sdmx1`,
  `smartapi-python`) — needs manual verification before a public release, not flagged as a
  problem by construction.
- **`openbb-mcp` sidecar closure** — `frozendict` (LGPL v3) plus **8 AGPL-3.0-only packages**
  (`openbb-core`, `openbb-economy`, `openbb-equity`, `openbb-fmp`, `openbb-fred`,
  `openbb-mcp-server`, `openbb-news`, `openbb-yfinance`). The core is no longer AGPL: it was
  relicensed to **PolyForm Strict 1.0.0** (D83, commit `0c63d46`, 23 Sep), with COMMERCIAL_LICENSE.md
  the only other path. Shipping AGPL-3.0 sidecar binaries (`externalBin`) inside a PolyForm Strict /
  commercially licensed app is therefore a live licensing question, not "consistent with the
  project's own track" — Tier-4 (licensing), a fact for the operator, not a change made here.
  7 packages carry no licence metadata.
- **`sec-edgar-mcp` sidecar closure** — `sec-edgar-mcp` itself is `AGPL-3.0` (same note as above);
  **`Unidecode` 1.4.0 is plain `GPL`** (not LGPL) — also copyleft over a distributed binary, so it
  belongs in the same operator review (AGPL-3.0 is GPL-3.0 plus a network-use clause, so GPL is not
  the stricter of the two; the point is that both are copyleft inside a non-copyleft product).
  5 packages carry no licence metadata.
- No SSPL, no "custom/proprietary-incompatible" licence strings, and no licence-check tooling
  failure encountered.

## 4. What changed since the R13 baseline

- **Battery continuity, not reset.** R15's hostile-data battery deliberately excludes every name
  R13 already used (`stage0/BATTERY_EXCLUSIONS.txt`, 130 entries, sourced from R13's own exclusion
  list, its probe-names note, and its full 17-name `BATTERY_MANIFEST.md` P1-P12/S1-S5 selection,
  plus R11/R12 which fully nest inside R13's list) — R15 samples 27 *new* names
  (`battery/packs/`, `battery/diffs/`) rather than re-testing R13's set, and the R13 evidence tree
  (`docs/redesign/verification/r13/battery/`) remains the reference baseline for anything that
  needs a prior-run comparison.
- **Tongyi/deepresearch backend removed.** CLAUDE.md still describes a
  `GET /system/deepresearch/probe` route and a live Tongyi->`minimax/minimax-m3` fallback
  (world-drift item 8 above); neither exists in the current tree — the research-depth backend
  moved to a `"native" | "perplexity"` enum sometime after R13, with legacy `"tongyi"` config
  blobs coerced to native. Documentation, not code, is what's stale.
- **Trading/broker surface slated for removal** (operator decision 23 Sep 2026, after R13):
  `code-brokers-adapters` (15 findings), the order-only slice of `safety-audit`
  (`OrderConfirmationDialog`, the order-gating half of the kill switch/audit log), and the
  order-proposal half of `host-actions-proposed-changes` are all now "removed with the feature"
  in this run's register and coverage map — R13 still tested all of these as live product surface.
- **Worktree salvage confirms R13-era branches are fully absorbed.** `stage0/RECONCILE_MANIFEST.md`
  Section 1 audited 22 registered worktrees / 68 local `worktree-*` branches: every branch with
  live work ahead of `004` was superseded by a later commit that re-landed the same change
  (palette rebuilt via cmdk in `bbb15ec`, Tiptap notes via `0fe8674`+`5629f9c`, the R10-errors
  humanizer/Tradesa-removal work re-applied, etc.) — nothing pre-R13/R14 needs recovering.
- **Screener fast path regressed since R13 was last measured live**, per world-drift item 1
  above: the Yahoo httpx TLS-fingerprint block is new rot on a path R13's own DRIFT_WORLD (if run)
  would have found healthy — R13's battery diffs did not carry this failure mode.
- **Dependency posture has drifted forward across the board** since R13 (45 JS packages, 104 of
  179 Python packages behind current, per §1) — routine version drift, not a regression, but the
  major-version-behind counts (`@tiptap/*`, `cryptography`, `fastmcp`, `anthropic`, `openai`) are
  each at least one more minor/patch cycle stale than they would have been at R13 time, simply by
  elapsed time.

## Method / evidence pointers

- `stage0/DRIFT_DEPS.md` (302 lines) — full JS/Rust/Python dependency + OSV.dev vulnerability
  sweep, with every `pnpm audit`/`pip list --outdated`/crates.io/OSV query documented.
- `stage0/DRIFT_WORLD.md` (321 lines) — live OpenRouter catalog cross-check, SearXNG image/degrade
  probe, NSE/BSE/Yahoo/SEC endpoint probes (one GET per host, >=1.2s apart).
- `surface/licence-audit/{pnpm-prod-licenses,cargo-runtime-licenses,pip-main-sidecar,
  pip-openbb-mcp,pip-sec-edgar-mcp}.json` — raw machine-readable licence closures.
- `stage0/RECONCILE_MANIFEST.md` / `.json` — worktree/branch reconciliation against `004`.
- `stage0/BATTERY_EXCLUSIONS.txt` — the R11/R12/R13 name exclusion list R15's battery built on.
- `docs/redesign/verification/r13/battery/` — the R13 baseline evidence tree itself.
