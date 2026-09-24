export const meta = {
  name: 'r15-stage-d-docs',
  description: 'R15 Stage D docs and scans wave, run beside the fix batches: FACTS at a 004 sha, five doc drafts (README, release runbook, operator briefing, release notes + CHANGELOG 0.9.0, CURRENT_STATE + BLOCKERS refresh), each with one Fable critic round and a Fable revise, in parallel with three read-only scans (secrets, dependency licences, licence consistency); a collator writes the index + operator questions and commits only the output dir. Repo reads, git, curl and cheap metadata commands only',
  whenToUse: 'Beside the R15 fix batches (mode draft), and again before rc2 (mode refresh) on 004-r4-experience-rebuild; args {sha, out, mode, cap, skip}',
  phases: [
    { title: 'Facts', detail: 'FACTS.json/.md at the sha: versions, sidecars, scripts, CI, plugins, agents, panels, register, decisions, git log' },
    { title: 'Drafts', detail: 'README, RELEASE_RUNBOOK, OPERATOR_BRIEFING, RELEASE_NOTES, CURRENT_STATE + BLOCKERS (Fable high each)' },
    { title: 'Scans', detail: 'secrets (tree + history), dependency licences, licence consistency (Fable high each, read-only)' },
    { title: 'Critic', detail: 'one Fable critic per draft (one same-tier retry), then one Fable revise per REVISE verdict', model: 'fable' },
    { title: 'Collate', detail: 'STAGE_D_INDEX.md + OPEN_QUESTIONS.md, output-dir secret guard, commit only the output dir on 004' },
  ],
}

const A = args || {}
if (!A.sha || !/^[0-9a-f]{7,40}$/i.test(String(A.sha))) throw new Error('stage-d-docs: REFUSED - args.sha (the 004-r4-experience-rebuild commit to draft against, 7-40 hex chars) is required')
const REPO = '/Users/lokavyasingh/Documents/dev/vysted-terminal'
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const SHA_IN = String(A.sha).toLowerCase()
const SH7 = SHA_IN.slice(0, 7)
const EVR = A.out == null ? 'docs/redesign/verification/r15/stage-d' : String(A.out).replace(/\/+$/, '')
// The collator runs 'git add -A' on this dir, so it must be a dir this wave owns: r15/stage-d or a stage-d-* sibling.
if (!/^docs\/redesign\/verification\/r15\/stage-d[A-Za-z0-9._-]*$/.test(EVR)) throw new Error('stage-d-docs: REFUSED - args.out must be docs/redesign/verification/r15/stage-d or a stage-d-* sibling (the collator git-adds the whole dir), got ' + JSON.stringify(A.out))
const MODE = A.mode == null ? 'draft' : String(A.mode)
if (MODE !== 'draft' && MODE !== 'refresh') throw new Error('stage-d-docs: REFUSED - args.mode must be draft or refresh, got ' + JSON.stringify(A.mode))
const posInt = (v, d) => (Number.isInteger(+v) && +v > 0 ? +v : d)
const CAP_ASKED = posInt(A.cap, 6)
const CAP = Math.min(16, CAP_ASKED)
if (CAP_ASKED > 16) log('cap ' + CAP_ASKED + ' is over the 16-agent ceiling - clamped to 16')
const LANE_KEYS = ['readme', 'runbook', 'briefing', 'notes', 'state', 'secrets', 'deps', 'licence']
const SKIP = A.skip == null ? [] : (Array.isArray(A.skip) ? A.skip : String(A.skip).split(',')).map(s => String(s).trim()).filter(Boolean)
const badSkip = SKIP.filter(s => !LANE_KEYS.includes(s))
if (badSkip.length) throw new Error('stage-d-docs: REFUSED - unknown skip names ' + JSON.stringify(badSkip) + '; allowed: ' + LANE_KEYS.join(', '))
const EV = REPO + '/' + EVR
const WORK = SCRATCH + '/stage-d-' + SH7

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
// Routing change 4: every agent runs on Fable; a wave that dies or starves gets ONE same-tier retry, never a third try.
const run = (prompt, opts) => once(prompt, opts).then(r => (r || opts.model !== 'fable') ? r : (log('agent ' + opts.label + ' on fable returned nothing (wave died or starved) - routing 4: same-tier retry, never a third try'), once(prompt, { ...opts, model: 'fable', label: opts.label + '-retry' })))

const COMMON = `Repo: ${REPO}, integration branch 004-r4-experience-rebuild. This is the R15 STAGE D DOCS AND SCANS wave: doc drafts and read-only scans at one sha, running BESIDE the fix batches. You fix nothing and edit no tracked file outside your output dir. The operator is away; never ask, decide and record. Before any pnpm/node/cargo command: export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH. Never print, log or copy a secret (no keystore, keychain, env dump or auth header, and never a matched secret value: a scan reports locations and redacted shapes only); never read docs/redesign/verification/R15_BRIEF*.md or docs/redesign/verification/r15/local/ (grep over docs/ passes --exclude='R15_BRIEF*' --exclude-dir=local; git grep passes ':!docs/redesign/verification/R15_BRIEF*' ':!docs/redesign/verification/r15/local'). No GUI. Trading is out of the product permanently (D81, a122dbf6 feat(d81)): no broker, order, paper account or live/paper switch anywhere; the user's tracked portfolio stays. Never describe any of it as a feature or propose it. Licence: PolyForm Strict 1.0.0 core + a commercial licence; the plugin contract (types/plugin.ts) and the example plugin are Apache-2.0. Target version 0.9.0. Three PyInstaller sidecars. The macOS production build is proven from a clean profile later by the lead, not by this wave. Never tag, merge to main, push anything, open a PR or force-push; never commit unless your role says so. Never edit a tracked file outside ${EV}: README.md, docs/*.md, CHANGELOG.md, BLOCKERS.md and every other tracked file are only READ; the lead promotes drafts at rc2. Your only writes are your own output files under ${EV} and scratch files under ${WORK} (mkdir -p it). Read the repo AT THE SHA (git -C ${REPO} show <sha>:<path>, git grep <pattern> <sha> --, git ls-tree, git cat-file -e <sha>:<path>), not the working tree: other workflows commit on 004 in ${REPO} while you run, and it carries uncommitted edits. Never touch other workflows' worktrees (.claude/worktrees, scratch dirs), branches, ports or files, and never git checkout/reset/stash/add/commit/worktree in ${REPO} (the collator's one commit excepted). Never speculate about code you have not opened: path:line at the sha for every code claim, command + output excerpt for every probe, URL + quote for every world claim. HARNESS STALL RULE (a 3-minute no-progress watchdog kills the agent and restarts it from scratch): NO single tool call may run longer than ~120 s. Anything longer MUST be started detached ('nohup <cmd> > <log> 2>&1 &') and polled with SEPARATE short calls ('sleep 30; tail -n 5 <log>'), never an 'until … sleep' loop inside one call. Keep emitting a tool call at least every 2 minutes. WRITE YOUR OUTPUT FILE(S) AS YOU GO. If you find output files from a previous attempt of your own role at the same sha (a restart), read them and CONTINUE from them. Shell: cat is aliased to bat and ls to eza (both can hang): use /bin/cat, /bin/ls or your Read tool. Your final text IS the return value: return only the structured object.`

const LANES = `LANES YOU MAY USE: (1) repo reads at the sha: git -C ${REPO} show / log / grep / ls-tree / blame / diff / cat-file / tag / merge-base / branch --contains, read-only; plain reads in ${REPO} only of untracked dependency trees (node_modules, the three sidecar venvs) and of the two scripts/r15 probes named below. (2) Cheap local metadata commands, each ≤120 s: node -e, pnpm licenses list, cargo metadata --offline --locked, <venv>/bin/python -m pip list, importlib.metadata, 'which', the repo's read-only probes scripts/r15/history_secrets_scan.py and scripts/r15/licence_scan.py (always PYTHONDONTWRITEBYTECODE=1). (3) The outside world via curl (browser UA, ≤1 request per 3 s per host).
LANES YOU MUST NEVER USE (other workflows own them): the operator's live app, vite :5173 or any GUI; any sidecar (never boot one, never send a request to any 127.0.0.1 port); Ollama or any local model; any agent run (vy.py, /agents/*); the heavy-job lane (pnpm install, pnpm ci-local, pnpm build, a full pytest or vitest run, cargo build/test/clippy, PyInstaller, ensure-*-sidecar scripts, pnpm sidecars:build, pnpm tauri build/dev, the smoke test); installing anything, global or local (pip/pnpm/cargo/brew install); starting or stopping any process other than your own detached probe; any write outside ${EV} and ${WORK}.`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }
const NUM = { type: 'number' }
const BOOL = { type: 'boolean' }
const STRS = { type: 'array', items: STR }
const OBJ = { type: 'object' }

const FACTS = S({ model: STR, status: { type: 'string', enum: ['ready', 'blocked'] }, sha: STR, previous_sha: STR, version: STR, version_consistent: BOOL, facts_md: STR, facts_json: STR, blockers: STRS, summary: STR })
const DRAFT = S({ model: STR, name: STR, files: STRS, sections: STRS, open_questions: STRS, verify_markers: NUM, summary: STR })
const CRITIC = S({ model: STR, name: STR, verdict: { type: 'string', enum: ['PASS', 'REVISE'] }, findings: NUM, by_kind: S({ wrong: NUM, missing: NUM, stale: NUM, unverifiable: NUM }), critic_file: STR, summary: STR })
const REVISE = S({ model: STR, name: STR, files: STRS, applied: NUM, rejected: NUM, open_questions: STRS, summary: STR })
const SCAN = S({ model: STR, name: STR, files: STRS, counts: OBJ, flagged: { type: 'array', items: S({ where: STR, what: STR, note: STR }) }, not_scanned: STRS, open_questions: STRS, summary: STR })
const COLLATE = S({ model: STR, sha: STR, rows: { type: 'array', items: S({ file: STR, status: STR, findings: NUM }) }, open_questions: NUM, redacted: STRS, files: STRS, commit: STR, summary: STR })

// ---------------------------------------------------------------- 1. Facts
phase('Facts')
const factsRes = await run(`${COMMON}

${LANES}

ROLE: FACTS (Fable, mechanical; label stage-d-facts). You assemble the facts every later agent reads instead of re-deriving; you judge nothing.
(1) Resolve: git -C ${REPO} rev-parse ${SHA_IN}^{commit} gives the full sha. It must be 004-r4-experience-rebuild or an ancestor (git merge-base --is-ancestor); otherwise status 'blocked' with the reason.
(2) Output dirs: mkdir -p ${EV}/critic ${WORK}. ${MODE === 'refresh'
    ? `REFRESH MODE: never delete anything under ${EV}. previous_sha = the sha in the existing ${EV}/FACTS.json ('' if there is none). Add to the facts: git -C ${REPO} log --oneline <previous_sha>..<sha> and git diff --stat <previous_sha> <sha> summarised per top-level dir.`
    : `DRAFT MODE: if ${EV}/FACTS.json exists at a DIFFERENT sha, an older run owns the dir: delete everything under ${EV} (git keeps its history) and start fresh. At the SAME sha (a restart) read what is there and complete it. previous_sha = ''.`}
(3) Collect, AT THE SHA, each fact with its source (path:line or the command):
- versions: the value and path:line of package.json "version", src-tauri/Cargo.toml [package] version, src-tauri/tauri.conf.json "version", sidecar/app.py FastAPI(version=…), HOST_VERSION in src/lib/plugin-bootstrap.ts, and the vysted-terminal entry in src-tauri/Cargo.lock; version_consistent = all equal. Then every other occurrence of that version string (git grep -nF '<version>' <sha> -- . ':!CHANGELOG.md' ':!docs/archive' ':!docs/redesign/verification' ':!docs/screenshots' ':!pnpm-lock.yaml'), each classed load_bearing (code, config, a test assertion) or prose; and whether '0.9.0' already appears anywhere.
- sidecars: the three bundle.externalBin names in src-tauri/tauri.conf.json; for each, the ensure script that builds it (scripts/ensure-*.mjs), the PyInstaller --name and entry script, its venv dir and requirements file, and the src-tauri/src file that spawns it.
- scripts: every package.json script name with its command verbatim.
- ci: each .github/workflows/*.yml: name, the 'on:' triggers verbatim, job names, OS matrix.
- plugins: each dir under plugins/: id, whether it is in BUNDLED_PLUGINS and in PLUGIN_COMPANIONS (src/lib/plugin-bootstrap.ts), its licence header or field.
- agents: the first-party agent JSON count and ids (sidecar/agents/*.json minus _schema.json) and the roster count the tests assert (git grep in sidecar/tests).
- panels: each module under src/modules/ with the panel ids and titles it registers.
- register: docs/redesign/verification/vysted-r15-register.json at the sha: counts by severity x status; the open critical/high/medium ids with subsystem; needs_gui ids; blocked_tier4 ids.
- decisions: docs/redesign/DECISIONS_FOR_OPERATOR.md at the sha: every numbered item: number, title, open or closed (CLOSED / SUPERSEDED = closed), tier4 yes/no, the one-line smallest unblock or undo.
- git: base_tag = the newest tag matching r13-* or r15-* that is an ancestor of the sha (git tag --merged <sha> --sort=-creatordate); commits since it (total and --first-parent); the first-parent merge subjects since it; the stage-c dirs under docs/redesign/verification/r15/stage-c/ at the sha with PLAN.md / VERDICTS.md presence and each VERDICTS.md tally line; CHANGELOG.md section headings newer than the base tag; docs/redesign/DECISIONS.md D-numbers added since the base tag (git log -p on that file, headings only).
- licence: LICENSE first heading, LICENSE-APACHE and LICENSING.md present, package.json license, src-tauri/Cargo.toml license / license-file.
- tools: which gitleaks trufflehog cargo-license pip-licenses (present or absent), pnpm --version, cargo --version; the three venvs present or absent.
Write ${EV}/FACTS.json as {sha, sha7, mode, previous_sha, versions, version_occurrences, sidecars, scripts, ci, plugins, agents, panels, register, decisions, git, licence, tools} and ${EV}/FACTS.md (line 1 '<!-- FACTS at <sha> by the Stage D docs wave -->', then one section per key, each fact with its source), section by section as you go.
Return model, status, sha (full), previous_sha, version (package.json), version_consistent, facts_md, facts_json (repo-relative paths), blockers, summary ≤80 words.`, { label: 'stage-d-facts', phase: 'Facts', model: 'fable', effort: 'medium', schema: FACTS })

if (!factsRes || factsRes.status !== 'ready') {
  const why = factsRes ? (factsRes.blockers.length ? factsRes.blockers : ['facts status ' + factsRes.status]) : ['facts agent died']
  log('facts blocked - the wave does not run: ' + JSON.stringify(why))
  return { status: 'blocked', sha: factsRes && factsRes.sha ? factsRes.sha : SHA_IN, mode: MODE, rows: [], skipped: SKIP, open_questions: 0, commit: null, blockers: why }
}
const SHA = factsRes.sha
log('facts @ ' + SHA.slice(0, 7) + ' (' + MODE + '): version ' + factsRes.version + (factsRes.version_consistent ? ', consistent' : ', INCONSISTENT across sources') + (factsRes.previous_sha ? '; previous run at ' + factsRes.previous_sha.slice(0, 7) : ''))

const HEADER = `<!-- DRAFT at ${SHA} by the Stage D docs wave; refresh before rc2 -->`
const FOOT = '<!-- critic-footer -->'
const diffCmd = (src, base) => `git -C ${REPO} show ${SHA}:${src} > ${WORK}/${base}.cur && tail -n +2 ${EV}/${base}.draft.md | sed '/^${FOOT}$/,$d' > ${WORK}/${base}.new; diff -u --label a/${src} --label b/${src} ${WORK}/${base}.cur ${WORK}/${base}.new > ${EV}/${base}.draft.diff (diff exits 1 when the files differ: that is success)`
const STATE_DIFFS = `${diffCmd('docs/CURRENT_STATE.md', 'CURRENT_STATE')}; and ${diffCmd('BLOCKERS.md', 'BLOCKERS')}`
const MODE_RULE = MODE === 'refresh'
  ? `REFRESH MODE: read your existing draft file(s) first. old_sha = the sha in line 1. A missing file or header: write it fresh (as a first draft) and say so in summary. Otherwise read git -C ${REPO} log --oneline <old_sha>..${SHA} and git diff --stat <old_sha> ${SHA}, then the diffs of the files your draft draws on, and update only what moved: numbers, commands, statuses, sections whose sources changed; fill each '<!-- fill at rc2: … -->' marker the new facts settle. Delete everything from the line '${FOOT}' to the end of the file (the critic runs again). Set line 1 to the header below. Append one line '<!-- refresh <old_sha7> to ${SHA.slice(0, 7)}: <what changed> -->' at the end.`
  : `DRAFT MODE: if your file already exists with this exact line 1, a previous attempt of yours died: continue it. If it carries another sha or no header, overwrite it from scratch.`

const DRAFT_RULES = `RULES FOR EVERY DRAFT: line 1 of each .draft.md is exactly '${HEADER}'. Write section by section as you go. Every command is copied verbatim from package.json scripts, scripts/, .github/workflows/ or a doc at the sha that runs it, never invented, and never run by you. Every behaviour claim rests on code or evidence you opened at the sha; a claim you could not verify stays out, or stays in wrapped as '<!-- VERIFY: <what, and how to check> -->' and goes to open_questions. Plain, direct prose; no marketing adjectives, no emojis. Trading appears only as removed or as what the product is not. Never write a key, token or keystore content, even an example-shaped one.`

const DRAFTS = [
  {
    key: 'readme', name: 'README', files: ['README.draft.md'], target: 'README.md', reader: 'a stranger who has never seen the project',
    brief: `Write README.draft.md for a stranger. (1) What it is, in two sentences. (2) What it is not: no trading (no brokerage connection; it cannot place, stage or simulate an order), not investment advice. (3) Install and run on macOS: a download path only as far as FACTS decisions say an installable release exists (the release-pipeline and signing items); if none is published, say the app is built from source and hold the download section as '<!-- fill at rc2: release asset URL and the Gatekeeper steps once the lead publishes -->'. Then build from source: prerequisites and the exact commands from package.json scripts and the current README at the sha. (4) BYOK: the providers, where keys are stored (confirm in code at the sha: the src-tauri keychain commands, the frontend key handling, any dev keystore file and when it is used), what leaves the machine and what does not, and keyless mode. (5) The plugin contract: types/plugin.ts and the example plugin are Apache-2.0 (confirm the SPDX headers and LICENSE-APACHE), pointer to docs/PLUGIN_DEVELOPMENT.md. (6) The licence split: core PolyForm Strict 1.0.0 (noncommercial) + commercial (COMMERCIAL_LICENSE.md, LICENSING.md); the AGPL-3.0-for-older-commits note only as LICENSING.md states it. (7) Support and roadmap pointers that exist at the sha (issues URL, CONTRIBUTING.md's stance, docs/README.md, specs/). Keep the current README's accurate parts (layout table; images only if git cat-file -e <sha>:<path> succeeds) and drop or correct stale ones from FACTS (redesign notices, test counts, 'version strings sit at 0.8.0'). Say 0.9.0 where the version appears. At most 250 lines.`,
    checks: 'Would a stranger on a clean Mac, following it top to bottom, reach a running app or an honest statement of why not? Does every prerequisite version match the repo (package.json engines, rust-toolchain, sidecar Python)?',
  },
  {
    key: 'runbook', name: 'RELEASE_RUNBOOK', files: ['RELEASE_RUNBOOK.draft.md'], target: 'docs/RELEASE_RUNBOOK.md (a new file)', reader: 'the lead or operator cutting the 0.9.0 release, step by step',
    brief: `Write RELEASE_RUNBOOK.draft.md: every button the release needs, in order, each step as: what; the exact command (verbatim from package.json scripts, scripts/, CLAUDE.md's verification gates at the sha); who (lead / NEEDS-OPERATOR / NEEDS-MANUAL-CHECK); and the expected output excerpt or the file it produces, quoted from real evidence at the sha with its path (the batch VERDICTS 'Chain observed' tables, r15 stage-c or rc1 logs, a script's own messages read from its source), never invented; where no evidence exists yet, '<!-- fill at rc2: expected output from the lead's run -->'. A checklist summary at the top, then: (1) version bump to 0.9.0: every load_bearing path:line from FACTS version_occurrences, then 'cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml', then the grep that proves no stale version string is left; (2) pnpm install --frozen-lockfile; (3) pnpm ci-local; (4) the sidecar builds (pnpm sidecars:build / node scripts/ensure-all-sidecars.mjs): the three binaries and where each lands; (5) node scripts/smoke-test-sidecars.mjs; (6) pnpm tauri build and the macOS bundle paths it produces (from tauri.conf.json bundle.targets); (7) the clean-profile launch check on macOS (fresh app-data dir: first-run terms, keyless mode, sidecar warm-up), performed by the lead, not by this wave; (8) signing and notarization: NEEDS-OPERATOR, quoting the exact Tier-4 items and smallest unblocks from DECISIONS_FOR_OPERATOR (R15-RELEASE-001 signing, 002 release pipeline, 003 updater, 004 CI on 004) and what stays unsigned until then; (9) tag and GitHub release: operator-only, commands shown and marked 'operator runs this'; (10) Windows: a NEEDS-MANUAL-CHECK section (prerequisites, the bundle targets tauri.conf.json declares, SmartScreen, and what nobody has verified); (11) rollback: pulling a release, reverting the version bump, restoring the previous tag's build.`,
    checks: 'Would the steps work in this order? Does every NEEDS-OPERATOR item match a DECISIONS_FOR_OPERATOR item? Does anything claim signing, notarization, a release pipeline or an updater exists when FACTS says it does not? Does the version-bump list match FACTS version_occurrences?',
  },
  {
    key: 'briefing', name: 'OPERATOR_BRIEFING', files: ['OPERATOR_BRIEFING.draft.md'], target: 'docs/redesign/OPERATOR_BRIEFING.md (a new file)', reader: 'the operator reading it cold on return, knowing nothing that happened while he was away',
    brief: `Write OPERATOR_BRIEFING.draft.md. (1) The state in one paragraph: what 0.9.0 is and where the run stands. (2) What shipped: each Stage C batch (FACTS git, the CHANGELOG batch sections, each VERDICTS.md tally line), the trading removal (D81) and the relicense, one line each with its merge commit. (3) What is open and why: register counts by severity x status from FACTS; the open critical/high/medium ids grouped by subsystem, one line each saying why open (not delivered / residual / needs_gui / blocked_tier4); the lows backlog, with the lows pre-triage result if docs/redesign/verification/r15/stage-c/lows-triage/LOWS_TRIAGE.md exists at the sha. (4) The operator-attended list: every item only he can do: each open DECISIONS_FOR_OPERATOR item (number, one line, smallest unblock, undo), the needs_gui ids and what their GUI proof needs, the keychain dev-signing setup (docs/redesign/KEYCHAIN_DEV_SIGNING.md), provider funding and OrbStack as that file states them. (5) How to relaunch: the app on the new code (pnpm tauri:dev per KEYCHAIN_DEV_SIGNING.md; the built .app) and how the R15 run resumes (docs/redesign/verification/vysted-r15-run-state.md at the sha). (6) Where every evidence file is: a table of paths (r15 stage0, census, stage-c batch-*/PLAN.md and VERDICTS.md, lows-triage, rc1 if present, this wave's ${EVR}), one line each; verify every path with git cat-file -e <sha>:<path> or git ls-tree. (7) What R15 decided on its own that he may want to revisit (DECISIONS_FOR_OPERATOR §1 and §3 done-and-revertable items), one line each with the undo. Where a number will move before rc2 (counts, gate results, release status) write the current value followed by '<!-- fill at rc2: <what> -->', or the marker alone when there is no value yet. Gloss any run jargon in one line. At most 300 lines.`,
    checks: 'Does every evidence path exist at the sha? Do the counts equal FACTS? Does every open item say why it is open? Is every operator-attended item one only he can do, with its unblock?',
  },
  {
    key: 'notes', name: 'RELEASE_NOTES', files: ['RELEASE_NOTES.draft.md'], target: 'the GitHub release body for 0.9.0 (part A) and the CHANGELOG.md v0.9.0 section (part B)', reader: 'a user upgrading to 0.9.0 (part A) and the next maintainer reading the changelog (part B)',
    brief: `Write RELEASE_NOTES.draft.md in two parts. PART A, the 0.9.0 release notes a user reads, grouped: 'What changed for you' (user-visible changes); 'Removed: trading' (no broker, order, paper account or live/paper switch; the tracked portfolio stays; what happens to old local broker data per DECISIONS_FOR_OPERATOR 3.1, as that file states it); 'Licence change' (PolyForm Strict 1.0.0 core + commercial; plugin contract and example plugin Apache-2.0); 'Fixed' (grouped by area, one line each, from the CHANGELOG R15 Stage C batch sections, only entries a batch VERDICTS.md certified: never list a not-delivered, residual or needs_gui entry as fixed); 'Known limitations' (unsigned build and the Gatekeeper path, no auto-update, Windows unverified, open high/medium counts by area from FACTS, needs_gui items, what DECISIONS_FOR_OPERATOR §2 leaves open). No register ids in part A. Then the line '<!-- PART B: CHANGELOG v0.9.0 section -->' and PART B, the '## v0.9.0' section draft in CHANGELOG.md's own voice (read its top sections at the sha): scope, the batches with their merge commits, decisions (docs/redesign/DECISIONS.md D-numbers since the base tag, read at the sha), a verification snapshot '<!-- fill at rc2: ci-local / smoke / rc gate results -->', carried forward. Register ids belong in part B.`,
    checks: 'Is every "Fixed" line certified in a batch VERDICTS.md (open each batch VERDICTS.md and check a sample of at least ten lines plus every line you doubt)? Is anything open presented as fixed? Is part A free of register ids and jargon?',
  },
  {
    key: 'state', name: 'STATE', files: ['CURRENT_STATE.draft.md', 'CURRENT_STATE.draft.diff', 'BLOCKERS.draft.md', 'BLOCKERS.draft.diff'], target: 'docs/CURRENT_STATE.md and BLOCKERS.md (repo root)', reader: 'the next maintainer who needs the honest current state',
    brief: `Refresh docs/CURRENT_STATE.md and BLOCKERS.md to the state at the sha, as proposals: the FULL proposed text of each in CURRENT_STATE.draft.md and BLOCKERS.draft.md (line 1 the header, the proposed file body from line 2), and a unified diff of each against the current file at the sha in CURRENT_STATE.draft.diff and BLOCKERS.draft.diff (the .diff files carry no header), made with: ${STATE_DIFFS}. Regenerate each diff whenever its draft changes. Surgical, per the repo's living-document rule; never delete a section wholesale. CURRENT_STATE: a new dated header ('as of <sha7>, 0.9.0 candidate'); a new top section with the current state (what R15 changed: trading removed, relicense, the Stage C batches, register counts from FACTS) that supersedes the older update notices, which stay as labelled history; stale present-tense claims in the body (test counts, 'redesign in flight', broker / kill-switch / audit-log sections, versions) corrected or marked historical in place; §7 works / buggy / deferred rewritten from FACTS and the batch VERDICTS. BLOCKERS: header 'as of 0.9.0 candidate <sha7>'; a new top section 'R15 open items' (the open Tier-4 DECISIONS_FOR_OPERATOR items by number, the open critical/high/medium ids grouped by subsystem, needs_gui ids, the MCP cold-bind --onedir carry-forward if still open at the sha); an existing item the code at the sha resolves is struck through with the resolving commit (verify each with git log and the code before striking); trading and broker items struck through 'removed with the feature (D81)' where not already. Every other existing item stays verbatim.`,
    checks: `Does each .diff apply to the file at the sha (copy the file into ${WORK} and run patch --dry-run <copy> < <diff>)? Is any section deleted wholesale? Does every strike-through name a resolving commit that really touches the item? Do the counts equal FACTS?`,
  },
]

const SCANS = [
  {
    key: 'secrets', name: 'SECRETS_SCAN', files: ['SECRETS_SCAN.md', 'SECRETS_SCAN.json'],
    brief: `ROLE: SECRETS SCAN (Fable; label stage-d-scan-secrets). Read-only. You report LOCATIONS and REDACTED SHAPES only: never let a matched value reach your terminal output or any file (no git grep -o, no raw matched lines, no reading a hit's file region); use counts, file names, or lines passed through the repo's redact().
TOOLS: 'which gitleaks trufflehog': use one if installed, with its redact flag and its report written to ${WORK}; never install either. In every case the baseline is the repo's scanner scripts/r15/history_secrets_scan.py (read its source first: the pre-push hook's rules plus provider shapes plus keyword-gated entropy; it writes only commit or blob, path, line, rule, length, entropy, sha10, fixture flags and a redacted line). Run it detached: cd ${REPO} && PYTHONDONTWRITEBYTECODE=1 nohup python3 scripts/r15/history_secrets_scan.py ${WORK}/history-secrets.json > ${WORK}/history-secrets.log 2>&1 & — then poll in separate short calls. It streams git log -p --all and sweeps every reachable blob, so it covers more than 004.
(1) Tree at the sha: a blob hit is 'present at the sha' when git -C ${REPO} rev-parse ${SHA}:<path> starts with its blob id. Cross-check with per-rule counts: git -C ${REPO} grep -IcE '<rule regex>' ${SHA} -- . ':!pnpm-lock.yaml' ':!**/Cargo.lock' ':!docs/redesign/verification/R15_BRIEF*' ':!docs/redesign/verification/r15/local' for the shapes sk-, sk-ant-, sk-or-v1-, sk-proj-, AKIA, ghp_/gho_/github_pat_, xox[abprs]-, '-----BEGIN … PRIVATE KEY-----', AIza, gsk_, xai-, literal api_key= / secret= / token= assignments, 'Bearer <long token>', JWTs. For line numbers use a small helper you write in ${WORK} that imports redact() from scripts/r15/history_secrets_scan.py and prints only path:line:rule:<redacted line>.
(2) History: for each history hit, reachable_from_004 (git merge-base --is-ancestor <commit> 004-r4-experience-rebuild) and pushed (git branch -r --contains <commit> is non-empty: a pushed secret is public).
(3) Secret-bearing file names: the script's filename_hits, plus git ls-tree -r --name-only ${SHA} filtered for .env, dev-keystore.json, keystore JSON, .pem/.p12/.key files; plus git -C ${REPO} ls-files --others --exclude-standard filtered the same way (names only, never opened: a file that is neither tracked nor ignored could be committed by accident; never 'git status', which can rewrite the index under the other workflows).
(4) Classify every hit: real_or_unknown / test_fixture / placeholder / redacted_example / allow_marked, with the reason (path is a test, fixture words, allow marker, value shape). A hit under R15_BRIEF* or r15/local/ is reported as path + rule only, never opened.
Write ${EV}/SECRETS_SCAN.json as {sha, tool, commits_scanned, blobs_scanned, tree_at_sha:[{path, line, rule, len, class, reason}], history:[{commit, path, line, rule, len, class, reachable_from_004, pushed}], filenames:[{path, where, tracked, ignored}], counts} (no sha10, no context lines, no values) and ${EV}/SECRETS_SCAN.md (line 1 '<!-- SCAN at ${SHA} by the Stage D docs wave -->'; method, counts table, then real_or_unknown hits first, pushed ones at the very top, each with the redacted shape, e.g. 'sk-or-v1-<64 chars>', never the value). Raw tool output stays in ${WORK}.
Return model, name 'SECRETS_SCAN', files, counts {tree_at_sha, history, filenames, real_or_unknown, pushed_real_or_unknown}, flagged (real_or_unknown hits: where = path:line or commit:path:line, what = rule + redacted shape, note = class + reachable/pushed), not_scanned, open_questions, summary ≤80 words.`,
  },
  {
    key: 'deps', name: 'DEPS_LICENCES', files: ['DEPS_LICENCES.md', 'DEPS_LICENCES.json'],
    brief: `ROLE: DEPENDENCY LICENCE SCAN (Fable; label stage-d-scan-deps). Read-only; installs nothing. Run every pnpm and cargo command below detached (nohup … > ${WORK}/<name>.log 2>&1 &) and poll it in separate short calls; if a log shows 'Blocking waiting for file lock' (another workflow's build holds the cargo or pnpm cache) for more than 5 minutes, kill only your own process and take that ecosystem's fallback. For every ecosystem record whether the installed tree matches the sha (git -C ${REPO} diff --quiet ${SHA} -- <lockfile or requirements>); when it differs, every row of that ecosystem carries 'installed tree differs from the sha'.
(1) pnpm (the frontend; production deps may reach the static export): cd ${REPO} && pnpm licenses list --json --prod > ${WORK}/pnpm-prod.json, and pnpm licenses list --json > ${WORK}/pnpm-all.json. If the command is missing or fails, read name / version / license from node_modules/.pnpm/*/node_modules/*/package.json with a short node script and say so. The prod set is scope 'bundled', the rest 'dev-only'.
(2) cargo (the Rust core, compiled into the app binary): cargo metadata --format-version 1 --no-deps --manifest-path src-tauri/Cargo.toml for the app's own licence fields, then cargo metadata --format-version 1 --locked --offline --manifest-path src-tauri/Cargo.toml > ${WORK}/cargo-metadata.json for every crate in Cargo.lock with license / license_file. Scope from resolve.nodes[].deps[].dep_kinds: reachable through normal deps is 'bundled', only through build deps 'build-only', only through dev deps 'dev-only'. Use 'cargo license' only if 'which cargo-license' finds it. If offline resolution fails, say so and fall back to the Cargo.lock names and versions with licence 'unknown (offline)'.
(3) Python: three venvs, each frozen into its own PyInstaller binary (FACTS sidecars): sidecar/.venv with sidecar/requirements.txt, sidecar/openbb_mcp_subprocess/.venv with its requirements.txt, sidecar/sec_edgar_mcp_subprocess/.venv with its requirements.txt. For each venv that exists: PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python scripts/r15/licence_scan.py <requirements.txt> ${WORK}/py-<name>.json (the repo's runtime-closure scanner; read its source first); those rows are 'bundled'. Then <venv>/bin/python -m pip list --format json for the full set; anything outside the closure is 'dev-only'. PyInstaller's bootloader is embedded in each binary (GPL with the bootloader exception): record it as a bundled row with that note. Use pip-licenses only if 'which pip-licenses' finds it. A missing venv: that ecosystem is 'not scanned: venv absent', never installed.
FLAG every package whose licence (SPDX expression, classifier or License field) contains AGPL, GPL, LGPL, SSPL, EUPL, OSL, CC-BY-NC, Commons Clause or BUSL, or is empty / unknown / UNLICENSED / custom. Before flagging an empty licence, check the package's own LICENSE file or its registry record by curl (crates.io/api/v1/crates/<name>/<ver>, pypi.org/pypi/<name>/<ver>/json, registry.npmjs.org/<name>/<ver>). For each flagged package: ecosystem, name, version, licence string verbatim, scope with the reason, and for bundled copyleft packages how it is linked (a static Rust crate, a Python module frozen into a PyInstaller binary, JS bundled into the static export): the facts a lawyer needs against the PolyForm Strict core, never a legal conclusion.
Write ${EV}/DEPS_LICENCES.json as {sha, ecosystems:{pnpm:{method, lock_matches_sha, counts_by_licence, packages:[{name, version, licence, scope}]}, cargo:{…}, python:{sidecar:{…}, openbb_mcp:{…}, sec_edgar_mcp:{…}}}, flagged:[{ecosystem, name, version, licence, scope, linkage, note}], not_scanned:[…]} and ${EV}/DEPS_LICENCES.md (line 1 '<!-- SCAN at ${SHA} by the Stage D docs wave -->'; method per ecosystem, a counts table, the flagged table with bundled copyleft first, the not-scanned list). Raw tool output stays in ${WORK}.
Return model, name 'DEPS_LICENCES', files, counts {per ecosystem: packages scanned}, flagged (where = ecosystem:name@version, what = licence, note = scope + linkage), not_scanned, open_questions, summary ≤80 words.`,
  },
  {
    key: 'licence', name: 'LICENCE_CHECK', files: ['LICENCE_CHECK.md'],
    brief: `ROLE: LICENCE CONSISTENCY CHECK (Fable; label stage-d-scan-licence). The intended state (operator decision, DECISIONS_FOR_OPERATOR 1.4): core under PolyForm Strict 1.0.0 + a commercial licence; the plugin contract (types/plugin.ts, types/plugin-runtime.ts) and the example plugin (plugins/example/) under Apache-2.0; commits before the relicense commit remain AGPL-3.0. Check every place that states or encodes a licence AT THE SHA against it: LICENSE (its text is PolyForm Strict 1.0.0: compare its sha256 with the one DECISIONS_FOR_OPERATOR 1.4 records, or curl https://polyformproject.org/licenses/strict/1.0.0.txt into ${WORK} and diff); LICENSE-APACHE; LICENSING.md; COMMERCIAL_LICENSE.md; package.json 'license'; src-tauri/Cargo.toml license / license-file; src-tauri/tauri.conf.json copyright or licence fields; every plugins/*/ manifest or package.json licence field and SPDX header; the headers of types/plugin.ts, types/plugin-runtime.ts and every plugins/example/ file; sidecar metadata (requirements carry none: check app.py, any __init__.py, pyproject or setup file at the sha for licence strings); the first-launch terms (src/modules/safety/DisclaimerFlow.tsx) and any About or Settings surface naming a licence; README.md; docs/BLUEPRINT.md §2; CLAUDE.md; CONTRIBUTING.md; docs/PLUGIN_DEVELOPMENT.md; docs/README.md; then a sweep: git -C ${REPO} grep -nIiE 'AGPL|GNU Affero|GPL-3|PolyForm|Apache-2|Apache License|licen[cs]ed under|dual.licen' ${SHA} -- . ':!CHANGELOG.md' ':!docs/archive' ':!docs/redesign/verification' ':!pnpm-lock.yaml' ':!**/Cargo.lock' ':!LICENSE' ':!LICENSE-APACHE'. Classify each hit: consistent / MISMATCH (states or implies, in the present tense, a licence other than the intended one for that file's scope) / historical (correctly past tense) / third-party (a dependency's own licence). Tier-1 files (CLAUDE.md, LICENSE*, COMMERCIAL_LICENSE.md, types/plugin.ts, src-tauri/tauri.conf.json, .github/) are listed like any other; you edit nothing.
Write ${EV}/LICENCE_CHECK.md (line 1 '<!-- SCAN at ${SHA} by the Stage D docs wave -->'): the intended state; a mismatch table: file | line | exact text quoted | the one-line fix | 'Tier-1: operator' where the file is locked; then the consistent and historical hits compactly; then open questions.
Return model, name 'LICENCE_CHECK', files, counts {checked, mismatches, tier1_mismatches, historical}, flagged (where = path:line, what = the quoted text, note = the fix + tier1 or not), not_scanned, open_questions, summary ≤80 words.`,
  },
]

const drafts = DRAFTS.filter(d => !SKIP.includes(d.key))
const scans = SCANS.filter(s => !SKIP.includes(s.key))
if (SKIP.length) log('skipped by args: ' + SKIP.join(', '))
if (!drafts.length && !scans.length) log('every lane skipped: only FACTS and the index are written')
log('lanes: ' + drafts.length + ' drafts (' + drafts.map(d => d.key).join(', ') + '), ' + scans.length + ' scans (' + scans.map(s => s.key).join(', ') + '); cap ' + CAP)

const draftPrompt = d => `${COMMON}

${LANES}

ROLE: DRAFTER ${d.name} (Fable; label stage-d-draft-${d.key}). Reader: ${d.reader}. Target, promoted by the lead at rc2 and never by you: ${d.target}. Your output: ${d.files.map(f => EV + '/' + f).join(', ')}. Sha ${SHA}.
INPUTS: ${EV}/FACTS.md first: do not re-derive what it states (if it is wrong, use the repo and say so in open_questions). Then the sources your brief names, at the sha.
${MODE_RULE}
BRIEF: ${d.brief}
${DRAFT_RULES}
Return model, name '${d.name}', files (repo-relative paths written), sections (headings written), open_questions, verify_markers (count of VERIFY markers left), summary ≤80 words.`

const criticPrompt = d => `${COMMON}

${LANES}

ROLE: CRITIC ${d.name} (Fable, fresh context; label stage-d-critic-${d.key}). You did not write this draft. Read ${d.files.map(f => EV + '/' + f).join(', ')} cold, as ${d.reader} would, then try to break it. Its target is ${d.target}. Sha ${SHA}.
CHECK: every command against package.json scripts, scripts/, .github/workflows/ and CLAUDE.md at the sha (git show ${SHA}:<path>): a command that does not exist, has the wrong flags or would not do what the draft says is WRONG. Every factual claim against ${EV}/FACTS.md and the repo at the sha (open the code, docs and evidence files; git cat-file -e ${SHA}:<path> for every path the draft names). The product facts in the rules above (no trading, the licence split, 0.9.0, three PyInstaller sidecars, the macOS production build proven later by the lead). No key, token or keystore content anywhere in it. Line 1 is '${HEADER}'. For this draft also: ${d.checks}
FINDINGS: numbered; each with kind wrong / missing / stale / unverifiable, the location (section + line), the evidence (path:line at the sha, or command + output excerpt) and the exact fix. Taste is not a finding. Verdict REVISE if any wrong, missing or stale finding would mislead the reader or make a step fail; otherwise PASS.
Write ${EV}/critic/${d.name}.md as you go, overwriting a file there that names another sha (line 1 '<!-- CRITIC of ${d.files.join(', ')} at ${SHA} -->'; the verdict; the findings; a short 'checked and correct' list). You edit nothing else.
Return model, name '${d.name}', verdict, findings (count), by_kind {wrong, missing, stale, unverifiable}, critic_file (repo-relative), summary ≤60 words.`

const revisePrompt = (d, c) => `${COMMON}

${LANES}

ROLE: REVISER ${d.name} (Fable; label stage-d-revise-${d.key}). The critic returned REVISE with ${c.findings} findings in ${EV}/critic/${d.name}.md. Apply every finding to ${d.files.filter(f => f.endsWith('.md')).map(f => EV + '/' + f).join(', ')} in place: fix what is wrong, add what is missing, update what is stale; for an unverifiable claim verify it now (path:line at the sha) or remove it or wrap it in '<!-- VERIFY: … -->'. A finding you judge mistaken: leave the text and give the reason in the footer. Keep line 1 exactly '${HEADER}'. ${DRAFT_RULES}${d.key === 'state' ? ` After editing, regenerate both diffs: ${STATE_DIFFS}.` : ''}
Then append to each .draft.md you changed the line '${FOOT}' followed by a section '## Critic findings applied' (the lead strips everything from that line down at promotion): one line per finding number: applied / verified instead / rejected: <reason>. One round only: never re-run the critic.
Return model, name '${d.name}', files (repo-relative), applied (count), rejected (count), open_questions, summary ≤60 words.`

const scanPrompt = s => `${COMMON}

${LANES}

Sha ${SHA}. Read ${EV}/FACTS.md first (sidecars, tools, licence facts); do not re-derive what it states.${MODE === 'refresh' ? ` REFRESH MODE: re-run the scan in full at this sha. If your previous output file exists, read its counts first and add a 'Since <previous sha7>' section (new, gone and changed hits) to the .md.` : ''}
${s.brief}`

const draftChain = async d => {
  const row = { name: d.name, key: d.key, kind: 'draft', files: d.files.map(f => EVR + '/' + f), status: 'FAILED', critic: null, findings: 0, by_kind: null, open_questions: [], note: '' }
  const r = await run(draftPrompt(d), { label: 'stage-d-draft-' + d.key, phase: 'Drafts', model: 'fable', effort: 'high', schema: DRAFT })
  if (!r) {
    row.note = 'drafter returned nothing; no critic ran'
    log(d.name + ': drafter returned nothing - no critic; a partial file may exist under ' + EVR)
    return row
  }
  row.open_questions = r.open_questions
  const extra = r.files.map(f => f.replace(REPO + '/', '')).filter(f => !row.files.includes(f))
  if (extra.length) log(d.name + ': drafter reported files outside its assignment (ignored by the index): ' + extra.join(', '))
  const c = await run(criticPrompt(d), { label: 'stage-d-critic-' + d.key, phase: 'Critic', model: 'fable', effort: 'high', schema: CRITIC })
  if (!c) {
    row.status = 'UNREVIEWED'
    row.note = 'critic returned nothing after the same-tier retry; draft stands unreviewed'
    log(d.name + ': critic returned nothing after the retry - UNREVIEWED')
    return row
  }
  row.critic = c.verdict
  row.findings = c.findings
  row.by_kind = c.by_kind
  if (c.verdict === 'PASS') {
    row.status = 'PASS'
    log(d.name + ': critic PASS (' + c.findings + ' findings)')
    return row
  }
  const v = await run(revisePrompt(d, c), { label: 'stage-d-revise-' + d.key, phase: 'Critic', model: 'fable', effort: 'high', schema: REVISE })
  if (!v) {
    row.note = 'critic REVISE, reviser returned nothing; findings in critic/' + d.name + '.md are unapplied'
    log(d.name + ': critic REVISE (' + c.findings + ') but the reviser returned nothing - FAILED')
    return row
  }
  row.status = 'REVISED'
  row.open_questions = [...row.open_questions, ...v.open_questions]
  row.note = v.applied + ' applied, ' + v.rejected + ' rejected'
  log(d.name + ': REVISED (' + v.applied + ' applied, ' + v.rejected + ' rejected of ' + c.findings + ')')
  return row
}

const scanChain = async s => {
  const row = { name: s.name, key: s.key, kind: 'scan', files: s.files.map(f => EVR + '/' + f), status: 'FAILED', critic: null, findings: 0, by_kind: null, open_questions: [], note: '' }
  const r = await run(scanPrompt(s), { label: 'stage-d-scan-' + s.key, phase: 'Scans', model: 'fable', effort: 'high', schema: SCAN })
  if (!r) {
    row.note = 'scanner returned nothing'
    log(s.name + ': scanner returned nothing - FAILED')
    return row
  }
  row.status = 'DONE'
  row.flagged = r.flagged
  row.counts = r.counts
  row.not_scanned = r.not_scanned
  row.open_questions = r.open_questions
  if (r.not_scanned.length) log(s.name + ': not scanned - ' + r.not_scanned.join('; '))
  log(s.name + ': done, ' + r.flagged.length + ' flagged')
  return row
}

// Drafts (each chained into its own critic + revise) and scans all start together; the limiter holds peak at CAP.
const all = [...drafts.map(d => ({ d, fn: () => draftChain(d) })), ...scans.map(s => ({ d: s, fn: () => scanChain(s) }))]
const got = await parallel(all.map(x => x.fn))
const rows = got.map((r, i) => r || { name: all[i].d.name, key: all[i].d.key, kind: DRAFTS.includes(all[i].d) ? 'draft' : 'scan', files: all[i].d.files.map(f => EVR + '/' + f), status: 'FAILED', critic: null, findings: 0, by_kind: null, open_questions: [], note: 'chain threw' })
for (const k of SKIP) {
  const d = [...DRAFTS, ...SCANS].find(x => x.key === k)
  rows.push({ name: d.name, key: k, kind: DRAFTS.includes(d) ? 'draft' : 'scan', files: d.files.map(f => EVR + '/' + f), status: 'SKIPPED', critic: null, findings: 0, by_kind: null, open_questions: [], note: 'skipped by args' })
}
const nDrafts = rows.filter(r => r.kind === 'draft' && ['PASS', 'REVISED', 'UNREVIEWED'].includes(r.status)).length
const nScans = rows.filter(r => r.kind === 'scan' && r.status === 'DONE').length
log('drafts ' + rows.filter(r => r.kind === 'draft').map(r => r.name + ' ' + r.status).join(', ') + '; scans ' + rows.filter(r => r.kind === 'scan').map(r => r.name + ' ' + r.status).join(', '))

// ---------------------------------------------------------------- 4. Collate
phase('Collate')
const verb = MODE === 'refresh' ? 'refresh' : 'wave'
const col = await run(`${COMMON}

ROLE: COLLATOR (Fable, mechanical; label stage-d-collate). No new judgement, no re-runs. Sha ${SHA}, mode ${MODE}, cap ${CAP}.
THE SCRIPT'S TALLY (authoritative for what ran; status PASS / REVISED / UNREVIEWED / FAILED for drafts, DONE / FAILED for scans, SKIPPED for lanes skipped by args): ${JSON.stringify(rows)}
(1) Check that every file a non-SKIPPED row names exists under ${EV}, and that line 1 of each .draft.md is '${HEADER}'. A missing file or a wrong header makes that row FAILED, with the reason.
(2) Output guard: every file under ${EV} must carry no secret value. Run the rules of scripts/r15/history_secrets_scan.py over them without printing any match: PYTHONDONTWRITEBYTECODE=1 python3 with sys.path including ${REPO}/scripts/r15, import history_secrets_scan as h, and for each file and line print only path:line:<rule name> for each h.RULES regex that matches. Replace each matched span in place with '<REDACTED:<rule>>' (these are this wave's own files) and list path:line:rule in redacted. Never print the matched text.
(3) Write ${EV}/STAGE_D_INDEX.md: a header (sha, mode, cap, the UTC time from 'date -u'); one row per output FILE: file | lane | status | critic findings (count, by kind, link to critic/<name>.md) | open questions for the lead (short); then 'How to promote at rc2': run this workflow with mode 'refresh' first; strip line 1 and everything from the line '${FOOT}' down; target paths (README.md, docs/RELEASE_RUNBOOK.md, docs/redesign/OPERATOR_BRIEFING.md, the GitHub release body + the CHANGELOG.md v0.9.0 section, docs/CURRENT_STATE.md + BLOCKERS.md); the state diffs apply with patch -p1 from the repo root.
(4) Write ${EV}/OPEN_QUESTIONS.md with only what the OPERATOR alone can answer: the open Tier-4 items (DECISIONS_FOR_OPERATOR numbers and smallest unblocks, from ${EV}/FACTS.md); the copyleft question if ${EV}/DEPS_LICENCES.md flags any bundled AGPL / GPL / LGPL / SSPL package (package, scope, linkage: facts, never a legal conclusion); LICENCE_CHECK mismatches in Tier-1 files; Windows (nothing verified); secrets hits classed real_or_unknown, pushed ones first (location + rule only); and draft open questions that need his decision. Everything the lead can answer stays in the index's open-questions column.
(5) Commit ONLY the output dir, on 004, never pushed. git -C ${REPO} rev-parse --abbrev-ref HEAD must print 004-r4-experience-rebuild; if not, do not commit (commit '' and the reason in summary), never checkout. Write the message to ${WORK}/commit.msg: subject 'docs(r15): stage-d docs ${verb} at ${SHA.slice(0, 7)} - <n> drafts, <m> scans' (n = draft rows PASS / REVISED / UNREVIEWED after your checks, m = scan rows DONE; the script counted ${nDrafts} and ${nScans}), a blank line, then 'Co-Authored-By: Claude <the model you run as> <noreply@anthropic.com>' and 'Claude-Session: https://claude.ai/code/session_01HJVZfFSmtgR7p7eW5tKNCg'. Then, in ONE shell call so nothing else can commit between them: git -C ${REPO} add -A -- ${EVR} && git -C ${REPO} -c core.hooksPath=/dev/null commit --only -F ${WORK}/commit.msg -- ${EVR} (the pathspec with --only keeps anything another agent staged out of this commit). If ${REPO}/.git/index.lock exists, wait 20 s in a separate call and retry, at most 5 times. Afterwards git -C ${REPO} show --stat --format= HEAD must list only files under ${EVR}; say so.
Return model, sha, rows [{file, status, findings}] as written in the index, open_questions (count in OPEN_QUESTIONS.md), redacted, files (repo-relative, committed), commit (the full sha, or ''), summary ≤80 words.`, { label: 'stage-d-collate', phase: 'Collate', model: 'fable', effort: 'medium', schema: COLLATE })

const out = rows.map(r => ({ name: r.name, kind: r.kind, status: r.status, files: r.files, critic: r.critic, findings: r.findings, flagged: r.flagged ? r.flagged.length : null, open_questions: r.open_questions.length, note: r.note }))
if (!col) {
  log('collator died: no index, no open-questions file, nothing committed; the drafts and scans sit uncommitted under ' + EVR)
  return { status: 'partial', sha: SHA, mode: MODE, rows: out, skipped: SKIP, open_questions: null, commit: null }
}
const failedByCollator = col.rows.filter(x => x.status === 'FAILED').map(x => x.file).filter(f => !rows.some(r => r.status === 'FAILED' && r.files.includes(f)))
if (failedByCollator.length) log('collator marked FAILED on its file checks: ' + failedByCollator.join(', '))
if (col.redacted.length) log('output guard redacted ' + col.redacted.length + ' span(s): ' + col.redacted.join(', '))
if (!col.commit) log('collator did not commit: ' + col.summary)
log('stage-d ' + MODE + ' @ ' + SHA.slice(0, 7) + ': ' + nDrafts + ' drafts, ' + nScans + ' scans, ' + col.open_questions + ' operator questions' + (col.commit ? '; commit ' + col.commit.slice(0, 7) : ''))
return { status: 'done', sha: SHA, mode: MODE, rows: out, index: col.rows, skipped: SKIP, open_questions: col.open_questions, redacted: col.redacted, commit: col.commit || null }
