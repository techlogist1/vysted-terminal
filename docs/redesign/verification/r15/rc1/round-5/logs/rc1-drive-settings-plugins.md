# rc1-drive-settings-plugins — working log (gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, confirmed via
`git -C rc1-round-5-cand rev-parse HEAD`.

1. Read `PROMPT_surface_s2.md` OWNER-DRIVE settings-plugins scope, census
   `surface/settings-plugins/EVIDENCE.md`/`COVERAGE.json`, the register entries mapped from
   the 6 census raw findings (all 6 accounted for: 4 `fixed`, 2 `open`/low, none in the
   9-entry operator-adjudicated list or the three-failure list).
2. Read `surface/settings-plugins/rc1/rc1-redrive.md` and `rc1/round-4/*` for method/context
   only (earlier gate rounds — not this round's evidence, not cited as such).
3. Seeded my own data dir: `cp -R rc1-round-5-seed-data -> rc1-round-5-data-settings-plugins`
   (keyless `dev-keystore.json`). Booted own sidecar on `:52325` from
   `rc1-round-5-cand/sidecar` (source), `/health` confirmed 0.8.0, `openbb-mcp: available`.
   sleep-pipe pid 32747 (parent sh wrapper 32745, worker 32748).
4. Ran the fixed-row re-drive live against `:52325` (fake OpenRouter key validate, untrimmed
   OpenAI/Anthropic key, NewsAPI status no-key/fake-key, plugin disable/enable roundtrip,
   Unicode/traversal/long workspace names + list/delete cleanup) — raw files
   `01`-`14` under `surface/settings-plugins/rc1/round-5/`.
5. Code-read the export/import gating (`SettingsPanel.tsx`) and confirmed unchanged since the
   last redrive — `17-ui058-export-import-grep.txt`.
6. `git log`/`git diff 4c6dfe8c..9bc600ec` across every file this group depends on — found
   exactly one new commit in scope, `ef102fa5` (`src/store/modules.ts`, R15-CODE-PLATFORM-013
   follow-up: `setEnabledMap` now preserves live `plugin:*` flags on a bulk write). Ran the
   candidate's own tests live (`npx vitest run src/store/modules.test.ts
   src/store/workspace.test.ts src/components/SettingsPanel.test.tsx`) — 69/69 pass, including
   the new pinned regression test. `18`, `19`.
7. Confirmed R15-UI-081 still genuinely open (code-read, `openPanel` unchanged) and noticed
   R15-UI-089's own repro no longer reproduces (fixed as a side effect of the DATA-094/UI-033
   commit already in the tree) — not filed as a finding since nothing is broken, flagged for
   the register owner in the drive writeup instead.
8. Verified `R15CANARY` never appears in the sidecar log (`grep -c` → 0).
9. Stopped own sidecar: `kill 32745` (sh wrapper; its sleep child 32747 and the uvicorn worker
   32748 exit with it). Shared `:52152/53/54` never touched.

No lock needed (no Ollama/hosted-model calls in this drive — every re-verification was a
direct HTTP call to my own sidecar, a code-read, or a run of the candidate's own committed
test suite). No spend.
