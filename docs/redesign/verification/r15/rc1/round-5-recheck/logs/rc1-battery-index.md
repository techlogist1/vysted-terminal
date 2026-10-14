# rc1-battery-index — working log

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd
Register read via `git show 949c3c9f...:docs/redesign/verification/vysted-r15-register.json` (not working tree).

- fixed status count at sha: 395 (matches gate-facts fixed_total).
- For every `docs/redesign/verification/r15/stage-c/batch-*/PLAN.md`, parsed writer sections
  (`## W<k>` / `### W<k>` / `## Writer <letter>` headings) and each batch's VERDICTS.json
  `certified` array.
- For each fixed id, assigned it to the HIGHEST-numbered batch whose VERDICTS.json certified
  it (handles ids reopened and re-fixed in a later batch, e.g. R15-AGENT-001: certified
  batch-2/3, reopened, certified again batch-28/29 — assigned to batch-29's writer set).
- Within that batch, assigned the id to the first writer section (in file order) whose body
  text mentions the id; ids certified but not textually found under any writer heading
  (8 total, across batch-3/10/13/18) landed in a `<batch>/unassigned` set — still exactly one
  set, just not a per-writer slug.
- 3 fixed ids were certified in no batch's VERDICTS.json at all (stage-c coverage gap) —
  grouped into `unplanned-N` sets of <=12 by subsystem.
- Verified: union of all sets == the 395 fixed ids at the sha, no id appears twice, no non-fixed
  id included. Script + intermediate files: scratchpad build_index.py / index_result.json.

Output: battery/INDEX.json, battery/INDEX.md (90 sets total).
