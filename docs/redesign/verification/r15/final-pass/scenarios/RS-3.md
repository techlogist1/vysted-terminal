# RS-3 — web search status with SearXNG unusable, and the OpenAI web-search lane (investor lens)

Raw: `raw/investor/rs3-status.txt`, `raw/investor/rs3-openai-web.log|.jsonl`.

## Status routes (sidecar :52810 and :52381, 15:10-15:13 IST)
- `GET /search/searxng/status` -> state `degraded`, detail "SearXNG is running but its search engines are blocked", reason "brave: Suspended: too many requests; duckduckgo: timeout; startpage: Suspended: CAPTCHA", container running (shared vysted-searxng on :8888 — not mine, not touched). Honest about the outage; no fake "ok".
- `GET /search/status` -> tier t1_keyless, available true, DDG/Brave/Mojeek all `closed`.

## OpenAI lane web search (gpt-4o-mini, options modelWebSearch true, :52381)
- The model called the LOCAL `web_search` tool (no `{"type":"web_search"}` tools entry): no 400. The OpenAI native-search per-model gate holds.
- Tool result ok:false: "keyless web search has no engine available right now — DuckDuckGo: unreachable; Brave: rate-limiting; Mojeek: rate-limiting …". The answer said it could not retrieve the announcements and invented nothing. Spend $0.0113 (app estimate, two rounds).
- Observation, not filed: right after that failure `/search/status` on the same sidecar still reported all three engines `closed` / "available". `search/breaker.py` trips only after 2 consecutive failures (DEFAULT_FAIL_THRESHOLD), so one failed sweep does not change the status. That is how it was designed, and the error message itself is honest.

VERDICT RS-3: pass
