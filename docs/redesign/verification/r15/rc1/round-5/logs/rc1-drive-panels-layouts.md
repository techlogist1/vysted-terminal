# rc1-drive-panels-layouts — working log (gate round 5)

Model: claude-sonnet-5. Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (confirmed via
`git rev-parse HEAD` in the round's cand worktree before driving).

1. Checked for a prior round-5 attempt at this label — none existed; started fresh (this is
   the first panels-layouts entry under `r15/rc1/round-5/`).
2. Read `PROMPT_surface_s2.md` (OWNER-DRIVE, panels-layouts group), `COMMON.md`,
   `ISO_STACK.md` boot recipe.
3. Copied the round's seed data dir to `rc1-round-5-data-panels-layouts`, booted the candidate
   sidecar from source on `127.0.0.1:52323` per the exact `ISO_STACK.md` recipe (MCP env vars
   set, stdin held via `sleep 86400 | ...`), sleep pid 35505. Health-checked before driving.
4. Read the census baseline (`surface/panels-layouts/EVIDENCE.md`, `COVERAGE.json`) to know
   what to re-drive rather than re-derive from scratch, and cross-referenced the register
   (`vysted-r15-register.json`) for each census headline finding's fix status before probing,
   to target live checks at what actually changed.
5. Drove all 20 panels+layouts skeleton rows: chart (30m timeframe + indicators), watchlist
   (cold/warm IN batch timing), news (bare IN ticker), equity-overview (keyless narrative),
   agent-builder (full CRUD + validation, own sidecar), backtest (strategies, a real run, an
   out-of-range param, own sidecar), macro (IMF catalog+series), SEC filings (list, sections,
   insider), earnings (upcoming, INFY history), analyst ratings (history/price-target/
   individual for RELIANCE.NS and AAPL), option pricer (binomial vs Black-Scholes at 200/201
   steps), greeks dashboard, bond pricer, yield curve (duplicate pillar), workspace save/load
   (own sidecar: basic, colon name, 300-char name, list, missing, round-trip, hand-corrupted
   file), and three existing vitest files for the pure-function rows (layout-templates,
   panel-context-publishers, workspace serialize/deserialize).
6. Several first-attempt calls 422'd on a guessed request shape (`/quant/option/price`,
   `/quant/option/greeks`, `/quant/yield-curve`, `/custom-agents`, `/news`) — read the actual
   Pydantic models / router / api.ts source each time and re-issued the corrected call; the
   corrected call's file is what's cited in COVERAGE.json/the drive doc.
7. Cross-checked every "now ok" result against the register before crediting a fix id, and
   checked the register before filing anything that looked new (yield-curve duplicate pillar
   turned out to be the already-open R15-UI-077, exactly; the corrupt-workspace 404 wording
   turned out to be an already-documented residual on the fixed R15-DATA-090) — neither
   re-filed as new.
8. One genuine new finding survived: the SEC Insider tab renders every filing-level row's
   reporter/shares/price/value fields blank and colours a `null` Direction green
   (`text-positive`) — R15-DATA-038 fixed the row *count* but not this rendering gap. Filed as
   `rc1-drive-panels-layouts:1`, medium.
9. Wrote `surface/panels-layouts/rc1/round-5/COVERAGE.json` (all 20 rows resolved to
   ok/partial/broken/NOT TESTED/NEEDS-GUI), `rc1/round-5/findings/rc1-drive-panels-layouts.json`
   (1 finding), `rc1/round-5/drives/panels-layouts.md` (scored table + deltas).
10. Stopped the own sidecar (`kill 35505`), confirmed `/health` no longer answers.

No LLM lane was needed for this group — every row is API- or code-level, and the census
already drove the agent-layer surfaces (arrange-via-agent, agent-completable host actions)
that belong to composer-chat, not panels-layouts.
