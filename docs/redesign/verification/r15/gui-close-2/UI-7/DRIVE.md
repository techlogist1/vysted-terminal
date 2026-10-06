# UI-7 — gui-close-2 drive at 1fddb2b (stranger keyless first run, FRESH PROFILE)

- item: UI-7 (final-pass/NEEDS_GUI.md "final-adv-maintainer — UI-7")
- sha: 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056
- app: `<scratchpad>/bundle-rc2b/src-tauri/target/debug/bundle/macos/Vysted Terminal.app` (debug build)
- home: `<scratchpad>/gui-close-home-UI-7`; data dir `<home>/Library/Application Support/com.vysted.terminal`, created empty holding only `dev-keystore.json` = `{"secrets": {}, "migrated": true}` (FRESH PROFILE, no seed)
- real data dir mtime before: 1790978102
- Ollama-down half: driven by env, for this app only. The onboarding status probe is a hard-coded constant (`sidecar/routers/system.py:28 _OLLAMA_URL = "http://127.0.0.1:11434"`, `/system/ollama/status`), but the lane's readiness probe (`POST /llm/keys/validate` -> `OllamaProvider.validate_key` -> `ollama.AsyncClient(host=self._base_url)` with `base_url=None`, `sidecar/services/llm/ollama.py:141-144`) and the chat lane fall to the ollama SDK 0.6.2 default `_parse_host(host or os.getenv('OLLAMA_HOST'))` (`_client.py:113`). The app is launched with `OLLAMA_HOST=http://127.0.0.1:9` (nothing listens on :9), so its chat lane, readiness chip and empty state see Ollama unreachable while the operator's daemon (answered `/api/tags` 200 at 12:31:51Z under the lock) is never stopped. Consequence: the onboarding Local step, which reads the hard-coded status route, still reports the real daemon as running.
- Plan: the sentinel expires 12:57:00Z and idle reaches 900 s about 12:42:35Z, so only ONE guarded batch fits. Coordinates come from the same debug build's 1280x832 window in gui-close-2/R15-LIFECYCLE-008 (terms accept (768,598), onboarding Skip (502,722); "Set up local AI" measured from its 1fddb2b-02-after-terms.png at point (758,658)). The local step's Back button position is unknown, so the batch reaches it by keyboard (Tab = first tabbable in the dialog is StepHeader's Back, then Return).
- launch: 2026-10-04T12:42:38Z, pid 22266, `HOME=<home> OLLAMA_HOST=http://127.0.0.1:9 nohup .../Contents/MacOS/vysted-terminal` (stdout raw/app-stdout.log, pid raw/app.pid)
- isolation proof: children 22284 openbb-mcp :63543, 22285 sec-edgar-mcp :63544, 22286 vysted-sidecar `--port 63542 --data-dir <home>/Library/Application Support/com.vysted.terminal --cache-dir <same>`; `logs/vysted.log` created under the isolated data dir; `ps -E` of the child carries `OLLAMA_HOST=http://127.0.0.1:9` (inherited). HTTP reads went to :63542 only.
- bounds: `{"owner": "Vysted Terminal", "id": 7758, "bounds": [116.0, 43.0, 1280.0, 832.0]}` -> 1280x832 pt; captures 2560x1664 (point = pixel/2).
- boot: sec-edgar-mcp did not bind in 45 s x 2 (12:44:08Z, /sec routes 501): the known open R15-LEAD-124, not re-filed. The main sidecar bound only at 12:44:28Z (~110 s after launch). `/health` 0.9.0 (raw/health.json). `POST /llm/keys/validate {"provider":"ollama","model":"qwen2.5:7b"}` on :63542 -> `{"ok":false,"reason":"unreachable","detail":"Ollama is not running. Start Ollama ..."}` (raw/validate-ollama.json): the env override took effect.

## Checks

### Passive capture (presence 12:44:23Z idle=1008.5, sentinel 12:57:00Z, front Zed, no Vysted GUI app but mine) -> raw/rig-01.log EXIT=0
- `1fddb2b-01-terms-boot.png` (opened): "Welcome to Vysted / Please review the terms before you start" with the four acknowledgements (no brokerage connection, data may be delayed, AI can be wrong, PolyForm Strict / commercial) and "I understand — continue"; behind it the chip reads CONNECTING…, "OLLAMA (LOCAL) · NOT RUNNING — SET UP IN SETTINGS", the banner "Add a cloud provider key — or run a local model (Ollama) … Set up a provider →", Chat 1 empty state with Try-this prompts.

### batch-01 raw/batch-01.json (presence 12:44:53Z idle=1038.4, sentinel 12:57:00Z, front Vysted Terminal (mine), only my Vysted app) -> raw/rig-02.log, 21/21 steps ok, EXIT=0
Steps: terms (768,598); capture; "Set up local AI" (758,658); wait 6; capture; Tab; capture; Return; capture; Skip (502,722); capture; composer model chip (234,800); capture; Escape; capture.
- `1fddb2b-02-onboarding-welcome.png` (opened): terms gone; onboarding WELCOME "An agent-native finance terminal", green "It already works — no key, no account", cards "Connect a model / Add a key →" and "Run it locally / Set up local AI →", "Skip — I'll explore first →". Header CONNECTED, Ollama NOT RUNNING.
- `1fddb2b-03-onboarding-local.png` (opened): "Run a local model": "Apple M1 Pro · 16 GB RAM · Apple Silicon", recommendation `qwen3:8b` "runs locally · ~7.8 GB" "fits with headroom (7.8 GiB of 10.6 GiB GPU budget) — enable locally.", button "✓ Use qwen3:8b". This step reads the hard-coded `/system/ollama/status` (log 12:44:57Z), so it saw the operator's real daemon as running with qwen3:8b installed while the header (env-routed readiness) says NOT RUNNING — see finding 2. "Use qwen3:8b" was deliberately not clicked (no Download/pull path touched).
- `1fddb2b-04-local-tab-focus.png` (opened): same step with the focus ring on the Back arrow (Tab landed on StepHeader's Back as planned).
- `1fddb2b-05-back-to-welcome.png` (opened): Return on Back -> WELCOME step again, identical layout.
- `1fddb2b-06-cockpit-composer.png` (opened): onboarding dismissed by Skip; cockpit: header CONNECTED | "OLLAMA (LOCAL) · NOT RUNNING — SET UP IN SETTINGS"; keyless CTA banner "Add a cloud provider key — or run a local model (Ollama) — to unlock the assistant, agents, and research tools … Set up a provider →"; Chat 1 empty state "Ask anything about what you're viewing", TRY THIS (Research $NVDA, Compare AAPL vs MSFT, Scan today's movers, Summarize my portfolio P&L), "Mode Agent · lens Vysted Copilot"; composer "Ask anything…" Normal + local-chip icon. No error text anywhere. Watchlist ^NSEI 22,421.95 / RELIANCE.NS 1,167.70 (EOD 2026-10-01), News (mint, NEGATIVE -0.34), empty Portfolio, Equity overview empty state.
- `1fddb2b-07-model-picker.png` (opened): picker open; PROVIDER list Anthropic, OpenAI, Google Gemini, Groq, **Ollama (local)** (highlighted = selected), DeepSeek, xAI, OpenRouter; MODEL llama3.1:8b, **qwen2.5:7b** (highlighted). The composer landed on the keyless local lane with no key.
- `1fddb2b-08-final.png` (opened): Escape closed the picker; same cockpit as 06.

## Results
- Terms + onboarding walked with no keys: shown (01 terms, 02 welcome, 03/04 local step, 05 back, 06 skipped). The Cloud ("Add a key") step and the Done step (reached only by "Use qwen3:8b") were not driven: one batch fitted the sentinel window, Use would have changed the lane away from the down-lane test, and the cloud step needs a key.
- Composer lands on the keyless Ollama lane: shown (07: Ollama (local) / qwen2.5:7b selected on a fresh profile with an empty keystore).
- Ollama unreachable -> keyless CTA, not an error: shown (06/08: the chat empty state stays the normal "Ask anything" + Try-this with no error; the CTA is the app banner directly above it, "… or run a local model (Ollama) … Set up a provider →", and the header chip "NOT RUNNING — SET UP IN SETTINGS"). At 1fddb2b the chat empty state itself has no keyless-CTA branch (ChatSidebar.tsx ~1690-1775 has none); the guided setup re-opens from a send (ChatSidebar.tsx:838-860: `model_not_pulled`/`not_configured` open onboarding, `unreachable` says "isn't ready: …"). A send was not driven.
- Dev keystore after: keys `['app-meta:first-launch-terms']`, migrated true (values not read out). No secret typed.

## Findings
1. medium (PLAUSIBLE) — keyless readiness chip/banner can stick on "NOT RUNNING" after a slow sidecar boot. In this run no frontend `POST /llm/keys/validate` reached the sidecar after it bound (the only one in vysted.log is my curl at 12:44:49Z, raw/vysted-log-excerpt.txt); the chip read NOT RUNNING already while CONNECTING (01). Here the lane really was down (env), but the same debug build showed "OLLAMA (LOCAL) · NOT RUNNING" with the real daemon up and no override in gui-close-2/R15-LIFECYCLE-008 01/02 and UPGRADE-080 01, where the sidecar also bound late behind sec-edgar's 90 s. `useKeylessReadiness` (provider-validation.ts) caches a failed probe for 30 s and re-probes on `sidecarStatus` change only if that cache has expired. Repro: launch the debug app cold with Ollama running (sec-edgar slow bind) -> header/banner say Ollama not running.
2. low — the onboarding Local step and the chat lane disagree on where Ollama is: `/system/ollama/status` hard-codes `http://127.0.0.1:11434` (system.py:28) and `/llm/models` is sent `base_url=http://127.0.0.1:11434` by the UI, while readiness/chat use `ollama.AsyncClient(host=None)` which honours `OLLAMA_HOST`. Repro: set OLLAMA_HOST to another host -> Local step offers "Use qwen3:8b" (03) while the header says NOT RUNNING (03/06).

## Quit
- 12:45:50Z `kill 22266`, then children 22284/22285/22286 by pid; `ps` shows none; ports 63542-63544 not listening.
- real data dir mtime after: 1790978102 (unchanged).

## Stops
- none.

## Verdict
**partial** — every driven part holds (terms, welcome, local step, back, skip; keyless lane selected; Ollama-down state shows the CTA banner, no error); not_driven: the Cloud step, the Done step, and a send on the down lane.
