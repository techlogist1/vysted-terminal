export const meta = {
  name: 'r15-gui-round',
  description: 'R15 standalone GUI round for the register entries with status needs_gui: preflight builds the packaged debug app at the candidate and seeds a keyless isolated home, one presence-safe GUI lane drives each entry in turn through scripts/rig/rig.py (registered captures only), a fresh Opus verifier rules on each driven entry, and an adjudicator applies the verdicts to the register and commits by path',
  whenToUse: 'While the operator is away and has armed ~/.vysted-rig-away; args {sha, ids, gui_wait_min, max_entries, dry_run, note}',
  phases: [
    { title: 'Preflight', detail: 'git, build the packaged app at the sha, isolated seed, presence read, needs_gui list' },
    { title: 'Drive', detail: 'one GUI lane, entries sequential, one Opus driver per entry through the rig' },
    { title: 'Verify', detail: 'one fresh Opus verifier per driven entry' },
    { title: 'Adjudicate', detail: 'register + md view + VERDICTS, commit by path, no push' },
  ],
}

const A = args || {}
const REPO = '/Users/lokavyasingh/Documents/dev/vysted-terminal'
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const EV = REPO + '/docs/redesign/verification/r15/gui-round'
const EVR = 'docs/redesign/verification/r15/gui-round'
const REG = 'docs/redesign/verification/vysted-r15-register.json'
const REGMD = 'docs/redesign/verification/vysted-r15-register.md'
const LEADNOTE = A.note ? '\n\nLEAD NOTE FOR THIS RUN (adds to the rules above, never relaxes presence, isolation or secrets): ' + String(A.note) : ''

// ---------------------------------------------------------------- args
const refuse = reason => {
  log('gui-round refused: ' + reason)
  return { status: 'refused', reason, driven: [], certified: [], not_certified: [], skipped: [], commit: null }
}
const SHA_IN = A.sha == null ? '' : String(A.sha).trim()
if (!SHA_IN) return refuse('args.sha is required (the candidate commit, hex)')
if (!/^[0-9a-f]{7,40}$/i.test(SHA_IN)) return refuse('args.sha must be 7-40 hex characters, got ' + JSON.stringify(A.sha))
if (A.ids != null && (!Array.isArray(A.ids) || !A.ids.every(x => typeof x === 'string' && /^R15-[A-Z0-9-]+$/.test(x)))) return refuse('args.ids must be a list of register ids like R15-UI-022, got ' + JSON.stringify(A.ids))
const GUI_WAIT_MIN = A.gui_wait_min == null ? 60 : +A.gui_wait_min
if (!(GUI_WAIT_MIN > 0 && GUI_WAIT_MIN <= 240)) return refuse('args.gui_wait_min must be a number of minutes in (0, 240], got ' + JSON.stringify(A.gui_wait_min))
const MAX_ENTRIES = A.max_entries == null ? 16 : +A.max_entries
if (!Number.isInteger(MAX_ENTRIES) || MAX_ENTRIES < 1 || MAX_ENTRIES > 16) return refuse('args.max_entries must be an integer 1..16, got ' + JSON.stringify(A.max_entries))
const DRY = A.dry_run === true || A.dry_run === 'true'
const IDS = A.ids ? [...new Set(A.ids)] : null

// ---------------------------------------------------------------- pacing + fallback (as rc1-gate.js)
function limiter(n) {
  let active = 0
  const q = []
  const pump = () => {
    while (active < n && q.length) {
      const t = q.shift()
      active++
      Promise.resolve().then(t.fn).then(t.res, t.rej).finally(() => { active--; pump() })
    }
  }
  return fn => new Promise((res, rej) => { q.push({ fn, res, rej }); pump() })
}
const GLOBAL = limiter(6)
const once = (prompt, opts) => GLOBAL(() => agent(prompt, opts)).catch(e => { log('agent ' + opts.label + ' failed: ' + e); return null })
// Routing 5: a wave that dies or starves gets ONE same-tier retry, never a third try.
const run = (prompt, opts) => once(prompt, opts).then(r => r ? r : (log('agent ' + opts.label + ' on ' + opts.model + ' returned nothing (wave died or starved) - one same-tier retry'), once(prompt, { ...opts, label: opts.label + '-retry' })))

// ---------------------------------------------------------------- rig + presence
const PY = REPO + '/sidecar/.venv/bin/python3' // the only interpreter here with PyObjC (scripts/rig/README.md)
const RIG = PY + ' ' + REPO + '/scripts/rig/rig.py'
const AWAY_CMD = PY + ` -c "import sys; sys.path.insert(0, '${REPO}/scripts/rig'); import rig; print(rig.real_away())"`
const APPS_CMD = "lsappinfo list | grep -i -B1 -A3 vysted"
const FRONT_CMD = 'lsappinfo info -only name $(lsappinfo front)'
const REAL_DATA = '~/Library/Application Support/com.vysted.terminal'

const COMMON = `Repo: ${REPO}, integration branch 004-r4-experience-rebuild, MAIN worktree: other agents share its index, so stage and commit BY PATH ONLY ('git add <paths>' then 'git -c core.hooksPath=/dev/null commit -q -m "<msg>" -- <paths>'); never 'git add -A', never 'git commit -a', never push. The operator is away; never ask, decide and record. Before any pnpm/node/cargo command: export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH. Never print or copy a secret; never read docs/redesign/verification/R15_BRIEF*.md or docs/redesign/verification/r15/local/. No GUI, except the Drive role under its own rules. Do not edit CLAUDE.md, the run-state, docs/redesign/verification/r15/spend-ledger.jsonl, src-tauri/tauri.conf.json, .github/, LICENSE*, types/plugin.ts, or any product source. Only the Adjudicate role edits ${REG}. Trading is out of the product (D81) — never re-add any of it. Never speculate about code you have not opened. HIS DATA IS UNTOUCHABLE: never read, write or launch against the real-home ${REAL_DATA}, ~/Library/Caches/vysted-terminal or ~/Library/WebKit/vysted-terminal (stat for mtime only), never add, read or delete an OS keychain item, never launch, quit or touch /Applications/Vysted.app or any Vysted process you did not start. Never write, extend or delete ~/.vysted-rig-away: only the operator arms it. HARNESS STALL RULE (a 3-minute no-progress watchdog kills the agent and restarts it from scratch): NO single tool call may run longer than ~120 s. Anything longer (pnpm install, cargo, sidecar builds, pnpm tauri build, app boots, presence waits) MUST be started detached — 'nohup <cmd> > <log> 2>&1 &' or the Bash tool's run_in_background — and polled with SEPARATE short calls ('sleep 60; tail -n 5 <log>'); never an 'until … sleep' loop inside one call. Waits are separate 'sleep 100' calls. Keep emitting a tool call at least every 2 minutes. If you find files from a previous attempt of your own role (a restart), read them and CONTINUE from them. LOCAL-MODEL LOCK: the local model (Ollama) is one lane shared by every agent on this machine. Wrap every call that reaches it (an app agent run on an Ollama model, any request to :11434) in a lock: in separate short calls, try 'mkdir /tmp/vysted-r15-ollama.lock 2>/dev/null' every 5 s (at most ~100 s of retries per call) for up to 15 min; a lock dir older than 20 min is stale ('find /tmp/vysted-r15-ollama.lock -maxdepth 0 -mmin +20' prints it) and may be removed with rmdir; release it with rmdir on success AND failure. A call that could not get the lock in 15 min is 'lock_timeout' (a harness cause), never a product failure. Your final text IS the return value: return only the structured object.${LEADNOTE}`
const STALL = 'STALL RULE, this role: every install, build, app boot and wait below starts detached (nohup ... > <log> 2>&1 &) or is a separate short call; no single tool call over ~120 s.'

const PRESENCE = `PRESENCE (the rig is the only input path; its gates are the law, scripts/rig/README.md). Rig: '${RIG} <subcommand>' from Bash, NEVER an MCP tool (no computer-use, no tauri-mcp, no playwright, no chrome). Subcommands: idle, bounds (unguarded); capture OUT.png, click X Y [--double], type "text", key "combo", resize W H, batch FILE.json (guarded: exit 3 = refused for presence, exit 4 = aborted on a surprise and any capture deleted, exit 2 = bad step, nothing posted). X/Y are window-relative POINTS: captures are 2x, so point = pixel / 2 (confirm with 'bounds' vs the PNG width). Never lower --min-idle and never set VYSTED_RIG_MIN_IDLE below 900. Every guarded rig process demands idle >= 900 s at its first step and the rig's own clicks and keystrokes reset the idle clock, so a separate rig call right after an input is refused: put each sub-check's whole sequence (clicks, keys, types, {"cmd":"wait","seconds":N} steps and capture steps) in ONE 'batch' file, look at a passive capture first to compute coordinates, and before any follow-up batch wait for idle >= 900 again with separate 'sleep 100' calls. The rig's mid-batch detector aborts the instant a human touches the machine.
Before launching an app and before every batch, read and append one line (UTC time from 'date -u +%FT%TZ', idle, sentinel, frontmost, vysted apps) to ${EV}/presence.log: idle = '${RIG} idle'; sentinel = ${AWAY_CMD} (prints the expiry, or None when absent/expired); frontmost = ${FRONT_CMD}; vysted apps = ${APPS_CMD}. You may act only when idle >= 900 AND the sentinel prints a time AND no Vysted GUI app runs except the one YOU launched (the rig matches any window whose owner contains 'vysted', so a second Vysted app — his /Applications/Vysted.app or anyone else's — makes every rig action unsafe: never quit it, wait). Not satisfied → re-check with separate 'sleep 100' calls for up to ${GUI_WAIT_MIN} min in total for this entry, then stop: quit your app by its pid, verdict operator_present. An exit 4 surprise (a foreign window, the frontmost app changed, a human input) = hard stop: quit your app by its pid, copy the RIG_ABORTS.log line into DRIVE.md; a human-input or focus change is operator_present, a foreign dialog of the app's own making (SecurityAgent, crash reporter) is blocked_env. Presence never produces a failed verdict.
TYPING: 'type' and 'key' go to the frontmost app, which the rig has proven is Vysted; never type anything but test text (a URL, a label, a note word, a prompt): no secrets, no key, no shell command.`

const ISOLATE = (home, sha) => `ISOLATED HOME ${home}. Build it fresh (rm -rf only this path): mkdir -p "${home}/Library/Application Support" and cp -R ${SCRATCH}/gui-round-seed "${home}/Library/Application Support/com.vysted.terminal"; confirm its dev-keystore.json reads exactly {"secrets": {}, "migrated": true} (r15/stage0/ISOLATION_MAP.md §2.4: without it the app sweeps his real keychain). Before launch: 'stat -f %m' the real ${REAL_DATA} (mtime only) and record it. Launch the BUILT binary of ${sha}, never /Applications/Vysted.app, never with 'open': HOME="${home}" nohup "<app_path>/Contents/MacOS/vysted-terminal" > <entry dir>/raw/app-stdout.log 2>&1 & and record its pid (§1.2: HOME moves the data dir, caches and WebKit store). Prove isolation before any input: the app's data dir and logs/vysted.log are under ${home} and its sidecar was spawned with --data-dir under ${home} (ps -o args of its child pids). Find the app's own sidecar port from its child pids ('pgrep -P <pid>', 'lsof -nP -iTCP -sTCP:LISTEN -a -p <child>'); HTTP reads and seeding writes go to THAT port only, never :52152-54 or anyone else's. Populate before proof shots if the seed lacks it (via your app's sidecar HTTP, not GUI input): watchlist AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT; portfolio >= 1 position with a cost basis; a note. Quit: kill <your app pid>, then any of its children still alive by their pids only; confirm with ps. After quitting, stat the real ${REAL_DATA} again: a changed mtime or any keychain/SecurityAgent dialog = record it as a hard stop in DRIVE.md and return blocked_env.`

// What each entry's drive must show, from its register note and the stage-c VERDICTS.md that sent it to needs_gui.
const CHECKS = {
  'R15-CODE-AGENT-001': 'Packaged app (tauri:// origin): every panel of the seeded layout loads with data (capture), then open the panels not in the layout through the toolbar "Open panel" button (cmd+k may not work) in one batch with a capture per panel; then grep <home>/.../logs/vysted.log and raw/app-stdout.log for " 403" and "Origin" into raw/403-grep.txt (must be zero hits for the webview origin). Dev half (http://localhost:5173 origin): only when preflight built dev_binary and :5173 is free — start vite from the gui worktree on :5173 (own pid, killed after), run the dev binary with the same isolated HOME, same panel check and 403 grep; if :5173 is held by another process, record the dev half as not_driven. The Windows half is out of reach on this Mac: record it as not_driven.',
  'R15-LIFECYCLE-001': `Four checks. Before launch start a detached stdlib python poller that every 0.5 s appends (monotonic t, the app pid children, their LISTEN ports, GET /health, /openbb-mcp/status and /sec/status on the main sidecar port once known) to raw/boot-timeline.txt. (1) Launch, then one batch as soon as presence allows: capture at ~2 s, click a toolbar control, capture at ~6 s and ~12 s — the window is painted and responds while both MCP children are still binding (timeline proves they are). (2) The timeline shows /health ok before the MCP binds finish. (3) Quit; cp -R the .app to ${SCRATCH}/gui-round-broken.app (never touch the built original), rename its Contents/MacOS/vysted-sidecar*, launch the copy with the isolated HOME: captures at ~3 s and ~15 s show the status chip red and panels naming "The data engine could not start (...)" at once, not after 120 s; quit it, rm -rf the copy. (4) On a healthy instance kill ONLY its main sidecar child pid: capture shows the chip "Sidecar error" and panels/chat saying "The data engine stopped (exit code ...)". A reboot is out of reach: record the launch as warm and say so; the verifier rules whether a warm launch carries the claim.`,
  'R15-LIFECYCLE-008': 'Before launch write filler lines to <home>/Library/Application Support/com.vysted.terminal/logs/vysted.log up to just under the 2 MiB cap (MAX_LOG_BYTES in src-tauri/src/diag_log.rs) so boot output forces one rotation. After boot: ls -la logs/ shows vysted.log and vysted.log.1; vysted.log holds fresh timestamped [sidecar], [vysted] and MCP lines (raw/ls-logs.txt, raw/log-head.txt). Then Settings -> "Copy diagnostics": capture the preview before copying, click copy, capture, and save pbpaste to raw/clipboard.txt (keyless isolated content; grep it for key shapes first and write only the verdict line if any match).',
  'R15-UI-009': 'Export CSV in Watchlist, Portfolio and Screener (run a screen first): each shows the saved path (capture per panel) and the file exists under <home>/Library/Application Support/com.vysted.terminal/exports/csv/ (ls -la and the header row of each file into raw/). A silent no-op on any of the three is regressed.',
  'R15-UI-022': 'Chart with a loaded daily symbol (SPY). Native events via the rig only. (1) Horizontal line and trendline clicked mid-candle, well away from the close: renders at the clicked y (capture; record the click point and the drawn y). (2) A trendline clicked twice right of the last bar is visible. (3) The Text tool asks for a label; type "gui-check": the chart shows gui-check, not "label". (4) Lock a drawing: its row delete control is disabled and a click on the drawing leaves it in place.',
  'R15-UI-025': 'Notes: open a note, select a word (double-click it), click the toolbar Link: an inline URL popover appears (capture); type https://example.com and apply: the selection carries the link mark (capture), and the stored note under the isolated data dir contains the link (raw/note-after.txt).',
  'R15-UI-050': 'Notes: at the start of an empty line type "/": the slash menu opens (capture); press down twice so an active row is highlighted (capture). No two-line row clips its description or overlaps the next item, and the active row background does not cut the next row. Save a crop-free full capture; name the rows in DRIVE.md.',
  'R15-UI-083': `A populated, settled research brief (seeded; else ask the composer "research AAPL" on the local llama3.1:8b under the LOCAL-MODEL LOCK, and if no settled brief appears in 10 min: blocked_env). Click Save .md, Save PDF and Save PNG: each reports its path (capture) and the file exists under exports/ (ls into raw/); copy the exported PNG into raw/ and register it with "python3 ${REPO}/scripts/rig/register_capture.py <png> --tool vysted-export"; copy the PDF into raw/. The raster must show the settled brief, not a mid-animation frame.`,
  'R15-UI-084': 'Resize the window as large as the display allows ("resize 2560 1440"; record the actual size from "bounds"). Open the agent dock (capture, note its width), double-click its resize handle: the dock spans the whole cockpit and the panel host is hidden (capture); double-click again: the prior width returns (capture). Record the measured widths.',
  'R15-LIFECYCLE-040': 'Packaged macOS app cold boot: the MCP children are processes spawned by the app (ps tree under the app pid, raw/ps-tree.txt), and GET /openbb-mcp/status and /sec/status on the app sidecar port report bound/ready (raw/mcp-status.txt); capture the cockpit with the status chip. The Windows half is out of reach on this Mac: record it as not_driven. Do not edit docs/redesign/DECISIONS.md (lead-owned): DRIVE.md is the record.',
}
// Entries the rig cannot drive by construction: it acts only on the Vysted window.
const NO_RIG = {
  'R15-DOCS-024': 'needs a real Claude Desktop session over mcp-remote/stdio; the rig drives only the Vysted window and the driver never types into another app',
}

// ---------------------------------------------------------------- schemas
const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }
const NUM = { type: 'number' }
const BOOL = { type: 'boolean' }
const STRS = { type: 'array', items: STR }
const PRE = S({ model: STR, status: { type: 'string', enum: ['ready', 'blocked'] }, sha: STR, worktree: STR, app_path: STR, dev_binary: STR, seed_dir: STR, seed_populated: BOOL, sentinel_expiry: STR, idle_s: NUM, frontmost: STR, vysted_apps: STRS, port_5173: STR, entries: { type: 'array', items: S({ id: STR, severity: STR, status: STR }) }, rejected_ids: { type: 'array', items: S({ id: STR, reason: STR }) }, blockers: STRS, notes: STRS, summary: STR })
const CHECK = S({ check: STR, result: { type: 'string', enum: ['shown', 'not_shown', 'not_driven'] }, capture: STR }, ['check', 'result'])
const DRIVE = S({ model: STR, id: STR, verdict: { type: 'string', enum: ['holds', 'regressed', 'blocked_env', 'operator_present'] }, evidence: STR, drive_file: STR, captures: STRS, checks: { type: 'array', items: CHECK }, launched_size: STR, stops: STRS, summary: STR }, ['model', 'id', 'verdict', 'evidence', 'drive_file', 'captures', 'checks', 'stops', 'summary'])
const VERIFY = S({ model: STR, id: STR, verdict: { type: 'string', enum: ['certified', 'not_certified', 'still_needs_gui'] }, reason: STR, evidence_file: STR, unregistered_captures: STRS, summary: STR })
const ADJ = S({ model: STR, commit: STR, changed: { type: 'array', items: S({ id: STR, from: STR, to: STR }) }, md_regenerated: BOOL, verdicts_file: STR, notes: STRS, summary: STR })

// ---------------------------------------------------------------- 1. Preflight
phase('Preflight')
const WT = SCRATCH + '/gui-' + SHA_IN.slice(0, 7)
const pre = await run(`${COMMON}

ROLE: GUI-ROUND PREFLIGHT (Sonnet, mechanical; label gui-preflight). ${DRY ? 'DRY RUN: read-only — no worktree, no install, no build, no seed; report what exists and what the round would do.' : 'You alone build now.'} ${STALL} Record each fact with its command in ${EV}/PREFLIGHT.md (mkdir -p ${EV}).
(1) Git: git fetch; resolve ${SHA_IN} to a full sha (git rev-parse --verify '${SHA_IN}^{commit}'); it must be 004-r4-experience-rebuild or an ancestor of it (git merge-base --is-ancestor), else status 'blocked'.
(2) Packaged app at that sha, in the scratch worktree ${WT}: if it exists at the sha with src-tauri/target/debug/bundle/macos/*.app built (a restart), reuse it; if it exists at another sha, remove only that worktree. ${DRY ? 'Dry run: only report whether it exists.' : `Else git worktree add --detach ${WT} <sha>; there, detached with logs in ${EV}/logs/: pnpm install --frozen-lockfile; node scripts/ensure-all-sidecars.mjs (all three sidecar binaries); pnpm tauri build --debug --bundles app (packaged tauri:// origin, bundled sidecars). app_path = the .app it produced; confirm Contents/MacOS/vysted-terminal and the three bundled sidecars exist in it. Then, non-blocking, a dev-origin binary for R15-CODE-AGENT-001: CARGO_TARGET_DIR=${WT}/src-tauri/target-devurl cargo build --manifest-path src-tauri/Cargo.toml (no custom-protocol feature, so it loads devUrl http://localhost:5173); dev_binary = its path if it built with its sidecars beside it, else '' with the reason in notes. A build failure that survives one clean retry → status 'blocked' with the step and log tail.`}
(3) Seed ${SCRATCH}/gui-round-seed ${DRY ? '(dry run: report whether it exists)' : `from ${SCRATCH}/vysted-iso/data (the shared stack's isolated profile; never his real data): sqlite3 "<db>" ".backup '<seed>/<name>.db'" per .db except audit_log.db, cp -R workspaces/, notes/ and searxng/settings.yml, and a fresh dev-keystore.json reading exactly {"secrets": {}, "migrated": true} (chmod 600; ISOLATION_MAP.md §2.4). Do not start, stop or write through the shared stack (:52152-54); reading its data dir is all you need. If ${SCRATCH}/vysted-iso/data is missing → status 'blocked'.`} seed_populated = the seed holds a watchlist with symbols, >= 1 portfolio position and >= 1 note (sqlite3 -readonly queries; list what is missing in notes).
(4) Presence, one reading each, no input: idle = ${RIG} idle; sentinel = ${AWAY_CMD} (sentinel_expiry = its output, '' when None); frontmost = ${FRONT_CMD}; vysted_apps = ${APPS_CMD} (each line); port_5173 = 'lsof -nP -iTCP:5173 -sTCP:LISTEN' holder ('free' when none). Append the reading to ${EV}/presence.log. Presence never blocks the preflight: the drivers wait for it.
(5) Entries: read ${REG} DIRECTLY (the 'entries' list; never 'register.py status'). ${IDS ? 'Requested ids: ' + JSON.stringify(IDS) + '. Each must exist with status exactly needs_gui; any other → rejected_ids with its actual status.' : 'Take every entry with status exactly needs_gui, in register order.'} entries = [{id, severity, status}] for those that qualify.
Return model, status, sha (full), worktree, app_path ('' in a dry run without a build), dev_binary, seed_dir, seed_populated, sentinel_expiry, idle_s, frontmost, vysted_apps, port_5173, entries, rejected_ids, blockers, notes, summary ≤120 words.`, { label: 'gui-preflight', phase: 'Preflight', model: 'sonnet', effort: 'medium', schema: PRE })

if (!pre || pre.status !== 'ready') {
  const why = pre ? (pre.blockers.length ? pre.blockers : ['preflight status ' + pre.status]) : ['preflight agent died']
  log('preflight blocked — the round does not run: ' + JSON.stringify(why))
  return { status: 'blocked', sha: pre ? pre.sha || null : null, blockers: why, driven: [], certified: [], not_certified: [], skipped: [], commit: null }
}
const SHA = pre.sha
const SH7 = SHA.slice(0, 7)
if (pre.rejected_ids.length) log('requested ids that are not needs_gui: ' + JSON.stringify(pre.rejected_ids))
const entries = pre.entries.slice(0, MAX_ENTRIES)
if (pre.entries.length > MAX_ENTRIES) log('max_entries ' + MAX_ENTRIES + ': ' + (pre.entries.length - MAX_ENTRIES) + ' entries left for a later round: ' + pre.entries.slice(MAX_ENTRIES).map(e => e.id).join(', '))
log('preflight ready @ ' + SH7 + '; ' + entries.length + ' entries: ' + entries.map(e => e.id).join(', ') + '; sentinel ' + (pre.sentinel_expiry || 'NOT ARMED') + '; idle ' + pre.idle_s + ' s; vysted apps ' + pre.vysted_apps.length + '; app ' + (pre.app_path || '(none)'))
if (!entries.length) {
  log('nothing to drive')
  return { status: 'done', sha: SHA, driven: [], certified: [], not_certified: [], skipped: [], commit: null }
}
if (DRY) {
  const plan = entries.map(e => ({ id: e.id, severity: e.severity, driver: NO_RIG[e.id] ? 'none (blocked_env: ' + NO_RIG[e.id] + ')' : 'opus/high', check: NO_RIG[e.id] ? '' : (CHECKS[e.id] || 'the GUI check in its register note') }))
  log('dry run: the round would drive ' + plan.filter(p => !NO_RIG[p.id]).length + ' entries sequentially, then one verifier each; no GUI input, no register edit')
  return { status: 'dry_run', sha: SHA, planned: plan, driven: [], certified: [], not_certified: [], skipped: [], commit: null }
}
if (!pre.app_path) {
  log('preflight returned no app_path — nothing can be launched')
  return { status: 'blocked', sha: SHA, blockers: ['no packaged app built at ' + SH7], driven: [], certified: [], not_certified: [], skipped: [], commit: null }
}

// ---------------------------------------------------------------- 2. Drive (ONE GUI lane, sequential)
phase('Drive')
const drives = []
let stopAt = null
for (const e of entries) {
  if (NO_RIG[e.id]) {
    drives.push({ id: e.id, verdict: 'blocked_env', evidence: NO_RIG[e.id], drive_file: '', captures: [], checks: [], stops: [NO_RIG[e.id]], auto: true })
    log(e.id + ': blocked_env without a driver — ' + NO_RIG[e.id])
    continue
  }
  if (stopAt) {
    drives.push({ id: e.id, verdict: 'operator_present', evidence: 'not attempted: the lane stopped at ' + stopAt + ' (operator present)', drive_file: '', captures: [], checks: [], stops: [], auto: true })
    continue
  }
  const dir = EV + '/' + e.id
  const d = await run(`${COMMON}

ROLE: GUI DRIVER ${e.id} (${e.severity}) (Opus; label gui-drive-${e.id}). You are the ONLY GUI owner now; COMMON's 'No GUI' is lifted for you alone, under these rules. ${STALL}
${PRESENCE}
${ISOLATE(SCRATCH + '/gui-round-home-' + e.id, SHA)}
APP: app_path = ${pre.app_path}${pre.dev_binary ? '; dev-origin binary = ' + pre.dev_binary : ''}; gui worktree ${pre.worktree} at ${SHA} (read-only for you, except starting vite there when your check says so). Preflight: seed populated = ${pre.seed_populated}; :5173 holder = ${pre.port_5173}.
ENTRY: read ${e.id} in ${REG} (title, repro, fix_shape, note) and the code it names at ${SHA} (git show ${SHA}:<path>) BEFORE driving. Reproduce its ORIGINAL repro through the app. What the drive must show: ${CHECKS[e.id] || 'the GUI check in the entry\'s register note, exactly.'}
EVIDENCE, AS YOU GO: entry dir ${dir} (mkdir -p; raw files in ${dir}/raw/). Captures ONLY via the rig ('capture' or a batch capture step) to ${dir}/${SH7}-NN-<slug>.png — the rig registers each one in docs/redesign/verification/r15/CAPTURES.jsonl, and an unregistered image is not evidence (and blocks the push). Never overwrite an existing capture; never take a screenshot any other way. Proof shots show POPULATED panels, dark theme; record the launched window size from 'bounds'. Write ${dir}/DRIVE.md from the first minute and extend it after every step: header (entry id, sha ${SH7}, app path, isolated home, launch time, window size), then per check: the batch file used, the presence line before it, what the capture shows (open each PNG with the Read tool and describe it; never describe a capture you did not open), the raw files; then the real-data mtime before/after, stops, and the verdict line. A restart of your role continues from DRIVE.md.
VERDICT: holds = every check the entry needs is shown on screen and read back; regressed = a check shows the defect (a silent no-op, the old behaviour); blocked_env = the environment prevented the drive (build missing, Screen Recording or Accessibility not granted — a black capture or an osascript error — a boot failure unrelated to the entry, the Claude Desktop or Windows half), with the reason; operator_present = presence never allowed it within ${GUI_WAIT_MIN} min, or a human touched the machine. A check you could not drive is result not_driven, never shown. Quit your app by its pid and confirm nothing of yours is left running (kill your vite pid if you started one). Return model, id '${e.id}', verdict, evidence (one line), drive_file '${EVR}/${e.id}/DRIVE.md', captures (repo-relative paths), checks[{check, result, capture}], launched_size, stops, summary ≤100 words.`, { label: 'gui-drive-' + e.id, phase: 'Drive', model: 'opus', effort: 'high', schema: DRIVE })
  const r = d || { id: e.id, verdict: 'blocked_env', evidence: 'driver died twice', drive_file: '', captures: [], checks: [], stops: ['driver died'] }
  r.id = e.id
  drives.push(r)
  log(e.id + ': ' + r.verdict + ' — ' + r.evidence)
  if (r.verdict === 'operator_present') stopAt = e.id
}
const driven = drives.filter(x => x.verdict === 'holds' || x.verdict === 'regressed')
if (stopAt) log('GUI lane stopped at ' + stopAt + ': operator present; the rest stay needs_gui')

// ---------------------------------------------------------------- 3. Verify (one fresh Opus per driven entry)
phase('Verify')
const VLIM = limiter(3)
const verdicts = (await parallel(driven.map(x => () => VLIM(() => run(`${COMMON}

ROLE: FRESH GUI VERIFIER ${x.id} (Opus, fresh context; label gui-verify-${x.id}). Rule whether ${x.id} is fixed at ${SHA} from the GUI evidence. Default to not certified where the evidence does not carry the claim. INPUTS, ONLY: the entry in ${REG} (title, repro, fix_shape, note), ${EVR}/${x.id}/DRIVE.md, the captures and raw files under ${EVR}/${x.id}/, docs/redesign/verification/r15/CAPTURES.jsonl, ${EVR}/presence.log, and the code at ${SHA} (git show ${SHA}:<path>). Never read another entry's DRIVE.md or VERIFY.md, any VERDICTS.*, PREFLIGHT.md, or the drive's summary (the driver's verdict is a claim, not an input). No GUI, no app launch.
CAPTURES ARE EVIDENCE ONLY IF REGISTERED: for each PNG DRIVE.md cites, shasum -a 256 it and find that sha256 in CAPTURES.jsonl with tool 'scripts/rig/rig.py capture' (or 'vysted-export' for an app-exported file) and a window_owner containing 'vysted'; an unregistered or mismatched image is ignored and listed in unregistered_captures. Open every registered capture with the Read tool and judge it yourself; a capture without a presence.log line before it is ignored too.
CERTIFY THE CLAIM, NOT ONLY THE REPRO: certified only when the entry's stated conclusion — its title and fix_shape — is visible in the registered captures and raw read-backs for every part of the GUI check its note names. not_certified when a capture shows the defect (name the capture and what it shows). still_needs_gui when what was driven holds but a part could not be driven here (the Windows half, the Claude Desktop half, a check recorded not_driven) — name exactly what remains. Write ${EVR}/${x.id}/VERIFY.md (per part: capture or raw file, what it shows, ruling). Return model, id '${x.id}', verdict, reason (≤60 words; for still_needs_gui, the remaining check), evidence_file, unregistered_captures, summary ≤80 words.`, { label: 'gui-verify-' + x.id, phase: 'Verify', model: 'opus', effort: 'high', schema: VERIFY }))))).filter(Boolean)
if (verdicts.length < driven.length) log('verifiers missing: ' + driven.filter(x => !verdicts.some(v => v.id === x.id)).map(x => x.id).join(', ') + ' — they stay needs_gui')

// ---------------------------------------------------------------- 4. Adjudicate
phase('Adjudicate')
const vOf = id => verdicts.find(v => v.id === id)
const certified = driven.filter(x => vOf(x.id) && vOf(x.id).verdict === 'certified').map(x => x.id)
const notCertified = driven.filter(x => vOf(x.id) && vOf(x.id).verdict === 'not_certified').map(x => ({ id: x.id, reason: vOf(x.id).reason }))
const skipped = drives.filter(x => !certified.includes(x.id) && !notCertified.some(n => n.id === x.id)).map(x => {
  const v = vOf(x.id)
  return { id: x.id, reason: v ? 'still_needs_gui: ' + v.reason : (x.verdict === 'holds' || x.verdict === 'regressed' ? 'verifier died' : x.verdict + ': ' + x.evidence) }
})
log('verdicts: certified ' + certified.length + ', not certified ' + notCertified.length + ', stays needs_gui ' + skipped.length)
if (!driven.length) {
  log('nothing was driven — no register change, no commit')
  return { status: 'done', sha: SHA, driven: [], certified: [], not_certified: [], skipped, commit: null }
}
const adj = await run(`${COMMON}

ROLE: GUI-ROUND ADJUDICATOR (Sonnet, mechanical + careful; label gui-adjudicate). Apply these rulings to ${REG} in the main worktree — no new judgement:
certified → status 'fixed': ${JSON.stringify(certified)}
not_certified → status 'open': ${JSON.stringify(notCertified)}
stay needs_gui: ${JSON.stringify(skipped)}
Edit with one python3 read-modify-write (json.load, change only these entries, json.dump with the file's existing indent and key order, ensure_ascii as the file has it) right after re-reading the file (other agents edit it too). Per id append to its 'note' (joined with ' || ', as existing notes are): 'gui-round@${SH7}: <certified | not certified: <reason> | stays needs_gui: <reason>>, evidence ${EVR}/<id>/DRIVE.md, verifier ${EVR}/<id>/VERIFY.md' (skip the VERIFY.md part where no verifier ran); for certified entries also set 'closure_evidence' to 'gui-round@${SH7} ${EVR}/<id>/DRIVE.md'. 'git diff --stat ${REG}' must show only those entries changed. Regenerate the md view: python3 scripts/r15/render_register_md.py > ${REGMD}. Write ${EVR}/VERDICTS.json {sha: '${SHA}', certified, needs_gui (the stay ids), not_certified [{id, reason}], concur_not_defect: [], refused_not_defect: []} and ${EVR}/VERDICTS.md (one line per entry: id, severity, drive verdict, ruling, reason, DRIVE.md and VERIFY.md paths). Commit BY PATH ONLY: git add ${EVR} ${REG} ${REGMD} docs/redesign/verification/r15/CAPTURES.jsonl (plus docs/redesign/verification/r15/RIG_ABORTS.log if it exists); first check 'git status --short ${EVR}' lists no file outside ${EVR}/ and that every PNG under ${EVR} has its sha256 in CAPTURES.jsonl (an unregistered one is removed from the commit and named in notes); then git -c core.hooksPath=/dev/null commit -q -m "docs(r15): gui-round @${SH7} — ${certified.length} certified, ${notCertified.length} reopened, ${skipped.length} stay needs_gui" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" -- <the same paths>. Do not push. Return model, commit (full sha), changed[{id, from, to}], md_regenerated, verdicts_file, notes, summary ≤80 words.`, { label: 'gui-adjudicate', phase: 'Adjudicate', model: 'sonnet', effort: 'high', schema: ADJ })
if (!adj) log('adjudicator died — the rulings are in this return value and in each ' + EVR + '/<id>/VERIFY.md; the register is unchanged')
else log('adjudicated: commit ' + (adj.commit || '').slice(0, 8) + '; ' + adj.changed.map(c => c.id + ' ' + c.from + '→' + c.to).join(', '))

return {
  status: adj ? 'done' : 'adjudicator_died',
  sha: SHA,
  driven: driven.map(x => x.id),
  certified,
  not_certified: notCertified,
  skipped,
  commit: adj ? adj.commit : null,
}
