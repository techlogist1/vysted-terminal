# OPP-LEDGER verify — session-2 verification pass

**Worker model:** `claude-sonnet-5` · **Date:** 2026-09-23 · **HEAD:** branch
`004-r4-experience-rebuild`. Verification-only pass on the seven Tier-A entries in
`census/OPPORTUNITY_LEDGER.md` (`OPP-1`…`OPP-7`) — re-checked every cited `file:line` against the
current code and every entry against the operator's 23 Sep 03:46 IST trading-removal decision
(`stage0/RECONCILE_MANIFEST.md` scope-change overlay). No raw findings emitted (opportunities are
not defects). `census/world-table-stakes.json` not reopened — nothing found factually wrong in it.

One line per Tier-A entry: id, verdict (held / corrected / struck), reason.

- **OPP-1** — The trigger layer, and the thesis watcher on top of it — **held**. All nine cited
  `file:line`s (`run_manager.py`, `runs_store.py`, `budget_guard.py`, `runs.py:63-126`,
  `builtin.py:321-336`, `workflow.ts:180`, `disclosures.py:36-40`, `catalog.py:1309,946,1374`,
  `workflow.py:38`) match verbatim at current HEAD; grep for `APScheduler`/`croniter`/
  `CronTrigger`/`schedule.every` across `sidecar/` returns zero hits, so no trigger/scheduler
  capability has shipped since filing. Composition (portfolio_add_position, get_portfolio,
  write_note, disclosures feed, workflow engine) has no broker dependency — not on the
  trading-removal surface.

- **OPP-2** — The lakh/crore scale witness — **held**. `range_check.py:1-20`,
  `market_cap_witness.py:1-20`, `extract.py:75,86-87`, `semantics.py:603-607` all match verbatim.
  No third (scale-vs-magnitude) witness exists in `sidecar/services/research/`. No broker
  dependency.

- **OPP-3** — Make the trust machinery visible — **corrected**. Deliverable (a), the "two sources
  disagree — here are both" card, is **already shipped**: `src/modules/research/
  brief-blocks.tsx:129-176` (`ConflictLine`/`conflictLines`) renders exactly this, tiered by
  `conflict_kind` per `types/brief.ts:93-108`; it landed in commit `38d08e6` (R10) and was refined
  by `ac694ea` (R13), both predating this ledger's 2026-09-19 filing — the original entry missed
  code that already existed when it was written. Corrected in place: score's proximity axis
  dropped 3→2, size S–M→S, remaining scope narrowed to deliverables (b) per-figure source
  attribution on metric cards and (c) the public benchmark page. No broker dependency in what
  remains.

- **OPP-4** — Guidance vs delivery: the concall tracker nobody ships — **held**.
  `catalog.py:528,537,547,655,1177` all match verbatim; zero `transcript` hits anywhere in
  `catalog.py`, so `WLD-T-6` still blocks it exactly as the entry states. No broker dependency
  (earnings calls, analyst history, corporate announcements).

- **OPP-5** — One-click, keyless broker connect — **struck**. This entry's entire subject is
  connecting a broker account via a keyless MCP path. Operator decision 23 Sep 03:46 IST removed
  trading from the product; per `stage0/RECONCILE_MANIFEST.md` the whole `brokers-adapters`
  partition (adapters/routes/panels/plugins/orders store) is `removed_with_feature`, and per the
  session-2 scope note an opportunity whose subject "exists only to connect a broker" is dropped,
  never filed as a defect or a build target. Underlying code citations (`openbb_mcp.rs`,
  `sec_edgar_mcp.rs`, `brokers.py:415`, `kite.py:13-17`) are still accurate at this HEAD, but the
  code itself sits on the removal surface and will not survive the removal batch. Heading prefixed
  `[STRUCK]`, entry kept (not deleted) per the ledger's own instruction that the record of what was
  considered matters.

- **OPP-6** — User-addable MCP servers — **corrected**. The broker-MCP examples cited as
  motivating evidence (Zerodha, Upstox ×2, Angel One, Dhan, Groww, 5paisa, INDmoney, the
  multi-broker server) are on the trading-removal surface and struck from the evidence list. The
  opportunity's actual subject — a user-config'd MCP server list, a general platform capability —
  is not itself a broker-connect feature and is not on the removal surface; it survives on its
  remaining non-broker evidence (~8 screener.in scrapers, Fiscal.ai's commercially-validated
  REST+MCP tier). Code check: `mcp.py:28,44` still match verbatim (`GET /mcp/status`,
  `GET /openbb-mcp/status`); no user-config'd or third route exists.

- **OPP-7** — Portfolio-aware research — **corrected**. `broker_portfolio` (`catalog.py:911`,
  handler at `sidecar/services/agent_tools/broker_portfolio.py:1-41`) reads a REAL
  connected-broker account via `services.brokers.registry` — on the trading-removal surface along
  with the rest of `brokers-adapters`; struck from evidence, along with the FR-041
  `broker_reads.py` citation. `get_portfolio` (`catalog.py:946`, `domain="portfolio"`) reads the
  user's **local, manually-tracked** portfolio, which the 23 Sep scope note explicitly keeps in
  scope (tracked holdings/cost bases/P&L/CSV/notes/watchlists) — this alone was always sufficient
  evidence for the opportunity (threading local position/cost-basis into research context), so the
  entry holds on corrected evidence, arguably strengthened since "local-first private portfolio
  reasoning" is now the entire mechanism instead of one of two paths.

**Rollup:** 3 held (OPP-1, OPP-2, OPP-4) · 3 corrected (OPP-3, OPP-6, OPP-7) · 1 struck (OPP-5) ·
0 raw findings emitted · 0 refute stage (this item skips it per spec).
