# R7 Track R — Research Engine Brief (worktree: worktree-agent-r7-research)

You are building the search-backend tiers + depth system for Vysted Terminal's research
engine, inside THIS worktree only: `~/Documents/dev/vysted-terminal/.claude/worktrees/r7-research`.
Branch: `worktree-agent-r7-research`. NEVER write to the main repo path. Use the main
venv's binaries for tooling (they have all deps incl. curl_cffi):
`~/Documents/dev/vysted-terminal/sidecar/.venv/bin/{python,ruff,pytest}` — run them with
cwd inside THIS worktree.

## Ground rules

- Conventional commits, one per concrete deliverable; push to `origin worktree-agent-r7-research` after each commit.
- Before each Python commit: `ruff format <changed> && ruff format --check sidecar && ruff check sidecar` and the targeted pytest suite (offline; mock network).
- NEVER touch: `types/plugin.ts`, `.github/`, `src-tauri/tauri.conf.json`, `LICENSE*`, `CLAUDE.md`, `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, broker code, `sidecar/services/agent_tools/catalog.py` (owned by another track). If a catalog/app-shared change is genuinely required, append it to `docs/redesign/INTEGRATION_NOTES_R7.md` (create it) for the lead instead.
- You OWN: `sidecar/services/search/**`, `sidecar/services/research/**`, `sidecar/services/searxng_manager.py` (new), `sidecar/services/config.py` (search-tier additions), `sidecar/routers/app-wiring for new routers` (you may edit `sidecar/app.py`), new routers, their tests, `sidecar/models/` files you create.
- No GPL code. Port MIT/Apache patterns with a one-line attribution comment
  (`# Adapted from odysseus (MIT) github.com/pewdiepie-archdaemon/odysseus`).
- Keyless-first: T1 must work with zero keys, zero setup.
- The research LOOP already exists and is good — `services/research/{fast,deep,iter}.py`
  carries adapted DeepResearch paradigms (IterResearch workspace reconstruction in iter.py,
  Heavy panel fan-out, coverage floor in deep.py). DO NOT rebuild the loop. You are
  rebuilding what's UNDER it (search backends) and the depth/tier routing AROUND it.
- Existing search ladder: `services/search/{registry,exa,searxng,ddg}.py` + `llm/native_search.py`.
  Extend/replace within this structure; keep the `SearchBackend` seam.

## Component 1 — T1 keyless tier (the default floor, rebuilt)

Multi-engine rotation: DuckDuckGo (existing, keep its token-bucket + typed SearchError),
Brave HTML scrape (html.brave.com... actually https://search.brave.com/search?q= HTML),
Mojeek HTML scrape (https://www.mojeek.com/search?q=). Engine adapters parse to the
uniform result dict {title,url,snippet}. Add:

- `curl_cffi.requests.AsyncSession(impersonate="chrome")` transport for engines that
  reject httpx TLS fingerprints (Brave; DDG 403 fallback). httpx stays for friendly hosts.
- Per-engine CircuitBreaker (CLOSED/OPEN/HALF_OPEN, fail_threshold≈2, cooldown≈30-60s).
- A small process-global async request queue with per-engine min-interval throttling and
  exponential backoff + jitter on retryable failures (2 attempts/engine, then rotate).
- Provider-chain rotation: primary→fallbacks, skip OPEN breakers.
- Full-page extraction for research `visit`: fetch via the same transport, BeautifulSoup
  heuristic main-content extraction (main/article/semantic divs; strip script/style/nav/
  header/footer), truncate at paragraph boundary. bs4 is already a transitive dep — import
  `bs4` and add an explicit pin to requirements.txt if missing.
- Dedup: URL-set per run.
- Quality filter: low-quality markers list (cookie banners, consent boilerplate).
- Prompt-injection scrubbing: port odysseus `untrusted_context_message` (guard markers,
  marker-escape, label sanitization) and apply it wherever fetched web content enters an
  LLM prompt in the research services.
- HONEST STATUS: a `tier_status()` surface (e.g. GET /search/status) reporting per-engine
  breaker state + cooldown remaining, so the UI can say "DuckDuckGo cooling down (24s)"
  instead of a fake global outage.

## Component 2 — T2 one-click SearXNG ("Unlimited Research")

New `services/searxng_manager.py` + router (e.g. `routers/search_tiers.py`):

- detect(): docker CLI present? daemon reachable? (run `docker version --format json`
  via asyncio subprocess; also recognize OrbStack).
- setup(): `docker pull searxng/searxng`, run with a generated settings.yml that enables
  the JSON output format (mount a config dir under the app data dir), port e.g. 8888
  (configurable; avoid collisions by probing), name `vysted-searxng`, restart=unless-stopped.
- health(): poll `http://127.0.0.1:<port>/search?q=test&format=json` until OK.
- status(): not_installed_docker | docker_present_not_setup | pulling | starting | ready | error(reason).
- teardown(): stop/remove container.
- Route the existing `searxng.py` backend at the managed localhost instance when ready.
- The STATE MACHINE is the contract for the UI's guided flow — expose it via the router.
- Tests: mock the subprocess layer; do not require docker in CI.

## Component 3 — T3 BYOK hosted tier

- OpenRouter **web-search server tool** (the `:online` suffix / `web` plugin is the OLD
  deprecated path — use the current `plugins: [{"id": "web", ...}]`? VERIFY against the
  live docs at https://openrouter.ai/docs (you have WebFetch) and implement what the docs
  say TODAY for: engine selection (Firecrawl default with its free-credit tier, Exa as
  option), max_results, and pricing fields. Surface per-search cost estimate in the
  response metadata. The BYOK key rides the request only — never persisted/logged.
- One-call research-model lane: `perplexity/sonar-deep-research` + sonar family through
  the existing OpenRouter adapter; they return citations — normalize via the existing
  `normalize_openai` citation path so briefs render sources.
- Tongyi-DeepResearch: confirmed DELISTED from OpenRouter (live check 2026-06-10). Keep it
  OUT of any picker; mention Bailian/WaveSpeed as direct sources only in code comment/docs.
- Tier selection config: `services/config.py` gains a search-tier setting
  (t1_local | t2_searxng | t3_hosted) with per-request override, defaulting t1, persisted
  via the existing settings round-trip (look at how deep-research backend selection is
  threaded via ContextVar — mirror that pattern).

## Component 4 — Depth router (N/D/U) + finance tuning

- Map depth → loop: NORMAL → existing FAST bundle (+agent prose); DEEP → run_iter_research
  (≈3 rounds, 3 researchers); ULTRA → run_heavy_research (3 angles × iter, stricter
  coverage). Depth is per-query, orthogonal to tier. The brief depth tiers
  (quick/deep/heavy) already exist — wire N/D/U onto them coherently (one naming, one
  source of truth; prefer normal/deep/ultra naming surface-side, mapped internally).
- Scale knobs by depth: report char cap, rounds, researchers, coverage strictness
  (ULTRA requires ≥2 web sources per section + cross-check pass).
- Finance tuning (the moat), inside `services/research/`:
  - Source prioritization: a domain-rank table (exchange/regulator/filings first:
    nseindia.com, bseindia.com, sebi.gov.in, rbi.org.in, sec.gov, company IR;
    then Tier-1 press: economictimes/bloomberg/reuters/ft/wsj/moneycontrol/livemint;
    then general). Searches bias query templates toward these (site: hints on DEEP/ULTRA
    rounds); rank gathered sources by tier for synthesis ordering and citation preference.
  - Recency awareness: thread the server date into every research prompt (exists for the
    agent preamble — ensure research loops carry it too); prefer results with fresh dates
    for time-sensitive queries.
  - Multi-source cross-checking: ULTRA adds a verification round that re-checks the top
    numeric claims across ≥2 independent sources, flagging disagreements in the brief.
  - No-price-feed resilience: research must succeed when price/fundamentals tools return
    empty (micro-caps) — the coverage floor must accept "web-only" for instruments where
    structured data legitimately doesn't exist (loosen: if price+fundamentals providers
    returned provider:none, web coverage alone satisfies the floor; the brief says so).
- Tests for the router + tuning (mock LLM + search).

## Definition of done for this track

Every component implemented (no stubs/TODOs), offline tests green
(`.venv pytest sidecar/tests -q` for your suites + full suite still green), ruff clean,
each component committed + pushed, and a final `docs/redesign/R7_TRACK_RESEARCH_REPORT.md`
in the worktree: what shipped (file:line), how verified (real test output), what needs
live-key/manual verification (label NEEDS-MANUAL-CHECK), integration notes for the lead.
