# RC1 fix round 1 (gate round 2, resumed run): triage plan

Triage lead: rc1-fix-r1-triage (Opus). Candidate and base `4c6dfe8c`. Written 26 Sep, 16:06 IST, for
the resumed gate-round-2 run. The first attempt of this role ran at 07:56. Its plan is kept
verbatim in `PLAN.gr2-attempt1.md`, and its probes in `triage/` are reused here because they ran
on the same sha. Working log: `../logs/rc1-fix-r1-triage.md`.

There are 5 findings: **1 real** in 1 writer set, **4 rejected** and **0 deferred**.

No sidecar was booted for this attempt. Every record was conclusive, either through the 07:56
probes on `:52331` at this sha or through the round-2 recheck's live and in-process evidence. The
new work is an in-process prototype of the round-3 classifier (`triage/r3-classifier-proto.*`)
and a scan of every published brief markdown in `r15/**.jsonl` for non-numeric bracket tokens
(`triage/r3-bracket-corpus.txt`, 28 briefs).

## Writer set

### W1 citation-pseudo-class (opus): rc1-drive-research-briefs:2

**Why opus.** This is the third fix attempt on this finding. Round 1
(`worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar`, then integrator fix `ca6ec990`)
and round 2 (`…-fix-r2-W1-citation-grammar-r2` @ `39585dc3`, integrated at `81fbfe91`) both
failed recheck (`RECHECK.md`, `../fix-r2/RECHECK.md`). If it fails again, the three-failure rule
stops it and sends it to DECISIONS. The fix is a root-cause change that has to stay identical in
two regex dialects.

**Start point.** Branch from `4c6dfe8c`, then run
`git merge --ff-only 39585dc3`, which is `origin/worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2`.
That brings in the r1 writer, the integrator fix and r2 as-is. All r1 and r2 tests must pass
unchanged.

**Mechanism.** There are two causes, and both are verified in the source.

1. **Source.** The researcher extraction prompt (`deep.py:1003-1015`) says "Cite concretely", but
   the evidence it gives the model is unnumbered. That evidence is the
   `Structured (<tool>): {…}` line (`deep.py:987-997`), the `wrap_untrusted("exchange disclosures
   (NSE/BSE feeds)", …)` block, raw URLs and "Web evidence:". So the model makes up its own
   bracket citations, and synthesis copies them into the brief. The live escapes were
   `[Structured: {'ok': True, 'count': 0, 'news': []}]` (Cochin, llama) and
   `[NSE filing, August 2026]` (Kaynes ULTRA, 4o-mini).
2. **Net.** Both `citecheck.py` and `brief-ingest.ts` recognise only digit groups plus one
   enumerated label family (`_PSEUDO_CITE_RE`). So a group that mixes a label with a marker
   (`[NSE filing, August 2026; 2][3]`, `[Web evidence; 2]`), a spelled-out marker (`[Source 2]`),
   a label with a payload (`[Structured: {…}]`, which also nests `[]`) and a paraphrased source
   label all ship verbatim (`../fix-r2/recheck/gr2/fresh-backend-probe.txt`).

**Fix.** The class is "a bracket token that names a source but does not resolve to the rail". It
is defined by what the token names, not by its shape or its position. That avoids both the round-1
over-match and the round-2 enumeration gap.

- **The scanner, in both `citecheck.py` and `brief-ingest.ts`.** Scan balanced `[…]` tokens on
  one line, counting nesting depth, so that `[Structured: {… 'news': [{'tags': []}]}]` is one
  token. Skip these tokens exactly as today:
  - markdown links `[..](`,
  - reference-link halves `[text][ref]`,
  - definitions `[ref]:`,
  - single-character tokens `[x]`,
  - pure numeric markers and groups (the existing r2 grammar).
- **Mixed group.** Split on `,` and `;`. A member matching
  `(?:sources?|refs?|references?)?\s*#?\d{1,3}(?:\s*[-–—]\s*\d{1,3})?` becomes a marker (ranges
  expand inclusive, as in r2), and every other member is dropped. So
  `[NSE filing, August 2026; 2]` becomes `[2]`, `[Source 2]` becomes `[2]` and `[Sources 2, 3]`
  becomes `[2][3]`. The markers produced then go through the normal range check.
- **Source-named token.** A token whose head names a source is a pseudo-citation. The head is the
  text before the first `:`, or the whole content when there is no colon. It names a source when
  it matches, case-insensitive with word boundaries, `sources?|references?|refs?|evidence|findings?|reports?|filings?|disclosures?|announcements?|releases?|transcripts?|presentations?|articles?|news|press|websites?|feeds?|structured|documents?`,
  or when the whole content holds a URL (`https?://` or `www.`). The backend strips it, counts it
  in `removed` and tidies the spacing. The frontend renders it as `[?]` and counts it in
  `countBrokenCitations`.
  - This replaces `_PSEUDO_CITE_RE`/`PSEUDO_CITE_RE`. The r2 label family is a subset of it.
  - Leave `data` out of the lexicon, so a disclaimer such as `[data unavailable]` survives.
    Mark that choice with a `ponytail:` comment.
- **`iter.py` `_remap_markers`.** It must use the same expansion, so that `[Source 2]` and
  `[Web evidence; 1]` from an angle remap per number.
- **`deep.py` extraction prompt.** Replace "Cite concretely" with an instruction to name the
  source in plain words and never write square-bracket citations, because numbered citations are
  added at synthesis.
- **No net change for these.** Positional heuristics, exchange or ticker words, and legitimate
  system brackets such as `[basis: …]`, `[= formula]` and `[CONFLICT]` need no rule. They carry
  no source noun in their head, so the rule never touches them.

**Acceptance tests.** Put the same cases in `test_research_citecheck.py` and
`brief-ingest.test.ts`, one test per behaviour:

- **Literal escapes.**
  - `[NSE filing, August 2026]` is stripped, or becomes `[?]` and counts as broken.
  - `…million [NSE filing, August 2026; 2][3].` with 13 sources becomes `…million [2][3].`
  - `…no results [Structured: {'ok': True, 'count': 0, 'news': []}]` is stripped whole.
- **Cases the fix was not written against.**
  - `[Company presentation; 1-2]` with 5 sources becomes `[1][2]`.
  - `[Ref 7]` with 5 sources is removed (removed=1), or becomes `[?]`.
  - `[per the Q1 transcript]` is stripped.
  - `[Structured (fundamentals): {'rows': [{'tags': []}]}]`, which nests two levels, is
    stripped whole.
  - `[https://nseindia.com/x]` is stripped.
- **Must survive byte-identical, with 0 broken.**
  - `[= (52w high - price) / 52w high]`
  - `[FY25]`
  - `[Note: consolidated per the annual report]`
  - `see [CONFLICT] note`
  - `[PDF] - 2026-09`
  - the r2 string with `[basis: …]`, `[NSE: BDL]`, `[the Company]` and `[sic]`
- **Remap.** In `test_research_iter.py`, `_remap_markers('x [Source 2] y [Web evidence; 1].')`
  maps each number to the merged list.

**Scratch check (not committed).** Push these through both nets:

- the finding's BDL markdown (`../fix-r1/recheck/gr2-original-bdl-brief-through-candidate.txt`
  input),
- r2's live Kaynes #1 and Cochin markdown (`../fix-r2/recheck/gr2/2-ultra-kaynes-4omini.jsonl`,
  `3-deep-cochin-llama.jsonl`),
- `triage/r3-bracket-corpus.txt`.

Afterwards, no bracket token whose head names a source may remain, and every `[basis: …]` must
be unchanged.

**Files (W1 owns all of them).**

- `sidecar/services/research/citecheck.py`
- `sidecar/services/research/iter.py`
- `sidecar/services/research/deep.py`
- `src/lib/brief-ingest.ts`
- `sidecar/tests/test_research_citecheck.py`
- `sidecar/tests/test_research_iter.py`
- `src/lib/brief-ingest.test.ts`

## Rejected (the final verifier must concur)

- **rc1-scenarios:1: in the accepted known-limitation class, not a mechanism defect.**
  - The "silent 90-bar cap" is disclosed in the payload through `bars_returned`,
    `bars_available` and `window_start` (the R15-AGENT-062 fix).
  - For ELCIDIN the cap changed nothing. `/history/ELCIDIN.NS` 1y has 111 bars from the
    2026-04-20 listing, and the minimum low is 102,210 both over all bars and over the last 90.
  - The stated "52-week low ₹110,095" is the `low` of the 2026-07-31 bar, which is inside the
    payload (`triage/elcidin-1y-summary.json`). "103,800 is 6,295 above 110,095" is the local
    model's own arithmetic.
  - That is value-only grounding of the wrong field, R15-LEAD-037, which is blocked_tier4 and
    accepted in DECISIONS 4.11. Per the lead note it is filed as a register note
    (`findings/rc1-fix-r1-triage.json` :1), with no fix round.
- **rc1-datapack:1: not a regression.** R15-DATA-008's fix_shape offered "carry a separate
  financial_currency on the model and format with it". That was built, and the mixed-basis P/S is
  withheld (`triage/sify-fundamentals-summary.json`).
  - The finding's premise is false. Both consumers format revenue with
    `financial_currency ?? currency` (`EquityOverviewPanel.tsx:833`, `brief-blocks.tsx:336`,
    re-read at `4c6dfe8c`).
  - Tests pin it: `EquityOverviewPanel.test.tsx:591` expects "₹14.0B" and asserts no "$14.0B",
    and `brief-blocks.test.ts:661` expects "₹12.0B".
- **rc1-datapack:2: not a regression.** R15-DATA-058's defect was truncation, and its fix_shape
  allowed "reserve a slot for the best cross-region match". `_capped`
  (`symbol_resolver.py:1116`) does that, SIFY 0.913 is listed (`triage/sify-resolve.json`), and
  batch 8 certified it.
  - Its last-place order is the D58c / V5 locale tie-break: "under an IN session a foreign row
    can never outrank an IN row at the same band" (`symbol_resolver.py:1103-1109`).
  - Reordering the list would reverse that decision, not fix a regression.
- **rc1-drive-onboarding-stranger:1: the drive itself filed this as a reclassification note.** It
  is the "hallucinated-tool-result-citation" class of R15-LEAD-030: Zomato figures stated with
  only `get_terminal_state` ok behind them. That class is blocked_tier4 and accepted in
  DECISIONS 4.9. It is filed as a register note under R15-LEAD-030
  (`findings/rc1-fix-r1-triage.json` :3), with no fix round.

## Deferred

None. No finding needs a Tier-1 file or reverses a locked decision.

## Carried from the 07:56 attempt (not in this run's finding list)

`findings/rc1-fix-r1-triage.json` :2 is still open for the lead: battery set-28 ran against 12
nonexistent ids. It is a coverage gap, and set-28 should be re-run with the ids at
`battery/INDEX.md:81`.
