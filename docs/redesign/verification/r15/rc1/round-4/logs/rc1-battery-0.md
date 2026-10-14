# rc1-battery-0 — REGRESSION BATTERY shard 0 (batch-5 + batch-12), round 4

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, verified: `git -C .../rc1-round-4-cand rev-parse HEAD` matched.

Sidecar: booted from the candidate's `sidecar/` source on port 52340, data dir
`.../rc1-round-4-data-rc1-battery-0` (copied from `rc1-round-4-seed-data`), sleep-pid 61254
(worker 61255). Reused for all three sets, stopped at end (`kill 61254`).

## set-15 (batch-5/W1-india-disclosures-agent-surface) — 12 ids, all `holds`
R15-DATA-020, R15-DATA-023, R15-DATA-024, R15-DATA-025, R15-DATA-056, R15-AGENT-060,
R15-AGENT-062, R15-AGENT-058, R15-CODE-RESEARCH-001, R15-DATA-074, R15-DATA-026, R15-AGENT-020.
Mix of live curl against the isolated sidecar (deals/corporate-actions/shareholding/
announcements/fundamentals endpoints), in-process candidate-venv calls to the agent-tool
functions directly (`price_data._price_data`, `market_overview._market_overview` with
`news_provider.fetch_news` monkeypatched to raise, matching the batch's "dead proxy" setup),
and source-code verification for the two entries that are pure code fixes
(`_clamp`/wall-budget schema, `get_announcements_cached` cache routing) plus one frontend/
runtime capability (R15-AGENT-020: `read_notes` + `captureAgentContext`'s `__notes__`) where
the pinning vitest exists but was not re-run here (heavy lane's job; no GUI/full agent loop
available in this shard).

## set-57 (batch-12/W2-screener-ordering + docs drift) — 3 ids, all `holds`
R15-DATA-043 (screener mixed-currency ranking + coverage note, both the original repro and the
fresh case matched exactly), R15-DOCS-018 (CURRENT_STATE.md preference-order + rank table
matches provider_registry.py verbatim; live fundamentals calls both served by yfinance,
matching the cert's noted nit), R15-DATA-112 (MANIKA's null market_cap sorts last in BOTH
directions).

## set-62 (batch-12/W7-instrument-region freshness) — 1 id, `holds` with a timing caveat
R15-UI-090: today is Sunday 02:01 IST — no exchange is open anywhere, so the cert's exact
"closed-US-quote reads live during NSE hours" live case could not be forced. What was verified
live: freshness is identical across `X-Vysted-Region: IN` vs `US` for every symbol tested
(NSEI/BSESN/NSEBANK/CNXIT/INDIAVIX/AAPL), consistent with the source fix
(`_label_freshness` → `instrument_region(quote.symbol, ...)`, never the session region) —
matches the certified fix exactly on inspection.

## Findings
None. No regressions found across the 16 assigned entries.

COVERAGE (all sets): 16/16 ids have raw output under `battery/raw/set-{15,57,62}/`; no id
without raw.
