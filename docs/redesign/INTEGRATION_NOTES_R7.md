# R7 Track R — integration notes for the lead

App-shared touchpoints this track needs but did NOT change (per the brief's
ownership rules), plus wiring the frontend/lead must pick up.

## Component 3 (T3 hosted tier) — 2026-06-10

### Shared files deliberately left untouched

- **`sidecar/services/llm/native_search.py` `openrouter_web_search_tool()`**
  still emits the bare `{"type": "openrouter:web_search"}` with no
  `parameters`. The live docs (verified 2026-06-10,
  https://openrouter.ai/docs/guides/features/server-tools/web-search) support
  `parameters: {engine, max_results, max_total_results, search_context_size,
  allowed_domains, excluded_domains}` — the agent-loop injection could carry
  the user's engine choice via `config.get_hosted_search_engine()`. The t3
  search backend (`services/search/hosted.py:web_search_server_tool`) owns its
  own fully-parameterized builder, so this is an enhancement, not a defect.
  Left to the lead because `services/llm/` is shared with the LLM track.
- **`normalize_openai` excerpt fallbacks** read `snippet`/`text`; the server
  tool's `url_citation` carries the excerpt under **`content`** (live docs).
  Suggested one-line addition: `_get(src, "content")` first in the fallback
  chain. The hosted backend parses `content` itself; the sonar lane degrades
  to an empty excerpt through `normalize_openai` (sources still render — the
  brief's requirement holds), so again enhancement-only.

### Frontend wiring needed (settings round-trip)

New per-request headers read by the region middleware (`sidecar/app.py`
`_RegionMiddleware`), mirroring the existing `X-Vysted-Search-Tier` transport:

| Header | ContextVar | Values |
| --- | --- | --- |
| `X-Vysted-Research-Tier` | `config.get_research_search_tier()` | `t1_local` / `t2_searxng` / `t3_hosted` (absent → no explicit selection, floors to t1) |
| `X-Vysted-Openrouter-Key` | `config.get_openrouter_search_key()` | BYOK secret — keychain-sourced, never persisted/logged |
| `X-Vysted-Search-Engine` | `config.get_hosted_search_engine()` | `firecrawl` (default) / `exa` / `parallel` / `auto` / `native` |

The Settings panel should persist the tier + engine in the frontend store
(same pattern as the deep-research engine selection) and send them on every
sidecar request. The deep-research Settings picker may now also offer
`sonar` (the OpenRouter-routed Perplexity lane) alongside
`native`/`perplexity` — `run_deep_brief` dispatches it already.

### Verified-live facts the UI copy can rely on (2026-06-10)

- The `plugins: [{"id": "web"}]` array and the `:online` suffix are
  **deprecated**; the `openrouter:web_search` server tool is current.
- Engine pricing: Firecrawl = $0 OpenRouter-side (bills Firecrawl credits;
  10,000 free credits at signup, 3-month expiry). Exa/Parallel = $0.005 per
  search including 10 results, then $0.001 per additional result. Native =
  provider pass-through.
- `perplexity/sonar-deep-research` is routable via OpenRouter ($2/M in,
  $8/M out, $5/1000 searches pass-through).
- `alibaba/tongyi-deepresearch-30b-a3b` is **delisted** from OpenRouter —
  kept out of every picker; direct sources (Alibaba Bailian / WaveSpeed) only.

### NEEDS-MANUAL-CHECK (live key required)

- One live `t3_hosted` search with a real OpenRouter key per engine
  (firecrawl + exa) to confirm the annotation shape end-to-end.
- One live `backend="sonar"` run to confirm OpenRouter passes the top-level
  `citations[]` array through alongside annotations.
