# RC1 fix round 2 (gate round 2): triage plan

Triage lead: rc1-fix-r2-triage (Opus). Candidate and base `ca6ec990`. This file replaces the
25 Sep round-2 plan for `b0f2b256`, which is in git at `b2cfbb68`. Working log:
`../logs/rc1-fix-r2-triage.md`. The repro is in `triage/r2-citecheck-repro.txt`.

There is 1 finding to close: rc1-drive-research-briefs:2. It is **real** and goes to 1 writer
set. **0 rejected, 0 deferred.**

## Evidence

The round-1 recheck (`../fix-r1/RECHECK.md`, rc1-fix-r1-recheck:1 and :2) was conclusive. I
re-ran it in-process with the candidate venv, with no sidecar, because no live run is needed to
show a regex's grammar. It reproduced, and one new over-match case turned up:

- `[2-4]`, `[2–4]`, out-of-range `[7-9]` (5 sources) and the mixed group `[1, 3-4]` all ship
  verbatim, and removed=0.
- `[New findings][2]` ships verbatim. `[Web evidence][9]` becomes `[Web evidence]`.
- `[basis: fraction of price]` and `[NSE: BDL]` are deleted. So is `[the Company]` in
  `He said [the Company] expects growth [1].`, which becomes "He said expects growth [1]."
- ULTRA `_remap_markers('x [1-2] y [1, 2].')` becomes `x [1-2] y [2][3]`, so the range keeps
  the angle-local numbering.

## Root cause

`citecheck.py` and `brief-ingest.ts` have the same two defects.

1. **Group grammar.** `MARKER_GROUP_RE` only accepts `,` and `;` separators, so a range
   (`-`, `–`, `—`) is never expanded. Because of that it is never range-checked, never remapped
   (iter.py:902 reuses `expand_marker_groups`) and never chipped.
2. **Pseudo-citation rule.** The rule recognises a pseudo-citation by its shape (`[` followed by
   any letter-led token), which cannot tell a leaked prompt label from real bracketed text.
   - It over-matches: basis qualifiers from `semantics.py:1290`, exchange tags, notes and
     editorial insertions are all caught.
   - Its `(?![(\[:])` lookahead under-matches: a label followed by `[n]` is spared.

   The mechanism behind the finding is narrower than the shape the rule matches. The model
   cites the **label of a prompt block** it was shown. The labels are "New findings this round"
   and "Current report" (iter.py:210-211), "Working report" (:270), "Latest evidence" (:506),
   "Panel reports" (:807, :1164), "Sources" and "Known sources", and "Web evidence"
   (deep.py:1015).

## W1 citation-grammar-r2 (opus): rc1-drive-research-briefs:2

**Why opus.** This is the second fix attempt on this entry. The operator's three-failure rule
applies, and the round-1 attempt both missed part of the class and over-matched. The grammar
also has to be exact, and identical, in two regex dialects.

**Fix.**

- **The group regex, in both files.** Use
  `\[(?=[^\]]*[-–—,;])(\d{1,3}(?:\s*[-–—]\s*\d{1,3})?(?:\s*[,;]\s*\d{1,3}(?:\s*[-–—]\s*\d{1,3})?)*)\](?!\()`.
  Expansion turns each range member into every number from its lower endpoint to its higher
  one, inclusive.
- **The pseudo regex, in both files.** Replace the shape rule with the prompt-label family,
  case-insensitive:
  `\[((?:the\s+)?(?:(?:new|latest|web|current|working|panel|known)\s+)?(?:findings?|evidence|reports?|sources?)(?:\s+this\s+round)?)\](?![(:])`.
  Drop the lookbehind.
- Update the docstrings. iter.py needs no change.

**Tests (acceptance).** Each case goes in both `test_research_citecheck.py` and
`brief-ingest.test.ts`:

- **Ranges.** `[2–4]` with 5 sources becomes `[2][3][4]`. `[7-9]` with 5 sources is removed
  (removed=3), or becomes `[?][?][?]` in the frontend. Case the fix was not written against:
  `[3—5]` with 4 sources becomes `[3][4]`.
- **Labels.** `[Latest evidence][3]` becomes `[3]`. `[basis: trailing 52 weeks]`, `[NSE: BDL]`,
  `[the Company] expects` and `[sic]` stay byte-identical, and countBroken is 0.
- **Remap.** In `test_research_iter.py`, `_remap_markers('x [1-2] y.')` remaps each member.

The existing round-1 tests must pass unchanged.

**Files.** `sidecar/services/research/citecheck.py`, `src/lib/brief-ingest.ts`,
`sidecar/tests/test_research_citecheck.py`, `sidecar/tests/test_research_iter.py`,
`src/lib/brief-ingest.test.ts`.

**Scratch acceptance check.** Re-run `../fix-r1/recheck/gr2-original-bdl-brief-through-candidate`
(the finding's BDL brief). Both nets must keep the two `[basis: …]` qualifiers and must not count
them as broken.

## Rejected

None.

## Deferred

None.
