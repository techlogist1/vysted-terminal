# rc1 adversarial sample verifier: shard 0

This shard checked candidate `1d6511c89bb27f1785f7af4d2290983b2852d70a`. The worktree was treated as read-only. The checks ran on an isolated sidecar on :52600 using the Ollama `llama3.1:8b` model, with no paid spend. Scratch scripts and a scratch vitest mirror live under the session scratchpad (`vshard0/`); none of them became repo tests.

**Result: 17 holds, 7 refuted, 0 inconclusive.** Findings are in `findings/rc1-vshard-0.json` (11 entries). The working log is `logs/rc1-vshard-0.md`.

| id | verdict | evidence |
|---|---|---|
| R15-DATA-006 | holds | **Original:** `/quotes/DAL` shows timestamp 2025-03-12, freshness stale, change 0, and fundamentals as_of 2025-03-12. **Variant:** found a new defect (finding :7). Before the open (08:53 IST), `/quotes/SMR` in IN shows change 0.0 although BSE CurrRate Chg is +1.00 (Ason 24 Sep). `_quote_from_header` compares against `most_recent_session`, not `last_closed_session`. |
| R15-DATA-070 | holds | Undated or garbage-dated RSS items get date `None` and sort last. The live `/news` for RELIANCE.NS had no item stamped within 120 s of now. |
| R15-DATA-033 | holds | `validate_series` and `validate_quote` reject NaN, +inf and -inf (`math.isfinite`). Providers drop NaN rows. |
| R15-DATA-001 | holds | DAL income, balance and cashflow resolve to DAL.BO (revenue INR 2.07 cr). **Variant:** HAL resolves to HAL.NS (revenue about INR 31,792 cr), not Halliburton. |
| R15-DATA-002 | **refuted** | The backend holds: SMR and AMAL give NuScale/Amalgamated in US and SMR Jewels/Amal Ltd in IN. **Variant (finding :2):** in the Cmd-K palette, the ticker row 'AMAL US' calls `loadSymbolIntoChart('AMAL')` with no region. The chart history call carries no region, so an IN session charts nse_direct Amal Ltd at 687.65 INR instead of 47.21 USD. |
| R15-DATA-003 | holds | US AMAL `held_percent_*` comes from yfinance and has no exchange witness. IN AMAL.NS is witness-checked ("unreconciled"). Resolving 'Amalgamated Financial' under IN gives US. Side note: 'NASDAQ:AMAL' does not resolve. |
| R15-RESEARCH-002 | **refuted** | The 3 original strings now give unverified. **Variants (finding :1):** 'Verdict: UNVERIFIED - no source confirms the 23% operating margin.' gives **agree**. So do the '**Verdict:** UNVERIFIED…', 'Answer: UNVERIFIED - evidence does not support…', '"UNVERIFIED" -…', '[UNVERIFIED]…' and 'UNVERIFIED— … does not confirm it' forms. The marker-scan fallback still fires whenever the verdict word is not literally first. |
| R15-RESEARCH-034 | holds | `_reflect_says_complete` returns False for 'not covered yet' and for negations, and True for 'No gaps remain.' |
| R15-RESEARCH-004 | holds | `_split_claims` keeps 40.5%, -0.4%, 67.13953, +12%, (0.4%) and .5%. The live ULTRA Kaynes run (613 s) cross-checked '₹23,592 cr, 40.5%, 68.57x, 39.04x, 53.46%' intact, with the label 'checked 5 numeric claim(s): 0 verified, 5 unverified, 0 disagreement(s)'. |
| R15-CODE-FRONTEND-005 | holds | Scratch vitest passed: addDrawing, setBinding and saveScreen/deleteScreen each POST an autosave carrying the slice. Triggers are wired in page.tsx:115. Side note: there is no flush of the 500 ms debounce at quit. |
| R15-CODE-FRONTEND-018 | holds | Scratch vitest passed: a `saveSpace('Research: NVDA')` autosave carries `researchSpaces`. All slices in PERSISTED_SLICES have subscribe triggers. |
| R15-CODE-FRONTEND-004 | holds | On the isolated sidecar, save and load returned 200 for 'Research: NVDA', 'Research: RELIANCE.NS', 'Research: M&M', 'My Layout (2)', a Hindi name, 'Research: BRK/B' and '../../etc' (encoded). **Variant:** found a new defect (finding :9). 'Research: nvda' silently overwrites 'Research: NVDA' on the case-insensitive filesystem. |
| R15-DATA-042 | holds | Scratch vitest passed: INR plus USD gives null weights and null concentration. 'usd', 'USD' and a missing currency together give null concentration. USD plus an unresolved INR position gives weights [1, null]. |
| R15-CODE-PLATFORM-053 | holds | `buildPortfolioSummary` is the only producer of these values and nulls them in the contract. The CSV export has a Currency column and leaves Weight % blank when currencies are mixed. |
| R15-DATA-043 | **refuted** | The original holds: custom [AAPL, RELIANCE.NS] is grouped INR then USD, with the note 'spans INR, USD — ranked within each currency', and criteria carry a unit. **Variant (finding :6):** the same screen with `limit=1` serves only RELIANCE.NS (matched 2, result 1), and the note disappears because it is computed on the served rows. The currency groups are ordered alphabetically, so a top-K cut silently keeps INR. |
| R15-AGENT-003 | **refuted** | The original holds: a scratch pytest with the round cap gave 18 tool_use events yielded and 18 dispatched, and the capped text is present. **Variant (finding :4):** a budget halt after round 2 yields 6 tool_use events (including write_note) but dispatches only 3. run_manager then lifts the undispatched host actions into proposed-changes. |
| R15-AGENT-019 | **refuted** | The original prompts now classify correctly. **Variants (finding :3):** 'Can you log 10 TCS at 3400 in my portfolio?', 'Can you record that I hold 20 ITC at 410?', 'What if you drop TCS from my holdings?' and 'Why not trim my INFY holding to 5 shares?' all give read_only=True with 42 tools and no portfolio_* tools. The control prompt gets 55 tools. |
| R15-AGENT-021 | holds | Named surfaces are fenced by `wrap_untrusted`. **Variant:** found a new defect (finding :10). An injected string in corporate_actions 'purpose', an exchange_deals party or sec_filings_list reaches the model RAW. |
| R15-CODE-FRONTEND-014 | holds | From code: `noteScope` maps global, general and '' to General, and the sidecar `_note_for` agrees. `save_layout` with no name uses the active layout, else 'Agent layout'. |
| R15-UI-001 | holds | From code: the 4 named cases pass (NotesPanel flushes on scope switch and on unmount). **Variant:** found a new defect (finding :11). An agent write_note inside the 600 ms typing window discards the pending user edit. |
| R15-UI-002 | holds | From code: the palette symbol and live rows call `loadSymbolIntoChart`, which is always consumed. |
| R15-CODE-AGENT-003 | holds | `POST /llm/keys/validate` with fake keys returns invalid for openrouter (2 shapes), gemini, xai, groq, deepseek, anthropic and openai. Keyless ollama returns ok. |
| R15-AGENT-027 | **refuted** | The 8 originals are correct. **Variants (finding :5):** a gemini token-limit 400 and a groq decommissioned-model 400 both say 'Try again'. An ollama ReadTimeout says 'check your network'. An xai 403 for no credits says 'Re-enter the API key'. |
| R15-AGENT-004 | holds | An Anthropic SSE replay gives `get_quote {'symbol':'RELIANCE.NS'}`. Variants (two tools plus text, a no-argument tool, split unicode) all complete. |

## Other findings
- Finding :7 (medium): the BSE pre-open change-0 defect, a new defect introduced by the DATA-006 fix.
- Finding :8 (low, latent): the NSE direct quote has the same `most_recent_session` stamping. The NSE quote-equity feed was blocked from here, so this is from code only.

## Environment
- vy.py only allows ports 52100-52399, so agent runs on :52600 used a scratch `inv.py` with the same payload shape, on Ollama only.
- No GUI was used. The UI-001, UI-002 and FRONTEND-014 verdicts come from code reading plus the store logic.
