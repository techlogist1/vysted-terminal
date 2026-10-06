# rc1-battery-3 — regression battery shard 3 (round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, worktree
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-cand`
(HEAD verified before starting).

Booted one sidecar for the whole shard on :52343, seed-data copy
`rc1-round-5-data-battery-3` (cp -R from `rc1-round-5-seed-data`), env
`VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154` pointing at
the shared read-only MCP stack. `/health` ok in <1s (source run). Reused across
all three sets, stopped at the end (sleep-wrapper pid 28946, worker pid 28949 —
both killed; worker needed a direct kill since it doesn't read the piped
sleep's stdin and doesn't die on the pipe closing).

No prior round-5 files existed for this label — started fresh.

## Sets

- **set-15** (batch-5/W1-india-disclosures-agent-surface, 10 ids): all hold.
  Live curl repros for the DATA-* ids (announcements dedup, promoter pledge,
  corporate actions, quarterly income, shareholding FII/DII derivation);
  in-process calls into the candidate's own venv for the AGENT-*/CODE-RESEARCH
  ids (market_overview headline-failure surfacing, shareholding_pattern note/
  catalog description, price_data truncation markers, deep-research wall
  clamp) plus source reads confirming the fix shape. DATA-074 confirmed by
  grepping `services/research/` for direct `get_announcements` calls (zero —
  every call site now goes through the same cached `corporate_announcements`
  agent tool the router uses).
- **set-36** (batch-9/W3-fundamentals-identity-earnings, 4 ids): all hold.
  DATA-052 (ELCIDIN/NAPEROL sector fix), DATA-069 (972 per-firm/per-day price-
  target rows, not one Consensus point), LEAD-016 (reported_date ~1mo after
  period_end), LEAD-023 (in-process FakeTicker with no metadata time + empty
  history raises typed ProviderError, not IndexError — confirmed against the
  real source, not a mock of the fix).
- **set-82** (batch-29/W3-sonnet, 2 ids): both hold. LEAD-049 (nifty50 sweep
  0 skipped, TMPV resolves/quotes, TATAMOTORS absent). LIFECYCLE-020: replayed
  the batch-29 verifier's exact circuit-breaker shape in-process against the
  real `provider_health` module (2 user-weight 429s, then 2436 warm-weight-0.0
  429s that advance nothing, then 1 more user 429 that opens the circuit —
  matches `_WARM_THROTTLE_WEIGHT = 0.0` at screener.py:170) plus a live
  `/system/provider-health` read (yahoo open=false, ct=0).

No batch VERDICTS.md files mention DATA-052/069/LEAD-016/023/049 or
LIFECYCLE-020 by grep (register `closure_evidence` names batch-9/batch-29
merge commits, not a per-entry VERDICTS row for these four batch-9 ids), so
round-4's `battery/set-37.md` and `set-19.md` (same repro shapes, prior
candidate) served as the repro reference for those, plus the register entries
themselves. batch-29's `VERDICTS.md` did have full per-entry write-ups for
LIFECYCLE-020 and LEAD-049 and was used directly.

No regressions, no new defects, no chain failures, no gate8/trading paths
touched, no environment blocks. 16/16 ids raw-covered.

COVERAGE: 16/16 ids raw; no raw: none.
