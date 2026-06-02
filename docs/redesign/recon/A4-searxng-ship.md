# Recon — A4:searxng-ship

I have everything. Writing the blueprint now.

---

# Keyless Web Search — "Works Out of the Box" Blueprint (Track 1, Deferred #4)

## 1. Findings (file:line precise)

**The autodetect is dead code.** `detect_searxng()` + `_DEFAULT_PROBE_URLS` (`sidecar/services/search/searxng.py:47,89-118`) — the multi-port 8888→8080 capability probe — is **never called** in the resolve path. The wiring is:

- `web_search` tool (`sidecar/services/agent_tools/web_search.py:52,57`) reads `config.get_searxng_url()` (→ `None` when user set no URL, `config.py:121-123`) and passes it to `registry.resolve(...)`.
- `registry._build_searxng` (`search/registry.py:44-54`) returns `None` when `searxng_url` is falsy. **No probe.** So an unconfigured local tier yields `backend=None` → honest "unavailable" message. The 8888/8080 autodetect the docstrings promise simply does not run. The Settings hint (`SettingsPanel.tsx:433`, "autodetect localhost:8888 then :8080") and store comment (`search-settings.ts:33`) **describe behavior that does not exist.**

**Default tier is `native`** (`types/search.ts:30`, `config.py:99`). On a fresh install with **no model key**, native search is impossible (no model), `byok-exa` needs an Exa key, `local-searxng` needs a running SearXNG. **→ Web search is fully dark out-of-the-box.** This is the real gap.

**Search package is structurally ready for a new backend:** uniform `SearchBackend` Protocol (`base.py:73-85`), `KNOWN_BACKENDS` tuple (`registry.py:28`), `_BUILDERS` dispatch dict (`registry.py:59-62`), `_TIER_BACKEND` map (`web_search.py:23`), `SearchTier` union (`types/search.ts:24`). Adding a backend = touch these 4 maps + 1 module. `httpx==0.28.1` already shipped (`requirements.txt:7`); `lxml`/`bs4` pulled transitively via yfinance/jugaad (`requirements.txt:104`).

**Sidecar spawn precedent is clean & copy-pasteable** (`openbb_mcp.rs`, `sec_edgar_mcp.rs`): pick_free_port → `app.shell().sidecar("name")` → drain stdout/stderr → `wait_for_port_with_retries(MCP_PORT_WAIT_SECS=45, ATTEMPTS=2)` → `app.manage` port+child → `RunEvent::Exit` kill. Env-var port handoff. `externalBin` declares 3 today (`tauri.conf.json:40-44`); `ensure-all-sidecars.mjs:28` SCRIPTS lists 3. Main sidecar is **105 MB** (target ≤120 MB — **only 15 MB headroom**).

**Keyless DATA is genuinely on by default — confirmed working:**

- yfinance `rank=50`, ccxt `rank=10` are **unconditional** (no `requires` gate, `provider_registry.py:114,161`). US equity + crypto serve with zero keys.
- India: `jugaad-data==0.33.1` shipped (`requirements.txt:108`), `nse` provider `requires=india_provider.is_available()` (import probe, `india_provider.py:67-77`), `rank=20`, region-scoped IN. Keyless IN equity works.
- News: RSS feeds keyless, NewsAPI optional (`news_provider.py:1-19`). Works.
- **No fresh-install gate blocks keyless data.** A provider only "disappears" if its import fails (openbb-mcp/sec via port-0 sentinel → graceful 501/yfinance fallback).

**Keyless RESEARCH is the weak link:** `gather_fast` (`research/fast.py`) runs structured pulls keyless BUT its one `web_search` round (`fast.py:242`) goes dark without a backend → surfaces honest `web.available=False` note (`fast.py:62,253-260`). `run_deep_research` (`deep.py:262`) needs both an LLM (a key) AND web_search. **So "real research with no keys" = structured-only today.** Fixing search fixes keyless FAST research's web round.

## 2. Exact change plan

**RECOMMENDATION: Option (c) — ship an in-sidecar keyless metasearch backend (DuckDuckGo HTML/lite) as the real default; keep SearXNG as the power-user upgrade. Wire the existing autodetect as a bonus. Do NOT bundle SearXNG.**

Why not (a): SearXNG is a Flask app with ~40 engine modules, `settings.yml`/locale data, `valkey`/redis optional — PyInstaller `--onefile` would mean `--collect-all searx` + every engine's data (per CLAUDE.md three-silent-drops trap), pushing a 4th binary to ~60-90 MB and a 4th cold-bind contending for disk at boot (the `_MEI` extraction race already forced `MCP_PORT_WAIT_SECS=45`). Not verifiable tonight. Why not (b): Docker/OrbStack presence is not guaranteed on the M1 travel rig or a fresh user box — can't be the _default_. Option (c) is a ~250-line in-process httpx client, zero new binary, zero size hit, verifiable with pytest tonight.

**New backend — `sidecar/services/search/ddg.py`** (CREATE): `DdgSearchBackend(SearchBackend)` + `BACKEND_ID="ddg"`. `async def search()` GETs `https://html.duckduckgo.com/html/?q=<query>` (POST form fallback), parses result rows with `lxml`/regex into `SearchResult`, maps to citations via `normalize_results_to_citations`. Honor `region` (DDG `kl=` param via `locale_domains` region → `us-en`/`in-en`), `maxResults`, `categories` (append "news"). Raise `SearchError` on transport failure (mirror `searxng.py:167-179`). Set a desktop User-Agent header. **No key, no config, always available.**

**`sidecar/services/search/registry.py`** (EDIT): add `"ddg"` to `KNOWN_BACKENDS` (line 28); add `_build_ddg(...)` that `return DdgSearchBackend(region=region)` **unconditionally** (no credential gate); register `"ddg": _build_ddg` in `_BUILDERS` (line 59).

**`sidecar/services/agent_tools/web_search.py`** (EDIT, lines 54-65): change the fallback chain so when `backend_id` resolves to `None` (or tier is `native` but tool is reachable), it falls through to **ddg** last: `... or registry.resolve("searxng", searxng_url=searxng_url, region=region) or registry.resolve("ddg", region=region)`. **This single edit guarantees web_search NEVER returns "unavailable" on a fresh install** — ddg is the floor.

**Wire the real autodetect (low-cost win):** in `web_search.py`, when `searxng_url` is `None` and tier is `local-searxng`, call `await detect_searxng()` first; if it returns a URL, use it. Fixes the docstring lie cheaply.

**`types/search.ts`** (EDIT): no new _tier_ needed — ddg is an internal fallback, not a user-selectable tier. Leave `SearchTier` untouched (avoids a frontend/store/workspace migration). Update the `native` default's UX so a keyless user still gets results: ddg fires whenever native/byok can't.

**Optional Settings copy fix** (`SettingsPanel.tsx:433`, `search-settings.ts:33`): the "autodetect 8888 then 8080" claim becomes true once the autodetect wire above lands — no copy change needed, but verify.

**Do NOT touch:** any Tier-1 locked file, `tauri.conf.json`, `externalBin`, `ensure-all-sidecars.mjs`, Rust spawn files — **option (c) needs zero Rust and zero new binary.**

## 3. Risks + safe fallback

| Risk                                                                | Fallback                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DDG HTML scraping is brittle (markup change / rate-limit / CAPTCHA) | Backend raises `SearchError` → `web_search` returns honest `ok:False` (existing path `fast.py:253`). Research degrades to structured-only — exactly today's behavior, never worse. Add a `format=lite` (`lite.duckduckgo.com/lite/`) parse path as secondary. |
| DDG ToS / scraping legality concern (Tier-3 surface, BLUEPRINT)     | Frame as the keyless default with SearXNG/Exa as upgrades; it's read-only GET, no auth. If operator objects → keep ddg behind an opt-in, ship autodetect-wire alone. **Flag to operator (Tier-3 doc trail).**                                                 |
| Native-tier user expects model search, gets ddg silently            | Only fires when native is **impossible** (no model). Order: native → byok → searxng → ddg. Never overrides a working higher tier.                                                                                                                             |
| New transitive parse dep                                            | None — reuse `lxml`/`httpx` already shipped. No `requirements.txt` change → no size hit, stays under 120 MB.                                                                                                                                                  |

## 4. Verification (exact commands)

```bash
# Unit: new backend + registry + fallback (write tests alongside ddg.py)
cd sidecar && python -m pytest tests/test_search_registry.py tests/test_web_search.py tests/test_searxng_backend.py -x -q
#  assert: registry.resolve("ddg") is non-None with NO key/url;
#  assert: web_search with tier="native", no exa_key, no searxng_url → ok:True, backend=="ddg"
#  assert: ddg backend maps a fixture HTML payload → SearchResult/Citation (monkeypatch httpx)

# Keyless research end-to-end (FAST web round now populated)
python -m pytest tests/test_research_fast.py -x -q
#  assert: gather_fast web.available == True via ddg fallback (mock tool_call→real web_search)

# Live smoke (network) — prove a fresh install actually searches:
python -c "import asyncio; from services.search.ddg import DdgSearchBackend; \
r=asyncio.run(DdgSearchBackend().search('NVDA earnings outlook')); \
print(len(r.results), r.results[0].url if r.results else 'EMPTY')"
#  expect: >0 results, a real URL

# Curl the running sidecar (CORS-masks-500 trap — curl direct):
curl -s -X POST 127.0.0.1:$PORT/agents/<id>/... -H 'X-Vysted-Search-Tier: native' \
  -d '{"query":"web search test"}'   # expect citations, not the unavailable message

# Gate: full parity (no new binary, so smoke-test unchanged but run it):
pnpm ci-local && node scripts/smoke-test-sidecars.mjs   # 3 sidecars, /health green
```

**Rig (tauri-mcp):** fresh-profile launch → Settings shows tier `native` → run a research prompt with **no keys set** → assert citations render (not "add a key"). Screenshot populated state per the visual-verification gate.

**In short:**

- **Ship option (c): a ~250-line in-sidecar DuckDuckGo backend as the unconditional keyless floor.** Zero new binary, zero size hit, fully testable tonight. The `web_search.py:54-65` fallback edit is the load-bearing change — it makes search never-dark.
- **The headline bug: `detect_searxng` is dead code** — the advertised 8888/8080 autodetect never runs. Wire it in `web_search.py` (cheap) so Settings copy stops lying.
- **Keyless DATA (US yfinance/ccxt, IN jugaad, RSS news) is genuinely on by default — verified, nothing gates it.** Keyless RESEARCH is structured-only today; the ddg backend lights up its web round, delivering "real research, no keys."
- **Log the ambitious path (bundled SearXNG externalBin) as deferred** — feasible but a 60-90 MB 4th binary + 4th cold-bind race, not shippable/verifiable tonight; revisit with `--onedir`.
- `Confidence: 8/10 — uncertain on DDG HTML markup stability long-term (mitigated by SearchError→structured-only degrade) and whether the operator wants DDG scraping as a default vs opt-in (Tier-3, surface it).`
