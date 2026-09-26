# RC1 gate round 2, fix round 2: recheck

Rechecker: rc1-fix-r2-recheck (Opus 5.5, fresh). Candidate `81fbfe910d472ecd154fa62e42d86bce213a697e`.
I ran everything from the running app on my own sidecar. The source was
`scratchpad/rc1-4c6dfe8-fix-int` (clean, read-only), on port `:52337`, with a fresh keyless seed copy
(`rc1-data-rc1-fix-r2-recheck`). I stopped the sidecar at the end (sleep pid 84426), and `:52337` is
free. For the in-process checks I used the candidate venv (`PYTHONDONTWRITEBYTECODE=1`) and node
v24 type-strip of the candidate `brief-ingest.ts`. Nothing was written to the worktree. Evidence is
in `fix-r2/recheck/gr2/`. Log: `logs/rc1-fix-r2-recheck.md`. Findings:
`findings/rc1-fix-r2-recheck.json`. (The previous round-2 recheck of `1d6511c8` is in git at
`b2cfbb68`, with its findings under `findings/round-1/`.)

**Result: 0 fixed, 1 still failing.**

| key | repro | observed | verdict |
|---|---|---|---|
| rc1-drive-research-briefs:2 | Literal: the finding's tokens `[New findings]` (BDL) and `[2, 3]`/`[2, 4]` (Kaynes) through both candidate nets. The finding's own published BDL (32 sources) and Kaynes ULTRA (8 sources) markdown went through both nets. Live on :52337 via harness/turn.py: BDL DEEP gpt-4o-mini (`gr2/1-deep-bdl-4omini`), Kaynes ULTRA gpt-4o-mini (`gr2/2-ultra-kaynes-4omini`), and a fresh-symbol, fresh-provider Cochin Shipyard DEEP llama3.1:8b (`gr2/3-deep-cochin-llama`). Every bracket token in each live `publish_brief.markdown` was scanned (`gr2/live-published-scan.txt`), and the live escapes plus variants were run in-process through both nets (`gr2/fresh-backend-probe.txt`, `gr2/fresh-frontend-probe.txt`). | **Literal repro fixed.** `[New findings]` is stripped by the backend or becomes `[?]` in the frontend, and `[2, 3]`/`[2, 4]` becomes `[2][3]`/`[2][4]` (`gr2/backend-probe.txt`, `gr2/frontend-probe.txt`, `gr2/original-briefs-through-candidate.txt`). Ranges, mixed numeric groups and the enumerated labels resolve, and the must-survive brackets (`[basis: …]`, `[NSE: BDL]`, `[sic]`, `[the Company]`, links and definitions) stay byte-identical. The live BDL publish (8 sources) and Kaynes publish #2 (8 sources) are clean. **The claim does not hold on fresh cases from the same live run:** (1) Kaynes ULTRA publish #1 (13 sources) ships `[NSE filing, August 2026]` twice and `[NSE filing, August 2026; 2][3]`, and the real `[2]` inside that group never chips. (2) Cochin DEEP (llama, 7 sources) ships `[Structured: {'ok': True, 'count': 0, 'news': []}]`. That is the leaked `deep.py:987-994` "Structured (tool): …" prompt-block label, exactly the mechanism PLAN.md names ("the model cites the label of a prompt block it was shown"), but it is not in the enumerated family. Both nets leave all of them byte-identical (removed=0, broken=0). The variants `[Structured]`, `[Web evidence; 2]`, `[Source 2]`, `[Sources 2, 3]` and `[exchange disclosures]` behave the same way. | **still failing (not certified).** The title claim is that a bracketed group or prose pseudo-citation ships as literal, unresolved text in the published brief. That still holds on this candidate's live output. The fix enumerates one label spelling family and digit-only groups. It does not cover the class of bracketed citation-position tokens that don't resolve to the rail: a group that mixes a label and a marker, other prompt-block labels (`Structured`), and model-paraphrased source labels. Fresh repro: rc1-fix-r2-recheck:1. |

**Chain.** `fix-r2/INTEGRATION.md` records everything at `81fbfe91`. The ci-local final run shows
`EXIT=0 2026-09-26T03:42:36Z` (3603 passed, 1 skipped), smoke shows `SMOKE_EXIT=0
2026-09-26T03:38:16Z`, and targeted vitest shows `VITEST_EXIT=0`.

**Adjacent.** Nothing I can see broke. The in-range `[n]` chips are intact in every live publish,
and the qualifier, ticker and editorial brackets survive.

**Note.** This is the second fix round on this finding. The fix-r2 PLAN already applies the
operator's three-failure rule to it, so the lead should decide whether this failure sends it to
DECISIONS.

**Environment note, not filed.** In Kaynes ULTRA, the post-publish chat turn ended with "Could
not reach OpenAI: Request timed out" at 572 s. Both briefs had already published. I did not run a
direct probe, so I have not classified it.
