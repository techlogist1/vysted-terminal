export const meta = {
  name: 'r15-lows-remaining',
  description: 'Burst (pacing change 5): second attempt on the 7 could_not lows by Opus in their own worktrees, a fresh Opus refuter on the 3 not_a_defect_proposed, Sonnet writers for NEW_LOWS_DRAFT and the unwritten lows; off-lane, untested pending integration; a collator writes lows/remaining/',
  whenToUse: 'R15 burst window while the rc1 gate owns the machine lanes. args {base (sha), scratch, dry_run}',
  phases: [
    { title: 'Write', detail: 'Opus could_not retries + Sonnet writers, own worktrees from base' },
    { title: 'Refute', detail: 'one fresh Opus refuter over the not_a_defect_proposed trio' },
    { title: 'Collate', detail: 'Sonnet collator: REMAINING.json/.md by path' },
  ],
}
const A = args || {}
const BASE = String(A.base || '')
if (!/^[0-9a-f]{7,40}$/.test(BASE)) throw new Error('args.base (the rc1 candidate sha) is required')
const B7 = BASE.slice(0, 7)
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const DRY = A.dry_run === true || A.dry_run === 'true'
const OUT = 'docs/redesign/verification/r15/stage-c/lows/remaining'
const LOWS = 'docs/redesign/verification/r15/stage-c/lows'
const REG = 'docs/redesign/verification/vysted-r15-register.json'
const WBASE = 'ebc5ed4194f9362422c3178c27d4cdf946428968'

const once = (p, o) => {
  if (!['opus', 'sonnet'].includes(o.model) || !o.effort) throw new Error('agent ' + o.label + ': model opus|sonnet and effort must be explicit (routing change 5)')
  return agent(p, o)
}
const run = (p, o) => once(p, o).then(r => r ? r : (log('agent ' + o.label + ' returned nothing; one same-tier retry'), once(p, { ...o, label: o.label + '-retry' })))

const COMMON = `
RULES (R15 burst window, operator pacing change 5; every rule binds):
- Repo /Users/lokavyasingh/Documents/dev/vysted-terminal, branch 004-r4-experience-rebuild. BASE for this run: ${BASE}. The earlier lows writers branched from ${WBASE}.
- OFF-LANE HARD RULE: never run pytest, vitest, cargo, pnpm ci-local, pnpm typecheck, tsc, project-wide eslint, any sidecar build, the rig, the app, or any model (ollama). Those lanes belong to the rc1 gate running now. Allowed: git, reading, writing, 'python3 -m py_compile' and 'ruff format' + 'ruff check' on the files you touched, 'pnpm exec prettier --write' on the files you touched (PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$PATH; ruff at sidecar/.venv/bin/ruff or python3 -m ruff). Every code change is 'untested pending integration': write the tests as source, never run them; say so in your report.
- Never read any file matching docs/redesign/verification/R15_BRIEF*.md or anything under docs/redesign/verification/r15/local/. The word spelled L-a-y-a (any case) is banned from everything you write; never write "low-latency trading".
- Worktrees: only under ${SCRATCH}, created with an explicit base: git worktree add <path> -b <branch> ${BASE}. Never checkout, switch, stash, reset or merge in the main worktree. If you must commit in the main worktree, commit by explicit path with '-c core.hooksPath=/dev/null'; if .git/index.lock exists, sleep 5 and retry (other agents share the index). Never 'git add -A' or '.', never commit CLAUDE.md, never touch ${REG}, docs/redesign/DECISIONS_FOR_OPERATOR.md or docs/redesign/verification/vysted-r15-run-state.md.
- Remote calls carry GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20". Push ONLY your own branch; never main, never 004, never force. The 'vysted-head-guard' hook messages are harmless.
- No tool call longer than ~120 s (start longer work with nohup ... > log 2>&1 & and poll with separate sleep/tail calls). Write your result to disk as you go (a RESULT.md in your worktree, committed on your branch) so a pause costs nothing; on restart continue from what your branch already holds.
- Tests are state: never delete, skip or weaken a test to get green; if a test is wrong, fix it and log why. Never special-case code for a test. Never speculate about code you have not opened.
- The order-safety surface is READ-ONLY (sidecar/models/audit_log.py, sidecar/services/kill_switch.py, src-tauri/src/kill_switch.rs, the proposed-changes gate in sidecar/services/agent_runtime.py, types/proposed-change.ts AUTO_APPLIED_KINDS): a fix that needs it stops and reports could_not with the reason.
- Signed-off local-model class (operator, 26 Sep): an instance of "the local model states a figure for a subject with no ok tool call behind it" (the R15-LEAD-030/035/037/038 class) is filed against that known limitation, never fixed: report outcome class_limitation.
- A fix that is really a feature build (days of work, new panels, new subsystems) is not a low fix: report outcome deferred_feature with a size estimate; build nothing.
- Timestamps only from date '+%H:%M IST'. Commit trailers on every commit: "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" and "Claude-Session: https://claude.ai/code/session_01HJVZfFSmtgR7p7eW5tKNCg". No emojis. Return raw data, not a human message.`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }, NUM = { type: 'number' }, BOOL = { type: 'boolean' }, STRS = { type: 'array', items: STR }
const ENTRY = S({ id: STR, outcome: { type: 'string', enum: ['fixed_untested', 'could_not', 'not_a_defect_proposed', 'class_limitation', 'deferred_feature', 'tier4'] }, commit: STR, test: STR, files: STRS, note: STR })
const WRITER = S({ model: STR, branch: STR, head_sha: STR, pushed: BOOL, cherry_picked: STRS, entries: { type: 'array', items: ENTRY }, notes: STRS, summary: STR })
const VERD = S({ id: STR, verdict: { type: 'string', enum: ['concur_not_defect', 'still_a_defect', 'needs_app'] }, reason: STR, fix_shape: STR })
const REFUTE = S({ model: STR, file: STR, verdicts: { type: 'array', items: VERD }, summary: STR })
const COLLATE = S({ model: STR, file: STR, branches_total: NUM, heads_verified: NUM, mismatches: STRS, counts: { type: 'object' }, summary: STR })

const COULD_NOT = [
  { id: 'R15-CODE-RESEARCH-005', p: 'P1', set: 'W3', branch: 'worktree-agent-lows-P1-W3-actions-research', why: 'shared loop helpers to _loop.py need edits in services/research/citecheck.py that W3 did not own' },
  { id: 'R15-CODE-AGENT-031', p: 'P1', set: 'W6', branch: 'worktree-agent-lows-P1-W6-runs-stores', why: 'a snake_case-only wire renames RunDetail hostActions to host_actions and breaks sidecar/tests/test_run_manager* which W6 did not own' },
  { id: 'R15-CODE-DATA-019', p: 'P2', set: 'W4', branch: 'worktree-agent-lows-P2-W4-warm-screener', why: 'needs three files W4 did not own; deleting matched_criteria from types/screener.ts breaks tsc elsewhere' },
  { id: 'R15-LIFECYCLE-035', p: 'P2', set: 'W5', branch: 'worktree-agent-lows-P2-W5-data-resilience', why: 'the correct fix (refresh() re-derives past a sticky error) regresses test_search_tiers_router.py HTTP-level sticky assertions' },
  { id: 'R15-CODE-FRONTEND-027', p: 'P2', set: 'W8', branch: 'worktree-agent-lows-P2-W8-shell-page', why: 'refreshCustom non-2xx now errors with server detail (landed); the sidecarRequest switch was blocked by quant panel tests W8 did not own' },
  { id: 'R15-AGENT-077', p: 'P3', set: 'W2', branch: 'worktree-agent-lows-P3-W2-llm-chat', why: 'the base_url fix is pushed and its own test passes but two unowned tests went red (the fakes in test_res*)' },
  { id: 'R15-DATA-102', p: 'P3', set: 'W3', branch: 'worktree-agent-lows-P3-W3-provenance-data', why: 'store part committed (growth_basis column, per-tier field_meta, yfinance mrq_yoy); flipping the consumer side was blocked' },
]
const NAD = [
  { id: 'R15-LEAD-025', p: 'P2', set: 'W4', note: 'did not reproduce at the sha: with openbb _call_tool spied, a US boot makes 0 openbb calls and the IN crawler ...' },
  { id: 'R15-CODE-PLATFORM-045', p: 'P3', set: 'W1', note: 'not reproducible: an intervening refactor (R15-AGENT-014/012/013) routes plugin bridging exclusively through ...' },
  { id: 'R15-CODE-PLATFORM-046', p: 'P3', set: 'W1', note: 'same root cause as -045: post-refactor host.attach() error handling already covers this scenario' },
]
const SONNET_SETS = [
  { label: 'new-lows', branch: 'worktree-agent-lows-NEW-drafted', source: LOWS + '/NEW_LOWS_DRAFT.json (drafted entries; the register does not carry them yet, use the proposed ids)', ids: ['R15-DOCS-025', 'R15-CODE-PLATFORM-078', 'R15-CODE-PLATFORM-079', 'R15-CODE-PLATFORM-080', 'R15-CODE-FRONTEND-038'], skip: 'R15-DOCS-026 is Tier-4 (CLAUDE.md is a locked file): do not touch it; report outcome tier4 with a one-line recommendation.' },
  { label: 'deferred-A', branch: 'worktree-agent-lows-DEF-A', source: REG + ' (open lows the partition deferred as cross-set; read ' + LOWS + '/PARTITION.json "deferred" and PARTITION.md for their files and notes)', ids: ['R15-AGENT-065', 'R15-AGENT-085', 'R15-AGENT-086', 'R15-CODE-FRONTEND-031', 'R15-CODE-FRONTEND-033'], skip: '' },
  { label: 'deferred-B', branch: 'worktree-agent-lows-DEF-B', source: REG + ' (open lows the partition deferred as cross-set; read ' + LOWS + '/PARTITION.json "deferred" and PARTITION.md for their files and notes)', ids: ['R15-CROSS-PLATFORM-012', 'R15-UI-068', 'R15-UI-071', 'R15-UI-073', 'R15-UI-082'], skip: '' },
]

if (DRY) {
  const would = [...COULD_NOT.map(c => 'CN-' + c.id + ' (opus/high, worktree)'), 'refuter (opus/default)', ...SONNET_SETS.map(s => s.label + ' (sonnet/high, worktree)'), 'LEAD-036 (opus/default, worktree)', 'collator (sonnet/medium)']
  would.forEach(w => log('dry_run: would spawn ' + w))
  return { dry_run: true, base: BASE, would_spawn: would }
}

const cnPrompt = (c) => `ROLE: SECOND-ATTEMPT WRITER (Opus) for ONE open low, ${c.id}, partition ${c.p}, prior set ${c.set}. The first writer reported could_not: "${c.why}". You own every file the fix needs (the ownership partition does not bind this attempt), except the read-only safety surface.
${COMMON}
STEPS
1. Read the entry ${c.id} in ${REG} (python3 json filter), the prior set's note in ${LOWS}/${c.p}/WRITERS.json and ${LOWS}/${c.p}/writers/${c.set}.jsonl, and the prior branch: git fetch origin ${c.branch}; git log --oneline ${WBASE}..origin/${c.branch}; git show --stat for the commits that touch this entry.
2. mkdir -p ${SCRATCH}/lows-cn && git worktree add ${SCRATCH}/lows-cn/${c.id.toLowerCase()} -b worktree-agent-lows-CN-${c.id.toLowerCase()}-${B7} ${BASE}. Work only inside that worktree.
3. Where the prior branch already carries part of THIS entry's fix, cherry-pick exactly those commits first (git cherry-pick -x <sha>; record them). Your branch is merged into the partition candidate AFTER the prior writer branch, so both must merge cleanly: never re-implement what you cherry-picked.
4. Complete the fix at the root cause, including the files the prior writer could not own, and make every affected test correct as source: a test that pinned the old wrong behaviour is fixed (say why in the commit body), never deleted or skipped. Add or extend the entry's acceptance test as source. You do NOT run tests (off-lane rule); run only py_compile/ruff/prettier on touched files.
5. Commit by explicit path (one or two commits, conventional message naming ${c.id}), write RESULT.md at the worktree root (entry, outcome, commits, files, tests written, what is untested pending integration, risks), commit it, push your branch, verify with git ls-remote origin worktree-agent-lows-CN-${c.id.toLowerCase()}-${B7}. Do not remove the worktree.
OUTCOME RULES: fixed_untested when the full fix is on the branch; could_not only with the concrete blocker (name the file/test and why), never for size alone; class_limitation / deferred_feature / tier4 per the rules above.`

const sonnetPrompt = (s) => `ROLE: WRITER (Sonnet) for a set of open lows: ${JSON.stringify(s.ids)}. Source of the entries: ${s.source}. ${s.skip}
${COMMON}
STEPS
1. For each id read the entry (title, files, repro, evidence, root_cause, fix_shape) and open every file it names at BASE. Check ${LOWS}/PARTITION.md and the three ${LOWS}/P*/WRITERS.json for prior notes on the id (some were deferred because they cross writer sets: you own all their files in this attempt).
2. git worktree add ${SCRATCH}/lows-${s.label} -b ${s.branch}-${B7} ${BASE}; work only inside it.
3. Fix each entry at the root cause with the smallest correct diff; write its acceptance test as source (the entry's fix_shape names one when it exists); never run tests (off-lane rule): py_compile/ruff/prettier on touched files only. One commit per entry, message naming the id. A Rust change (src-tauri) is written with care and marked untested; never run cargo.
4. Write RESULT.md at the worktree root as you go (per entry: outcome, commit, test, files, note) and commit it; push your branch; verify with git ls-remote. Do not remove the worktree.
OUTCOME RULES: fixed_untested; could_not with the concrete blocker; not_a_defect_proposed with the evidence (the code at BASE already behaves correctly: cite file:line); class_limitation; deferred_feature with a size estimate when the fix is a feature build; tier4 when the fix needs a locked file (CLAUDE.md, types/plugin.ts, CI workflows, tauri.conf.json, LICENSE).`

const lead036Prompt = `ROLE: WRITER (Opus) for ONE open low, R15-LEAD-036, which no partition set carried. ${COMMON}
STEPS: read the entry in ${REG} and every batch VERDICTS.md under docs/redesign/verification/r15/stage-c/batch-*/ that names LEAD-036 (grep -l), plus docs/redesign/DECISIONS_FOR_OPERATOR.md sections 4.9 to 4.12 (read-only). FIRST decide whether the entry is an instance of the signed-off local-model class; if it is, write nothing to code, return outcome class_limitation with the sentence that files it against the limitation, and put the same in ${SCRATCH}/lows-lead036-RESULT.md. If it is not, git worktree add ${SCRATCH}/lows-lead036 -b worktree-agent-lows-LEAD-036-${B7} ${BASE}, fix it at the root cause with its test as source (never run tests), commit by path, RESULT.md, push, ls-remote verify.`

const refutePrompt = `ROLE: FRESH REFUTER (Opus, read-only, no worktree, no code edits) over three lows their writers proposed as not_a_defect: ${JSON.stringify(NAD)}.
${COMMON}
For each id: read the entry in ${REG}, the writer's note in ${LOWS}/<P>/WRITERS.json and writers/<set>.jsonl, and the code at BASE (git show ${BASE}:<path> or the main worktree, which is at or after BASE). Try to REFUTE the writer: is the defect reproducible from the repo alone at BASE (a grep, a file:line, a static trace)? Verdict per id: concur_not_defect (the code at BASE cannot exhibit the reported behaviour; cite file:line), still_a_defect (cite the path that still exhibits it and give the fix shape), needs_app (only decidable against the running app; say what run would decide it). Write ${OUT}/REFUTE.md (verdict, evidence, fix shape per id) in the MAIN worktree, mkdir -p first, commit it by path with hooks off (retry on index.lock), do not push.`

const collatePrompt = (results) => `ROLE: COLLATOR (Sonnet). Inputs (the structured returns of every writer and the refuter): ${JSON.stringify(results)}.
${COMMON}
Verify every branch named in the inputs on origin (git fetch --prune then git ls-remote origin <branch>; a head that differs from head_sha or is missing is a mismatch). Write ${OUT}/REMAINING.json (one row per entry: id, partition-or-set, outcome, branch, head, commit, test, files, note, untested_pending_integration true) and ${OUT}/REMAINING.md (a table per outcome, then the branch list grouped for the partition candidates: P1 gets the CN branches of P1 entries plus deferred-A, P2 its CN branches plus deferred-B, P3 its CN branches plus new-lows and LEAD-036 if a branch exists; say this grouping is the lead's default and can be re-cut). Commit both by path in the main worktree with hooks off (retry on index.lock). Do not push. Return counts.`

phase('Write')
const writes = parallel([
  ...COULD_NOT.map(c => () => run(cnPrompt(c), { label: 'CN-' + c.id, phase: 'Write', model: 'opus', effort: 'high', schema: WRITER })),
  ...SONNET_SETS.map(s => () => run(sonnetPrompt(s), { label: s.label, phase: 'Write', model: 'sonnet', effort: 'high', schema: WRITER })),
  () => run(lead036Prompt, { label: 'LEAD-036', phase: 'Write', model: 'opus', effort: 'medium', schema: WRITER }),
])
phase('Refute')
const refute = run(refutePrompt, { label: 'refuter', phase: 'Refute', model: 'opus', effort: 'medium', schema: REFUTE })
const [wr, rf] = await Promise.all([writes, refute])
const results = { writers: wr.filter(Boolean), refuter: rf }
log('writers returned ' + results.writers.length + '/' + (COULD_NOT.length + SONNET_SETS.length + 1))
phase('Collate')
const col = await run(collatePrompt(results), { label: 'collator', phase: 'Collate', model: 'sonnet', effort: 'medium', schema: COLLATE })
return { base: BASE, results, collate: col }
