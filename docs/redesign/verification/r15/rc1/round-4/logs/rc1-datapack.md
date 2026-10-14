# rc1-datapack — R15 gate round 4 log

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad confirmed at scratchpad worktree.
Own sidecar :52313 booted from candidate source (sidecar/.venv), data dir a fresh copy
of the keyless seed (rc1-round-4-data-rc1-datapack), env VYSTED_OPENBB_MCP_PORT=52153 /
VYSTED_SEC_EDGAR_MCP_PORT=52154 pointing at the shared read-only openbb/sec-edgar MCPs.

Minimal copy tree rc1-round-4-pack held scripts/r15/collect_battery.py +
docs/redesign/verification/r15/battery/manifest.json copied from the candidate. Ran
`python3 scripts/r15/collect_battery.py --port 52313 --force` from that copy, detached,
polled via Monitor (battery/collected/ file count) every ~20s. Yahoo circuit breaker was
open at run start (cooldown ~100s); collector's bounded park (max 120s) absorbed it, no
manual intervention needed. Total run ~15 minutes for 24 slots x 12 calls each
(2s min gap + circuit-breaker parking + live upstream latency, mostly the fundamentals
call at 3-14s).

All 24 names collected with complete:true, zero errors. Output copied from the pack's
battery/collected/ to this round's evidence dir, never touching the candidate's own
battery/collected/ (the census baseline, read-only).

Re-diff method: 42 fixed register entries whose raw_ids/title/repro name a battery
symbol, spot-checked directly against raw re-collected JSON; plus a structural diff
script (redig.py, in the session scratchpad) comparing fundamentals/quote/shareholding
scalar fields old-census-vs-new-recollection, excluding field_meta and price-like keys.

Findings: one regression (R15-DATA-008, SIFY currency mislabel — the register's own
batch-23 note already suspected this; live re-check confirms revenue_ttm/net_income_ttm
still serve INR-scale numbers under currency=USD with status=ok, though the newer
financial_currency field and P/S-P/B withholding are correctly in place). All other
spot-checked fixed entries (DATA-001, 004, 005, 006, 052, 115) confirmed holding.

Sidecar :52313 stopped at end of run (kill on its sleep pid).
