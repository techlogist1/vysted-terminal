export const meta = {
  name: 'r15-fanout',
  description: 'R15 generic templated fan-out: each item runs through the staged prompts as an independent pipeline, with retries',
  phases: [{ title: 'Stage 1' }, { title: 'Stage 2' }, { title: 'Stage 3' }],
}
// args = { tag, common, stages: [{label, model, effort?, prompt}], items: [{id, skip?: [stageIdx], ...vars}] }
// {{var}} in a stage prompt is replaced from the item. A stage listed in item.skip is not run.
// item.model overrides the stage model (lets one workflow mix Fable and Opus).
// R15 session-2 pacing law (operator, 23 Sep): the limit lives in the tool, not in the lead's memory.
// A launch never exceeds the per-workflow cap (CPUs-2 = 6 on this Mac; machine-wide ceiling 8 agents at
// once, so a second concurrent workflow may hold at most 2), every stage names its model AND effort
// explicitly (agents never inherit the session's), and Haiku / the fast tier are never used.
const MAX_ITEMS = 32
const BANNED = /haiku|fast/i
if (!args || !Array.isArray(args.items) || !Array.isArray(args.stages)) throw new Error('r15-fanout: REFUSED - args.items and args.stages are required')
if (args.items.length > MAX_ITEMS) throw new Error(`r15-fanout: REFUSED - ${args.items.length} items exceed the per-workflow cap of ${MAX_ITEMS}; split into waves`)
for (const st of args.stages) {
  if (!st.model || !st.effort) throw new Error(`r15-fanout: REFUSED - stage "${st.label}" must name model and effort explicitly`)
  if (BANNED.test(st.model)) throw new Error(`r15-fanout: REFUSED - stage "${st.label}" model "${st.model}" is banned (never Haiku, never the fast tier)`)
}
for (const it of args.items) if (it.model && BANNED.test(it.model)) throw new Error(`r15-fanout: REFUSED - item "${it.id}" model "${it.model}" is banned`)
const RESULT = {
  type: 'object',
  properties: {
    model: { type: 'string' },
    output_file: { type: 'string' },
    summary: { type: 'string' },
    count: { type: 'number' },
    top: { type: 'array', items: { type: 'string' } },
  },
  required: ['model', 'summary'],
}
const fill = (t, item) => t.replace(/\{\{(\w+)\}\}/g, (_, k) => (item[k] === undefined ? '' : String(item[k])))
const RETRY = '\nNOTE: a previous attempt at this exact task died mid-way (connection loss). Check your output file(s) for partial work FIRST and continue from it instead of starting over.'
const run = async (prompt, opts) => {
  for (let i = 0; i < 3; i++) {
    try {
      const r = await agent(i ? prompt + RETRY : prompt, opts)
      if (r) return r
    } catch { log(`${opts.label}: attempt ${i + 1} threw`) }
  }
  log(`${opts.label}: FAILED after 3 attempts`)
  return null
}
const stageFns = args.stages.map((st, si) => async (prev, item) => {
  if ((item.skip || []).includes(si)) return prev || { model: 'skipped', summary: 'stage skipped (already done)' }
  if (si > 0 && !prev) return null
  return run(args.common + '\n' + fill(st.prompt, item), {
    label: `${args.tag}:${st.label}:${item.id}`, phase: `Stage ${si + 1}`, schema: RESULT,
    model: item.model || st.model, effort: st.effort,
  })
})
const out = await pipeline(args.items, ...stageFns)
const failed = args.items.filter((it, i) => !out[i]).map(it => it.id)
if (failed.length) log(`${args.tag}: items with no final result: ${failed.join(', ')}`)
return { tag: args.tag, done: args.items.filter((it, i) => out[i]).map(it => it.id), failed, results: out.filter(Boolean).map(r => ({ model: r.model, summary: r.summary, top: r.top })) }
