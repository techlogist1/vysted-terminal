# Final-pass owner-drive — onboarding-stranger (final-drive-onboarding-stranger)

Head `d38b5d1a`. Keyless stranger on a CLEAN profile: my own sidecar `:52846` from `final-cand/sidecar`
(source), data dir `final-data-final-drive-onboarding-stranger` created EMPTY with only
`dev-keystore.json = {"secrets": {}, "migrated": true}` (0600), MCP pair `:52801/:52802`, sleep pid 86518
(stopped at the end). Read cross-checks on the shared `:52800` (X01-X05: same answers as my sidecar).
Drivers: `harness/drive.py` (HTTP, `http-log.jsonl`, tags B/K/U/C/X); a scratch jsdom vitest replay
(`harness/onb.fp.test.tsx`, config root `final-cand`, jsdom url `http://localhost:5173/?sidecar-port=52846`)
rendering the REAL `OnboardingBanner` + `DisclaimerFlow` + `OnboardingFlow` with Tauri `invoke` shimmed to an
in-memory keychain + app-meta and every fetch going to `:52846` (output `20-onboarding-replay.json`, T1-T11;
run 1 missed the "Use qwen3:8b" click on a harness regex and is kept as `...-run1-harness-regex-miss.json`);
one keyless agent turn via `vy.py` (scratch copy admitting `:52846`, diff noted) on llama3.1:8b under the
Ollama lock. $0 spent; no hosted lane used.

Evidence: `docs/redesign/verification/r15/surface/onboarding-stranger/final/`.

## Scored table

| # | Control / state | Final result | Score | Evidence |
|---|---|---|---|---|
| 1 | Clean first boot GETs | `/health` 0.9.0, `/workspace` `[]`, `/portfolio/positions` `[]`, 13 agents, `/mcp/status` ready 39 tools, Yahoo breaker closed, `/screener/default-universe` nifty50; `/safety/disclaimer-status` and `/brokers` 404 (removed with D81) | ok | http-log B01-B15 |
| 2 | Order of first-run surfaces | T1: terms dialog shown, onboarding held behind it, banner hidden (keyless default `ollama/qwen2.5:7b` probed ready) | ok | replay T1 |
| 3 | Terms text (R15-UI-041) | "no brokerage connection … cannot place, route or simulate orders", data-may-be-wrong, AI-can-be-wrong, PolyForm Strict / commercial | ok | replay T1 |
| 4 | Terms accept | `keychain_set app-meta:first-launch-terms`; dialog closes; onboarding Welcome opens | ok | replay T2 |
| 5 | Welcome copy (R15-UI-052) | "Your keys, notes and portfolio stay on this machine — market data and web searches go to public providers." / "Live quotes, charts, news and screeners run right now." | ok | replay T2 |
| 6 | Escape on onboarding | stays open | ok | replay T3 |
| 7 | Cloud: empty / whitespace key | Save disabled both | ok | replay T4 |
| 8 | Cloud: Get a key | shell open `https://openrouter.ai/keys` (shim; real browser NEEDS-GUI) | ok | replay T4 |
| 9 | Cloud: fake key (R15-UI-008) | "That key wasn't accepted by OpenRouter. Check it and try again."; no keychain write; default stays `ollama` | ok | replay T4; K02 |
| 10 | Cloud: fake key + trailing space/newline (R15-UI-057) | same "not accepted" (trimmed, not a transport error) | ok | replay T4; K05 |
| 11 | Provider unreachable (closed local port 59997) | openrouter/openai `reason:unreachable` "Could not reach … — check your network. Check your internet connection and try again."; ollama "Ollama is not running. Start Ollama …" | ok (Ollama copy attached to open R15-LEAD-133) | U01-U03 |
| 12 | Validate bad body | extra field 422 `extra_forbidden`; unknown provider 422 literal list | ok | U04, U05 |
| 13 | Local step: hardware + recommendation | "Detecting your hardware…" then "Apple M1 Pro · 16 GB RAM · Apple Silicon · qwen3:8b runs locally · ~7.8 GB · fits with headroom" | ok | replay T5; B02/B03 |
| 14 | Local: Use qwen3:8b | default `ollama`, model `qwen3:8b`, DoneStep "Your local model is set …", `app-meta onboarding-complete=local` (not keychain: R15-CROSS-PLATFORM-011) | ok | replay T5_done |
| 15 | Start exploring + relaunch | closes; relaunch with same stores: no terms, no onboarding | ok | replay T5_closed, T6 |
| 16 | CTA re-open at local step (R15-AGENT-028 route) | `open("local")` after seen → local step renders | ok | replay T7 |
| 17 | Skip | `onboarding-complete=skip`, closes | ok | replay T8 |
| 18 | Banner, default model not pulled | banner shown (public-providers disclosure); Dismiss → `onboarding-banner-dismissed`, hidden | ok | replay T9 |
| 19 | Banner, keyless default ready (R15-UI-019) | hidden | ok | replay T1, T6 |
| 20 | Local: Ollama not running branch | install guidance + Download Ollama + brew line + re-check; re-check with daemon up → "Use qwen3:8b" | partial (status STUBBED `running:false`; the shared daemon is never stopped) | replay T10 |
| 21 | Keychain denied on first launch (R15-UI-044) | no terms, no onboarding, banner hidden, unhandled "User interaction is not allowed." | broken — known, blocked_tier4, attached | replay T11 |
| 22 | Validate: ollama ready / not pulled / openai fake / deepseek no key | ok:true; `model_not_pulled` with detail; OpenAI `invalid`; DeepSeek `not_configured` | ok | K06-K10 |
| 23 | First cockpit, IN defaults (R15-UI-076) | chart `^NSEI`, watchlist `^NSEI, RELIANCE.NS, TCS.NS, HDFCBANK.NS`; quotes 200 (23.6 s cold for 4 NSE names); ^NSEI quote 22,421.95 = last history close 2026-10-01 | ok | replay `defaults`; C01-C03 |
| 24 | News IN, fundamentals RELIANCE.NS | 200, 10 items; 200 (14.8 s cold) | ok | C04, C05 |
| 25 | Renamed stock (R15-DATA-018) | `zomato`/`ZOMATO`/autocomplete → ETERNAL; `/quotes/ZOMATO.NS` clean 404 not_found; ETERNAL.NS 313.9 | ok | C06-C11, X04 |
| 26 | Keyless first message (llama3.1:8b, "what can you do, and how is Zomato doing") | 71 s; real `market_overview(region=IN)` ok, indices table matches the quote; no fabricated figure; then a raw `{"name": "get_stock_data", …}` blob (tool not offered, so not rescued) and no Zomato answer | partial (model output; see notes) | A1-keyless-zomato-llama31.* |
| 27 | Live model download, real browser links, real window | — | NEEDS-GUI | NEEDS_GUI.md entry |

## Census → final deltas

- Census broken, fixed since and still holding at d38b5d1a: R15-UI-008, R15-UI-057, R15-UI-052, R15-UI-019,
  R15-AGENT-028, R15-DATA-018, R15-UI-076 (now fixed: IN cockpit defaults; rc1 still saw SPY), R15-UI-041
  (not_a_defect, the terms text is the post-D81 one). No regression of any fixed entry in this group.
- New since rc1 and driven: onboarding/banner flags live in the data-dir app-meta file (R15-CROSS-PLATFORM-011)
  and the terms ack moved to `app-meta:first-launch-terms` in the keychain; the unreachable-validation detail is
  humanised (R15-CODE-AGENT-019; no raw SDK text).
- First full jsdom render of all three first-run surfaces since the census (rc1 rounds were code-read only).
- Still present, known: R15-UI-044 (keychain-denied dead end, blocked_tier4), R15-LEAD-133 (Ollama
  unreachable says "Start Ollama" and does not open the guided install), both attached in ATTACHED.json.
- Keyless first message: the census (qwen2.5:7b) said "couldn't find Zomato"; rc1 round 5 (llama3.1:8b) made up
  a ₹122.5 price (R15-LEAD-030). This time no figure was made up; the turn ended in a JSON blob for a tool that
  does not exist. That is model output shown as text, not as data (R1(b)), so it is not filed.

## Findings

None admitted. Attached: R15-UI-044 (T11), R15-LEAD-133 (U02). NEEDS-GUI: links, live pull, keychain
denial, real window (NEEDS_GUI.md).
