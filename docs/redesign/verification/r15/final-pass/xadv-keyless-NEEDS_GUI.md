# xadv-keyless — needs_gui items (operator-attended)

## NG-1 (xadv-keyless-9): keyless stranger's first launch, no Ollama
Head d38b5d1a build. A macOS user account (or a clean data dir + a debug build seeded with dev-keystore.json `{"secrets": {}, "migrated": true}`) with NO provider keys, and Ollama NOT installed (or quit, and `ollama` not on PATH).
1. Launch. Accept the terms dialog.
   Expected: the welcome dialog shows "It already works — no key, no account." with "Connect a model" and "Run it locally" cards; no mention that web research works without a model.
2. Click "Skip — I'll explore first →".
   Expected: "You're exploring keyless — data, charts, news and screeners all work. Add a model anytime from Settings..." then the cockpit: Chart on ^NSEI (populated), watchlist ^NSEI / RELIANCE.NS / TCS.NS / HDFCBANK.NS with prices, News populated, Portfolio empty state, Equity overview.
   Time from launch to populated cockpit (README promises ~30–90 s on first launch): ______ s.
3. Expected: the banner "Add a cloud provider key — or run a local model (Ollama) — to unlock the assistant..." with "Set up a provider →" is visible.
4. In the chat composer type "What is Kitex Garments trading at?" and send (default provider Ollama).
   Observed at source level (keyless:2): status line "Ollama (local) isn't ready: Ollama is not running. Start Ollama (open the app or run `ollama serve`), then try again."; the guided setup is not opened. Record what actually shows and whether any route to "Download Ollama — ollama.com/download" is offered from there.
5. Open Settings -> AI Providers: record whether an Ollama install link / guided local setup is reachable from Settings.
6. Open the Macro panel (not in the default layout): expected the FRED-key message naming ECB / IMF / World Bank as keyless alternatives, loaded once (no flicker).
