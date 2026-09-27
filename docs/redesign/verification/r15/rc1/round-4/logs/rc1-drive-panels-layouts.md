# rc1-drive-panels-layouts — gate round 4 log

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`, worktree
`/private/tmp/claude-501/.../scratchpad/rc1-round-4-cand`, sha confirmed via
`git rev-parse HEAD` before starting.

## Stack

- Own sidecar booted from `<cand>/sidecar` on `127.0.0.1:52323` (sleep pid 71382, sh
  wrapper 71380, worker pid 71383), data dir a fresh `cp -R` of `rc1-round-4-seed-data`
  into `rc1-round-4-data-panels-layouts`, pointed at the shared read-only MCP pair
  `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154`. `/health` -> 200
  in <6s.
- Reads went to the shared stack `127.0.0.1:52152` (candidate source, already up).
  Writes (workspace save) and compute-only quant POSTs went to my own `:52323`.
- Prior round-4 attempt for this role: none found (surface/panels-layouts/rc1/round-4/
  and rc1/round-4/{drives,findings,logs}/*panels-layouts* did not exist before this run).
  Started fresh, read round-3's drive (`rc1/round-3/drives/panels-layouts.md`) and the
  census `EVIDENCE.md`/`COVERAGE.json` first.

## Method

Read `EVIDENCE.md` (census, 9 findings) and round-3's `drives/panels-layouts.md`
(14 register-fixed rows re-verified live, all held, one open-low confirmed still open)
first. Since round 3, batch-27 fixed two items touching this group per the lead note:
R15-DATA-117 (ADR price-to-book mixed-currency) and R15-LEAD-040 (resolver pool). This
round targeted: (1) fresh verification of those two new fixes, (2) a regression spot
of the highest-severity round-3-held items (not the full 14 -- time-boxed), (3)
re-confirmation of the one open-low (R15-UI-077), (4) filling round-3's `NOT TESTED`
gaps this budget allowed (backtest strategies list, greeks dashboard, bond pricer,
SEC insider detail, agent-builder tool-ids). `panel-context-publishers` (a vitest
run) and the arrange-templates/layout pure-frontend logic stayed NOT TESTED --
frontend-only, no sidecar surface, same as round 3's carry-forward.

Schema note: several routes needed correcting against the actual pydantic models
(`/quant/option/price` not `/quant/option-price`, `/sec/filings/{accession}/sections`
not `/sec-filings/...`, `/workspace` not `/workspaces`, full field sets for
`YieldCurveRequest`/`OptionPricingRequest`/`BondPricingRequest`/`GreeksRequest`) --
corrected from `sidecar/models/quant.py` and `sidecar/routers/*.py` reads before
re-sending; the first 422/404 attempts are not counted as findings (own request
error), only the corrected send's result is scored.

## Rows driven (raw file per row, see COMMON.md naming)

01-03: R15-DATA-117 fix check (fundamentals TSM/HDB withheld, AAPL control unaffected)
04: R15-UI-077 still-open confirm (yield curve duplicate pillar)
05: R15-LEAD-040 fix check (code read: dedicated `_RESOLVE_POOL`, 4 workers)
07: backtest strategies list (not tested r3)
08: R15-DATA-064 regression (chart 30m AAPL)
09-10: R15-DATA-011 regression (binomial gamma at 200/201 steps, no parity flip; theta correct sign)
11, 11a, 11b: R15-DATA-038 regression (SEC sections real text; filings list; insider rows)
12: R15-DATA-028/029/067 regression (earnings upcoming IN, .NS names present, fiscal_period honest-null)
13-15: news relevance drive (INFY.NS defect found; AAPL control; RELIANCE.NS empty)
16-17: workspace save colon-name / 300-char regression (both hold)
18-19: greeks dashboard / bond pricer (not tested r3, both ok, cross-checks binomial gamma)
20: R15-UI-003 backend-half regression (56 tool ids)

## Sidecar stop

Stopped at end of drive by killing sleep pid 71382 (own dedicated process, port
52323, never the shared `:52152-54` stack). Confirmed via `/health` timeout after
kill.
