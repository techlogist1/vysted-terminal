export const meta = {
  name: 'r15-fanout',
  description: 'R15 generic templated fan-out: each item runs through the staged prompts as an independent pipeline, with retries',
  phases: [{ title: 'Stage 1' }, { title: 'Stage 2' }, { title: 'Stage 3' }],
}
// args = { tag, common, stages: [{label, model, effort?, prompt}], items: [{id, skip?: [stageIdx], ...vars}] }
// {{var}} in a stage prompt is replaced from the item. A stage listed in item.skip is not run.
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
    model: st.model, effort: st.effort,
  })
})
const out = await pipeline(args.items, ...stageFns)
const failed = args.items.filter((it, i) => !out[i]).map(it => it.id)
if (failed.length) log(`${args.tag}: items with no final result: ${failed.join(', ')}`)
return { tag: args.tag, done: args.items.filter((it, i) => out[i]).map(it => it.id), failed, results: out.filter(Boolean).map(r => ({ model: r.model, summary: r.summary, top: r.top })) }
