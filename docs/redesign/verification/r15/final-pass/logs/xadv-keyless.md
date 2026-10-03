# xadv-keyless — working log (Opus 5.5, claude-opus-5-5, effort medium)

Lens: brand-new Mac user, first five minutes, no API keys, no Docker. Head d38b5d1a (built worktree final-cand, read-only).
Own stack: clean data dir (dev-keystore `{"secrets":{},"migrated":true}`), main :52900, openbb-mcp :52901, sec-edgar-mcp :52902. Never touched :52800-52895, the operator data dir, keychain, /Applications, GUI.

Environment caveats: Docker/OrbStack + SearXNG exist on this box (SearXNG degraded) -> "no Docker" covered by code read + the keyless t1 tier; Ollama exists (llama3.1:8b) -> "no Ollama" simulated with a closed base URL :52909. Shared IP throttled (DDG hang, Brave/Mojeek captcha/429, yfinance 429, NSE historical resets) — findings were filed only where reproduced independent of throttling or the mechanism is source-proven.
vy.py refuses non-GET outside 52100-52399; the Ollama invoke payload was replicated with curl (no key), each run inside the /tmp/vysted-r15-ollama.lock hold.

Scenarios: 1 cold boot pass · 2 keyless quotes/chart/screener/news pass (values = NSE bhavcopy) · 3 holiday bhavcopy mislabel finding keyless:1 · 4 no-Ollama chat dead-end finding keyless:2 · 5 Ollama Kitex turn pass · 6 README vs reality finding keyless:3 (+A1->R15-DOCS-003, A2->R15-RELEASE-002 attached) · 7 research KITEX finding keyless:4, keyless:5 · 8 default cockpit + error edges pass · 9 first-launch window flow needs_gui.
Not filed (taste/env): 168 s cold boot under contention; BTC-USD unknown (app uses BTC/USDT); a news tag oddity; Macro defaults to FRED (honest key message; R15-UI-015 fixed, R15-LEAD-067 open); stale 2024 SME rows no universe surfaces.
Teardown: sleep-holder pids 36286 36292 36299 killed; ports 52900-52902 verified closed; lock absent.
