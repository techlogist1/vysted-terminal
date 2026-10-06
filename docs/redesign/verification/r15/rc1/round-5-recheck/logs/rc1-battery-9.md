# rc1-battery-9 — regression battery shard 9

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, scratch worktree
`rc1-round-5-recheck-cand` (read-only). Sidecar booted from source, `127.0.0.1:52355`,
data dir `rc1-round-5-recheck-data-rc1-battery-9` (copied from
`rc1-round-5-recheck-seed-data`). openbb-mcp/sec-edgar-mcp not needed for this shard's
entries (no MCP-routed repro in scope). Sidecar stopped at end of shard (pid 79661,
confirmed down: `/health` connection refused).

Sets: batch-7/W5-agent-writes-portfolio (set-29, 9 ids), batch-9/W3-fundamentals-identity-earnings
(set-37, 4 ids), batch-10/W8-plugins-dock (set-47, 2 ids), batch-25/W1-opus (set-68, 1 id).
16 ids total.

## Method

- Every id: first read the register entry, then the certifying batch's `VERDICTS.md`
  "Per-entry evidence" line, to find the ORIGINAL repro and how it was certified.
- Backend/API entries (LEAD-023, DATA-052, LEAD-016, DATA-069, the resolver half of
  AGENT-044): re-ran the exact repro live against the fresh sidecar (curl / an in-process
  python call for LEAD-023's empty-history case, since it needs a dead upstream).
- Frontend-only entries (everything else in set-29, all of set-47 and set-68): these have
  no sidecar route — the defect and its fix live entirely in React components / Zustand
  stores, exercised in the original batches only via vitest against real components. This
  role may not run vitest or a GUI, so there is no live probe available for these ids'
  OWN repro. For each: confirmed via `git ls-files` that the test file the batch verifier
  named is a real, committed, permanent test (not a scratch file — batch-25's own cited
  filename `plat013.test.tsx` turned out NOT to exist at this sha, so I searched for and
  found the real committed tests instead), then read the exact pinned test body to confirm
  it still asserts the register's repro shape. Verdict: `ci_pinned`, naming the test(s).

## Findings

None. All 16 ids hold at this candidate: 5 by live repro, 11 by pinned committed test
(verified present and asserting the right shape, not merely assumed).

## Notes

- Port 52349 (this shard's assigned port per the task prompt) was already held by an
  unrelated leftover process (`agent023/receiver.py`, a webhook listener from another
  role's earlier work, PID 73871, answering 501 on GET). Not a sidecar, not mine to kill
  — booted this shard's sidecar on `:52355` instead.
- `rc1-round-5-recheck/battery/` already held 27 other sets (raw evidence + set-*.md) from
  shards `rc1-battery-0` through `rc1-battery-8` when this shard started; none of them are
  this shard's sets (29/37/47/68), so none were reused or touched.
- No Ollama/local-model calls were needed for this shard's ids (no agent-run repro; all
  backend or store-level checks), so the local-model lock was never taken.

COVERAGE: 16/16 ids raw; no raw: none.
