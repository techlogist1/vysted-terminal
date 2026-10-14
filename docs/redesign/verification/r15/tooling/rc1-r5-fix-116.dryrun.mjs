// Stubbed dry run of rc1-r5-fix-116.js: no agents spawn. Loads the file the same way rc1-gate.dryrun.mjs
// does (meta literal first, body wrapped as an async function), runs it once with a stub agent() that
// returns schema-shaped placeholders, and checks it invokes exactly three agent() calls in order
// Write -> Integrate -> Verify with the expected labels and models. Usage: node rc1-r5-fix-116.dryrun.mjs
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const SCRIPT = path.join(HERE, 'rc1-r5-fix-116.js')

const load = file => {
  const src = fs.readFileSync(file, 'utf8')
  const lines = src.split('\n')
  if (!lines[0].startsWith('export const meta = {')) throw new Error('meta literal must come first')
  const body = lines.slice(lines.indexOf('}') + 1).join('\n')
  return new Function('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'return (async()=>{' + body + '})()')
}
const shape = s => (!s ? 'x' : s.enum ? s.enum[0] : s.type === 'object' ? Object.fromEntries(Object.entries(s.properties || {}).map(([k, v]) => [k, shape(v)])) : s.type === 'array' ? [] : s.type === 'number' ? 0 : s.type === 'boolean' ? false : 'x')

async function run() {
  const calls = []
  const agent = async (prompt, opts) => {
    calls.push({ label: opts.label, phase: opts.phase, model: opts.model })
    const o = shape(opts.schema)
    if ('status' in o) o.status = opts.label.endsWith('-writer') ? 'done' : 'green'
    if ('certified' in o) o.certified = true
    if ('branch' in o) o.branch = 'worktree-agent-' + opts.label
    if ('commit' in o) o.commit = 'a'.repeat(40)
    if ('int_head' in o) o.int_head = 'b'.repeat(40)
    if ('int_branch' in o) o.int_branch = 'worktree-agent-' + opts.label
    return o
  }
  const fn = load(SCRIPT)
  const result = await fn(agent, () => {}, () => {}, () => {}, () => {}, {}, {})
  return { calls, result }
}

let failed = 0
const check = (ok, msg) => { console.log((ok ? 'PASS ' : 'FAIL ') + msg); if (!ok) failed++ }

const { calls, result } = await run()
check(calls.length === 3, 'exactly 3 agent() calls (' + calls.length + ')')
check(calls.map(c => c.phase).join(',') === 'Write,Integrate,Verify', 'phases in order Write -> Integrate -> Verify: ' + calls.map(c => c.phase).join(' > '))
check(calls.map(c => c.label).join(',') === 'rc1-r5-fix-116-writer,rc1-r5-fix-116-int,rc1-r5-fix-116-verifier', 'labels: ' + calls.map(c => c.label).join(', '))
check(calls.map(c => c.model).join(',') === 'opus,sonnet,opus', 'models: ' + calls.map(c => c.model).join(', '))
check(!!result && !!result.writer && !!result.integrator && !!result.verifier, 'result carries writer/integrator/verifier')
console.log(failed ? failed + ' check(s) FAILED' : 'all checks passed')
process.exit(failed ? 1 : 0)
