export const meta = {
  name: 'r15-lows-preint',
  description: 'Burst (pacing change 5): assemble one candidate integration branch per lows partition (P1/P2/P3) on the rc1 candidate base by merging every writer branch in merge order, with an Opus diff review, a conflict and risk map and the claimed-tests list; off-lane (no tests, no builds); pushed, never merged',
  whenToUse: 'R15 burst window while the rc1 gate owns the machine lanes; re-run cheaply with a new base after gate fix rounds or with extra branches. args {base (sha), partitions, extra {P1:[branch,...]}, scratch, dry_run}',
  phases: [
    { title: 'Assemble', detail: 'Opus/high: worktree from base, merge writer branches in order, resolve conflicts, PREINT.md' },
    { title: 'Review', detail: 'fresh Opus: read-only diff review, PREINT_REVIEW.md' },
    { title: 'Fix', detail: 'Opus: one bounded pass on blocking review items' },
  ],
}
const A = args || {}
const BASE = String(A.base || '')
if (!/^[0-9a-f]{7,40}$/.test(BASE)) throw new Error('args.base (the rc1 candidate sha) is required')
const B7 = BASE.slice(0, 7)
const PARTS = Array.isArray(A.partitions) && A.partitions.length ? A.partitions : ['P1', 'P2', 'P3']
const EXTRA = A.extra && typeof A.extra === 'object' ? A.extra : {}
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const DRY = A.dry_run === true || A.dry_run === 'true'
const LOWS = 'docs/redesign/verification/r15/stage-c/lows'
const REG = 'docs/redesign/verification/vysted-r15-register.json'
const WBASE = 'ebc5ed4194f9362422c3178c27d4cdf946428968'
const SAFETY = ['sidecar/models/audit_log.py', 'sidecar/services/kill_switch.py', 'src-tauri/src/kill_switch.rs', 'types/proposed-change.ts', 'sidecar/services/agent_runtime.py (the proposed-changes gate)']

const once = (p, o) => {
  if (!['opus', 'sonnet'].includes(o.model) || !o.effort) throw new Error('agent ' + o.label + ': model opus|sonnet and effort must be explicit (routing change 5)')
  return agent(p, o)
}
const run = (p, o) => once(p, o).then(r => r ? r : (log('agent ' + o.label + ' returned nothing; one same-tier retry'), once(p, { ...o, label: o.label + '-retry' })))

const COMMON = `
RULES (R15 burst window, operator pacing change 5; every rule binds):
- Repo /Users/lokavyasingh/Documents/dev/vysted-terminal, branch 004-r4-experience-rebuild. BASE for this run: ${BASE}. The lows writer branches were cut from ${WBASE}.
- OFF-LANE HARD RULE: never run pytest, vitest, cargo, pnpm ci-local, pnpm typecheck, tsc, project-wide eslint, any sidecar build, the rig, the app, or any model. Those lanes belong to the rc1 gate running now. Allowed: git, reading, writing, 'python3 -m py_compile' and 'ruff format' + 'ruff check' on changed .py files (sidecar/.venv/bin/ruff or python3 -m ruff), 'pnpm exec prettier --check/--write' on changed files (PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$PATH). Everything is 'untested pending integration'.
- Never read any file matching docs/redesign/verification/R15_BRIEF*.md or anything under docs/redesign/verification/r15/local/. The word spelled L-a-y-a (any case) is banned from everything you write; never write "low-latency trading".
- Worktrees: only under ${SCRATCH}, created with an explicit base (git worktree add <path> -b <branch> ${BASE}). Never checkout, switch, stash, reset or merge in the main worktree. Commits in the main worktree are by explicit path with '-c core.hooksPath=/dev/null'; if .git/index.lock exists, sleep 5 and retry (other agents share the index). Never 'git add -A' or '.', never commit CLAUDE.md, never touch ${REG}, docs/redesign/DECISIONS_FOR_OPERATOR.md or docs/redesign/verification/vysted-r15-run-state.md.
- Remote calls carry GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20". Push ONLY the candidate branch you own; never main, never 004, never a writer branch, never force.
- No tool call longer than ~120 s (a long merge series is fine as separate calls). Write PREINT.md as you go so a pause costs nothing; on restart continue from the branch state.
- Tests are state: never delete, skip or weaken a test; a conflict resolution never drops a writer's test or hunk silently (record every choice). Never speculate about code you have not opened.
- The order-safety surface is READ-ONLY: ${JSON.stringify(SAFETY)}. A writer hunk that touches it is NOT merged: leave it out, record it as a blocked hunk with the entry id.
- Timestamps only from date '+%H:%M IST'. Commit trailers: "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" and "Claude-Session: https://claude.ai/code/session_01HJVZfFSmtgR7p7eW5tKNCg". No emojis. Return raw data.`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }, NUM = { type: 'number' }, BOOL = { type: 'boolean' }, STRS = { type: 'array', items: STR }
const ASM = S({ model: STR, partition: STR, branch: STR, head_sha: STR, pushed: BOOL, merged: STRS, skipped: STRS, conflicts: NUM, blocked_hunks: STRS, claimed_tests: NUM, file: STR, summary: STR })
const REV = S({ model: STR, partition: STR, verdict: { type: 'string', enum: ['ready', 'needs_fix'] }, blocking: { type: 'array', items: S({ file: STR, issue: STR, fix: STR }) }, advisories: STRS, safety_surface_touched: BOOL, file: STR, summary: STR })
const FIX = S({ model: STR, partition: STR, head_sha: STR, pushed: BOOL, applied: STRS, left: STRS, summary: STR })

const branchName = (p) => 'worktree-agent-lows-' + p + '-int-' + B7

if (DRY) {
  PARTS.forEach(p => log('dry_run: would spawn assemble-' + p + ' (opus/high) -> review-' + p + ' (opus/medium) -> fix-' + p + ' (opus/medium, only on needs_fix); branch ' + branchName(p) + '; extra ' + JSON.stringify(EXTRA[p] || [])))
  return { dry_run: true, base: BASE, partitions: PARTS }
}

const asmPrompt = (p) => `ROLE: PRE-INTEGRATION ASSEMBLER (Opus) for lows partition ${p}. Goal: ONE candidate branch ${branchName(p)} = BASE plus every ${p} writer branch merged in merge order, conflicts resolved, so that after the r15-rc1 tag the integration is: rebase onto the tag, run the chain, one fresh verifier, merge, nothing else. The branch is pushed and NEVER merged by you.
${COMMON}
INPUTS: ${LOWS}/PARTITION.md (the ${p} merge order and per-set entries), ${LOWS}/${p}/WRITERS.json (each set's branch, merge_order_hint, head_sha_origin, per-entry outcome/commit/test), ${LOWS}/${p}/writers/*.jsonl (per-entry notes). Extra branches to merge LAST, in the given order, if any: ${JSON.stringify(EXTRA[p] || [])} (these come from second-attempt writers; a CN branch for an entry merges after the set branch that carried the entry's first partial attempt).
STEPS
1. git fetch --prune origin. Confirm every set branch head on origin equals WRITERS.json head_sha_origin (record a mismatch, use origin's head). mkdir -p ${SCRATCH}/lows-preint; git worktree add ${SCRATCH}/lows-preint/${p} -b ${branchName(p)} ${BASE} (if the worktree/branch already exists from an interrupted run, continue from it).
2. In the worktree, for each branch in merge order: git merge --no-ff --no-edit origin/<branch>. On conflict: open both sides, the writers' notes and the entries' intent; resolve so that BOTH writers' behaviours and tests survive; git add the resolved paths; git commit --no-edit. Record in PREINT.md: file, the two intents, the resolution, the entry ids. A hunk that touches the safety surface is left out (record as blocked). After each merge append the merge sha to PREINT.md (write-as-you-go).
3. Sanity, touched files only: python3 -m py_compile on every changed .py; ruff format --check + ruff check on changed .py under sidecar/ (format-only fixes go in one commit 'style: ruff/prettier on the ${p} candidate'); pnpm exec prettier --check on changed ts/tsx/js/mjs/json/md/css. Do NOT run tsc, eslint, vitest, pytest, cargo or any build.
4. Push: git push origin ${branchName(p)}; verify with git ls-remote.
5. Write ${LOWS}/${p}/PREINT.md and ${LOWS}/${p}/PREINT.json in the MAIN worktree (commit both by path, hooks off, retry on index.lock; do not push): base, branch, head, the merge order with shas and head mismatches, the conflict map, the risk map (files touched by more than one writer; files touched by more than one partition if you notice them; safety-surface hunks left out; Rust or config changes; anything untested that looks risky), the CLAIMED TESTS list (every WRITERS.json/jsonl 'test' field of this partition, grouped by test file, plus the extra branches' RESULT.md tests) as the exact focused-test commands for the integrator, and the integration recipe (git commands) for after the tag. Do not remove the worktree.`

const revPrompt = (p, asm) => `ROLE: FRESH DIFF REVIEWER (Opus, read-only: no worktree of your own, no code edits, no pushes) for the lows partition ${p} candidate branch. Assembler's return: ${JSON.stringify(asm)}.
${COMMON}
Read ${LOWS}/${p}/PREINT.md, then git fetch origin ${branchName(p)} and review git diff ${BASE}...origin/${branchName(p)} (use --stat first, then per file; the diff can be large: read it in pieces, never one call over 120 s). Check: (a) the safety surface is untouched (git diff --stat ${BASE}...origin/${branchName(p)} -- <each safety path> must be empty); (b) every claimed test in PREINT.md exists on the branch as source and asserts the entry's behaviour; (c) each conflict resolution kept both writers' hunks (spot-check every conflicted file against the two writer branches); (d) obvious defects, broken imports, duplicated definitions, changed public contracts (types/*.ts mirrors of sidecar/models, MCP surface, register-counted tests); (e) risk: anything that plausibly fails the chain (ci-local: lint, format, typecheck, clippy, ruff, vitest, cargo test, pytest) so the integrator knows where to look first. Write ${LOWS}/${p}/PREINT_REVIEW.md in the main worktree (commit by path, hooks off, retry on index.lock; do not push) with verdict ready|needs_fix, blocking items (file, issue, fix) and advisories.`

const fixPrompt = (p, rev) => `ROLE: FIX PASS (Opus, one bounded pass) on the lows partition ${p} candidate branch ${branchName(p)}. Reviewer's blocking items: ${JSON.stringify(rev.blocking)}. Advisories (fix only when trivial and safe): ${JSON.stringify(rev.advisories)}.
${COMMON}
Work in the assembler's worktree ${SCRATCH}/lows-preint/${p} (it exists; if not, git worktree add it from origin/${branchName(p)} with -b ${branchName(p)}-fix and say so). Apply each blocking fix at the root cause, tests as source only (never run them), py_compile/ruff/prettier on touched files, one commit per item naming the entry id, push the candidate branch (never force), ls-remote verify. Append a 'Fix pass' section to ${LOWS}/${p}/PREINT.md in the main worktree (commit by path, hooks off, retry on index.lock; do not push) listing applied and left items with reasons.`

const results = await pipeline(
  PARTS,
  p => run(asmPrompt(p), { label: 'assemble-' + p, phase: 'Assemble', model: 'opus', effort: 'high', schema: ASM }),
  (asm, p) => run(revPrompt(p, asm), { label: 'review-' + p, phase: 'Review', model: 'opus', effort: 'medium', schema: REV }).then(rev => ({ asm, rev })),
  async (r, p) => {
    if (!r || !r.rev || r.rev.verdict === 'ready' || !r.rev.blocking || !r.rev.blocking.length) return { ...r, fix: null }
    const fix = await run(fixPrompt(p, r.rev), { label: 'fix-' + p, phase: 'Fix', model: 'opus', effort: 'medium', schema: FIX })
    return { ...r, fix }
  },
)
return { base: BASE, partitions: PARTS, results: results.map((r, i) => ({ partition: PARTS[i], ...(r || {}) })) }
