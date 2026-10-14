# rc1 gate round 5 — adversarial sample verifier, shard 8 (rc1-vshard-8)

- Candidate: `633f844071d972b337f4c3526d86555c80df0568`. `git rev-parse HEAD` in the scratch worktree `rc1-round-5-9bc600e-fix-int` printed this sha before every run. The worktree was only read. The vitest runs used `--cache=false`, and `git status` afterwards showed only the pre-existing `spend-ledger.jsonl` change.
- Own sidecar: the source boot on :52608 with data dir `rc1-round-5-data-rc1-vshard-8`, sleep pid 87537. It was stopped by that pid and the port is closed.
- The llama3.1:8b agent runs went to the shared stack :52152 in mode `ask` with autonomy `ask`, so they were read-only. `vy.py` refuses non-GET calls outside 52100-52399, and :52608 is outside that range. Every run held the Ollama lock.
- Raw evidence: `verifier/shard-8-raw/`. The scratch scripts are saved there as `*.py.txt` / `*.ts.txt`.
- Upstream: Yahoo (yfinance) returned 429 intermittently throughout the run. The sidecar log says "Too Many Requests", and the Yahoo-family circuit opened in-process. Fresh-process calls to yfinance fundamentals were throttled the whole time. Where a live leg was throttled, I proved the same code path by another route, as noted below.

## Verdicts

| id | verdict | one line |
|---|---|---|
| R15-LEAD-031 | **NOT CERTIFIED (refuted by a fresh case)** | The literal sify-1 repro holds. A type-first leaked call streams whole, and the guard's replacement is glued onto it. |
| R15-LEAD-033 | **NOT CERTIFIED (refuted by a fresh case)** | The literal repro holds, because `[tool steps:` is stripped. The sibling `[failed: …]` trailer from the same `withTrailer` still rides the assistant content, and llama echoed it. |
| R15-LEAD-034 | holds | `-SM` infix stripped in `_match_key`. Fresh random Emerge names pass the gate and the registry. |
| R15-CODE-PLATFORM-013 | holds | 157/157 pinned vitest tests pass. The fresh case (blob with plugin on restored while the plugin is disabled, and the reverse) behaves correctly. |
| R15-LEAD-028 | holds | Quotes, history, fundamentals, income, indicators and shareholding all resolve by scrip code. The fresh case is RELIANCE 500325. |
| R15-DATA-064 | holds | 30m serves 286 bars. Explicit ranges clamp to Yahoo's caps with `partial` and `coverage_start` set. BSE-only 30m has reason null. |
| R15-CODE-AGENT-034 | holds | Both workspace MCP tools work through a FastMCP client. The fresh case is a name with spaces and parentheses. |
| R15-DATA-116 | holds | All 5 repro symbols return 200 with June-2026 quarters. The fresh case is a 2026 IPO addressed by ticker and by code. |
| R15-RESEARCH-015 | holds | The one-domain case is unverified. Fresh cases on co.uk, com.au, in./www., api./www. and indiatimes subdomains are all unverified. |
| R15-AGENT-093 | holds | Coercion works at every depth across 12 fresh params and tools. 'ten', '7.5' and 'NaN' stay invalid. |

LEAD-028 and CODE-PLATFORM-013 both stand at two certification failures, so a third one would stop them for the operator. Both HOLD in this shard.

## R15-LEAD-031 — not certified

- **Entry repro (holds).** I ran the real `OllamaProvider` with a fake `ollama.AsyncClient` through `agent_runtime.invoke_agent`. Round 1 used the sify-1 chunking `' {"','name','":',' "','fundamentals','", "parameters": {"symbol": "SIFY"}}'`. Round 2 was "SIFY's ADR-to-ordinary-share ratio is 1:1, per the fundamentals tool." The streamed text was `"The ADR-to-ordinary-share ratio is not available from this session's sources."`, and no fragment reached the stream.
- **Fresh case (reproduces the title defect).** The round-1 leak uses llama's type-first key order: `{"type": "function", "name": "fundamentals", "parameters": {"symbol": "SIFY"}}`. `rescue_leaked_tool_call` recognises it and the fundamentals call runs. `LeakHold` never holds it, because `_MARKER` and `_PARTIAL_JSON` require `{"name"` as the first key. The whole JSON streams, and the ratio guard's replacement is glued on with no separator:
  `'{"type": "function", "name": "fundamentals", "parameters": {"symbol": "SIFY"}}The ADR-to-ordinary-share ratio is not available from this session\'s sources.'`
  The same happens after leading prose (`'Let me check. {"type": ...}}The ADR-...'`) and with plain prose (`'...}}Sify is an Indian ICT company.'`).
- Command: `cd <worktree>/sidecar && PYTHONPATH=. ./.venv/bin/python shard-8-raw/l031rt.py.txt`. Output is in `l031rt-final.txt`. The adapter-level view is in `l031.txt`: the entry shape is `shown=''`, and the type-first shape is `shown='{"type": ...}}'` with `rescued=('fundamentals', …)`.
- Root-cause pointer: `sidecar/services/llm/tool_call_rescue.py` `_MARKER` / `_PARTIAL_JSON` / `leak_start`. These only recognise `{"name"` as the opening. `rescue_leaked_tool_call` accepts any key order through `json.loads`, so the hold and the rescue disagree about what counts as a leaked call.

## R15-LEAD-033 — not certified

- **Entry repro (holds).** On :52152 with llama3.1:8b, I sent the entry's literal turn-1 history (`"The market cap of AAPL is $4.90T.\n\n[tool steps: Using fundamentals]"`) and the prompt "Which tool gave you that market cap figure? Show exactly what it returned." The answer contains no `[tool steps` text (`grep -c` on the raw jsonl is 0). I ran turn 1 live too, but Yahoo returned 429 on fundamentals, so turn 2 used the entry's literal history.
- **Fresh case (reproduces the defect class).** `withTrailer` in `src/store/chat-history.ts:300-311` builds the trailer from two lines, `[tool steps: …]` and `[failed: …]`. The runtime's `_without_step_trailers` (`agent_runtime.py:660-676`) strips only `[tool steps:`. I sent the history `"SIFY's market cap is $420M and it last traded at $5.80.\n\n[tool steps: Using fundamentals; Using price data]\n\n[failed: provider error: yfinance history rate-limited for 'SIFY']"` with the prompt "Repeat your previous answer to me word for word…". llama answered `"SIFY's market cap is $420M and it last traded at $5.80.\n\n[failed: provider error: yfinance history rate-limited for 'SIFY']"`, so the bookkeeping line and internal error text came out as its own prose. The in-process capture (`l033-inproc.py.txt`) proves the provider-bound assistant message still carries the `[failed: …]` line, so this is deterministic and not model noise.
- If the lead grades this narrowly on the title's literal `[tool steps: …]` string, that half holds. The residual is the same trailer function and the same echo mechanism.
- Concurrence only: in the entry-repro turn 2, llama wrote a fabricated `price_data` dump (`"quote": {"market_cap": 2433600000000}`). That is the local-model figure-without-an-ok-result class, the known limitation under DECISIONS 4.9-4.12 (LEAD-030/035/037/038). It is not filed as a defect.

## Holds — evidence

- **LEAD-028.** `GET /quotes/506597.BO` -> AMAL 673.05 (bse). `/quotes/544774.BO` -> SMR. `/history/544774.BO?range=1y` -> 72 bars (bse). `/fundamentals/506597.BO` -> "Amal Ltd". `/544774.BO` -> "SMR Jewels Limited". `/532540.BO` -> TCS. `/506597.BO/income` -> 5 periods. Fresh case: `500325.BO` quote, history and fundamentals -> RELIANCE. `/indicators/506597.BO` -> AMAL (bse). `/disclosures/shareholding?symbol=506597.BO` -> 104 quarters. `500209.BO/balance` came back as canonical `INFY.BO` with empty periods, the same as the `INFY.BO` ticker form, so this is not code-specific.
- **DATA-064.** `/history/{SPY,AAPL,RELIANCE,RELIANCE.NS,TCS.NS}?timeframe=30m` -> 286 bars, reason null. With `range=1y`, RELIANCE.NS returned 767 bars and AAPL 780, both with `partial:true` and `coverage_start` about 60 days back. Fresh cases: INFY.NS 15m 6mo, MSFT 1h 5y (730d), ASML 5m ytd and HDFCBANK.NS 1m 1mo (7d) all clamp and set `partial`. `AMAL.BO` and `506597.BO` at 30m -> 254 bars, reason null. `/indicators/SPY?…30m` and `/indicators/TCS.NS?…30m` -> populated. The agent's `_price_data` uses the same `provider_registry.get_history` path. Its in-process leg hit Yahoo 429.
- **CODE-AGENT-034.** I saved `vshard8-ws` and `Desk 2 (vshard8)` to my own sidecar, then used a FastMCP `Client(_build_server())` with `VYSTED_SIDECAR_INTERNAL_BASE_URL=:52608`. `list_workspaces` returns a dict, and `get_workspace` returns both blobs. A missing name returns `{ok:false, 404}`, and `is_error` is False on every call. `list_agents`, `list_workflows` and `list_runs` also return dicts.
- **DATA-116.** `/disclosures/shareholding` for AMAL, DAL, NAPEROL, JUMBO and ELCIDIN -> 200 with the latest quarter 2026-06-30 (bseindia XBRL). Fresh cases: `SMR.BO` and `544774.BO` -> 200. `_fetch_shp_index` goes through `_api_json` (`bse_provider.py:877-883`).
- **LEAD-034.** `symbols_match('INSPIRE','INSPIRE-SM.NS')` is True. Fresh random Emerge names (SKP, RULKA, SILKFLEX, THESL) are True. The negatives `INSPIRESM.NS` and `SBINSM.NS` are False. `validate_fundamentals` and `validate_series` pass for `X-SM.NS` results against bare requests. `provider_registry.get_fundamentals('SKP'/'RULKA')` returns the `-SM.NS` result with yfinance faked, because Yahoo was 429 live. The sidecar log has 0 "symbol mismatch" lines across the IN warm crawl.
- **CODE-PLATFORM-013.** `vitest run --cache=false` on modules, store/workspace, lib/workspace, plugin-runtime and SettingsPanel tests -> 157/157. Fresh case (`plat013.test.ts.txt`): an older blob with `plugin:vysted-example=true` restored while the plugin is disabled keeps it off, with 0 plugin commands live. An older blob with the flag false restored after re-enabling keeps it on, with 1/1 commands live. The serialised blob carries no `plugin:*` key.
- **RESEARCH-015.** Run in-process with `cross_check` and the test-suite fakes. Entry case: `blog.example` on both lanes -> unverified, corroborated False, 0 verdict calls. Fresh cases, all unverified with 0 verdict calls: `bbc.co.uk` www/news, `in.reuters`/`www.reuters`, `api.bseindia`/`www.bseindia`, economictimes/timesofindia on `indiatimes.com`, `asx.com.au` subdomains, and a single-lane `sec.gov` pair. Control: reuters + bloomberg -> agree and corroborated.
- **AGENT-093.** Entry repro through `_normalise_tool_args`: option_chain `'5'`, sec_filings_list `'10'`, sec_insider_transactions `'100'` and corporate_announcements `'10'` all coerce to int. Fresh cases that coerce: price_option numbers, price_bond enum `'2'`, walk_forward `'3.0'`, boolean `'true'`, negative `'-0.005'`, `' 25 '`, `'1e2'`, and a stringified `instruments` array with nested strings. `'ten'`, `'7.5'` and `'NaN'` stay invalid. The catalog has no numeric union-typed param.

## Concurrence notes (no new defect)

- R15-AGENT-090 (DECISIONS 4.17). With round-2 chunks ending in a bare trailing space (`', per the '`), the ratio-guard replacement left an orphan `' fundamentals tool.'` behind it (`l031rt-tail.txt`, first run). This is the adjudicated segment-close-on-trailing-whitespace residual.
- Harness. Twice, my lock-release trap found `/tmp/vysted-r15-ollama.lock` already gone while my Ollama call was still running, which means another holder removed a live lock. Recorded here as a harness race, not a product fault.
