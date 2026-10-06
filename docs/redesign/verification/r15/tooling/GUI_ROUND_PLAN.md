# R15 GUI round: workflow plan

Script: `docs/redesign/verification/r15/tooling/gui-round.js`. It is the rc1 gate's GUI phase pulled out into its own workflow. rc1 gate round 1 skipped that phase because the computer-use grant did not cover the built app. This round never uses computer-use, tauri-mcp, playwright or chrome. Every input and every capture goes through the repo's own rig, `scripts/rig/rig.py`, run from Bash.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/gui-round.js", args: {sha: "<candidate sha on 004>"}})
Workflow({scriptPath: "…/gui-round.js", args: {sha: "<sha>", dry_run: true}})           # preflight read-only + the plan
Workflow({scriptPath: "…/gui-round.js", args: {sha: "<sha>", ids: ["R15-UI-022"]}})      # a subset
```

Args:

- `sha`: required, 7-40 hex characters. Preflight resolves it and requires it to be `004-r4-experience-rebuild` or an ancestor of it.
- `ids`: optional list of register ids. The default is every entry whose status is `needs_gui` at launch. Requested ids that are not `needs_gui` are reported and dropped.
- `gui_wait_min`: default 60, in the range (0, 240]. How long a driver waits for presence before it stops with `operator_present`.
- `max_entries`: default 16, an integer 1..16.
- `dry_run`: runs the preflight read-only (no worktree, no build, no seed) and returns `planned`.
- `note`: a lead note appended to every prompt.
- `scratch`: the scratch root.

Bad args are refused before any agent is spawned. The script returns `{status: 'refused', reason}`.

Return: `{status: done | dry_run | blocked | refused | adjudicator_died, sha, driven[ids], certified[ids], not_certified[{id, reason}], skipped[{id, reason}], commit}`.

**Before launching, the operator has to arm the away sentinel.** Arm it for the whole round, which runs about 15-30 min per entry:

```
date -u -v+6H +%Y-%m-%dT%H:%M:%S+00:00 > ~/.vysted-rig-away
```

No agent writes, extends or deletes this file. When it is absent or expired, the rig refuses every action. The first driver then waits `gui_wait_min` and stops the lane with `operator_present`.

## What must be running

| Need | Who provides it |
| --- | --- |
| Packaged debug app at the sha (`tauri://` origin, bundled sidecars) | Preflight: `git worktree add --detach $SCRATCH/gui-<sha7> <sha>`, then `pnpm install --frozen-lockfile`, `node scripts/ensure-all-sidecars.mjs` and `pnpm tauri build --debug --bundles app`, all detached and polled. A restart reuses an existing build at the same sha. |
| Dev-origin binary (loads `http://localhost:5173`), for the dev half of CODE-AGENT-001 only | Preflight, non-blocking: `CARGO_TARGET_DIR=<wt>/src-tauri/target-devurl cargo build`. The CODE-AGENT-001 driver starts vite on :5173 from the gui worktree (its own pid, killed after), and only if :5173 is free. A port held by any other process means that half is `not_driven`; the driver never kills a foreign process. |
| Keyless isolated seed `$SCRATCH/gui-round-seed` | Preflight: `sqlite3 .backup` of each db in `$SCRATCH/vysted-iso/data` except `audit_log.db`, plus `workspaces/`, `notes/` and `searxng/settings.yml`, and a fresh `dev-keystore.json` of `{"secrets": {}, "migrated": true}` (chmod 600, ISOLATION_MAP §2.4). Each driver copies it to its own `$SCRATCH/gui-round-home-<id>`. |
| The rig | Already in the repo. The interpreter is `sidecar/.venv/bin/python3`, the only one on this Mac with PyObjC. It needs no bridge, port or server. Posting clicks and keys needs Accessibility, and `capture` needs Screen Recording, on the process tree that runs it. A missing grant shows up as a black capture or an osascript error, and the entry becomes `blocked_env`. |
| Shared stack :52152-54 | **Not needed.** The packaged app spawns its own three sidecars. Preflight only reads the stack's data dir to build the seed, and never starts, stops or writes through the stack. |
| Ollama llama3.1:8b | Only when the seed has no settled research brief for UI-083, and then under the LOCAL-MODEL LOCK. |

## Lanes and agents

| # | Phase | Agents (model / effort) | What it does |
| - | ----- | ----------------------- | ------------ |
| 1 | Preflight | 1 Sonnet medium | Handles git, the build, the seed, one presence reading (idle, sentinel, frontmost, running Vysted apps, :5173 holder) and the entry list, read directly from the register JSON. `blocked` stops the round with nothing else spawned. |
| 2 | Drive | 1 Opus high per entry, **strictly sequential**, one GUI lane | Launches the built binary with `HOME=<isolated home>` and proves isolation. Reproduces the entry's original repro through `rig.py batch` with registered captures and writes `DRIVE.md` as it goes. Returns `holds / regressed / blocked_env / operator_present`. R15-DOCS-024 gets `blocked_env` without a driver (details below). The first `operator_present` stops the lane: every later entry is recorded as not attempted, and they all stay `needs_gui`. |
| 3 | Verify | 1 fresh Opus high per driven entry (`holds` or `regressed`), at most 3 at once | Reads only the entry, its `DRIVE.md`, its captures and raw files, `CAPTURES.jsonl`, `presence.log` and the code at the sha. Rules `certified / not_certified / still_needs_gui` and writes `VERIFY.md`. |
| 4 | Adjudicate | 1 Sonnet high | Applies the script-computed rulings to the register JSON by path and regenerates the md view with `scripts/r15/render_register_md.py`. Writes `VERDICTS.json` and `VERDICTS.md`, then commits by path. It does not push. It is skipped when nothing was driven. |

Every call goes through a global limiter of 6 and the `run` idiom from rc1-gate.js: `once` plus one same-tier `-retry`, never a third try. COMMON carries the stall rule (no tool call over ~120 s, detach and poll), the LOCAL-MODEL LOCK, the rule to stage and commit by path only in the main worktree, and the isolation and secrets rules. No agent reads the brief or `r15/local/`.

## Presence rules (enforced by the rig, restated in every driver prompt)

1. **Sentinel.** `~/.vysted-rig-away` must hold a future ISO time. It is re-read at every rig step. Drivers read it with the rig's own `real_away()` and never write it.
2. **Idle.** Idle must be at least 900 s at the first step of every guarded rig process. The floor is 300, and this round never lowers the bar. The rig's own events reset the idle clock, so **one sub-check is one `rig.py batch` file** (clicks, keys, types, waits and capture steps together). A driver first takes a passive capture to compute window-relative point coordinates, where point = pixel / 2. Before any follow-up batch it waits for idle ≥ 900 again, using separate `sleep 100` calls.
3. **Mid-batch human detector, foreground gate, surprise detector.** These are the rig's gates 3-5. Exit 3 means refused; the driver waits, up to `gui_wait_min` for the entry, and then records `operator_present`. Exit 4 is a hard stop: the capture is deleted, the line goes to `RIG_ABORTS.log`, and the driver quits its app by pid. A human input or focus change counts as `operator_present`. A dialog raised by the app itself counts as `blocked_env`.
4. **One Vysted app.** The rig matches any window whose owner contains "vysted". If the operator's `/Applications/Vysted.app`, or any Vysted app the driver did not launch, is running, the driver does not act and waits. It never quits that app.
5. **Launch gating.** The driver launches only after the same three checks pass (sentinel, idle ≥ 900, no foreign Vysted app), because a launched app takes the foreground. Each check is appended to `r15/gui-round/presence.log`.
6. **Only the Vysted window receives input.** `type` and `key` carry only test text: a URL, a label, a note word or a prompt.
7. **His data is untouchable.** The driver records the mtime of the real `~/Library/Application Support/com.vysted.terminal` before launch and after quit, using stat only. A change, or any keychain or SecurityAgent dialog, is a hard stop and makes the entry `blocked_env`.

A presence problem or an environment wall always leads to a skip, never a failure.

## Evidence layout

```
docs/redesign/verification/r15/gui-round/
  PREFLIGHT.md  presence.log  logs/            preflight facts, every presence reading, build logs
  <id>/DRIVE.md                                 written as it goes: header, per check (batch, presence line, what each capture shows, raw files), mtimes, stops, verdict
  <id>/<sha7>-NN-<slug>.png                     rig captures only, never overwritten, each registered in r15/CAPTURES.jsonl
  <id>/raw/                                     app stdout, log greps, ls of exports, curl/ps output, exported CSV/PDF/PNG (an exported PNG is registered with register_capture.py --tool vysted-export)
  <id>/VERIFY.md                                the fresh verifier's per-part ruling
  VERDICTS.json  VERDICTS.md                    the adjudicator's record
```

A capture counts as evidence only if it is registered. The verifier hashes each cited PNG and finds that hash in `CAPTURES.jsonl`, with tool `scripts/rig/rig.py capture` (or `vysted-export`) and a window owner containing "vysted". It also requires a `presence.log` line before the capture. An unregistered image is ignored, and it would also fail the pre-push guard, which is why the adjudicator commits `CAPTURES.jsonl` together with the captures.

## How verdicts reach the register

The script works out the rulings itself. The adjudicator applies them mechanically in one read-modify-write of `vysted-r15-register.json`, right after re-reading the file. `git diff` must show only these entries changed.

| Drive | Verifier | Register |
| --- | --- | --- |
| holds / regressed | certified | `fixed`; `closure_evidence` = `gui-round@<sha7> r15/gui-round/<id>/DRIVE.md`; note += `gui-round@<sha7>: certified, evidence …/DRIVE.md, verifier …/VERIFY.md` |
| holds / regressed | not_certified | `open`; note += the verifier's reason |
| holds / regressed | still_needs_gui | stays `needs_gui`; note += what remains (e.g. the Windows half) |
| holds / regressed | verifier died | stays `needs_gui`; note says so |
| blocked_env / operator_present | (none run) | stays `needs_gui`; note += the reason |

Next, the adjudicator runs `python3 scripts/r15/render_register_md.py > docs/redesign/verification/vysted-r15-register.md` and writes `VERDICTS.json`, shaped `{sha, certified, needs_gui, not_certified[{id, reason}], concur_not_defect: [], refused_not_defect: []}`, plus `VERDICTS.md`.

Finally it commits with `git add` followed by `git -c core.hooksPath=/dev/null commit -q -- <paths>`, where the paths are `r15/gui-round/`, the register JSON and md, `r15/CAPTURES.jsonl`, and `r15/RIG_ABORTS.log` if it exists. It does not push.

`render_register_md.py` is the lead's `disp/render.py`, promoted with a usage docstring and a repo-relative default path. It reproduced the committed md byte for byte, checked with `cmp` three ways: the default path, an explicit JSON argument, and a different working directory.

## Entries (the 11 `needs_gui` at 734d40f)

| id | sev | Came from | What the drive must show | Proof |
| --- | --- | --- | --- | --- |
| R15-CODE-AGENT-001 | high | batch-5 VERDICTS.md | Packaged app: every panel loads, and the app log has no 403 for the webview origin. Dev half (5173) only if the port is free. | Per-panel captures; `raw/403-grep.txt`. The Windows half is out of reach, so expect `still_needs_gui`. |
| R15-LIFECYCLE-001 | high | batch-8 VERDICTS.md | (1) The window paints and responds while both MCP children are still binding. (2) `/health` answers before the binds finish. (3) With the bundled sidecar renamed, in a copy of the .app, the red chip and "could not start" message appear at once. (4) Killing the sidecar child brings up "Sidecar error" and "The data engine stopped". | Captures at about 2/6/12 s; `raw/boot-timeline.txt` from a 0.5 s poller. The boot is warm, since a reboot is out of reach, and the verifier rules whether that carries the claim. |
| R15-LIFECYCLE-008 | high | batch-5 VERDICTS.md | `logs/vysted.log` gets timestamped `[sidecar]`/`[vysted]`/MCP lines and rotates: it is pre-filled to just under the 2 MiB `MAX_LOG_BYTES`, so boot forces `vysted.log.1`. Settings "Copy diagnostics" shows a preview, then copies. | `raw/ls-logs.txt`, `raw/log-head.txt`, the preview capture, `raw/clipboard.txt` (keyless). |
| R15-UI-009 | high | batch-4 VERDICTS.md | Export CSV in Watchlist, Portfolio and Screener each shows the saved path, and each file exists under `exports/csv/`. | A capture per panel; `ls` and header rows in raw/. |
| R15-UI-022 | medium | batch-7 VERDICTS.md | Drawings made with native clicks: (1) they land at the clicked y mid-candle; (2) a drawing placed right of the last bar is visible; (3) Text asks for a label and shows `gui-check`; (4) a locked drawing's delete is disabled and the drawing survives. | Captures, with the click points and drawn y recorded. |
| R15-UI-025 | medium | batch-4 VERDICTS.md | Notes: select a word, click Link, and an inline URL popover appears; applying it sets the link mark. | Popover and applied captures; `raw/note-after.txt`. |
| R15-UI-050 | medium | batch-9 VERDICTS.md | The Notes "/" menu: no two-line row clips or overlaps the next one, including with an active row highlighted. | Two full captures. |
| R15-UI-083 | medium | batch-9 VERDICTS.md | A settled brief saves as .md, PDF and PNG with the paths reported, and the PNG/PDF show the settled brief, not a frame from mid-animation. | Toast captures; the exported files in raw/ (the PNG registered). |
| R15-UI-084 | medium | batch-10 VERDICTS.md | The window as large as the display allows. Double-clicking the dock handle makes the dock span the whole cockpit with the panel host hidden; double-clicking again restores the prior width. | Three captures with measured widths; the size from `bounds`. |
| R15-DOCS-024 | low | lows PARTITION.md | Needs a real Claude Desktop session. | **No driver.** Automatic `blocked_env`: the rig acts only on the Vysted window. It stays `needs_gui` for the operator. |
| R15-LIFECYCLE-040 | low | lows PARTITION.md | Packaged macOS cold boot: the app spawns the MCP children, and `/openbb-mcp/status` and `/sec/status` report bound. | `raw/ps-tree.txt`, `raw/mcp-status.txt`, a cockpit capture. `DECISIONS.md` is not edited (lead-owned). The Windows half is out of reach, so expect `still_needs_gui`. |

## Stubbed dry run (verification of the script)

The harness is `$SCRATCH/gui-round-dry.mjs` (untracked). It strips `meta`, wraps the body in `new Function("args","agent","parallel","pipeline","phase","log","budget","workflow", …)`, and runs it against stub `agent/parallel/pipeline/phase/log`. The stub preflight reads the real register. A syntax check of the same wrapping passes. Output summary at HEAD 734d40f:

```
A. {sha, dry_run:true}  phases: Preflight | 1 call gui-preflight[sonnet/medium]
   log: the round would drive 10 entries sequentially, then one verifier each; no GUI input, no register edit
   return: status dry_run, planned 11, commit null
B. {sha, ids:['R15-UI-022']}  phases: Preflight > Drive > Verify > Adjudicate | 4 calls
   gui-preflight[sonnet/medium], gui-drive-R15-UI-022[opus/high], gui-verify-R15-UI-022[opus/high], gui-adjudicate[sonnet/high]
   drive: 1 driver, max concurrent 1 | verify: 1 for 1 driven | return: done, certified [R15-UI-022]
C. {sha} (all 11; stub UI-050 regressed, LIFECYCLE-008 blocked_env)  phases: all four | 21 calls
   drive: 10 drivers, max concurrent 1 (sequential=true), register order; R15-DOCS-024 blocked_env without a driver
   verify: 9 verifiers for 9 driven (one per driven entry = true)
   return: certified 6, not_certified [R15-UI-050], skipped 4 (CODE-AGENT-001 + LIFECYCLE-040 still_needs_gui, LIFECYCLE-008 + DOCS-024 blocked_env)
D. {sha} (stub operator_present at R15-UI-025)  13 calls: 6 drivers (max concurrent 1), then the lane stops
   log: GUI lane stopped at R15-UI-025: operator present; the rest stay needs_gui
   verify: 5 for 5 driven | return: certified 5, skipped 6 (UI-025 + 4 not attempted + DOCS-024)
E. {}                          0 calls: refused — args.sha is required (the candidate commit, hex)
F. {sha:'xyz123g'}             0 calls: refused — args.sha must be 7-40 hex characters, got "xyz123g"
G. {sha, ids:'R15-UI-022'}     0 calls: refused — args.ids must be a list of register ids like R15-UI-022
H. {sha, max_entries:40}       0 calls: refused — args.max_entries must be an integer 1..16, got 40
```

## Risks

- **The sentinel is not armed now** (`~/.vysted-rig-away` is absent). Until the operator arms it, the round can only build and then record `operator_present`. That is the intended behaviour.
- **Screen Recording and Accessibility grants for the rig's process tree have not been measured** (README re-measure checklist). If either is missing, every entry becomes `blocked_env`, not a failure.
- **Idle resets.** Every follow-up batch costs another 15 min of idle, so 10 drivers at 1-3 batches each take about 3-6 hours. Arm the sentinel for that long, or pass `ids` in chunks.
- **LIFECYCLE-001 wants a cold boot after a reboot,** which cannot be done here. The warm launch is recorded as warm, and the verifier may return `still_needs_gui`.
- **The Windows halves** (CODE-AGENT-001, LIFECYCLE-040) and **Claude Desktop** (DOCS-024) cannot be driven on this Mac, so those entries stay `needs_gui` unless the verifier judges the driven part to carry the claim.
- **UI-083 needs a settled brief.** If the seed has none, the local 8b model has to produce one, which can end in `blocked_env`.
- **"Copy diagnostics" overwrites the operator's clipboard** once, with keyless isolated content.
- **Rig input sequences are not yet measured**: typing into the WKWebView, `cmd+k`, and the 2x capture scale are all on the README checklist. Drivers use toolbar clicks where `cmd+k` might fail.
