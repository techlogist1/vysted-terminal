# settings-plugins — owner-drive evidence (R15 Stage B item 4, surf-S2C, agent Q)

Worker: claude-opus-5-5[1m] ("agent Q" in `_TWIN_AGENTS.md`). Date 2026-09-23 09:00-09:20 IST.
Headless only: HTTP against the sidecar + the REAL panels rendered in jsdom against it.

## Rig

- Sidecar `127.0.0.1:52222`, source run, data dir `$SCRATCH/vysted-iso/seat-settings-plugins/data`
  (`cp -R $SCRATCH/vysted-iso/data`, keyless `dev-keystore.json` = `{"secrets": {}, "migrated": true}`),
  MCP pair `:53221/:53222`, `/health` -> `openbb-mcp: available`, version 0.8.0.
- Twin launch: a second agent booted the identical stack one second after Q (see `_TWIN_AGENTS.md`).
  The :52222 worker that won the bind (31126) is the other agent's process; Q reused it (COMMON.md:
  reuse, never restart) and does not stop it. Split: the other agent owns portfolio-notes, Q owns
  settings-plugins.
- `harness/sp.py`: one JSON line per request -> `http-log.jsonl` (tags A-G below).
- `harness/*.s2cq.test.tsx` + `harness/vitest.s2c.config.mjs` (scratch config; nothing under `src/`):
  `@tauri-apps/api/core.invoke` is shimmed (`harness/mocks.ts`) to answer `get_sidecar_port` with
  52222 and to keep an IN-MEMORY keychain, so `SettingsPanel`, `KeyEntryDialog`, `PluginManagerPanel`,
  `MarketplacePanel` and `bootstrapPlugins()` run their real code and real `fetch` against :52222.
  Every request body with `api_key` is redacted in the replay. All keys used are fake canaries
  (`sk-...R15CANARY...`); no keystore was read, no real key left the machine.
- Seeded evidence: no seat transcript and nothing in `seat-breaker/http-log.jsonl` touches Settings
  or plugins. Heavy prior CODE coverage exists (COD-frontend-panels-shell-chrome-2/3/4/7/8,
  COD-plugins-1..14, COD-llm-adapters-2-4/-9, COD-workspace-layout-1/5/12, COD-frontend-stores-4/11);
  this drive reproduces those live where cheap and reports only NEW defects as raw findings.

## 1. Settings shell + nav (`10-settings-panel-replay.json` S1)

All five sections and the five Advanced subsections render populated on mount; 8 GETs, all 200:
`/health, /llm/providers, /custom-agents, /agents, /workspace, /llm/models?provider=ollama,
/system/hardware, /search/searxng/status` (the SearXNG status takes 3.4 s - it shells out to docker).
Nav: 5 chips at the full-label step, every target id resolves. Scroll behaviour = NEEDS-GUI.

## 2. AI Providers (S1-S3, http-log A02-A03, B01-B12)

| Drive | Result | Score |
|---|---|---|
| 8 provider rows, no key | 'No key yet' x7, Ollama 'No key required (local)'; Defaults: 13 agents, 8 providers, live Ollama models | ok |
| Model catalog keyless (A03) | openai/anthropic/gemini/groq/deepseek -> `source:fallback`, honest note 'Live catalog unavailable — showing known models'; openrouter -> live 300+ models; ollama live 3 | ok |
| Fake key, each provider (B01) | openai/anthropic/groq/deepseek -> `unauthorized or no key supplied`; gemini/xai -> `transport error: 400 ... {'error': ...}` raw dict; **openrouter -> `ok:true`** | broken (COD-llm-adapters-2-4 live) |
| Fake OpenRouter key through the real dialog (S2) | validate 200 ok:true -> keychain write -> row 'Key configured' -> Tier B 'OpenRouter key configured — research bills to it.' | **broken -> SURF-SETTINGS-PLUGINS-1** |
| Key + trailing space / newline (S3, B08-B11) | OpenAI dialog: 'transport error: Connection error.'; Anthropic + '\n': 'unauthorized...'; direct: anthropic/groq/deepseek + space -> Connection error | **broken -> SURF-SETTINGS-PLUGINS-2** |
| base_url dead port (B05/B06) | 'transport error: Connection error.' — no URL/key echo | ok |
| canary echo | `R15CANARY` never appears in any response body or in the sidecar log (grep count 0) | ok |

## 3. Research tiers + SearXNG (S1, S2, C01-C05, G01)

- Tier A card: chip **Ready**, 'Running at http://127.0.0.1:8888 — research searches route through it
  automatically.' + Stop. (SURF-RESEARCH-BRIEFS-4 already shows 'ready' while engines are CAPTCHA-blocked.)
  Other SearXNG states NOT TESTED: inducing them means tearing down / setting up the SHARED
  `vysted-searxng` container (forbidden; the failure-inducer item owns Docker-absent).
- Tier B, no key: 'Needs your OpenRouter API key — research stays on the local tier until one is added.' ok.
- Tier B with the fake key (G01, `vy.py invoke copilot ... --provider ollama --model llama3.1:8b --tier
  tier_b --header X-Vysted-Openrouter-Key=<fake>`): llama DID call `research` (depth quick); the stream
  carried two `research_step` frames, both `status: ok`, then `done`. No error step, no error frame
  (`deep_research.py:723-724` returns `ok:false` without a `_step`). The model then wrote "market
  capitalization of over $200 billion USD" with "Brief sources: Wikipedia, Forbes, Bloomberg" —
  nothing was fetched. -> SURF-SETTINGS-PLUGINS-1.
- Hardware card: Apple M1 Pro · 16 GiB · 10.6 GiB GPU budget · 6P/8 · macOS 26.3; 3 Ollama models scored
  green; frontier deep-research candidates scored 'too large — remote'. ok.

## 4. Region, Keybindings, Modules (11-modules-region-replay.json, 12-keybindings-record-replay.json)

- Region: select IN -> US round-trips into the store (ok); the row still says 'Defaults to United
  States.' while the live default is IN (COD-frontend-panels-shell-chrome-4, reproduced).
- Keybindings: 11 actions / 6 categories render; Record shows 'Press keys… (Esc to cancel)' and stores
  the combo. Recording **Ctrl+K** on 'Toggle agent panel' (non-mac path): `matchesEvent` is true for
  BOTH palette.open (`mod+k`) and agent.toggle (`ctrl+k`), yet `conflicts()` = [] and no banner —
  COD-frontend-panels-shell-chrome-3 reproduced on the Windows/Linux path as well as macOS.
- Modules: 22 rows, Platform locked 'always on'. Notes OFF -> `notes.open` leaves `enabledCommands()`
  (ok). 'AI Assistant  0 panels · 0 commands' has a live switch that nothing reads ->
  SURF-SETTINGS-PLUGINS-5.

## 5. Advanced > Layouts — finding-6 row RESOLVED (http-log D01-D13, S6)

Content (read in full, `SettingsPanel.tsx:1587-1708`): a 'Save current layout as…' form + 'Reset to
default', the list of saved NAMED workspaces (reserved `__*` names filtered) with Load / X-delete, and
an autosave-slot footnote. It does **not** show or edit the four arrange templates.
- API: save 'R15 Swing' 200, list/get/delete ok, delete-missing 404. `__mine` saves 200 and is then
  hidden from the list (COD-workspace-layout-12). `../evil`, `a/b`, `मेरा लेआउट`, `'   '` -> 400 with
  a clear rule the frontend discards; 230-300-char names -> **500** `OSError [Errno 63] File name too
  long` on the `.tmp` path -> SURF-SETTINGS-PLUGINS-6.
- UI Save = NEEDS-GUI: `serializeWorkspace` needs the mounted dockview (jsdom renders 'The panel
  layout is not ready yet.').

## 6. Export / Import (S4, S5)

- Export bundle = `{version:1, keybindingOverrides, settings:{defaultAgentId, region,
  deepResearchBackend}}`. With Tier B + a Deep model + a custom SearXNG URL + Default provider OpenAI
  set, none of them is in it; `deepResearchBackend` has no Settings control. The file is written via
  `<a download>` (WLD-T-2, NEEDS-GUI in the webview).
- Import: non-JSON -> 'Could not read that file — expected a Vysted export.' (ok); `{}` and another
  app's JSON -> green 'Imported settings.' with every store unchanged; numeric bindings / region 'XX'
  are dropped by the store guards (ok). -> SURF-SETTINGS-PLUGINS-3.

## 7. About + provider-health — finding-6 row RESOLVED

- About: 'Vysted v0.8.0' = `/health` 0.8.0 = package.json / Cargo.toml / tauri.conf.json / app.py /
  HOST_VERSION. ok.
- `provider-health-breaker`: **no frontend surface** — `grep -rn 'provider-health\|providerHealth' src`
  returns no non-test hit. GET `/system/provider-health` -> yahoo `open:true`, opens_total 3,
  throttles_total 126 (this IP's normal state). trip/reset POSTs not called.

## 8. Plugin Manager + Marketplace (20-plugins-marketplace-replay.json, F01/F02)

- Boot: `bootstrapPlugins()` against :52222 -> 5 active (yfinance, openbb-mcp, lenses, news, example),
  7 broker adapters 'discovered' (out of scope, not analysed). Header '5 active of 12 loaded · 6 data
  sources · 1 agents · 0 nodes'. Every config fetched twice (COD-plugins-11 reproduced: 2 GETs per id).
- Plugin Manager toggle OFF on 'Vysted Example Plugin': runtime -> `stopped`, **zero requests**,
  persisted row stays `enabled:true`, module stays registered; re-bootstrap -> `active` again
  (COD-plugins-1 reproduced live).
- Marketplace: Data providers 4, Agents 1 (+ Brokers 7 out of scope). disable / enable / remove /
  install on vysted-example each persist and read back from `GET /plugins` (ok).
- Configure Market News with a fake NewsAPI key: saved + `configured:true`, no probe; `/news` with the
  key returns the same 20 RSS items as keyless, 1.60 s vs 0.94 s, only a sidecar log line records the
  401 -> SURF-SETTINGS-PLUGINS-4.

## Raw findings (census/raw/surf-settings-plugins.json)

| id | sev | one line |
|---|---|---|
| SURF-SETTINGS-PLUGINS-1 | high | fake OpenRouter key certified; Tier-B 401 invisible in trace/stream; local model fabricated sources |
| SURF-SETTINGS-PLUGINS-2 | medium | untrimmed key -> 'transport error: Connection error.' (onboarding trims, Settings does not) |
| SURF-SETTINGS-PLUGINS-3 | medium | export omits the visible research/provider/module preferences; import 'succeeds' on any JSON |
| SURF-SETTINGS-PLUGINS-4 | medium | NewsAPI key never validated; rejected key silently leaves the feed RSS-only |
| SURF-SETTINGS-PLUGINS-5 | low | 'AI Assistant' module switch is a dead control |
| SURF-SETTINGS-PLUGINS-6 | low | layout-name 400 reason dropped; >~210-char name 500s |

Live reproductions of existing findings (not re-filed): COD-llm-adapters-2-4, COD-plugins-1,
COD-plugins-11, COD-frontend-panels-shell-chrome-3/-4, COD-workspace-layout-12.

## Merge from agent P (09:30), additive only; Q's sections above are unchanged

P drove the same surface on its own worker (:52222) before it saw Q's split. The files are
`10-settings-plugins-replay.json` (S0-S4, P1), `11-key-validate-http.jsonl`, `12-region-resolve-probe.jsonl`,
`13-openpanel-ids-disabled-module.json`, `14-provider-health.json`, `15-research-about-gets.txt` and
`16-provider-health-frontend-grep.txt`. The harness is `harness/settings.s2c.test.tsx` + `harness/extra.s2c.test.tsx`
(in-memory keychain shim, real panels, real fetch). P's runs confirm Q's rows and add the following:

- **New raw finding SURF-SETTINGS-PLUGINS-7 (low).** Disabling a module does not stop its panel
  opening. With Portfolio off, `openPanel('portfolio')` still calls dockview `addPanel` (component
  `portfolio-panel`, present in PanelHost's all-modules map). Every host action that opens a panel on
  apply therefore reopens a "disabled" module. Control: `openPanel('marketplace')` adds the panel and
  `openPanel('marketplace-panel')` adds nothing (the dead Integrations and Plugin Manager CTA id).
- Import (Q's -3, evidence appended): 6 files. `{}`, a package.json, `{"settings":{"region":"XX"}}` and
  an unknown-action bindings file all say 'Imported settings.'; only malformed JSON errors. Code-read:
  `settings.ts:162-176` merges over the seed, so an imported block without a valid region or engine
  resets them to the defaults.
- Region: a live `/resolve` probe proves the Region switch reroutes symbol resolution today: 'infosys'
  resolves to INFY (US ADR) versus INFY (NSE), 'hdfc' to HDB versus HDFCBANK. The section copy says
  number formatting only (known COD-frontend-panels-shell-chrome finding).
- Key dialog: a canary OpenRouter key is saved and the row shows 'Key configured' (Q's -1). Gemini ignores
  a supplied `base_url` (the dead-host probe still reached Google). The canary never appears in the
  sidecar log.
- Layouts 'Layout operation failed.' in P's S3 is a harness artifact (fake dockview api). It is not a
  product defect; the save/load leg is NEEDS-GUI.
- `/search/tiers/status` answers 404 on this sidecar. SettingsPanel never calls it: the skeleton
  row's note names it, but the panel reads `/search/searxng/status` only.
