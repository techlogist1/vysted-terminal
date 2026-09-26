// Stubbed dry run of rc1-gate.js: no agents spawn. agent() is replaced by a stub that keys each call exactly as the Claude Code
// workflow harness does (sha256(prevKey \0 prompt \0 canon(opts)), a chain over invocation sequence) and returns schema-shaped
// placeholders after a timing-mode delay. The battery index is round 3's real INDEX.json (392 ids, 75 sets). Usage:
// node rc1-gate.dryrun.mjs [script] [--control <older script>]  (the control replays round 3's placeholder index return)
import fs from 'fs'
import crypto from 'crypto'
import path from 'path'
import { fileURLToPath } from 'url'

const argv = process.argv.slice(2)
const ci = argv.indexOf('--control')
const control = ci >= 0 ? argv.splice(ci, 2)[1] : null
const HERE = path.dirname(fileURLToPath(import.meta.url))
const SCRIPT = argv[0] || path.join(HERE, 'rc1-gate.js')
const LAUNCH = { sha: '4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2', round: 4, max_fix_rounds: 2, skip_gui: true, drive_limit: 3, batt_limit: 4, batt_shards: 25, note: 'dry run' }
const RND = '/r15/rc1/round-' + LAUNCH.round

const load = file => {
  const src = fs.readFileSync(file, 'utf8')
  const lines = src.split('\n')
  if (!lines[0].startsWith('export const meta = {')) throw new Error('meta literal must come first')
  const body = lines.slice(lines.indexOf('}') + 1).join('\n')
  if (/Date\.now\(|Math\.random\(|new Date\(\)/.test(body)) throw new Error('non-deterministic builtin in the script body')
  return new Function('args', 'agent', 'parallel', 'pipeline', 'phase', 'log', 'budget', 'workflow', 'return (async()=>{' + body + '})()')
}
const canon = o => {
  const g = p => (Array.isArray(p) ? p.map(g) : p && typeof p === 'object' ? Object.fromEntries(Object.keys(p).sort().map(k => [k, g(p[k])])) : p)
  const r = {}
  for (const k of ['schema', 'model', 'effort', 'isolation', 'agentType', 'disallowedTools', 'bashCommandClamp']) if (o && o[k] !== undefined) r[k] = o[k]
  return JSON.stringify(g(r))
}
const shape = s => (!s ? 'x' : s.enum ? s.enum[0] : s.type === 'object' ? Object.fromEntries(Object.entries(s.properties || {}).map(([k, v]) => [k, shape(v)])) : s.type === 'array' ? [] : s.type === 'number' ? 0 : s.type === 'boolean' ? false : 'x')
const R3 = JSON.parse(fs.readFileSync(path.join(HERE, '../rc1/round-3/battery/INDEX.json'), 'utf8'))
const SETS = R3.sets.map(x => ({ batch: x.batch, set: x.set, entries: x.entries }))
const IDS = SETS.flatMap(x => x.entries)
// What round 3's indexer actually returned (journal wf_3bab62fa-c4d, row 12).
const PLACEHOLDER = { sets: [{ batch: 'see INDEX.json', set: '75 sets total (batch-plan writer sets + unplanned-N groups)', entries: ['full per-set id lists are in INDEX.json/INDEX.md, too large to inline here'] }], fixed_total: 392, unplanned_fixed: 28 }
const idsIn = prompt => IDS.filter(id => prompt.includes('"' + id + '"'))
const FIX = 'rc1-drive-research-briefs:1'
const SURF = 'docs/redesign/verification/r15/surface/'
// opt.index: 'ok' | 'placeholder' (first ask placeholder, redo ok) | 'placeholder-both' | 'short' (last set dropped, twice);
// opt.narrative: a drive group that saves only a narrative .md; opt.hosted: the scenario lane's hosted provider.
const fill = (label, prompt, schema, opt) => {
  const o = shape(schema)
  if ('model' in o) o.model = 'stub'
  if (label === 'rc1-preflight') Object.assign(o, { status: 'ready', sha: LAUNCH.sha, stack_ok: true, status_counts: { fixed: IDS.length, open: 205 }, needs_gui: ['R15-UI-009'] })
  if (label === 'rc1-battery-index' || label === 'rc1-battery-index-redo') {
    const redo = label.endsWith('-redo')
    const bad = opt.index === 'placeholder-both' || (opt.index === 'placeholder' && !redo)
    Object.assign(o, bad ? PLACEHOLDER : opt.index === 'short' ? { sets: SETS.slice(0, -1), fixed_total: IDS.length } : { sets: SETS, fixed_total: IDS.length })
  }
  const g = (label.match(/^rc1-drive-(.+)$/) || [])[1]
  if (g) o.evidence_files = g === opt.narrative ? [SURF + g + '/rc1/round-' + LAUNCH.round + '/RC1-NARRATIVE.md', 'drives/' + g + '.md'] : [SURF + g + '/rc1/round-' + LAUNCH.round + '/01-step.json', 'drives/' + g + '.md']
  if (label === 'rc1-scenarios') Object.assign(o, { hosted: { provider: opt.hosted || 'openai', model: 'gpt-4o-mini', reason: 'r' }, properties: ['read-back', 'skepticism', 'self-consistency'].map(property => ({ property, hosted_triples: 4, hosted_complete: 4, hosted_pass3: 4, local_ran: 4, local_pass: 2 })) })
  if (label === 'rc1-drive-research-briefs') o.findings = [{ key: FIX, kind: 'regression', severity: 'medium', title: 't', evidence_file: 'e' }]
  if (/^rc1-battery-\d+$/.test(label)) o.results = idsIn(prompt).map(id => ({ set: 's', id, verdict: 'holds', evidence: 'e' }))
  if (/^rc1-fix-r\d+-triage$/.test(label)) o.writers = [{ name: 'W1-cite', model: 'sonnet', keys: [FIX], files: ['a.py'], brief: 'b' }]
  if (/^rc1-fix-r\d+-W/.test(label)) Object.assign(o, { pushed: true, items: [{ key: FIX, outcome: 'fixed', note: 'n' }] })
  if (/^rc1-fix-r\d+-int$/.test(label)) Object.assign(o, { pushed: true, chain: 'pass', head_sha: 'b'.repeat(40) })
  if (/^rc1-fix-r\d+-recheck$/.test(label)) o.fixed = [FIX]
  if (label === 'rc1-verifier') o.verdict = 'FAIL'
  return o
}
// timing modes: 'asc' later calls finish later, 'desc' later calls finish first, 'mix' a fixed pseudo-random sequence (seeded, not Math.random)
const delayOf = (mode, n) => (mode === 'asc' ? n : mode === 'desc' ? Math.max(1, 90 - n) : ((n * 7919) % 37) + 1)

async function run(file, launch, mode, cache, opt = { index: 'ok' }) {
  const fn = load(file)
  let prev = ''
  let y = false
  const calls = []
  const logs = []
  const agent = async (prompt, opts) => {
    const key = 'v2:' + crypto.createHash('sha256').update(prev).update('\0').update(prompt).update('\0').update(canon(opts)).digest('hex')
    prev = key
    const call = { label: opts.label, model: opts.model, effort: opts.effort, prompt, key, hit: false }
    calls.push(call)
    if (cache && !y && cache.has(key)) { call.hit = true; return cache.get(key) }
    y = true
    const out = (call.out = fill(opts.label, prompt, opts.schema, opt))
    await new Promise(r => setTimeout(r, delayOf(mode, calls.length)))
    return out
  }
  const parallel = thunks => Promise.all(thunks.map(t => Promise.resolve().then(t).catch(() => null)))
  const pipeline = (items, ...stages) => Promise.all(items.map((it, i) => stages.reduce((p, st) => p.then(v => st(v, it, i)), Promise.resolve(it)).catch(() => null)))
  let result
  try { result = await fn(launch, agent, parallel, pipeline, () => {}, m => logs.push(m), { total: null, spent: () => 0, remaining: () => Infinity }, () => null) } catch (e) { e.calls = [...calls]; throw e }
  return { calls, logs, result }
}

let failed = 0
const check = (ok, msg) => { console.log((ok ? 'PASS ' : 'FAIL ') + msg); if (!ok) failed++ }
const seq = r => r.calls.map(c => c.label + '\n' + c.prompt + '\n' + c.key).join('\n\u0001\n')

async function main() {
  const throws = async (launch, re, opt) => { try { await run(SCRIPT, launch, 'asc', null, opt) } catch (e) { return re.test(String(e)) ? String(e) : 'WRONG ' + e } return '' }
  for (const bad of [undefined, 0, '0', 'abc', 2.5, true]) check(!!await throws({ ...LAUNCH, round: bad }, /args\.round is required/), 'refuses to run with round=' + JSON.stringify(bad))
  for (const bad of [0, 65, 'abc', 2.5]) check(/^Error: args\.batt_shards/.test(await throws({ ...LAUNCH, batt_shards: bad }, /args\.batt_shards must be an integer 1\.\.64/)), 'refuses to run with batt_shards=' + JSON.stringify(bad))
  const A = await run(SCRIPT, LAUNCH, 'asc')
  const B = await run(SCRIPT, LAUNCH, 'desc')
  const C = await run(SCRIPT, LAUNCH, 'mix')
  check(seq(A) === seq(B) && seq(A) === seq(C), 'labels, prompts and keys byte-identical across 3 completion sequences (' + A.calls.length + ' calls each): no prompt or position depends on call sequence')
  const cache = new Map(A.calls.map(c => [c.key, c.out]))
  for (const mode of ['asc', 'desc', 'mix']) {
    const R = await run(SCRIPT, LAUNCH, mode, cache)
    const miss = R.calls.filter(c => !c.hit)
    check(miss.length === 0 && seq(R) === seq(A), 'resume (' + mode + '-timed original, instant cached results) replays ' + (R.calls.length - miss.length) + '/' + R.calls.length + ' calls' + (miss.length ? '; first miss ' + miss[0].label : ''))
  }
  const R2 = await run(SCRIPT, { ...LAUNCH, max_fix_rounds: 3 }, 'desc', cache)
  check(R2.calls.every(c => c.hit), 'resume with max_fix_rounds 2 -> 3 replays ' + R2.calls.filter(c => c.hit).length + '/' + R2.calls.length)
  check(A.calls.every(c => ['opus', 'sonnet'].includes(c.model) && c.effort), 'every call names model (opus|sonnet) and effort')
  const bad = A.calls.filter(c => !c.prompt.includes(RND) || new RegExp('rc1-(cand|seed-data|pack|gui-home|data-)|vr15-rc1/(?!round-' + LAUNCH.round + ')').test(c.prompt))
  check(!bad.length, 'every prompt is scoped to ' + RND.slice(1) + ' and no unscoped scratch or screenshot path remains' + (bad.length ? ': ' + bad.map(c => c.label).join(', ') : ''))
  const legacy = A.calls.flatMap(c => (c.prompt.match(new RegExp('r15/rc1/(?!round-' + LAUNCH.round + ')[^ ,;)]*', 'g')) || []).map(m => c.label + ' ' + m))
  console.log('INFO r15/rc1 mentions outside round-' + LAUNCH.round + ' (prohibitions and the rubric\'s concurrence file only): ' + [...new Set(legacy.map(x => x.split(' ')[1]))].join(' | '))

  // Battery: coverage of round 3's real index, the batt_shards override, the 24-id cap and the placeholder return.
  const shardCalls = r => r.calls.filter(c => /^rc1-battery-\d+$/.test(c.label))
  const cover = (r, n, what) => {
    const sh = shardCalls(r)
    const ids = sh.flatMap(c => idsIn(c.prompt))
    const sizes = sh.map(c => idsIn(c.prompt).length)
    check(sh.length === n && ids.length === IDS.length && new Set(ids).size === IDS.length && Math.max(...sizes) <= 24, what + ': ' + sh.length + ' shards cover all ' + IDS.length + ' fixed ids of the ' + SETS.length + '-set round-3 index exactly once (sizes ' + Math.min(...sizes) + '-' + Math.max(...sizes) + ', cap 24)')
  }
  cover(A, 25, 'batt_shards 25')
  const noArg = { ...LAUNCH }
  delete noArg.batt_shards
  cover(await run(SCRIPT, noArg, 'asc'), 25, 'no batt_shards (NB = ceil(preflight fixed 392 / 16))')
  const S30 = await run(SCRIPT, { ...LAUNCH, batt_shards: 30 }, 'asc')
  cover(S30, 30, 'batt_shards 30 overrides the preflight-derived 25')
  const e10 = await throws({ ...LAUNCH, batt_shards: 10 }, /BATTERY PLAN INVALID \(harness\): shard \d+ carries \d+ ids/)
  check(e10.startsWith('Error: BATTERY PLAN INVALID'), 'batt_shards 10 (39+ ids a shard) throws the named cap error: ' + e10.slice(0, 110))
  const P = ['asc', 'desc', 'mix'].map(m => run(SCRIPT, LAUNCH, m, null, { index: 'placeholder' }))
  const [PA, PB, PC] = await Promise.all(P)
  const at = PA.calls.findIndex(c => c.label === 'rc1-battery-index-redo')
  check(at > 0 && seq(PA) === seq(PB) && seq(PA) === seq(PC), 'round 3\'s placeholder index return gets ONE redo, issued at call ' + (at + 1) + ' (' + PA.calls.slice(at - 1, at + 2).map(c => c.label).join(' > ') + ') under all 3 completion sequences, keys identical')
  cover(PA, 25, 'after the redo')
  const pcache = new Map(PA.calls.map(c => [c.key, c.out]))
  const PR = await run(SCRIPT, LAUNCH, 'desc', pcache, { index: 'placeholder' })
  check(PR.calls.every(c => c.hit) && seq(PR) === seq(PA), 'resume of the redo path replays ' + PR.calls.filter(c => c.hit).length + '/' + PR.calls.length)
  for (const index of ['placeholder-both', 'short']) {
    let err = null
    try { await run(SCRIPT, LAUNCH, 'asc', null, { index }) } catch (e) { err = e }
    check(err && /BATTERY PLAN INVALID \(harness\)/.test(String(err)) && err.calls.some(c => c.label === 'rc1-battery-index-redo') && !shardCalls(err).length, 'index ' + index + ' on the ask and the redo: the gate throws by name and issues no shard: ' + String(err).slice(0, 120))
  }
  const cl = A.calls.find(c => c.label === 'rc1-collate')
  check(idsIn(cl.prompt).length === IDS.length && /MISSING_RAW\.json/.test(cl.prompt) && /## Missing ids by shard/.test(cl.prompt) && /## Drive raw output/.test(cl.prompt), 'collator gets the full shard plan (' + idsIn(cl.prompt).length + ' ids) and must always write MISSING_RAW.json, "## Missing ids by shard" and "## Drive raw output"')

  // Drives and scenarios: named harness failures.
  check(A.result.harness.drive_raw_missing.length === 0 && !A.result.blockers.some(b => /^HARNESS/.test(b)), 'baseline: no HARNESS blocker (' + JSON.stringify(A.result.harness) + ')')
  const N = await run(SCRIPT, LAUNCH, 'asc', null, { index: 'ok', narrative: 'onboarding-stranger' })
  check(N.result.harness.drive_raw_missing.join() === 'onboarding-stranger' && N.result.blockers.some(b => b.startsWith('HARNESS drive-raw-missing: onboarding-stranger')), 'a narrative-only drive dir is flagged by name: ' + N.result.blockers.find(b => b.startsWith('HARNESS drive')))
  const H = await run(SCRIPT, LAUNCH, 'asc', null, { index: 'ok', hosted: 'none' })
  check(H.result.blockers.some(b => b.startsWith('HARNESS scenarios-lane: no hosted key')), 'a hosted lane with no key is a named lane failure: ' + H.result.blockers.find(b => b.startsWith('HARNESS scen')))
  const sc = A.calls.find(c => c.label === 'rc1-scenarios').prompt
  check(/pass\^3/.test(sc) && /--tag rc1-round-4-scenarios/.test(sc) && /\$0\.90/.test(sc) && /vy\._key\(p\) is not None/.test(sc), 'scenario role: hosted triples graded pass^3, key resolved via vy.py booleans, tagged spend with a $0.90 stop')
  const dr = A.calls.find(c => c.label === 'rc1-drive-onboarding-stranger').prompt
  check(/RAW OUTPUT IS MANDATORY/.test(dr) && /NOT RUN: <named reason>/.test(dr), 'drive role makes per-row raw files mandatory')

  const count = {}
  for (const c of A.calls) { const k = c.label.replace(/-\d+$/, '-<k>').replace(/^rc1-drive-.*/, 'rc1-drive-<group>').replace(/^rc1-fix-r(\d+)-W.*/, 'rc1-fix-r$1-<writer>'); count[k] = (count[k] || 0) + 1 }
  console.log('INFO would spawn ' + A.calls.length + ' agents: ' + Object.entries(count).map(([k, v]) => k + ' x' + v).join(', '))
  console.log('INFO invocation sequence: ' + A.calls.map(c => c.label.replace(/^rc1-/, '')).join(' > '))
  if (control) {
    const O = await run(control, LAUNCH, 'asc', null, { index: 'placeholder-both' })
    const sh = shardCalls(O)
    console.log('CONTROL ' + control + ' fed round 3\'s placeholder index return: issued ' + sh.length + ' battery shard(s) carrying ' + sh.flatMap(c => idsIn(c.prompt)).length + ' of ' + IDS.length + ' fixed ids, and did not stop')
  }
  console.log(failed ? failed + ' check(s) FAILED' : 'all checks passed')
  process.exit(failed ? 1 : 0)
}
main().catch(e => { console.error(e); process.exit(2) })
