# Agent Tool-Use Plan — Build Run Report

**Branch:** `004-r4-experience-rebuild` · **Build start:** `2f0bbcd` · **Build head:** `9ed5001`
**Aggregate:** 10 commits · 68 files · +5159 / −305 · 7 new files · version frozen **0.8.0** · **no new runtime dependency** · **no merge to main**

Executed workstream-by-workstream (WS1→WS8) via subagent-driven development (per-WS implementer → spec-compliance review → code-quality review, with fix loops), each workstream committed as its own checkpoint. The lead verified every safety-critical diff by hand and ran the gates.

---

## FINAL GATE STATUS — ✅ GREEN

| Gate | Result |
|------|--------|
| `pnpm lint` (eslint) | ✅ 0 errors (1 pre-existing warning in `EquityOverviewPanel.tsx`, untouched by this build) |
| `pnpm format:check` (prettier) | ✅ clean (306 files) |
| `pnpm typecheck` (tsc --noEmit) | ✅ clean |
| `cargo fmt --check` / `clippy -D warnings` / `cargo test` | ✅ clean (zero Rust changes in this build) |
| `ruff check sidecar` / `ruff format --check` | ✅ clean (306 files) |
| `pnpm test` (vitest) | ✅ **129 files / 1109 passed** |
| `pytest` (full sidecar) | ✅ **1473 passed, 1 skipped** (network-gated live search test), 1 benign websockets DeprecationWarning |
| `test_safety_end_to_end.py` (§6.5) | ✅ **9 / 9** (re-confirmed after WS1 and WS8, the §6.5-adjacent workstreams) |
| `test_capability_catalog` / `test_mcp_catalog_parity` | ✅ parity holds after the new `market_overview` tool (roster 33→34) |
| `node scripts/ensure-all-sidecars.mjs` | ✅ main sidecar rebuilt cleanly with all changes (bse master bundles via the existing `resolver_masters` dir glob; no missing `--copy-metadata`/`--add-data`) |
| `node scripts/smoke-test-sidecars.mjs` | ✅ all sidecars boot cleanly; `/health` OK; screener/resolver OK; both MCP subprocesses bound + survived; **BSE bhavcopy probe reached the live endpoint** (validates the WS6 URL shape against the real BSE server) |

Baseline before the build was the same suite at 54-area / safety 9-9; the build added net +new tests across every workstream and the full suite grew 1409 → 1473 passing.

---

## PER-WORKSTREAM THREE-BUCKET REPORT

### WS1 — Grounding + truthful AUTO (`64a6524`)
**VERIFIED:** Server-date + stale-data directive injected into every turn's preamble. `market_overview` read_handler (read-only, SAFE-auto) added via the single-source catalog (auto-projects to TOOL_SCHEMAS/allow-list/MCP), roster 33→34, parity green. Autonomy threaded request→sidecar; non-order host-actions narrate truthfully under AUTO. **`propose_order` returns `awaiting_user_review` in EVERY mode** (verified in code + test — the §6.5 invariant holds). Read-gate loosened for inferred-read panel grounding; `propose_order` provably cannot be re-admitted (read_only=False, not in the allow-list); legacy ASK mode stays strict. Lead add-on: fixed the frontend transcript so an order under AUTO narrates "Proposed" not "Applied" (completes the truthful-narration story). Safety 9/9.
**BROKEN:** none.
**NEEDS-MANUAL-CHECK:** the keyless `ollama` qwen2.5:7b default still under-invokes tools — WS1 makes the failure *honest* (date directive + market branch + "say so if you can't fetch"); the deeper fix rides WS8 resilience and/or steering the default to a tool-capable provider (surfaced, not silently changed).

### WS2 — Reuse brief renderer in chat (`724d31d`)
**VERIFIED:** Shared `MarkdownBody` extracted+exported from `brief-blocks.tsx` (brief output byte-identical); fenced-code block kind; streaming incomplete-token completer (`markdown-stream.ts`, ported original, no dep); chat `MessageBody` renders markdown with watchlist-scoped ticker chips (never a bare word). Lead polish: fence-parser agreement on indented fences, hoisted per-line regex, stable no-op `onCite`. vitest 102.
**BROKEN:** none. **NEEDS-MANUAL-CHECK:** none (streaming re-parse cost measured O(n)/microseconds — kept simple).

### WS3 — Honest web-search banner + provenance (`4c5435c`, + WS1-test follow-up `59cb9d6`)
**VERIFIED:** `web_available` reconciled with source count at three layers — symptom #2 (N-sources + "web unavailable" banner together) killed at the data layer. Transient throttle vs no-backend distinguished via a typed `SearchError.reason`; banner copy is per-symbol/honest; the structured-only affordance preserved. ProvenanceBadge keyed off **real** web sources (http(s) URLs) so a structured-only run isn't mislabeled "web + structured". The full-suite integration pass caught a stale WS1 e2e test (`test_agent_mode_infers_read_intent_and_gates_to_read_only` asserted the pre-Decision-4 strict gate) — fixed as a standalone WS1 follow-up commit.
**BROKEN:** none. **NEEDS-MANUAL-CHECK:** none.

### WS4 — Brief depth state, export, chart dedup (`aee0457`)
**VERIFIED:** Depth carried across re-publish (omitted→prev, both→MAX tier, cross-symbol isolation) — #5 fixed; `publish_brief` schema gained an explicit `depth`. Chat-side `ResearchDepthControl` with current tier + running state + 'deepest' at heavy; escalation is **deterministic** (`research <subject> at depth=<tier>`, not the old fuzzy "go all out") through the one §6.5-gated send path; brief's affordance is now a read-only mirror (no racing dual controls). Export→Copy-markdown (clipboard-guarded) with the framer-motion raster path removed — #6 fixed at the root. Chart `singleton:true` — #7 fixed; no caller relied on the minted id. Lead polish: DRY via the shared `briefDepthTier`, honest JSDoc, stale-comment cleanup. vitest 409.
**BROKEN:** none. **NEEDS-MANUAL-CHECK:** the deterministic-prompt escalation still routes through the model (by design — a hard tool-call bypass would skip §6.5); the operator's own live typed test (FAST→DEEP→HEAVY) confirms it end-to-end.

### WS5 — OpenRouter native-search rung + per-model capability (`faba3b0`)
**VERIFIED:** OpenRouter native-search rung (`openrouter:web_search`, citations via `normalize_openai`); gate made **per-model** not per-provider (`_native_search_enabled`); the 5 existing providers + FR-082 local fallback unaffected. Per-model flags derived from `supported_parameters`/`pricing` (native>plugin>none; a "0"-priced row is correctly `none`) — **mirror-by-hand `models/llm.py` ↔ `types/ai.ts` in the same commit**. Honest, matrix-tested `nativeSearchStatus` Settings copy + subtle picker pip. Per-search cost surfaced as a documented may-drift estimate. Lead polish: docstring fix, `nativeSearchStatus` simplified+exported+matrix-tested, plugin-truthiness fix+test.
**BROKEN:** none.
**NEEDS-MANUAL-CHECK:** native-search **citation events** are not surfaced from the streaming path for ANY provider (pre-existing, not introduced here) — the WS3 banner fold-in is forward-compatible for when they are. The per-model hint is threaded from the frontend catalog; a non-frontend MCP client driving OpenRouter falls back to the local tool (safe FR-082 default).

### WS6 — Indian data: yfinance fix + keyless BSE (`1284c19` standalone, `a811581`)
**VERIFIED:** Step 1 (standalone): `get_quote`/`get_history` route through the region-aware `_yahoo_symbol` so `RELIANCE.NS`/`532837.BO` pass through unmangled. Keyless BSE provider (AGPL reimpl, **zero new dep**, ~14-line token-bucket replaces GPL mthrottle, **no BseIndiaApi import**): per-day bhavcopy cache (cold-download bounded to 8 days), `getScripHeaderData` quote + bhavcopy fallback, intraday RAISES the honest BYOK-broker message, EQ-series preference (lead hardening). Resolver master + `is_bse_symbol`/`region_hint` (bare BSE→IN); registry `id=bse` rank 25 (nse<bse<yfinance); a dual-listed name still prefers NSE. Region-aware no-data state (`reason='in_eod_only'`, mirror-by-hand into `types/data.ts`). **Smoke probe reached the live BSE bhavcopy endpoint** — URL shape validated. 32 offline tests; full suite 1441→ green.
**BROKEN:** none.
**NEEDS-MANUAL-CHECK:** the live BSE endpoint **response shapes** (bhavcopy columns, `getScripHeaderData` fields) are modeled from public knowledge and defensively coded but not exhaustively verified against live data — the no-SLA smoke probe confirms reachability, not field-by-field correctness; a first-load BSE-only chart is sparse until the daily cache warms (bounded by design). Seeded master uses 2 placeholder ISINs (routing keys on symbol, not ISIN); `regenerate_bse_master.py` pulls the full live master.

### WS7 — Keyless DDG floor rate-limiter (`b251a20`)
**VERIFIED:** Proactive async token-bucket (~20/min, lazy process-global, monotonic clock, `asyncio.Lock`-serialised) acquired before each DDG hit so the 202 anomaly is dodged before it triggers; first request immediate; deterministic tests (injected `_FakeClock`, no real sleeps); the stale-event-loop trap handled. WS3 typed reason + reactive 202/429 retry untouched. Lead polish: inlined a trivial helper. DDG suite 12 in <1s. curl_cffi stays deferred (Decision 2).
**BROKEN:** none. **NEEDS-MANUAL-CHECK:** none.

### WS8 — DeepSeek/OpenRouter tool-loop resilience (`9ed5001`)
**VERIFIED:** Tool-args **validate+repair** — the coerce-to-`{}` bug is fixed: malformed/invalid args get exactly ONE `oneshot.complete` repair round (sent without tool_ids so it can't recurse); on persistent failure the call carries `INVALID_ARGS_SENTINEL` which `_dispatch_tool` turns into a graceful `role='tool'` error keyed on `tool_call_id` **without dispatching** (§6.5-safer — an order tool never dispatches with bad args). Content-leak rescue gated to {deepseek,openrouter,ollama} + offered tool ids (never mis-fires on OpenAI/Anthropic). Header-aware transport retry (SDK `max_retries=0` so the adapter is the single authority; only RateLimitError/5xx/connection; 400 never retried; Retry-After honored — integer **and**, via lead hardening, RFC-7231 HTTP-date). Full suite 1473; safety 9/9.
**BROKEN:** none.
**NEEDS-MANUAL-CHECK:** **deepseek-reasoner echo-vs-steer (Step 4).** The low-risk default is implemented — `reasoning_content` is echoed on the reconstructed assistant tool-use turn ONLY for a `reasoner` model (non-reasoner stays `content=''`, verified). Choosing echo vs. steering tool loops to non-reasoner `deepseek-chat` needs a **live deepseek-reasoner multi-round repro** (real BYOK key + real multi-round tool loop) that cannot run in a network-mocked sandbox. Flagged in the code comment at the reconstructed-turn block.

---

## OPERATOR DECISIONS — as applied

**4 locked (2026-06-09), all applied as locked:**
- #3 BSE → reimplemented under **AGPL, zero new lib** (WS6).
- #4 read-gate → **read-safe panel actions allowed** on inferred read intents; `propose_order` stays stripped (WS1).
- #5 → **`market_overview` read_handler** tool added (WS1).
- #7 export → **replaced with Copy-markdown** (WS4).

**6 defaults — stood, surfaced as they landed:**
- #1 OpenRouter `web_search` cost → enabled + surfaced as a documented may-drift estimate (no dedicated pre-call cost-preview component exists; surfaced minimally in Settings per the plan's fallback). #2 `curl_cffi` → deferred (token-bucket only). #6 autonomy threaded. #8 pending-proposal persistence → left ephemeral for 0.8.0. #9 Tavily → deferred (Exa stays BYOK default). #10 external MCP control-plane → deferred (Tier-4).

---

## TELEMETRY RUN REPORT

**Orchestration:** 8 dynamic workflows (one per workstream; WS6 split Step-1-solo + BSE workflow) + lead review/commit between each. Workstreams were **not** parallelized (shared files: `agent_runtime.py` spans WS1/3/5/8; `host-actions.ts` spans WS3/4); intra-workstream parallelism was unnecessary given the proven single-implementer+review template.

| WS | workflow agents | wall-clock | tool calls | files | lines (+/−) | commit(s) |
|----|----------------|-----------|-----------|-------|-------------|-----------|
| WS1 | 3 (impl+spec+quality, clean) | 21.7 min | 142 | 12 | +432/−24 | `64a6524` |
| WS2 | 5 (impl+spec+quality+fix+re-review) | 18.1 min | 126 | 5 | +466/−30 | `724d31d` |
| WS3 | 3 (clean) | 23.2 min | 178 | 18 | +492/−39 | `4c5435c`, `59cb9d6` |
| WS4 | 3 (clean) | 15.7 min | 130 | 11 | +473/−123 | `aee0457` |
| WS5 | 3 (clean) | 25.6 min | 186 | 15 | +595/−35 | `faba3b0` |
| WS6 | 5 (impl+spec+quality+fix+re-review) | 29.3 min | 197 | 17 | +1276/−43 | `1284c19`, `a811581` |
| WS7 | 3 (clean) | 10.2 min | 58 | 2 | +209/−1 | `b251a20` |
| WS8 | 5 (impl+spec+quality+fix+re-review) | 32.0 min | 183 | 4 | +1195/−24 | `9ed5001` |
| **Total** | **30 workflow agents** (+ lead) | **~176 min workflow compute** | **~1200** | **68 (union)** | **+5159/−305** | **10 commits** |

- **Subagent tokens (workflow):** ~2.52M output tokens across the 30 agents.
- **Lead interventions:** every workstream got a hand-verified safety/diff review; lead polish/fixes landed in WS1 (narration), WS2 (3), WS3 (3 incl. the badge-honesty + stale-WS1-test catch), WS4 (3), WS5 (3), WS6 (Step-1 solo + prefer-EQ), WS7 (1), WS8 (1 HTTP-date Retry-After). Each was independently gated (ruff/eslint/prettier/typecheck + targeted tests) before commit.
- **Per-WS commits are the checkpoints** — a later session can resume from any of the 10 commits if needed.

---

## OPEN ITEMS FOR THE OPERATOR (your live typed-agent testing)

1. **deepseek-reasoner multi-round** (WS8 Step 4) — confirm the `reasoning_content` echo behaves on a real multi-round tool loop; decide echo vs. steer-to-`deepseek-chat`.
2. **BSE live field shapes** (WS6) — a real BSE-only ticker's chart/quote against the live endpoint (probe confirmed reachable; field correctness is the live check).
3. **The four flows you named** — how's-the-market (market_overview + date grounding), ASK vs AUTO narration truthfulness, Copy-markdown, and the chat markdown/chart rendering.
4. The keyless `ollama` default still under-invokes tools (honest now, not silent) — consider steering the default to a tool-capable provider.

Nothing is merged to `main`. All work is on `004-r4-experience-rebuild`.
