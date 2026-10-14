# UI-7 — a stranger with no keys reaches a usable keyless path (final-adv-maintainer, d38b5d1a)

Stranger profile: the BUNDLE sidecar binary on :52820 with a fresh data dir ($S/final-stranger-maintainer), no keystore, no keys.

- Keyless data (UI-7/keyless-probes.txt, X-Vysted-Region IN): /quotes/RELIANCE.NS, /history/INFY.NS, /news, /resolve "tata motors" → TMCV (post-demerger), /agents (13) all 200 with real data; /llm/providers lists the keyless `ollama` lane.
- Whole app, first run (scratch jsdom, real `<Page/>` from src/app/page.tsx with ?sidecar-port=52820; UI-7/harness-firstrun.json): within 2 s the shell shows "Connected", the agent composer defaults to "Ollama (local) · Qwen2.5 7B" with starter prompts (Research $NVDA, Compare AAPL vs MSFT, …), and the keyless panels populate (watchlist ^NSEI/RELIANCE.NS/TCS.NS/HDFCBANK.NS with EOD prices, News Feed with sentiment). Only Tauri-only calls fail in jsdom (`invoke` undefined) — expected outside the shell.
- A keyless local agent turn on the same bundle binary completed ok in 53.6 s (LS-1).
- Observed on the way (filed as a free attack, maintainer:4, low): the News Feed renders "F&amp;O Talk: …" literally.

GUI half (first-run terms/onboarding screens and the no-Ollama empty state on the packaged shell) appended to NEEDS_GUI.md.

VERDICT UI-7: pass
