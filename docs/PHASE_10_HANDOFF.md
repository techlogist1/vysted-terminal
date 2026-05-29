# Phase 10 — Handoff Report ("the shell becomes a copilot")

Single unattended session on the Mac. All work merged to `main` and pushed to
`origin`. **No tag, no release** — handed back for your personal-testing gate.

The brief: the app worked but was a data viewer with a raw LLM chat bolted on.
Phase 10 fixes every live bug, turns the chat into a real agentic copilot, ships
a real broker-integrations hub with Kite Connect read-only, retires the
amber-brass design for "Claude after dark", and persists the watchlist. §6.5 was
never reopened.

## Gate results (all green on merged main)

- **`pnpm ci-local` → exit 0** — full CI parity: install · ensure-all-sidecars
  (the main sidecar rebuilt with the copilot + broker changes) · eslint ·
  prettier · tsc · cargo fmt · clippy -D · ruff 0.15.12 · **619 vitest** ·
  6 cargo tests · **942 pytest**.
- **§6.5 safety audit → 9/9.** All six LOCKED files
  (`sidecar/models/audit_log.py`, `sidecar/models/kill_switch.py`,
  `src-tauri/src/kill_switch.rs`, `sidecar/services/broker_base.py`,
  `types/plugin.ts`, `tests/test_safety_end_to_end.py`) are **byte-identical to
  the pre-Phase-10 baseline** (`git diff 4dba230..HEAD` empty for each) —
  §6.5 holds by construction, not just by passing tests.
- **`node scripts/smoke-test-sidecars.mjs` → exit 0** — freshness gate + all
  three sidecars spawn + bind (see the run log appended at hand-back).
- **`next build` (static export) compiles** — Fraunces variable font + the
  `@tauri-apps/plugin-shell` dynamic import both resolve under static export.

## What I studied, and the decisions that came out of it

**Studied (read-only fan-out + adversarial verification, 81 agents):** the live
codebase subsystem-by-subsystem; **Fincept Terminal** (Qt6/C++ + embedded
Python, 55 screens — its declarative connector registry + persona-config format
were the adoptable patterns); **OpenBB Platform** (router-names-a-standard-model
↔ provider-implements-it decoupling; but its plaintext-JSON credential store is
the anti-pattern to avoid given our keychain); and the **real Kite Connect**
auth + the agentic-copilot tool-loop patterns. Full reports under
`docs/research/phase-10/`.

Key autonomous decisions (Tier-2/3, documented for your review):

1. **Hybrid orchestration, not blanket parallelism.** The five tracks collide
   heavily on shared files (`SettingsPanel`, `workspace.ts`, `ChatSidebar`,
   `page.tsx`, `globals.css`), and the repo's own gotchas repeatedly burned on
   parallel-worktree contamination. So: parallel agents for _read/research_ and
   for _disjoint mechanical fan-out_ (the 12-file canvas reskin, the 4 LLM
   adapters); lead-driven serial surgery on shared files; all build/GUI/verify
   serial and mine. Every shared-file edit verified via `git diff`.
2. **Design: keep token NAMES, change VALUES.** Re-valuing `amber-*`→coral,
   `charcoal-*`→espresso in place re-skins 80+ consumer files with zero edits; a
   project-wide rename would be a 40+-file churn for cosmetic accuracy. Accepted
   cost: the names are now historical (an `amber-400` class renders coral) — the
   `tokens.css` comments are rewritten so nothing lies.
3. **Kite OAuth runs in the sidecar, not a new Rust loopback module.** The
   blueprint's Rust loopback listener needs 3 new crates (sha2 + an HTTP client +
   a browser opener) — a cross-OS build/clippy risk I can't fully verify, for a
   flow that's operator-manual anyway. Instead the genuine login exchange runs in
   the sidecar via the already-bundled `kiteconnect` SDK's `generate_session`
   (which does the SHA-256 checksum + `/session/token` internally). No new deps,
   fully pytest-testable. (The Rust loopback that auto-captures `request_token`
   is a documented deferred polish — manual paste works on any machine.)
4. **Copilot scope:** built the keystone (live tool loop + context + router
   persona + bare-text NL + a clickable roster + 5 adapters) to a tested, working
   state; the heavier Tier-2 `/agents/roster` metadata endpoint + 3-pane roster
   panel + hard `delegate_to_persona` are architected in the blueprint and noted
   as follow-ups.

## 1. Every live bug fixed (Phase B — `fix(phase-10)` commit)

| Bug (your report)                                          | Root cause                                                                                                                                                                                            | Fix                                                                                                                                                                                                                                                                         |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Boot crash** (`applyDefaultLayout` / parentElement null) | Track C made layout-restore async; under StrictMode/HMR the dockview api is disposed before the fetch resolves, and a plugin panel can be restored before its component registers (`fromJSON` throws) | `restoreLastSessionOrDefault` re-checks the live api after every await + skips-to-clean-default on an unknown component; `PanelHost` mounted-ref guard. `PanelHost.tsx`, `workspace.ts`                                                                                     |
| **News/Portfolio "failed to load"** on cold boot           | Rust hands the frontend a port before the sidecar binds; the cached URL had no `/health` probe and panels fetched once with no retry                                                                  | `getSidecarBaseUrl` now gates on a `/health` probe with backoff (shared, re-armable); News+Portfolio auto-retry ~50s (PyInstaller `_MEI` re-exec takes ~30s — found this on a real cold boot, the first 7s retry was too short). `sidecar-client.ts`, News/Portfolio panels |
| **Settings double-scrollbar → blue void**                  | Two nested scroll containers; the unpainted dockview over-scroll region fell through to the WKWebView backdrop                                                                                        | single clipped scroll container + paint `.dv-view`. `SettingsPanel.tsx`, `globals.css`                                                                                                                                                                                      |
| **"Set as default" only on Ollama**                        | the button was gated on key-presence; only the no-key provider showed it. Also `defaultProviderId` was in-memory only (reset to anthropic each launch)                                                | show on every non-default row + persist `defaultProviderId` via the workspace blob. `SettingsPanel.tsx`, `workspace.ts`                                                                                                                                                     |

Plus the adversarially-confirmed hunt batch: plugin-runtime + 30s-interval leak
on early teardown; KillSwitch listener leak + a visible fire-failure banner;
screener desc-sort floating null market-caps to the top; portfolio zero-cost-
basis rendering `+0.00%`; FastAPI 422 rendering `[object Object]`; screener
`currency` silently returning zero rows; earnings equal-time chart crash; the
MCP shared-session race (generation guard); workspace save/reset/restore
correctness; node-palette duplicate. New regression tests for the readiness gate

- boot-crash guards.

## 2. The copilot — architecture + how to use it (Phase D, headline)

**The unlock:** the agentic tool loop already existed in `agent_runtime.py` but
was DEAD — no adapter ever sent a `tools=` schema, so no model ever called a
tool. The keystone is the new `sidecar/services/agent_tools/schemas.py` (the tool
catalog + per-provider serializers) threaded through `stream_chat(tool_ids=…)`;
all five adapters (anthropic/openai/groq/gemini/ollama) now build + send native
tools (the OpenAI streaming-arg-reassembly bug is fixed; the assistant tool-call
turn is reconstructed via `LLMMessage.metadata` so multi-round use associates).

- **Terminal-aware:** `src/modules/chat/context-provider.ts` captures a
  structured `TerminalState` (focused symbol, charts, watchlist, portfolio, open
  panels); the runtime renders a terse preamble with the deixis line ("this"/"it"
  → focused symbol) + a `get_terminal_state` pull tool.
- **Drives the terminal:** `set_chart_symbol` / `open_panel` / `add_to_watchlist`
  execute on the host on `tool_use`; `propose_order` only prepares a
  review-required order (never places — §6.5 grep stays green).
- **Discoverable personas:** a clickable roster strip replaces the `<select>`;
  the default `copilot` router persona means bare text just works; `/ask` stays
  the raw-passthrough escape hatch.

**How to use it:** open the AI panel, type plainly — "how's my portfolio?",
"is this cheap?" (with a chart focused), "pull up TSLA", "add NVDA to my
watchlist". Click a persona chip (Buffett, Graham, …) to switch lens.
**You must add a provider key first** (Settings → AI Providers). The logged
end-to-end proof that the loop runs + answers from live state + calls a terminal
tool is `sidecar/tests/test_tool_loop_e2e.py` (a real LLM call needs your BYOK
key — the harness has none).

## 3. Broker + integrations hub — how to connect Kite (Phase E, headline)

**Where:** Settings → **Integrations** (the discoverable surface) lists Zerodha,
Dhan, Angel One with a Connect button.

**Kite Connect (the real OAuth, not a static paste):**

1. Create an app at the Kite developer console; set its redirect URL to
   `http://127.0.0.1:43117/kite/callback`.
2. In the Connect card, paste your **API key + API secret**, click **Connect with
   Zerodha** → the system browser opens the Kite login.
3. After logging in you land on the redirect URL carrying a one-time
   `request_token` — paste that URL (or the token) back into the card.
4. The sidecar exchanges it for the **daily access token** (`generate_session`
   does the SHA-256 checksum + `/session/token`; your **api_secret is used only
   for this exchange — never stored, never echoed**) and connects read-only.

**What you get:** read-only positions/holdings/P&L (equity now = `margins.net`,
not just cash; intraday/F&O positions merged with long-term holdings — both were
wrong/invisible before). New `GET /brokers/{id}/positions|holdings|margins`,
`POST /brokers/{id}/disconnect`, and a 419 "reconnect" cue when the daily token
expires. The `broker_portfolio` agent tool lets the copilot analyse your **real**
account ("is my Zerodha portfolio overexposed?"). **Dhan + Angel One** slot into
the same routes + the same Connect card (static-token / live-TOTP flows).

**Order execution stays OUT.** Every new route is a GET or a token/connection
POST; no new `_place_confirmed` call site; §6.5 untouched.

## 4. Design system — "Claude after dark" (Phase C)

Warm espresso near-black base, a single coral/clay accent (`#d97757`), cream
text, **Fraunces** humanist display serif over JetBrains Mono, de-skeuomorphized
(no brass bezels / CRT bloom). New coral-pip + Fraunces wordmark.
`styles/tokens.css` + `src/app/globals.css` are the source of truth;
`src/lib/chart-theme.ts` single-sources the 12 canvas files (and fixed 3 values
that had silently drifted off-palette, including a forbidden cyan). Full spec:
`docs/DESIGN_SYSTEM.md`.

## 5. Customizability (Phase F) + what's deferred

Persisted the **watchlist** across relaunch (it was in-memory only) via the
workspace blob — completing the "it's yours" loop alongside persistent
layouts/named workspaces, the integrations hub, the terminal-driving copilot,
and the themeable design system. The larger build-your-own surfaces from
`docs/research/phase-10/blueprint-customizability.md` (data-source/connector hub,
panel gallery, saved screens, command-palette-as-action-driver) are architected
there and left as follow-ups.

## 6. What remains for YOUR validation (honest limits)

- **Visual sign-off is yours (per the CLAUDE.md visual protocol).** The harness
  cannot drive the Tauri webview with real data, and mid-session macOS screen
  capture degraded to an `SCContentFilter` failure — so the populated-state
  screenshots at both resolutions are operator-manual. Named checks: the
  **coral-vs-loss-red** legibility in a populated Watchlist/Portfolio against a
  coral button (pre-approved fallback negative `#d6493a`); that **Fraunces**
  actually loads (not the Georgia fallback); the boot/Settings/News/Portfolio
  fixes render as described. (I did confirm a clean boot + Settings + populated
  Portfolio early in the session before capture broke — see the session log.)
- **Live copilot demo needs your BYOK key.** The loop is proven end-to-end with a
  mocked provider (`test_tool_loop_e2e.py`); a real answer needs a key in
  Settings → AI Providers.
- **Live Kite round-trip needs a real Zerodha app** (api_key/secret + the
  registered redirect URL). The exchange + read paths are unit-tested + curl-
  verifiable against a running sidecar; the browser handshake is operator-manual.
- **Kite request_token auto-capture (Rust loopback) is deferred** — manual paste
  is the v1 flow (see decision 3).

## 7. Verification snapshot

`ci-local` exit 0 · §6.5 9/9 + locked files byte-identical to baseline ·
smoke-test exit 0 · 619 vitest · 942 pytest · build compiles. Commit trail on
`main`: research → bug-fixes → design → copilot → integrations → watchlist, each
on its own branch merged `--no-ff`.
