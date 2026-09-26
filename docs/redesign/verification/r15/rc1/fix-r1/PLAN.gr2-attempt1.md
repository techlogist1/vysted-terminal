# RC1 fix round 1 (gate round 2): triage plan

Triage lead: rc1-fix-r1-triage (Opus). Candidate and base `4c6dfe8c`. Reproductions ran on my
own sidecar `:52331` (rc1-cand source, seed-data copy `rc1-data-rc1-fix-r1-triage`) and
in-process with the rc1-cand venv. Probe outputs are in `triage/`. Working log:
`../logs/rc1-fix-r1-triage.md`. This file supersedes the 25 Sep plan for base `4097dac4`.

There are 6 findings: **1 real** in 1 writer set, **5 rejected**, **0 deferred**.

## Writer set

### W1 citation-marker-grammar (sonnet): rc1-drive-research-briefs:2

Files: `sidecar/services/research/citecheck.py`, `sidecar/services/research/iter.py`,
`src/lib/brief-ingest.ts`, `sidecar/tests/test_research_citecheck.py`,
`sidecar/tests/test_research_iter.py`, `src/lib/brief-ingest.test.ts`.

The mechanism is confirmed. The evidence and the offline repro are in `triage/citecheck_repro.txt`.

`MARKER_RE` in `citecheck.py:39`, `CITE_MARKER_RE` in `brief-ingest.ts:396` and
`_remap_markers` in `iter.py:891` all use the same grammar, `\[(\d{1,3})\](?!\()`. That grammar
recognises only one bare integer. As a result:

- **(a) Grouped markers are never checked.** A group such as `[2, 3]` is never range-checked,
  audited or chipped. In ULTRA, `_remap_markers` rewrites an angle's `[2]` to its merged
  number, but it leaves `[2, 3]` in the angle's LOCAL numbering. The repro shows
  `x [2, 3] y [2]` becoming `x [2, 3] y [5]`, so the group would point at the wrong sources.
- **(b) Pseudo-citations ship verbatim.** `[New findings]` is a leaked prompt-block label. The
  iter merge prompt (`iter.py:181-209`) tells the model to end every fact with an `[n]` marker.
  The findings it gives the model come from the researchers' `_run_researcher` extraction
  (`deep.py:998`) and are unnumbered, so the model cites the block label instead.

**Fix.**

- **citecheck.py:** add `expand_marker_groups()`, which turns `[2, 3]` and `[2; 3]` into
  `[2][3]`. Call it first in `ensure_citation_integrity` and in `_remap_markers`.
- **citecheck.py:** strip a citation-position bracket token whose content starts with a letter
  and is at least 2 characters long. Examples: `[New findings]`, and `[6][New findings]`
  becoming `[6]`. The token must not be followed by `(`, `[` or `:`. This rule leaves links,
  reference links and `[x]` checkboxes alone.
- **Merge prompt:** add one line telling the model to cite only the Known-sources numbers and
  never a section label.
- **brief-ingest.ts:** add the same expansion. Flag pseudo-citations as `BROKEN_CITE_MARKER`
  and count them in `countBrokenCitations`.

**Tests.**

- A citecheck test on a case the fix was not written against: `[1; 4]` with 3 sources becomes
  `[1]`, because 4 is out of range. `[Current report]` and `[Web evidence]` are stripped.
  `[link](u)`, `[x]` and a reference link survive.
- A remap test: `[2, 3]` from an angle is remapped per number.
- A vitest test: `[2, 3]` becomes two chips, and `[Panel reports]` becomes `[?]`, counted as
  broken.

## Rejected (the final verifier must concur)

- **rc1-scenarios:1: not a product defect in the mechanism it names.** The claimed "silent
  90-bar cap" is disclosed through the payload's `bars_returned`, `bars_available` and
  `window_start` fields, which is the R15-AGENT-062 fix. For ELCIDIN the cap also changed
  nothing:
  - `/history/ELCIDIN.NS` 1y has only 111 bars, starting from the 2026-04-20 listing.
  - The minimum low over all 111 bars and over the last 90 bars is the same value, 102,210.

  The stated "52-week low ₹110,095" is not untraceable. It is the 2026-07-31 bar's `low`,
  which is inside the payload (`triage/elcidin-1y-summary.json`). The model labelled one
  historical bar value as the 52-week low, and then wrote "103,800 is 6,295 above 110,095".
  That is the value-only-grounding class of **R15-LEAD-037**, which is blocked_tier4 and
  accepted as a known limitation in DECISIONS 4.11, plus the local model's own arithmetic.
  Under the lead note it is filed as a register note under R15-LEAD-037
  (`findings/rc1-fix-r1-triage.json`), with no fix round.
- **rc1-datapack:1: not a regression.** R15-DATA-008's fix took the second option in its
  fix_shape: "carry a separate financial_currency on the model and format with it". There is
  no FX conversion (D-B2-3), and the mixed-basis P/S and EV/EBITDA ratios are withheld.
  - Live `/fundamentals/SIFY` returns `currency` USD, `financial_currency` INR,
    `revenue_ttm` 46.5e9 and `price_to_sales` null (`triage/sify-fundamentals-summary.json`).
  - The finding says `EquityOverviewPanel.tsx` and `brief-blocks.tsx` read `currency` next to
    revenue. That is false: they format with `financial_currency ?? currency`
    (`EquityOverviewPanel.tsx:833`, `brief-blocks.tsx:336`).
  - Tests pin that behaviour: `EquityOverviewPanel.test.tsx:591` expects "₹14.0B" and asserts
    no "$14.0B", and `brief-blocks.test.ts:661` expects "₹12.0B".
- **rc1-datapack:2: not a regression.** R15-DATA-058's defect was that SIFY was truncated out
  of the chooser. Its fix_shape offered two options: "…score dominate locale… (or reserve a
  slot for the best cross-region match)". The fix (`2f308200`, `_capped`,
  `symbol_resolver.py:1116`) took the second, and batch 8 certified it. SIFY is now listed
  (`triage/sify-resolve.json`). Its last-place order is the documented D58 V5 / D58c locale
  tie-break ("under an IN session a foreign row can never outrank an IN row at the same band",
  `symbol_resolver.py:1103-1109`). Changing that order would reverse a decision, not fix a
  regression.
- **set67-untraced-ratio-escape: the claim was traced, and the guard behaved correctly.** The
  battery assumed that the cashflow result carries no depositary term. That is false:
  `_financial_statements` spreads `_statement_context`'s `ads_ratio` into every statement
  result for a foreign reporter (`agent_tools/fundamentals.py:258-271`, part of the
  AGENT-090 fix).
  - Live, the SIFY quarterly cashflow result carries `ads_ratio.ordinary_shares_per_ads: 6`
    with the 20-F cover text "each represented by Six Equity Shares" (`triage/fs_result.json`).
  - `_ratio_claim_traced` returns True for the model's sentence against that result, and
    False against a result with no depositary term. `_guard_ratio_claims` then replaces the
    sentence with `RATIO_UNAVAILABLE` (`triage/ratio_guard_check.txt`).
  - No register note is needed under R15-LEAD-030.
- **set28-research-gap: harness data defect, not a product defect.** The set-28 shard was
  handed ids that do not exist, `R15-RESEARCH-044` to `-066`. `battery/INDEX.md:81` assigns
  `batch-7/W4-research-funnel` these 12 real ids: R15-DATA-075, R15-RESEARCH-019/020/021/022/
  023/024/026/033/038, R15-UI-038 and R15-UI-092. No `set-*.md` covers them. **Lead action
  before the gate verdict:** re-run battery set-28 against those 12 ids. That is a coverage
  gap for the verification run to close, not code to fix.

## Deferred

None.
