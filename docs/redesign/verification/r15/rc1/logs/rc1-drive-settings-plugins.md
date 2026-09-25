# rc1-drive-settings-plugins — working log

- Read `PROMPT_surface_s2.md` OWNER-DRIVE section + settings-plugins group scope.
- Read census `surface/settings-plugins/EVIDENCE.md`, `COVERAGE.json`, `_TWIN_AGENTS.md` (agents Q+P,
  2026-09-23). 15 COVERAGE rows, statuses: ok x2, partial x7, broken x6.
- Cross-referenced `docs/redesign/verification/vysted-r15-register.json` for every
  `SURF-SETTINGS-PLUGINS-*` and `COD-plugins-*`/`COD-frontend-panels-shell-chrome-*` raw id this
  group's census cited: found which register entries are `fixed` (re-verify -> should be ok now) vs
  `open`/`blocked_tier4` (should still be broken/deferred, not a regression).
- Read panel + api code before driving: `src/components/SettingsPanel.tsx`, `KeyEntryDialog.tsx`,
  `PluginManagerPanel.tsx`, `src/modules/marketplace/MarketplacePanel.tsx`, `src/store/marketplace.ts`,
  `src/lib/plugin-bootstrap.ts`, `src/lib/plugin-agents.ts`, `src/store/workspace.ts`,
  `sidecar/routers/llm.py`, `sidecar/services/llm/openai.py`, `sidecar/routers/news.py`,
  `sidecar/routers/workspace.py`, `sidecar/services/workspace_store.py`.
- Copied `rc1-seed-data` -> `rc1-data-rc1-drive-settings-plugins`; booted own sidecar on `:52325`
  from `rc1-cand/sidecar` source (read-only), sleep pid 87924, worker pid 87927; `/health` ok.
- Drove: OpenRouter fake-key validate, NewsAPI key probe, plugin enable/disable toggle round-trip,
  workspace-name edge cases (234-char, `../evil`) against `:52325` (writes). Read-only context checks
  against `:52152` were unnecessary this round since all fixed claims were directly testable on my
  own sidecar.
- All 7 previously-broken/partial interactions with a `fixed` register entry now score `ok`, verified
  live or by direct code read of the cited fix. The one still-open row (Modules dead switch /
  disabled-module-still-opens, R15-UI-081) reconfirmed broken by code read — matches register, not a
  regression.
- No regressions, no new defects found for this group.
- Wrote `surface/settings-plugins/rc1/rc1-redrive.md` (never overwrote census files),
  `rc1/drives/settings-plugins.md`, `rc1/findings/rc1-drive-settings-plugins.json` (empty array).
- Stopped own sidecar (sleep pid 87924). Left shared `:52152` stack untouched.
