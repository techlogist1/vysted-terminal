# Wave-2 task specs (Surface bug bash, research funnel, probes, audits)

Paths relative to repo root. `CENSUS` = `docs/redesign/verification/r15/census`. Every task
writes RAW FINDINGS (shape in COMMON.md) to `CENSUS/raw/<task-id>.json` with raw_id prefix
`<TASK-ID>` upper-cased, plus a readable evidence file under
`docs/redesign/verification/r15/surface/<task-id>/` (transcripts, request/response excerpts).
If your task gives you a `<port>`, start YOUR OWN sidecar on it (COMMON.md has the command)
with a data dir you create under `/tmp/claude-501/r15-<task-id>/data` — copy the operator's
data safely (`r15/stage0/ISOLATION_MAP.md` §1a: sqlite `.backup`, autosave blob, never the
keystore; seed `dev-keystore.json` with `{"secrets": {}, "migrated": true}`) unless the task
says CLEAN profile — and stop it when done. LLM-backed calls ONLY via
`python3 scripts/r15/vy.py invoke <agent> "<prompt>" --provider openrouter --port <port> --tag <task-id>`
(free lane by default; `--out <file>` saves the raw event stream; see `--help`). Budget: at
most 14 LLM-backed invokes per task unless stated. The HTTP surface is at
`/openapi.json` (111 routes); the frontend calls are in `src/lib/sidecar-client.ts`,
`src/modules/*/api.ts`.

You cannot touch the GUI. Drive the product the way the UI does: call the same endpoints
with the same payloads the panels send (read the panel's api.ts first), and READ THE PANEL
CODE for what it would render from each response — a response the panel cannot render
(null it does not guard, an error shape it does not map, an overflow it does not clamp) is a
finding with both halves cited (response + `file:line`). Test every surface for: empty,
loading, error, overflow, offline, and the tenth item in the list — not just the happy path.

## SEAT — bug-bash tester

You are `<seat>`. Behave like that person for real: pursue THEIR goals through the product end
to end (resolve → profile → research → compare → screen → watchlist → portfolio (paper) →
notes → layouts → settings), multi-turn with the agent (3-6 turn conversations, tool chains,
follow-ups that depend on earlier answers, asking it to do agent-completable actions: add to
watchlist, write a note, paper-trade, author a screen, arrange the workspace). Judge every
answer like a demanding owner: is it right (spot-check numbers against an outside source via
WebFetch/WebSearch), complete, honest about gaps, fast enough, and does the agent claim
anything it did not do? Use FRESH symbols suited to your seat — never the marquee names in
`docs/redesign/verification/r15/stage0/BATTERY_EXCLUSIONS.txt`. Log every defect the moment
you see it. Two passes: after your first pass, re-drive the areas where you found the most
smoke.

## INDUCER — induced failures at the app's edge

Induce and record EXACTLY what the user would see (HTTP status, error frame JSON, the text the
panel/chat would render per the frontend error mapping in `src/` — cite it): 401 (`--bad-key`),
no key (`--no-key`), 402 (the unfunded lane: `--provider deepseek`), 429 (find how the adapters
surface it; stub if needed by calling the adapter with a fake response in python), network
unreachable (point a provider base URL at a closed port via config/env where supported),
SearXNG down + Docker absent (the real current state: `/search/status`,
`/search/searxng/status` — does any frontend surface tell the user research is degraded?),
malformed symbols (`"   "`, `"$$$"`, 300 chars, SQL/HTML, unicode, `"RELIANCE.NS.NS"`), a
retired model slug (`z-ai/glm-4.5-air:free`), a nonsense slug, a provider returning junk
(non-JSON / truncated stream — stub the adapter). For each: honest + actionable, or silent /
misleading / a raw stack trace / a CORS-masked 500?

## FUNNEL — research funnel trace (`<query-class>`)

The operator reports THIN BRIEFS and "web search bugging out". Boring causes first, already
observed: Docker is down so SearXNG is down and the app runs on the keyless scraper tier
(`t1_keyless`: ddg/brave/mojeek with 2-3 s min intervals), and the shipped default
provider/model lane is unfunded. Your job: trace the funnel on REAL prompts for your query
class at EACH depth the product offers (normal / deep / ultra — read
`sidecar/services/research/` to learn how depth is selected; the model can be asked to use its
research tool at a given depth), logging at each stage: queries issued → results retrieved
(per engine, with failures/rate-limits) → passed relevance → extracted → cited in the brief.
Use the engine's own telemetry/execution record (`test_research_execution_record.py` shows the
shape) plus sidecar logs. Find the stage that STARVES and why (file:line), and what a user
sees. Never propose loosening a healthy filter to hide a starved retriever. Classes:
`largecap` (a large-cap NOT in the exclusions list), `microcap` (a sub-₹500 cr name),
`thematic` (e.g. "which listed Indian companies benefit from the data-centre buildout and
how exposed is each?"). Also judge the final brief against what Perplexity Finance /
screener.in would give for the same prompt (use web tools to check facts): completeness,
sourcing, every figure traceable. Budget: up to 9 research runs. Write the funnel table to
`docs/redesign/verification/r15/research/funnel-<query-class>.md`.

## PROBES (one per task id)

- `screener-probe`: cold and warm screener; a pasted screener.in-style formula; an
  agent-authored screen; the operator's standing test query (NSE IT services, market cap under
  ₹5,000 cr, P/E under 20, ROE over 15%) — validate 10 returned rows against outside truth
  (WebFetch screener.in / exchange pages): wrong inclusions, missing names that should
  qualify, stale fundamentals, unit errors (lakh / crore / million), sector misclassification,
  pagination / sort / the tenth row, rate-limit behaviour and how progress/errors are reported.
- `resolver-probe`: hammer `/resolve` (read `sidecar/services/symbol_resolver.py` +
  `resolution_policy`) with ambiguity families and collision tickers NOT in the exclusions
  list: Indian vs US same-ticker, BSE-only numeric codes, renamed symbols (old → new), recent
  listings absent from the bundled masters (e.g. JNPR / Juniper Green Energy, DHOOTTRANS,
  SUMAX on NSE Emerge), SME boards, rights-entitlement twins (DHAN-RE), company-name queries
  with Ltd/Limited/typos, ISINs, ADRs of Indian issuers (SIFY), lowercase / whitespace /
  suffix forms (`.NS`, `.BO`, `NSE:`), and nonsense. For each: what bound, confidence band, was
  it right, and is a wrong bind SILENT? How stale are the bundled masters and is there any
  refresh path (file:line)?
- `agent-behaviour`: API-level agent probes via vy.py on your own sidecar: multi-turn
  consistency (how is history threaded? read `src/modules/chat/streaming.ts`), tool chains of
  4+ tools, stop mid-stream (close the HTTP connection mid-run — does the sidecar cancel the
  upstream LLM call and tool work, or keep burning tokens? check logs), the queue, ask vs auto
  autonomy (auto must never apply an order), every agent-completable host action (watchlist,
  note, paper trade, screen, layout, publish_brief) — does the tool result claim success
  without an ack?; order placement MUST halt for human review (`propose_order` staged, nothing
  placed, `audit_orders` 0 rows in YOUR data dir) — prove it; persona agents (13 roster
  entries) each answer in role with their allow-listed tools; the `thinking` event kind: a free
  model's FINAL ANSWER text appeared streamed as `kind: thinking` events as well as `delta` —
  find whether the adapter mislabels content as thinking (file:line) and what the chat UI does
  with it.
- `security`: threat-model the local-first boundary and try to break it (read-only + your own
  instance): sidecar CORS is `allow_origins=["*"]` on a loopback port with BYOK keys in request
  BODIES — can any web page the user visits reach it (port discovery, DNS rebinding, no auth
  token / origin check)? What can it do (read portfolio/notes, burn the user's API key, write
  data, trigger SearXNG docker setup/teardown, `/system/ollama/pull`)? MCP endpoint exposure
  (`/mcp`, `mcp-endpoint.json`), plugin loading / marketplace trust, Tauri capabilities + CSP
  (`src-tauri/capabilities`, `tauri.conf.json` — READ ONLY, it is a locked file), path traversal
  in workspace / notes / export routes, SSRF via URL-taking routes (searxng url header, PDF
  fetch, web fetch tools), prompt injection from fetched web content into tool calls with side
  effects, secrets in logs. Prove each with a harmless PoC against your own instance.
- `test-quality`: tests are state — audit the suite: tautological or over-mocked tests that
  cannot fail, skipped / xfail tests and why, code special-cased to satisfy a test, money paths
  (fundamentals math, unit scaling lakh/crore, corporate-action adjustment, P&L, screener
  criteria evaluation, research citation check) with no or weak pins, flaky-by-construction
  tests (time, network, ordering). Output a ranked list of the 25 most valuable missing pins.
- `harness-design`: DESIGN (read-only; nothing is built yet) the repeatable agent SCENARIO
  HARNESS the brief mandates: scripted multi-step tasks, scored automatically, run headlessly
  against the cheapest models, doubling as a MODEL-COMPATIBILITY MATRIX across BYOK providers
  (tool loop, streaming, native search, reasoning params) with honest capability gating. Read
  `agent_runtime.py`, `services/llm/*`, `agents/*.json`, `test_agent_runtime.py`,
  `scripts/r15/vy.py`. Use the `software-design-philosophy` skill. Deliver
  `docs/redesign/verification/r15/agent/SCENARIO_HARNESS_DESIGN.md`: 20-30 concrete scenarios
  (prompt script, expected tool trajectory, programmatic pass criteria, what defect class each
  pins), runner shape (one deep module; where it lives; how it stubs vs hits live models; cost
  per full run), the matrix columns, and for each structural choice the principle behind it
  and the alternative it ruled out. Raw findings: gaps in the runtime that make behaviour
  un-checkable today.
- `route-fuzzer`: write and run a small stdlib script (keep it at
  `scripts/r15/route_fuzz.py`) that walks `/openapi.json` on YOUR sidecar and, for every GET
  route (and POST routes that are pure reads), sends: a valid call, missing params, wrong
  types, unknown symbols, huge limits, negative numbers, unicode. Flag every 500, every
  response slower than 10 s, every non-JSON error body, every stack trace, and every sibling
  inconsistency (one route 404s on unknown symbol, its sibling 200s with nulls, another 500s).
  Never call order / kill-switch / docker-setup / ollama-pull / teardown routes.
- `collector`: battery IN-APP collection. For every entry in
  `docs/redesign/verification/r15/battery/manifest.json` collect what the app says via the
  isolated sidecar `:52152`, exactly as the EquityOverview panel does (read
  `src/modules/*/api.ts` for its calls): resolve (bare symbol, name, BSE code), fundamentals
  (+ `field_meta`), quote, shareholding, dividends / corporate actions, 52-week range,
  disclosures / announcements, identity notes — politely (≥2 s between upstream-hitting
  calls; respect the Yahoo breaker at `/system/provider-health`). Save
  `docs/redesign/verification/r15/battery/collected/<slot>_<SYMBOL>.json` and write the
  collector as a re-runnable script `scripts/r15/collect_battery.py` (it becomes the
  regression battery). Then, for every name whose outside-truth pack exists under
  `battery/packs/`, diff field by field (including the subtle tier: shareholding, promoter,
  declared vs paid dividends, 52-week range, as-of dates, units) into
  `battery/diffs/<slot>_<SYMBOL>.md`, and file RAW FINDINGS (prefix `DAT`) for each mismatch
  class: wrong value shown as true = critical/high; silent blank where the world has the
  value = medium; honest labelled gap = not a finding.
- `rig-salvage`: a previous worker died mid-task in the git worktree
  `.claude/worktrees/wf_6871fdb3-621-11` (branch `worktree-agent-rig`) leaving uncommitted
  `scripts/rig/rig.py`, `scripts/rig/test_rig_guard.py`, `scripts/rig/README.md`. Work ONLY in
  that worktree. Finish the presence-safe GUI rig per its README + the spec: refuses
  click/type/capture when HIDIdleTime is below the threshold (default 900 s, never lowerable
  below 300), aborts the batch and DELETES the capture on an unexpected frontmost window,
  registers captures in `docs/redesign/verification/r15/CAPTURES.jsonl`, no flag to disable
  safety. The operator IS present: prove REFUSAL only (exit 3, no file) — perform no real
  click / keystroke / capture. Run `sidecar/.venv/bin/python3 -m pytest scripts/rig/test_rig_guard.py -q`,
  ruff-format + ruff-check the files, commit on that branch (explicit paths; do NOT push; do
  NOT commit anything under docs/redesign/verification/r15/ except
  `r15/stage0/RIG_PROOF.md`). Return the commit sha.
- `browser-harness`: build a HEADLESS browser harness for the frontend without touching the
  repo's dependencies: a scratch venv under `/tmp/claude-501/r15-browser/` with Python
  Playwright using the Chromium already cached in `~/Library/Caches/ms-playwright` (match the
  playwright version to a cached build if possible; otherwise `playwright install chromium`).
  The app runs in a plain browser via `http://localhost:5173/?sidecar-port=<port>` (the
  operator's vite dev server — GET only, which is all a page load is; see ISOLATION_MAP §1b for
  browser-mode limits: keyed chat sends do not work, onboarding overlay shows). Start your own
  sidecar on your `<port>`. Deliver `scripts/r15/browse.py` (open the app headless at a given
  viewport, dismiss onboarding, open a panel via the palette / toolbar, wait for data, save a
  screenshot + DOM text + console errors; register each PNG with
  `python3 scripts/rig/register_capture.py <png> --tool browse.py`), prove it by capturing the
  default cockpit at 1920×1080 and at the app's narrowest supported width into
  `docs/redesign/verification/r15/surface/browser-harness/`, and list every console error /
  failed request seen on a clean load as raw findings.
- `licence-audit`: read `LICENSE` and `COMMERCIAL_LICENSE.md` first (AGPL-3.0 + commercial
  dual licence). Enumerate the licences of every runtime dependency in all three ecosystems
  (pnpm `licenses list`, `cargo metadata` / Cargo.lock + crates.io, pip metadata in
  `sidecar/.venv`) and of bundled data (resolver masters, fonts, icons, the SearXNG image, the
  OpenBB / sec-edgar MCP sidecars). Flag anything incompatible with AGPL distribution OR with
  selling a commercial licence (GPL-only deps taint the commercial side; non-commercial data
  terms — yfinance/Yahoo ToS, NSE/BSE data redistribution, screener seeds), missing NOTICE /
  attribution obligations. Output `docs/redesign/verification/r15/release/LICENCE_AUDIT.md`.
- `history-secrets`: scan the FULL git history of every local branch for secrets using the
  patterns in `scripts/git-hooks/pre-push` plus entropy heuristics on added lines
  (`git log -p --all`; stream it, never load it whole; NEVER print a matched value — print
  commit, path, line, rule). Separate real hits from fixtures. Also scan tracked files for
  personal data that should not be public (absolute home paths, emails, machine names,
  account balances). Output `docs/redesign/verification/r15/release/SECRETS_HISTORY_SCAN.md`.
- `docs-truth`: audit every user- and contributor-facing doc against reality: `README.md`,
  `docs/CURRENT_STATE.md`, `CONTRIBUTING.md`, `docs/*.md` index, `BLOCKERS.md`, `CLAUDE.md`
  (e.g. it says Next.js 16 static export; package.json says Vite), `docs/SIDECAR_API.md` vs
  `/openapi.json`, `docs/PLUGIN_DEVELOPMENT.md` vs `types/plugin.ts`, install steps that would
  fail for a stranger, screenshots that show an older UI, version strings. One raw finding per
  stale claim that would mislead a stranger (area `docs`), with the true statement.
- `patch-proof`: prove the 3 Sep OpenAI patch LIVE (commit `043850c`; the paid lane, keep it
  under $0.10): via `vy.py invoke copilot ... --provider openai --model gpt-5-nano` a
  tool-using prompt must succeed (the `reasoning_effort` 400 is repaired in place — find the
  repair in the sidecar log); `--model gpt-4o-mini` with a prompt that wants web search must
  use the LOCAL web_search tool (no `web_search_options`, no 400); confirm per-model gating
  with a `*-search-preview` model only if it is listed for this key at negligible cost. Also
  list every OTHER provider adapter quirk of the same class you can find by reading
  `sidecar/services/llm/*` against the providers' current API docs (context7 / web).
  Output `docs/redesign/verification/r15/agent/PATCH_3SEP_LIVE_PROOF.md`.
- `deps-runtime`: from `docs/redesign/verification/r15/stage0/DRIFT_DEPS.md` and
  `DRIFT_WORLD.md`, turn each drift risk that is REAL for a 0.9.0 public release into a raw
  finding with the exact safe upgrade (version, what to re-test), separating runtime from
  dev-only; verify each claim against the lockfiles before filing.
