# drive:settings-plugins — final pass (head d38b5d1a2487bd52fe8a7e741a3a5266e3206611)

Method: `tooling/PROMPT_surface_s2.md` OWNER-DRIVE settings-plugins. Seeded from the census
(`surface/settings-plugins/EVIDENCE.md`, `COVERAGE.json`) and the rc1 drive (`rc1/drives/settings-plugins.md`).
Own sidecar :52845 from the final-cand source on a copy of `final-seed-data` (keyless), MCP pair
:52801/:52802 shared. Writes (plugin config, workspace saves, key validation) went only to :52845; the
shared :52800 was used for one read-only GET. Headless routes: direct HTTP (`final/harness/probe.py`, one
JSON line per request) and a scratch jsdom vitest harness (config root = final-cand, jsdom url
http://localhost:5173) that renders the real `SettingsPanel`, `KeyEntryDialog`, `PluginManagerPanel` and
`MarketplacePanel` against :52845, with an in-memory keychain shim. Every key is a fake `R15CANARYfinal`
canary: 0 occurrences in any response body and 0 in the sidecar log.

Evidence: `surface/settings-plugins/final/` (http `01-*`, `02-*`, `run1-*` = first identical pass, `03`
SearXNG, `04` provider-health grep, `05-harness-*` replays and run logs, `06` LEAD-068, `COVERAGE.json`, `harness/`).

## Scored table

| Interaction | Census | rc1 | Final | Register | Evidence |
|---|---|---|---|---|---|
| Settings mount: all sections populated | ok | — | ok | — | `05-harness-settings-replay.json` S1: 8 GETs 200, ten subsections render |
| Section nav chips | partial | — | ok (render); scroll NEEDS-GUI | — | S1.nav: 5 chips |
| AI Providers: fake key per provider (7) | broken | ok | ok | R15-RESEARCH-010 | `02-http-B.jsonl`: all `ok:false, reason:invalid` |
| Fake OpenRouter key through the dialog | broken | ok | ok | R15-RESEARCH-010 | S2: "OpenRouter rejected this key.", keychain writes 0, row stays "No key yet" |
| Whitespace-padded keys (OpenAI space, Anthropic newline, Groq tabs) | broken | ok | ok | R15-UI-057 | S3 + B: "rejected this key", never "Connection error" |
| Empty or whitespace-only key | — | — | ok | — | B: `not_configured` "No API key is set for OpenAI." |
| Validate transport failure copy | — | — | ok | R15-CODE-AGENT-019 | B: dead base_url -> humanized "Could not reach OpenAI ...", no SDK repr |
| Ollama readiness (pulled / missing model) | — | — | ok | — | B: `ok:true`; `model_not_pulled` with the model named |
| Research tiers copy (keyless, after a rejected key) | partial | — | ok | — | S1/S2 Research section |
| SearXNG card: degraded engines | partial | — | ok | R15-RESEARCH-028 | S1: "Degraded — engines blocked (brave ...; duckduckgo: CAPTCHA ...)" |
| SearXNG card: Docker installed, daemon stopped | not tested | — | **broken** | new (medium) | `03-searxng-daemon-down.txt` |
| Region select + copy | partial | — | ok | — | `05-harness-modules-replay.json`: IN->US round-trips; copy names resolver/calendar/providers; "Defaults to India." |
| Keybindings: Ctrl+K on Toggle agent panel | broken | — | ok | — | S9: conflict banner "Ctrl+K is bound to Open command palette and Toggle agent panel." |
| Command palette subsection hint | — | — | ok | — | S1: "How Ctrl+K ranks ..." (live chord) |
| Integrations: Open Marketplace | broken | — | ok | — | modules replay: `openPanel("marketplace")` adds 1 panel, old `marketplace-panel` adds 0 |
| Layouts: HTTP leg (names, 200-byte rule, reserved, delete) | partial | ok | ok | R15-UI-082 | `02-http-F.jsonl`: 200 bytes saved, 201 bytes / 67 Devanagari chars -> 400 with the byte reason; `__mine` hidden; missing -> 404 |
| Layouts: UI save/load | NEEDS-GUI | — | NEEDS-GUI | — | S6: jsdom "The panel layout is not ready yet." |
| Modules: AI Assistant switch | partial | still broken | ok | R15-UI-081 | modules replay: "AI Assistant enabled [disabled]" (always on) |
| Modules: disabled module still opens | partial | still broken | ok | R15-UI-081 | modules replay: Portfolio off -> `openPanel` adds 0; back on -> 1 |
| Modules: Notes off drops its command | ok | — | ok | — | `notes.open` leaves `enabledCommands()` |
| Export bundle | broken | ok | ok | R15-UI-058 | S5: version 2 with searchSettings, defaultProviderId/Model, enabledModules, providerOrder |
| Import: junk / `{}` / foreign JSON | broken | ok | ok | R15-UI-058 | S4: "Could not read that file — expected a Vysted export.", stores unchanged |
| Import: `{settings:{fontSize:14}}` | — | — | partial | R15-LEAD-089 (open, attached) | S4: "Imported settings." with no state change |
| About version | ok | — | ok | — | S1 "Vysted v0.9.0" = `/health` 0.9.0 |
| Provider health | ok | — | ok | R15-LIFECYCLE-033 | `02-http-C.jsonl`: GET 200; trip/reset 404 without `VYSTED_RIG_HOOKS`; frontend reader = StatusChrome fallthroughs (`04-*.txt`) |
| Plugin Manager populated | ok | — | ok | — | P1: "5 active of 5 loaded · 6 data sources · 1 agents · 0 nodes" |
| Plugin Manager toggle persistence | broken | ok | ok | R15-CODE-PLATFORM-012 | P2: POST `enabled:false`, persisted false, simulated relaunch -> `discovered` |
| Marketplace disable/enable/remove/install | ok | — | ok | — | P3: each persists and reads back from `GET /plugins` |
| Marketplace: fake NewsAPI key | broken | ok | ok | R15-DATA-094 / R15-UI-089 | P3: probe -> rejected, keychain empty, grants `[]`; `/news` header `rss=ok;newsapi=unauthorized` |
| Plugin config API: unknown id / malformed body | — | — | ok | — | D: 404 named, 422 bool parse |
| Settings privacy copy | — | — | open | R15-LEAD-068 (open, attached) | `06-lead068-privacy-copy.txt`: SettingsPanel.tsx:122 unchanged |

## Census and rc1 to final deltas

- Census broken or partial now ok: 12 interactions (provider keys, padded keys, keybinding conflict, Integrations CTA, Region copy, Modules dead switch and disabled-module open, export, import junk, Plugin Manager toggle, NewsAPI probe, layouts HTTP). Each matches a `fixed` register entry, or a fix in the group's code delta (4c6dfe8c..d38b5d1a: AGENT-019, LIFECYCLE-033, CROSS-PLATFORM-011, PLATFORM-049, FRONTEND-030, the openPanel id and contributesNothing changes).
- rc1 "still broken" now ok: R15-UI-081, both halves.
- No census-ok or rc1-ok row regressed.
- New: one medium. The SearXNG card renders the sidecar's `not_installed_docker` state (CLI found, daemon stopped) as "Docker not found / install Docker first". The status payload's `docker.daemon_running` and its "start Docker/OrbStack" detail never reach the UI. The census had not tested this state.
- Attached, not new: R15-LEAD-089 (import toast with nothing applied) and R15-LEAD-068 (privacy copy). Both are still open.
- `tradesa-v2` is still a persisted `enabled:true` row in `GET /plugins` (seed data). It is not loaded: Plugin Manager shows 5 of 5 and there is no broker section. Out of scope, as the census and rc1 found.
- Docker came up during the drive. At 16:45 IST the status was daemon_running:false; by 16:50 it was degraded/running with CAPTCHA-blocked engines. Both states are recorded.
