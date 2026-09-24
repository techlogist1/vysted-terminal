export const meta = {
  name: 'r15-laya-groundwork',
  description: 'R15 scope change 2, Laya groundwork (verification evidence only, nothing enters the release): prep mode verifies the package, baselines the small typed text decisions, mines real candidate items, labels each shard with two independent Opus labellers (disagreements dropped), assembles the dataset, smoke-installs laya-mlx in a scratch venv and drafts the backlog entry; measure mode (idle lanes only) measures laya-mlx zero-shot against the dataset, has the verdict critiqued and inserts the backlog entry for the Stage E panel',
  whenToUse: 'R15 Laya groundwork. args {mode: prep|measure, sha, dry_run, max_shard, min_items, venv, scratch}. Runbook: LAYA_GROUNDWORK_PLAN.md',
  phases: [
    { title: 'Verify', detail: 'prep: package, licence and PyPI provenance, before any install' },
    { title: 'Baseline', detail: 'prep: code sites + evidence scouts, then the baseline analyst' },
    { title: 'Options', detail: 'prep: the fixed composer surface set' },
    { title: 'Mine', detail: 'prep: one candidate extractor per source family' },
    { title: 'Label', detail: 'prep: two independent labellers per shard, agreement computed in the script' },
    { title: 'Assemble', detail: 'prep: dataset files + DATASET.md, only when verified' },
    { title: 'Install', detail: 'prep: scratch-venv install + 20-item smoke, only when verified' },
    { title: 'Backlog draft', detail: 'prep: BACKLOG_ENTRY.md, verdict pending' },
    { title: 'Lane check', detail: 'measure: heavy-job and local-model lanes idle' },
    { title: 'Measure', detail: 'measure: zero-shot run, calibration, latency, RSS, current-path comparison' },
    { title: 'Critic', detail: 'measure: re-run a subset, check the arithmetic and sources' },
    { title: 'Backlog', detail: 'measure: final entry into r15/invent/BACKLOG.md' },
  ],
}
const REPO = '/Users/lokavyasingh/Documents/dev/vysted-terminal'
const A = args || {}
const MODE = A.mode
const DRY = A.dry_run === true || A.dry_run === 'true'
const SHA = A.sha ? String(A.sha) : ''
const SCRATCH = A.scratch || '/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad'
const VENV = A.venv || `${SCRATCH}/laya-venv`
const HF = `${SCRATCH}/laya-hf`
const intArg = (name, dflt, max) => {
  if (A[name] == null) return dflt
  const n = Number(A[name])
  if (!Number.isInteger(n) || n < 1 || n > max) throw new Error(`args.${name} must be an integer 1..${max} (got ${JSON.stringify(A[name])})`)
  return n
}
const MAX_SHARD = intArg('max_shard', 40, 200)
const MIN_ITEMS = intArg('min_items', 1000, 100000)
if (!['prep', 'measure'].includes(MODE)) throw new Error(`args.mode must be prep | measure (got ${JSON.stringify(MODE)})`)
if (A.dry_run != null && ![true, false, 'true', 'false'].includes(A.dry_run)) throw new Error(`args.dry_run must be a boolean (got ${JSON.stringify(A.dry_run)})`)
if (SHA && !/^[0-9a-f]{7,40}$/.test(SHA)) throw new Error(`args.sha must be a 7-40 char hex sha (got ${SHA})`)
if (MODE === 'prep' && !DRY && !SHA) throw new Error('args.sha (the 004-r4-experience-rebuild head recorded as base) is required for prep')
for (const [k, v] of [['scratch', SCRATCH], ['venv', VENV]]) if (typeof v !== 'string' || !v.startsWith('/')) throw new Error(`args.${k} must be an absolute path (got ${JSON.stringify(v)})`)
if (VENV === REPO || VENV.startsWith(REPO + '/')) throw new Error(`args.venv must live outside the repo, never sidecar/.venv (got ${VENV})`)

const LAYA = `${REPO}/docs/redesign/verification/r15/laya`
const LAYA_REL = 'docs/redesign/verification/r15/laya'
const BACKLOG_REL = 'docs/redesign/verification/r15/invent/BACKLOG.md'
const FAMILIES = [
  { fam: 'research', task: 'entity_match', src: 'research funnel traces for the large-cap, micro-cap and thematic prompts: look under r15/research/, r15/surface/, r15/stage-c/ and r15/census/ for funnel outputs, retrieved passages and citations. Each retrieved passage becomes an item asking whether it is about the entity the prompt asked for.', q: 'Is this passage about <entity>?' },
  { fam: 'collision', task: 'entity_match', src: 'the KSE name collision and its register siblings: the resolver and name-collision entries of docs/redesign/verification/vysted-r15-register.json (repro, evidence, raw_ids, and the raw finding files under r15/census/raw they point at) and the r15/battery/ resolver collections. Both the right entity and the colliding one yield items.', q: 'Is this passage about <entity>?' },
  { fam: 'composer', task: 'composer_intent', src: 'composer messages: the scenario harness prompts, the scripted owner-drives (r15/surface/*/ and tooling/PROMPT_surface_*.md), intent chunks, and the battery composer captures. The passage is the user message itself.', q: 'Which surface does this message belong to?' },
  { fam: 'news', task: 'holding_relevance', src: 'news and holdings evidence: the r15/battery/ news collections and the portfolio probes (r15/surface/portfolio-notes/, r15/census/ portfolio captures). The holdings list comes from the probe the item sits beside.', q: 'Is this item about a holding in <portfolio list>?' },
]

// Pacing: at most 6 agents at once (this session's per-workflow cap), FIFO so the early phases go first.
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
const GATE = limiter(6)
// Routing change 5: every agent names its model and effort; a dead agent gets ONE same-tier retry, never a third try.
const once = (prompt, opts) => {
  if (!['opus', 'sonnet'].includes(opts.model) || !opts.effort) throw new Error(`agent ${opts.label}: model must be opus|sonnet and effort explicit (routing 5)`)
  return GATE(() => agent(prompt, opts)).catch(e => { log('agent ' + opts.label + ' failed: ' + e); return null })
}
const run = (prompt, opts) => once(prompt, opts).then(r => r ? r : (log('agent ' + opts.label + ' on ' + opts.model + ' returned nothing (died or starved) - routing 5: same-tier retry, never a third try'), once(prompt, { ...opts, label: opts.label + '-retry' })))

const COMMON = `Repo: ${REPO}, branch 004-r4-experience-rebuild, main worktree (never switch its branch, never stash, reset or restore anything in it). R15 scope change 2, Laya groundwork: the operator decided no Laya code enters this release and no release document (README, CHANGELOG, runbooks, briefings, docs/*.md, DECISIONS*.md) mentions Laya; this work is verification evidence only. The operator is away; never ask, decide and record. Never read docs/redesign/verification/R15_BRIEF*.md or anything under docs/redesign/verification/r15/local/. WRITE SCOPE: only under ${LAYA}/ (mkdir -p)${MODE === 'measure' ? ` and ${REPO}/${BACKLOG_REL}` : ''}, plus the scratch dir ${SCRATCH} (scratch venv ${VENV}, model cache HF_HOME=${HF}); never touch sidecar/.venv, node_modules, src/, sidecar/, types/, CLAUDE.md, docs/redesign/verification/r15/spend-ledger.jsonl or any release document; everything else in the repo is read-only for you. Trading is permanently out of this product: never frame anything as trading, never use broker or order language, and never pair the words low-latency and trading. Never print, copy or commit a secret (API keys, tokens, auth headers, keychain values); skip any evidence passage that contains one. Never speculate about code or files you have not opened; every number you write carries its source path or is marked unknown. Shell: cat is aliased to bat and ls to eza (both can hang): use /bin/cat, /bin/ls or your Read tool. HARNESS STALL RULE (a 3-minute no-progress watchdog kills the agent and restarts it from scratch): NO single tool call may run longer than ~120 s. Anything longer (pip/uv installs, wheel downloads, model loads, measurement runs, large greps over the census) MUST be started detached - 'nohup <cmd> > <log> 2>&1 &' or the Bash tool's run_in_background - and then polled with SEPARATE short calls ('sleep 60; tail -n 5 <log>'), never an 'until ... sleep' loop inside one call. Keep emitting a tool call at least every 2 minutes. Write your own result file as you go (named in your role); if it already exists from a previous attempt of your role (a restart), read it and CONTINUE from it instead of redoing the work. Your final text IS the return value: return only the compact structured object.`
const COMMIT = (paths, msg) => `COMMIT: refuse (commit '', pushed false, say why) unless git -C ${REPO} rev-parse --abbrev-ref HEAD prints 004-r4-experience-rebuild. Then git -C ${REPO} add -- ${paths} and ONE call: git -C ${REPO} -c core.hooksPath=/dev/null commit --only -m '${msg}' -m 'Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>' -- ${paths} (explicit paths only; never git add -A; CLAUDE.md and r15/spend-ledger.jsonl carry the lead's uncommitted edits and must never ride your commit). Nothing changed: commit nothing, commit ''. Then push: GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20" git -C ${REPO} push origin 004-r4-experience-rebuild. A rejected push (origin moved) is never rebased, pulled or forced: pushed false with the error; the lead pushes.`

const S = (props, req) => ({ type: 'object', properties: props, required: req || Object.keys(props) })
const STR = { type: 'string' }
const NUM = { type: 'number' }
const BOOL = { type: 'boolean' }
const STRS = { type: 'array', items: STR }
const OBJ = { type: 'object' }
const NSTR = { type: ['string', 'null'] }
const NNUM = { type: ['number', 'null'] }
const NBOOL = { type: ['boolean', 'null'] }
const VERIFY = S({ verified: BOOL, reasons: STRS, license: STR, repo: STR, versions: S({ laya: NSTR, laya_mlx: NSTR }), python_requires: NSTR, macos_requires: NSTR, install_command: NSTR, api_summary: STR, finetune_format: NSTR, risks: STRS })
const SITES = S({ sites: { type: 'array', items: S({ type: STR, file: STR, line: NUM, path_today: { type: 'string', enum: ['paid_llm', 'local_model', 'heuristic', 'none'] }, keyless: NBOOL, hint: STR }) }, notes: STRS, summary: STR })
const EVID = S({ observations: { type: 'array', items: S({ type: STR, metric: STR, value: NNUM, unit: STR, source: STR }) }, sessions_basis: STR, notes: STRS, summary: STR })
const DECISION = S({ type: STR, sites: NUM, per_session: NNUM, latency_ms: NNUM, cost_usd: NNUM, keyless: NBOOL })
const BASE = S({ decisions: { type: 'array', items: DECISION }, totals: S({ per_session: NNUM, cost_usd_per_session: NNUM }), summary: STR })
const OPTIONS = S({ options: { type: 'array', items: STR, minItems: 2, maxItems: 8 }, source: STR })
const MINE = S({ family: STR, file: STR, count: NUM, ids_first: STR, ids_last: STR, notes: STRS })
const LABELS = S({ shard: STR, labels: { type: 'array', items: S({ id: STR, answer: STR, confidence: NUM, note: STR }, ['id', 'answer', 'confidence']) } })
const ASSEMBLE = S({ counts: S({ entity_match: NUM, composer_intent: NUM, holding_relevance: NUM, dropped: NUM }), majority_rates: OBJ, commit: STR, pushed: BOOL })
const INSTALL = S({ feasible: BOOL, versions: OBJ, peak_rss_mb: NNUM, smoke_items: NUM, p50_ms: NNUM, error: NSTR, commit: STR, pushed: BOOL })
const DRAFT = S({ file: STR, ingestion_exists: NBOOL, summary: STR, commit: STR, pushed: BOOL })
const LANE = S({ clear: BOOL, state: OBJ })
const MEASURE = S({ ok: BOOL, error: NSTR, seed: NUM, items: OBJ, noul: OBJ, composer: OBJ, calibration: OBJ, latency: OBJ, rss: OBJ, current_path: OBJ, verdict_file: STR, summary: STR })
const CRITIC = S({ ok: BOOL, corrections: STRS })
const FINAL = S({ inserted: BOOL, commit: STR, pushed: BOOL })

const dry = (spawn, writes) => {
  spawn.forEach(s => log(`dry_run: would spawn ${s.label} (${s.model}/${s.effort})`))
  return { mode: MODE, dry_run: true, sha: SHA || null, max_shard: MAX_SHARD, min_items: MIN_ITEMS, venv: VENV, would_spawn: spawn, writes }
}

// ---------------------------------------------------------------- measure mode (only when the local-model and heavy-job lanes are idle)
if (MODE === 'measure') {
  if (DRY) return dry([{ label: 'laya-lane-check', model: 'sonnet', effort: 'medium' }, { label: 'laya-measure', model: 'sonnet', effort: 'high' }, { label: 'laya-verdict-critic', model: 'opus', effort: 'high' }, { label: 'laya-backlog', model: 'sonnet', effort: 'high' }], [`${LAYA_REL}/measurements/*.json`, `${LAYA_REL}/VERDICT.md`, `${LAYA_REL}/BACKLOG_ENTRY.md (final)`, `${BACKLOG_REL} (entry inserted)`, 'one commit + push on 004'])

  const lane = await run(`${COMMON}

ROLE: LANE CHECKER (Sonnet; label laya-lane-check). Read-only; write ${LAYA}/measurements/lane.json with what you saw. Check, each in its own short call: (1) heavy jobs: pgrep -fl for ci-local, cargo, 'pnpm build', 'tauri build', pyinstaller, vitest, pytest; (2) the local-model lane: ollama ps; a listed model counts as a generation in progress unless the ollama runner process (ps -o pid,%cpu,command) sits under 5% CPU in two samples 30 s apart; (3) sidecars up: lsof -nP -iTCP -sTCP:LISTEN | grep '127.0.0.1:52' (record port and command); (4) sysctl -n vm.loadavg and hw.ncpu; (5) free memory from vm_stat (free + inactive pages x page size, in GB). clear = no heavy job AND no ollama generation in progress AND 1-minute load below 0.75 x ncpu AND free+inactive memory at least 3 GB. Return clear and state {heavy_jobs, ollama, sidecars_up, load, ncpu, free_gb, reasons_not_clear}.`, { label: 'laya-lane-check', phase: 'Lane check', model: 'sonnet', effort: 'medium', schema: LANE })
  log(`lane check: ${lane ? (lane.clear ? 'clear' : 'BUSY') : 'died'}; state ${JSON.stringify(lane?.state ?? null)}`)
  if (!lane || !lane.clear) return { mode: 'measure', aborted: lane ? 'lane_busy' : 'lane_check_died', state: lane?.state ?? null }

  const m = await run(`${COMMON}

ROLE: MEASURER (Sonnet; label laya-measure). Inputs: ${LAYA}/dataset/{entity_match,composer_intent,holding_relevance}.jsonl, ${LAYA}/DATASET.md, ${LAYA}/PACKAGE_VERIFICATION.md (the laya-mlx API: choice / score / noul), ${LAYA}/INSTALL.md (the verified install and the smoke commands), ${LAYA}/BASELINE.json (the current path per decision type). If INSTALL.md says NOT FEASIBLE, the venv ${VENV} is missing, or the dataset files are missing: stop, ok false, error naming what is missing. Lane state at launch: ${JSON.stringify(lane.state)} (sidecars up are recorded from this). Work with ${VENV}/bin/python and HF_HOME=${HF}; your scripts live in ${SCRATCH}/laya-measure/ (never in the repo); every run is detached and polled, and every measurement process exits at its end so the model is unloaded. (1) Zero-shot: run every dataset item through laya-mlx with its task type: entity_match and holding_relevance as noul (yes probability), composer_intent as choice over its fixed options. (2) Split each task's items into halves A and B with python random.Random(918).shuffle over the sorted ids; record the seed and the split in measurements/split.json. (3) noul tasks: precision/recall/F1 over a confidence-threshold sweep (0.05 steps) on B; the gate = the lowest threshold with precision >= 0.90 on B if any, else the max-F1 point; report both with the majority-class rate. composer_intent: accuracy and the per-option confusion matrix on B vs the majority-class rate. (4) Calibration: fit ONE temperature on A (minimise NLL), report ECE with 10 equal-width bins and the reliability table on B before and after. (5) Latency: per-item p50/p99 single and batched (state the batch size), throughput items/s; peak RSS via /usr/bin/time -l and steady RSS mid-run (ps -o rss), with the sidecars up that the lane check recorded. (6) Current path: for each decision type in BASELINE.json with a keyless heuristic function in the sidecar source, import it read-only from ${REPO}/sidecar with ${REPO}/sidecar/.venv/bin/python (PYTHONPATH=${REPO}/sidecar, cwd ${SCRATCH}/laya-measure; never install into or modify that venv) and run it on the same B items; paid paths are marked 'not run (needs a key)'. Write ${LAYA}/measurements/*.json (one per step, as you go) and ${LAYA}/VERDICT.md: every number with the file it came from and the exact commands, the honest comparison, and a one-paragraph verdict (worth fine-tuning or not, and why). Do not commit. Return ok, error, seed, items {per task counts}, noul {per task: gate, precision, recall, f1, majority_rate}, composer {accuracy, majority_rate}, calibration {temperature, ece_before, ece_after}, latency {p50_ms, p99_ms, batched_p50_ms, batch_size, throughput_per_s}, rss {peak_mb, steady_mb, sidecars_up}, current_path {per type: result or 'not run (needs a key)'}, verdict_file, summary <=120 words.`, { label: 'laya-measure', phase: 'Measure', model: 'sonnet', effort: 'high', schema: MEASURE })
  log(`measure: ${m ? (m.ok ? 'ok' : 'FAILED: ' + m.error) : 'died'}; items ${JSON.stringify(m?.items ?? null)}; noul ${JSON.stringify(m?.noul ?? null)}; composer ${JSON.stringify(m?.composer ?? null)}; calibration ${JSON.stringify(m?.calibration ?? null)}; latency ${JSON.stringify(m?.latency ?? null)}; rss ${JSON.stringify(m?.rss ?? null)}`)
  if (!m || !m.ok) return { mode: 'measure', numbers: m, critic: null, inserted: false, commits: [] }

  const critic = await run(`${COMMON}

ROLE: VERDICT CRITIC (Opus, fresh; label laya-verdict-critic). The measurer reported: ${JSON.stringify(m)}. Read ${LAYA}/VERDICT.md and ${LAYA}/measurements/*.json. Re-run the exact commands from VERDICT.md on a subset (at least 50 items per task, detached, HF_HOME=${HF}, ${VENV}/bin/python, scripts in ${SCRATCH}/laya-critic/) and confirm the numbers reproduce within noise. Check the arithmetic from the raw per-item outputs yourself: the held-out split really is disjoint and seeded as recorded, ECE with 10 bins before and after the temperature, precision/recall at the stated gate and that the gate rule was applied as written, accuracy and the majority-class baselines per task. Check the honesty of the comparison with the current path (nothing paid claimed as run; no heuristic run on different items) and that every number has a source. Fix VERDICT.md (and the measurement json) in place where wrong, adding a 'Critic corrections' section; do not commit. Return ok (true when nothing needed correcting) and corrections (one line each).`, { label: 'laya-verdict-critic', phase: 'Critic', model: 'opus', effort: 'high', schema: CRITIC })
  log(`critic: ${critic ? (critic.ok ? 'ok' : critic.corrections.length + ' corrections: ' + critic.corrections.join(' | ')) : 'died - VERDICT.md stands uncritiqued'}`)

  const fin = await run(`${COMMON}

ROLE: BACKLOG FINALIZER (Sonnet; label laya-backlog). Read ${LAYA}/VERDICT.md (as corrected by the critic: ${JSON.stringify(critic)}) and ${LAYA}/BACKLOG_ENTRY.md. (1) Replace 'Verdict: pending MEASURE' in BACKLOG_ENTRY.md with the verdict and its numbers (gate precision/recall per noul task, composer accuracy vs majority, ECE before/after, p50/p99, peak and steady RSS, the current-path comparison), each with its file pointer. (2) Read ${REPO}/${BACKLOG_REL} in full first and insert the entry in the ranked list's own format: if the file has a candidates (unranked) section, append it there as an unranked candidate for the Stage E judge panel; else add such a section after the ranked list and put it there. The panel ranks it; nothing is built. Touch nothing else in that file. (3) ${COMMIT(`${LAYA_REL} ${BACKLOG_REL}`, 'docs(r15): laya measure verdict and backlog candidate (scope change 2)')} Return inserted, commit, pushed.`, { label: 'laya-backlog', phase: 'Backlog', model: 'sonnet', effort: 'high', schema: FINAL })
  log(`backlog: inserted ${fin?.inserted ?? 'died'}; commit ${(fin?.commit || '').slice(0, 7) || 'none'}; pushed ${fin?.pushed ?? false}`)
  return { mode: 'measure', numbers: m, critic, inserted: !!fin?.inserted, commits: [fin?.commit].filter(Boolean) }
}

// ---------------------------------------------------------------- prep mode
if (DRY) return dry([
  { label: 'laya-verify', model: 'opus', effort: 'high' },
  { label: 'laya-scout-code', model: 'sonnet', effort: 'medium' },
  { label: 'laya-scout-evidence', model: 'sonnet', effort: 'medium' },
  { label: 'laya-baseline', model: 'opus', effort: 'high' },
  { label: 'laya-options', model: 'sonnet', effort: 'medium' },
  ...FAMILIES.map(f => ({ label: `laya-mine-${f.fam}`, model: 'sonnet', effort: 'high' })),
  ...FAMILIES.flatMap(f => ['A', 'B'].map(r => ({ label: `laya-label-${f.fam}-<k>-${r} (one per shard of ${MAX_SHARD} items; shard count = ceil(extracted/${MAX_SHARD}))`, model: 'opus', effort: 'high' }))),
  { label: 'laya-assemble (only when verified)', model: 'sonnet', effort: 'medium' },
  { label: 'laya-install (only when verified and assembled)', model: 'sonnet', effort: 'high' },
  { label: 'laya-backlog-draft', model: 'sonnet', effort: 'high' },
], [`${LAYA_REL}/PACKAGE_VERIFICATION.md`, `${LAYA_REL}/baseline/{code-sites,evidence}.json`, `${LAYA_REL}/BASELINE.md + BASELINE.json`, `${LAYA_REL}/OPTIONS.json`, `${LAYA_REL}/candidates/<family>.jsonl`, `${LAYA_REL}/labels/<family>-<k>-<A|B>.json`, `${LAYA_REL}/dataset/{entity_match,composer_intent,holding_relevance,DROPPED}.jsonl`, `${LAYA_REL}/DATASET.md`, `${LAYA_REL}/INSTALL.md`, `${LAYA_REL}/BACKLOG_ENTRY.md`, `scratch venv ${VENV}`, 'up to three commits + pushes on 004 (assemble, install, backlog draft), r15/laya/ only'])

// P1 Verify, P2 Baseline and P3 Options start together; mining waits only for the composer options.
const verifyP = run(`${COMMON}

ROLE: PACKAGE VERIFIER (Opus; label laya-verify). Nothing is installed anywhere by you: no pip install, no uv pip install, no import of the package. Claims to confirm or refute, each with its source: Laya is an open decision model from Convai Innovations at github.com/NandhaKishorM/laya, said to be Apache-2.0 and released 18 Sep 2026; a 421M ModernBERT encoder (not a language model) that answers typed questions over a passage in one forward pass: 'choice' over a fixed option set with probabilities, 'score' on an ordered rubric, 'noul' as a yes/no probability; PyPI 'laya' (PyTorch) and 'laya-mlx' (Apple Silicon, macOS 14+, Python 3.11+, under 1 GB resident); zero-shot accuracy reportedly below the majority-class baseline, a base to fine-tune, over-confident until a temperature is fitted, weak past ~20 options and on ordinal scores, a context of a few hundred tokens; generates nothing. Investigate: (1) the GitHub repo (owner, the LICENSE file text, release/tag dates, README, model card, where the weights are hosted and their own licence) via WebFetch/WebSearch or gh api; (2) PyPI 'laya' and 'laya-mlx' via https://pypi.org/pypi/<name>/json (authors, versions, upload dates, project URLs pointing back to that repo, python_requires, requires_dist) and pip index versions; (3) the artefacts: pip download --no-deps --only-binary=:all: <name> -d ${SCRATCH}/laya-verify (wheels only: an sdist would run build code; if only an sdist exists, fetch its file URL from the JSON with curl and inspect it with tar, never build it), then unzip -l / read METADATA, RECORD, entry_points, any .pth file, and setup.py/pyproject build hooks for install-time or import-time code, network calls, or telemetry. Typosquat check: the PyPI projects must link to the same repo/owner. verified = true only if the licence is Apache-2.0 (or another permissive licence you name), the PyPI projects trace to that repo, no install-time hooks or unexplained import-time network or code execution, and laya-mlx supports this Mac (arm64, the Python you can offer: ~/.local/bin/python3.12 or /opt/homebrew/bin/python3.13). Write ${LAYA}/PACKAGE_VERIFICATION.md as you go: every claim with confirmed / refuted / unverifiable and its source URL or file, the artefact inspection, the licence notice text needed later, the API usage, the fine-tune data format the package documents (verbatim field names if any), and risks. Do not commit. Return verified, reasons, license, repo, versions {laya, laya_mlx}, python_requires, macos_requires, install_command (pinned to the verified version), api_summary (how to call choice/score/noul in laya-mlx, from the docs), finetune_format (verbatim, or null if undocumented), risks.`, { label: 'laya-verify', phase: 'Verify', model: 'opus', effort: 'high', schema: VERIFY }).then(v => {
  log(`verify: ${v ? (v.verified ? 'VERIFIED' : 'NOT verified') : 'died'}; licence ${v?.license ?? '?'}; laya ${v?.versions?.laya ?? '-'}, laya-mlx ${v?.versions?.laya_mlx ?? '-'}; reasons: ${(v?.reasons || []).join(' | ')}`)
  return v
})

const baselineP = (async () => {
  const [code, ev] = await parallel([
    () => run(`${COMMON}

ROLE: CODE-SITES SCOUT (Sonnet; label laya-scout-code). Read-only on code. grep ${REPO}/sidecar/ and ${REPO}/src/ (skip node_modules, .venv, tests only as corroboration) for every small typed text decision the terminal makes: entity/passage match in the resolver and the research funnel (is this retrieved passage about the entity asked for; the KSE-class name collision), composer surface routing / intent classification, news-to-holding relevance, thesis contradiction, and similar yes/no or pick-one decisions over short text. Per site: type (entity_match | composer_intent | holding_relevance | thesis_contradiction | other:<name>), file, line, path_today (paid_llm = a BYOK model round-trip, local_model, heuristic, none = the decision is not made today), keyless (works with no key: true/false/null), hint (the code's own latency, timeout, token or cost hints, or ''). Open each site before recording it. Write ${LAYA}/baseline/code-sites.json as you go. Return sites, notes, summary <=80 words.`, { label: 'laya-scout-code', phase: 'Baseline', model: 'sonnet', effort: 'medium', schema: SITES }),
    () => run(`${COMMON}

ROLE: EVIDENCE SCOUT (Sonnet; label laya-scout-evidence). Read-only. From ${REPO}/docs/redesign/verification/r15/ (spend-ledger.jsonl, battery/, surface/, research/, census/, lifecycle/, stage-c/; never local/) derive, for the decision types entity_match, composer_intent, holding_relevance, thesis_contradiction and any other small typed text decision you find: per-session counts (how many such decisions one session makes, from real transcripts or captures), measured latencies and costs (tokens and USD from the spend ledger rows that correspond). Each observation: type, metric (e.g. per_session_count, latency_ms, cost_usd_per_call), value (null when the evidence only shows it happens), unit, source (file path plus line or record id). Say what a 'session' means in your sources (sessions_basis). Write ${LAYA}/baseline/evidence.json as you go. Return observations, sessions_basis, notes, summary <=80 words.`, { label: 'laya-scout-evidence', phase: 'Baseline', model: 'sonnet', effort: 'medium', schema: EVID }),
  ])
  log(`baseline scouts: ${code ? code.sites.length + ' code sites' : 'code scout died'}; ${ev ? ev.observations.length + ' evidence observations' : 'evidence scout died'}`)
  return run(`${COMMON}

ROLE: BASELINE ANALYST (Opus; label laya-baseline). Code-sites scout (also in ${LAYA}/baseline/code-sites.json): ${JSON.stringify(code)}. Evidence scout (also in ${LAYA}/baseline/evidence.json): ${JSON.stringify(ev)}. Spot-check the scouts (open at least one site per decision type and one evidence source per number you use; drop what does not hold and say so). Write ${LAYA}/BASELINE.md and ${LAYA}/BASELINE.json: per decision type - the sites (file:line list), estimated count per session with its derivation, latency, cost per session, keyless yes/no, source pointers; every number sourced or marked unknown (null), never invented; then a one-paragraph business case with the totals (what these decisions cost a session today, in paid round-trips, latency and USD, and which are skipped entirely keyless). Do not commit. Return decisions [{type, sites, per_session, latency_ms, cost_usd, keyless}], totals {per_session, cost_usd_per_session}, summary <=120 words.`, { label: 'laya-baseline', phase: 'Baseline', model: 'opus', effort: 'high', schema: BASE })
})().then(b => {
  log(`baseline: ${b ? b.decisions.map(d => `${d.type} sites=${d.sites} per_session=${d.per_session ?? '?'} cost=${d.cost_usd ?? '?'}`).join('; ') + `; totals ${JSON.stringify(b.totals)}` : 'analyst died - BASELINE.md not written'}`)
  return b
})

const optionsP = run(`${COMMON}

ROLE: OPTIONS SCOUT (Sonnet; label laya-options). Read-only on code. Find the composer's real surface routing: where a composer message is routed to a surface / intent (grep ${REPO}/src/ for the composer and its intent routing, and ${REPO}/sidecar/ for any server-side intent classification). Derive the FIXED option set of at most 8 surface names the code actually routes to (lowercase, one word each where the code allows; include 'other' only if the code has a fallback route). Write ${LAYA}/OPTIONS.json {options, source, notes}. Return options and source (file:line list).`, { label: 'laya-options', phase: 'Options', model: 'sonnet', effort: 'medium', schema: OPTIONS }).then(o => {
  log(`options: ${o ? o.options.join(', ') + ' (' + o.source + ')' : 'died - the composer family is skipped'}`)
  return o
})

// P4 Mine -> P5 Label, pipelined per family. Agreement is computed here, never by an agent.
const TOT = { candidates: 0, labelled: 0, agreed: 0, dropped: 0 }
const AGREED = {}
const DROPPED = {}
const norm = (task, opts, x) => {
  if (x == null) return null
  const s = String(x).trim().toLowerCase()
  if (s === 'skip') return 'skip'
  if (task === 'composer_intent') return (opts || []).find(o => o.toLowerCase() === s) || null
  return s === 'yes' || s === 'no' ? s : null
}
const fams = await pipeline(FAMILIES,
  async (_, f) => {
    let opts = null
    if (f.task === 'composer_intent') {
      const o = await optionsP
      if (!o) { log(`mine ${f.fam}: skipped (no composer option set)`); return null }
      opts = o.options
    }
    const r = await run(`${COMMON}

ROLE: CANDIDATE EXTRACTOR '${f.fam}' (Sonnet; label laya-mine-${f.fam}). Task type: ${f.task}. Source family: ${f.src} Paths are under ${REPO}/docs/redesign/verification/ unless absolute. Output: ${LAYA}/candidates/${f.fam}.jsonl, one JSON object per line: {"id": "${f.fam}-<n>" (n contiguous from 1 in file order, no gaps), "task": "${f.task}", "passage": REAL text copied verbatim from the evidence (a window of at most ~300 tokens around the relevant span; never invented, never paraphrased, never summarised), "question": "${f.q}" (fill the placeholder from the evidence), "options": ${opts ? JSON.stringify(opts) + ' (exactly this list, verbatim)' : 'null'}, "context": {the entity / holdings / prompt named${f.task === 'holding_relevance' ? ', holdings as a list' : ''}}, "provenance": {"file": repo-relative path, "locator": line number or record id, "sha": "${SHA}"}}. Do NOT label: never add an answer field, and do not pre-select items for one answer - take what the evidence yields, including the items whose honest answer would be no${f.task === 'composer_intent' ? ' or other' : ''}. Drop near-duplicates (the same passage and question up to whitespace or a trivial edit). Aim for as many real items as the evidence honestly yields, up to ~600 for this family; when the evidence runs out first, stop and say so in notes with the count. Append lines as you go (a restart reads the file, continues after its last id and never renumbers). Finish with a python3 check that every line parses, ids run ${f.fam}-1..${f.fam}-<count> with no gap or repeat, and no passage exceeds ~1500 characters; fix what it shows. Return family '${f.fam}', file (repo-relative), count, ids_first, ids_last, notes (sources used with item counts; where the evidence ran out).`, { label: `laya-mine-${f.fam}`, phase: 'Mine', model: 'sonnet', effort: 'high', schema: MINE })
    if (!r) { log(`mine ${f.fam}: died twice - no items from this family`); return null }
    const count = Math.max(0, Math.floor(r.count || 0))
    TOT.candidates += count
    log(`mine ${f.fam}: ${count} candidates (${r.ids_first}..${r.ids_last}); running candidates ${TOT.candidates}; notes: ${(r.notes || []).join(' | ')}`)
    if (count && (r.ids_first !== `${f.fam}-1` || r.ids_last !== `${f.fam}-${count}`)) log(`mine ${f.fam}: ids ${r.ids_first}..${r.ids_last} are not ${f.fam}-1..${f.fam}-${count}; labellers mark missing ids and they drop`)
    return { ...r, count, opts }
  },
  async (r, f) => {
    if (!r || !r.count) return { fam: f.fam, task: f.task, count: 0, shards: 0, agreed: 0, dropped: 0 }
    const shards = []
    for (let lo = 1; lo <= r.count; lo += MAX_SHARD) {
      const ids = []
      for (let n = lo; n <= Math.min(r.count, lo + MAX_SHARD - 1); n++) ids.push(`${f.fam}-${n}`)
      shards.push({ k: shards.length + 1, ids })
    }
    log(`label ${f.fam}: ${shards.length} shards of <=${MAX_SHARD} items, ${shards.length * 2} labellers`)
    AGREED[f.fam] = []
    DROPPED[f.fam] = []
    const rule = f.task === 'composer_intent'
      ? `answer = exactly one of ${JSON.stringify(r.opts)} (the surface the message belongs to), or "skip"`
      : f.task === 'entity_match'
        ? 'answer = "yes" only if the passage is about the named entity itself (not a same-name, similar-ticker or colliding different entity, not merely its sector), else "no"; or "skip"'
        : 'answer = "yes" only if the item is about one of the listed holdings (the issuer itself or its own securities, not merely its sector or a peer), else "no"; or "skip"'
    await parallel(shards.map(sh => async () => {
      const shard = `${f.fam}-${sh.k}`
      const labeller = role => run(`${COMMON}

ROLE: LABELLER ${role} (Opus; label laya-label-${shard}-${role}). Shard ${shard}: items ${sh.ids[0]} through ${sh.ids[sh.ids.length - 1]} of ${LAYA}/candidates/${f.fam}.jsonl, ids ${JSON.stringify(sh.ids)}. Read those lines only (one python3 command filtering by id). You label independently: never open ${LAYA}/labels/ files other than your own, never read any other labeller's output, never consult another agent. For each item answer its question from the passage and its context alone (no outside lookup, no guessing beyond the text): ${rule}. "skip" = the item is unusable (malformed, not real evidence text, truncated so the answer cannot be decided, or the question does not fit the passage). confidence = your probability that the answer is right, 0..1. note only when it helps (<=15 words). An id missing from the file: answer "skip", note "missing". Write ${LAYA}/labels/${shard}-${role}.json ({shard, labels}) as you go. Return shard '${shard}' and labels [{id, answer, confidence, note?}], one per id.`, { label: `laya-label-${shard}-${role}`, phase: 'Label', model: 'opus', effort: 'high', schema: LABELS })
      const [a, b] = await parallel([() => labeller('A'), () => labeller('B')])
      const pick = res => {
        const m = {}
        ;(res?.labels || []).forEach(l => { if (!(l.id in m)) m[l.id] = l.answer })
        return m
      }
      const ma = pick(a)
      const mb = pick(b)
      let ok = 0
      sh.ids.forEach(id => {
        const x = norm(f.task, r.opts, ma[id])
        const y = norm(f.task, r.opts, mb[id])
        const n = Number(id.slice(f.fam.length + 1))
        if (x && x === y && x !== 'skip') { AGREED[f.fam].push([n, x]); ok++ } else DROPPED[f.fam].push([n, ma[id] ?? null, mb[id] ?? null])
      })
      TOT.labelled += sh.ids.length
      TOT.agreed += ok
      TOT.dropped += sh.ids.length - ok
      log(`label ${shard}: ${ok}/${sh.ids.length} agreed (${Math.round(100 * ok / sh.ids.length)}%)${a ? '' : ', labeller A died'}${b ? '' : ', labeller B died'}; running ${TOT.agreed} agreed / ${TOT.dropped} dropped of ${TOT.labelled} labelled (${TOT.candidates} candidates so far)`)
    }))
    const agreed = AGREED[f.fam].length
    log(`label ${f.fam}: ${agreed}/${r.count} agreed, ${DROPPED[f.fam].length} dropped`)
    return { fam: f.fam, task: f.task, count: r.count, shards: shards.length, agreed, dropped: DROPPED[f.fam].length }
  })
const perFamily = fams.map((x, i) => x || { fam: FAMILIES[i].fam, task: FAMILIES[i].task, count: 0, shards: 0, agreed: 0, dropped: 0, died: true })
log(`labelling done: ${TOT.candidates} candidates, ${TOT.agreed} agreed, ${TOT.dropped} dropped (${TOT.labelled ? Math.round(100 * TOT.agreed / TOT.labelled) : 0}% agreement); target ${MIN_ITEMS} clean items ${TOT.agreed >= MIN_ITEMS ? 'met' : 'NOT met (informational)'}`)
Object.keys(AGREED).forEach(k => AGREED[k].sort((p, q) => p[0] - q[0]))
Object.keys(DROPPED).forEach(k => DROPPED[k].sort((p, q) => p[0] - q[0]))

const verify = await verifyP
const baseline = await baselineP
const options = await optionsP
const verified = verify?.verified === true
const commits = []
let assembled = null
let install = null
if (!verified) log(`BLOCKED_BY_VERIFICATION: assemble and install skipped; ${verify ? verify.reasons.join(' | ') : 'the verifier died twice'}. The agreed/dropped lists ride this run's return value and the per-labeller files under ${LAYA_REL}/labels/`)
else {
  const FAMTASK = Object.fromEntries(FAMILIES.map(f => [f.fam, f.task]))
  assembled = await run(`${COMMON}

ROLE: DATASET ASSEMBLER (Sonnet; label laya-assemble). Inputs: the candidates files ${LAYA}/candidates/<family>.jsonl (family -> task ${JSON.stringify(FAMTASK)}); the composer option set ${JSON.stringify(options?.options ?? null)}; the two-labeller outcome computed by the workflow script, per family as [n, answer] for AGREED and [n, answer_A, answer_B] for DROPPED, where n is the id number (id = '<family>-<n>'): AGREED ${JSON.stringify(AGREED)} DROPPED ${JSON.stringify(DROPPED)}. Fine-tune format documented by the package (from ${LAYA}/PACKAGE_VERIFICATION.md): ${JSON.stringify(verify.finetune_format)} - use it verbatim when documented, else one JSON object per line {task, passage, question, options, answer, provenance}; either way keep id and provenance on every row. Write with ONE python3 script in ${SCRATCH}/laya-assemble/ (never in the repo): ${LAYA}/dataset/entity_match.jsonl, composer_intent.jsonl, holding_relevance.jsonl (the agreed items joined to their candidate lines by id, answer from AGREED; an exact duplicate across families - same task, passage and question - keeps the first id and is listed in DATASET.md as a cross-family duplicate), ${LAYA}/dataset/DROPPED.jsonl ({id, task, a, b}), and ${LAYA}/DATASET.md: counts per task, class balance per task, the majority-class rate per task, provenance summary by source family (files and item counts), the two-labeller protocol (two Opus labellers per shard of ${MAX_SHARD}, identical prompts apart from the role name, blind to each other; agreed = same answer and neither skip; disagreements dropped, no third labeller, no retry on disagreement), the base sha ${SHA}, and the agreement rate per family. ${COMMIT(LAYA_REL, 'docs(r15): laya groundwork dataset, baseline and package verification (scope change 2)')} Return counts {entity_match, composer_intent, holding_relevance, dropped}, majority_rates {per task}, commit, pushed.`, { label: 'laya-assemble', phase: 'Assemble', model: 'sonnet', effort: 'medium', schema: ASSEMBLE })
  log(`assemble: ${assembled ? JSON.stringify(assembled.counts) + '; majority ' + JSON.stringify(assembled.majority_rates) + '; commit ' + (assembled.commit || 'none').slice(0, 7) + ', pushed ' + assembled.pushed : 'died - dataset not written, install skipped'}`)
  if (assembled?.commit) commits.push(assembled.commit)

  if (assembled) {
    install = await run(`${COMMON}

ROLE: INSTALLER (Sonnet; label laya-install). Verified package facts: ${JSON.stringify({ install_command: verify.install_command, versions: verify.versions, python_requires: verify.python_requires, macos_requires: verify.macos_requires, api_summary: verify.api_summary })}. (1) Create the scratch venv: uv venv ${VENV} --python ~/.local/bin/python3.12 (fallback /opt/homebrew/bin/python3.13 if 3.12 fails python_requires or the install); NEVER ${REPO}/sidecar/.venv or any venv in the repo; a venv already there from a previous attempt of your role is reused. (2) Install laya-mlx with the verified install command (pinned version) into that venv only (uv pip install --python ${VENV}/bin/python ...), detached with a log, polled; export HF_HOME=${HF} for anything that fetches weights. (3) Smoke: a script in ${SCRATCH}/laya-smoke/ (never in the repo) runs at most 20 items from ${LAYA}/dataset/*.jsonl covering all three task types (noul for entity_match and holding_relevance, choice over the fixed options for composer_intent), prints per-item latency and the answer, and exits (so the model is unloaded); run it under /usr/bin/time -l, detached, polled. Record in ${LAYA}/INSTALL.md: the python and package versions (pip freeze of the venv), weights source and size, wall time, peak RSS (maximum resident set size from time -l, in MB), per-item latency and p50, the per-item outputs, and the exact commands. On ANY failure: write NOT FEASIBLE with the exact error text in INSTALL.md, stop, feasible false. (4) ${COMMIT(`${LAYA_REL}/INSTALL.md`, 'docs(r15): laya-mlx scratch install and smoke (scope change 2)')} Return feasible, versions, peak_rss_mb, smoke_items, p50_ms, error, commit, pushed.`, { label: 'laya-install', phase: 'Install', model: 'sonnet', effort: 'high', schema: INSTALL })
    log(`install: ${install ? (install.feasible ? `feasible; peak RSS ${install.peak_rss_mb} MB, ${install.smoke_items} smoke items, p50 ${install.p50_ms} ms` : 'NOT FEASIBLE: ' + install.error) + '; commit ' + ((install.commit || 'none').slice(0, 7)) + ', pushed ' + install.pushed : 'died'}`)
    if (install?.commit) commits.push(install.commit)
  }
}

// Runs last so its commit never races the assembler's or the installer's on the main worktree.
const draft = await run(`${COMMON}

ROLE: BACKLOG DRAFTER (Sonnet; label laya-backlog-draft). Write ${LAYA}/BACKLOG_ENTRY.md; do NOT insert it into ${BACKLOG_REL} (the measure run does, for the Stage E judge panel, which ranks it and builds nothing). Title: 'Filing watcher: System 1 triage in front of the BYOK model'. Sections: (1) design sketch: a local triage pass over every NSE/BSE corporate announcement, pledge change, bulk or block deal and rating action, judged against the user's holdings, watchlist and written thesis; it wakes the BYOK model only for what matters, and every surfaced item carries a receipt linking to the filing page. (2) Ingestion today: grep ${REPO}/sidecar/ for NSE/BSE corporate-announcement ingestion (announcements, corporate actions, pledge, bulk/block deal, rating feeds) and say with file:line whether it exists or is itself a build. (3) Fine-tune plan: distil labels from a strong model over real announcements, tune on a GPU box, fit a calibration temperature on held-out data, ship the checkpoint in the sidecar behind an opt-in setting with the existing path as fallback, and never as sole authority on anything the user sees. (4) Licence: the Apache-2.0 notice as verified (${JSON.stringify({ license: verify?.license ?? null, repo: verify?.repo ?? null, verified })}; the text is in ${LAYA}/PACKAGE_VERIFICATION.md). (5) Windows route: laya-mlx is Apple-only; the PyTorch 'laya' package or an ONNX export there. (6) Baseline: the numbers from ${LAYA}/BASELINE.md (${JSON.stringify(baseline ? { totals: baseline.totals, decisions: baseline.decisions } : null)}), each with its pointer. (7) Groundwork so far: dataset counts (${JSON.stringify(assembled?.counts ?? null)}), install smoke (${JSON.stringify(install ? { feasible: install.feasible, peak_rss_mb: install.peak_rss_mb, p50_ms: install.p50_ms, error: install.error } : null)}). End with the line 'Verdict: pending MEASURE'. ${COMMIT(LAYA_REL, 'docs(r15): laya filing-watcher backlog draft (scope change 2)')} (the whole r15/laya/ directory, so evidence the assembler did not commit lands too). Return file (repo-relative), ingestion_exists, summary <=80 words, commit, pushed.`, { label: 'laya-backlog-draft', phase: 'Backlog draft', model: 'sonnet', effort: 'high', schema: DRAFT })
log(`backlog draft: ${draft ? `${draft.file}; ingestion exists ${draft.ingestion_exists}; commit ${(draft.commit || 'none').slice(0, 7)}, pushed ${draft.pushed}` : 'died'}`)
if (draft?.commit) commits.push(draft.commit)

return {
  mode: 'prep',
  sha: SHA,
  verified,
  ...(verified ? {} : { status: 'BLOCKED_BY_VERIFICATION', reasons: verify ? verify.reasons : ['verifier died twice'], labels: { agreed: AGREED, dropped: DROPPED } }),
  baseline: baseline ? baseline.totals : null,
  options: options ? options.options : null,
  candidates: TOT.candidates,
  per_family: perFamily,
  agreed: TOT.agreed,
  dropped: TOT.dropped,
  dataset: assembled ? assembled.counts : null,
  feasible: install ? install.feasible : null,
  commits,
}
