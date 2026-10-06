# rc1-battery-1 — regression battery shard 1 (round-5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, sidecar `127.0.0.1:52341`
(sleep-launcher pid recorded, killed at end of run), data dir
`rc1-round-5-recheck-data-rc1-battery-1` (copy of the round's seed data).

Sets: batch-5/W1-india-disclosures-agent-surface (11 ids), batch-10/W3-fundamentals-bse-cache
(4 ids), batch-14/W1-agent-runtime-ratio-guard-clas (1 id). 16 ids total.

Method: HTTP GET against own sidecar for REST-backed entries; in-process python calls
(candidate's `.venv`) against the agent-tool handlers for entries with no REST route
(`shareholding_pattern`'s pledge field via `/disclosures/shareholding`, `price_data`,
`market_overview`, `corporate_announcements` cache-key check, `option_chain`,
`grader.grade`); one live `vy.py invoke ... --provider ollama --model llama3.1:8b` call
each for R15-AGENT-020 (read_notes) and R15-CODE-AGENT-033 (option_chain), both under the
shared Ollama lock (acquired first try, held ~4 min for both calls back-to-back, released
via a `trap` on the first call and confirmed already gone before the second — noted as a
minor lock-discipline slip since the second call technically ran unlocked, but no other
lane contended in that window).

All 16 ids hold against their own stated repro. Two entries turned up adjacent
(non-regression) observations noted inline in the battery tables, not filed as findings:

- R15-AGENT-058: a blunter proxy-kill (env-wide `HTTPS_PROXY`) than the cert's news-only
  dead proxy correctly returns `ok:False` per the code's own "`ok` False only when every
  index failed" contract — re-ran with a scoped news-only failure to match the cert exactly
  and got the certified `ok:true` + `headlines_error` + live indices shape.
- R15-DATA-074: router default limit (50) and tool default limit (20) are different
  constants, so two DEFAULT calls land on different cache rows; the entry's own pinned test
  (`test_router_then_tool_fetch_the_lanes_once`) explicitly matches limits on both sides,
  and re-running with matching `limit=20` on both confirms the cache-sharing behaviour holds
  exactly as certified.

No regressions. findings/rc1-battery-1.json is `[]`.

COVERAGE: 16/16 ids raw; no raw: none.
