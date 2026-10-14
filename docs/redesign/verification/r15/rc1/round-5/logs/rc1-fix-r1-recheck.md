# rc1-fix-r1-recheck log
- 16:31 IST: the candidate worktree rev-parse printed 633f844071d972b337f4c3526d86555c80df0568 (OK). Read the finding, fix-r1/PLAN.md, INTEGRATION.md and the 38a64fda diff.
- Seed data copied to scratchpad/rc1-round-5-data-rc1-fix-r1-recheck. Sidecar started from the candidate source on :52336 (sleep pid 86439); /health ok, version 0.8.0.
- Fetched /sec/insider for AAPL, MSFT, NVDA and TSLA (plus TSLA form=all -> 422 by design, and JPM form=5 -> 0 rows) into fix-r1/recheck/.
- Rendered the candidate InsiderTradingTable on each live payload in jsdom from a git-archive scratch copy: 81 rows, 0 coloured, 0 blank, note present, 0 console errors. The sec vitest dir passed 24/24.
- 16:33 IST: sidecar stopped (kill 86439). RECHECK.md written. Verdict: rc1-drive-panels-layouts:1 fixed.
