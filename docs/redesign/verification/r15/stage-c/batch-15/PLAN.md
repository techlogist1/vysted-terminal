# R15 Stage C — batch 15 plan (RC1 round 2, certification batch)

Base: `004-r4-experience-rebuild` @ `f7b3abf3a507dc44f3b5f4921b483cf580ec6617`.
Planner: Opus. Lows are not planned this batch (lead note). Queue after adjudication:
`{critical:0, high:1, medium:0, low:210}`.

## Selection

The only open critical/high/medium entry is **R15-AGENT-090** (high; agent-chat, research-search).
It is the whole batch. One writer set, **W1**, whose branch already exists.

| id | sev | operator area | writer |
|---|---|---|---|
| R15-AGENT-090 | high | agent-chat, research-search | W1 |

## W1 (opus): validate the salvaged AGENT-090 fix, do not redesign it

**Why opus.** The guard rewrites every sentence the agent relays, on chat, Delegate runs and MCP
invoke. It sits in the agent runtime's streaming state machine (`_consume_round` / `_release`),
in the agent-chat named area. The branch was written by a strongest-tier root-cause pass after two
Opus attempts failed. Judging whether a residual actually fails the bar is a judgement call.

**Branch.** `origin/worktree-agent-batch-15-W1` @ `aaf32a7e`: 6 commits on `17301f54`. Salvage
per the run-state: check out that branch in the W1 worktree first
(`git fetch origin && git checkout -B worktree-agent-batch-15-W1 origin/worktree-agent-batch-15-W1`,
then `git reset --hard aaf32a7e` if the worktree started elsewhere). Since `17301f54`, 004 has only
docs commits (register json/md, run-state), so the merge is clean. The planner confirmed this.

**Files (W1 owns all of them. No other writer exists.)**
- `sidecar/services/adr_ratio.py` (new)
- `sidecar/services/agent_runtime.py`
- `sidecar/services/agent_tools/fundamentals.py`
- `sidecar/tests/conftest.py`
- `sidecar/tests/test_adr_ratio.py` (new)
- `sidecar/tests/test_agent_runtime.py`
- `docs/redesign/verification/r15/stage-c/batch-15/writer-evidence/**`

No `types/data.ts` mirror is needed. `ads_ratio` is a key on an agent-tool result dict, not a
`sidecar/models/` field. No catalog, schema or roster change is needed.

### Mechanism (confirmed in the code on the branch, not from the title)

1. **Grounding (`services/adr_ratio.py`).** EDGAR is keyless.
   - `_fetch`: ticker → CIK (`sec_filings_provider._load_company_tickers`) → submissions index →
     newest `20-F` primary document.
   - `parse_cover_ratio`: reads only the 6,000 chars after the "Section 12(b)" anchor. It matches
     both cover-statement forms, accepting an integer or a number word up to twenty. It returns
     `{ordinary_shares_per_ads, statement}` only when exactly one distinct ratio is stated, and
     `None` otherwise.
   - Adds a nested `provenance {source: "SEC 20-F cover page", filed, url}`.
   - `lookup`: caches hits for 30 d and misses for 24 h (`sec:ads-ratio:<SYM>[:miss]`) and never
     raises.
2. **Attachment (`agent_tools/fundamentals.py`).**
   - `_result` / `_ads_ratio` put `ads_ratio` as the LEADING key of the `fundamentals` ok result.
     The key is added only when `financial_currency` is set (a foreign reporter). It leads because
     the 8,192-char model-facing cap cut it off when it came last.
   - `_statement_context` does the same for `financial_statements`.
   - A domestic reporter (no `financial_currency`) carries no key.
3. **Guard (`agent_runtime.py`).**
   - Claims are now decided by markers, not wording. A sentence is in scope when it names a
     depositary term, or when it follows such a sentence (`ratio_context` on `_TurnState`, carried
     across `_release`) and speaks of shares.
   - In scope, every number counts as a claimed share count unless its own `_MARKED` marker blanks
     it. The markers are: currency, %, a unit word, points, a period, a year, FY/Q/H, an ordinal, a
     form number (20-F, F-6), a clock time, a decimal, thousands or 4+ digits, "one of"/"one-",
     and a count of a lower-case plural noun other than shares/units/securities.
   - The claim is the counts minus the unit `1`. It is traced when one tool result has a segment
     (split on `. ; \n { } [ ]`) that names a depositary term (incl. `Repr`) and carries every
     claimed number. Otherwise the sentence becomes `RATIO_UNAVAILABLE`, and the replacement is
     logged at INFO.

### Planner pre-check (scratch, at aaf32a7e, not committed)

`_guard_ratio_claims` was run against a fundamentals result with no depositary term
(`shares_outstanding 144869230`, `pe 22.4`). Results:
- All 7 GUARDED sentences were replaced. The split-sentence case replaced only the second sentence.
- All 8 KEPT sentences came back byte-identical.
- All 4 TRACED pairs were kept. The sources were `"Each Repr 6 Ords"` and an `ads_ratio` dict whose
  statement is "American Depositary Shares, each represented by Six Equity Shares".

This is not a substitute for the verifier. It means W1 should expect a green bar and must not
redesign the fix.

### W1 task

1. Read `git diff 17301f54..aaf32a7e`.
2. Run the focused tests with `sidecar/.venv`. Detach any run over 120 s.
   - `pytest sidecar/tests/test_adr_ratio.py sidecar/tests/test_agent_runtime.py sidecar/tests/test_fundamentals_tool.py`
   - `ruff format --check sidecar && ruff check sidecar`
3. Check the three residuals the root-causer named against the bar below:
   - (a) "the ADR closed at 5": an unmarked small integer beside a depositary term is replaced
     unless a depositary tool-result segment carries it.
   - (b) Whole-sentence replacement loses true content in the same sentence.
   - (c) An EDGAR miss or outage means no grounding. The guard still replaces the claim, which is
     the safe direction.

   Fix ONLY a residual that a bar sentence actually fails on. Pin the fix with one test on a
   sentence the fix was not written against. None is expected to fail. (a) and (b) are accepted
   limits already recorded in the `ponytail:` docstring. A new true-prose miss is fixed by
   extending `_MARKED`, never the claim class.
4. PyInstaller audit. `adr_ratio.py` is a plain module with no `Path(__file__)` data. The planner
   grepped for it and found none. It is imported lazily (`from services import adr_ratio` inside
   `_ads_ratio`), and modulegraph scans nested code objects, so no `--hidden-import` is needed.
   Record that in the commit or report. The integrator confirms `services.adr_ratio` is in the
   built binary, e.g. `pyi-archive_viewer` or a `/health` smoke plus one SIFY fundamentals call on
   the binary.
5. Push every commit to `origin/worktree-agent-batch-15-W1`. Change no existing test.

## Acceptance bar (verifier, verbatim)

GUARDED when no tool result carries the ratio — 'American Depositary Shares each represent six underlying equity shares', 'Each ADR is equivalent to 2 shares of common stock', 'The ADR-to-share ratio is 1 ADR : 6 shares', '1 ADR = 6 shares.', 'One ADR is worth 10 shares of Sify.', 'A single SIFY ADR gives you 2 shares.', 'SIFY trades as an ADR on Nasdaq. For SIFY, one ordinary share represents 1 share.'; KEPT verbatim — 'Each ADR closed at 5.20 USD on Friday.', 'Each ADS's 52-week high was 12.4.', 'SIFY's ADSs each gained 3 points in 2024.', 'the ADR traded between 10 and 12 dollars', 'Each ADR closed at $12.50 on volume of 40,000 shares.', 'The PE ratio is 22.4.', 'Revenue represents 12% of the segment.', 'SIFY filed its 2024 20-F in July.'; TRACED and kept — '1 ADR : 6 shares' and 'Each ADS represents six ordinary shares' when a tool result carries 'Each Repr 6 Ords' or the cover-page sentence; GROUNDING — for SIFY the fundamentals result carries ads_ratio with ordinary_shares_per_ads 6 and a provenance pointing at the 20-F, and a domestic reporter carries no key; LIVE — 5 runs of the original repro plus 3 fresh phrasings on llama3.1:8b, 0 untraced, and the verifier invents at least three fresh fabrication wordings and two fresh true-prose sentences of its own.

The verifier also re-runs the batch-13 and batch-14 escape lists and the kept lists from the
register note on R15-AGENT-090. The GUARDED/KEPT lines above include them.

## Integrator run order

1. Merge W1 only: `origin/worktree-agent-batch-15-W1` into a scratch integration branch off
   `f7b3abf3`. Audit via `origin/<branch>` only. Nothing else is in this batch.
2. `pnpm sidecars:build`, forced for the main sidecar so `adr_ratio.py` is inside the binary.
   Run it detached and poll it.
3. `pnpm ci-local`, detached and polled.
4. `node scripts/smoke-test-sidecars.mjs`. Then, on the built binary, call SIFY fundamentals once
   and confirm the `ads_ratio` key, or log an EDGAR miss honestly.
5. Hand off to the reviewer, then to the fresh verifier on the bar above.

## Deferred / not-defect

None. There are no other open critical/high/medium entries, and lows are not planned (lead note).
