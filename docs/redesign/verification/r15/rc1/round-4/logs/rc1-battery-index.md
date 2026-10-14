# rc1-battery-index — gate round 4

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad
Register read via `git show <sha>:docs/redesign/verification/vysted-r15-register.json` (not working tree).

counts.entries=661, fixed=395 (matches lead-note 395 fixed ids).

Method:
- Parsed every `docs/redesign/verification/r15/stage-c/batch-*/PLAN.md` (25 batches, batch-2..batch-27) for W<k> headings (heading level varies: `##`/`###`, `### W1: name`, `## W1 — role — ids`); section text = heading line to next heading of same-or-shallower level.
- For each batch's VERDICTS.json `certified` list, kept only ids whose register status (at candidate sha) is `fixed`.
- Some ids appear certified in more than one batch's VERDICTS.json (R15-DOCS-017/018, R15-CODE-PLATFORM-013 in batch-10, batch-12/13, and batch-25) — these are reopen/recert cycles; the LATEST batch by number is the authoritative owner (matches lead note: batch-25 "fixed and fresh-certified" the reopened PLATFORM-013 etc.), so later-batch assignment overwrites earlier.
- Matched each owned id's exact string (or its `AREA-NNN` suffix as fallback) inside a batch's W-sections to pick the specific writer set.
- 2 ids (R15-CODE-PLATFORM-014, R15-CODE-PLATFORM-030) are certified in batch-10's VERDICTS.json but their id string never appears inside any batch-10 W-section text (plan text doesn't spell them out) — left unresolved, folded into unplanned.
- 2 ids (R15-CODE-DATA-023, R15-LEAD-043) never appear in ANY batch-N PLAN.md/VERDICTS.json at all — R15-CODE-DATA-023 was fixed via the separate `stage-c/lows/PARTITION.json` low-severity track; R15-LEAD-043 was filed fixed outside the batch process per round-4 lead note (11). Both go to unplanned.

Result: 79 writer sets (391 ids) across batch-2..batch-27, + 4 unplanned sets (1 id each, grouped by subsystem: screener, plugins, backtest, llm-adapters) = 83 sets, 395 ids total, verified as an exact set-equal to the fixed-id set at the candidate sha (no duplicates, no gaps).

Skipped per task: needs_gui (11), removed_with_feature (14) — not battery-relevant.

Output: docs/redesign/verification/r15/rc1/round-4/battery/INDEX.json, INDEX.md.
