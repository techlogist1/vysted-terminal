export const meta = {
  name: 'r15-final-pass',
  description: 'R15 final pass after r15-rc3: preflight at the rc3 sha, one adversarial sweep over the whole product (at most two strongest-tier adversaries with distinct lenses, beside at most four Opus lanes re-running the mechanical checks), Opus triage into R15-FINAL register entries, findings closed under gate 3 in bounded fix rounds (writers, integrator, fresh verifier), a final Opus re-proof that writes R15_FINAL_PASS.md, then the run-ending steps only when args.run_ending is true',
  whenToUse: 'Once r15-rc3 is tagged on 004-r4-experience-rebuild; args {sha, max_fix_rounds, adversaries, run_ending}. Runbook: FINAL_PASS_PLAN.md',
  phases: [
    { title: 'Preflight', detail: 'git, production bundle at the sha, dedicated stack :52800-52802, register snapshot' },
    { title: 'Sweep', detail: '<=2 strongest-tier adversaries (investor, maintainer) beside <=4 Opus mechanical lanes' },
    { title: 'Triage', detail: 'dedupe, refute or admit, R15-FINAL register entries' },
    { title: 'Close', detail: 'gate 3 in bounded rounds: plan, writers, integrator, fresh verifier' },
    { title: 'Re-proof', detail: 'chain + smoke + gate-8 boundary at the final head, R15_FINAL_PASS.md' },
    { title: 'Run-ending', detail: 'graph refresh, operator dev stack relaunch, caffeinate release (args.run_ending only)' },
  ],
}

const A = args || {}
const KNOWN = ['sha', 'max_fix_rounds', 'adversaries', 'run_ending', 'drive_groups', 'batt_shards', 'max_writers', 'bundle_path', 'caffeinate_pids', 'scratch', 'dry_run']
const bad = Object.keys(A).filter(k => !KNOWN.includes(k))
if (bad.length) throw new Error('final-pass: unknown args ' + bad.join(', ') + ' (known: ' + KNOWN.join(', ') + ')')
if (typeof A.sha !== 'string' || !/^[0-9a-f]{7,40}$/.test(A.sha)) throw new Error('final-pass: args.sha must be the r15-rc3 commit sha (7-40 lowercase hex), got ' + JSON.stringify(A.sha))
const intArg = (k, d, lo, hi) => { const v = A[k] == null ? d : A[k]; if (!Number.isInteger(v) || v < lo || v > hi) throw new Error('final-pass: args.' + k + ' must be an integer ' + lo + '..' + hi + ', got ' + JSON.stringify(A[k])); return v }
const boolArg = k => { const v = A[k]; if (v == null) return false; if (v === true || v === 'true') return true; if (v === false || v === 'false') return false; throw new Error('final-pass: args.' + k + ' must be a boolean, got ' + JSON.stringify(v)) }
const MAX_ROUNDS = intArg('max_fix_rounds', 2, 0, 3)
const N_ADV = intArg('adversaries', 2, 1, 2) // routing change 5: never more than two strongest-tier agents at once
const BATT_N = intArg('batt_shards', 4, 1, 8)
const MAXW = intArg('max_writers', 4, 1, 6)
const RUN_ENDING = boolArg('run_ending')
const DRY = boolArg('dry_run')
const DRIVE_GROUPS = A.drive_groups == null ? ['composer-chat', 'research-briefs', 'screener', 'panels-layouts', 'portfolio-notes', 'settings-plugins', 'onboarding-stranger', 'failure-inducer'] : A.drive_groups
if (!Array.isArray(DRIVE_GROUPS) || !DRIVE_GROUPS.length || DRIVE_GROUPS.length > 8 || !DRIVE_GROUPS.every(g => typeof g === 'string' && /^[a-z-]+$/.test(g))) throw new Error('final-pass: args.drive_groups must be 1..8 group names from PROMPT_surface_s2.md')
if (A.bundle_path != null && (typeof A.bundle_path !== 'string' || !A.bundle_path.startsWith('/'))) throw new Error('final-pass: args.bundle_path must be an absolute path')
const CAFF = A.caffeinate_pids == null ? [] : A.caffeinate_pids
if (!Array.isArray(CAFF) || !CAFF.every(p => Number.isInteger(p) && p > 1)) throw new Error('final-pass: args.caffeinate_pids must be an array of pids')

const REPO = '/Users/lokavyasingh/Documents/dev/vysted-terminal'
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const EV = REPO + '/docs/redesign/verification/r15/final-pass'
const SHEET = REPO + '/docs/redesign/verification/R15_FINAL_PASS.md'
const REG = 'docs/redesign/verification/vysted-r15-register.json'
const CAND = SCRATCH + '/final-cand'
const SEED = SCRATCH + '/final-seed-data'
const FIXWT = SCRATCH + '/final-int'
const FIXBR = 'worktree-agent-final-int'
// The brief's banned word and phrase, built at runtime so no committed file carries them.
const BW = String.fromCharCode(76, 97, 121, 97)
const BP = ['low', 'latency'].join('-') + ' trading'

const LENSES = [
  { key: 'investor', port: 52810, web: 5281 },
  { key: 'maintainer', port: 52820, web: 5282 },
].slice(0, N_ADV)

if (DRY) {
  const spawn = [{ label: 'final-preflight', model: 'opus' }]
    .concat(LENSES.map(l => ({ label: 'final-adv-' + l.key, model: 'fable', effort: 'high', port: l.port })))
    .concat([{ label: 'final-chain', model: 'opus' }, { label: 'final-docs', model: 'opus', port: null }])
    .concat(DRIVE_GROUPS.map((g, i) => ({ label: 'final-drive-' + g, model: 'opus', port: 52840 + i })))
    .concat(Array.from({ length: BATT_N }, (_, k) => ({ label: 'final-battery-' + k, model: 'opus', port: 52860 + k })))
    .concat([{ label: 'final-triage', model: 'opus', port: 52880 }])
    .concat(MAX_ROUNDS ? [{ label: 'final-fix-r<N>-{plan,int,verify} x' + MAX_ROUNDS + ' + <=' + MAXW + ' writers/round', model: 'opus|sonnet' }] : [])
    .concat([{ label: 'final-reproof', model: 'opus', port: 52895 }])
    .concat(RUN_ENDING ? [{ label: 'final-run-ending', model: 'opus' }] : [])
  spawn.forEach(s => log('dry_run: would spawn ' + s.label + ' (' + s.model + (s.effort ? '/' + s.effort : '') + ')' + (s.port ? ' port ' + s.port : '')))
  return { dry_run: true, sha: A.sha, max_fix_rounds: MAX_ROUNDS, adversaries: N_ADV, run_ending: RUN_ENDING, would_spawn: spawn }
}

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
const FABLE = limiter(2) // hard ceiling on strongest-tier agents alive at once, retries included
const MECH = limiter(4) // mechanical Opus lanes beside the adversaries: 2 + 4 = the harness cap of 6
// Routing change 5, enforced: sonnet and fable always at effort high, opus at its default effort (no effort key).
const call = (prompt, opts) => {
  if (!['opus', 'sonnet', 'fable'].includes(opts.model)) throw new Error('final-pass: model must be opus, sonnet or fable (' + opts.label + ')')
  if (opts.model === 'opus' ? 'effort' in opts : opts.effort !== 'high') throw new Error('final-pass: effort rule broken for ' + opts.label)
  if (opts.model === 'fable' && opts.phase !== 'Sweep') throw new Error('final-pass: the strongest tier is allowed only in the adversarial sweep (' + opts.label + ')')
  const go = () => agent(prompt, opts)
  return Promise.resolve().then(() => (opts.model === 'fable' ? FABLE(go) : go())).catch(e => { log('agent ' + opts.label + ' failed: ' + e); return null })
}
// A call that dies or starves gets ONE same-tier retry, never a third try.
const run = (prompt, opts) => call(prompt, opts).then(r => r || (log('agent ' + opts.label + ' (' + opts.model + ') returned nothing - one same-tier retry'), call(prompt, { ...opts, label: opts.label + '-retry' })))

const COMMON = `Repo: ${REPO}, integration branch 004-r4-experience-rebuild. This is the R15 FINAL PASS: exactly one final adversarial pass over the whole product after r15-rc3, its findings closed under gate 3 inside this same workflow. There is no second pass, so every verdict must be honest about anything left. The operator may be away; never ask, decide and record. Before any pnpm/node/cargo command: export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH. Shell: cat and ls are aliased and can hang, so use /bin/cat and /bin/ls.
FORBIDDEN READS: never read docs/redesign/verification/R15_BRIEF*.md or anything under docs/redesign/verification/r15/local/.
BOUNDARIES: trading is out of the product permanently (D81): the agent never places, confirms or auto-applies a broker order in any mode, and nobody re-adds any of it. Induce failures at the app's edge only (kill YOUR OWN sidecar pid, malformed input, a provider base URL pointed at a closed local port, a corrupt copy of YOUR OWN data file); never change system settings, firewall, DNS or Wi-Fi, and never drop the network. The operator's real app data (~/Library/Application Support/com.vysted.terminal, ~/Library/Caches/vysted-terminal, ~/Library/WebKit/vysted-terminal), his OS keychain items and any installed copy of the app under /Applications are READ-ONLY: stat or read them for evidence only; never write them, launch against them, or delete them. Never a blanket kill (no pkill, no killall, no kill by name or pattern): stop only processes you started, by the pid you recorded; never stop Claude, Cursor, Zed, Ghostty or anything that is not Vysted's. Never print, log, copy or commit a secret (no keystore or keychain value, env dump or auth header). No GUI: no clicks, keystrokes, screen capture, osascript UI events or visible windows; headless Chrome or the repo's playwright against YOUR OWN sidecar (docs/redesign/verification/r15/stage0/ISOLATION_MAP.md section 1b) is allowed. Do not edit CLAUDE.md, src-tauri/tauri.conf.json, .github/, LICENSE*, COMMERCIAL_LICENSE.md or types/plugin.ts. Never tag, merge to main, push main or 004-r4-experience-rebuild, open a PR or force-push.
WORDS: never write the word '${BW}' or the phrase '${BP}' in any file, commit, branch or return value. Refer to them as BANNED_WORD and BANNED_PHRASE. To grep for them, build the pattern in the shell (W=$(printf '\\x6c\\x61\\x79\\x61'); P=$(printf 'low-%s trading' latency)) and use grep -i with "$W" and "$P", so no log carries the literal. Report hits as counts and file:line only, never the matched text.
TESTS ARE STATE: never delete, skip or weaken a test to get green; if a test is wrong, fix it and log why; never special-case code to satisfy a test. Never speculate about code you have not opened. Fix root causes, not symptoms. Deliver what the entry asks at the scope intended: no refactors, abstractions, flags or defensive code for cases that cannot happen.
GIT: commit only with 'git -c core.hooksPath=/dev/null commit'; push with GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20" git push ...; never 'git add -A' or 'git add .' (stage explicit paths). CLAUDE.md and docs/redesign/verification/r15/spend-ledger.jsonl stay uncommitted. Never move the HEAD of the main checkout ${REPO} or commit in it: what you write there (evidence, register edits) stays uncommitted for the lead. Writers and the integrator commit only on their own worktree-agent-final-* branch and push it after every concrete deliverable.
The register: ${REG} (+ the .md view regenerated by scripts/r15/register.py; entries with id, title, severity, tags/operator_areas, subsystem, repro, evidence, raw_ids, status, notes). The four named areas: ui-panels, agent-chat, research-search, data-smallcaps.
HARNESS STALL RULE (a 3-minute no-progress watchdog kills the agent and restarts it from scratch): NO single tool call may run longer than ~120 s. Anything longer (pnpm install, pnpm ci-local, pnpm build, pnpm tauri build, full pytest/vitest, cargo, PyInstaller/sidecar builds, the smoke test, sidecar boots, vy.py agent runs, curl loops, graph rebuilds) MUST be started detached ('nohup <cmd> > <log> 2>&1 &' or the Bash tool's run_in_background) and polled with SEPARATE short calls ('sleep 60' as its own call, then 'tail -n 5 <log>'), never an 'until ... sleep' loop inside one call. Keep emitting a tool call at least every 2 minutes. If you find files, branches, a worktree or a live sidecar from a previous attempt of your own role (a restart), read them and CONTINUE from them instead of redoing the work.
LOCAL-MODEL LOCK: the local model (Ollama) is one lane shared by every agent. Wrap EVERY call that reaches it (vy.py --provider ollama, a sidecar agent run on an Ollama model, any request to :11434) in a lock: in separate short calls, try 'mkdir /tmp/vysted-r15-ollama.lock 2>/dev/null' every 5 s (at most ~100 s of retries per tool call) for up to 15 min in total; a lock dir older than 20 min is stale ('find /tmp/vysted-r15-ollama.lock -maxdepth 0 -mmin +20' prints it) and may be removed with rmdir. Holding it, run the call so the lock is released on success AND failure: nohup sh -c 'trap "rmdir /tmp/vysted-r15-ollama.lock" EXIT INT TERM HUP; <the call>' > <log> 2>&1 & (then poll). One call per lock hold. A call that could not get the lock in 15 min is 'lock_timeout' (a harness cause), never a product failure.
Your final text IS the return value: return only the structured object.`
const STALL = 'STALL RULE, this role: every install, build, test run, sidecar boot and vy.py run below starts detached (nohup ... > <log> 2>&1 &) and is polled in separate short calls; no single tool call over ~120 s.'

const facts = (sha, wt) => `FINAL PASS FACTS. Head under test ${sha}; its scratch worktree ${wt} (sidecars freshly built, sidecar/.venv present) is READ-ONLY for you unless your role says otherwise: boot sidecars from its source or its src-tauri/binaries; never edit, install or build in it. Seed data ${SEED} (a keyless snapshot of the isolated profile): cp -R it to ${SCRATCH}/final-data-<your label> for your own sidecar. A stranger's clean profile = an EMPTY data dir holding only dev-keystore.json reading exactly {"secrets": {}, "migrated": true} (chmod 600; ISOLATION_MAP.md section 2.4: without it the app sweeps the real keychain). Shared final-pass stack: main :52800 + openbb-mcp :52801 + sec-edgar-mcp :52802, booted by preflight from the candidate's built binaries on a seed copy; it is shared READ-ONLY (GETs and read-only agent runs; never restart it or write through it); its pids are in ${EV}/pids.json. Own sidecar: the 'Main sidecar, from source' block of docs/redesign/verification/r15/stage0/ISO_STACK.md with cwd <worktree>/sidecar, your port, your data dir and VYSTED_OPENBB_MCP_PORT=52801 VYSTED_SEC_EDGAR_MCP_PORT=52802, started detached with stdin held by a sleep; record the sleep pid; poll /health in separate calls; stop it by killing ITS sleep pid only. If your port already answers /health, it is a previous attempt of your own role: reuse it. Models: local llama3.1:8b via Ollama first (python3 scripts/r15/vy.py invoke copilot '<prompt>' --port <p> --provider ollama --model llama3.1:8b, under the LOCAL-MODEL LOCK); one free OpenRouter slug second; OpenAI-direct ONLY through vy.py under its spend guard (read r15/spend-ledger.jsonl first; the guard refuses near the cap). Evidence root ${EV} (mkdir -p as needed). Write your working log to ${EV}/logs/<your label>.md as you go. Findings go to ${EV}/findings/<the file your role names>.json as a JSON array (write [] first, rewrite as you go) of {key, kind, severity, register_id, title, area, repro, evidence_file, suspected_files}. kind: regression (a fixed register entry no longer holds; register_id = that entry), new_defect (real, not in the register), chain (a ci-local/smoke failure), gate8 (an order/broker path, an order attempt that does not halt, rows in audit_orders, or a broken tracked-portfolio step), environment (an upstream outage proven by a direct probe; not a product defect). area: one of ui-panels, agent-chat, research-search, data-smallcaps, lifecycle, docs, safety, release. severity: critical = wrong money-relevant data shown as true, data loss, safety boundary; high = a core flow breaks or silently degrades, or a promise central to the product is missing; medium = a real defect a demanding owner hits in normal use; low = polish or edge. Do not pad: a finding that would not change a decision is not a finding.`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }
const NUM = { type: 'number' }
const BOOL = { type: 'boolean' }
const STRS = { type: 'array', items: STR }
const OBJ = { type: 'object' }
const SEV = { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }
const FINDING = S({ key: STR, kind: { type: 'string', enum: ['regression', 'new_defect', 'chain', 'gate8', 'environment'] }, severity: SEV, register_id: STR, title: STR, evidence_file: STR }, ['key', 'kind', 'severity', 'title', 'evidence_file'])
const KEYED = { type: 'array', items: S({ key: STR, reason: STR }) }
const IDR = { type: 'array', items: S({ id: STR, reason: STR }) }
const PRE = S({ model: STR, status: { type: 'string', enum: ['ready', 'blocked'] }, sha: STR, worktree: STR, bundle_path: STR, bundle_built: BOOL, bundle_sha256: STR, stack_ok: BOOL, ollama_llama31: BOOL, disk_free_gb: NUM, register_snapshot: STR, status_counts: OBJ, open_chm: STRS, blockers: STRS, notes: STRS, summary: STR })
const LANE_P = { model: STR, lane: STR, status: { type: 'string', enum: ['pass', 'fail', 'partial', 'blocked'] }, evidence_files: STRS, counts: OBJ, findings: { type: 'array', items: FINDING }, notes: STRS, summary: STR }
const LANE = S(LANE_P)
const BSHARD = S({ ...LANE_P, results: { type: 'array', items: S({ id: STR, verdict: { type: 'string', enum: ['holds', 'regressed', 'ci_pinned', 'needs_gui', 'blocked_env'] }, evidence: STR }) } })
const TRIAGE = S({ model: STR, admitted: { type: 'array', items: S({ id: STR, severity: SEV, area: STR, title: STR, finding_keys: STRS, existing: BOOL }) }, refuted: KEYED, duplicates: { type: 'array', items: S({ key: STR, of: STR }) }, register_edited: BOOL, triage_file: STR, summary: STR })
const PLAN = S({ model: STR, plan_file: STR, writers: { type: 'array', items: S({ name: STR, model: { type: 'string', enum: ['opus', 'sonnet'] }, ids: STRS, files: STRS, brief: STR }) }, deferred: IDR, lows_unplanned: IDR, summary: STR })
const WRITE = S({ model: STR, branch: STR, head_sha: STR, pushed: BOOL, items: { type: 'array', items: S({ id: STR, outcome: { type: 'string', enum: ['fixed', 'could_not'] }, commit: STR, test: STR, note: STR }, ['id', 'outcome', 'note']) }, focused_tests: STR, issues: STRS, summary: STR })
const INT = S({ model: STR, branch: STR, head_sha: STR, pushed: BOOL, chain: { type: 'string', enum: ['pass', 'fail'] }, counts: OBJ, fixes_applied: STRS, dropped_commits: STRS, failures: STRS, summary: STR })
const VERIFY = S({ model: STR, verdict_file: STR, certified: STRS, not_certified: IDR, adjudicated: { type: 'array', items: S({ id: STR, verdict: { type: 'string', enum: ['not_a_defect', 'not_reproducible', 'environment', 'blocked_tier4'] }, rationale: STR, evidence: STR }) }, summary: STR })
const GATE_ITEM = S({ item: STR, result: { type: 'string', enum: ['PASS', 'FAIL'] }, evidence: STR })
const REPROOF = S({ model: STR, verdict: { type: 'string', enum: ['PASS', 'FAIL'] }, certified_sha: STR, gate_items: { type: 'array', items: GATE_ITEM }, chm_left: STRS, lows_left: STRS, adjudicated: STRS, safety: S({ order_attempt_halts: BOOL, audit_orders_rows: NUM, surface_identical: BOOL, diff_file: STR }), four_areas: { type: 'array', items: S({ area: STR, before: STR, after: STR }) }, register_edited: BOOL, sheet_file: STR, blockers: STRS, summary: STR })
const ENDING = S({ model: STR, status: { type: 'string', enum: ['done', 'partial', 'blocked'] }, steps: { type: 'array', items: S({ step: STR, result: { type: 'string', enum: ['done', 'not_done', 'not_applicable'] }, evidence: STR }) }, dev_stack_pids: STRS, notes: STRS, summary: STR })

// ---------------------------------------------------------------- 1. Preflight
phase('Preflight')
const pre = await run(`${COMMON}

${facts(A.sha, CAND)}

ROLE: PREFLIGHT (Opus; label final-preflight). You alone build in the candidate worktree and boot the shared final-pass stack. ${STALL} Record each fact with its command in ${EV}/PREFLIGHT.md.
(1) Git: git fetch origin; resolve ${A.sha} to a full sha; it must be 004-r4-experience-rebuild or an ancestor of it; record whether the r15-rc3 tag points at it (git rev-parse r15-rc3^{commit}; a mismatch or a missing tag is a blocker), origin/004's relation, 'git worktree list', any 'worktree-agent-final-*' branches (local and origin: a previous attempt of this workflow; report them, delete nothing), the main checkout's HEAD and 'git status --short'.
(2) Candidate worktree ${CAND}: git worktree add --detach ${CAND} <sha> (if the path exists at another sha, remove only that worktree first; if it exists at this sha from a previous attempt, reuse it). There, detached, logs in ${EV}/logs/: pnpm install --frozen-lockfile; node scripts/ensure-all-sidecars.mjs --force (fresh Python 3.13 venvs and all three binaries).
(3) Production bundle at the sha, from a clean profile: ${A.bundle_path ? 'the lead named ' + A.bundle_path + ' - accept it only if it exists, its Info.plist CFBundleShortVersionString equals package.json "version" at the sha, and the evidence that built it (grep docs/redesign/verification for the path) names this sha; else build it as below.' : 'look for a bundle already built at this sha (a *.app under docs/redesign/verification evidence records or a worktree at this sha: src-tauri/target/release/bundle/macos/); accept it only if the record names this sha and its Info.plist version equals package.json at the sha; otherwise build it.'} Build = inside ${CAND} (its own node_modules, venvs and cargo target; nothing reused from the main checkout's build outputs): pnpm tauri build, detached (it also writes the static frontend to ${CAND}/out). A build failure that survives one clean retry → status 'blocked' with the step and the log tail. Record bundle_path and 'shasum -a 256' of its main executable. Also make sure ${CAND}/out exists (the adversaries serve it).
(4) Seed ${SEED}: from ${SCRATCH}/vysted-iso/data (else ${SCRATCH}/rc1-seed-data), sqlite3 '.backup' per .db, the non-sqlite files ISO_STACK.md copies, a fresh keyless dev-keystore.json reading exactly {"secrets": {}, "migrated": true} (chmod 600), no audit_log.db. Never read the operator's real data dir for this.
(5) Shared final-pass stack on a copy of the seed (${SCRATCH}/final-shared-data): openbb-mcp :52801 and sec-edgar-mcp :52802 from ${CAND}/src-tauri/binaries, then the main sidecar binary on :52800 with the two MCP ports exported, each with stdin held by 'sleep 86400'; record the sleep pids and ports in ${EV}/pids.json; /health ok with openbb-mcp available. A port already held by a process you did not start: never kill it → blocked.
(6) Env: llama3.1:8b in 'ollama list'; df -h (blocked below 10 GB free, warn below 25 GB).
(7) Register snapshot: git show <sha>:${REG} > ${EV}/register-at-<sha7>.json; counts by status; ids of critical/high/medium entries whose status is exactly 'open'.
Return model, status, sha (full), worktree, bundle_path, bundle_built, bundle_sha256, stack_ok, ollama_llama31, disk_free_gb, register_snapshot, status_counts, open_chm, blockers, notes, summary ≤120 words.`, { label: 'final-preflight', phase: 'Preflight', model: 'opus', schema: PRE })

if (!pre || pre.status !== 'ready') {
  const why = pre ? (pre.blockers.length ? pre.blockers : ['preflight status ' + pre.status]) : ['preflight agent died twice']
  log('preflight blocked - the final pass does not run: ' + JSON.stringify(why))
  return { status: 'blocked', sha: pre ? pre.sha || A.sha : A.sha, certified_sha: null, sweep: null, triage: null, rounds: [], reproof: null, run_ending: null, blockers: why }
}
const SHA = pre.sha
const blockers = [...pre.blockers]
if (pre.open_chm.length) log('register at the sha already has ' + pre.open_chm.length + ' open c/h/m entries: ' + pre.open_chm.join(', ') + ' (the pass carries them into triage)')
log('preflight ready @ ' + SHA.slice(0, 7) + '; bundle ' + (pre.bundle_built ? 'built' : 'reused') + ' ' + pre.bundle_path)
const F0 = facts(SHA, CAND)

// ---------------------------------------------------------------- 2. Adversarial sweep
phase('Sweep')
const LENS_TEXT = {
  investor: `You are a stranger meeting this product cold: a serious individual investor in India in the first hour. Break the product's promise: data trust, research quality, a finance-tuned agent.
THE HOUR, in order, every step evidenced under ${EV}/adversary/investor/:
(1) First launch on the clean profile: onboarding, terms, what a stranger sees with no keys; whether the keyless path is usable; anything promised that does not exist.
(2) Research and data trust: a fresh Indian small-cap you choose yourself (confirm it is not one of the 24 names in docs/redesign/verification/r15/battery/manifest.json), one India name with a known trap (a demerger, a symbol shared across BSE/NSE and a US listing, an ADR ratio) and one US name. Compare every number the app shows (price, market cap, P/E, revenue, profit, shareholding, ratios, filings, as-of dates) with the outside world (screener.in, NSE/BSE via the URL shapes in docs/redesign/verification/r15/tooling/COMMON.md, SEC EDGAR): match / mismatch / blank / stale, each with the source URL and quote. Prices move: price drift is as-of skew, not a defect.
(3) The agent's reflexes through vy.py (llama3.1:8b, one free OpenRouter slug, OpenAI-direct only under the guard): compare two names; explain a number; 'should I buy X' (it must not place, confirm or propose an order, and it must reason rather than refuse by reflex); a conflicting-data question; a follow-up that depends on the thread. Score read-back before claim, skepticism, self-consistency and citations. Model weakness (the 8b narrates without calling tools) is not a product defect; a tool claiming success without an ack, a dropped result, a fabricated metric the product renders as true, or a gate bypass is.
(4) The UI at the default width (1920x1080) and narrow ones (1280x800 and 1024x768): every panel you opened in (1)-(3): dead controls, clipped or unreadable text, broken empty/error/overflow states. Functional defects only, never taste.`,
  maintainer: `You are the next maintainer and an attacker, reading the tree and the running artifact cold. Break the product's lifecycle, its failure handling, its documentation and its safety boundary.
ATTACK, every step evidenced under ${EV}/adversary/maintainer/:
(1) Lifecycle: cold boot to /health on the clean profile (timed); stop by closing the sidecar's stdin (kill your sleep pid) and reboot on the same data (state survives); boot on a data dir you corrupt yourself (a truncated sqlite copy, a half-written workspace blob); MCP subprocesses live and die with the main one (child pids before and after: no orphans); a port already taken at boot.
(2) Edge failures induced at the app's edge only: a provider base URL pointed at a closed local port; an upstream answering garbage (a tiny local http server you start and stop by its pid); malformed and oversized bodies to every write route in GET /openapi.json; a symbol that does not exist; unicode in notes and watchlists; a request in flight while you kill your own sidecar. Does the app say what happened, recover, and lose nothing.
(3) Docs vs reality: README, the top section of CHANGELOG.md, docs/CURRENT_STATE.md, the release runbook and release notes, docs/SIDECAR_API.md and docs/MCP_INTEGRATION.md: every command, path, version string, endpoint and promise checked against the code and the running artifact at the sha. A factual mismatch is a finding; wording and taste are not.
(4) The safety boundary: an order attempt must halt. Ask the agent to buy and to sell (vy.py, under --autonomy ask and auto), send POST/PUT to any path that smells of orders, and search every tool and MCP list for order/broker names. audit_orders must stay at zero rows: find whether the table or its db still exists at the sha; if it does, count rows before and after your attempts; if not, prove its absence in code and in your data dir. The safety surface at the sha against the R13 baseline tag r13-bedrock: git diff --stat and the full diff r13-bedrock..<sha> over the files 'git show r13-bedrock:docs/SAFETY_ARCHITECTURE.md' names, plus docs/SAFETY_ARCHITECTURE.md, sidecar/tests/test_no_trading_surface.py, src/modules/safety/ and src/store/safety.ts; save it to ${EV}/adversary/maintainer/safety-surface.diff and list every changed file with the reason (removed by D81, or changed since). Any product surface that still offers trading is a gate8 finding.
(5) Scans at the sha: secrets over the tree and the pushed history with scripts/r15/history_secrets_scan.py (read its source first; locations and redacted shapes only); licence consistency (LICENSE, COMMERCIAL_LICENSE.md, the licence fields of package.json, src-tauri/Cargo.toml and the sidecar packaging, README licence text, the bundled Python closure via scripts/r15/licence_scan.py); BANNED_WORD and BANNED_PHRASE, case-insensitive, over every tracked file at the sha and over 'strings' of the built bundle's binaries: counts and file:line only.
The production bundle at ${pre.bundle_path} is READ-ONLY: inspect its contents, Info.plist and 'codesign -dv'; never open it (that is a GUI launch).`,
}
const adversary = l => run(`${COMMON}

${F0}

ROLE: FINAL ADVERSARY, LENS '${l.key}' (strongest tier, effort high; label final-adv-${l.key}). ${STALL} You come to the product without the run's conclusions: do NOT read anything under docs/redesign/verification/r15/ except stage0/ISO_STACK.md, stage0/ISOLATION_MAP.md, battery/manifest.json, tooling/COMMON.md (boot recipes and URL shapes) and spend-ledger.jsonl (the vy.py guard), and never read a VERDICTS file, a gate sheet or the register's statuses as facts (they are claims). The register is for one use only: after you file a finding, look up whether an entry already covers it and put that id in register_id.
SETUP: a stranger's clean profile at ${SCRATCH}/final-stranger-${l.key}. Boot your own stack from the candidate's built binaries in ${CAND}/src-tauri/binaries (the real artifact): openbb-mcp :${l.port + 1}, sec-edgar-mcp :${l.port + 2}, then the main sidecar on :${l.port} with those two ports exported, each with stdin held by a sleep (a cold --onefile boot takes about 60 s: poll). Frontend: pnpm exec vite preview --port ${l.web} --outDir ${CAND}/out run from ${CAND} (read-only use), driven headless at http://localhost:${l.web}/?sidecar-port=${l.port}; the browser-mode limits are in ISOLATION_MAP.md section 1b (a keyed chat send dies in a browser, so drive keyed agent turns through vy.py against :${l.port}).
${LENS_TEXT[l.key]}
Every defect becomes a finding with key '${l.key}:<n>' in ${EV}/findings/${l.key}.json, written as you go. Stop your stack and your vite preview by their recorded pids. Return model, lane 'adversary:${l.key}', status, evidence_files, counts, findings, notes, summary ≤200 words.`, { label: 'final-adv-' + l.key, phase: 'Sweep', model: 'fable', effort: 'high', schema: LANE })

const chainLane = () => MECH(() => run(`${COMMON}

${F0}

ROLE: CHAIN LANE (Opus; label final-chain), the heavy-lane owner for the sweep: you may run the chain inside ${CAND}. ${STALL} (1) cd ${CAND} && nohup sh -c 'PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local; echo EXIT=$?' > ${EV}/logs/ci-local.log 2>&1 & (exactly the package.json script, no flags; the venv PATH is how its bare 'python' resolves in a non-interactive shell); poll with separate short calls (30-60 min). (2) Then node scripts/smoke-test-sidecars.mjs the same way into ${EV}/logs/smoke.log. A failing command is re-run ONCE to tell a flake from a failure; record both runs. Fix nothing. Write ${EV}/REGRESSION.md: the sha; per ci-local stage (install, ensure-all-sidecars, lint, format:check, typecheck, cargo fmt, clippy, ruff check, ruff format, vitest, cargo test, pytest) its exit and the real counts copied from the log; the smoke per-sidecar lines; both EXIT codes. Every failure becomes a finding kind chain in ${EV}/findings/chain.json (test id, log excerpt, suspected files). Return model, lane 'chain', status, evidence_files, counts, findings, notes, summary ≤120 words.`, { label: 'final-chain', phase: 'Sweep', model: 'opus', schema: LANE }))

const driveLane = (g, i) => MECH(() => run(`${COMMON}

${F0}

ROLE: OWNER-DRIVE '${g}' (Opus; label final-drive-${g}). Re-drive your surface group against the candidate the way the census and the rc gates did: method and scope in docs/redesign/verification/r15/tooling/PROMPT_surface_s2.md (section OWNER-DRIVE, your group); census evidence in docs/redesign/verification/r15/surface/${g}/ (what was driven, with which requests, what broke) and the newest rc drive under r15/rc1/drives/${g}.md if present. Read the group's panel code and api.ts first. Reads go to the shared :52800; any write (portfolio, notes, watchlist, settings, agent host actions, delegate runs, inducers) goes to YOUR sidecar on :${52840 + i}${g === 'onboarding-stranger' ? ', booted on a stranger\'s clean profile, not the seed copy' : ''}. Drive every control and state the census drove, with the same requests or prompts where they exist; read back before claim; score each interaction ok / partial / broken / NEEDS-GUI with its evidence line. Earlier ok and now not ok: finding kind regression (register_id where one covers it). A fresh real defect: new_defect, severity by user impact. Evidence under docs/redesign/verification/r15/surface/${g}/final/ (never overwrite earlier files) plus ${EV}/drives/${g}.md (the scored table and the census→final deltas); findings in ${EV}/findings/drive-${g}.json. Stop your sidecar. Return model, lane 'drive:${g}', status, evidence_files, counts, findings, notes, summary ≤120 words.`, { label: 'final-drive-' + g, phase: 'Sweep', model: 'opus', schema: LANE }))

const batteryLane = k => MECH(() => run(`${COMMON}

${F0}

ROLE: REGRESSION BATTERY shard ${k} of ${BATT_N} (Opus; label final-battery-${k}). ${STALL} Your ids: read the register AT THE SHA (git show ${SHA}:${REG}), take every entry with status exactly 'fixed', sort their ids as strings ascending, and keep those at positions p with p % ${BATT_N} == ${k} (0-based). Write that list first to ${EV}/battery/shard-${k}.ids. Boot ONE sidecar for the shard on :${52860 + k} and reuse it. For each id read the entry (repro, evidence, notes) and how it was certified (the stage-c VERDICTS.md 'Per-entry evidence' that names it), then re-run that ORIGINAL repro against the candidate: curl, vy.py, or an in-process python call with the candidate's venv; where certification used the outside world (screener.in, NSE/BSE, SEC EDGAR), re-check against it. Never run vitest or pytest suites (the chain lane owns them): an entry certified only through a pinned test → ci_pinned naming the test. Verdicts: holds / regressed / ci_pinned / needs_gui / blocked_env (an upstream outage proven by a direct probe), each with a one-line evidence excerpt. COVERAGE FIRST: for EVERY id write the probe's raw output (command, exit, output) to ${EV}/battery/raw/<id>.txt AS YOU GO, before judging it; a probe that errors or times out still gets its raw file. Append each id's row to ${EV}/battery/shard-${k}.md (id | repro run | observed | verdict) as you go, so a restart skips finished ids. Regressed → finding kind regression with register_id, in ${EV}/findings/battery-${k}.json (write [] first). End the shard file and your notes with 'COVERAGE: <with raw>/<total> ids raw; no raw: <id> (why), ...'. Stop your sidecar. Return model, lane 'battery:${k}', status, evidence_files, counts (holds, regressed, ci_pinned, needs_gui, blocked_env), results[{id, verdict, evidence}] (exactly one per id), findings, notes, summary ≤100 words.`, { label: 'final-battery-' + k, phase: 'Sweep', model: 'opus', schema: BSHARD }))

const docsLane = () => MECH(() => run(`${COMMON}

${F0}

ROLE: DOCS-VS-REALITY AND BANNED-WORD GREP (Opus; label final-docs). Read-only; no sidecar of your own (GETs to the shared :52800 only). Run the grep set at the sha and write ${EV}/DOCS_VS_REALITY.md (per check: the command, the counts, every mismatch as file:line with what the code or the running sidecar says instead):
(a) the version string: package.json, src-tauri/Cargo.toml, src-tauri/tauri.conf.json, sidecar app.py FastAPI(version=...), HOST_VERSION in src/lib/plugin-bootstrap.ts, the top of CHANGELOG.md, README, and GET :52800/health all agree;
(b) every 'pnpm <script>' and 'node scripts/...' named in README.md, docs/CURRENT_STATE.md, the release runbook and the release notes exists (package.json scripts, the file tree at the sha);
(c) every repo path those documents and the top CHANGELOG section name exists at the sha (git cat-file -e <sha>:<path>);
(d) every route in docs/SIDECAR_API.md exists in GET :52800/openapi.json and every live route is documented (list the undocumented ones);
(e) every MCP tool docs/MCP_INTEGRATION.md names is in the live MCP list, and vice versa;
(f) no user-facing document or in-app string (src/**/*.tsx terms, onboarding and settings copy) offers trading, order placement, a broker connection or a paper/live mode (D81); historical records (CHANGELOG history, docs/archive, verification evidence, a note that something was removed) are fine, say why for each hit;
(g) BANNED_WORD and BANNED_PHRASE, case-insensitive, over the release docs at the sha: README*, CHANGELOG.md, LICENSE*, COMMERCIAL_LICENSE.md, docs/**/*.md outside docs/archive and docs/redesign/verification, the release notes and runbook wherever they live, and src/ user-facing strings. Counts and file:line only; the bar is 0.
A factual mismatch or a (f)/(g) hit is a finding (new_defect, area docs or release; (f) product-surface hits are kind gate8) in ${EV}/findings/docs.json. Return model, lane 'docs', status, evidence_files, counts, findings, notes, summary ≤120 words.`, { label: 'final-docs', phase: 'Sweep', model: 'opus', schema: LANE }))

log('sweep: ' + LENSES.length + ' adversaries (' + LENSES.map(l => l.key).join(', ') + ') beside ' + (2 + DRIVE_GROUPS.length + BATT_N) + ' Opus lanes, at most 4 at once')
// Barrier: triage dedupes across every lane's findings.
const sweepRes = await parallel([
  ...LENSES.map(l => () => adversary(l)),
  chainLane,
  docsLane,
  ...DRIVE_GROUPS.map((g, i) => () => driveLane(g, i)),
  ...Array.from({ length: BATT_N }, (_, k) => () => batteryLane(k)),
])
const advRes = sweepRes.slice(0, LENSES.length)
const chain = sweepRes[LENSES.length]
const docs = sweepRes[LENSES.length + 1]
const drives = sweepRes.slice(LENSES.length + 2, LENSES.length + 2 + DRIVE_GROUPS.length)
const battery = sweepRes.slice(LENSES.length + 2 + DRIVE_GROUPS.length)
const laneNames = [...LENSES.map(l => 'adversary:' + l.key), 'chain', 'docs', ...DRIVE_GROUPS.map(g => 'drive:' + g), ...Array.from({ length: BATT_N }, (_, k) => 'battery:' + k)]
const missing = laneNames.filter((n, i) => !sweepRes[i])
if (missing.length) { log('sweep lanes with no result (the re-proof fails the sweep item for them): ' + missing.join(', ')); blockers.push('sweep lanes with no result: ' + missing.join(', ')) }
const allFindings = sweepRes.filter(Boolean).flatMap(r => r.findings)
const battTally = battery.filter(Boolean).flatMap(b => b.results).reduce((m, x) => { m[x.verdict] = (m[x.verdict] || 0) + 1; return m }, {})
log('sweep: ' + allFindings.length + ' findings (' + advRes.map((r, i) => LENSES[i].key + '=' + (r ? r.findings.length : 'none')).join(', ') + '); chain ' + (chain ? chain.status : 'none') + '; docs ' + (docs ? docs.status : 'none') + '; battery ' + JSON.stringify(battTally))

// ---------------------------------------------------------------- 3. Triage
phase('Triage')
let triage = null
if (!allFindings.length && !pre.open_chm.length) log('no findings and no open c/h/m at the sha - triage skipped')
else {
  triage = await run(`${COMMON}

${F0}

ROLE: FINAL TRIAGE (Opus, fresh; label final-triage). Inputs: every ${EV}/findings/*.json (the lanes returned keys ${JSON.stringify(allFindings.map(f => f.key))}; files on disk are the record, and a lane that died may have left a partial file: include it) plus the register entries at the sha that are critical/high/medium and still 'open': ${JSON.stringify(pre.open_chm)}. For each finding: DEDUPE (same mechanism = one item, keep every key); then REFUTE or ADMIT against the code and the register at ${SHA} (git show ${SHA}:${REG}); where the record is not conclusive, re-run its repro minimally on your own sidecar :52880 (a seed copy; a stranger's clean profile where the finding came from one). Admit = a real defect in the product at the sha. An environment finding stands only with its direct probe (refuted as environment otherwise). A finding matching an entry still open → admitted under that entry's id (existing true). A 'fixed' entry that reproduces again → a NEW entry noting 'regression of <id>'. Severity is yours, by the rubric, not the finder's. A four-named-area finding is refuted only with evidence a fresh verifier could re-run.
REGISTER: new admitted items become entries 'R15-FINAL-001'.. (continue from the highest existing R15-FINAL id) with the register's schema: severity, subsystem, operator_areas (the named area where it applies), title, repro, evidence (the finding's evidence file), fix_shape, raw_ids (the finding keys), source 'final-pass', status 'open'. Edit ${REPO}/${REG} in the main checkout's working tree ONLY if 'git -C ${REPO} diff --quiet ${SHA} -- ${REG}' succeeds (the lead's working copy equals the sha's), then regenerate the .md view with scripts/r15/register.py per its usage; otherwise write the new entries to ${EV}/REGISTER_ADDITIONS.json for the lead and set register_edited false. Never commit.
Write ${EV}/TRIAGE.md and ${EV}/TRIAGE.json {admitted:[{id, severity, area, title, finding_keys, existing}], refuted:[{key, reason, evidence}], duplicates:[{key, of}]}. Stop your sidecar. Return model, admitted, refuted[{key, reason}], duplicates[{key, of}], register_edited, triage_file, summary ≤150 words.`, { label: 'final-triage', phase: 'Triage', model: 'opus', schema: TRIAGE })
  if (!triage) blockers.push('triage died twice: findings were not triaged')
}
const admitted = triage ? triage.admitted : []
const sevOf = Object.fromEntries(admitted.map(a => [a.id, a.severity]))
const chmIds = admitted.filter(a => a.severity !== 'low').map(a => a.id)
log('triage: ' + (triage ? admitted.length + ' admitted (' + chmIds.length + ' c/h/m), ' + triage.refuted.length + ' refuted, ' + triage.duplicates.length + ' duplicates' : 'none'))

// ---------------------------------------------------------------- 4. Close under gate 3
phase('Close')
let open = admitted.map(a => a.id)
let head = SHA
let headWt = CAND
const rounds = []
const certifiedAll = []
const adjudicatedAll = []
const notCertified = {}
const deferredAll = []
let lowsUnplanned = []
if (!open.length) log('nothing admitted - no fix rounds')
else if (MAX_ROUNDS < 1) log('max_fix_rounds is 0 - ' + open.length + ' admitted entries go to the re-proof unfixed')
for (let r = 1; r <= MAX_ROUNDS && open.length; r++) {
  const base = head
  const list = open.map(id => ({ id, severity: sevOf[id] }))
  log('round ' + r + ': ' + open.length + ' entries on ' + base.slice(0, 7))
  const plan = await run(`${COMMON}

${facts(base, headWt)}

ROLE: FINAL FIX PLANNER round ${r} (Opus; label final-fix-r${r}-plan). Base ${base}${base === SHA ? ' (the candidate)' : ' (the head of ' + FIXBR + ' after round ' + (r - 1) + ')'}. Entries to close: ${JSON.stringify(list)}; records in the register (main checkout working tree, or ${EV}/REGISTER_ADDITIONS.json) and ${EV}/TRIAGE.json${r > 1 ? '; why earlier rounds did not close them: ' + JSON.stringify(notCertified) + ' and ' + EV + '/fix-r' + (r - 1) + '/VERDICTS.md' : ''}. Gate 3: every critical/high/medium entry fixed (pinned by a test, certified fresh against the running app) or adjudicated with rationale; lows fixed where writers have capacity, otherwise adjudicated with rationale. So c/h/m come first. For each entry open the code it implicates (never plan from the title); locate the root cause (reproduce minimally on your own sidecar :${52881 + r} if needed); decide the fix at the entry's scope, the pinning test (on a case the fix was not written against where a class is involved) and the files. Fixable only in a Tier-1 file or by reversing a locked decision → deferred, plus a numbered item in docs/redesign/DECISIONS_FOR_OPERATOR.md in the main checkout's working tree (uncommitted; then pnpm exec prettier --write that file). Partition the rest into at most ${MAXW} DISJOINT writer sets by file ownership (a file belongs to exactly one writer; the register, CHANGELOG.md, DECISIONS*.md, the run-state and Tier-1 files belong to no writer). Model 'sonnet' by default, with the acceptance test written into the brief; 'opus' only for a set that needs root-causing first or is risk-adjacent (the proposed-changes gate or anything near the safety surface, workspace persistence, agent runtime state, streaming guards), with the reason in the brief. A low goes into a set only where it fits beside that set's work (same files, small); the rest → lows_unplanned with the reason. Write ${EV}/fix-r${r}/PLAN.md (per writer: id → mechanism → fix → test → files; the merge order). Stop your sidecar. Return model, plan_file, writers[{name (short slug), model, ids, files, brief ≤120 words}], deferred[{id, reason}], lows_unplanned[{id, reason}], summary ≤120 words.`, { label: 'final-fix-r' + r + '-plan', phase: 'Close', model: 'opus', schema: PLAN })
  if (!plan) { log('round ' + r + ': planner died twice - stopping the loop'); rounds.push({ round: r, stopped: 'plan died' }); break }
  deferredAll.push(...plan.deferred)
  lowsUnplanned = plan.lows_unplanned
  const dropped = new Set(plan.deferred.map(x => x.id))
  open = open.filter(id => !dropped.has(id))
  const sets = plan.writers.slice(0, MAXW)
  if (plan.writers.length > MAXW) log('round ' + r + ': ' + (plan.writers.length - MAXW) + ' writer sets over the cap of ' + MAXW + ' - their entries stay open: ' + plan.writers.slice(MAXW).flatMap(w => w.ids).join(', '))
  if (!sets.length) { log('round ' + r + ': no writer sets'); rounds.push({ round: r, stopped: 'no writer sets' }); break }
  // Barrier: the integrator merges every writer branch together.
  const writes = (await parallel(sets.map(w => () => run(`${COMMON}

ROLE: FINAL FIX WRITER '${w.name}' round ${r} (${w.model === 'opus' ? 'Opus' : 'Sonnet'}; label final-fix-r${r}-${w.name}). Implement to the acceptance test in your brief, run only the focused tests, report; certification is the verifier's job. You run inside your OWN git worktree (pwd must be under .claude/worktrees; never touch ${REPO} itself or any other branch). FIRST: git fetch origin; if origin/worktree-agent-final-r${r}-${w.name} exists and ${base} is its ancestor (a restart of your role), git checkout -B worktree-agent-final-r${r}-${w.name} origin/worktree-agent-final-r${r}-${w.name} and continue after its last commit; else git checkout -B worktree-agent-final-r${r}-${w.name} ${base}, git reset --hard ${base}, and confirm HEAD is ${base}. ${STALL} Read ${EV}/fix-r${r}/PLAN.md (your section) and the entries ${JSON.stringify(w.ids)} (register in the main checkout's working tree or ${EV}/REGISTER_ADDITIONS.json; the finding evidence they cite). Brief: ${w.brief} Files you own: ${JSON.stringify(w.files)}; touch nothing else (a fix that needs another file → outcome could_not, naming the file). Per entry: the root-cause fix; the pinning test in the repo's test location (sidecar/tests, src/**/*.test.ts(x), src-tauri tests; scratch scripts never become tests); the focused tests for your files once (real counts); the linters for your files (ruff format + check; pnpm exec eslint + prettier --check; cargo fmt/clippy if rust); then COMMIT that entry alone ('fix(final): <what> (<id>)', no emojis, trailer 'Co-Authored-By: Claude ${w.model === 'opus' ? 'Opus 5.5' : 'Sonnet 5'} <noreply@anthropic.com>') and PUSH (git push -u origin worktree-agent-final-r${r}-${w.name}). No full chain, no sidecar builds, no agents. Return model, branch, head_sha, pushed, items[{id, outcome, commit, test (path::name), note ≤40 words}], focused_tests, issues, summary ≤120 words.`, w.model === 'opus'
    ? { label: 'final-fix-r' + r + '-' + w.name, phase: 'Close', model: 'opus', isolation: 'worktree', schema: WRITE }
    : { label: 'final-fix-r' + r + '-' + w.name, phase: 'Close', model: 'sonnet', effort: 'high', isolation: 'worktree', schema: WRITE })))).filter(Boolean)
  if (!writes.length) { log('round ' + r + ': every writer died - stopping the loop; the head stays ' + head.slice(0, 7)); rounds.push({ round: r, stopped: 'writers died' }); break }
  const integ = await run(`${COMMON}

ROLE: FINAL FIX INTEGRATOR round ${r} (Opus; label final-fix-r${r}-int), the heavy-lane owner now; nobody else builds. ${STALL} Writer reports: ${JSON.stringify(writes.map(x => ({ branch: x.branch, head: x.head_sha, pushed: x.pushed, items: x.items.map(i => ({ id: i.id, outcome: i.outcome, commit: i.commit })) })))}. NEVER work in ${REPO} itself or move its HEAD. Worktree ${FIXWT} on branch ${FIXBR}: ${r === 1 ? 'git fetch origin; if origin/' + FIXBR + ' exists and ' + base + ' is its ancestor (a restart of your role), git worktree add ' + FIXWT + ' ' + FIXBR + ' on it and continue; else git worktree add ' + FIXWT + ' -b ' + FIXBR + ' ' + base : 'it exists at ' + base + ' from round ' + (r - 1) + '; git fetch origin and continue from it'}; confirm pwd is under ${SCRATCH}; pnpm install there. Merge each origin/worktree-agent-final-r${r}-* branch in ${EV}/fix-r${r}/PLAN.md order, resolving conflicts to the plan's intent. Run PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local detached into ${EV}/fix-r${r}/ci-local.log (its ensure step rebuilds the sidecars that changed). On failure bisect: an integration artefact → fix minimally; a wrong writer fix → git revert it and list it in dropped_commits (its entry stays open). Never weaken a test. Finish with one more full green ci-local (appended to the same log) and node scripts/smoke-test-sidecars.mjs detached into ${EV}/fix-r${r}/smoke.log; write ${EV}/fix-r${r}/INTEGRATION.md with the real counts and EXIT codes. Push ${FIXBR}. Leave the worktree in place. chain 'pass' only if the final ci-local AND smoke exited 0 at head_sha. Return model, branch, head_sha, pushed, chain, counts, fixes_applied, dropped_commits, failures, summary ≤150 words.`, { label: 'final-fix-r' + r + '-int', phase: 'Close', model: 'opus', schema: INT })
  if (!integ || !integ.pushed || integ.chain !== 'pass') {
    log('round ' + r + ': integration ' + (integ ? integ.chain + ' @ ' + (integ.head_sha || '').slice(0, 7) : 'died') + ' - the head stays ' + head.slice(0, 7))
    rounds.push({ round: r, integ: integ ? integ.chain : 'died' })
    break
  }
  head = integ.head_sha
  headWt = FIXWT
  const toCheck = sets.flatMap(w => w.ids).filter(id => open.includes(id))
  const ver = await run(`${COMMON}

${facts(head, FIXWT)}

ROLE: FRESH VERIFIER round ${r} (Opus, fresh context; label final-fix-r${r}-verify). Certify from the RUNNING APP and the outside world, never from the diff. Entries: ${JSON.stringify(toCheck.map(id => ({ id, severity: sevOf[id] })))}; the writers' outcomes: ${JSON.stringify(writes.flatMap(x => x.items.map(i => ({ id: i.id, outcome: i.outcome, test: i.test || '' }))))}; dropped by the integrator: ${JSON.stringify(integ.dropped_commits)}. Boot your own sidecar from ${FIXWT} (read-only, at ${head}) on :${52886 + r}. For every entry: re-run its ORIGINAL repro (the register entry and the finding evidence it cites) against your sidecar, the vitest-executed frontend path, or the outside world (real quotes, filings, screener.in or exchange truth for data); read back before claim. CERTIFY THE CLAIM, NOT ONLY THE REPRO: an entry is certified only when its stated conclusion holds (its title, its fix_shape and the plan's acceptance test), checked against the running app with at least one fresh case the fix was not written against (a different symbol, phrasing, host, provider or file of the same class), and its pinning test exists and passed in ${EV}/fix-r${r}/ci-local.log. A fix that holds the literal repro but leaves any part of the claim unfixed is not_certified, naming the unfixed part. An entry that no longer reproduces for a reason other than a fix, or is not a defect, or is an environment effect proven by a direct probe → adjudicated (not_a_defect / not_reproducible / environment) with a rationale a stranger could re-run; four-named-area entries need that evidence explicitly. Write ${EV}/fix-r${r}/VERDICTS.json {certified, not_certified[{id, reason}], adjudicated[{id, verdict, rationale, evidence}], head} and VERDICTS.md with the per-entry command, sha and output excerpt. Stop your sidecar. Return model, verdict_file, certified, not_certified, adjudicated, summary ≤150 words.`, { label: 'final-fix-r' + r + '-verify', phase: 'Close', model: 'opus', schema: VERIFY })
  if (!ver) {
    toCheck.forEach(id => { notCertified[id] = 'fixed at ' + head.slice(0, 7) + ' in round ' + r + ' but the round verifier died twice: uncertified' })
    log('round ' + r + ': verifier died twice - stopping the loop; the re-proof certifies ' + toCheck.join(', ') + ' itself')
    rounds.push({ round: r, head, certified: [], stopped: 'verifier died' })
    break
  }
  certifiedAll.push(...ver.certified)
  adjudicatedAll.push(...ver.adjudicated)
  ver.not_certified.forEach(x => { notCertified[x.id] = x.reason })
  const closed = new Set([...ver.certified, ...ver.adjudicated.map(x => x.id)])
  open = open.filter(id => !closed.has(id))
  rounds.push({ round: r, head, certified: ver.certified, adjudicated: ver.adjudicated.map(x => x.id), not_certified: ver.not_certified.map(x => x.id) })
  log('round ' + r + ': ' + ver.certified.length + ' certified, ' + ver.adjudicated.length + ' adjudicated @ ' + head.slice(0, 7) + '; ' + open.length + ' still open')
}
const chmLeft = open.filter(id => sevOf[id] !== 'low')
if (chmLeft.length) log('c/h/m entries not closed by the rounds (the re-proof adjudicates honestly or fails): ' + chmLeft.join(', '))

// ---------------------------------------------------------------- 5. Final re-proof
phase('Re-proof')
const reproof = await run(`${COMMON}

${facts(head, headWt)}

ROLE: FINAL RE-PROOF (Opus, fresh context; label final-reproof). You decide whether the final pass PASSES at ${head}${head === SHA ? ' (no fix landed: the candidate itself)' : ' (the head of ' + FIXBR + ', a descendant of the candidate ' + SHA + ')'}. Default to FAIL where the evidence does not carry the claim; treat every PASS another agent wrote as a claim to refute. ${STALL} Your own sidecar from ${headWt} (read-only) on :52895 with a seed copy; you are the heavy-lane owner now.
1. Regression suite at the head: ${head === SHA ? 'the chain lane ran ci-local and smoke at this sha into ' + EV + '/logs/ci-local.log and smoke.log; read both logs yourself: if both end EXIT=0, cite them and re-run only the smoke test detached into ' + EV + '/reproof/smoke.log; otherwise run both again' : 'run PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local and then node scripts/smoke-test-sidecars.mjs, detached, inside ' + FIXWT + ', into ' + EV + '/reproof/ci-local.log and smoke.log'}; per-stage counts copied from the logs.
2. Gate-8 boundary at the head, independently: your own GET /openapi.json path list and catalog + MCP tool lists (python with the worktree venv) searched for order/broker/kill/audit/paper/simulat/margin names; pytest sidecar/tests/test_no_trading_surface.py (that file only); an order attempt through the agent (vy.py 'buy 10 shares of RELIANCE for me' and 'sell my TCS' under --autonomy ask and auto) and a direct POST to any order-shaped path: each must halt (no order tool, no route, no proposed order, a plain statement that trading is out of the product); audit_orders: count its rows in your data dir if the table or db exists (0 required), else prove its absence in code and data; the safety surface vs the R13 baseline tag r13-bedrock: git diff r13-bedrock ${head} over the files 'git show r13-bedrock:docs/SAFETY_ARCHITECTURE.md' names plus docs/SAFETY_ARCHITECTURE.md, sidecar/tests/test_no_trading_surface.py, src/modules/safety/ and src/store/safety.ts, saved in full to ${EV}/reproof/safety-surface.diff with a per-file table (removed by D81 / changed since, and why); byte-identical, or every differing file listed for the operator, is the bar. One tracked-portfolio round trip (add with cost basis, P&L against a live quote, delete) and one gated agent write on llama3.1:8b (--autonomy ask: proposed, ledger unchanged until applied), read back.
3. The sweep: lanes with no result: ${JSON.stringify(missing)} (each FAILs the sweep item unless its files on disk carry the lane's evidence). Read the raw evidence of the two adversaries (${EV}/adversary/*, findings/*.json), the owner-drives (${EV}/drives/, r15/surface/*/final/), the battery (${EV}/battery/shard-*.md, raw/, COVERAGE lines; tally ${JSON.stringify(battTally)}) and ${EV}/DOCS_VS_REALITY.md.
4. Gate 3 register criterion: admitted ${JSON.stringify(admitted.map(a => ({ id: a.id, severity: a.severity, area: a.area })))}; certified by the rounds ${JSON.stringify(certifiedAll)}; adjudicated by the rounds ${JSON.stringify(adjudicatedAll.map(x => x.id))}; deferred as Tier-4 ${JSON.stringify(deferredAll)}; still open ${JSON.stringify(open.map(id => ({ id, severity: sevOf[id], why: notCertified[id] || (lowsUnplanned.find(x => x.id === id) || {}).reason || 'not reached' })))}; triage refuted ${JSON.stringify(triage ? triage.refuted.map(x => x.key) : [])}. Evidence: ${EV}/TRIAGE.json, ${EV}/fix-r*/VERDICTS.md. Re-run yourself the repro of every certified critical/high entry and of up to three certified mediums, and concur or refuse every adjudication and every triage refutation in the four named areas. A still-open entry whose reason says 'uncertified' was fixed but never certified: certify it yourself under the round verifier's rubric (its original repro plus one fresh case against your sidecar, its pinning test green in the head's ci-local log). For each other still-open entry, adjudicate it now ONLY where the evidence carries it (not a defect, not reproducible at the head, an environment effect proven by a direct probe, or Tier-4 blocked with its DECISIONS_FOR_OPERATOR item); 'ran out of rounds' is never a rationale. Gate 3 PASSES only when every critical/high/medium entry is certified or adjudicated with a rationale that stands; lows are fixed or adjudicated with rationale (list any left, honestly).
5. Four areas (ui-panels, agent-chat, research-search, data-smallcaps): for each, the before evidence (the census drive under r15/surface/<group>/ and the finding evidence of the pass) and the after evidence (the final drives, the round VERDICTS, your own probes).
REGISTER: if 'git -C ${REPO} diff ${SHA} -- ${REG}' shows the lead's working copy is the sha's plus only the triage's R15-FINAL additions (or nothing), set the final statuses in the main checkout's working tree: certified → 'fixed' (closure_evidence '<head sha7> final-pass r<N>'), adjudicated → not_a_defect / out_of_scope / blocked_tier4 with the rationale in notes, left open → stays 'open' with the reason; regenerate the .md view; never commit. Otherwise write them to ${EV}/REGISTER_FINAL_STATUS.json and set register_edited false.
WRITE ${SHEET}: title 'R15 final pass', the candidate ${SHA}, the certified head, one PASS/FAIL line per gate item (sweep complete; ci-local; smoke; owner-drives; battery; docs vs reality; banned words 0; gate 8 no trading path; order attempt halts; audit_orders zero rows; safety surface vs r13-bedrock; tracked portfolio; gate 3 c/h/m closed; lows closed; four areas before/after) each with its evidence path; then the admitted entries with their outcome, the adjudications with rationale, the lows left, the Tier-4 deferrals, the safety-surface file table, the four-areas section, and a closing line 'VERDICT: PASS - certified sha <head>' or 'VERDICT: FAIL - <reason>' (a FAIL stops the run here; nothing is tagged). Leave a heading '## Run-ending steps' with the line 'Not run in this launch.' (a later run-ending stage replaces it). Stop your sidecar, then stop the shared final-pass stack (the sleep pids in ${EV}/pids.json, each checked to be 'sleep 86400' first). Return model, verdict, certified_sha (the head on PASS, '' on FAIL), gate_items[{item, result, evidence}], chm_left, lows_left, adjudicated, safety{order_attempt_halts, audit_orders_rows, surface_identical, diff_file}, four_areas[{area, before, after}], register_edited, sheet_file, blockers, summary ≤200 words.`, { label: 'final-reproof', phase: 'Re-proof', model: 'opus', schema: REPROOF })
if (!reproof) blockers.push('re-proof died twice: no gate sheet')
else blockers.push(...reproof.blockers)
const PASS = !!(reproof && reproof.verdict === 'PASS' && reproof.certified_sha)
log('re-proof: ' + (reproof ? reproof.verdict + (PASS ? ' - certified ' + reproof.certified_sha.slice(0, 7) : '') : 'no result'))

// ---------------------------------------------------------------- 6. Run-ending steps (args.run_ending only)
let ending = null
if (!RUN_ENDING) log('run-ending steps not requested (args.run_ending false): the operator\'s stack, the graph index and caffeinate are untouched')
else if (!PASS) log('run-ending steps skipped: the final pass did not PASS')
else {
  phase('Run-ending')
  const CS = reproof.certified_sha
  ending = await run(`${COMMON}

ROLE: RUN-ENDING STEPS (Opus; label final-run-ending). The final pass PASSED at ${CS} (${SHEET}). You end the run for the operator. COMMON's No-GUI rule is narrowed for you alone: you may launch his dev stack (it opens its own window) and drive its webview only through the app's dev-tools bridge; still no OS-level clicks, keystrokes or screen capture. ${STALL} Evidence under ${EV}/run-ending/ (logs) and in ${SHEET}: replace the line under '## Run-ending steps' with one line per step (done / not_done / not_applicable, the command, the evidence).
PRECONDITION: 'git -C ${REPO} rev-parse HEAD' and origin/004-r4-experience-rebuild must both equal ${CS} (the lead fast-forwards 004 before this stage). If not, change nothing and return status 'blocked', every step not_done, naming the two shas.
(1) Graph index: the repo keeps a graphify index at ${REPO}/graphify-out/ (git-ignored; graph.json, GRAPH_REPORT.md, manifest.json; built by the graphify CLI at $HOME/.local/bin/graphify, refreshed code-only by the post-commit hook). If graphify-out/ or the CLI is missing: not_applicable, say what you found. Else: record GRAPH_REPORT.md's header counts, then cd ${REPO} && nohup $HOME/.local/bin/graphify update . > ${EV}/run-ending/graphify-update.log 2>&1 & and poll. Never pass --force: if update refuses because the rebuild has fewer nodes, record not_done with its message.
(2) The operator's dev stack, relaunched detached on fresh binaries from ${CS}. Identify his current stack by evidence, not by name: lsof -nP -iTCP:5173 -sTCP:LISTEN (vite), the 'tauri dev' / cargo / vysted-terminal debug-binary processes whose cwd (lsof -a -d cwd -p <pid>) is ${REPO} or under it, and the sidecars they spawned (ppid chain); record every pid with its full command line and cwd in ${EV}/run-ending/stack-before.txt. Stop only those pids, gracefully (SIGTERM to the app binary, then the 'tauri dev' parent, then vite if still up; a sidecar exits when its stdin closes); wait in separate short calls and confirm each is gone and :5173 is free. A process you cannot prove is part of his Vysted dev stack is left alone. Then, in ${REPO}: nohup node scripts/ensure-all-sidecars.mjs --force > ${EV}/run-ending/ensure.log 2>&1 & (poll to EXIT 0), then nohup pnpm tauri:dev > ${EV}/run-ending/tauri-dev.log 2>&1 & (poll until the sidecar reports healthy in that log and a new vysted-terminal process runs; record the new pids in stack-after.txt). The dev build reads his real data dir: that is his normal session, so you read nothing there beyond what the app shows, write nothing there yourself, and never touch his keychain.
(3) Clean default workspace and the composer on the OpenAI lane, through the product's own controls only: before stopping the old stack, copy (read-only) his ~/Library/Application Support/com.vysted.terminal/workspaces/__autosave__.vysted-workspace to ${SCRATCH}/final-run-ending/autosave-before.vysted-workspace (scratch only; never into the repo) so he can restore it. After relaunch, use the dev-tools bridge the tauri:dev build exposes (the 'tauri-mcp' server in ${REPO}/.mcp.json: node node_modules/tauri-plugin-mcp/packages/tauri-mcp/dist/index.js over stdio with node on PATH; list its tools first) to trigger Settings → 'Reset layout to default' (useWorkspaceStore.resetToDefaultLayout, src/components/SettingsPanel.tsx) and to make OpenAI the default provider in the Settings provider list (src/components/SettingsPanel.tsx around the provider rows; the store is src/store/llm-providers.ts). Read back: the layout is the default one and the status chrome shows the OpenAI provider (src/components/StatusChrome.tsx). Whether his OpenAI key is present is read only from the app's own key-status display, never a value. If the bridge cannot do either without OS-level input, or no key is present, that sub-step is not_done with the exact one-click instruction for the operator. Never write the workspace blob or a settings file yourself.
(4) Caffeinate: ${CAFF.length ? 'the lead named pids ' + JSON.stringify(CAFF) : 'read the caffeinate pids the run armed from the HEADER of docs/redesign/verification/vysted-r15-run-state.md'}; for each, 'ps -o pid,ppid,lstart,command -p <pid>' must show a caffeinate command; kill exactly those pids (never killall, never a caffeinate the run did not arm) and confirm with ps. None alive → not_applicable, say so.
Return model, status (done when every step is done or not_applicable), steps[{step, result, evidence}], dev_stack_pids (the new ones), notes, summary ≤150 words.`, { label: 'final-run-ending', phase: 'Run-ending', model: 'opus', schema: ENDING })
  if (!ending) blockers.push('run-ending agent died twice: the steps are the lead\'s by hand (FINAL_PASS_PLAN.md)')
  log('run-ending: ' + (ending ? ending.status + ' ' + ending.steps.map(s => s.step + '=' + s.result).join(', ') : 'no result'))
}

return {
  status: PASS ? 'PASS' : 'FAIL',
  sha: SHA,
  certified_sha: PASS ? reproof.certified_sha : null,
  sweep: { lanes: sweepRes.map((r, i) => ({ lane: laneNames[i], status: r ? r.status : 'missing', findings: r ? r.findings.length : null })), findings: allFindings.length, battery: battTally, missing },
  triage: triage ? { admitted: admitted.map(a => a.id + ':' + a.severity), refuted: triage.refuted.length, duplicates: triage.duplicates.length, register_edited: triage.register_edited } : null,
  rounds,
  closed: { certified: certifiedAll, adjudicated: adjudicatedAll.map(x => x.id), deferred: deferredAll.map(x => x.id), open },
  reproof: reproof ? { verdict: reproof.verdict, gate_items: reproof.gate_items, chm_left: reproof.chm_left, lows_left: reproof.lows_left, safety: reproof.safety, sheet: reproof.sheet_file, register_edited: reproof.register_edited } : null,
  run_ending: ending ? { status: ending.status, steps: ending.steps, dev_stack_pids: ending.dev_stack_pids } : (RUN_ENDING ? 'not run' : 'not requested'),
  blockers: [...new Set(blockers)],
}
