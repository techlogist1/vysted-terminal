# Refutation audit round 4, group surface: rc1-verifier:10 (tie R15-AGENT-043; also rc1-vshard-3:6)

Auditor: Opus, 06:45-07:12 IST. HEAD 33586c21, code tree equals 01015033 (checked: `git diff --name-only
01015033 HEAD | grep -v '^docs/'` printed nothing). Own sidecar :52415 (`sidecar/.venv`, `python -m uvicorn
app:app`, `VYSTED_DATA_DIR` = scratch). Scratch vitest: config root = repo, `test.dir` = scratchpad
`refaudit4-surface/vt`; artifacts copied to `scratchpad/refaudit4-surface/evidence/` (cases.json,
res-*.json, body-*.json, live-p1..p7.jsonl, the *.scratch.test.ts files).

## Tied entry (defines the class)

R15-AGENT-043, fixed (batch-7 certified, 98311dfb). Class: `silent-partial-apply`. fix_shape: "Report
rejected leaves in the label and tool result ... so the model can retry. Test: a 3-criterion call with one
bad leaf returns the drop reason." Its own repro still holds at HEAD (case A below).

## Claim

A flat AND group sent by the agent never runs: `applyFilters` keeps it with `advanced=false`, and
`runScreener` sends a group only for real nesting or `combinator === "or"`.

## Code at HEAD

- `src/store/screener.ts:343-351` applyFilters: `criteria` (the caller's flat list), `group: group ?? null`,
  `advanced: hasNestedGroup(group ?? null)`, `combinator: group && group.combinator === "or" &&
  !hasNestedGroup(group) ? "or" : "and"`. The comment assumes "a flat group from the agent collapses to
  the simple combinator", i.e. that `criteria` already equals the group's leaves.
- `src/store/screener.ts:416-422` runScreener: nested -> `group = pruned`; `combinator === "or"` ->
  `group = { combinator: "or", criteria: [...criteria] }` (the FLAT list, not the group's leaves); else no
  group.
- `src/lib/host-actions.ts:914-925` parseScreenRecipe: `flat = criteria.length ? criteria : group ?
  flattenLeaves(group) : []`, but `count: group ? countLeaves(group) : criteria.length` and `dropped: group
  ? groupDropped : [...]` ("A surviving group is what applies (and is counted)").
- The contract says the group supersedes: `sidecar/services/agent_tools/catalog.py:1529-1531` ("pass a
  `group` tree ... which supersedes the flat list"), `sidecar/services/screener.py:373` ("When ``group`` is
  given it supersedes the flat ``criteria``"). `criteria` is schema-required (catalog.py `["criteria"]`), so
  every group call carries a flat list.

## Reproduction at HEAD (scratch vitest `screener043.scratch.test.ts`, fetch stubbed to capture the
POST /screener/run/stream body; real stores, real host-actions)

| case | agent args | review diff / label | body actually sent |
|---|---|---|---|
| C (verifier) | criteria [market_cap gt 1000], group and[pe_ratio lt 20] | "Wrote 1 screener criterion — running" | criteria [market_cap gt 1000], no group |
| D (flat OR) | criteria [market_cap gt 1e11], group or[pe_ratio lt 15, dividend_yield gt 0.03] | "Wrote 2 screener criteria — running" | criteria [market_cap gt 1e11], group or[market_cap gt 1e11] |
| H | criteria [market_cap gt 1000], group and[pe_ratio lt 20, roe gt "15"] | "Wrote 1 of 2 screener criteria; dropped roe: value must be a number — running" | criteria [market_cap gt 1000], no group |
| I (llama p5 shape) | criteria [dividend_yield gt 0.03, pe_ratio lt 12], group or[market_cap gt 5e10] | "Wrote 1 screener criterion — running" | group or[dividend_yield gt 0.03, pe_ratio lt 12] |
| F (mirrored AND) | same leaves in criteria and group | "Wrote 2 screener criteria" | same leaves: correct |
| G (criteria []) | group and[pe_ratio lt 20, market_cap gt 1000] | "Wrote 2 screener criteria" | same leaves: correct |
| J (llama p4 mirrored OR) | same leaves in criteria and or-group | "Wrote 3 screener criteria" | or[same leaves]: correct |

`save_screen` takes the same path (`savescreen.scratch.test.ts`): saved `{criteria:[market_cap gt 1000],
group:{and:[pe_ratio lt 20]}, combinator:"and"}`; `loadScreen` + `runScreener` sends criteria
[market_cap gt 1000], no group.

So the defect is wider than the verifier wrote: ANY flat group (AND or OR) whose leaves differ from the
flat list is replaced by the flat list; the label, review diff and ack describe the group.

## Live proof of the consequence (own sidecar :52415, same universe, captured bodies)

`curl -X POST :52415/screener/run --data @body-<k>.json`, universe custom
[AAPL,MSFT,JPM,XOM,KO,PFE,VZ,T,CVX,INTC]:

```
C_executed HTTP 200 -> 10 rows (AAPL pe 39.07, MSFT 28.74, PFE 37.72, KO 26.37, ...)   label said pe_ratio < 20
C_intended HTTP 200 ->  4 rows (JPM 14.70, CVX 19.64, VZ 12.26, T 8.38)
D_executed HTTP 200 -> 10 rows
D_intended HTTP 200 ->  5 rows (JPM, CVX, VZ, T, PFE)
```

## Live agent lane (llama3.1:8b, Ollama lock held per call, `inv.py` = vy.py's invoke payload; vy.py itself
refuses ports >= 52400), 7 fresh phrasings, tool calls read from the SSE transcript:

- p1 OR + market cap -> write_screener_filters, flat criteria only (OR flattened to AND).
- p2 ROE/D:E nifty50 run -> flat criteria only.
- p3 "P/E < 25 AND (ROE > 20% OR yield > 2%)" -> flat criteria only.
- p4 "match ANY" -> text-only pseudo call, criteria and an OR group with the SAME leaves (benign shape J).
- p5 "OR group ... also require market cap" -> `screener_run` with criteria [dividend_yield gt 0.03,
  pe_ratio lt 12] and group or[market_cap gt 5e10]: the divergent shape (server path, where the group does
  supersede).
- p6 "write the filters into my panel ... OR group ... and market cap" -> write_screener_filters attempted
  with an OR group, rejected "invalid arguments" (malformed JSON from the model).
- p7 -> flat criteria only.

The local model emits the divergent flat-group shape (p5) and tries it on the host action (p6), but no
valid host write carrying a flat group landed in 7 phrasings. Hosted lanes not exercised (no spend).

## Not the tied entry's class

AGENT-043's fix_shape class is "rejected (malformed) leaves are reported". Here every leaf is well-formed;
the host counts and reports them correctly; the store then runs a different list. Root cause is the
store's flat-group collapse (present since ba2d0eb5, before AGENT-043's fix 98311dfb). No register entry
covers it: R15-UI-007 (fixed) is the preset path with a stale nested tree (hidden-mode-coupling, fixed by
presets passing `group: null`); R15-CODE-DATA-019 is the dead matched_criteria field.

## Verdict: new_defect_confirmed, medium

Severity reasoning: deterministic for every write_screener_filters / save_screen call whose flat group
differs from the flat list; with `run:true` a different screen runs at once and the agent's ack claims the
group was written (rows like AAPL P/E 39 under a "P/E < 20" screen). It stays medium, not high: the panel's
simple builder shows the list that actually runs, so a user reviewing the staged filters can see it, and
the local model reached the shape only on the server-side tool (p5) or with malformed JSON (p6).

- root_cause: `src/store/screener.ts:343-351` (applyFilters keeps the caller's flat `criteria` beside a
  flat group and sets `advanced=false`), so `runScreener` (`:416-422`) serialises the flat list (AND: no
  group; OR: `{or: criteria}`) and never the flat group's leaves; `src/lib/host-actions.ts:916` passes the
  agent's flat list whenever it is non-empty, although the host's own count (`:925`), the tool contract
  and the server treat the group as superseding it.
- fix_shape: in applyFilters, a flat (un-nested) group supplies the criteria: `criteria: group &&
  !hasNestedGroup(group) ? (group.criteria as ScreenerCriterion[]) : criteria` (the combinator already
  follows the group). One line in the shared function, so write_screener_filters, save_screen (the saved
  screen then stores the group's leaves) and any later caller get the contract "group supersedes the flat
  list". Checked in scratch (`fixcheck.scratch.test.ts`, applyFilters patched this way): C -> run body
  criteria [pe_ratio lt 20]; D -> group or[pe_ratio lt 15, dividend_yield gt 0.03]; B -> [pe_ratio lt 20];
  A unchanged ("Wrote 2 of 3 ...; dropped roe", body pe_ratio + debt_to_equity).
- acceptance_test: `src/store/screener.test.ts`: `applyFilters({criteria:[mcap gt 1000], group:{combinator:
  "and", criteria:[pe lt 20]}})` -> `criteria` equals [pe lt 20]; `src/lib/host-actions.test.ts` with fetch
  stubbed: write_screener_filters `{criteria:[{market_cap gt 1000}], group:{combinator:"and",
  criteria:[{pe_ratio lt 20}]}, run:true}` -> the POST body's criteria is [pe_ratio lt 20] and has no
  market_cap; `{criteria:[{market_cap gt 1e11}], group:{combinator:"or", criteria:[{pe_ratio lt 15},
  {dividend_yield gt 0.03}]}, run:true}` -> body group or[pe_ratio lt 15, dividend_yield gt 0.03]; the
  rc1-vshard-3:3 input `{criteria:[{roe gt "15"},{market_cap gt 1000}], group:{combinator:"and",
  criteria:[{pe_ratio lt 20}]}}` -> body [pe_ratio lt 20]; save_screen + loadScreen + runScreener on the
  first input -> body [pe_ratio lt 20]. Live re-proof: replay the captured body against `/screener/run`
  on custom [AAPL,MSFT,JPM,XOM,KO,PFE,VZ,T,CVX,INTC] -> 4 rows (JPM, CVX, VZ, T), not 10.

Certification-failure count: 0, n/a (a new defect; lands on no register entry). AGENT-043 is not
reopened by this verdict.
