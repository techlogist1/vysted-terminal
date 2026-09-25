# RC1 owner-drive — panels-layouts

Worker: claude-sonnet-5 (label `rc1-drive-panels-layouts`). Candidate
`4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`. Reads against the shared candidate sidecar
`127.0.0.1:52152` (+ MCP `:52153`/`:52154`); writes against my own isolated sidecar
`127.0.0.1:52323`, data dir `rc1-data-rc1-drive-panels-layouts` (a `cp -R` of
`rc1-seed-data`, keyless).

Method: re-drove the group scope (`panels-layouts` in
`docs/redesign/verification/r15/tooling/PROMPT_surface_s2.md`, OWNER-DRIVE section) against
the census baseline in `surface/panels-layouts/` (`COVERAGE.json`, `EVIDENCE.md`,
`P-*` files). Cross-referenced the register
(`docs/redesign/verification/vysted-r15-register.json`) for entries tagged to this group's 9
census findings (`SURF-PANELS-LAYOUTS-1..9`): 8 are `fixed` (`R15-DATA-011/029/038/064/065/066/
067`, `R15-UI-053`), 1 is `open` (`R15-UI-077`, low). Drove every fix directly at the route
each finding's repro used, plus a light re-check of the write-path (workspace save/load edge
cases) and a side-effect check (analyst ratings, which shares the earnings/news symbol-resolver
fix). Rows not tied to a register fix or the trading-scope change were carried forward
unchanged from census (not re-driven this pass — no reason to expect drift).

Evidence: `docs/redesign/verification/r15/surface/panels-layouts/rc1/` (raw response bodies +
`rc1-http-log.txt`). Full row-by-row: `docs/redesign/verification/r15/surface/panels-layouts/
rc1/COVERAGE.json` (32 rows, same shape as census).

## Scored table — census → rc1 deltas

| Row | Census | RC1 | Delta | Evidence |
|---|---|---|---|---|
| panel-chart | broken | **ok** | fixed | 30m SPY/RELIANCE.NS: 286 bars each (was 0 for every symbol) |
| charts-timeframe | broken | **ok** | fixed | same fix, duplicate row for the same 2 defects |
| panel-watchlist | broken | **ok** | fixed | own-sidecar cold 20-name IN batch 87.7s (throttle unchanged), warm repeat 0.01s (EOD-cached — the 5s-poll starvation is gone) |
| panel-news | broken | **ok** | fixed | BDL -> "Bharat Dynamics shares rise 2%..." (was Flanigan's Enterprises) |
| panel-macro | broken | **ok** | fixed | IMF catalog 10 entries incl. 2 India series; `/macro/WEO%2FIND.NGDP_RPCH.A?provider=imf` -> 200, real data |
| panel-sec-filings | broken | **ok** | fixed | same accession `0000320193-25-000079`: 2 sections / 20,000 chars, 9 insider Form-4 rows (was 0/0) |
| panel-earnings-calendar | broken | **ok** | fixed | JPM/TSLA `fiscal_period` now `null` (was wrong "Q4 2026"); INFY estimates now INFY.NS, one consistent INR currency (was USD EPS beside INR revenue) |
| panel-analyst-ratings | broken | **ok** | fixed (bonus, same root cause) | RELIANCE.NS ratings now 200 with a real consensus/target (was dead for every IN symbol, COD-mdp-1-3) |
| panel-option-pricer | broken | **ok** | fixed | panel defaults: binomial gamma 1.004x BS (was 1.39x); 201 steps gamma 0.0188 (was exactly 0); theta -40.43 (was positive-sign bug) |
| panel-yield-curve | partial | **broken** (unchanged) | none — confirmed still open | dup 10y pillar -> bare 500, no CORS header (R15-UI-077 register status: open, low) |
| layouts-workspace-save-load | partial | **ok** | fixed (2 of 3 edge cases) | `Research: X` now 200/saved (was 400); 300-char name now honest 400 "too long to save" (was 500); round-trip clean. Corrupt-file-listed-but-404 (COD-wl-8) still reproduces — pre-existing code-critique item, not re-filed |
| panel-broker-connect | NOT TESTED | **removed_with_feature** | scope change | trading removed (D81); no `src/modules/*broker*` on candidate |
| panel-broker-order-entry | NOT TESTED | **removed_with_feature** | scope change | same |
| panel-audit-log | partial | **removed_with_feature** | scope change | order-audit-only viewer removed with the feature; no `src/modules/*audit*` on candidate |
| all other rows (17) | as census | **unchanged, carried forward** | none | not tied to a register fix or the D81 scope change; not re-driven this pass |

## Notes

- No regressions: every census `broken` row this pass touched is now `ok`, backed by a direct
  re-probe of the same repro the census finding used (mostly the same symbol/accession/params).
- No new defects: one transient upstream 502 on `INFY` earnings estimates ("Too Many Requests"
  from Yahoo, per the sidecar log) resolved to 200 on retry 15s later — logged as an environment
  artifact of the shared-run's concurrent yfinance load, not filed.
- `panel-earnings-calendar`'s default (no-watchlist) `/earnings/upcoming` returned 0 events on
  both the shared and my own sidecar, where the census description implies a populated 10-US-name
  default (WLD-T-7, not one of the 9 tracked findings). Not confirmed as a regression under this
  budget (could be a provider/calendar-window state at test time) — flagged for the lead, not
  scored.
- Observed but not filed: the TCS.NS Yahoo news feed carries some tangential AI-industry items
  (Rezolve AI, a Porsche/MHP deal that does name TCS) alongside on-topic ones — every URL
  resolves through the correctly-suffixed `TCS.NS` feed, so this reads as Yahoo's own per-symbol
  RSS editorial mix, not a symbol-resolution bug; insufficient evidence to file as a defect.
- `R15-UI-077` (yield-curve duplicate-pillar 500) is the one register item still `open`;
  re-verified unchanged, exactly matching the census repro (bare 500, no
  `access-control-allow-origin` header) — no regression, no new information.

## Sidecar

Own sidecar stopped: sleep pid 83129 had already exited on its own; killed the worker pid 83132 directly (own port/process). Port 52323 confirmed free after.
