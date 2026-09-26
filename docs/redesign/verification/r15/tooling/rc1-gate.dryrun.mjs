// Stubbed dry run of rc1-gate.js: no agents spawn. agent() is replaced by a stub that keys each call exactly as the Claude Code
// workflow harness does (sha256(prevKey \0 prompt \0 canon(opts)), a chain over invocation sequence) and returns schema-shaped
// placeholders after a timing-mode delay. Usage: node rc1-gate.dryrun.mjs [script] [--control <older script>]
import fs from 'fs'
import crypto from 'crypto'
import path from 'path'
import { fileURLToPath } from 'url'

const argv = process.argv.slice(2)
const ci = argv.indexOf('--control')
const control = ci >= 0 ? argv.splice(ci, 2)[1] : null
const SCRIPT = argv[0] || path.join(path.dirname(fileURLToPath(import.meta.url)), 'rc1-gate.js')
const LAUNCH = { sha: '4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2', round: 3, max_fix_rounds: 2, skip_gui: true, note: 'dry run' }

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
const IDS = Array.from({ length: 391 }, (_, i) => 'R15-TEST-' + String(i).padStart(3, '0'))
const SETS = []
for (let i = 0, s = 0; i < IDS.length; s++) { const n = 1 + (s % 12); SETS.push({ batch: 'batch-' + (2 + (s % 17)), set: 'batch-' + (2 + (s % 17)) + '/W' + s, entries: IDS.slice(i, i + n) }); i += n }
const FIX = 'rc1-drive-research-briefs:1'
const fill = (label, prompt, schema) => {
  const o = shape(schema)
  if ('model' in o) o.model = 'stub'
  if (label === 'rc1-preflight') Object.assign(o, { status: 'ready', sha: LAUNCH.sha, stack_ok: true, status_counts: { fixed: 391, open: 205 }, needs_gui: ['R15-UI-009'] })
  if (label === 'rc1-battery-index') Object.assign(o, { sets: SETS, fixed_total: IDS.length })
  if (label === 'rc1-drive-research-briefs') o.findings = [{ key: FIX, kind: 'regression', severity: 'medium', title: 't', evidence_file: 'e' }]
  if (/^rc1-battery-\d+$/.test(label)) o.results = [...new Set(prompt.match(/R15-TEST-\d{3}/g) || [])].map(id => ({ set: 's', id, verdict: 'holds', evidence: 'e' }))
  if (/^rc1-fix-r\d+-triage$/.test(label)) o.writers = [{ name: 'W1-cite', model: 'sonnet', keys: [FIX], files: ['a.py'], brief: 'b' }]
  if (/^rc1-fix-r\d+-W/.test(label)) Object.assign(o, { pushed: true, items: [{ key: FIX, outcome: 'fixed', note: 'n' }] })
  if (/^rc1-fix-r\d+-int$/.test(label)) Object.assign(o, { pushed: true, chain: 'pass', head_sha: 'b'.repeat(40) })
  if (/^rc1-fix-r\d+-recheck$/.test(label)) o.fixed = [FIX]
  if (label === 'rc1-verifier') o.verdict = 'FAIL'
  return o
}
// timing modes: 'asc' later calls finish later, 'desc' later calls finish first, 'mix' a fixed pseudo-random sequence (seeded, not Math.random)
const delayOf = (mode, n) => (mode === 'asc' ? n : mode === 'desc' ? Math.max(1, 90 - n) : ((n * 7919) % 37) + 1)

async function run(file, launch, mode, cache) {
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
    const out = (call.out = fill(opts.label, prompt, opts.schema))
    await new Promise(r => setTimeout(r, delayOf(mode, calls.length)))
    return out
  }
  const parallel = thunks => Promise.all(thunks.map(t => Promise.resolve().then(t).catch(() => null)))
  const pipeline = (items, ...stages) => Promise.all(items.map((it, i) => stages.reduce((p, st) => p.then(v => st(v, it, i)), Promise.resolve(it)).catch(() => null)))
  const result = await fn(launch, agent, parallel, pipeline, () => {}, m => logs.push(m), { total: null, spent: () => 0, remaining: () => Infinity }, () => null)
  return { calls, logs, result }
}

let failed = 0
const check = (ok, msg) => { console.log((ok ? 'PASS ' : 'FAIL ') + msg); if (!ok) failed++ }
const seq = r => r.calls.map(c => c.label + '\n' + c.prompt + '\n' + c.key).join('\n\u0001\n')

async function main() {
  for (const bad of [undefined, 0, '0', 'abc', 2.5, true]) {
    let threw = false
    try { await run(SCRIPT, { ...LAUNCH, round: bad }, 'asc') } catch (e) { threw = /args\.round is required/.test(String(e)) }
    check(threw, 'refuses to run with round=' + JSON.stringify(bad))
  }
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
  check(R2.calls.every(c => c.hit), 'resume with max_fix_rounds 2 -> 3 (the round-2 change) replays ' + R2.calls.filter(c => c.hit).length + '/' + R2.calls.length)
  check(A.calls.every(c => ['opus', 'sonnet'].includes(c.model) && c.effort), 'every call names model (opus|sonnet) and effort')
  const bad = A.calls.filter(c => !c.prompt.includes('/r15/rc1/round-3') || /rc1-(cand|seed-data|pack|gui-home|data-)|vr15-rc1\/(?!round-3)/.test(c.prompt))
  check(!bad.length, 'every prompt is scoped to r15/rc1/round-3 and no unscoped scratch or screenshot path remains' + (bad.length ? ': ' + bad.map(c => c.label).join(', ') : ''))
  const legacy = A.calls.flatMap(c => (c.prompt.match(/r15\/rc1\/(?!round-3)[^ ,;)]*/g) || []).map(m => c.label + ' ' + m))
  console.log('INFO r15/rc1 mentions outside round-3 (prohibitions and the rubric\'s concurrence file only): ' + [...new Set(legacy.map(x => x.split(' ')[1]))].join(' | '))
  const shards = A.calls.filter(c => /^rc1-battery-\d+$/.test(c.label))
  const ids = shards.flatMap(c => [...new Set(c.prompt.match(/R15-TEST-\d{3}/g))])
  const sizes = shards.map(c => new Set(c.prompt.match(/R15-TEST-\d{3}/g)).size)
  check(ids.length === IDS.length && new Set(ids).size === IDS.length, 'battery: ' + shards.length + ' shards cover all ' + IDS.length + ' fixed ids exactly once (sizes ' + Math.min(...sizes) + '-' + Math.max(...sizes) + ')')
  const count = {}
  for (const c of A.calls) { const k = c.label.replace(/-\d+$/, '-<k>').replace(/^rc1-drive-.*/, 'rc1-drive-<group>').replace(/^rc1-fix-r(\d+)-W.*/, 'rc1-fix-r$1-<writer>'); count[k] = (count[k] || 0) + 1 }
  console.log('INFO would spawn ' + A.calls.length + ' agents: ' + Object.entries(count).map(([k, v]) => k + ' x' + v).join(', '))
  console.log('INFO invocation sequence: ' + A.calls.map(c => c.label.replace(/^rc1-/, '')).join(' > '))
  if (control) {
    const L = { ...LAUNCH }
    delete L.round
    for (const mode of ['asc', 'desc', 'mix']) {
      const O = await run(control, L, mode)
      const OR = await run(control, L, mode, new Map(O.calls.map(c => [c.key, c.out])))
      const miss = OR.calls.findIndex(c => !c.hit)
      console.log('CONTROL ' + control + ' (' + mode + '-timed original): resume replays ' + OR.calls.filter(c => c.hit).length + '/' + OR.calls.length + (miss >= 0 ? '; first miss at call ' + (miss + 1) + ' ' + OR.calls[miss].label + ' (original call ' + (miss + 1) + ' was ' + O.calls[miss].label + ')' : ''))
    }
  }
  console.log(failed ? failed + ' check(s) FAILED' : 'all checks passed')
  process.exit(failed ? 1 : 0)
}
main().catch(e => { console.error(e); process.exit(2) })
