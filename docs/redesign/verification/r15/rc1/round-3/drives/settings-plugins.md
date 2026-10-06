# settings-plugins — owner-drive, RC1 gate round 3

Label `rc1-drive-settings-plugins`. Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own
sidecar `127.0.0.1:52325` (source: `rc1-round-3-cand/sidecar`, data:
`rc1-round-3-data-settings-plugins/` cp'd from `rc1-round-3-seed-data`, keyless). Shared stack
`:52152-54` untouched (read-only, not needed this drive — every write went to `:52325`).
Evidence under `docs/redesign/verification/r15/surface/settings-plugins/rc1/round-3/`.

## Method

`git diff --stat 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2..01d6920a` scoped to this group's
files (`SettingsPanel.tsx`, `KeyEntryDialog.tsx`, `PluginManagerPanel.tsx`, `marketplace.ts`,
`workspace.ts` (store), `modules.ts`, `llm.py`, `news.py`, `workspace_store.py`, `openai.py`,
`news_provider.py`) shows exactly 2 files touched since the round-2 candidate:
`src/lib/host-actions.ts` (watchlist-region logic, R15-DATA-002 — portfolio-notes/composer-chat
scope, not this group) and `src/store/modules.ts` (`setEnabledMap` now keeps live `plugin:*`
flags — R15-CODE-PLATFORM-013's follow-up, in this group's scope). Every other file this group
owns is byte-identical to the round-2 candidate, where a Sonnet agent already live-verified 6
fixed rows (`surface/settings-plugins/rc1/rc1-redrive.md`). This round: re-ran the 6 previously-
fixed rows live against my own fresh sidecar (not just cited), read and functionally exercised
the one new in-scope change, re-confirmed the two still-open rows are genuinely unchanged
(code-diff proof, not just assertion), and read the panel/store code first per the prompt.

## Scored table — census/round-2 → round 3

| Row (register id) | Round-2 rc1 | Round-3 rc1 | Evidence |
|---|---|---|---|
| Fake OpenRouter key certifies `ok:true` (R15-RESEARCH-010) | ok (fixed) | **ok** | `01-fixed-rows-recheck.txt`: `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` |
| Untrimmed key → misleading "Connection error" (R15-UI-057) | ok (fixed) | **ok** | `01-fixed-rows-recheck.txt`: trailing-space OpenAI key → `{"ok":false,"detail":"OpenAI rejected this key."}` (a real rejection, not a transport error — trim landed) |
| Export/import (R15-UI-058) | ok (fixed) | **ok** | `rc1-round-3-vitest-settings-plugins.log`: `SettingsPanel.test.tsx` 157/157 pass across the 5-file scoped suite, incl. the export/import cases; no code change since round 2 |
| NewsAPI key never validated (R15-DATA-094 / R15-UI-033) | ok (fixed) | **ok** | `01-fixed-rows-recheck.txt`: `{"newsapi":"unauthorized"}` fake key, `{"newsapi":"absent"}` keyless |
| Plugin toggle lies (R15-CODE-PLATFORM-012) | ok (fixed) | **ok** | `02-workspace-and-plugin-recheck.txt`: disable → `enabled:false` persisted + read back via `GET /plugins`; restored |
| Layout name 400-reason-dropped / >210-char 500 (R15-UI-082) | ok, redesigned; residual noted | **ok, residual confirmed live** | `02-workspace-and-plugin-recheck.txt`: 234-char ASCII → `400 "...too long to save."`; 33-char Devanagari (36 encoded-bytes/glyph) → `400 "...too long..."` (the register's documented residual — byte-expansion trips the length cap early on Unicode); a short 10-char Devanagari name → `200 saved`, cleaned up |
| Disabled module panel still opens / dead "AI Assistant" switch (R15-UI-081) | still open | **still open, unchanged** | code-read: `src/store/workspace.ts` `openPanel` (`:109-`) still only calls `findPanel`, no `enabled` read; file untouched in the 4c6dfe8c..01d6920a diff — not a stale claim, a proven no-change |
| **NEW this round**: `setEnabledMap` preserves live `plugin:*` flags on workspace-load/import (R15-CODE-PLATFORM-013 follow-up) | n/a (not yet fixed at 4c6dfe8c) | **ok, new fix confirmed** | `rc1-round-3-vitest-settings-plugins.log`: `store/modules.test.ts` "setEnabledMap keeps the live plugin:\* flags and ignores incoming ones", plus `workspace.test.ts` ×2 and `plugin-runtime.test.ts` pinned regressions — 157/157 pass |

## Deltas from round 2

None. No round-2-`ok` row regressed. The one new in-scope code change
(`ef102fa5 fix(modules): setEnabledMap keeps lifecycle-owned plugin:* flags`) is confirmed
working via the repo's own committed regression tests (already pinned by the fix's author, not
written by this drive) and holds live.

## New defects

None found in this group this round.

## Not re-driven live this round (unchanged code, no regression risk, cited instead)

`settings-research` Tier-B fake-key trace (deep_research.py unchanged since round 2 — the root
validate-key fix it depends on was re-verified live above), `settings-keybindings` conflict
detection, `settings-region` copy mismatch, `settings-advanced-integrations` dead CTA,
`settings-searxng` non-ready states — none of these files appear in the 4c6dfe8c..01d6920a
diff; re-running an LLM/API drive against unchanged code would not have found anything new and
would have spent local-model-lane time other roles needed.

## Rig

Sidecar boot log: `rc1-round-3-sidecar-settings-plugins.log` (scratch). Sleep-wrapper pid 87059
(bash -c "sleep 86400 | ..."), worker pid 87062. Stopped via `kill 87059` at the end of this
drive. Data dir `rc1-round-3-data-settings-plugins/` is my own copy of the round-3 seed data;
shared `:52152-54` never written to.
