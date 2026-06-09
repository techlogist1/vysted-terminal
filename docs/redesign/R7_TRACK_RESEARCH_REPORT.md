# R7 Track R — Research Engine Report

Branch `worktree-agent-r7-research`, worktree `.claude/worktrees/r7-research`.
All four components shipped (no stubs, no TODOs), each as a conventional commit
pushed to `origin worktree-agent-r7-research`. Full-suite + ruff gate run from
this worktree on 2026-06-10 (output below).

## Commits (one per deliverable, all pushed)

| Commit | Deliverable |
| --- | --- |
| `02c76ef` | deps: `curl_cffi==0.15.0` + explicit `beautifulsoup4==4.14.3` pin (`sidecar/requirements.txt:12,16`) |
| `2b72b95` | T1 primitives: per-engine circuit breakers, pacing queue, dual-lane transport |
| `e259d57` | Brave + Mojeek HTML engine adapters; DDG 403 impersonation fallback |
| `94d16f5` | T1 keyless multi-engine rotation backend + honest `GET /search/status` |
| `32a435d` | Full-page `visit` extraction + odysseus prompt-injection scrubbing |
| `6d0d609` | T2 one-click managed SearXNG (docker state machine + guided-flow router) |
| `b194354` | fix: sticky error state on the SearXNG status poll |
| `336968a` | Tier-selection config (`t1_local\|t2_searxng\|t3_hosted`) via per-request ContextVars |
| `5d6c016` | T3 BYOK hosted tier — OpenRouter `web_search` server tool + cost estimate |
| `1c327bf` | Sonar one-call lane via OpenRouter + `normalize_openai` citation path |
| `53a87c3` | Depth router (normal/deep/ultra) + finance tuning |

## Component 1 — T1 keyless tier (shipped)

- **Dual-lane transport** `sidecar/services/search/transport.py` —
  `httpx_fetch` (:72, friendly hosts) and `impersonated_fetch` (:112,
  `curl_cffi.requests.AsyncSession(impersonate="chrome")` for TLS-fingerprint
  blockers).
- **Per-engine CircuitBreaker** `sidecar/services/search/breaker.py:45`
  (CLOSED/OPEN/HALF_OPEN, fail_threshold 2, cooldown 45s), process registry
  `breaker_for`/`breaker_status`/`reset_breakers` (:126/:135/:145).
- **Pacing queue** `sidecar/services/search/pacing.py:73` `RequestQueue` —
  process-global, per-engine min-interval throttling + `backoff_delay`
  (exponential + jitter, :55); 2 attempts/engine then rotate.
- **Engine adapters** uniform `{title,url,snippet}`: Brave HTML scrape
  `sidecar/services/search/brave.py` (impersonated lane), Mojeek HTML scrape
  `sidecar/services/search/mojeek.py`, DDG kept with token-bucket + typed
  `SearchError`, plus a one-shot Chrome-impersonated 403 fallback
  (`sidecar/services/search/ddg.py:182` `_impersonated_fallback`).
- **Rotation backend** `sidecar/services/search/keyless.py:130`
  `KeylessSearchBackend` — chain `ddg → brave → mojeek` (:53), skips OPEN
  breakers, per-run URL-set dedup + low-quality marker filter
  (`is_low_quality` :84, `_filter_results` :92).
- **Honest status** `keyless.tier_status()` (:235) →
  `GET /search/status` (`sidecar/routers/search_status.py:20`): per-engine
  breaker state + `cooldown_remaining` so the UI can say "DuckDuckGo cooling
  down (24s)" instead of a fake global outage.
- **Full-page extraction** `sidecar/services/search/extract.py` —
  `fetch_page` (:197, same dual-lane transport, SSRF guard `is_public_http_url`
  :101 with private-address resolver check), BeautifulSoup main-content
  heuristic (main/article/content-ish divs; script/style/nav/header/footer
  stripped, `_paragraphs` :126), paragraph-boundary truncation (:168);
  `visit_for_research` (:253) is the research `visit` surface.
- **Prompt-injection scrubbing** `sidecar/services/search/scrub.py` — ported
  odysseus `untrusted_context_message` (:105) with guard markers,
  marker-escape (:59) and label sanitization (:70); applied where fetched web
  content enters LLM prompts (`services/research/deep.py:394,430-432`
  `wrap_untrusted` on web results + visited pages; `sanitize_inline` :331).
- **Registry seam kept**: `sidecar/services/search/registry.py` —
  `keyless` is the unconditional default floor (`_build_keyless` :81), `ddg`
  retained as the single-engine rung it grew out of; `SearchBackend` contract
  unchanged (`base.py`).

## Component 2 — T2 one-click SearXNG (shipped)

- `sidecar/services/searxng_manager.py:243` `SearxngManager` — the
  state machine (states :76): `not_installed_docker | docker_present_not_setup
  | pulling | starting | ready | error(reason)`.
  - `detect()` via `docker version --format json` over asyncio subprocess
    (`_run_docker` :128, `_parse_docker_version` :192 — recognizes OrbStack).
  - `setup()`: pull `searxng/searxng`, generate a JSON-format-enabled
    `settings.yml` under the app data dir (`write_settings` :227), port-probe
    to avoid collisions (`_port_is_free` :182), container `vysted-searxng`,
    `restart=unless-stopped`.
  - `health()` polls `/search?q=test&format=json` (`_probe_health` :161).
  - `teardown()` (:576) stop+remove, then re-derives honest state.
  - Passive `refresh()` (:376) never mutates docker; in-flight setup state
    (pulling/starting) wins; `reset_for_tests` (:604) + lifespan `shutdown`
    (:610).
- Router `sidecar/routers/search_tiers.py` — `GET /search/searxng/status`
  (:29), `POST /setup` (:35), `POST /teardown` (:41): the state machine IS the
  UI guided-flow contract.
- Existing backend routed at the managed instance:
  `sidecar/services/search/searxng.py:69` `_managed_base_url()` — a READY
  manager wins over the configured URL.
- Tests mock the subprocess + httpx layers entirely — no docker in CI
  (`test_searxng_manager.py`, 25 tests).

## Component 3 — T3 BYOK hosted tier (shipped)

- Verified against the LIVE OpenRouter docs (2026-06-10): the
  `plugins:[{"id":"web"}]` array and `:online` suffix are **deprecated**; the
  current path is the `openrouter:web_search` **server tool**. Implemented in
  `sidecar/services/search/hosted.py` — `web_search_server_tool` (:125,
  engine/max_results parameters), `HostedSearchBackend` (:249),
  `estimate_search_cost_usd` (:150) surfaces a per-search cost estimate in the
  response metadata (Firecrawl default = $0 OpenRouter-side, free-credit tier;
  Exa/Parallel $0.005/search incl. 10 results + $0.001/extra). The BYOK key
  rides the request only — never persisted/logged (asserted in tests).
- **Sonar one-call lane** `sidecar/services/research/sonar.py:241`
  `OpenRouterSonarBackend` — `perplexity/sonar-deep-research` + sonar family
  via the existing OpenRouter adapter path; citations normalized through the
  existing `normalize_openai` path so briefs render sources
  (`_extract_sources` :177 reads annotations AND the top-level `citations[]`);
  dispatched as opt-in `backend="sonar"`
  (`sidecar/services/agent_tools/deep_research.py:136` `_run_sonar`).
- **Tongyi-DeepResearch is DELISTED from OpenRouter** (live check 2026-06-10):
  kept out of every picker; Bailian/WaveSpeed noted as direct sources in code
  comments only.
- **Tier config** `sidecar/config.py` — `normalize_research_search_tier`
  (:249), `get_research_search_tier` (:264) ContextVar (defaults to the t1
  floor), `get_openrouter_search_key` (:290), `get_hosted_search_engine`
  (:309), mirroring the deep-research-backend ContextVar pattern. Transport:
  per-request headers read by the `sidecar/app.py` middleware (:238-266) —
  `X-Vysted-Research-Tier`, `X-Vysted-Openrouter-Key` (never logged),
  `X-Vysted-Search-Engine` — reset on request exit.
- Registry: `_build_hosted` (`registry.py:92`) errors honestly when the key is
  missing rather than silently re-routing; hosted is never a fallback.

## Component 4 — Depth router + finance tuning (shipped)

- **One source of truth** `sidecar/services/research/depth.py` —
  `normalize_depth` (:69; `quick`→`normal`, `heavy`→`ultra`, legacy aliases
  accepted forever), `DepthProfile` (:85) + `PROFILES` knob table
  (rounds, researchers, report char cap, `min_web_domains` coverage
  strictness, `site_bias`), `profile_for` (:154). Mapping: NORMAL → FAST
  bundle, DEEP → `run_iter_research` (3 rounds, 3 researchers), ULTRA →
  `run_heavy_research` (3 angles × iter, stricter coverage). Depth is
  per-query and orthogonal to tier; results carry both legacy `mode` and new
  `depth` (`deep_research.py:292-295`).
- **Finance tuning** `sidecar/services/research/finance.py` — domain-rank
  table (exchange/regulator/filings → Tier-1 press → general; `domain_tier`
  :115 incl. company-IR heuristic :107), `rank_sources` (:135) orders
  synthesis citations, `bias_query` (:168) adds `site:` hints on DEEP/ULTRA
  rounds (`deep.py:412`), `priority_note` (:146) biases synthesis ordering
  (`deep.py:516`), `date_directive` (:184) threads the server date into every
  research prompt (`deep.py:444,531,635,719`).
- **ULTRA cross-check** `sidecar/services/research/verify.py:198`
  `cross_check` — re-checks top numeric claims across ≥2 independent source
  domains, flags disagreements in the brief (`structured.cross_check` +
  `## Cross-check` markdown section + disagreement count in `note`).
- **No-price-feed resilience** `sidecar/services/research/deep.py` — the
  coverage floor LOOSENS to web-only when price+fundamentals providers
  returned `provider: none` (:741 area), with the honest
  `web_only_floor_note` (:232) stating it in the brief.

## Verification (real output, run 2026-06-10 from this worktree)

Full sidecar suite (`sidecar/.venv/bin/python -m pytest sidecar/tests -q`):

```
1716 passed, 1 skipped, 1 warning in 59.51s
```

(The 1 skip is `test_native_search_live.py` — gated on a live key by design.
The 1 warning is a pre-existing `websockets.legacy` DeprecationWarning from
the alpaca broker test, not this track.)

R7-targeted suites (215 tests):

```
sidecar/tests/test_search_breaker.py (10)  test_search_pacing.py (10)
test_search_transport.py (9)  test_search_extract.py (19)
test_search_scrub.py (13)  test_search_status_router.py (2)
test_searxng_manager.py (25)  test_search_tiers_router.py (5)
test_search_tier_config.py (14)  test_hosted_search.py (26)
test_sonar_lane.py (20)  test_research_depth.py (16)
test_research_finance.py (12)  test_research_verify.py (8)
test_web_search.py (8)  test_searxng_backend.py (12)
→ 215 passed in 1.04s
```

Ruff (same venv, worktree cwd):

```
ruff format --check sidecar → 339 files already formatted
ruff check sidecar         → All checks passed!
```

No unrelated failures observed — the full suite is green.

## NEEDS-MANUAL-CHECK (live network / live key / docker)

1. **T1 live SERP parse drift** — Brave + Mojeek HTML scrapes and the DDG 403
   impersonation fallback are tested against captured fixtures; run one live
   `keyless` search to confirm current markup still parses (SERP HTML drifts
   without notice).
2. **T3 hosted, per engine** — one live search with a real OpenRouter key for
   `firecrawl` and `exa` to confirm the `url_citation` annotation shape
   end-to-end and that the cost-estimate fields match the live billing meta.
3. **Sonar lane** — one live `backend="sonar"` run to confirm OpenRouter
   passes the top-level `citations[]` through alongside annotations.
4. **T2 with real docker/OrbStack** — one `setup()`→READY→`teardown()` cycle
   on this Mac (OrbStack) to confirm the pull/run/health timing and that the
   generated `settings.yml` mount works against the current
   `searxng/searxng:latest` image. Tests mock the subprocess layer per the
   brief.
5. **PyInstaller dep audit** — `curl_cffi` needs `--collect-all=curl_cffi`
   in the sidecar build (noted in `requirements.txt:11`); verify the built
   binary via `node scripts/smoke-test-sidecars.mjs` before the next tag.

## Integration notes for the lead

Full detail in `docs/redesign/INTEGRATION_NOTES_R7.md`. Summary:

- **Catalog (owned by another track, untouched):** the `research`
  capability's `depth` enum still reads `["quick","deep","heavy"]` — works
  unchanged because `depth.normalize_depth` accepts both namings forever.
  Suggested update when the lead touches `catalog.py`: enum
  `["normal","deep","ultra"]`.
- **`services/llm/native_search.py` (shared, untouched):** its
  `openrouter_web_search_tool()` still emits the bare parameterless server
  tool; the live docs support `parameters:{engine,max_results,...}` — an
  enhancement the lead can apply, the t3 backend owns its own builder.
- **`normalize_openai` excerpt fallback:** the server tool's `url_citation`
  carries the excerpt under `content`; suggested one-line `_get(src,
  "content")` first in the fallback chain (sources still render without it).
- **Frontend settings round-trip:** persist tier + engine in the frontend
  store and send `X-Vysted-Research-Tier` / `X-Vysted-Openrouter-Key`
  (keychain-sourced) / `X-Vysted-Search-Engine` on every sidecar request —
  same pattern as the deep-research engine selection. Settings picker may add
  `sonar` next to `native`/`perplexity`.
- **Brief panel:** the engine result now carries top-level
  `depth: normal|deep|ultra` (read it instead of `mode` when renaming the
  "Go deeper" tiers); ULTRA briefs may carry `structured.cross_check` for a
  disagreement badge; SearXNG guided flow drives off
  `GET /search/searxng/status` states verbatim.
