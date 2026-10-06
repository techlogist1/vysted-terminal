# rc1-drive-onboarding-stranger — round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `:52326`, clean empty data dir
(`dev-keystore.json = {"secrets": {}, "migrated": true}` only). Shared `:52152` used for read-only
comparisons where noted. Method: continue the census (`SURFACE/onboarding-stranger/EVIDENCE.md`,
23 Sep), re-drive each row that the register now marks `fixed`, plus one keyless agent round-trip.
Raw file per row under this directory (`01`-`22`).

## Scored table

| # | Row | Census result | RC1 round-5 result | Score | Evidence |
|---|---|---|---|---|---|
| 1 | Fake OpenRouter key validate | `ok:true` (R15-UI-008, "OpenRouter is connected") | `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` — probes `/key` now, not `/models` (`sidecar/services/llm/openai.py:815-836`) | **ok — regression fixed, confirmed** | `01-fake-openrouter-key-validate.json` |
| 2 | Empty key validate | `ok:false` | `ok:false, reason:not_configured` | ok (unchanged) | `02-empty-openrouter-key-validate.json` |
| 3 | Trailing-space key | Settings never trimmed (R15-UI-057); onboarding trimmed client-side | Sidecar itself now rejects a padded fake key as `invalid` (not a transport error) | **ok — fixed, confirmed** | `03-trailingspace-openrouter-key-validate.json` |
| 4 | Resolve "zomato" (R15-DATA-018) | "No instrument matched" | `{"symbol":"ETERNAL", ..., "rename":{"renamed_from":"ZOMATO","renamed_to":"ETERNAL", ...}}` | **ok — fixed, confirmed** | `04-resolve-zomato.json` |
| 5 | Resolve "Zomato Ltd" | Disambiguation led by "HMT Ltd" | ETERNAL top match, confidence 0.99, disambiguation candidates now sane (ROBU/FLUIDOM/JOJO/OMAXAUTO/IZMO) | ok — fixed | `05-resolve-zomato-ltd.json` |
| 6 | Ollama model not pulled, validate | 404 humanised to "pick another model" with no pull hint (R15-AGENT-028) | `reason:model_not_pulled`; `ChatSidebar.tsx:831` now opens `useOnboardingStore.open("local")` (the Download-model step) instead of dead-ending | **ok — fixed, confirmed (code + API)** | `06-ollama-model-not-pulled-validate.json` |
| 7 | `/system/hardware` | M1 Pro 16GB, 3 models green | identical shape/verdicts | ok, no change | `07-system-hardware.json` |
| 8 | `/workspace` fresh profile | `[]` | `[]` | ok | `08-workspace-empty.json` |
| 9 | Keyless composer, llama3.1:8b, "how is Zomato stock doing" | qwen2.5:7b said "couldn't find Zomato" (resolver miss, R15-DATA-018) | Resolver is now fixed (see #4), but the AGENT itself never called a price/resolve tool for Zomato — only `market_overview()` — then narrated `**Calling price_data for Zomato...**` (never issued) and stated a fabricated ₹122.5 / 52w-high ₹152.8 / low ₹82.2 with no tool result behind any of it | **not filed as a fix-round item** — this is a live instance of **R15-LEAD-030** ("llama3.1:8b narrates a fabricated 'tool returned' citation for a financial figure no tool result carries"), which is `blocked_tier4` under DECISIONS 4.9-4.12. Recorded here as a **concurrence**, not a new defect or regression, per the round's standing rule (1). | `09-keyless-zomato-llama31.jsonl` |
| 10 | `/system/region` | n/a | 404 (no such route; region rides `X-Vysted-Region` header / other endpoints, not its own GET) | ok, non-issue | `10-system-region.json` |
| 11 | `/portfolio/positions` fresh | `[]` | `[]` | ok | `11-portfolio-empty.json` |
| 12 | `/agents` | 13 agents | roster present (not re-diffed line by line; out of this group's scope) | ok | `12-agents-list.json` |
| 13 | Quotes SPY/QQQ/NVDA/AAPL | 200, 1.4s | 200, live prices | ok | `13-quotes-default-watchlist.json` |
| 14 | Fundamentals SPY (ETF) | 200, 13.2s, every field null | now a clean `404 not_found` "check the symbol" | ok — behavior changed from silent-null to typed error; not a regression (arguably an improvement, not scored as a fix since it wasn't a registered defect) | `14-fundamentals-spy.json` |
| 15 | News region IN | 200, 10 items | 200, populated feed | ok | `15-news-region-in.json` |
| 16 | Screener nifty50 PE<30 | 200, 49/50 evaluated | 200, 49/50 evaluated, `throttled:false` | ok | `16-screener-nifty50-pe30.json` (note: request shape is `criteria`/`operator`, not `filters`/`op` — a stale query in this drive's first attempt 422'd correctly, not a product defect) |
| 17 | Autocomplete "zom" | n/a | Returns `ZOMDF` (Zomedica, US) as the best 3-letter prefix match, not ETERNAL | ok — a 3-char prefix legitimately favors a symbol-prefix match over a former-name substring match; full "zomato" (#19) resolves correctly, so not filed | `17-autocomplete-zom.json` |
| 18 | Quotes `ZOMATO.NS` (stale ticker) | Census R03: `502` with `yfinance` internals leaking (`'PriceHistory' object has no attribute '_dividends'`) | `200 []` — degrades cleanly, no stack trace | **ok — silent-crash-to-clean-empty is an improvement**; not filed as a regression (it was never a `fixed` register item — recorded as a favorable delta) | `18-quotes-zomato-ns-stale.json` |
| 19 | Autocomplete "zomato" (full) | n/a | ETERNAL, confidence 1.0, rename annotation | ok | `19-autocomplete-zomato-full.json` |
| 20 | TOS body content read | Census finding 4: "broken content" — described live trading venues, broker orders, a kill switch that "halts all order routing" (register `R15-UI-041`, adjudicated `not_a_defect`) | `DisclaimerFlow.tsx` `TOS_BODY` is now completely rewritten: "Vysted has no brokerage connection. It cannot place, route or simulate orders," plus AI-output and data-accuracy disclosures and a licensing line | **ok — the D81 trading removal resolved this in substance**, even though the register entry is formally `not_a_defect` (not `fixed`); no regression | `20-tos-body-coderead.txt` |
| 21 | Banner gate logic read | Census: banner still nagged a correctly-configured local-model user (live repro of a known finding) | `defaultLaneNotReady` now conditions on the keyless lane's own readiness probe (R15-UI-019 fixed) | **ok — fixed, confirmed** | `21-banner-gate-coderead.txt` |
| 22 | OpenRouter validate code read | n/a | Confirms `/key` probe path backing row 1 | ok | `22-openrouter-validate-coderead.txt` |

## Census → RC1 deltas

- **Fixed and confirmed live:** R15-UI-008 (fake key), R15-UI-057 (trailing space), R15-DATA-018
  (Zomato→Eternal resolver), R15-AGENT-028 (model-not-pulled routes to download step),
  R15-UI-019 (banner no longer nags a working local user), R15-UI-052 (no more "nothing leaves
  this computer" / "web research runs now" false claims), R15-UI-013 (validation reasons split:
  `invalid` / `not_configured` / `unreachable` / `model_not_pulled`, each with its own copy).
- **Substantively resolved though registered `not_a_defect`:** R15-UI-041 (TOS content) — the D81
  trading removal rewrote the TOS body; it no longer mentions brokers, live trading or a kill
  switch, and now carries the disclosures the census said were missing.
- **No regressions found** on any item the register marks `fixed` for this group.
- **Unchanged, out of this round's scope:** R15-UI-076 (region defaults to IN but the seed
  watchlist/chart still hardcode SPY) — still `open`/low in the register, not part of this gate's
  fix batch; reconfirmed present, not filed again.
- **Concurrence, not a fix-round finding:** a fresh instance of R15-LEAD-030 (llama3.1:8b
  fabricates a "calling price_data" narration and a specific price with no such tool call in the
  event log) reproduced live on the keyless default lane — recorded per row 9 above and per the
  round's standing rule on this defect class (blocked_tier4, DECISIONS 4.9-4.12); not added to
  `findings/rc1-drive-onboarding-stranger.json`.

## Not driven this round

- A live `ollama pull` and the "Ollama not running" LocalStep state (shared daemon, state-changing;
  same skip rationale as the census).
- Full jsdom re-render of `OnboardingFlow`/`DisclaimerFlow` (budget; the underlying logic and copy
  changes were verified by direct code read plus the API calls that back them, which is where every
  register-cited defect actually lived).

Evidence root: `docs/redesign/verification/r15/surface/onboarding-stranger/rc1/round-5/` (files
`01`-`22`). Findings file: `docs/redesign/verification/r15/rc1/round-5/findings/rc1-drive-onboarding-stranger.json`
(empty — no regressions, no new defects, no fix-round items this round).
