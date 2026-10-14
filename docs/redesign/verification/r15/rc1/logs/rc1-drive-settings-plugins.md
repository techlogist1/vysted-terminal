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

## Gate-round-2 re-drive (26 Sep, same session — continued from the 25-Sep pass above)

- Found `rc1-cand` at scratch is now sha `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (the
  gate-round-2 candidate per this run's LEAD NOTE), NOT `4097dac4` that the 25-Sep pass
  evidenced — candidate moved between attempts of this same run. Confirmed via
  `git log --oneline 4097dac4..4c6dfe8c` (297 commits, mostly R15 verification docs) and
  `git diff --stat` scoped to this group's files: only `SettingsPanel.tsx` changed (+12/-0,
  commit `5109567e`, R15-CODE-PLATFORM-013 fix).
- Register check: R15-CODE-PLATFORM-013 status is `fixed` but carries a `note` recording an
  rc1-refutation-audit finding it `partial` (Settings toggle bypassed the marketplace
  lifecycle owner for bridged plugin modules). Commit `5109567e` in the new range fixes
  exactly that gap.
- Verified via `vitest run src/components/SettingsPanel.test.tsx` against `rc1-cand`
  (detached run, polled via Monitor — 10.69s wall, well under the 120s single-call cap): 52/52
  pass, including the pinned regression test for this exact fix.
- Re-booted own sidecar on `:52325` from `rc1-cand/sidecar` (source, read-only) against the
  existing `rc1-data-rc1-drive-settings-plugins` data dir (reused — no sidecar/server file in
  this group's scope changed between candidates, so the existing keyless data dir is still
  valid); re-ran the 3 live round-trips from the 25-Sep pass (key validate, NewsAPI probe,
  plugin enable/disable) — all still `ok`, no regression.
- Re-confirmed by code read that R15-UI-081 (`workspace.ts` `openPanel` never reads the
  `enabled` map) is untouched by this range and still genuinely open — a distinct defect from
  PLATFORM-013, not fixed by it.
- No new defects. Updated `surface/settings-plugins/rc1/rc1-redrive.md` and
  `rc1/drives/settings-plugins.md` with the gate-round-2 delta; findings file stays `[]`.
- Stopped own sidecar (sleep-pipe pid 70950). Shared `:52152` untouched throughout.
