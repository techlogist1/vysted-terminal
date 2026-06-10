# R9 Track A report — tier collapse (three research tiers become two)

Branch `worktree-agent-r9-tiers` (from 004 HEAD at dispatch, `6f835e6`). Six
commits, each pushed as a recovery checkpoint. Partition respected with two
surgical out-of-list edits, both justified below. NOTE: origin/004 advanced
during the build (`f462863` content-aware arrange, `1862452` telemetry
skeleton — layout-templates/host-actions/capability tests); zero overlap with
this partition, merge should be clean.

## What shipped

### 1. The contract (pushed first, commit 1)

- **`src/store/search-settings.ts`** — `ResearchTier = "tier_a" | "tier_b"`;
  `researchModels: {normal, deep, ultra}` (defaults: `perplexity/sonar`,
  `perplexity/sonar-reasoning-pro`, `perplexity/sonar-deep-research` — verified
  on OpenRouter 2026-06-11); `RESEARCH_MODEL_OPTIONS` is THE one frontend
  constant with per-model `priceHint` + `priceVerified` (Team D renders it);
  `setResearchModel(stop, id)` validates slugs (model-agnostic charset). The
  legacy `tier` / `hostedEngine` / `exaDirect` fields are GONE from the bundle
  and the state. Migration: `migrateSearchSettings` folds any pre-R9 blob —
  native / local-searxng / t1_local / t2_searxng → `tier_a`;
  t3_hosted / byok-exa → PROVISIONAL `tier_b`, then `reconcileMigratedTierB`
  confirms the OpenRouter keychain slot asynchronously and demotes to `tier_a`
  when no key is configured (keychain failure counts as no key — it could not
  serve a request either). One `console.info` migration note, never a user
  error. An authoritative R9 blob is never key-checked or rerouted.
- **`src/lib/search-headers.ts`** — wire contract: `X-Vysted-Research-Tier`
  (always), `X-Vysted-Searxng-Url` (when set — retrieval is ONE lane, rides
  under either tier), `X-Vysted-Openrouter-Key` + `X-Vysted-Research-Models`
  (`normal=…,deep=…,ultra=…`, tier_b only). The Exa-direct lane
  (`X-Vysted-Search-Tier: byok-exa`, `X-Vysted-Exa-Key`) and
  `X-Vysted-Search-Engine` never ride again. tier_a never touches a keychain
  slot.
- **`sidecar/config.py`** — `SEARCH_TIER_A/B`,
  `KNOWN_RESEARCH_SEARCH_TIERS = {tier_a, tier_b}`; legacy ids fold in via the
  alias table (logged ONCE per spelling, rule 5);
  **`get_effective_research_tier()`** is the one tier truth: explicit header →
  legacy `byok-exa` → tier_b-iff-key-on-request else tier_a → tier_a default
  (there is no "no tier" state). Per-stop model map:
  `parse_research_models` / `get_research_model_for` /
  `set_request_research_models` ContextVar (defensive parse, any plausible slug,
  missing stops floor to defaults, unknown stop floors to NORMAL — never a
  silent escalation). Exa-key + hosted-engine ContextVars deleted.
- **`sidecar/app.py`** — middleware parses `x-vysted-research-models`; the Exa
  key and engine headers are no longer read (legacy `x-vysted-search-tier`
  stays as migration input for third-party callers).
- **`services/llm/native_search.py`** (interface for Team B, pushed in commit
  1): `native_search_available(provider, model_web_search)` — THE detection
  truth (the runtime's injection gate now delegates to it, so loop and
  cross-verify can never disagree) — and `native_search_oneshot(...)` — the
  callable channel: one native-search-grounded completion via the adapter's
  `web_search` opt-in, returns `{ok, text, citations}`, never raises, never
  logs the key. NOTE for Team B: `citations` is best-effort and currently
  empty (adapters surface grounding inline in TEXT; no structured citation
  events ride the stream) — treat `text` as the verification payload.

### 2. The ONE retrieval resolution path (`web_search.py`)

Retrieval is tier-INDEPENDENT (the tier governs research routing, not
retrieval): explicit custom SearXNG URL → managed READY instance (instant
in-process `ready_base_url()`, no network probe) → keyless rotation stamped
**`backend="keyless-fallback"`** (`KEYLESS_FALLBACK_BACKEND_ID`, exported — Team
C's nudge banner keys off it). A SearXNG backend that resolves but fails at
SEARCH time with an `unreachable` reason degrades ONCE to the same stamped
floor; a typed `rate_limited` error surfaces honestly (the instance is alive).
A stopped SearXNG can never yield "no web backend". The R7 conventional-port
network autodetect is off the hot path entirely (the matrix pins zero
`detect_searxng` calls); a custom non-managed instance is reached via the
Settings URL field.

### 3. Tier B lane + tool-boundary routing

- **`deep_research.run_research_model_brief`** — one OpenRouter
  chat-completions call on the per-stop model (explicit arg > request map >
  verified defaults; model-agnostic so the lead can re-pin without touching
  routing). Citations: `normalize_openai` over message annotations first, the
  `citations[]` url-list fallback second, de-duplicated, provenance-labelled.
  Key order: explicit arg → `X-Vysted-Openrouter-Key` ctx → active LLM creds
  iff the user is ON OpenRouter; no key → honest stop naming the unlock (D25
  key boundary), never a demotion. Wall clocks: normal 120s / deep 300s /
  **ultra 480s** (brief mandates ≥360). Progress is streamed honestly: an
  `engine` step naming `research-model:<model-id>` up front + 20s-cadence
  elapsed-time heartbeats (a vendor one-call lane has no internal stages —
  elapsed time is the truthful signal). The brief AND every step carry
  `backend="research-model:<model-id>"` (rule 2 evidence, test-pinned). Cost
  rides as a flagged per-stop ESTIMATE.
- **`research.py`** — tier routing at the tool boundary: `tier_b` owns ALL
  depth stops (NORMAL included — one search-grounded call instead of the no-LLM
  fast gather) and OUTRANKS any model-passed `backend` arg; the LLM can never
  pick the model that bills the user's key (no model passthrough). `tier_a`
  keeps the existing fast/iter/heavy lanes and per-run opt-in paid backends
  unchanged.
- **`agent_runtime`** — native-search suppression: `tier_b` ignores chat-model
  native search ENTIRELY (research model owns research; the local `web_search`
  tool stays for plain retrieval — no double-run/double-bill). `tier_a`
  COMPOUNDS: a native-capable model rides its own search (Team B cross-verifies
  channels). The R8 explicit-t2 suppression is deliberately retired with the
  t2 tier (test updated, called out below).

### 4. Kills (delete, don't stub)

- `services/search/hosted.py` (OpenRouter web-plugin scraper),
  `services/search/exa.py`, `tests/test_hosted_search.py`,
  `tests/test_exa_backend.py` — DELETED.
- `registry.py`: exa/hosted builders + credential kwargs gone;
  `KNOWN_BACKENDS = (searxng, keyless, ddg)`; regression test pins the dead ids
  unresolvable.
- Keyless engines (`keyless.py`, `ddg.py`, `brave.py`, `mojeek.py`, breakers,
  pacing) untouched — the invisible fallback.
- `routers/search_tiers.py`: routes unchanged (now core), docstring reframed;
  there were no t3 bits in code.

## Test counts

- **Full sidecar pytest suite: 1993 passed, 1 skipped, 0 failed (66s)** —
  `PATH=sidecar/.venv/bin pytest -q`, run in-worktree at final push.
  `ruff check sidecar` clean; `ruff format --check sidecar` clean (361 files).
- New/rewritten pins: `test_web_search.py` **43** items (30-cell matrix —
  R8's 14 cells extended, `test_matrix_did_not_shrink_from_r8` pins ≥29);
  `test_search_tier_config.py` **29**; `test_research_model_lane.py` **18**
  (new); `test_native_search.py` **31** (6 new interface tests);
  `test_agent_runtime.py` **56** (tier_b suppression, tier_a compounding, and
  the rule-4 depth-cost parity pin: byte-identical LLM request at normal vs
  ultra for a non-research ask); `test_search_registry.py` updated (dead-id
  regression).
- Frontend vitest (my partition): `search-settings.test.ts` **22**,
  `search-headers.test.ts` **12**, `workspace.test.ts` **30** — 64 green.
- `node scripts/audit-design-tokens.mjs --report`: 274 violations — the exact
  pre-existing inventory (D29); zero NEW from this track (no JSX/classes
  touched).

## Decisions taken (Tier 2/3, documented here)

1. **Retrieval is tier-independent.** "ONLY research routes to the research
   model" — so under tier_b the plain `web_search` tool resolves through the
   same local lane (SearXNG/keyless-fallback). The dead hosted scraper is not
   replaced by per-search research-model calls (cost honesty).
2. **R9 semantics change, deliberate:** an old explicit-`t1_local` client now
   gets a READY managed SearXNG (t1 folds into tier_a; there is no keyless
   tier to honor). The R8 cell that pinned "explicit t1 → keyless even when
   READY" is retired with the tier; called out in the matrix comments.
3. **tier_a explicit selection compounds native search** (R8 suppressed on
   explicit t2). Mandated by rule 3 / Team B's B4 cross-verify.
4. **Conventional-port SearXNG autodetect is off the hot path.** tier_a is now
   the default tier on EVERY request; a network probe per web_search is not
   acceptable. Custom instances use the Settings URL field. (R7's
   `detect_searxng` stays in the codebase for the searxng module's own use.)
5. **Tier B `mode` field:** `"fast"` for the normal stop, `"deep"` otherwise —
   stays inside the existing `RESEARCH_MODES` contract; `depth` carries the
   per-stop truth.
6. **Migration demotion on keychain failure** (frontend): a legacy hosted/Exa
   blob with an unreadable keychain demotes to tier_a — an unreadable key could
   not serve requests either, and the user can re-select tier_b in Settings.

## Out-of-list edits (flagged)

- **`services/agent_runtime.py`** (2 surgical edits): the native-search gate is
  rule 3's mandated behavior and the gate lives there;
  `_native_search_enabled` now delegates to `native_search_available` (one
  detection truth). No other runtime code touched.
- **`services/search/__init__.py`**: one stale docstring line ("Exa REST")
  updated after the module deletion.

## NEEDS-MANUAL-CHECK (integration)

1. **`src/components/SettingsPanel.tsx` + `src/components/SettingsPanel.test.tsx`
   reference the deleted store fields** (`exaDirect`, `hostedEngine`,
   `setResearchTier("t1_local")`, `HostedSearchEngine` type, Exa keychain rows).
   Team D's track rebuilds the Research surface on the new contract; until
   their branch merges, repo-wide `typecheck` and the SettingsPanel vitest file
   are red ON AN ISOLATED CHECKOUT OF THIS BRANCH. My partition's gates
   (ruff, full pytest, vitest for my files, token audit) are green.
2. **`src/app/page.tsx` line ~144** subscribes to `state.tier` (deleted field).
   The subscription is redundant since R8 (the store self-persists from every
   setter) — the lead can delete the `state.tier !== previous.tier` comparison
   (or the whole search subscription block) at integration. page.tsx is in no
   R9 track's partition; deliberately not touched.
3. **Alternate-model pricing hints** in `RESEARCH_MODEL_OPTIONS`
   (`sonar-pro`, `o4-mini-deep-research`, `o3-deep-research`) are best-known
   catalog values, `priceVerified: false`; `sonar-pro-search` and `grok-4.3`
   carry "OpenRouter metered — see model page". Lead should re-pin at
   integration (the brief's table verified only the three defaults).
4. **`native_search_oneshot` citations are currently always `[]`** (adapters
   don't surface structured citation events through the stream). Team B's
   cross-verify must key on the grounded TEXT. If structured citations are
   needed, the adapters' stream events need a citation channel — out of this
   track's partition.
5. **Live Tier B smoke** (real OpenRouter key, one sonar + one
   sonar-deep-research run, ULTRA wall observed) — all lane tests are offline
   by policy; a single live run at integration is cheap insurance.

## Files touched

Sidecar: `config.py`, `app.py`, `services/agent_tools/{web_search,research,deep_research}.py`,
`services/llm/native_search.py`, `services/search/{registry,__init__}.py` (+
deletions above), `routers/search_tiers.py`,
`tests/{test_web_search,test_search_tier_config,test_search_registry,test_native_search,test_agent_runtime,test_research_model_lane}.py`.
Frontend: `src/store/search-settings.ts` (+test), `src/lib/search-headers.ts`
(+test), `src/lib/workspace.ts` (+test).
