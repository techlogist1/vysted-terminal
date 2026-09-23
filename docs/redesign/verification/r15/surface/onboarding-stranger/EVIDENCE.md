# surf-S2D onboarding-stranger — OWNER-DRIVE evidence (keyless, CLEAN profile)

Agent: claude-opus-5-5[1m], 23 Sep 2026 09:24-09:50 IST. Claimed at 09:24 (`_CLAIM.txt`): the
failure-inducer twin was already claimed and live on :52224, this item had no dir, raw file or
sidecar. Continues past `SURFACE/seat-stranger/transcript.md` (19 Sep: pass-1 status GETs +
resolve/autocomplete sweep, stopped there): this drive does the onboarding SCREENS, the keyless
first message, the first data panels and the key paths, which the seat never reached.

## Stack (mine, stopped at the end)

- Main sidecar from source on **:52223**, data dir
  `<scratchpad>/vysted-iso/seat-onboarding-stranger/data` — created EMPTY, only
  `dev-keystore.json = {"secrets": {}, "migrated": true}` seeded (chmod 600). No operator data.
- MCP pair: openbb-mcp **:53223**, sec-edgar-mcp **:53233** (own binaries, `VYSTED_*_MCP_PORT`
  env on the main sidecar), per `ISO_STACK.md`. Pids: `<scratchpad>/vysted-iso/pids-surf-S2D-onboarding.json`
  (sleeps 37790 main / 37781 openbb / 37784 sec).
- Harnesses: `harness/drive.py` (HTTP, appends `http-log.jsonl`, tags B/C/K/R/S), vitest replay
  `<scratchpad>/s2d-onb/vt/onboarding.s2donb.test.tsx` (renders the REAL `OnboardingBanner` +
  `DisclaimerFlow` + `OnboardingFlow` in jsdom; Tauri `invoke` shimmed to an in-memory keychain and
  `get_sidecar_port -> 52223`, every `fetch` goes to the real sidecar; output
  `20-onboarding-replay.json`). LLM turns via `scripts/r15/vy.py` only (local lane; $0 spent).

## 1. First boot, clean profile (http-log B01-B16)

All 16 first-run GETs 200 in <0.1 s except `/search/searxng/status` (3.35 s, `ready` - shared
container, only read). `/workspace` = `[]`, `/portfolio/positions` = `[]`, `/agents` = 13,
`/mcp/status` ready 36 tools, openbb/sec MCP `available`. `/system/provider-health` already showed
the Yahoo breaker OPEN (`opens_total 2, throttles_total 85`) within ~2 min of an idle clean boot
(the machine's IP is shared with other lanes — noted, not filed). **ok.**

## 2. What renders, in what order (20-onboarding-replay.json)

| Step | Observed | Score |
|---|---|---|
| T1 before ack | TOS dialog shown; onboarding NOT shown (sequenced on `firstLaunchTosAcked`); key banner shown ABOVE the TOS: "Add a cloud provider key — or run a local model (Ollama) … nothing leaves this machine." | ok (order) |
| TOS text | "Please review the operating terms before connecting a broker. Vysted Terminal connects to live trading venues … All orders sent to your broker … Live trading mode requires per-broker disclaimer … kill switch … halts all order routing" | **broken content** → finding 4 |
| TOS accept | `keychain_set broker:_meta:first-launch-tos`, dialog closes, onboarding opens | ok |
| Escape on onboarding | stays open (prevented, `OnboardingFlow.tsx:164`) | ok |
| Welcome | "It already works — no key, no account. Live quotes, charts, news, screeners and web research run right now." / "Nothing leaves this computer except the model calls you authorize." | claims checked below → findings 2, 3 |
| Path A, empty / whitespace key | Save disabled (both) | ok |
| Path A "Get a key" | shell `open("https://openrouter.ai/keys")` | ok |
| Path A, FAKE key `sk-or-v1-000…notarealkey` | `POST /llm/keys/validate` -> `{"ok":true}`; key saved to keychain; default provider -> `openrouter`, model -> `deepseek/deepseek-v4-flash`; **"You're set — OpenRouter is connected — the agent and deep research are live."**; banner hides (`openrouter: configured`) | **broken** → finding 1 |
| Path B (real M1 Pro + real Ollama) | "Detecting your hardware…" → "Apple M1 Pro · 16 GB RAM · Apple Silicon · qwen3:8b runs locally · ~7.8 GB · fits with headroom … Use qwen3:8b" → click → provider `ollama`, model `qwen3:8b`, DoneStep "Your local model is set — the agent runs privately on your machine." | ok |
| Banner after Path B | still "Add a cloud provider key — or run a local model…" | live repro of COD-frontend-panels-agent-shell-11 (not re-filed) |
| Skip | `app-meta:onboarding-complete = "skip"`, closes; relaunch with same keychain: no TOS, no onboarding | ok |
| T5 keychain denied (every `keychain_*` rejects) | NO TOS, NO onboarding, only the banner; one unhandled rejection "User interaction is not allowed" | live repro of COD-safety-audit-12 (not re-filed) |

Not driven: LocalStep "Ollama not running" (install guidance) and "model not pulled → Download &
use" states — the machine's Ollama is shared (never stopped) and a real pull is state-changing
(skeleton note). `/system/ollama/status` hardcodes `127.0.0.1:11434` (`routers/system.py:27,153`)
while the adapter/pull honour `OLLAMA_HOST` via `ollama.AsyncClient()` — a divergence I could not
induce without touching the shared daemon; noted only.

## 3. Key validation from the stranger's side (K01-K09)

| Req | Result |
|---|---|
| K01 ollama, no key | ok:true (daemon up) |
| K02 openrouter FAKE key | **ok:true** — `openai.py:842-849` probes `client.models.list()`; OpenRouter's `/api/v1/models` is public: `curl -H "Authorization: Bearer <fake>" …/models` = **200**, same fake bearer on `…/api/v1/key` = **401** "User not found." |
| K03/K04 openrouter "" / null | ok:false "unauthorized or no key supplied" |
| K07 ollama at a dead base_url | ok:false, detail "unauthorized or no key supplied" (wording wrong for a dead daemon; only the bool is used) |
| K08 openrouter key + trailing space | ok:false "transport error: Connection error." (onboarding trims, `OnboardingFlow.tsx:348`; Settings does not — SURF-SETTINGS-PLUGINS-2) |
| K09 openai fake key | ok:false (correct) |

A3 (`A3-fake-openrouter-key-first-message.*`): the first agent message after the fake-key "You're
set" → `error code=auth "The OpenRouter API key was rejected — check it in Settings."` (0.5 s).
(vy.py refuses the paid default slug even with `--bad-key`, so a `:free` slug was used; the 401
path is key-level, not model-level — same frame as `inducer/01-401-badkey.txt`.)

## 4. Keyless first message (composer) — the default lane is local Ollama `qwen2.5:7b`

- A1 `A1-keyless-default-qwen25.*` — "hi, I just installed this. what can you do, and how is Zomato
  stock doing today?" → 182 s total, first token ~60 s; one `resolve_symbol("Zomato")` → not found →
  "I couldn't find Zomato in our database. It's possible they are listed on an exchange we don't
  have coverage for yet." **wrong answer** (ETERNAL is covered) → finding 5.
- A2 `A2-ollama-model-not-pulled.*` — model absent → `model_not_found` "The requested model is not
  available on Ollama — pick another model." / "Choose a different model in Settings." — no
  `ollama pull` hint (live repro of COD-error-layer-2-2, not re-filed).
- A4 `A4-donestep-research-nvda-qwen3.*` — the DoneStep's own suggestion "research NVDA" on the
  onboarding-recommended `qwen3:8b`: first token at 122 s, done at 463 s, input pinned at 16384; the
  research tool ran (4/4 data sources, "searching the web for NVIDIA CORP", 6 web sources: cnn,
  finance.yahoo, cnbc, tradingview, nasdaq, seekingalpha) and the runtime auto-published the brief
  (`publish_brief` `__autobrief`) — so "a visual brief lands" holds. The prose, however, tells the
  user "For real-time data, visit Yahoo Finance" although `structured.price` carried 228.87, and
  invents "Goldman … Sansera Engineering (a supplier to NVIDIA)". Research-quality is the
  research-briefs group's; recorded as evidence for finding 3 (what leaves the machine) and 4
  (no "AI output can be wrong" disclosure anywhere in first run).
- No-Ollama stranger: code-read `ChatSidebar.tsx:794-805` — `validateProvider("ollama")` false →
  status line "No AI model is set up yet — opening setup. (Quotes, charts, news and web research
  already work without one.)" + `useOnboardingStore.open()`. Cloud provider without key:
  `ChatSidebar.tsx:789-795` "No API key for <label>. Add one in Settings → AI Providers". Both
  honest except the web-research clause → finding 2.

## 5. First data panels, keyless (C01-C10, S01-S03, R01-R05)

Default cockpit (`config/default-layout.ts`): chart + equity-overview (tab) + watchlist + news +
portfolio. Region default `IN` (`lib/region.ts:39`) but chart = `SPY` (`ChartPanel.tsx:80`) and
watchlist = SPY, QQQ, BTC/USDT, ETH/USDT, NVDA, AAPL (`store/symbols.ts:21-27`) → finding 6.

| Req | Status / time | Note |
|---|---|---|
| C01 quotes SPY,QQQ,NVDA,AAPL | 200 1.4 s | ok |
| C02 BTC/USDT ticker | 200 2.4 s | ok |
| C03 history SPY | 200 0.3 s | ok |
| C04 fundamentals SPY | 200 **13.2 s**, every field null (ETF) | the equity-overview is empty by default (chips AAPL/RELIANCE/NVDA), so not a default-view defect |
| C05 news region IN | 200 2.0 s, 10 items (ET Markets, Zerodha Pulse, Mint; one off-topic Mint world story) | ok |
| C06/C07 RELIANCE.NS quote/history | 200 6.8 s / 5.7 s | ok |
| C08 fundamentals RELIANCE.NS | 200 2.1 s | ok |
| S01-S03 screener nifty50 PE<30, cold | 200 8.4 s: 49 evaluated, 25 rows, 1 skip (TATAMOTORS.NS "rate_limited"); warm 0.01 s | ok keyless on an empty profile |
| C09/C10/R01/R04 "zomato"/"ZOMATO" | resolve + autocomplete: no match | finding 5 |
| R02 "Zomato Ltd" | disambiguation led by "HMT Ltd" | finding 5 |
| R03 /quotes/ZOMATO.NS | **502** `yfinance quote failed for 'ZOMATO.NS': 'PriceHistory' object has no attribute '_dividends'` | library internals as the error text; failure-inducer's malformed-symbol domain, noted in finding 5 |
| R05 "eternal" | resolves ETERNAL NSE | the current symbol works |

Rename master check: my clean data dir's `data_cache.db` holds `nse_symbol_change:20260923`
(81,901 B, contains `ZOMATO`; NSE symbolchange.csv row `ETERNAL LIMITED,ZOMATO,ETERNAL,09-APR-2025`),
while `resolver_masters/nse_instruments.json` (2,675 rows) has only `ETERNAL`. The lane is loaded and
still never fires for the query — see finding 5.

## 6. Hardware fit (B02/B03)

`/system/hardware`: 3 installed models all `green` (qwen3:8b 8.1 GiB ctx 10240, qwen2.5:7b, llama3.1:8b)
plus reference candidates `red` ("can't hold a usable context") — `fits` and `does-not-fit` states
reached; `marginal` unreachable on this 16 GB machine. `/system/local-model-recommendation` scores
the catalog (recommends `qwen3:8b` 7.8 GiB ctx 12288 — the same model is scored differently by the two
routes, 8.1 vs 7.8 GiB; cosmetic, not filed). `verdictMeta` maps green/marginal/other →
"runs locally"/"tight"/"too large — remote" (`hardware-fit.ts:169-178`).

## Existing findings this drive reproduced live (NOT re-filed)

COD-safety-audit-12 (T5), COD-frontend-panels-agent-shell-11 (T3 banner), COD-error-layer-2-2 (A2),
COD-llm-adapters-2-4 + SURF-SETTINGS-PLUGINS-1 (mechanism + Settings instance of finding 1),
COD-rust-core-3 / INT-blueprint-192-1 (kill-switch line inside the TOS), INT-deferred-84-6 (keyless
default lane).
