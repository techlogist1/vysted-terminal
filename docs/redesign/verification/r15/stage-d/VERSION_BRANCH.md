# Version branch — worktree-agent-r15-version-0.9.0-rc1

Re-cut 07:47 IST 26 Sep from the rc1 gate-certified sha. Supersedes
`origin/worktree-agent-r15-version-0.9.0` (`517da226` + `c1e9164c` on `3d64ca17`), which stays
on origin untouched for reference.

Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (rc1 gate-certified sha)
Pushed: `origin/worktree-agent-r15-version-0.9.0-rc1` @ `1dfda1f3` (`git ls-remote` confirms).
Not merged (the lead merges after the `r15-rc1` tag). Worktree:
`<session scratchpad>/version-0.9.0-rc1`.

| Commit | Subject | Touches |
|---|---|---|
| `3e2a7092` | chore(release): bump version to 0.9.0 | cherry-pick of `517da226`, clean, same patch-id (`d3683da5`); 8 files, 8+/8- |
| `1dfda1f3` | docs: the single CLAUDE.md commit for the 0.9.0 release (R15) | `CLAUDE.md` only; 117+/66- vs base, 395 lines |

`git log --oneline 4c6dfe8c..HEAD` shows exactly these two commits.

## Commit 1: version sites (0.8.0 -> 0.9.0)

Verified at `1dfda1f3`:

- package.json:3 `"version": "0.9.0"`
- src-tauri/Cargo.toml:3 `version = "0.9.0"`
- src-tauri/Cargo.lock:5486-5487 `vysted-terminal` / `0.9.0` (carried by the cherry-pick; no
  `cargo update` needed)
- src-tauri/tauri.conf.json:4 `"version": "0.9.0"` (only that string touched)
- sidecar/app.py:329 `FastAPI(..., version="0.9.0", ...)` (`/health` derives from it)
- src/lib/plugin-bootstrap.ts:38 `HOST_VERSION = "0.9.0"`
- src/store/marketplace.test.ts:46 fixture `hostVersion: "0.9.0"` (its comment says it matches
  HOST_VERSION)
- README.md:53 status line ("version strings sit at `0.9.0` pending the launch tag")

Stale-string grep (`git grep -F 0.8.0`, excluding CHANGELOG, docs, node_modules/target/dist):
no remaining app-version site. Left alone, with reasons:

- plugins/{yfinance,vysted-news,vysted-lenses}/manifest.json:6 `requiredHostVersion "0.8.0"`:
  a floor; 0.9.0 satisfies it
- package.json:77 prettier-plugin-tailwindcss 0.8.0: a dependency version
- src-tauri/Cargo.lock `0.8.0` rows: third-party crates (bit-set, bit-vec, ctor, libspa,
  libspa-sys, pipewire, pipewire-sys)
- sidecar/tests/test_data_cache.py, test_schema_version.py: build-transition fixtures
- src/lib/plugin-runtime.test.ts, plugin-agents.test.ts, MarketplacePanel.test.tsx,
  SettingsPanel.test.tsx (mocked diagnostics), workspace.test.ts:1574 ("v0.8.0 rows"):
  arbitrary or historical fixtures
- src/lib/plugin-runtime.ts:133: doc-comment range example
- README.md:15,66 `docs/screenshots/v0.8.0/...`: real paths
- BLOCKERS.md headings, docs/ (CURRENT_STATE baseline, archive, research, redesign reports,
  verification evidence), CHANGELOG: historical. The files naming 0.8.0 that are new since the
  old base are all Stage D evidence (THIRD_PARTY_NOTICES drafts, bundle-rehearsal logs), none
  of which names the app version as current.

## Commit 2: the single CLAUDE.md commit

Built as: `git show c1e9164c -- CLAUDE.md | git apply` (clean; `CLAUDE.md` is byte-identical at
`3d64ca17` and `4c6dfe8c`, blob `4823d012`, so the result hashed equal to
`c1e9164c:CLAUDE.md`), then `patch -p1 < CLAUDE_MD_ADDENDUM.draft.diff` (clean, 7 hunks, no
rejects). Message = the `c1e9164c` message plus one line naming the folded-in addendum.

From `c1e9164c` (unchanged; itemised in the old notes): the Vite stack line, the relicense line,
the D81 trading-removal edits, the §6.5 agent-write line, `CATALOG_ROWS`, the shared-index rule,
`wait_for_port_with_retries`, the OpenAI 400-traps gotcha (the held hunk), the
`ADAPTER_OPTION_KEYS` allowlist, the keyless local-lane known limitation, the
`deserializeWorkspace` slice order, the dev-keystore keychain rule, the version-sites rule, the
R13 smoke-test line.

From the audit addendum (`CLAUDE_MD_AUDIT.md`):

- Stack: JetBrains Mono self-hosted via `@fontsource/jetbrains-mono` (b.2)
- Model assignment: the Haiku bullet replaced by "never Haiku, never the fast tier" (d)
- Copilot: `transform.code` node (12 built-in node types), `save_workflow` MCP-only, the four
  control keys popped by `agent_runtime`, the composer depth slider (b.8.4-b.8.7)
- Frontend: Vite watcher ignores, the tauri-plugin-mcp HMR wedge, WKWebView stale JS with the
  `com.vysted.terminal` cache paths, the `layout-templates.ts` registered-id rule (b.7, b.8.1-b.8.3)
- Visual verification: owner name `Vysted Terminal`, the dead `/tmp/rigcap.py` pointer dropped
  (f, R15-DOCS-026)

Coherence read end to end: no duplicated bullet (the OpenAI 400-traps gotcha appears once), no
contradiction (the control-keys bullet is additive to the `ADAPTER_OPTION_KEYS` one; the
wait-for-port budget matches `MCP_PORT_WAIT_SECS=45`). Every file the new bullets cite exists
at `4c6dfe8c` (spot-checked: page.tsx `initDevMcpBridge`, `_RUNTIME_ONLY` `save_workflow`,
`--font-jetbrains-mono`, `graphify-out` ignore, the `12` node log line, `BANNED` in
r15-fanout.js, `screener-panel`, `_NO_TOOL_CUE` still in planner.py).

Prettier: `CLAUDE.md` is not in `.prettierignore`. The repo's prettier 3.8.3 with the repo
config flagged two continuation lines from the addendum (the Vite-watcher and WKWebView
bullets); fixed to prettier's own output (the two lines lose their two-space indent, like the
existing `brief-blocks.tsx` continuation line) and re-checked clean. No other change.

## Containment check (held 3 Sep hunk)

`git -C <repo> diff -- CLAUDE.md` in the main worktree is 9 `+` lines, 0 `-` lines (the OpenAI
chat-completions 400-traps gotcha). Each `+` line was matched as a whole line in the branch
`CLAUDE.md` (`grep -xF`), before and after the prettier fix: **9/9 present, missing lines: none**
(branch `CLAUDE.md:202-210`).

## Not re-run on this branch (off-lane for the re-cut)

pnpm install/typecheck/lint/format:check, vitest, cargo fmt/check, ruff and pytest were run on
the old branch's commit-1 tree (the old notes, `<session scratchpad>/version-0.9.0-VERSION_BRANCH.md`)
and were not re-run here. Commit 1 is the same patch (same patch-id) on a newer base; the
gate's own runs cover `4c6dfe8c`. A read-only `git merge-tree --write-tree` of this branch into
`004-r4-experience-rebuild` @ `3dfcc9aa` is clean.

## Merge recipe (lead, after the `r15-rc1` tag)

The branch carries the held hunk, so the main worktree's uncommitted `CLAUDE.md` must go first
or the merge refuses to overwrite it:

```sh
git -C <repo> restore CLAUDE.md
# only if r15-rc1 is NOT 4c6dfe8c (a gate fix-round head), move the two commits first:
#   git -C <worktree> rebase --onto r15-rc1 4c6dfe8c worktree-agent-r15-version-0.9.0-rc1
#   a rebase rewrites both shas: pushing it is a force (the lead's call) or a new branch name;
#   update DECISIONS §5.4 to the new CLAUDE.md sha
git -C <repo> merge --no-ff worktree-agent-r15-version-0.9.0-rc1
```

After the merge: `git -C <repo> diff -- CLAUDE.md` should be empty and `git log -1 --format=%h
-- CLAUDE.md` should print `1dfda1f3` (or its rebased sha). The single CLAUDE.md commit reverts as
one commit (`git revert 1dfda1f3`, or its rebased sha).
