# batch-25/W1-data-002-code-platform-013

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-013 | Source read (`src/lib/workspace.ts` PERSISTED_SLICES `enabledModules` slice) + 5 committed pinned tests covering this exact drift class | `plugin:<id>` flags are never persisted into the workspace blob and restore keeps the LIVE plugin-runtime state, never the blob's; `workspace.test.ts` reproduces the register's own fresh case verbatim (an older blob with `plugin:vysted-news:false` restored after re-enabling it keeps it `true`); `store/workspace.test.ts`, `store/modules.test.ts` and `plugin-runtime.test.ts` cover `resetToDefaultLayout`, `setEnabledMap` and the never-persisted default respectively | ci_pinned (workspace.test.ts: "never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on (R15-CODE-PLATFORM-013)"; store/workspace.test.ts: "resetToDefaultLayout keeps lifecycle-owned plugin:* flags"; store/modules.test.ts: "setEnabledMap keeps the live plugin:* flags and ignores incoming ones"; plugin-runtime.test.ts: "PluginRuntime — the one never-persisted default") |

Note: batch-25's own certification ran a scratch, uncommitted `plat013.test.tsx` (never
committed, per the batch's teardown convention) — that exact file is gone, but its assertions
are now covered (and exceeded, 5 files vs 1) by tests actually committed to the repo, so this
is stronger evidence than a re-run of the original scratch script would have been.

COVERAGE: 1/1 ids raw; no raw: none.
