export const meta = {
  name: 'r15-lows-triage',
  description: 'R15 lows pre-triage: re-check every open low register entry at a 004 sha (read-only checkout with symlinked deps, git history, its own GET-only sidecar at the sha on :52350, the outside world, focused tests) and record already_fixed / still_reproduces / not_a_defect_proposed / duplicate_of / blocked with evidence; an Opus critic re-runs a sample; a collator commits the evidence dir',
  whenToUse: 'Before the R15 low fix batches, on 004-r4-experience-rebuild; args {sha, shard_size, cap, exclude_ids, only_ids, dry_run}',
  phases: [
    { title: 'Index', detail: 'open lows at the sha, scratch checkout + own sidecar on :52350, shards by locality' },
    { title: 'Refute', detail: 'one Fable agent per shard, one jsonl verdict line per entry', model: 'fable' },
    { title: 'Critic', detail: 'Opus re-runs a sample of already_fixed + low-confidence not-a-defect', model: 'opus' },
    { title: 'Collate', detail: 'LOWS_TRIAGE.json/.md, stop the own sidecar, remove the checkout, commit the evidence dir' },
  ],
}

const A = args || {}
if (!A.sha || !/^[0-9a-f]{7,40}$/i.test(String(A.sha))) throw new Error('lows-triage: REFUSED - args.sha (the 004-r4-experience-rebuild commit to check against, 7-40 hex chars) is required')
const REPO = '/Users/lokavyasingh/Documents/dev/vysted-terminal'
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const SHA_IN = String(A.sha).toLowerCase()
const SH7 = SHA_IN.slice(0, 7)
const posInt = (v, d) => (Number.isInteger(+v) && +v > 0 ? +v : d)
const SHARD_SIZE = posInt(A.shard_size, 12)
const CAP_ASKED = posInt(A.cap, 8)
const CAP = Math.min(16, CAP_ASKED)
if (CAP_ASKED > 16) log('cap ' + CAP_ASKED + ' is over the 16-agent ceiling - clamped to 16')
const EXCLUDE = Array.isArray(A.exclude_ids) ? A.exclude_ids.map(String) : []
const ONLY = Array.isArray(A.only_ids) && A.only_ids.length ? A.only_ids.map(String) : null
const DRY = A.dry_run === true || A.dry_run === 'true'
const EVR = 'docs/redesign/verification/r15/stage-c/lows-triage'
const EV = REPO + '/' + EVR
const REG = 'docs/redesign/verification/vysted-r15-register.json'
const WT = SCRATCH + '/lows-triage-' + SH7
const VERDICTS = ['already_fixed', 'still_reproduces', 'not_a_defect_proposed', 'duplicate_of', 'blocked']

// Pacing: this wave holds at most CAP agents at once, whatever the machine's CPU count.
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
const GLOBAL = limiter(CAP)
const once = (prompt, opts) => GLOBAL(() => agent(prompt, opts)).catch(e => { log('agent ' + opts.label + ' failed: ' + e); return null })
// Routing change 3: a strongest-tier agent that dies or starves gets ONE fallback to the workhorse tier, never a third identical try.
const run = (prompt, opts) => once(prompt, opts).then(r => (r || opts.model !== 'fable') ? r : (log('agent ' + opts.label + ' on fable returned nothing (wave died or starved) - one fallback to opus'), once(prompt, { ...opts, model: 'opus', label: opts.label + '-opus' })))

const COMMON = `Repo: ${REPO}, integration branch 004-r4-experience-rebuild. This is the R15 LOWS PRE-TRIAGE wave: READ-ONLY re-checking of open low register entries at one sha. You fix nothing. The operator is away; never ask, decide and record. Before any pnpm/node command: export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH. Never print, log or copy a secret (no keystore, keychain, env dump or auth header); never read docs/redesign/verification/R15_BRIEF*.md or docs/redesign/verification/r15/local/ (any grep over docs/ passes --exclude='R15_BRIEF*' --exclude-dir=local). No GUI of any kind. Trading is out of the product (D81, a122dbf6 feat(d81)): never propose re-adding any of it. Never tag, merge to main, push anything, open a PR or force-push; never commit unless your role says so. Never edit a tracked file: your only writes are your own evidence files under ${EV}. Never speculate about code you have not opened: file:line at the sha for every code claim, command + output excerpt for every probe, URL + quote for every world claim. Batch 9 runs concurrently: its writers live in .claude/worktrees and its adjudicator commits on 004 in ${REPO}. Never touch their worktrees, branches, ports or files, and never git checkout/reset/stash/add/commit in ${REPO} (the collator's one commit excepted). HARNESS STALL RULE (a 3-minute no-progress watchdog kills the agent and restarts it from scratch): NO single tool call may run longer than ~120 s. Anything longer MUST be started detached ('nohup <cmd> > <log> 2>&1 &') and polled with SEPARATE short calls ('sleep 30; tail -n 5 <log>'), never an 'until … sleep' loop inside one call. Keep emitting a tool call at least every 2 minutes. If you find output files from a previous attempt of your own role (a restart), read them and CONTINUE from them. Shell: cat is aliased to bat and ls to eza (both can hang): use /bin/cat, /bin/ls or your Read tool. Your final text IS the return value: return only the structured object.`

const facts = (sha, ix) => `TRIAGE FACTS. Sha ${sha} (on 004-r4-experience-rebuild). The register AT THE SHA: ${WT}/${REG} (entries: id, title, severity, area, subsystem, files, repro, evidence, root_cause, fix_shape, defect_class, note, raw_ids, tier4, operator_areas, status; a 'note' from a batch verifier or adjudicator corrects the raw repro where they conflict). Stage C fix history: git -C ${REPO} log --oneline a122dbf6..${sha} (batch 2-9 merge commits name their register ids); per-batch PLAN.md / VERDICTS.md / VERDICTS.json under ${REPO}/docs/redesign/verification/r15/stage-c/batch-*/ (grep there with --exclude-dir=lows-triage). Evidence root ${EV}.
LANES YOU MAY USE: (1) the read-only scratch checkout ${WT} at the sha: read, grep, git -C ${WT} show/log/blame; never edit, install or build in it. (2) git show / log / blame in ${REPO}, read-only. (3) The wave's OWN main sidecar AT THE SHA: http://127.0.0.1:52350, GET requests only; ${ix.own_up ? 'UP' : 'NOT UP'} (${ix.own_stack}; record ${EV}/stack.json). It runs from ${WT} on an EMPTY keyless data dir with NO MCP sidecars (the MCP port env vars are unset), so openbb-mcp and sec-edgar-mcp backed routes degrade there by design; that degradation is not a finding. It is the probe target for at-sha evidence. (4) FALLBACK ONLY: the shared stack http://127.0.0.1:52152 (MCP :52153/:52154), GET only, runs an OLDER tree (${ix.stack_desc}). Use it only when ${EV}/stack.json says the own sidecar is not up; any verdict that leaned on it says so in its note ('probe on :52152, older tree') and its confidence is capped at 3. (5) The outside world via curl (browser UA, ≤1 request per 3 s per host). (6) Focused tests, each ≤120 s, inside ${WT}, whose sidecar/.venv and node_modules are READ-ONLY symlinks to the main worktree's (never install into or write through them): 'cd ${WT}/sidecar && PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest <file>::<test> -q -p no:cacheprovider' or 'cd ${WT} && pnpm exec vitest run --no-cache <file>'. The checkout ${ix.venv ? 'HAS sidecar/.venv' : 'LACKS sidecar/.venv (the symlink target was missing: skip pytest and say so)'} and ${ix.node_modules ? 'HAS node_modules' : 'LACKS node_modules (the symlink target was missing: skip vitest and say so)'}; a symlink whose target is missing means skip and say so. A test that fails on an import or dependency error (the sha's lockfiles differ from the main worktree's) is 'focused test inconclusive: deps', never a verdict.
LANES YOU MUST NEVER USE (another workflow owns them): the operator's live app, vite :5173 or any GUI; Ollama or any local model; the heavy-job lane (pnpm install, pnpm ci-local, a full pytest or vitest run, cargo anything, PyInstaller, sidecar builds, ensure-all-sidecars, tauri build); any agent run (POST /agents/*/invoke, /agents/*/runs, vy.py); any non-GET request to any sidecar; starting, stopping or restarting any process (the indexer starts the :52350 sidecar and the collator stops it; nobody else touches it); any write to the register or to a tracked file.`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }
const NUM = { type: 'number' }
const BOOL = { type: 'boolean' }
const STRS = { type: 'array', items: STR }
const VERDICT = { type: 'string', enum: VERDICTS }
const BYV = S(Object.fromEntries(VERDICTS.map(v => [v, STRS])))

const INDEX = S({ model: STR, status: { type: 'string', enum: ['ready', 'blocked'] }, sha: STR, shards: { type: 'array', items: S({ k: NUM, ids: STRS, hint: STR }) }, total: NUM, skipped: STRS, stack_desc: STR, venv: BOOL, node_modules: BOOL, own_up: BOOL, own_stack: STR, index_file: STR, blockers: STRS, summary: STR })
const REFUTE = S({ model: STR, shard: NUM, by_verdict: BYV, low_confidence: STRS, not_reached: STRS, jsonl_file: STR, md_file: STR, summary: STR })
const CRITIC = S({ model: STR, checked: { type: 'array', items: S({ id: STR, from: VERDICT, holds: BOOL, evidence: STR }) }, flips: { type: 'array', items: S({ id: STR, from: VERDICT, to: VERDICT, reason: STR }) }, unused_modalities: STRS, files: STRS, summary: STR })
const COLLATE = S({ model: STR, sha: STR, by_verdict: BYV, missing: STRS, files: STRS, sidecar_stopped: STR, worktree_removed: BOOL, commit: STR, summary: STR })

// ---------------------------------------------------------------- 1. Index
phase('Index')
const idx = await run(`${COMMON}

ROLE: INDEXER (Sonnet, mechanical; label lows-index). You build the work list; you judge no defect.
(1) Resolve: git -C ${REPO} rev-parse ${SHA_IN}^{commit} gives the full sha. It must be 004-r4-experience-rebuild or an ancestor (git merge-base --is-ancestor); otherwise status 'blocked' with the reason.
(2) Evidence dir: mkdir -p ${EV}. If ${EV}/INDEX.json exists for a DIFFERENT sha, an older triage owns the dir: delete everything under ${EV} (git keeps its history) and start fresh. If it exists for the SAME sha with the same selection (a restart), reuse its shards verbatim.
(3) Stack, read-only: ${SCRATCH}/vysted-iso/pids.json (sidecar_pid, started_at, ports); curl -s -m 5 127.0.0.1:52152/health; lsof -a -p <sidecar_pid> -d cwd -Fn for its cwd. Source head: when the cwd is ${REPO}/sidecar, the 004 commit current at started_at (git -C ${REPO} rev-list -1 --first-parent --before=<started_at> 004-r4-experience-rebuild); otherwise that cwd's git HEAD; unknown stays unknown. Never start, stop or restart it.
(4) Select from the register AT THE SHA (git -C ${REPO} show <sha>:${REG}): status == 'open' && severity == 'low'${ONLY ? ', restricted to only_ids ' + JSON.stringify(ONLY) : ''}, minus exclude_ids ${JSON.stringify(EXCLUDE)}. Each id a filter drops, or an only_id that is absent, not open or not low, goes to skipped[] as '<id>: <reason>'.
(5) ${DRY ? 'DRY RUN: do NOT create the scratch checkout or start any sidecar; venv, node_modules and own_up are false, own_stack is \'dry run\'.' : `Scratch checkout: git -C ${REPO} worktree add --detach ${WT} <sha>. If ${WT} already exists at the sha (a restart), reuse it; at another sha, stop its sidecar as the collator would, then git -C ${REPO} worktree remove --force ${WT} (that path only, never prune) and add it again. Dependencies, READ-ONLY: ln -s ${REPO}/sidecar/.venv ${WT}/sidecar/.venv and ln -s ${REPO}/node_modules ${WT}/node_modules, each only if its target exists and the link does not; never install, never write into either target. venv / node_modules = whether each link resolves.
(5b) The wave's OWN main sidecar at the sha, on 127.0.0.1:52350 (the wave owns that port; nothing else in the run uses it). Restart first: if ${EV}/stack.json records a pid whose 'ps -o command= -p <pid>' contains ${WT} and GET :52350/health answers, reuse it. If :52350 answers but no such record matches, never kill it: own_up false, reason ':52350 held by an unknown process'. Otherwise: mkdir -p ${WT}/.lows-triage-data and write ${WT}/.lows-triage-data/dev-keystore.json as exactly {"secrets": {}, "migrated": true} (chmod 600; r15/stage0/ISOLATION_MAP.md §2.4: without it the first boot sweeps the operator's real keychain). Start it detached, per the 'Main sidecar, from source' recipe in docs/redesign/verification/r15/stage0/ISO_STACK.md, main sidecar only, with VYSTED_OPENBB_MCP_PORT and VYSTED_SEC_EDGAR_MCP_PORT UNSET so the MCP-backed routes degrade: (bash -c 'cd ${WT}/sidecar; unset VYSTED_OPENBB_MCP_PORT VYSTED_SEC_EDGAR_MCP_PORT; sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52350 --data-dir ${WT}/.lows-triage-data > ${SCRATCH}/lows-triage-${SH7}-sidecar.log 2>&1' &). Poll curl -s -m 5 127.0.0.1:52350/health in SEPARATE short calls ('sleep 10' between them) for up to ~3 minutes. Then pid = lsof -nP -t -iTCP:52350 -sTCP:LISTEN; confirm 'ps -o command= -p <pid>' contains ${WT}; wrapper_pid = its ppid; stdin_pid = pgrep -P <wrapper_pid> -x sleep. Write ${EV}/stack.json as {up, pid, stdin_pid, wrapper_pid, port: 52350, sha, started_at, health_excerpt, log, reason}. Not healthy in time: up false, reason = the log tail (≤10 lines, no secrets); the wave then falls back to :52152.`}
(6) Shard by locality: same subsystem first, then shared files (the entry's files[]), then area, into shards of about ${SHARD_SIZE} (never more than ${SHARD_SIZE + 4}). Two entries naming the same file stay in one shard unless that breaks the size limit. Order the ids in a shard by file. k = 0..n-1 in array order. hint = one line naming the subsystem(s) and the main files/dirs. Every selected id sits in exactly one shard.
Write ${EV}/INDEX.json as {sha, shards:[{k, ids, hint}], total, skipped, stack:{pid, cwd, started_at, source_head, health}, checkout:{path, venv, node_modules}} and ${EV}/INDEX.md (table k | size | hint | ids, then skipped, stack, checkout).
Return model, status, sha (full), shards, total, skipped, stack_desc (one line: 'pid <p> from <cwd>, started <t>, source head <sha or unknown>, health <ok|down>'), venv, node_modules, own_up, own_stack (one line: 'pid <p> on :52350 at <sha7>, health <excerpt>' or the reason it is not up), index_file, blockers, summary ≤80 words.`, { label: 'lows-index', phase: 'Index', model: 'sonnet', effort: 'medium', schema: INDEX })

if (!idx || idx.status !== 'ready') {
  const why = idx ? (idx.blockers.length ? idx.blockers : ['index status ' + idx.status]) : ['indexer died']
  log('index blocked - the wave does not run: ' + JSON.stringify(why))
  return { status: 'blocked', sha: idx && idx.sha ? idx.sha : SHA_IN, counts: null, files: [], missing: [], commit: null, blockers: why }
}
const SHA = idx.sha
// Re-apply the filters and one-shard-per-id to what the indexer returned; anything dropped is logged.
const excl = new Set(EXCLUDE)
const only = ONLY ? new Set(ONLY) : null
const seen = new Set()
const stray = []
const kOk = new Set(idx.shards.map(s => s.k)).size === idx.shards.length && idx.shards.every(s => Number.isInteger(s.k) && s.k >= 0)
if (!kOk) log('indexer shard numbers are not unique non-negative integers - using array positions (INDEX.json k may differ)')
const shards = idx.shards.map((s, i) => ({
  k: kOk ? s.k : i,
  hint: s.hint,
  ids: s.ids.filter(id => {
    const keep = !excl.has(id) && (!only || only.has(id)) && !seen.has(id)
    if (!keep) stray.push(id)
    seen.add(id)
    return keep
  }),
})).filter(s => s.ids.length)
const selected = new Set(shards.flatMap(s => s.ids))
if (stray.length) log('script dropped ' + stray.length + ' ids the indexer sharded against the filters or twice: ' + stray.join(', '))
if (selected.size !== idx.total) log('indexer total ' + idx.total + ' != ' + selected.size + ' ids in shards')
if (idx.skipped.length) log('skipped ' + idx.skipped.length + ': ' + idx.skipped.join('; '))
const big = shards.filter(s => s.ids.length > SHARD_SIZE + 4)
if (big.length) log('oversize shards (> ' + (SHARD_SIZE + 4) + '): ' + big.map(s => s.k + ':' + s.ids.length).join(', '))
log('index @ ' + SHA.slice(0, 7) + ': ' + selected.size + ' open lows in ' + shards.length + ' shards (sizes ' + shards.map(s => s.ids.length).join('/') + '), cap ' + CAP + ' => ' + Math.ceil(shards.length / CAP) + ' round(s); stack ' + idx.stack_desc)
if (!DRY && !idx.venv) log('scratch checkout has no sidecar/.venv (symlink target missing): pytest focused tests are skipped this wave')
if (!DRY && !idx.node_modules) log('scratch checkout has no node_modules (symlink target missing): vitest focused tests are skipped this wave')
if (!DRY) log(idx.own_up ? 'own sidecar at the sha: ' + idx.own_stack : 'own sidecar on :52350 NOT up (' + idx.own_stack + ') - probes fall back to the older :52152 stack, confidence capped at 3')

if (DRY) {
  log('dry run: INDEX.json / INDEX.md written (uncommitted); no scratch checkout, nothing refuted, nothing committed')
  return { status: 'dry_run', sha: SHA, counts: { selected: selected.size, shards: shards.length, skipped: idx.skipped.length }, files: [EVR + '/INDEX.json', EVR + '/INDEX.md'], missing: [], commit: null }
}
const F = facts(SHA, idx)

// ---------------------------------------------------------------- 2. Refute
phase('Refute')
const tally = Object.fromEntries(VERDICTS.map(v => [v, []]))
const lowConf = new Set()
const dead = []
await pipeline(shards,
  (_, sh) => run(`${COMMON}

${F}

ROLE: REFUTER shard ${sh.k} (Fable, fresh context; label lows-refute-${sh.k}). Shard hint: ${sh.hint}. Entries, in this order: ${JSON.stringify(sh.ids)}. For EACH entry decide whether its defect still exists AT THE SHA, and try hardest to refute the comfortable answer. Budget about 2-3 minutes per entry: the cheapest decisive probe, not an investigation. If deciding needs more, return still_reproduces with confidence ≤2 and say what would decide it.
RESTART FIRST: if ${EV}/shard-${sh.k}.jsonl exists, read it, skip every id already in it and continue from the first id not yet present. Never rewrite existing lines.
PER ENTRY, in order: (a) read the entry in the register at the sha; (b) git -C ${REPO} log --oneline a122dbf6..${SHA} -- <its files>, and git log --grep=<the id without 'R15-'> over the same range (mind prefix collisions: AGENT-007 also matches CODE-AGENT-007); grep the id in the stage-c batch dirs; (c) open the code at the sha in ${WT} at the lines the entry cites; (d) RE-RUN the original repro at the sha by the cheapest allowed lane: the grep or read the repro names, re-run in ${WT}; a GET on :52350 (the :52152 fallback only as the lanes allow); curl to the world; or a focused test. Save raw outputs under ${EV}/evidence/<id>/ (excerpts, each file ≤100 KB, never a secret) or inline them as 'cmd: <command> => <excerpt>'.
VERDICTS. already_fixed: fix_commit = the sha + subject that changed the cited lines (git log/blame), AND a fresh probe or focused test at the sha shows the original repro no longer reproduces. Never already_fixed without that fresh probe. still_reproduces: fix_shape {files, acceptance_test (what to pin, where), effort S|M|L, collides: none|trading_removal|redesign, with why}; a partial fix is still_reproduces with the residual named. not_a_defect_proposed: the reason grounded in code at the sha (file:line) or in the spec (specs/, .specify/memory/constitution.md, docs/BLUEPRINT.md, file:line). duplicate_of: the surviving register id, its status at the sha, and why the root cause is the same. blocked: blocked_kind needs_gui|operator|tier4 with the reason, only when no allowed lane can decide it. DEFAULT WHEN UNCERTAIN: still_reproduces (the cheap error). Confidence 1-5 (5 = reproduced or disproved by a fresh probe).
APPEND one line to ${EV}/shard-${sh.k}.jsonl IMMEDIATELY after each entry, before starting the next (python json.dumps, one object per line): {id, verdict, fix_commit, duplicate_of, blocked_kind, fix_shape, reason, evidence_paths, confidence, note, model}, null where not applicable; reason ≤60 words; note ≤40 words; evidence_paths are ${EVR}/evidence/<id>/... paths or 'cmd: … => …' strings.
At the end write ${EV}/shard-${sh.k}.md: a header (shard, sha, hint, model) and one row per entry: id | verdict | fix commit / duplicate / blocked kind | confidence | evidence | reason.
Return model, shard ${sh.k}, by_verdict {already_fixed, still_reproduces, not_a_defect_proposed, duplicate_of, blocked} as id lists covering every line in your jsonl, low_confidence (ids at confidence ≤3), not_reached, jsonl_file, md_file, summary ≤80 words.`, { label: 'lows-refute-' + sh.k, phase: 'Refute', model: 'fable', effort: 'high', schema: REFUTE }),
  (r, sh) => {
    if (!r) {
      dead.push(sh.k)
      log('shard ' + sh.k + ': no result after the fallback - its partial shard-' + sh.k + '.jsonl still counts; the collator lists the ids it never reached')
      return null
    }
    const got = new Set()
    const foreign = []
    for (const v of VERDICTS) for (const id of r.by_verdict[v]) {
      if (!sh.ids.includes(id)) foreign.push(id)
      else if (!got.has(id)) { tally[v].push(id); got.add(id) }
    }
    r.low_confidence.forEach(id => lowConf.add(id))
    const gap = sh.ids.filter(id => !got.has(id))
    log('shard ' + sh.k + ' done: ' + VERDICTS.map(v => v + ' ' + r.by_verdict[v].length).join(', ') + (gap.length ? '; not reached ' + gap.join(', ') : '') + (foreign.length ? '; ignored ids outside the shard ' + foreign.join(', ') : ''))
    return { k: sh.k, gap }
  })

// ---------------------------------------------------------------- 3. Critic
phase('Critic')
const af = tally.already_fixed.slice().sort()
const m = Math.min(af.length, Math.max(8, Math.ceil(af.length / 10)))
const sampleAF = Array.from({ length: m }, (_, i) => af[Math.floor((i * af.length) / m)])
const nadLow = tally.not_a_defect_proposed.filter(id => lowConf.has(id))
log('critic sample: ' + m + ' of ' + af.length + ' already_fixed (' + (af.length - m) + ' unsampled; the next batch verifier still certifies each), ' + nadLow.length + ' low-confidence not_a_defect_proposed (' + (tally.not_a_defect_proposed.length - nadLow.length) + ' at confidence 4-5 go to the verifier concur list unsampled)' + (dead.length ? '; plus the jsonl lines of dead shards ' + dead.join(', ') : ''))
let critic = null
if (!m && !nadLow.length && !dead.length) log('critic skipped: nothing to sample')
else {
  critic = await run(`${COMMON}

${F}

ROLE: CRITIC (Opus, fresh context; label lows-critic). Try to REFUTE the wave's comfortable verdicts. The script chose the sample deterministically: already_fixed ${JSON.stringify(sampleAF)} (${m} of ${af.length}), and every not_a_defect_proposed at confidence ≤3: ${JSON.stringify(nadLow)}.${dead.length ? ` Shards whose agents returned nothing: ${JSON.stringify(dead)}; their partial ${EV}/shard-<k>.jsonl lines were never sampled, so add every tenth already_fixed line by line order (at least 1 per such shard that has any) and every not_a_defect_proposed line at confidence ≤3.` : ''}
For each: read its line in ${EV}/shard-*.jsonl and its evidence, then RE-RUN its probe yourself at the sha (the same command, on :52350 where the original used :52152, plus one fresh variant the verdict did not look at). For already_fixed, read the fix commit's diff (git show) and confirm it touches the cited mechanism. For not_a_defect_proposed, re-check the reason against the code or spec line it cites. holds = keep; does not hold = FLIP, to still_reproduces or to whatever verdict your own evidence supports, with the reason. Never flip toward already_fixed or not_a_defect_proposed without a fresh probe of your own. Raw outputs to ${EV}/evidence/critic/<id>.txt.
Then name the allowed modalities the wave did NOT use, or used too little, by scanning the evidence_paths in every shard jsonl: focused tests skipped, no :52152 probe, no outside-world check, verdicts resting on code reading alone. Count them per verdict.
Write ${EV}/CRITIC.json as {sha, checked:[{id, from, holds, evidence}], flips:[{id, from, to, reason, evidence}], unused_modalities:[...]} and ${EV}/CRITIC.md (the sample, per-id result, the flips table, unused modalities with counts). Return model, checked, flips, unused_modalities, files, summary ≤100 words.`, { label: 'lows-critic', phase: 'Critic', model: 'opus', effort: 'high', schema: CRITIC })
  if (!critic) log('critic returned nothing - no flips applied; the collator says so at the top of LOWS_TRIAGE.md')
}

const final = {}
for (const v of VERDICTS) for (const id of tally[v]) final[id] = v
for (const f of critic ? critic.flips : []) {
  if (!selected.has(f.id)) { log('critic flip on an id outside the selection ignored: ' + f.id); continue }
  final[f.id] = f.to
}
if (critic) log('critic: ' + critic.checked.length + ' checked, ' + critic.flips.length + ' flipped' + (critic.flips.length ? ' (' + critic.flips.map(f => f.id + ' ' + f.from + '->' + f.to).join(', ') + ')' : '') + '; unused modalities: ' + critic.unused_modalities.join('; '))
const expect = Object.fromEntries(VERDICTS.map(v => [v, 0]))
Object.values(final).forEach(v => { expect[v]++ })
const expectMissing = [...selected].filter(id => !(id in final))

// ---------------------------------------------------------------- 4. Collate
phase('Collate')
const col = await run(`${COMMON}

ROLE: COLLATOR (Sonnet, mechanical; label lows-collate). No new judgement, no re-runs. Sha ${SHA}.
(1) Merge every ${EV}/shard-*.jsonl (if an id repeats, the LAST line wins; list repeats in the .md) with the flips in ${EV}/CRITIC.json (${critic ? critic.flips.length + ' flips expected' : 'the critic did not run or returned nothing: say so at the top of the .md'}). A flipped id takes the flip's 'to' verdict and its note gains 'critic flip: <reason>'. The expected ids are the shards in ${EV}/INDEX.json (${selected.size}). Write ${EV}/LOWS_TRIAGE.json as {sha, by_verdict:{already_fixed:[], still_reproduces:[], not_a_defect_proposed:[], duplicate_of:[], blocked:[]}, entries:{<id>:{verdict, fix_commit?, duplicate_of?, blocked_kind?, fix_shape?, evidence_paths, confidence, note}}, missing:[expected ids with no line]} and ${EV}/LOWS_TRIAGE.md: a counts table (verdict | n, plus missing and INDEX.json skipped), then per-verdict lists (already_fixed with its fix commit; still_reproduces with effort, files and collides; not_a_defect_proposed with the reason; duplicate_of with the target; blocked with its kind), the critic's flips and unused modalities, the missing ids.
(2) Stop the wave's own sidecar, then remove the scratch checkout. Read ${EV}/stack.json. No pid recorded → sidecar_stopped 'never_started'. 'ps -o command= -p <pid>' empty → 'already_gone'. It contains ${WT} → kill <pid> (plain TERM; never -9, never pkill/killall or any blanket kill), then kill the recorded stdin_pid only if 'ps -o command= -p <stdin_pid>' is exactly 'sleep 86400' (its stdin holder), and confirm both are gone in a separate call → 'killed'. It does NOT contain ${WT} → kill nothing → 'refused: <what the command line was>'. Then unlink the two dependency symlinks (rm ${WT}/sidecar/.venv ${WT}/node_modules: plain rm of the links, no trailing slash, never -r, so the main worktree's targets are untouched) and git -C ${REPO} worktree remove --force ${WT} (that path only, which also removes ${WT}/.lows-triage-data; never prune, never another worktree).
(3) Commit ONLY the evidence dir, on 004, never pushed. git -C ${REPO} rev-parse --abbrev-ref HEAD must print 004-r4-experience-rebuild; if not, do not commit (commit '' and the reason in summary), never checkout. Write the message to ${SCRATCH}/lows-triage-${SH7}.msg: subject 'docs(r15): lows pre-triage at ${SH7} - <n> already_fixed, <n> still_reproduces, <n> not_a_defect_proposed, <n> duplicate_of, <n> blocked, <n> missing', a blank line, then a trailer paragraph 'Co-Authored-By: Claude <the model you run as> <noreply@anthropic.com>' and 'Claude-Session: https://claude.ai/code/session_01HJVZfFSmtgR7p7eW5tKNCg'. Then, in ONE shell call so nothing else can commit between them: git -C ${REPO} add -A -- ${EVR} && git -C ${REPO} -c core.hooksPath=/dev/null commit --only -F ${SCRATCH}/lows-triage-${SH7}.msg -- ${EVR} (the pathspec with --only keeps anything another agent has staged out of this commit). If ${REPO}/.git/index.lock exists, wait 20 s in a separate call and retry, at most 5 times. Afterwards git -C ${REPO} show --stat --format= HEAD must list only files under ${EVR}; say so.
Return model, sha, by_verdict (as written), missing, files (repo-relative paths committed), sidecar_stopped, worktree_removed, commit (the full sha, or '' if none), summary ≤80 words.`, { label: 'lows-collate', phase: 'Collate', model: 'sonnet', effort: 'medium', schema: COLLATE })

if (!col) {
  log('collator died: nothing committed; the own sidecar on :52350 may still run (pid in ' + EVR + '/stack.json; kill it, then its sleep stdin holder) and the scratch checkout is still registered (git -C ' + REPO + ' worktree remove --force ' + WT + ')')
  return { status: 'partial', sha: SHA, counts: { ...expect, missing: expectMissing.length }, files: [], missing: expectMissing, commit: null }
}
const counts = Object.fromEntries(VERDICTS.map(v => [v, col.by_verdict[v].length]))
counts.missing = col.missing.length
const drift = VERDICTS.filter(v => counts[v] !== expect[v])
if (drift.length) log('collated counts differ from the agents\' returns (the jsonl files are authoritative): ' + drift.map(v => v + ' ' + expect[v] + '->' + counts[v]).join(', '))
log('own sidecar: ' + col.sidecar_stopped)
if (!col.worktree_removed) log('scratch checkout not removed: ' + WT)
if (!col.commit) log('collator did not commit: ' + col.summary)
log('lows pre-triage @ ' + SHA.slice(0, 7) + ': ' + VERDICTS.map(v => v + ' ' + counts[v]).join(', ') + ', missing ' + counts.missing + (col.commit ? '; commit ' + col.commit.slice(0, 7) : ''))
return { status: 'done', sha: SHA, counts, files: col.files, missing: col.missing, commit: col.commit || null }
