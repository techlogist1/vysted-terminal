# rc1-battery-21 — regression battery shard 21 (Sonnet), round 5-recheck

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via `git rev-parse HEAD`
against `.../scratchpad/rc1-round-5-recheck-cand`, read-only).

Own sidecar: port `52361`, data dir copied from `rc1-round-5-recheck-seed-data` ->
`rc1-round-5-recheck-data-battery21`, booted from the candidate's `sidecar/` source
(`VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154`, both shared
read-only). Health confirmed OK before any probe; stopped cleanly at the end by
killing its own sleep pid (97210) — no other agent's port touched.

Sets covered (all four in the shard, one set file each, per-id raw file under
`battery/raw/set-<n>/`):

- **batch-5/W2-resolver-market-data** (`set-17.md`) — R15-DATA-097, R15-DATA-057,
  R15-LEAD-011, R15-DATA-015, R15-DATA-037, R15-LEAD-009, R15-DATA-072. All hold.
  Two (DATA-097, DATA-072) are design/structural repros verified by source
  re-check + pinned-test citation rather than execution (this role never runs
  pytest/vitest suites); the rest re-ran live against the own sidecar, including
  the crypto range fix (needed `asset_class=crypto` on the query — the raw
  `%2F`-encoded curl the register flagged as a pre-existing, out-of-scope routing
  quirk still 404s and is not part of this entry's own repro).
- **batch-8/W5-agent-runtime-research** (`set-34.md`) — R15-CODE-AGENT-004,
  R15-LEAD-019, R15-CODE-AGENT-007, R15-CODE-AGENT-016, R15-LIFECYCLE-014,
  R15-CODE-RESEARCH-003. All hold. Two in-process python calls against the
  candidate's own venv (`price_per_million`, `default_base_url_for`) gave a live,
  executed result rather than a source-only read; AGENT-004 is ci_pinned (needs a
  real billed Gemini thinking round, not run to avoid spend).
- **batch-6/W1-india-exchange-data** (`set-21.md`) — R15-DATA-017. Holds; re-ran
  every named sub-repro (JNPR/DHOOTTRANS/SUMAX disclosures, SUMAX quote, the
  exact-legal-name resolver search, AMAL's NSE+BSE resolve and results calendar).
- **batch-12/W3-as-of-on-the-ratings-consensus** (`set-59.md`) — R15-DATA-068.
  Holds; sidecar side live (`as_of` now on the wire for all 4 earnings envelopes),
  frontend side by source re-check (TTL + `refresh()` + displayed "As of" stamp
  in both stores and the panel).

No regressions found. `findings/rc1-battery-21.json` is `[]`.

COVERAGE: 15/15 ids raw; no raw: none.
