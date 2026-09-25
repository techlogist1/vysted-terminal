export const meta = {
  name: 'r15-rc1-gate',
  description: 'R15 rc1 gate: preflight + clean build at the candidate, Gate 8 proof (no trading path, tracked portfolio intact), regression suite in lanes (ci-local, smoke, agent scenarios, owner-drives, fixed-name battery in <=8 shards, data packs), bounded fix loop, GUI round for needs_gui when the operator is away, fresh adversarial verifier writes R15_GATE_RC1.md',
  whenToUse: 'Once the R15 Stage C fix batches are merged on 004-r4-experience-rebuild; args {sha, max_fix_rounds, skip_gui}',
  phases: [
    { title: 'Preflight', detail: 'git, shared stack, clean sidecar build at the candidate' },
    { title: 'Gate 8', detail: 'no order/broker/simulated-account path; tracked portfolio e2e' },
    { title: 'Regression', detail: 'ci-local + smoke, scenarios, owner-drives, battery shards, data packs' },
    { title: 'Fix', detail: 'triage (Opus), writers (Sonnet default, Opus for risk-adjacent fixes), integrator (Opus), recheck (Opus), bounded rounds' },
    { title: 'GUI', detail: 'needs_gui entries, only while the operator is away' },
    { title: 'Verify', detail: 'fresh adversarial verifier, gate sheet, tag sha' },
  ],
}

const A = args || {}
const LEADNOTE = A.note ? '\n\nLEAD NOTE FOR THIS RUN (applies to every role; it adds to the rules above, never relaxes lanes or secrets): ' + String(A.note) : ''
const REPO = '/Users/lokavyasingh/Documents/dev/vysted-terminal'
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const MAX_ROUNDS = A.max_fix_rounds == null || !Number.isInteger(+A.max_fix_rounds) ? 2 : Math.max(0, +A.max_fix_rounds)
const SKIP_GUI = A.skip_gui === true || A.skip_gui === 'true'
const GUI_WAIT_MIN = +A.gui_wait_min > 0 ? +A.gui_wait_min : 60
const EV = REPO + '/docs/redesign/verification/r15/rc1'
const ISO = SCRATCH + '/vysted-iso'
const CAND = SCRATCH + '/rc1-cand'
const SEED = SCRATCH + '/rc1-seed-data'
const DRIVE_GROUPS = Array.isArray(A.drive_groups) && A.drive_groups.length ? A.drive_groups : ['composer-chat', 'research-briefs', 'screener', 'panels-layouts', 'portfolio-notes', 'settings-plugins', 'onboarding-stranger', 'failure-inducer']
const intArg = (k, d) => { const v = A[k] == null ? d : +A[k]; if (!Number.isInteger(v) || v < 1 || v > 16) throw new Error('args.' + k + ' must be an integer 1..16, got ' + A[k]); return v }
const IDLE_CMD = "ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'"
const FRONT_CMD = 'lsappinfo info -only name $(lsappinfo front)'

// Pacing law: at most 6 agents at once, whatever the machine's CPU count.
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
const GLOBAL = limiter(32)
const once = (prompt, opts) => GLOBAL(() => agent(prompt, opts)).catch(e => { log('agent ' + opts.label + ' failed: ' + e); return null })
// Routing change 5: Sonnet is the default (clear spec, checkable output), Opus for refutation/root-causing/integration/certification; a wave that dies or starves gets ONE same-tier retry, never a third try.
const run = (prompt, opts) => once(prompt, opts).then(r => r ? r : (log('agent ' + opts.label + ' on ' + opts.model + ' returned nothing (wave died or starved) - routing 5: same-tier retry, never a third try'), once(prompt, { ...opts, label: opts.label + '-retry' })))

const COMMON = `Repo: ${REPO}, integration branch 004-r4-experience-rebuild. The operator is away; never ask, decide and record. Before any pnpm/node/cargo command: export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH. Never print or copy a secret; never read docs/redesign/verification/R15_BRIEF*.md or r15/local/. No GUI. Do not edit CLAUDE.md, src-tauri/tauri.conf.json, .github/, LICENSE*, types/plugin.ts, r15-fanout.js. Trading is out of the product (D81, merged as the newest 'feat(d81)' merge commit on 004) — never re-add any of it. Never tag, merge to main, push main, open a PR or force-push. Tests are state: never delete, skip or weaken a test to get green; if a test is wrong, fix it and log why; never special-case code to satisfy a test. Never speculate about code you have not opened. Fix root causes, not symptoms; where a defect class shows up twice, fix the class and pin it with a test on a case the fix was not written against. Deliver what the register entry asks at the scope intended — no refactoring beyond it, no abstractions, flags or defensive code for cases that cannot happen; pre-existing oddities outside the entry go to issues[], not into the diff. Commit tests only where the repo keeps them (sidecar/tests, src/**/*.test.ts(x), src-tauri tests), one focused test per pinned behaviour; scratch scripts never become permanent tests. The register: docs/redesign/verification/vysted-r15-register.json (entries with id, title, severity, tags/operator_areas, subsystem, repro, evidence, raw_ids, status). HARNESS STALL RULE (a 3-minute no-progress watchdog kills the agent and restarts it from scratch; batch 6 lost 9 hours to it): NO single tool call may run longer than ~120 s. Anything longer (pnpm install, pnpm ci-local, full pytest/vitest, cargo, PyInstaller/sidecar builds, pnpm tauri build, the smoke test, sidecar boots, vy.py agent runs, soak waits, curl loops) MUST be started detached — 'nohup <cmd> > <log> 2>&1 &' or the Bash tool's run_in_background — and then polled with SEPARATE short calls ('sleep 60; tail -n 5 <log>'), never an 'until … sleep' loop inside one call, never a foreground pytest of the whole suite. Keep emitting a tool call at least every 2 minutes. If you find files, branches or a worktree from a previous attempt of your own role (a restart), read them and CONTINUE from them instead of redoing the work. LOCAL-MODEL LOCK: the local model (Ollama) is a single lane shared by every agent in this run. Wrap EVERY call that reaches it (vy.py --provider ollama, a sidecar agent run on an Ollama model, any request to :11434) in a lock: in separate short calls, try 'mkdir /tmp/vysted-r15-ollama.lock 2>/dev/null' every 5 s (at most ~100 s of retries per tool call) for up to 15 min in total; a lock dir older than 20 min is stale ('find /tmp/vysted-r15-ollama.lock -maxdepth 0 -mmin +20' prints it) and may be removed with rmdir. Holding it, run the call so the lock is released on success AND failure, e.g. nohup sh -c 'trap "rmdir /tmp/vysted-r15-ollama.lock" EXIT INT TERM HUP; <the call>' > <log> 2>&1 & (then poll). One call per lock hold. A call that could not get the lock in 15 min is recorded as 'lock_timeout' (a harness cause), never as a product failure. Your final text IS the return value: return only the structured object.${LEADNOTE}`
const STALL = 'STALL RULE, this role: every install, build, test run, sidecar boot and vy.py run below starts detached (nohup ... > <log> 2>&1 &) and is polled in separate short calls; no single tool call over ~120 s.'

const facts = (sha, wt) => `RC1 GATE FACTS. Candidate sha ${sha}; its scratch worktree ${wt} (sidecars freshly built, sidecar/.venv present). It is READ-ONLY for you unless your role says otherwise: boot sidecars from its source, never edit, install or build in it. Seed data ${SEED} (keyless isolated-profile snapshot): cp -R it to ${SCRATCH}/rc1-data-<your label> and boot your own sidecar on that copy. The operator's ~/Library/Application Support/com.vysted.terminal and his running app are never touched. Shared stack: main :52152 (candidate source) + openbb-mcp :52153 + sec-edgar-mcp :52154 — shared READ-ONLY (GETs and read-only agent runs; never restart it, never write through it). Own sidecar: the 'Main sidecar, from source' block of docs/redesign/verification/r15/stage0/ISO_STACK.md with cwd <worktree>/sidecar, your port and your data dir, started detached; record its sleep pid; poll /health in separate calls; stop it by killing ITS sleep pid only — never a blanket kill, never another owner's port. Models: local llama3.1:8b via Ollama first (python3 scripts/r15/vy.py invoke copilot '<prompt>' --port <p> --provider ollama --model llama3.1:8b); one free OpenRouter slug second; OpenAI-direct ONLY through vy.py under its spend guard (it refuses at $7.50 of the $8.00 cap; read r15/spend-ledger.jsonl first). Evidence root ${EV} (mkdir -p as needed). Write your working log to ${EV}/logs/<your label>.md and EVERY finding to ${EV}/findings/<your label>.json as a JSON array of {key, kind, severity, register_id, title, repro, evidence_file, suspected_files}: key '<your label>:<n>'; kind regression (a fixed/certified behaviour no longer holds), new_defect (real, not in the register), chain (a ci-local/smoke failure), gate8 (a trading path, or a broken tracked-portfolio step), environment (an upstream outage proven by a direct probe; not a product defect).`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }
const NUM = { type: 'number' }
const BOOL = { type: 'boolean' }
const STRS = { type: 'array', items: STR }
const OBJ = { type: 'object' }
const FINDING = S({ key: STR, kind: { type: 'string', enum: ['regression', 'new_defect', 'chain', 'gate8', 'environment'] }, severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }, register_id: STR, title: STR, evidence_file: STR }, ['key', 'kind', 'severity', 'title', 'evidence_file'])
const KEYED = { type: 'array', items: S({ key: STR, reason: STR }) }

const PRE = S({ model: STR, status: { type: 'string', enum: ['ready', 'blocked'] }, sha: STR, build_log: STR, stack_ok: BOOL, ollama_llama31: BOOL, searxng: STR, disk_free_gb: NUM, idle_s: NUM, frontmost: STR, status_counts: OBJ, open_chm: STRS, needs_gui: STRS, blocked_tier4: STRS, blockers: STRS, notes: STRS, summary: STR })
const LANE_P = { model: STR, lane: STR, status: { type: 'string', enum: ['pass', 'fail', 'partial', 'blocked'] }, evidence_files: STRS, counts: OBJ, findings: { type: 'array', items: FINDING }, notes: STRS, summary: STR }
const LANE = S(LANE_P)
const BSHARD = S({ ...LANE_P, results: { type: 'array', items: S({ set: STR, id: STR, verdict: { type: 'string', enum: ['holds', 'regressed', 'ci_pinned', 'needs_gui', 'blocked_env'] }, evidence: STR }) } })
const INDEX = S({ model: STR, sets: { type: 'array', items: S({ batch: STR, set: STR, entries: STRS, shard: NUM }) }, fixed_total: NUM, id_shard: OBJ, unplanned_fixed: NUM, index_file: STR, summary: STR })
const COLLATE = S({ model: STR, files_written: STRS, missing: STRS, battery_status: { type: 'string', enum: ['complete', 'incomplete'] }, no_raw: KEYED, summary: STR })
const TRIAGE = S({ model: STR, plan_file: STR, writers: { type: 'array', items: S({ name: STR, model: STR, keys: STRS, files: STRS, brief: STR }) }, rejected: KEYED, deferred: KEYED, summary: STR })
const WRITE = S({ model: STR, branch: STR, head_sha: STR, pushed: BOOL, items: { type: 'array', items: S({ key: STR, outcome: { type: 'string', enum: ['fixed', 'could_not'] }, commit: STR, test: STR, note: STR }, ['key', 'outcome', 'note']) }, focused_tests: STR, issues: STRS, summary: STR })
const INT = S({ model: STR, branch: STR, head_sha: STR, pushed: BOOL, chain: { type: 'string', enum: ['pass', 'fail'] }, counts: OBJ, fixes_applied: STRS, dropped_commits: STRS, failures: STRS, summary: STR })
const RECHECK = S({ model: STR, fixed: STRS, still_failing: KEYED, evidence_file: STR, summary: STR })
const PRESENCE = S({ model: STR, away: BOOL, idle_s: NUM, frontmost: STR, waited_min: NUM, note: STR })
const GUI = S({ model: STR, status: { type: 'string', enum: ['done', 'partial', 'deferred', 'blocked'] }, per_entry: { type: 'array', items: S({ id: STR, verdict: { type: 'string', enum: ['certified', 'failed', 'deferred'] }, evidence: STR }) }, deferred: STRS, idle_rule: STR, stops: STRS, summary: STR })
const VSHARD = S({ model: STR, shard: STR, checked: { type: 'array', items: S({ id: STR, verdict: { type: 'string', enum: ['holds', 'refuted', 'inconclusive'] }, evidence: STR, command: STR, checkout_sha: STR }, ['id', 'verdict', 'evidence']) }, adjacent: { type: 'array', items: S({ near_id: STR, title: STR, severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }, evidence: STR }) }, evidence_file: STR, summary: STR })
const VERDICT = S({ model: STR, verdict: { type: 'string', enum: ['PASS', 'FAIL'] }, gate_items: { type: 'array', items: S({ item: STR, result: { type: 'string', enum: ['PASS', 'FAIL', 'DEFERRED'] }, cause: { type: 'string', enum: ['none', 'product_defect', 'harness_environment', 'operator_attended'] }, evidence: STR }) }, gate8_refuted: BOOL, refuted_entries: STRS, operator_attended: STRS, fixed_uncertified: STRS, adjacent_findings: STRS, blockers: STRS, needs_gui: STRS, tag_sha: STR, sheet_file: STR, area_concurrences: { type: 'array', items: S({ id: STR, area: STR, verdict: { type: 'string', enum: ['concur', 'refuse'] }, evidence: STR }) }, summary: STR }, ['model', 'verdict', 'gate_items', 'gate8_refuted', 'refuted_entries', 'operator_attended', 'fixed_uncertified', 'adjacent_findings', 'blockers', 'needs_gui', 'tag_sha', 'sheet_file', 'summary'])

const fixable = f => ['regression', 'chain', 'gate8'].includes(f.kind) || (f.kind === 'new_defect' && f.severity !== 'low')

// ---------------------------------------------------------------- 1. Preflight
phase('Preflight')
const pre = await run(`${COMMON}

${facts(A.sha || '(to resolve)', CAND)}

ROLE: PREFLIGHT (Sonnet, mechanical; label rc1-preflight). You alone may build in the candidate worktree and restart the shared stack. ${STALL} Record each fact with its command in ${EV}/PREFLIGHT.md.
(1) Git: fetch; candidate = ${A.sha ? A.sha : 'git rev-parse 004-r4-experience-rebuild (no sha given)'} as a full sha; it must be 004-r4-experience-rebuild or an ancestor; record origin/004's relation, worktree list, 'worktree-agent-rc1-*' branches, newest r15-* tag.
(2) Clean build: git worktree add --detach <worktree> <sha> (if that path exists at another sha, remove only it first); there, detached, logs in ${EV}/logs/: pnpm install --frozen-lockfile; node scripts/ensure-all-sidecars.mjs --force (Python 3.13 venv + all three binaries). A failure that survives one clean retry → status 'blocked' with the step and log tail.
(3) Seed ${SEED} from ${ISO}/data: sqlite3 '.backup' per .db, the non-sqlite files ISO_STACK.md copies, a fresh keyless dev-keystore.json reading exactly {"secrets": {}, "migrated": true} (chmod 600; ISOLATION_MAP.md §2.4), no audit_log.db.
(4) Shared stack: kill only the sleep pids ${ISO}/pids.json lists (each must be 'sleep 86400'); boot :52153/:52154 from the worktree's src-tauri/binaries and :52152 from its sidecar/ on ${ISO}/data per ISO_STACK.md; new pids → pids.json; /health ok with openbb-mcp available. A port held by an unlisted process: never kill it → 'blocked'.
(5) Env: llama3.1:8b in ollama list; /search/status + /search/searxng/status on :52152 (never start Docker); df -h (block < 10 GB, warn < 25 GB); idle: ${IDLE_CMD}; frontmost: ${FRONT_CMD}.
(6) Register: read docs/redesign/verification/vysted-r15-register.json DIRECTLY at the candidate (its own 'counts' field + the 'entries' list); NEVER 'register.py status', which recomputes from r15/census/merge/ and lags the JSON that the Stage-C adjudicators write. Counts by status; critical/high/medium ids whose status is exactly 'open'; needs_gui ids; blocked_tier4 ids.
Return model, status, sha, build_log, stack_ok, ollama_llama31, searxng, disk_free_gb, idle_s, frontmost, status_counts, open_chm, needs_gui, blocked_tier4, blockers, notes, summary ≤120 words.`, { label: 'rc1-preflight', phase: 'Preflight', model: 'sonnet', effort: 'medium', schema: PRE })

if (!pre || pre.status !== 'ready') {
  const why = pre ? (pre.blockers.length ? pre.blockers : ['preflight status ' + pre.status]) : ['preflight agent died']
  log('preflight blocked — the gate does not run: ' + JSON.stringify(why))
  return { status: 'blocked', gate8: null, regression: null, scenarios: null, drives: [], battery: null, gui: null, verifier: null, tag_sha: null, candidate_sha: pre ? pre.sha || null : null, blockers: why, deferred_needs_gui: pre ? pre.needs_gui : [] }
}
const SHA = pre.sha
// Fix branches and the integration worktree are per candidate, so a re-run of the gate never needs a force-push.
const SH7 = SHA.slice(0, 7)
const FIXWT = SCRATCH + '/rc1-' + SH7 + '-fix-int'
const FIXBR = 'worktree-agent-rc1-' + SH7 + '-fix-int'
const blockers = [...pre.blockers]
if (pre.open_chm.length) {
  blockers.push('register: ' + pre.open_chm.length + ' critical/high/medium entries still open: ' + pre.open_chm.join(', '))
  log('register criterion already failing: ' + pre.open_chm.length + ' open c/h/m entries (the gate still runs and records them)')
}
log('preflight ready @ ' + SHA.slice(0, 7) + '; needs_gui ' + JSON.stringify(pre.needs_gui) + '; idle ' + pre.idle_s + ' s; disk ' + pre.disk_free_gb + ' GB')
const F0 = facts(SHA, CAND)

// ---------------------------------------------------------------- 2. Gate 8
phase('Gate 8')
const g8 = await run(`${COMMON}

${F0}

ROLE: GATE 8 PROVER (Opus; label rc1-gate8). Law (D81): prove NO order, broker or simulated-account path exists anywhere in the product AND the tracked portfolio works end to end. Evidence, not assertion: every raw list and output goes under ${EV}/gate8/. Your sidecar: :52310.
(a) Routes: GET /openapi.json → every method+path to openapi-paths.txt; grep -iE 'order|broker|kill|audit|margin|paper|simulat|safety|static.?ip|disclaimer|holding|position'; explain each hit (/portfolio/positions is the tracked portfolio; order/broker/kill-switch/audit-order = FAIL).
(b) Tools: dump CAPABILITY_CATALOG, TOOL_SCHEMAS, KNOWN_TOOL_IDS, registered tools and MCP list_tools names (worktree venv, as sidecar/tests/test_no_trading_surface.py does) to tools-*.txt, plus your sidecar's live MCP surface if served; explain every hit.
(c) pytest sidecar/tests/test_no_trading_surface.py (that file only) → counts.
(d) rg -n -i over src/, sidecar/, src-tauri/, plugins/, docs/ (skip node_modules, .venv, target, out, .next, binaries) for broker, place.?order, propose_order, 'order (entry|ticket|book|placement)', paper.?trad, simulat, 'live.?(trading|mode)', kill.?switch, audit_orders, margin, demat. One hit file per root; classify EVERY hit: product surface (UI, tool, route, setting, terms, user-facing doc offering trading → FAIL), historical record (CHANGELOG, docs/archive, verification evidence, a doc saying it was removed → OK, say why), false positive. Quote what Settings and the first-launch terms say about trading.
(e) Portfolio e2e on :52310: add 3 manual holdings with cost bases (NSE, US, one with a note), read back; recompute P&L from /quote prices you fetch and compare; update, delete, read back; CSV export via the panel's code path, run headless (scratch code never committed): columns vs holdings; notes CRUD; watchlist CRUD; the agent on llama3.1:8b: get_portfolio matches the ledger, then a GATED write: portfolio_add_position under --autonomy ask is proposed and the ledger is unchanged until applied; apply it as the frontend does, read back.
Write ${EV}/GATE8.md (per item: command, excerpt, verdict) and ${EV}/gate8.json {pass, routes, tools, mcp, grep:{<root>:{total, product, historical, false_positive}}, portfolio:{steps}, failures}. Each product-surface hit or portfolio break → finding kind gate8. Stop your sidecar. Return model, lane 'gate8', status, evidence_files, counts, findings, notes, summary ≤150 words.`, { label: 'rc1-gate8', phase: 'Gate 8', model: 'opus', effort: 'high', schema: LANE })
if (!g8) blockers.push('Gate 8 agent died: no proof')
log('gate 8: ' + (g8 ? g8.status + ', ' + g8.findings.length + ' findings' : 'no result'))

// ---------------------------------------------------------------- 3. Regression suite
phase('Regression')
const DRIVE = limiter(intArg('drive_limit', 3))
const BATT = limiter(intArg('batt_limit', 2))

const heavyLane = () => run(`${COMMON}

${F0}

ROLE: HEAVY-LANE OWNER (Sonnet; label rc1-heavy). You are the only process building or testing now; you may run the chain inside ${CAND}. ${STALL} (1) cd ${CAND} && nohup sh -c 'PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local; echo EXIT=$?' > ${EV}/logs/ci-local.log 2>&1 & — exactly the package.json script, no flags, no --force (the venv PATH is how its bare 'python' resolves in a non-interactive shell); poll with separate short calls (30-60 min). (2) Then node scripts/smoke-test-sidecars.mjs the same way into ${EV}/logs/smoke.log. A failing command is re-run ONCE to tell a flake from a failure; record both runs. Never fix anything. Write ${EV}/REGRESSION.md: the sha, per ci-local stage (install, ensure-all-sidecars, lint, format:check, typecheck, cargo fmt, clippy, ruff check, ruff format, vitest, cargo test, pytest) exit and real counts copied from the log, the smoke per-sidecar lines, both EXIT codes. Every failure → finding kind chain (test id, log excerpt, suspected files). Return model, lane 'ci-smoke', status, evidence_files, counts, findings, notes, summary ≤120 words.`, { label: 'rc1-heavy', phase: 'Regression', model: 'sonnet', effort: 'medium', schema: LANE })

const scenarioLane = () => run(`${COMMON}

${F0}

ROLE: AGENT SCENARIO HARNESS (Sonnet; label rc1-scenarios). Your own sidecar: :52311. Probe three properties of the agent on the candidate. (1) READ-BACK BEFORE CLAIM: every agent write (watchlist add, note write, portfolio add/update through the proposed-changes gate, screen author, layout arrange, publish_brief) is claimed done only after its ack or read-back; a tool result or answer that claims success without an ack, or states a value it never read, fails. (2) SKEPTICISM: conflicting or implausible data is flagged, not smoothed — AMAL (BSE) vs AMAL (NASDAQ), SMR, DAL vs Delta, ELCIDIN's five-figure price, SIFY's 1 ADR = 6 shares, BGNE→ONC; no fabricated metric; unresolvable → says so. (3) SELF-CONSISTENCY: the same question asked twice fresh and once inside a multi-turn thread gives the same numbers and the same resolution. Read sidecar/services/agent_runtime.py (tool rounds, ack/read-back) and the proposed-changes gate first, then the census evidence in r15/surface/composer-chat/ and the seat transcripts: reuse prompts that failed before so results compare. At least 4 scenarios per property on llama3.1:8b; the same set once on ONE free OpenRouter slug; OpenAI-direct via vy.py only where both fail for model-capability reasons and the ledger has headroom (stop at the guard). Run the llama3.1:8b scenarios ONE AT A TIME, each under the LOCAL-MODEL LOCK, and record for every scenario × model run an explicit outcome: 'ran', 'lock_timeout' or 'upstream_5xx' (with the status line); only 'ran' results are scored, the others are harness causes, never product failures; put the three tallies in counts. Separate model weakness (the 8b narrates without calling tools) from product defects (a tool claims success without an ack, the runtime drops a result, a gate bypass); only product defects are findings (regression if a certified entry covered it, else new_defect). Save each run as .jsonl under ${EV}/scenarios/ and write ${EV}/SCENARIOS.md: scenario × model matrix, outcome (ran / lock_timeout / upstream_5xx) and pass/fail with the evidence line. Stop your sidecar. Return model, lane 'scenarios', status, evidence_files, counts, findings, notes, summary ≤150 words.`, { label: 'rc1-scenarios', phase: 'Regression', model: 'sonnet', effort: 'high', schema: LANE })

const driveLane = () => pipeline(DRIVE_GROUPS, (_, g, i) => DRIVE(() => run(`${COMMON}

${F0}

ROLE: OWNER-DRIVE '${g}' (Sonnet; label rc1-drive-${g}). Re-drive your surface group against the candidate the way the census did: method and group scope in docs/redesign/verification/r15/tooling/PROMPT_surface_s2.md (section OWNER-DRIVE, your group), census evidence in docs/redesign/verification/r15/surface/${g}/ (what was driven, with which requests, what broke). Read the group's panel code and api.ts first. Reads go to the shared :52152; any write (portfolio, notes, watchlist, settings, agent host actions, delegate runs, inducers) goes to YOUR sidecar on :${52320 + i}.${g === 'onboarding-stranger' ? ' Boot it on a CLEAN empty data dir (only dev-keystore.json seeded as {"secrets": {}, "migrated": true}), not the seed copy.' : ''} Drive every control and state the census drove, with the same requests or prompts where they exist, read back before claim, and score each interaction ok / partial / broken / NEEDS-GUI with its evidence line. Census broken → now ok: cite the fixing register id if you can find it. Census ok → now not ok: finding kind regression. A fresh real defect: new_defect, severity by user impact (fails every time = high; wrong or stale value = medium; cosmetic = low). Evidence under docs/redesign/verification/r15/surface/${g}/rc1/ (never overwrite census files) plus ${EV}/drives/${g}.md with the scored table and the census→rc1 deltas. Stop your sidecar. Return model, lane 'drive:${g}', status, evidence_files, counts, findings, notes, summary ≤120 words.`, { label: 'rc1-drive-' + g, phase: 'Regression', model: 'sonnet', effort: 'high', schema: LANE })))

let batteryIndex = null
let batteryShards = []
const MAX_BATT_SHARDS = 8
const entryCount = sh => sh.sets.reduce((n, x) => n + x.entries.length, 0)
const batteryLane = async () => {
  batteryIndex = await run(`${COMMON}

${F0}

ROLE: BATTERY INDEXER (Sonnet; label rc1-battery-index). Build the regression battery's work list; no re-runs. COVERAGE IS THE JOB: read the register AT THE CANDIDATE ('git show ${SHA}:docs/redesign/verification/vysted-r15-register.json', not the working tree) and assign EVERY entry with status 'fixed' to exactly one set (no id twice, none left out), then every set to exactly one shard. For every docs/redesign/verification/r15/stage-c/batch-*/PLAN.md read the per-writer sections (headings like '### W1: name (…)') and the batch's VERDICTS.json certified list: a writer set = {batch: 'batch-N', set: 'batch-N/W<k>-<name>', entries: the certified ids listed in that writer's section whose register status is now 'fixed'}. Register entries with status 'fixed' that no set covers → sets {batch: 'unplanned', set: 'unplanned-<n>'} of ≤12 ids grouped by subsystem. Skip needs_gui and removed_with_feature. Shards: number the distinct batches in order of first appearance in your sets list; the first ${MAX_BATT_SHARDS} batches are shards 0..${MAX_BATT_SHARDS - 1}; every later batch goes whole to the shard with the fewest entries at that point; shard numbers are contiguous from 0. Check before returning: the union of all sets' entries equals the fixed ids at the sha, with no duplicates. Write ${EV}/battery/INDEX.json and INDEX.md (set → shard, ids, counts; the id → shard map). Return model, sets[{batch, set, entries, shard}], fixed_total (count of status 'fixed' at the sha), id_shard {id: shard}, unplanned_fixed (count), index_file, summary ≤80 words.`, { label: 'rc1-battery-index', phase: 'Regression', model: 'sonnet', effort: 'medium', schema: INDEX })
  if (!batteryIndex || !batteryIndex.sets.length) { log('battery index empty or failed — the fixed-name battery did not run'); return [] }
  const covered = batteryIndex.sets.flatMap(x => x.entries)
  const dupes = covered.filter((id, i) => covered.indexOf(id) !== i)
  if (dupes.length) log('battery index: ids in more than one set: ' + [...new Set(dupes)].join(', '))
  if (new Set(covered).size !== batteryIndex.fixed_total) log('battery index: ' + new Set(covered).size + ' ids in sets vs ' + batteryIndex.fixed_total + ' fixed at ' + SHA.slice(0, 7))
  // The indexer's shard numbers are used when they are contiguous 0..m-1 (m <= 8); otherwise the script shards by batch below.
  const nums = [...new Set(batteryIndex.sets.map(x => x.shard))].sort((a, b) => a - b)
  const agentShards = nums.length <= MAX_BATT_SHARDS && nums.every((v, i) => v === i)
  // One shard per stage-c batch (~5 writer sets each); batches past the 8th fold into the lightest shard.
  const byBatch = []
  batteryIndex.sets.forEach((x, idx) => {
    const b = x.batch || x.set.split('/')[0]
    let g = byBatch.find(y => y.batch === b)
    if (!g) byBatch.push(g = { batch: b, sets: [] })
    g.sets.push({ set: x.set, entries: x.entries, file: 'set-' + idx + '.md', raw: 'raw/set-' + idx })
  })
  if (agentShards) {
    batteryShards = nums.map(() => ({ batches: [], sets: [] }))
    batteryIndex.sets.forEach((x, idx) => {
      const t = batteryShards[x.shard]
      const b = x.batch || x.set.split('/')[0]
      if (!t.batches.includes(b)) t.batches.push(b)
      t.sets.push({ set: x.set, entries: x.entries, file: 'set-' + idx + '.md', raw: 'raw/set-' + idx })
    })
  } else {
    log('battery index: shard numbers ' + JSON.stringify(nums) + ' not contiguous from 0 (<= ' + MAX_BATT_SHARDS + ') — sharding by batch')
    batteryShards = byBatch.slice(0, MAX_BATT_SHARDS).map(g => ({ batches: [g.batch], sets: g.sets.slice() }))
    for (const g of byBatch.slice(MAX_BATT_SHARDS)) {
      const t = batteryShards.reduce((m, x) => (entryCount(x) <= entryCount(m) ? x : m))
      t.batches.push(g.batch)
      t.sets.push(...g.sets)
    }
  }
  log('battery: ' + batteryIndex.sets.length + ' writer sets, ' + batteryIndex.sets.reduce((n, x) => n + x.entries.length, 0) + ' fixed entries in ' + batteryShards.length + ' shards (' + batteryShards.map(x => x.batches.join('+') + ':' + entryCount(x)).join(', ') + ')')
  return pipeline(batteryShards, (_, sh, k) => BATT(() => run(`${COMMON}

${F0}

ROLE: REGRESSION BATTERY shard ${k} (Sonnet; label rc1-battery-${k}), stage-c ${sh.batches.join(' + ')}. ${STALL} Re-run the ORIGINAL repro of every certified entry in these writer sets against the freshly built candidate — never judge from the diff: ${JSON.stringify(sh.sets.map(x => ({ set: x.set, file: x.file, entries: x.entries })))}. Boot ONE sidecar for the whole shard on :${52340 + k} at the start, reuse it for every set, stop it at the end. For each id read the register entry (repro, evidence) and how the batch verifier certified it (that batch's VERDICTS.md, 'Per-entry evidence'), then re-run that repro: curl, vy.py, or an in-process python call with the candidate's venv; where the certification used the outside world (screener.in, NSE/BSE, SEC EDGAR), re-check against it. Never run vitest or pytest suites (the heavy lane owns them): an entry certified only through a pinned test → verdict ci_pinned naming the test. Verdicts: holds / regressed / ci_pinned / needs_gui / blocked_env (an upstream outage proven by a direct probe), each with a one-line evidence excerpt. COVERAGE FIRST: for EVERY id in your sets, write the probe's raw output (command, exit, output) to ${EV}/battery/raw/set-<n>/<id>.txt (n as in the set's file; <id>-<suffix>.txt for extra probes) AS YOU GO, before judging it — a probe that errors, times out or is blocked still gets its raw file with that output. Write ${EV}/findings/rc1-battery-${k}.json after each set (a JSON array, [] when none), so a partial shard still leaves its findings file. Regressed → finding kind regression with register_id. Work one set at a time and write its ${EV}/battery/<file> (header: the set name; table id | repro run | observed | verdict) before starting the next — a restart skips sets whose file is complete. End the last set file and your notes with one line 'COVERAGE: <with raw>/<total> ids raw; no raw: <id> (why), …'. Stop your sidecar. Return model, lane 'battery:shard-${k}', status, evidence_files, counts (holds, regressed, ci_pinned, needs_gui, blocked_env), results[{set, id, verdict, evidence}] (exactly one per entry), findings, notes, summary ≤100 words.`, { label: 'rc1-battery-' + k, phase: 'Regression', model: 'sonnet', effort: 'high', schema: BSHARD })))
}

const packLane = () => run(`${COMMON}

${F0}

ROLE: DATA-PACK RE-COLLECTION (Sonnet; label rc1-datapack). The 24 battery names (docs/redesign/verification/r15/battery/manifest.json) were collected by the census into r15/battery/collected/ and diffed against pack truth in r15/battery/diffs/ and r15/BATTERY_DIFFS.json/.md (match, mismatch, app blank, no source truth, definitional, as-of skew). Your own sidecar: :52313. Make a minimal copy tree ${SCRATCH}/rc1-pack holding scripts/r15/collect_battery.py and docs/redesign/verification/r15/battery/manifest.json (copied from ${CAND}) and run the collector FROM THAT COPY (--port 52313 --force, detached, polled) so it never overwrites the census baseline; copy its output JSONs to ${EV}/battery/collected/. Fields to re-diff: every field a fixed register entry touched (fixed entries whose repro/evidence names a battery symbol or a BATTERY_DIFFS field — list them with ids) using BATTERY_DIFFS.md's rules against the census pack truth; also scan all 24 names for any field that was 'match' in the census and is not now. Prices move: price-like drift is as-of skew, not a regression. Write ${EV}/DATAPACK.md (per slot: fields re-diffed, census status → rc1 status, fixing register id) and ${EV}/datapack.json. A match that became a mismatch or blank → finding kind regression. Stop your sidecar. Return model, lane 'datapack', status, evidence_files, counts, findings, notes, summary ≤100 words.`, { label: 'rc1-datapack', phase: 'Regression', model: 'sonnet', effort: 'medium', schema: LANE })

// Barrier: the fix loop needs every lane's findings.
const [heavy, scen, driveRes, battRes, pack] = await parallel([heavyLane, scenarioLane, driveLane, batteryLane, packLane])
const drives = (driveRes || []).filter(Boolean)
const battery = (battRes || []).filter(Boolean)
const expectedSets = batteryIndex ? batteryIndex.sets.map(s => s.set) : []
const expectedIds = batteryShards.flatMap(sh => sh.sets.flatMap(x => x.entries))
const seenIds = new Set(battery.flatMap(b => b.results.map(x => x.id)))
const battMissing = expectedIds.filter(id => !seenIds.has(id))
const battTally = battery.flatMap(b => b.results).reduce((m, x) => { m[x.verdict] = (m[x.verdict] || 0) + 1; return m }, {})
if (drives.length < DRIVE_GROUPS.length) log('owner-drives missing: ' + DRIVE_GROUPS.filter(g => !drives.some(d => d.lane === 'drive:' + g)).join(', '))
if (battery.length < batteryShards.length) log('battery shards missing: ' + (batteryShards.length - battery.length) + ' of ' + batteryShards.length)
if (battMissing.length) log('battery entries with no result: ' + battMissing.length + ' of ' + expectedIds.length + ': ' + battMissing.join(', '))
log('regression lanes: ci/smoke ' + (heavy ? heavy.status : 'none') + '; scenarios ' + (scen ? scen.status : 'none') + '; drives ' + drives.map(d => d.lane.slice(6) + '=' + d.status).join(' ') + '; battery ' + battery.length + '/' + batteryShards.length + ' shards ' + JSON.stringify(battTally) + '; datapack ' + (pack ? pack.status : 'none'))

const collate = await run(`${COMMON}

${F0}

ROLE: COLLATOR (Sonnet, mechanical; label rc1-collate). Write index files from the per-agent evidence already on disk — no new judgement, no re-runs. ${EV}/OWNER_DRIVE.md: one row per group from ${EV}/drives/*.md (interactions driven; ok/partial/broken/NEEDS-GUI counts; census→rc1 deltas; finding keys; evidence dir). ${EV}/BATTERY.md: one row per set from ${EV}/battery/set-*.md (ids; holds/regressed/ci_pinned/needs_gui/blocked_env counts), then a data-pack section from ${EV}/DATAPACK.md. Battery coverage, checked on disk: shard → sets is ${JSON.stringify(batteryShards.map((sh, k) => ({ shard: k, sets: sh.sets.map(x => x.raw) })))}; for every fixed id in ${EV}/battery/INDEX.json, look for ${EV}/battery/raw/set-<n>/<id>*.txt; in BATTERY.md list, per shard, the ids with no raw file (reason from that shard's COVERAGE line, else 'no raw output') and write the battery status line 'incomplete' (listing them) when any fixed id lacks raw output, 'complete' only when none does — never 'pass'. Merge every ${EV}/findings/*.json into ${EV}/FINDINGS.json (sorted by kind then severity) and a FINDINGS.md table. Expected groups: ${JSON.stringify(DRIVE_GROUPS)}; expected sets: ${expectedSets.length} (${EV}/battery/INDEX.json). Anything expected with no file → listed as MISSING in the index file and in your return. Return model, files_written, missing, battery_status, no_raw[{key: id, reason}], summary ≤80 words.`, { label: 'rc1-collate', phase: 'Regression', model: 'sonnet', effort: 'medium', schema: COLLATE })
if (collate && collate.missing.length) log('collator: missing evidence ' + collate.missing.join(', '))
const battNoRaw = collate ? collate.no_raw.map(x => x.key) : null
if (collate && collate.battery_status === 'incomplete') log('battery incomplete: ' + battNoRaw.length + ' fixed ids with no raw output: ' + battNoRaw.join(', '))

const allFindings = [g8, heavy, scen, pack, ...drives, ...battery].filter(Boolean).flatMap(r => r.findings)
const lows = allFindings.filter(f => f.kind === 'new_defect' && f.severity === 'low')
const env = allFindings.filter(f => f.kind === 'environment')
if (lows.length) log(lows.length + ' low new defects recorded for rc2, not fixed here: ' + lows.map(f => f.key).join(', '))
if (env.length) log(env.length + ' environment findings (upstream outages), not fixed: ' + env.map(f => f.key).join(', '))

// ---------------------------------------------------------------- 4. Fix loop
phase('Fix')
let open = allFindings.filter(fixable)
let tagSha = SHA
let tagWt = CAND
const rounds = []
const rejectedAll = []
const deferredAll = []
if (!open.length) log('no regressions or c/h/m new defects — fix loop skipped')
else if (MAX_ROUNDS < 1) log('max_fix_rounds is 0 — ' + open.length + ' findings left open')
for (let r = 1; r <= MAX_ROUNDS && open.length; r++) {
  const base = tagSha
  const keys = open.map(f => f.key)
  log('fix round ' + r + ': ' + keys.length + ' findings on ' + base.slice(0, 7))
  const triage = await run(`${COMMON}

${facts(base, tagWt)}

ROLE: FIX TRIAGE round ${r} (Opus, root-causing; label rc1-fix-r${r}-triage). Per writer set decide the model field: return 'sonnet' by default (clear spec + checkable output) and 'opus' only for a risk-adjacent or root-cause fix; write the acceptance test into the brief (clear spec + checkable output), and where the fix needs root-causing first or is risk-adjacent (safety surface, workspace persistence, agent runtime state), say why in the brief. Findings to close: ${JSON.stringify(keys)} — their records are in ${EV}/findings/*.json with the evidence files they cite. Base ${base}. For each: open the code it implicates and, if the record is not conclusive, reproduce it minimally on your own sidecar (:${52330 + r}). Decide: real (root cause located; which files) / not reproducible or environment (evidence) → rejected with the reason (the final verifier must concur) / fixable only in a Tier-1 file or by reversing a locked decision → deferred (and a numbered item in docs/redesign/DECISIONS_FOR_OPERATOR.md, then pnpm exec prettier --write that file: it is format-checked). Partition the real ones into ≤4 DISJOINT writer sets by file ownership (a file belongs to exactly one writer), each with a brief ≤120 words: mechanism → fix → pinning test → files. Write ${EV}/fix-r${r}/PLAN.md. Stop your sidecar. Return model, plan_file, writers[{name, keys, files, brief}], rejected[{key, reason}], deferred[{key, reason}], summary ≤120 words.`, { label: 'rc1-fix-r' + r + '-triage', phase: 'Fix', model: 'opus', effort: 'high', schema: TRIAGE })
  if (!triage) { log('fix round ' + r + ': triage died — stopping the loop'); break }
  rejectedAll.push(...triage.rejected)
  deferredAll.push(...triage.deferred)
  const dropped = new Set([...triage.rejected, ...triage.deferred].map(x => x.key))
  const sets = triage.writers.slice(0, 4)
  if (triage.writers.length > 4) log('fix round ' + r + ': ' + (triage.writers.length - 4) + ' writer sets over the cap of 4 — their findings carry to the next round')
  if (!sets.length) { open = open.filter(f => !dropped.has(f.key)); log('fix round ' + r + ': no writer sets'); break }
  // Barrier: the integrator merges every writer branch together.
  const writes = (await parallel(sets.map(w => () => run(`${COMMON}

ROLE: RC1 FIX WRITER '${w.name}' round ${r} (${w.model === 'opus' ? 'Opus' : 'Sonnet'}; label rc1-fix-r${r}-${w.name}). Implement to the acceptance test named in your brief, run only the focused tests, report; do not re-verify (the recheck agent certifies once per round). You run inside your OWN git worktree (pwd must be under .claude/worktrees; never touch ${REPO} itself or any other branch). FIRST: git fetch origin; if origin/worktree-agent-rc1-${SH7}-fix-r${r}-${w.name} exists and ${base} is its ancestor (a restart of your role), git checkout -B worktree-agent-rc1-${SH7}-fix-r${r}-${w.name} origin/worktree-agent-rc1-${SH7}-fix-r${r}-${w.name} and continue after its last commit; else git checkout -B worktree-agent-rc1-${SH7}-fix-r${r}-${w.name} ${base}, git reset --hard ${base}, confirm HEAD is ${base}. ${STALL} Read ${EV}/fix-r${r}/PLAN.md (your section) and the finding records ${JSON.stringify(w.keys)} in ${EV}/findings/*.json. Brief: ${w.brief}. Files you own: ${JSON.stringify(w.files)} — touch nothing else (a fix that needs another file → outcome could_not, name the file). Per finding: the root-cause fix, the pinning test in the repo's test location, the focused tests for your files once (real counts), the linters for your files (ruff format + check; pnpm eslint + prettier --check; cargo fmt/clippy if rust), then COMMIT that finding alone ('fix(rc1): <what> (<register id or finding key>)', no emojis, Co-Authored-By: Claude ${w.model === 'opus' ? 'Opus' : 'Sonnet'} 5.1 <noreply@anthropic.com>) and PUSH the branch (git push -u origin worktree-agent-rc1-${SH7}-fix-r${r}-${w.name}). Certification is not your job: no full chain, no agents. Return model, branch, head_sha, pushed, items[{key, outcome, commit, test (path::name), note ≤40 words}], focused_tests, issues, summary ≤120 words.`, { label: 'rc1-fix-r' + r + '-' + w.name, phase: 'Fix', model: (w.model === 'opus' ? 'opus' : 'sonnet'), effort: 'high', isolation: 'worktree', schema: WRITE })))).filter(Boolean)
  if (!writes.length) {
    log('fix round ' + r + ': every writer died — stopping the loop; the candidate stays ' + tagSha.slice(0, 7))
    rounds.push({ round: r, integ: 'skipped', fixed: [] })
    break
  }
  const integ = await run(`${COMMON}

ROLE: RC1 FIX INTEGRATOR round ${r} (Opus; label rc1-fix-r${r}-int) — heavy-lane owner now; nobody else builds. ${STALL} Writer reports: ${JSON.stringify(writes.map(x => ({ branch: x.branch, head: x.head_sha, pushed: x.pushed, items: x.items.map(i => ({ key: i.key, outcome: i.outcome, commit: i.commit })) })))}. NEVER work in ${REPO} itself or move its HEAD. Worktree ${FIXWT} on branch ${FIXBR}: ${r === 1 ? 'git fetch origin; if origin/' + FIXBR + ' exists and ' + base + ' is its ancestor (a restart of your role), git worktree add ' + FIXWT + ' ' + FIXBR + ' on it and continue; else git worktree add ' + FIXWT + ' -b ' + FIXBR + ' ' + base : 'it exists at ' + base + ' from round ' + (r - 1) + '; git fetch origin and continue from it'}; confirm pwd is under ${SCRATCH}; pnpm install there. Merge each origin/worktree-agent-rc1-${SH7}-fix-r${r}-* branch in ${EV}/fix-r${r}/PLAN.md order. Run PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local detached into ${EV}/fix-r${r}/ci-local.log (its ensure step rebuilds the sidecars that changed, clean in this worktree). On failure bisect: an integration artefact → fix minimally; a wrong writer fix → git revert it and list it in dropped_commits (its finding stays open). Never weaken a test. Finish with one more full green ci-local (same log, appended) and node scripts/smoke-test-sidecars.mjs detached into ${EV}/fix-r${r}/smoke.log; write ${EV}/fix-r${r}/INTEGRATION.md with the real counts and EXIT codes. Push ${FIXBR}. Leave the worktree in place. chain 'pass' only if the final ci-local AND smoke exited 0 at head_sha. Return model, branch, head_sha, pushed, chain, counts, fixes_applied, dropped_commits, failures, summary ≤150 words.`, { label: 'rc1-fix-r' + r + '-int', phase: 'Fix', model: 'opus', effort: 'high', schema: INT })
  if (!integ || !integ.pushed || integ.chain !== 'pass') {
    log('fix round ' + r + ': integration ' + (integ ? integ.chain + ' @ ' + (integ.head_sha || '').slice(0, 7) : 'died') + ' — the candidate stays ' + tagSha.slice(0, 7))
    rounds.push({ round: r, integ: integ ? integ.chain : 'died', fixed: [] })
    break
  }
  tagSha = integ.head_sha
  tagWt = FIXWT
  const toCheck = open.filter(f => !dropped.has(f.key) && sets.some(w => w.keys.includes(f.key))).map(f => f.key)
  const recheck = await run(`${COMMON}

${facts(tagSha, FIXWT)}

ROLE: RC1 RECHECK round ${r} (Opus, fresh — certify from the running app, never from the diff; label rc1-fix-r${r}-recheck). Findings: ${JSON.stringify(toCheck)} (records in ${EV}/findings/*.json). Your own sidecar from ${FIXWT} (read-only, at ${tagSha}) on :${52335 + r}. Re-run each finding's exact repro and, for a regression, the register entry's original repro too; one fresh variant where the fix pins a class. A chain finding is fixed when ${EV}/fix-r${r}/INTEGRATION.md and its ci log show that stage green at ${tagSha}. fixed = no longer reproduces and nothing adjacent broke. CERTIFY THE CLAIM, NOT ONLY THE REPRO: an entry is certified only when its stated conclusion holds — its title, its fix_shape and its acceptance_test — checked against the running app with at least one fresh case the fix was not written against (a different symbol, phrasing, host, provider or file of the same class). A fix that holds the entry's literal repro but leaves any part of the title claim or fix_shape unfixed is not_certified, with the unfixed claim named in the reason and the fresh case recorded as its repro. Write ${EV}/fix-r${r}/RECHECK.md (key | repro | observed | verdict). Stop your sidecar. Return model, fixed, still_failing[{key, reason}], evidence_file, summary ≤100 words.`, { label: 'rc1-fix-r' + r + '-recheck', phase: 'Fix', model: 'opus', effort: 'high', schema: RECHECK })
  const fixedKeys = new Set(recheck ? recheck.fixed : [])
  rounds.push({ round: r, head: tagSha, fixed: [...fixedKeys], still: recheck ? recheck.still_failing.map(x => x.key) : toCheck })
  open = open.filter(f => !fixedKeys.has(f.key) && !dropped.has(f.key))
  log('fix round ' + r + ': ' + fixedKeys.size + ' fixed @ ' + tagSha.slice(0, 7) + ', ' + open.length + ' still open')
}
if (open.length) {
  log('fix loop could not close: ' + open.map(f => f.key).join(', '))
  blockers.push('unfixed findings: ' + open.map(f => f.key + ' (' + f.kind + ', ' + f.severity + ')').join('; '))
}
if (deferredAll.length) blockers.push('Tier-4 deferred findings: ' + deferredAll.map(x => x.key).join(', '))

// ---------------------------------------------------------------- 5. GUI round
phase('GUI')
let gui = null
const idleRule = 'HIDIdleTime >= 1500 s (' + IDLE_CMD + ') immediately before launching the app and every click/type/capture batch; a frontmost-window surprise is a hard stop'
if (!pre.needs_gui.length) {
  log('GUI round skipped: no register entry has status needs_gui')
  gui = { status: 'done', per_entry: [], deferred: [], idle_rule: idleRule, stops: [], summary: 'nothing needs the GUI' }
} else if (SKIP_GUI) {
  log('GUI round skipped by args.skip_gui — deferred: ' + pre.needs_gui.join(', '))
  gui = { status: 'deferred', per_entry: [], deferred: pre.needs_gui, idle_rule: idleRule, stops: ['skip_gui: computer-use grant does not cover the built app'], summary: 'skipped by args: operator-attended' }
} else {
  const presence = await run(`${COMMON}

ROLE: PRESENCE GATE (Sonnet; label rc1-gui-presence). Decide whether the GUI round may start; touch nothing. Every ~2 minutes, for up to ${GUI_WAIT_MIN} minutes, take one reading in its own call — idle seconds: ${IDLE_CMD}; frontmost app: ${FRONT_CMD} — with 'sleep 100' as a separate call between readings (never a loop inside one call). Append each reading (time, idle, frontmost) to ${EV}/gui/presence.log (mkdir -p). Return away=true at the first reading with idle ≥ 1500; else away=false after the window. Return model, away, idle_s, frontmost, waited_min, note.`, { label: 'rc1-gui-presence', phase: 'GUI', model: 'sonnet', effort: 'medium', schema: PRESENCE })
  if (!presence || !presence.away) {
    log('GUI round deferred: operator present (last idle ' + (presence ? presence.idle_s : '?') + ' s < 1500 s over ' + GUI_WAIT_MIN + ' min) — needs_gui stays: ' + pre.needs_gui.join(', '))
    gui = { status: 'deferred', per_entry: [], deferred: pre.needs_gui, idle_rule: idleRule, stops: ['operator present for the whole ' + GUI_WAIT_MIN + '-minute window'], summary: 'deferred: operator present' }
  } else {
    gui = await run(`${COMMON}

${facts(tagSha, tagWt)}

ROLE: GUI ROUND (Opus; label rc1-gui). You are the ONLY GUI owner and the heavy-lane owner now; COMMON's 'No GUI' is lifted for you alone, under these rules. ${STALL}
GRANT, FIRST, before building anything: ToolSearch 'computer-use' (the whole toolkit in one call), then mcp__computer-use__list_granted_applications. The run's grant was recorded for the Vysted bundle 'com.vysted.desk'; the built app's identifier is what ${tagWt}/src-tauri/tauri.conf.json says (com.vysted.terminal when this was written) — they may differ. Continue only if the granted list contains the built app (its identifier or name). Otherwise never call request_access (he is away): return status 'deferred', every entry deferred, stops ['computer-use not granted: granted <list>, built app <identifier>'].
PRESENCE, immediately before launching the app and before EVERY click/type/capture batch: ${IDLE_CMD} must be ≥ 1500, and ${FRONT_CMD} must be your app or the one you last raised. Append every check (time, idle, frontmost) to ${EV}/gui/presence.log. Idle < 1500 → stop; re-check with separate 'sleep 100' calls for up to 20 min, else quit your app and defer the rest. A frontmost surprise = hard stop: delete that batch's captures, quit your app, defer the rest. Operator presence always means deferred, never failed.
APP: in ${tagWt} run pnpm tauri build --debug (static frontend, the three sidecars, the packaged tauri:// origin R15-CODE-AGENT-001 needs). Home = ${SCRATCH}/rc1-gui-home: seed <home>/Library/Application Support/com.vysted.terminal from a copy of ${SEED} and confirm its dev-keystore.json reads {"secrets": {}, "migrated": true} (r15/stage0/ISOLATION_MAP.md §2.4: without it the app sweeps his real keychain). Launch the BUILT binary with HOME=<home> (§1.2: on the binary, never the toolchain). HIS DATA IS UNTOUCHABLE: never read, write or launch against the real-home ~/Library/Application Support/com.vysted.terminal, ~/Library/Caches/vysted-terminal or ~/Library/WebKit/vysted-terminal (stat for mtime only), and never add, read or delete an OS keychain item. Record the real data dir's mtime before launch and after you quit: any change, or any keychain/SecurityAgent dialog (deny it), = hard stop, quit your app, record it in stops. Prove isolation before any interaction: the app's data dir and diag log are under <home>. Never touch his own Vysted instance: match windows by YOUR pid. RIG: tauri-mcp and playwright are NOT connected: computer-use, plus the Quartz capture /tmp/rigcap.py (re-create if missing; only sidecar/.venv/bin/python has pyobjc; match kCGWindowOwnerPID = your pid). ENTRIES: every register entry with status needs_gui (preflight saw ${JSON.stringify(pre.needs_gui)}); its note holds the verifier's GUI check: run exactly that. Populate first (watchlist AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT; portfolio ≥1 position with P&L; a note). Proof shots: POPULATED panels, dark theme, launched size recorded, saved under docs/screenshots/vr15-rc1/, never overwriting. Per entry: certified (on screen + read-back), failed (also a finding kind regression), or deferred (presence or rig reason). Quit your app by its pid; nothing else. Return model, status, per_entry[{id, verdict, evidence}], deferred, idle_rule, stops, summary ≤150 words.`, { label: 'rc1-gui', phase: 'GUI', model: 'opus', effort: 'high', schema: GUI })
    if (!gui) gui = { status: 'blocked', per_entry: [], deferred: pre.needs_gui, idle_rule: idleRule, stops: ['GUI agent died'], summary: 'GUI agent died' }
    const failed = gui.per_entry.filter(e => e.verdict === 'failed').map(e => e.id)
    if (failed.length) blockers.push('GUI round failed (after the fix loop — the lead opens a fix batch): ' + failed.join(', '))
    if (gui.deferred.length) log('GUI round deferred: ' + gui.deferred.join(', ') + ' — ' + gui.stops.join('; '))
  }
}

// ---------------------------------------------------------------- 6. Fresh adversarial verifier
phase('Verify')
// Three certified entries per writer set, picked by index (deterministic, varies across sets).
const sample = (batteryIndex ? batteryIndex.sets : []).map((s, i) => {
  const n = s.entries.length
  const start = (i * 7 + 3) % Math.max(n, 1)
  const picks = [...new Set([0, 1, 2].map(k => s.entries[(start + k) % n]))].filter(Boolean)
  return { set: s.set, picks }
}).filter(x => x.picks.length)
if (!sample.length) log('no writer sets indexed — the final verifier samples 3 fixed entries per batch itself')
const SHARD = 8
const shards = []
for (let k = 0; k * SHARD < sample.length; k++) shards.push(sample.slice(k * SHARD, (k + 1) * SHARD))
log('adversarial sample: ' + sample.reduce((n, x) => n + x.picks.length, 0) + ' entries over ' + sample.length + ' sets in ' + shards.length + ' shards')
const shardRes = (await parallel(shards.map((sh, k) => () => run(`${COMMON}

${facts(tagSha, tagWt)}

ROLE: ADVERSARIAL SAMPLE VERIFIER shard ${k} (Opus, fresh context; label rc1-vshard-${k}). Try to REFUTE that these certified entries are fixed at ${tagSha}: ${JSON.stringify(sh)}. Your inputs are the register entries (repro, evidence), the running app and the outside world — do NOT read anything under ${EV} or any VERDICTS.md conclusion. Your own sidecar from ${tagWt} (read-only) on :${52600 + k}. RUBRIC. For each id: run the ENTRY'S OWN stated repro at ${tagSha} (curl, vy.py on llama3.1:8b, in-process python with the worktree venv; screener.in, NSE/BSE, SEC EDGAR where the entry is data). 'refuted' ONLY when that repro reproduces THIS entry's defect. Then one fresh variant the fix was not written against: a different defect it (or anything else) turns up nearby is an ADJACENT finding (new, its own severity) returned in adjacent[], never a refutation. A docs entry is refuted only by a factual mismatch between the document and the code at ${tagSha}, never on taste, wording or completeness. CERTIFY THE CLAIM, NOT ONLY THE REPRO: an entry is certified only when its stated conclusion holds — its title, its fix_shape and its acceptance_test — checked against the running app with at least one fresh case the fix was not written against (a different symbol, phrasing, host, provider or file of the same class). A fix that holds the entry's literal repro but leaves any part of the title claim or fix_shape unfixed is not_certified, with the unfixed claim named in the reason and the fresh case recorded as its repro. Every refutation records the exact command, the checkout sha it ran in ('git rev-parse HEAD' in that directory) and the output. holds / refuted / inconclusive (say what blocked you: a lock_timeout or upstream 5xx is inconclusive), each with an evidence excerpt. Write ${EV}/verifier/shard-${k}.md. Stop your sidecar. Return model, shard '${k}', checked[{id, verdict, evidence, command, checkout_sha}], adjacent[{near_id, title, severity, evidence}], evidence_file, summary ≤80 words.`, { label: 'rc1-vshard-' + k, phase: 'Verify', model: 'opus', effort: 'high', schema: VSHARD })))).filter(Boolean)
const refuted = shardRes.flatMap(s => s.checked.filter(c => c.verdict === 'refuted').map(c => c.id + ' (' + (c.checkout_sha || 'no sha').slice(0, 7) + ': ' + (c.command || 'no command') + ')'))
const adjacent = shardRes.flatMap(s => s.adjacent || [])
if (shardRes.length < shards.length) log('verifier shards missing: ' + (shards.length - shardRes.length))

const verifier = await run(`${COMMON}

${facts(tagSha, tagWt)}

ROLE: FRESH ADVERSARIAL GATE VERIFIER (Opus, xhigh; label rc1-verifier). You decide whether rc1 may be tagged at ${tagSha}. Default to FAIL where the evidence does not carry the claim. Treat every PASS written by another agent as a claim to refute.

INPUTS — EVIDENCE ONLY. You may open: the register; the raw evidence other agents saved — ${EV}/gate8/* (raw lists and outputs), ${EV}/logs/ci-local.log and smoke.log, ${EV}/fix-r*/ci-local.log and smoke.log, ${EV}/scenarios/*.jsonl, docs/redesign/verification/r15/surface/*/rc1/*, ${EV}/battery/raw/**, ${EV}/battery/collected/*, ${EV}/gui/presence.log, docs/screenshots/vr15-rc1/, ${EV}/findings/*.json (defect claims to re-run, never verdicts), your own sample shards ${EV}/verifier/shard-*.md; plus the running app and the outside world. NEVER read another agent's conclusions, before or after your verdict: PREFLIGHT.md, GATE8.md, gate8.json, REGRESSION.md, SCENARIOS.md, OWNER_DRIVE.md, drives/*.md, BATTERY.md, battery/INDEX.md, battery/set-*.md, DATAPACK.md, datapack.json, FINDINGS.*, fix-r*/PLAN.md, INTEGRATION.md, RECHECK.md, GUI_ROUND.md, logs/*.md. The register statuses and stage-c VERDICTS.json lists are the record the register criterion is checked against, never proof that a fix still holds. Outcomes quoted below (triage rejections, the GUI round) are claims to refute, not inputs to trust. Your own sidecar from ${tagWt} (read-only) on :52312 with a seed copy.

WORK.
1. Gate 8, refute independently: your own GET /openapi.json path list; your own catalog + MCP tool lists (python with the worktree venv); your own rg sweeps over src/, sidecar/, src-tauri/, plugins/, docs/ with terms the test's token list does not cover ('place order', 'buy now', 'execute trade', 'paper trading', 'simulated account', 'live mode', 'broker', 'demat', 'leverage', 'margin'), classifying every hit as product surface / historical record / false positive; read the Settings sections and the first-launch terms text; then one tracked-portfolio round trip (add with cost basis, P&L vs a live quote, CSV export path, delete) and one gated agent write on llama3.1:8b (--autonomy ask: proposed, ledger unchanged until applied), read back.
2. Register criterion (RUBRIC a): read the register AT THE CANDIDATE ('git show ${tagSha}:docs/redesign/verification/vysted-r15-register.json'). ONLY entries with status exactly 'open' at severity critical/high/medium fail this criterion. blocked_tier4, needs_gui, not_a_defect and removed_with_feature are closed for this run: list them in the sheet as operator-attended, never as failures. A 'fixed' entry with no certification anywhere (no stage-c VERDICTS.json certified list, no rc1 battery raw output that holds) is listed as 'fixed-uncertified' — a finding, not a criterion failure — unless YOUR OWN probe of its repro reproduces the defect, which makes it a failure (record command, sha, output). Lows may stay open (rc2). Exception that overrides the closed-for-the-run rule: an entry whose named area is one of the four (ui-panels, agent-chat, research-search, data-smallcaps — its 'area' field, else the surface in its id/notes) and whose status is not_a_defect, out_of_scope or removed_with_feature needs a RECORDED fresh concurrence — its id in a concur_not_defect list of some docs/redesign/verification/r15/stage-c/batch-*/VERDICTS.json, or a rc1 verifier concurrence in r15/rc1/findings/rc1-verifier.json. Where none exists, give yours now (re-read the entry's own repro against the candidate and record concur or refuse with evidence in your area_concurrences return field) or refuse it; a refused entry is an open defect for this criterion → FAIL. Nothing in the four named areas is adjudicated away without a fresh verifier's concurrence.
3. Fix-loop rejections the triage made — concur or refuse each, with evidence: ${JSON.stringify(rejectedAll)}. Unclosed: ${JSON.stringify(open.map(f => f.key))}. Tier-4 deferred: ${JSON.stringify(deferredAll.map(x => x.key))}.
4. Regression suite: ci-local EXIT=0 from a clean sidecar build AT ${tagSha} (${tagSha === SHA ? 'the heavy lane ran it in ' + CAND : 'the last fix round ran it in ' + FIXWT}; read the raw log tail and the per-stage counts yourself); smoke EXIT=0; the scenario transcripts; the owner-drive raw evidence for all ${DRIVE_GROUPS.length} groups; the battery raw output (entries with no result: ${JSON.stringify(battMissing)}; fixed ids with no raw file per the collator, a claim to check on disk: ${JSON.stringify(battNoRaw)} — the battery item is never PASS while any fixed id lacks raw output) and the data-pack raw output. Spot-check at least two drives yourself on your sidecar.
5. Adversarial sample (RUBRIC b). Your shards refuted: ${JSON.stringify(refuted)}${sample.length ? '' : ' (no shards ran: pick 3 fixed entries per stage-c batch by position and re-run their original repros yourself)'}; adjacent findings they filed: ${JSON.stringify(adjacent)}. A refutation stands ONLY if the entry's own stated repro reproduces the entry's defect at ${tagSha} — re-run it yourself and record the exact command, 'git rev-parse HEAD' of the directory it ran in, and the output; a refuted entry that holds on your re-run is not a blocker. A different defect found nearby is an adjacent finding (new, its own severity; c/h/m ones are blockers as new defects, not refutations). A docs entry is refuted only by a factual mismatch between the document and the code at ${tagSha}, never on taste.
6. GUI round${SKIP_GUI ? ' — SKIPPED by args.skip_gui (the computer-use grant does not cover the built app): read every id with status needs_gui from the register at ' + tagSha + ' and list each in the sheet as operator-attended with the reason \'computer-use grant does not cover the built app\'; the GUI item reads DEFERRED with cause operator_attended, never FAIL. As recorded' : ', as claimed'}: status ${gui.status}; deferred ${JSON.stringify(gui.deferred)}; rule: ${gui.idle_rule}. A GUI-certified id counts only with its populated proof shot in docs/screenshots/vr15-rc1/ and presence readings in ${EV}/gui/presence.log bracketing it; else it stays needs_gui. The brief allows deferring the GUI proof, not the fix: a deferred entry stays needs_gui and the item reads DEFERRED, not FAIL.

WRITE docs/redesign/verification/R15_GATE_RC1.md — the sheet the lead reads: one PASS/FAIL/DEFERRED line per gate item (register criterion; Gate 8 no trading path; Gate 8 tracked portfolio; ci-local; smoke; agent scenarios; owner-drives; fixed-name battery; data packs; fix loop closed; GUI round; adversarial sample) with the evidence path for each, and for every FAIL or DEFERRED item its cause: product defect, harness/environment (lock_timeout, upstream 5xx, missing grant, a lane that produced no output) or operator-attended (blocked_tier4 / needs_gui / not_a_defect / removed_with_feature, a skipped GUI round); an operator-attended section listing those ids with status and reason; the fixed-uncertified ids; the adjacent findings; the blockers; the exact ids still needs_gui; a 'four named areas' section: for each of ui-panels, agent-chat, research-search, data-smallcaps, one line naming the before evidence (the census drive under r15/surface/<group>/ or the R15 gate-2 sheet) and the after evidence (the rc1 owner-drive raw output under r15/rc1/drives/ and the battery shards) with the count of entries in that area by status at the candidate, plus the list of not_a_defect/out_of_scope/removed_with_feature ids in that area with the concurrence pointer for each (or 'refused'); the sha to tag (you never tag it: ${tagSha}${tagSha === SHA ? '' : ': the head of ' + FIXBR + ', a fast-forward of ' + SHA + '; the lead fast-forwards 004 to it'}; if 004 has moved past it, say the tagged tree must be this sha or the gate re-runs). Then ${EV}/VERDICT.md with the evidence excerpt behind every line. Overall PASS only if every item is PASS or an allowed DEFERRED. Stop your sidecar. Return model, verdict, gate_items[{item, result, cause, evidence}], gate8_refuted, refuted_entries, operator_attended, fixed_uncertified, adjacent_findings, blockers, needs_gui, tag_sha, sheet_file, summary ≤200 words.`, { label: 'rc1-verifier', phase: 'Verify', model: 'opus', effort: 'xhigh', schema: VERDICT })
if (!verifier) blockers.push('final verifier died: no gate sheet')
else blockers.push(...verifier.blockers)
log('verifier: ' + (verifier ? verifier.verdict + ' — tag ' + (verifier.tag_sha || '').slice(0, 7) : 'no result'))

return {
  status: verifier && verifier.verdict === 'PASS' ? 'PASS' : 'FAIL',
  gate8: g8 ? { status: g8.status, findings: g8.findings.length, summary: g8.summary } : null,
  regression: heavy ? { status: heavy.status, counts: heavy.counts, fix_rounds: rounds } : { status: 'missing', fix_rounds: rounds },
  scenarios: scen ? { status: scen.status, counts: scen.counts } : null,
  drives: drives.map(d => ({ lane: d.lane, status: d.status, findings: d.findings.length })),
  battery: { status: collate ? collate.battery_status : 'unknown', no_raw: battNoRaw, shards: battery.length, of: batteryShards.length, sets: expectedSets.length, entries: expectedIds.length, by_verdict: battTally, missing: battMissing, regressed: battery.flatMap(b => b.findings).filter(f => f.kind === 'regression').length, datapack: pack ? pack.status : null },
  gui: { status: gui.status, per_entry: gui.per_entry, deferred: gui.deferred },
  verifier: verifier ? { verdict: verifier.verdict, gate_items: verifier.gate_items, sheet: verifier.sheet_file, gate8_refuted: verifier.gate8_refuted, refuted_entries: verifier.refuted_entries, operator_attended: verifier.operator_attended, fixed_uncertified: verifier.fixed_uncertified, adjacent_findings: verifier.adjacent_findings } : null,
  tag_sha: verifier && verifier.verdict === 'PASS' ? verifier.tag_sha : null,
  candidate_sha: tagSha,
  blockers: [...new Set(blockers)],
  deferred_needs_gui: verifier ? verifier.needs_gui : gui.deferred,
}
