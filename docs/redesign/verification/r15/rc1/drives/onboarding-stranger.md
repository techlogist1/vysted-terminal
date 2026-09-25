# rc1-drive-onboarding-stranger — OWNER-DRIVE re-drive vs census

Agent: claude-sonnet-5 (Sonnet), 25 Sep 2026. Candidate sha `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`
(`rc1-cand` worktree, sidecar built from that source). Own sidecar booted from `rc1-cand/sidecar`
on **:52326**, data dir `rc1-data-onboarding-stranger` — created CLEAN/EMPTY, only
`dev-keystore.json = {"secrets": {}, "migrated": true}` seeded (chmod 600), per the task's
keyless-clean-profile instruction (no operator-data copy). MCP env pointed at the shared
read-only `openbb-mcp:52153` / `sec-edgar-mcp:52154` (GETs only, never restarted/written to).
Sleep pid 92807 (worker 92805); stopped at the end of this drive.

Method: read `docs/redesign/verification/r15/surface/onboarding-stranger/EVIDENCE.md`,
`COVERAGE.json`, `CENSUS/raw/surf-onboarding-stranger.json` and
`CENSUS/refute/surf-onboarding-stranger.json` (6 admitted findings, SURF-ONBOARDING-STRANGER-1..6)
plus the register (`docs/redesign/verification/vysted-r15-register.json`) to get each finding's
merged register id and RC1 status. For every finding whose register status is `fixed`, re-drove
the exact repro headlessly against the candidate and confirmed live; for `not_a_defect` /
`blocked_tier4` / `open`, re-checked the code/behaviour still matches the register's stated
current state (no regression). Then looked for new defects in the same surfaces.

## Scored table — census → rc1 delta

| # | Register id | Census verdict | RC1 re-drive | Score | Evidence |
|---|---|---|---|---|---|
| 1 | R15-UI-008 | admitted (high) | **FIXED, confirmed live**: `validate_key` now probes OpenRouter's `/key` (auth-required) instead of unauthenticated `/models`; a fake key returns `ok:false reason:invalid` end to end (frontend `CloudStep` unchanged — routes on the sidecar's answer, which is now correct) | ok | `rc1/K02-fake-openrouter-key.txt`; `sidecar/services/llm/openai.py:795-810` (candidate); direct curl proof: OpenRouter `/api/v1/models` fake-bearer = 200, `/api/v1/key` = 401 |
| 2 | R15-DATA-018 | admitted (high) | **FIXED, confirmed live**: `GET /resolve?q=zomato` and `q=ZOMATO` and `q=Zomato Ltd` all resolve straight to ETERNAL with a `rename` block (`renamed_from/renamed_to/effective_date`); autocomplete likewise; the disambiguation-led-by-HMT-Ltd sub-bug from the census note is also gone (clean `needs_disambiguation:false`) | ok | `rc1/R5-resolve-zomato.txt`, `R5-resolve-ZOMATO.txt`, `R5-autocomplete-ZOMATO.txt`; live curl of "Zomato Ltd" |
| 3 | R15-UI-052 | admitted (medium, 2 raws) | **FIXED, confirmed by code read**: welcome copy now reads "Live quotes, charts, news and screeners run right now. Pick a path below to turn on the AI agent (and its web research)…" — web research is no longer claimed keyless; local-path copy now says "it still reaches out for market data and web searches, but the model itself is yours" instead of "fully private…offline"; banner copy dropped "nothing leaves this machine" and now reads "Keys stay in your OS keychain — market data and web searches still go to public providers" | ok | `src/components/OnboardingFlow.tsx:237-243` (candidate); `src/components/OnboardingBanner.tsx:66-69` (candidate) |
| 4 | R15-UI-041 | admitted_with_correction (medium) | Register status `not_a_defect` post-D81 — **confirmed live**: `TOS_BODY` in the candidate is the rewritten research-terms text (no brokerage connection, orders/kill-switch/live-trading language gone; carries the data-may-be-wrong caveat, the AI-can-be-wrong caveat, and the PolyForm Strict/commercial licence line) | ok (matches register, correctly reclassified) | `src/modules/safety/DisclaimerFlow.tsx:29-34` (candidate) |
| 5 | R15-UI-076 | admitted (low) | Register status `open` — **confirmed still present, no regression**: chart still hardcodes `DEFAULT_CHART_SYMBOL = "SPY"` (`store/chart-drawings.ts:50`) and the watchlist `DEFAULT_SYMBOLS` is still SPY/QQQ/BTC/ETH/NVDA/AAPL while `DEFAULT_REGION = "IN"` — same contradiction as census | expected-open (unchanged) | `src/store/chart-drawings.ts:50`, `src/store/symbols.ts:30-36`, `src/lib/region.ts:37` (candidate) |
| 6 | R15-UI-019 (COD-frontend-panels-agent-shell-11, live-repro'd by the census, not separately filed as an onboarding-stranger raw) | fixed | **FIXED, confirmed live**: `OnboardingBanner`'s `defaultLaneNotReady` now derives from `useKeylessReadiness` (a real `/llm/keys/validate` probe), not a static flag; live probe for `provider:ollama, model:qwen3:8b` (the onboarding LocalStep's recommended model) returns `ok:true`, so `showBanner` would correctly evaluate false for a properly-configured local-model user | ok | `src/components/OnboardingBanner.tsx:35-49` (candidate); live curl `/llm/keys/validate {"provider":"ollama","model":"qwen3:8b"}` → `{"ok":true}` |
| 7 | R15-AGENT-028 (COD-error-layer-2-2, live-repro'd, not separately filed) | fixed | **FIXED, confirmed live**: a model-not-pulled probe now returns `reason:"model_not_pulled"` with a specific detail, and `ChatSidebar.tsx:831-836` routes that reason to "…opening setup to download it" + `useOnboardingStore.getState().open("local")` — the real Download-model flow, not the dead "pick another model in Settings" message the census hit | ok | live curl `/llm/keys/validate {"provider":"ollama","model":"llama3.1:70b-not-pulled-xyz"}` → `model_not_pulled`; `src/modules/chat/ChatSidebar.tsx:829-836` (candidate) |
| 8 | R15-UI-044 (COD-safety-audit-12, live-repro'd, not separately filed) | `blocked_tier4` | **Confirmed still present, no regression** (expected — register marks it blocked, not fixed): `hasFirstLaunchTosAck()` still calls `getSecret` with no try/catch, and `DisclaimerFlow`'s `refreshFirstLaunchAck` effect has no catch either — a keychain-denied read still throws uncaught, `hydrated` never becomes `true`, so the dialog silently never renders | expected-broken (unchanged, Tier-4 blocked in register) | `src/store/safety.ts:20-22, 39-42` (candidate); `src/modules/safety/DisclaimerFlow.tsx:44-49` (candidate) |
| 9 | (extra) `ZOMATO.NS` quote for the retired ticker | census: 502 leaking yfinance internals (`'PriceHistory' object has no attribute '_dividends'`) | **Improved, confirmed live**: now a clean `404 {"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found",...}` — no internals leak. Not filed as its own register id under onboarding-stranger census, but the same repro is now honest | ok (bonus fix, riding the resolver work) | live curl `/quotes/ZOMATO.NS` → 404 not_found |
| 10 | (extra) keyless first message factual accuracy on the renamed-symbol question | census A1: wrong ("I couldn't find Zomato… not covered") | **NEW DEFECT** (resolver-side wrongness is fixed, but a different failure surfaced): the model called `market_overview` (real tool_use event, no Zomato data in it), then instead of calling `price_data` for real it wrote a fenced "Tool call: `price_data(symbol="ZOMATO.NS")`" followed by a hand-typed JSON "Result" block (`current_price: 164.4`, a market cap, `"name":"Zomato Ltd."`) and answered "As per the live data, Zomato's stock price is currently ₹164.4…" — in the same message it also hedges "this information might not be up-to-the-minute as it relies on my training data" (self-contradicting the "live data" claim). `sidecar/services/llm/tool_call_rescue.py:109-111` only rescues a leaked `{"name": "<tool>", "parameters": {...}}` REQUEST shape whose `name` is in the round's offered tool set; my transcript's JSON is a fabricated RESULT shape with no `parameters` key, so the rescue mechanism (which fixed R15-AGENT-018) does not and cannot catch this — it is a distinct failure mode: the model narrating a fake tool invocation and a fake numeric result as prose, never going through the tool-call protocol at all. Filed below. | **broken** | `rc1/A1-keyless-zomato-rc1.stdout.txt` |

## New-defect sweep

Drove every remaining onboarding-group control/state not already covered by a register id:
hardware-fit `fits`/`does-not-fit` verdicts (`/system/hardware`, unchanged from census — 3
installed models green, reference red candidates unreachable-fit `marginal` on this 16 GB M1
Pro, same as census, not a regression), the `/llm/keys/validate` reason matrix for openrouter
(empty/whitespace key still `ok:false`), and the TOS/onboarding sequencing gate. The one
improvement not separately register-tracked (`ZOMATO.NS` 404 vs 502) is noted above as a
positive side-effect, not filed as a fresh finding (it rides the same resolver fix as
R15-DATA-018, already register-fixed).

One genuine new defect found (row 10 above, filed as `SURF-ONBOARDING-STRANGER-RC1-1` /
`findings/onboarding-stranger.json:rc1-drive-onboarding-stranger:1`): on the mandated local
free-lane probe (`llama3.1:8b`, the exact model `PROMPT_surface_s2.md` specifies for this
group's local-lane test), the keyless first message about the DEFAULT-lane-recommended stock
now resolves correctly server-side but the model itself fabricates a fake tool invocation and a
fake numeric quote in its answer text, prefaced with "As per the live data" — presenting
invented money-relevant data as authoritative on the exact path (keyless, first message, first
lane) every new stranger hits by default. Severity scored `medium` under this role's own rubric
("wrong or stale value = medium"), not `high`/`critical` under COMMON.md's general scale,
because it is non-deterministic small-model behaviour on the free/local lane (already documented
project-wide as unreliable — MEMORY.md "qwen 7b tool-use inconsistency", COMMON.md's own
"this model DOES call tools some of the time and fails others"), not a guaranteed-every-time
code bug, and the same message self-contradicts ("relies on my training data").

## Sidecar

Boot: `cd rc1-cand/sidecar && VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154 sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52326 --data-dir rc1-data-onboarding-stranger`.
`/health` ok, `openbb-mcp: available`. Stopped via `kill <sleep pid>` at the end of this drive.
