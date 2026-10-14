# Gate 8 grep dumps — kept out of git (GitHub file-size limit)

The round-4 gate8 role wrote two raw grep dumps into this directory. GitHub rejected the push (GH001: `grep-docs.txt` 111.75 MB is over the 100 MB limit; `grep-docs-classified.tsv` 64.97 MB over the 50 MB warning). Both files were moved, unchanged, to the session scratchpad (`round-4-gate8-large/`) and are summarised here; GATE8.md carries the classification conclusion (0 product-surface hits, every hit classified).

## grep-docs.txt

- size: 117180184 bytes; lines: 193123; sha256: b06a4a9274fcec280ba867b30fd77a4cb917dd8796de6133db5a114b0d008f1a
- first lines:
```
docs/BLUEPRINT.md:20:**v1.0 scope:** 20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap), 12 AI agents, full plugin architecture, MCP server, node editor for workflow automation, backtest engine. Trading (broker connectivity, order placement, simulated accounts) was removed perma
docs/BLUEPRINT.md:65:| Trading | None — no broker connectivity, order placement or simulated account (D81, operator, 23 Sep 2026) |
docs/BLUEPRINT.md:206:| Warren Buffett | Value investing — business quality, margin of safety |
docs/BLUEPRINT.md:226:  "philosophy": "Value investing, margin of safety, business quality",
docs/BLUEPRINT.md:280:27. Position tracking + P&L attribution (local SQLite, manually tracked holdings — no broker connection)
```

## grep-docs-classified.tsv

- size: 68122588 bytes; lines: 193123; sha256: f6a8226a31d14a4a061007899fbb41a701c119df640289af5f02e982ee4823d3
- first lines:
```
historical	docs/BLUEPRINT.md:20:**v1.0 scope:** 20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap), 12 AI agents, full plugin architecture, MCP server, node editor for workflow automation, backtest engine. Trading (broker connectivity, order placement, simulated accounts) was re
historical	docs/BLUEPRINT.md:65:| Trading | None — no broker connectivity, order placement or simulated account (D81, operator, 23 Sep 2026) |
false_positive	docs/BLUEPRINT.md:206:| Warren Buffett | Value investing — business quality, margin of safety |
false_positive	docs/BLUEPRINT.md:226:  "philosophy": "Value investing, margin of safety, business quality",
historical	docs/BLUEPRINT.md:280:27. Position tracking + P&L attribution (local SQLite, manually tracked holdings — no broker connection)
```
- last-column (classification) counts:
  - 40966  docs/redesign/verification/r15/rc1/round-3/gate8/grep-docs.t
  - 5435  docs/redesign/verification/r15/rc1/verifier/g2/rg-docs.txt:1
  - 5317  docs/redesign/verificatio
  - 3569  docs/redesign/verification/r15/rc1/verifier/r2/rg-docs.txt:1
  - 2485  docs/redesign/verification
  - 1775  docs/redesign/verification/r15/rc1/verifier/g2/safety-surfac
  - 1736  docs/redesign/verification/r15/rc1/round-3/verifier/gate8/sa
  - 1683  docs/redesign/verification/r15/census/intent/ledger-blueprin
  - 1504  archived / verification evidence 
  - 1495  docs/redesign/verification/r15/census/intent/ledger-pdd-read
  - 1175  docs/redesign/verification/r15/census/code/brokers-adapters.
  - 1172  archived / verification evidence / da
  - 1117  docs/redesign/verification/r15/census/raw/code-brokers-adapt
  - 1111  docs/redesign/verification/r15/rc1/verifier/r2/rg-docs.txt:9
  - 1103  docs/redesign/verification/r15/rc1/verifier/g2/rg-docs.txt:9
  - 1099  docs/redesign/verification/r15/rc1/verifier/g2/rg-docs.txt:2
  - 1098  docs/redesign/verification/r15/rc1/verifier/r2/rg-docs.txt:2
  - 1069  docs/redesign/verification/r15/rc1/verifier/g2/rg-docs.txt:8
  - 1064  docs/redesign/verification/r15/rc1/verifier/r2/rg-docs.txt:3
  - 927  docs/redesign/verification/r15/rc1/verifier/g2/rg-docs.txt:3
  - 924  docs/redesign/verification/r15/stage0/SUBSYSTEM_PARTITION.js
  - 836  docs/redesign/verification/r15/rc1/round-3/verifier/gate8/rg
  - 810  docs/redesign/verification/r15/census/CODE_PARTITION.json:11
  - 798  docs/redesign/verification/r15/rc1/verifier/r2/rg-docs.txt:4
  - 798  docs/redesign/verification/r15/surface/route-fuzzer/results.
- rows whose path is NOT under docs/redesign/verification/r15 (the product-surface rows; first 400):
```
historical	docs/BLUEPRINT.md:20:**v1.0 scope:** 20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap), 12 AI agents, full plugin architecture, MCP server, node editor for workflow automation, backtest engine. Trading (broker connectivity, order placement, simulated accounts) was re
historical	docs/BLUEPRINT.md:65:| Trading | None — no broker connectivity, order placement or simulated account (D81, operator, 23 Sep 2026) |
false_positive	docs/BLUEPRINT.md:206:| Warren Buffett | Value investing — business quality, margin of safety |
false_positive	docs/BLUEPRINT.md:226:  "philosophy": "Value investing, margin of safety, business quality",
historical	docs/BLUEPRINT.md:280:27. Position tracking + P&L attribution (local SQLite, manually tracked holdings — no broker connection)
historical	docs/BLUEPRINT.md:390:Vysted Terminal has no brokerage connection and does not place orders. It is
historical	docs/BLUEPRINT.md:400:- **Vysted Terminal is not a broker.** It has no order-placement path, no
historical	docs/BLUEPRINT.md:401:  simulated account, and no broker relationship of any kind.
historical	docs/BLUEPRINT.md:410:portfolio, notes, screens, layouts, settings) — never a broker order, since
historical	docs/BLUEPRINT.md:511:### Phase 5 — Broker & Trading Plugins
historical	docs/PHASE_10_HANDOFF.md:3:> **Historical.** Broker integrations were removed permanently (D81, 23 Sep 2026).
historical	docs/PHASE_10_HANDOFF.md:4:> Vysted has no broker connectivity, order placement or simulated account. §3 below
historical	docs/PHASE_10_HANDOFF.md:5:> (Kite/`/brokers`/`broker_portfolio`) describes a surface that no longer exists — see
historical	docs/PHASE_10_HANDOFF.md:6:> `docs/BROKER_INTEGRATIONS.md`. The rest of this handoff is otherwise historical record.
historical	docs/PHASE_10_HANDOFF.md:13:a real broker-integrations hub with Kite Connect read-only, retires the
historical	docs/PHASE_10_HANDOFF.md:20:  (the main sidecar rebuilt with the copilot + broker changes) · eslint ·
historical	docs/PHASE_10_HANDOFF.md:24:  (`sidecar/models/audit_log.py`, `sidecar/models/kill_switch.py`,
historical	docs/PHASE_10_HANDOFF.md:25:  `src-tauri/src/kill_switch.rs`, `sidecar/services/broker_base.py`,
historical	docs/PHASE_10_HANDOFF.md:83:on early teardown; KillSwitch listener leak + a visible fire-failure banner;
historical	docs/PHASE_10_HANDOFF.md:107:  execute on the host on `tool_use`; `propose_order` only prepares a
historical	docs/PHASE_10_HANDOFF.md:121:## 3. Broker + integrations hub — how to connect Kite (Phase E, headline)
historical	docs/PHASE_10_HANDOFF.md:123:> **Historical.** Broker integrations were removed permanently (D81, 23 Sep 2026).
historical	docs/PHASE_10_HANDOFF.md:124:> Vysted has no broker connectivity, order placement or simulated account. None of
historical	docs/PHASE_10_HANDOFF.md:125:> the Kite flow, `/brokers/*` routes or `broker_portfolio` tool described below
historical	docs/PHASE_10_HANDOFF.md:126:> exist anymore — see `docs/BROKER_INTEGRATIONS.md`.
historical	docs/PHASE_10_HANDOFF.md:143:**What you get:** read-only positions/holdings/P&L (equity now = `margins.net`,
historical	docs/PHASE_10_HANDOFF.md:145:wrong/invisible before). New `GET /brokers/{id}/positions|holdings|margins`,
historical	docs/PHASE_10_HANDOFF.md:146:`POST /brokers/{id}/disconnect`, and a 419 "reconnect" cue when the daily token
historical	docs/PHASE_10_HANDOFF.md:147:expires. The `broker_portfolio` agent tool lets the copilot analyse your **real**
historical	docs/SAFETY_ARCHITECTURE.md:4:> permanently — no broker connectivity, order placement or simulated account
historical	docs/SAFETY_ARCHITECTURE.md:13:Vysted Terminal has no brokerage connection. It cannot place, stage or
historical	docs/SAFETY_ARCHITECTURE.md:14:simulate a trade, and it has no simulated account. What it _can_ do is act
historical	docs/SAFETY_ARCHITECTURE.md:22:- **Cannot**: connect to a broker, place/stage/simulate an order, or read or
historical	docs/SAFETY_ARCHITECTURE.md:23:  write a simulated brokerage account. There is no code path anywhere in the
historical	docs/SAFETY_ARCHITECTURE.md:76:`catalog.FORBIDDEN_TOOL_SUBSTRINGS` (`place_order`, `submit_order`,
historical	docs/SAFETY_ARCHITECTURE.md:80:order/broker/margin/trade/paper/kill-switch/audit-shaped id on the catalog,
historical	docs/SAFETY_ARCHITECTURE.md:117:  (`audit_orders`) existed only to record order placement; it went with the
historical	docs/SAFETY_ARCHITECTURE.md:123:  kill switch any more (§10) and no per-action pause; the available control
historical	docs/SAFETY_ARCHITECTURE.md:133:exclusively to gate broker order placement. The census that decided this
historical	docs/SAFETY_ARCHITECTURE.md:136:- the kill-switch bus's only subscriber was `BrokerAdapter.__init__`;
historical	docs/SAFETY_ARCHITECTURE.md:138:- nothing in the UI ever fired the kill switch or listened for its event;
historical	docs/SAFETY_ARCHITECTURE.md:142:gate, so they were deleted rather than kept as dead weight: the broker
historical	docs/SAFETY_ARCHITECTURE.md:143:adapters and registry, `broker_base.py`, `kill_switch.py`,
historical	docs/SAFETY_ARCHITECTURE.md:145:`static_ip_detector.py`, the `/brokers/*` and `/safety/*` routers, the
historical	docs/SAFETY_ARCHITECTURE.md:148:broker-connect and order-review panels, and the OS-wide kill-switch
historical	docs/MCP_INTEGRATION.md:118:`price_bond`, `yield_curve_value`. No broker tool exists — Vysted has no
historical	docs/MCP_INTEGRATION.md:119:brokerage connection (D81, 23 Sep 2026).
historical	docs/README.md:30:| [BROKER_INTEGRATIONS.md](./BROKER_INTEGRATIONS.md) | Removal note — trading was removed permanently (D81, 23 Sep 2026)                               |
historical	docs/README.md:32:| [PHASE_10_HANDOFF.md](./PHASE_10_HANDOFF.md)       | Historical phase handoff (copilot + reskin) — its §3 broker/Kite content is superseded by D81   |
historical	docs/BROKER_INTEGRATIONS.md:1:# Broker Integrations
historical	docs/BROKER_INTEGRATIONS.md:3:Broker integrations were removed permanently (D81, 23 Sep 2026). Vysted has no
historical	docs/BROKER_INTEGRATIONS.md:4:broker connectivity, order placement or simulated account. Your manually
historical	docs/archive/PHASE_9_BUG_CATALOG.md:141:### Group H — Plugins / Brokers / Safety
historical	docs/archive/PHASE_9_BUG_CATALOG.md:146:| 77  | **PASS**                | `/brokers` → 200 with the 10-broker list (dhan disconnected/paper/readOnly:false + capabilities). Bad-creds GUI connect not driven (no live orders).                                                                   
historical	docs/archive/PHASE_9_BUG_CATALOG.md:147:| 78  | _not exercised_         | Broker paper↔live + read-only toggle.                                                                                                                                                                                  
historical	docs/archive/PHASE_9_BUG_CATALOG.md:150:| 81  | **PASS — S1**           | Kill-switch full cycle: fire → `fired:true` + per-broker ack times (dhan 1.7 ms…); reset **blocked without acknowledgment** (gate holds; returns 422 rather than the documented 400 — trivial); reset-with-ack → `{rese
historical	docs/archive/PHASE_9_BUG_CATALOG.md:151:| 82  | **PASS (partial) — S1** | Order proposal gate: unknown `proposal_id` → 404. Full AI-review-checkbox dialog needs a broker order proposal (paper-only/no-live constraint); gate architecturally enforced per SAFETY_ARCHITECTURE.md.              
historical	docs/archive/PHASE_9_BUG_CATALOG.md:152:| 83  | _not observed_          | First-launch ToS / per-broker disclaimer not seen (disclaimer ack is session-scoped; may have been acked on a prior boot of this data-dir).                                                                            
historical	docs/archive/PHASE_9_BUG_CATALOG.md:190:- **None NEW confirmed.** All safety gates HELD: kill-switch fire+ack-gated-reset (#81), order proposal 404 gate (#82), Tradesa read-only 405/401 (#88), no XSS/SQLi (adversarial). The only S1-flagged checklist items that remain _unverified_ are defe
historical	docs/archive/PHASE_9_BUG_CATALOG.md:194:1. **Audit Log Viewer unreadable — `/safety/audit-log` → 500 on all valid limits (#79).** Root-cause hypothesis: the append-only audit read path (reader connection `PRAGMA query_only`, or a query/serialization error on the `audit_orders` read) throw
historical	docs/archive/PHASE_9_BUG_CATALOG.md:206:- **Kill-switch reset-without-ack returns 422, docs say 400 (#81).** Gate still holds; trivial code/doc mismatch.
historical	docs/archive/PHASE_9_BUG_CATALOG.md:217:- DEFERRED setup: backtest SSE (#50–52), agent-builder CRUD (#48–49), Tradesa-configured data (#85–87), broker connect/mode (#77 connect/#78), disclaimer flow (#83), quant edge (#54–60 individual), node-editor graph (#73–75 behind untestable canvas)
historical	docs/archive/PHASE_9_BUG_CATALOG.md:223:The app is **functional and robust at its core**: the 5-panel cockpit renders live data, cmd+K opens every panel, the quant engine is fast and correct, sentiment-scored news works, portfolio P&L is correct, and **every safety gate held** (kill-switc
historical	docs/archive/PHASE_9_BUG_CATALOG.md:293:App relaunched to a clean, usable state: default 5-panel cockpit, watchlist reset to the 4 seed symbols (the 55 test symbols did **not** persist), fresh sidecar healthy (`0.8.0`, dynamic port — 58321 at write time, agents=12, openbb-mcp down per UC1
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:91:- **Layout:** `src-tauri/` drops "kill-switch" from its one-line description (no
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:92:  `kill_switch.rs` any more). `plugins/` becomes "(openbb-mcp, yfinance, vysted-news,
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:93:  vysted-lenses, example)" — the `brokers` entry is gone.
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:96:  > ⚠️ The redesign vision **changes some locked decisions** (e.g. broker order execution
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:102:  > Trading (broker connectivity, orders, simulated accounts) was removed permanently by
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:106:  grep check, kill-switch, read-only trading-wrapper layers) with one line: "§6.5
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:117:- **Gotchas → Broker & credentials:** rename the section to "Gotchas → Credentials." Delete
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:118:  the "Kite Connect read-only login runs in the SIDECAR" bullet and the "Granular broker
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:119:  reads" bullet in full — no broker exists to read from. In the BYOK secrets bullet, change
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:125:- **Reference docs:** drop the `docs/BROKER_INTEGRATIONS.md` mention from the
historical	docs/redesign/CLAUDE_MD_PROPOSAL.md:127:docs/BROKER_INTEGRATIONS.md, docs/DESIGN_SYSTEM.md` list (it is now a one-paragraph
historical	docs/redesign/R9_TRACK_PROPORTION_REPORT.md:61:- [x] **Broker connect + order entry** (visual only, §6.5 untouched) — status/
historical	docs/redesign/R9_TRACK_PROPORTION_REPORT.md:64:      Order-entry was already on the h-8 rung. `broker-connect-1280.png`,
historical	docs/redesign/R9_TRACK_PROPORTION_REPORT.md:123:   broker reads, backtest results/equity curve) — empty-state proportions are
historical	docs/redesign/R9_TRACK_PROPORTION_REPORT.md:138:| `52bd93f` | broker-connect visual                       |
historical	docs/redesign/REBUILD_R3_SPEC.md:58:  `types/safety.ts`, `types/broker.ts`, the safety/broker/audit/kill-switch models
historical	docs/redesign/REBUILD_R3_SPEC.md:59:  (`sidecar/models/{safety,broker,audit_log,kill_switch}.py`),
historical	docs/redesign/REBUILD_R3_SPEC.md:60:  `sidecar/services/broker_base.py`, `src-tauri/src/kill_switch.rs`,
historical	docs/redesign/REBUILD_R3_SPEC.md:66:- **Brokers read-only.** GET-only routes, duck-typed to `account_info()` /
historical	docs/redesign/REBUILD_R3_SPEC.md:252:| `src/modules/integrations/ConnectCard.tsx` (whole)      | old broker ConnectCard, superseded by `broker-connect` + Marketplace | confusing | **Delete** (verify `broker-connect` doesn't import it) |
historical	docs/redesign/REBUILD_R3_SPEC.md:672:  on tables). Kill-switch = stillness, red border, NO glow. Remove gradients on
historical	docs/redesign/REBUILD_R3_SPEC.md:765:7.  curl -s http://127.0.0.1:NNNNN/fundamentals/AAPL | python3 -m json.tool   # roe/margin/debt populated
historical	docs/redesign/R10_TRACK_SCREENER_BRIEF.md:53:shares_outstanding/roe/margins/debt_to_equity/growth/52wk, quote_* columns,
historical	docs/redesign/R7_TRACK_DATA_BRIEF.md:14:- NEVER touch: `types/plugin.ts`, `.github/`, `src-tauri/tauri.conf.json`, `LICENSE*`, `CLAUDE.md`, §6.5 safety files, broker code, `sidecar/app.py` (owned by another track), `sidecar/services/config.py` (owned by another track), `sidecar/services/s
historical	docs/CURRENT_STATE.md:11:> human-checkable ones** — live UX, populated visuals, and any BYOK/live-broker
historical	docs/CURRENT_STATE.md:19:> **Everything below this notice that describes brokers, orders, the kill
historical	docs/CURRENT_STATE.md:21:> capability that no longer exists.** D81 (operator Tier-4 sign-off, 23 Sep 2026) removed trading from the product permanently: no broker
historical	docs/CURRENT_STATE.md:22:> connectivity, order placement or simulated account exists anywhere —
historical	docs/CURRENT_STATE.md:23:> surfaces, agent tools, routes or docs. The kill switch and the append-only
historical	docs/CURRENT_STATE.md:88:>   pre-installed (yfinance + news keyless); the broker entries that shipped here
historical	docs/CURRENT_STATE.md:100:>   broker reads that shipped here (FR-042/SC-012) were removed with trading (D81).
historical	docs/CURRENT_STATE.md:109:> `types/plugin.ts` remained **byte-for-byte untouched**. (The safety/broker models
historical	docs/CURRENT_STATE.md:136:- **No broker layer.** Trading — broker connectivity, order placement, the
historical	docs/CURRENT_STATE.md:137:  simulated paper account, the kill switch, the append-only order audit log —
historical	docs/CURRENT_STATE.md:139:  the removal notice describes the broker layer as it existed before D81;
historical	docs/CURRENT_STATE.md:145:  broker plugins that used to exist in the tree are gone (D81), not merely
historical	docs/CURRENT_STATE.md:161:there is no kill-switch shortcut any more, D81). The Next.js frontend is a
historical	docs/CURRENT_STATE.md:225:(`keychain.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`) — `kill_switch.rs` was
historical	docs/CURRENT_STATE.md:311:| —                   | _(none — the broker and safety routes were removed, D81, 23 Sep 2026)_                     | No broker, order or kill-switch route exists     | see §0.x                                                                   |
historical	docs/CURRENT_STATE.md:433:seven broker plugins this section used to describe as dead-wired test
historical	docs/CURRENT_STATE.md:436:### 3.5 Broker layer — removed (D81, 23 Sep 2026)
historical	docs/CURRENT_STATE.md:438:No broker layer exists. See §0.x. The Kite Connect OAuth read-only path,
historical	docs/CURRENT_STATE.md:440:`margins`), and the Kite static-IP UX this section used to describe are all
historical	docs/CURRENT_STATE.md:447:only to gate broker order placement and was removed with the feature. What
historical	docs/CURRENT_STATE.md:451:broker or simulated-account path exists anywhere.
historical	docs/CURRENT_STATE.md:590:  `SettingsPanel`; one dialog drives any `IntegrationSpec`. There is no broker
historical	docs/CURRENT_STATE.md:609:agent cannot select** (`broker_portfolio`, this section's third example, is
historical	docs/CURRENT_STATE.md:690:any more — no broker connection exists to place one against (D81).
historical	docs/CURRENT_STATE.md:703:catalog.py`, the single source of truth per §0). No `broker_portfolio` or
historical	docs/CURRENT_STATE.md:704:`propose_order` tool exists any more (D81):
historical	docs/CURRENT_STATE.md:762:5. **No order, broker or simulated-account path exists anywhere** — pinned by
historical	docs/CURRENT_STATE.md:778:| Portfolio positions (manually tracked — no broker connection)                  | Sidecar    | SQLite `positions`             | `get_data_dir()/portfolio.db`                  |
historical	docs/CURRENT_STATE.md:781:There is no order audit log any more (D81); the append-only `audit_orders`
historical	docs/CURRENT_STATE.md:782:table and `audit_log.db` existed only to record order placement. A user who
historical	docs/CURRENT_STATE.md:799:per-broker namespace any more, D81). The `provider-keys` store tracks
historical	docs/CURRENT_STATE.md:838:| Trading (broker connectivity, orders, simulated account)                               | **Removed permanently (D81, 23 Sep 2026)** — not deferred, not dead code; deleted                             | §0.x; SAFETY_ARCHITECTURE        |
historical	docs/CURRENT_STATE.md:871:  There is no broker connectivity, order placement or simulated account to
historical	docs/CURRENT_STATE.md:880:  them (staged through the same trust gate). There is no broker connection
historical	docs/CURRENT_STATE.md:917:  (§5); there are no broker plugins left to decide the fate of (D81).
historical	docs/redesign/verification/R10_DEFECT_CATALOGUE.md:122:broker tools do unbounded network work. **Fix:** Team RUNTIME — per-tool-class
historical	docs/archive/PHASE_9.5_MORNING_REPORT.md:20:diff origin/main` empty for audit_log/kill_switch/broker_base/plugin.ts/
historical	docs/archive/PHASE_9.5_MORNING_REPORT.md:53:  JSON normalized to typed errors (sidecar-client/workspace); broker order-entry
historical	docs/archive/PHASE_9.5_MORNING_REPORT.md:112:   `test_safety_end_to_end.py` regenerates `kill-switch-benchmark.json` on every
historical	docs/redesign/INTEGRATION_NOTES_R7_PANELS.md:8:- `src/store/llm-providers.ts` — one label string: `"OpenRouter (broker)"` →
historical	docs/redesign/INTEGRATION_NOTES_R7_PANELS.md:12:  the sidecar registry DID still carry `"label": "OpenRouter (broker)"`, and
historical	docs/redesign/INTEGRATION_NOTES_R7_PANELS.md:15:  the broker label resurfaced at runtime regardless of the frontend fix. Fixed
historical	docs/redesign/INTEGRATION_NOTES_R7_PANELS.md:17:  `test_get_providers_returns_all` so it cannot regress. The frontend no-broker
historical	docs/redesign/verification/COMPARISON_R5.html:19:        margin: 0;
historical	docs/redesign/verification/COMPARISON_R5.html:25:      h1 { font-size: 28px; letter-spacing: -0.012em; margin: 0 0 4px; }
historical	docs/redesign/verification/COMPARISON_R5.html:26:      .sub { color: var(--mut); margin: 0 0 4px; }
historical	docs/redesign/verification/COMPARISON_R5.html:27:      .gate { color: var(--ter); font-size: 12px; margin: 0 0 32px; }
historical	docs/redesign/verification/COMPARISON_R5.html:28:      section { margin: 0 0 48px; border-top: 1px solid var(--line); padding-top: 24px; }
historical	docs/redesign/verification/COMPARISON_R5.html:29:      h2 { font-size: 18px; margin: 0 0 2px; }
historical	docs/redesign/verification/COMPARISON_R5.html:37:        margin-right: 10px;
historical	docs/redesign/verification/COMPARISON_R5.html:41:      .verdict { color: #3fbf6f; font-size: 12px; font-weight: 600; margin: 0 0 16px; }
historical	docs/redesign/verification/COMPARISON_R5.html:42:      .what { color: var(--mut); font-size: 13px; margin: 0 0 16px; max-width: 90ch; }
historical	docs/redesign/verification/COMPARISON_R5.html:46:        margin: 0;
historical	docs/redesign/R9_SAKSOFT_DIAGNOSIS.md:51:- Q4 FY26 PAT: **₹3,593.09 lakh** (₹359.31 Mn; +19.7% YoY; margin 14.44%)
historical	docs/redesign/R7_TRACK_RESEARCH_BRIEF.md:14:- NEVER touch: `types/plugin.ts`, `.github/`, `src-tauri/tauri.conf.json`, `LICENSE*`, `CLAUDE.md`, `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, broker code, `sidecar/services/agent_tools/catalog.py` (owned by another track)
historical	docs/redesign/R4_FAILURE_MODE_MATRIX.md:26:| **paper/synthetic**  | non-live broker / simulated              | `<ProvenanceBadge>` (`paper·synthetic·mode·provider`) — FR-041/065                                                                                                                
historical	docs/redesign/R4_FAILURE_MODE_MATRIX.md:57:| **Broker connect** (`broker-connect`)                   | ✅              | ✅          | ✅               | ◧ paper | —          | —                           | disconnected/expired-token state; paper badge                                        
historical	docs/redesign/R4_FAILURE_MODE_MATRIX.md:112:| **Kill-switch active / read-only / paper**            | any order proposal is **blocked + explained**; the surface goes _still + red_ (no glow, design doc §5) | §6.5; FR-011/012                                                      |
historical	docs/archive/PHASE_6_HANDOFF.md:160:   tool ids do NOT match `place_order|submit_order|execute_order|
historical	docs/archive/PHASE_6_HANDOFF.md:250:  (unchanged; Phase 6 doesn't touch broker execution)
historical	docs/archive/PHASE_6_HANDOFF.md:251:- `docs/BROKER_INTEGRATIONS.md` — per-broker setup (unchanged)
historical	docs/archive/PHASE_6_HANDOFF.md:274:- `pytest sidecar` (excluding the slow kill-switch benchmark) —
historical	docs/redesign/verification/R9_DEFECT_CATALOGUE.md:78:| `broker-connect` chips `py-[1px]` (off-grid arbitrary) | **Fixed** (`py-0.5` micro-chip pattern) | §1 quarter-step is for optical gaps only |
historical	docs/redesign/REBUILD_SPEC.md:28:byte untouched: `types/plugin.ts`, `types/safety.ts`, `types/broker.ts`,
historical	docs/redesign/REBUILD_SPEC.md:29:`sidecar/models/{safety,broker,audit_log,kill_switch}.py`,
historical	docs/redesign/REBUILD_SPEC.md:30:`sidecar/services/broker_base.py`, `src-tauri/src/kill_switch.rs`,
historical	docs/redesign/REBUILD_SPEC.md:32:auto-apply; every mutation routes the diff/accept gate; broker secrets stay
historical	docs/redesign/REBUILD_R4_SESSION2_REPORT.md:118:| Orders never auto-apply / brokers read-only / keyless-first | **intact**                                                                               |
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:49:1. The Kite adapter (`sidecar/services/brokers/kite.py`) does **not** use `KiteTicker` (Zerodha's WebSocket streaming class that uses autobahn). The adapter uses only the REST session (`kiteconnect.KiteConnect`) for order placement, positions and a
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:178:### Finding T2-mypy-oanda-broker-id: `OandaAdapter.BROKER_ID` typed as `ClassVar[str]` conflicts with base class `Literal` union [S2] [status: open]
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:184:sidecar\services\brokers\oanda.py:61: error: Incompatible types in assignment
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:185:  (expression has type "str", base class "BrokerAdapter" defined the type as
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:190:**Impact:** `OandaAdapter.BROKER_ID: ClassVar[str] = "oanda"` is annotated as `ClassVar[str]` but the base class expects a `Literal` union. The broker registry (`services/brokers/registry.py`) maps broker IDs to adapter classes — a runtime typo in
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:192:**Suggested fix path:** Change `BROKER_ID: ClassVar[str] = "oanda"` to `BROKER_ID: ClassVar = "oanda"` (let mypy narrow to `Literal["oanda"]`) or `BROKER_ID: ClassVar[BrokerId] = "oanda"`.
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:193:**Files:** `sidecar/services/brokers/oanda.py:61`
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:205:sidecar\routers\brokers.py:132: RUF100 Unused `noqa` directive (non-enabled: `ANN202`)
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:206:sidecar\routers\brokers.py:166: RUF100 Unused `noqa` directive (unused: `BLE001`)
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:214:**Files:** `sidecar/routers/agents.py:72`, `sidecar/routers/backtest.py:71`, `sidecar/routers/brokers.py:132,166`, `sidecar/routers/earnings.py:72`, `sidecar/openbb_mcp_subprocess/main.py:42,49`
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:239:- **S110** (`try/except/pass` without logging): Present in `main.py:39`, `openbb_mcp_subprocess/main.py:49`, `sec_edgar_mcp_subprocess/main.py:48`, `analyst_ratings_extended.py:162,278`, `brokers/alpaca.py:296`, `brokers/registry.py:92`. Most are 
historical	docs/archive/PHASE_8_SIDECAR_AUDIT.md:264:5. **[S2] T2-mypy-oanda-broker-id** — Change `BROKER_ID: ClassVar[str]` to `ClassVar` in `OandaAdapter` to restore mypy's ability to narrow to `Literal["oanda"]`.
historical	docs/redesign/KEYCHAIN_DEV_SIGNING.md:52:  `llm-provider:openrouter`, `app-meta:first-launch-terms` (renamed from `broker:_meta:first-launch-tos`, D81),
historical	docs/redesign/KEYCHAIN_DEV_SIGNING.md:183:   `app-meta:first-launch-terms` (then named `broker:_meta:first-launch-tos`; renamed D81), `app-meta:onboarding-complete`). Your "~4 prompts per
historical	docs/archive/PHASE_8_BUG_CATALOG.md:36:- `<id>` is a short stable slug (`fastmcp-runtime`, `kill-switch-toggle-react-warn`,
historical	docs/archive/PHASE_8_BUG_CATALOG.md:212:itself a minor S3 (asymmetry with `/openbb-mcp/status`) but the L9 broker
historical	docs/archive/PHASE_8_BUG_CATALOG.md:569:Grep-based audit of the broker-execution surface. Per CLAUDE.md "Defense-in-
historical	docs/archive/PHASE_8_BUG_CATALOG.md:578:1. **New public methods on `broker_base.py`?** No. Public surface = 11 documented members:
historical	docs/archive/PHASE_8_BUG_CATALOG.md:582:   - Order entry: `propose_order` (sync), `confirm_and_place` (async — sole `_place_confirmed` caller)
historical	docs/archive/PHASE_8_BUG_CATALOG.md:585:   _Note: my plan-doc listed `set_position_limits` as expected — that method does not exist; per-broker position limits are enforced at `propose_order` time via the per-adapter `CAPABILITIES` / position-limit class var. Spec misremember on my part, 
historical	docs/archive/PHASE_8_BUG_CATALOG.md:587:2. **New `_place_confirmed` call sites outside `confirm_and_place`?** No. Single production call site at `sidecar/services/broker_base.py:365` (inside `confirm_and_place`). All other matches are either definitions in the 7 per-broker overrides, docs
historical	docs/archive/PHASE_8_BUG_CATALOG.md:589:3. **New `audit_orders` UPDATE/DELETE write paths?** No. Only matches are intentional test paths at `tests/test_audit_log.py:141,156` and `tests/test_safety_end_to_end.py:268,274` that explicitly verify the SQLite triggers fire and raise `IntegrityE
historical	docs/archive/PHASE_8_BUG_CATALOG.md:591:4. **New backend-internal `confirm_and_place(human_confirmed=True)` paths with no UI surface?** No. All non-test matches resolve to `sidecar/routers/brokers.py:225` (the UI route handler) which passes `human_confirmed=request.human_confirmed` — the 
historical	docs/archive/PHASE_8_BUG_CATALOG.md:593:5. **New imports of broker internals from outside the broker package?** No. All matches are allowed callers:
historical	docs/archive/PHASE_8_BUG_CATALOG.md:594:   - `sidecar/routers/brokers.py:46,47,48` — the broker router
historical	docs/archive/PHASE_8_BUG_CATALOG.md:595:   - `sidecar/services/brokers/{registry,oanda,kite,ib,dhan,ccxt_exec,angelone,alpaca}.py` — inside-package adapters
historical	docs/archive/PHASE_8_BUG_CATALOG.md:603:`brokers_registry.bootstrap_default_adapters()` only registers the 3 India
historical	docs/archive/PHASE_8_BUG_CATALOG.md:604:brokers (Dhan, AngelOne, Kite). The 4 non-India adapters (Alpaca, IB, OANDA,
historical	docs/archive/PHASE_8_BUG_CATALOG.md:606:`sidecar/services/brokers/__init__.py` but no production code path
historical	docs/archive/PHASE_8_BUG_CATALOG.md:611:**may surface as a UC1/L9 broker-connect finding**: any`/brokers/<non-India-
historical	docs/archive/PHASE_8_BUG_CATALOG.md:630:## L9 — Broker connect + §6.5 cycle
historical	docs/archive/PHASE_8_BUG_CATALOG.md:632:Paper-mode broker exercise (whatever credentials are available on the
historical	docs/archive/PHASE_8_BUG_CATALOG.md:633:operator's machine) + failure-state UX for the brokers without credentials.
historical	docs/archive/PHASE_8_BUG_CATALOG.md:799:- **T4-brokers-not-registered [S2]:** all 7 broker plugins (alpaca,
historical	docs/archive/PHASE_8_BUG_CATALOG.md:803:  catalog X-broker-bootstrap-india-only** — the broker plugins exist but
historical	docs/archive/PHASE_8_BUG_CATALOG.md:805:  `bootstrap_default_adapters` (only India brokers).
historical	docs/archive/PHASE_8_BUG_CATALOG.md:821:  `resetKillSwitch()` entirely untested. POST body field `reAck: true`
historical	docs/archive/PHASE_8_BUG_CATALOG.md:823:  kill switch with no test catching it. **§6.5-adjacent finding —
historical	docs/archive/PHASE_8_BUG_CATALOG.md:825:- **T5-broker-base-invalid-order-type [S1]:** `propose_order()`
historical	docs/archive/PHASE_8_BUG_CATALOG.md:826:  raises `BrokerError` on invalid `order_type` but test only covers
historical	docs/archive/PHASE_8_BUG_CATALOG.md:828:  `"stop-limit"`→`"stop_limit"` would reach live broker undetected.
historical	docs/archive/PHASE_8_BUG_CATALOG.md:855:### Finding X-broker-bootstrap-india-only [S? — confirm at L9] [status: open]
historical	docs/archive/PHASE_8_BUG_CATALOG.md:857:**Repro:** `sidecar/services/brokers/registry.py::bootstrap_default_adapters`
historical	docs/archive/PHASE_8_BUG_CATALOG.md:860:`CcxtExecutionAdapter`) are imported in `services/brokers/__init__.py:27-33`
historical	docs/archive/PHASE_8_BUG_CATALOG.md:864:services/brokers/` returns only `bootstrap_default_adapters`.
historical	docs/archive/PHASE_8_BUG_CATALOG.md:866:**Impact:** At sidecar startup, a `POST /brokers/alpaca/connect` (or `/ib/`,
historical	docs/archive/PHASE_8_BUG_CATALOG.md:867:`/oanda/`, `/ccxt-*/`) would raise `KeyError: no broker adapter registered
historical	docs/archive/PHASE_8_BUG_CATALOG.md:868:for id='alpaca'` via `brokers_registry.get`. UC1 paper-mode broker connect
historical	docs/archive/PHASE_8_BUG_CATALOG.md:872:all 7 broker classes guarded by a feature flag per broker, OR (b) make the
historical	docs/archive/PHASE_8_BUG_CATALOG.md:873:broker-connect router lazy-register on first request when the broker's
historical	docs/archive/PHASE_8_BUG_CATALOG.md:879:- `sidecar/services/brokers/registry.py:97-112` — `bootstrap_default_adapters`
historical	docs/archive/PHASE_8_BUG_CATALOG.md:880:- `sidecar/services/brokers/__init__.py:27-33` — adapter class imports
historical	docs/archive/PHASE_8_BUG_CATALOG.md:882:**Notes:** Severity deferred to L9. If L9 confirms the broker-connect UX
historical	docs/archive/PHASE_8_BUG_CATALOG.md:883:gracefully degrades ("broker not bootstrapped — connect through the broker
historical	docs/redesign/R9_DESIGN_SYSTEM.md:69:  controls (Settings, Order entry) **h-8 (32px)**. Hit target ≥24×24.
historical	docs/redesign/R9_DESIGN_SYSTEM.md:125:- **Forms** (settings, order entry): body-13 labels, micro-11 hints as eyebrows or
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:16:- **§6.5 is byte-identical to pre-R10** across the entire broker/order/audit surface (empty diff vs base `393e8e5`), the safety suite is **40/40 green**, and the AI-order gate provably blocks any agent path to `confirm_and_place` in every
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:52:- `git diff 393e8e5 HEAD` over `sidecar/services/brokers/`, `models/audit_log.py`, `models/broker.py`, `routers/brokers.py`, `routers/safety.py`, `services/kill_switch.py`, `src-tauri/src/kill_switch.rs` → **empty**. Byte-identical to pre
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:53:- Safety suite `test_safety_end_to_end + test_audit_log + test_kill_switch + test_safety_router` → **40 passed**.
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:54:- `test_audit_2_no_bypass_path_to_place_confirmed`: greps the whole sidecar — `_place_confirmed` has exactly one production call site (`BrokerAdapter.confirm_and_place`).
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:55:- `test_audit_6_ai_order_gate`: "the agent_tools registry has NO tool that places orders directly." The catalog documents (line 19-22) and enforces that the AI's only broker capability is `propose_order` (opens a review dialog); there is 
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:158:| **Order placement** | `propose_order` ONLY (review dialog) | **PROVEN not auto-placeable** | §6.5 / `test_audit_6_ai_order_gate` |
historical	docs/redesign/verification/R10_VERIFY_REPORT.md:238:- Two uncommitted non-engine files left exactly as-is: `sidecar/services/resolver_masters/enrich_nse_sectors.py` (working copy carries the `_nse_symbols` fix that ran the enrichment) and `docs/screenshots/v0.5.0/safety-audit/kill-switch-
historical	docs/redesign/REBUILD_R4_SPEC.md:29:  `publish_brief`, `propose_order`), the §6.5 **propose-then-accept gate** (`proposed-changes.ts` →
historical	docs/redesign/REBUILD_R4_SPEC.md:434:   broker-WS BYOK Kite/Upstox → paid EODHD) is documented (`R4_BUILD_SEQUENCE` / research). Realtime
historical	docs/redesign/REBUILD_R4_SPEC.md:435:   broker-WebSocket tick is a sizable **new subsystem** beyond the experience layer.
historical	docs/redesign/REBUILD_R4_SPEC.md:437:   broker-WS realtime + EODHD are a **separate later track**. (Alt: pull Kite/Upstox WS into R4.)
historical	docs/archive/BLOCKERS-I.md:1:# BLOCKERS-I.md — Teammate I (India brokers)
historical	docs/archive/BLOCKERS-I.md:10:1. `BrokerConnectPanel` with Dhan + Angel One + Kite connected in paper
historical	docs/archive/BLOCKERS-I.md:13:   broker-connect panel.
historical	docs/archive/BLOCKERS-I.md:15:Both require Teammate S's `BrokerConnectPanel.tsx`, which lives in their
historical	docs/archive/BLOCKERS-I.md:23:1. Merge Teammate S's `agent-S` branch first so `BrokerConnectPanel.tsx`
historical	docs/archive/BLOCKERS-I.md:27:   `src/modules/broker-connect/kite-static-ip-banner.tsx`.
historical	docs/archive/BLOCKERS-I.md:28:4. Bring up `pnpm dev`, connect all three India brokers in paper mode,
historical	docs/archive/BLOCKERS-I.md:37:`src/modules/broker-connect/kite-static-ip-banner.test.tsx` so its
historical	docs/redesign/R7_TRACK_PANELS_REPORT.md:24:  (broker)" label.
historical	docs/redesign/R7_TRACK_PANELS_REPORT.md:31:### OpenRouter "(broker)" — killed at the runtime source
historical	docs/redesign/R7_TRACK_PANELS_REPORT.md:36:still carried `"label": "OpenRouter (broker)"` — so the defect resurfaced live
historical	docs/redesign/R7_TRACK_PANELS_REPORT.md:39:no-broker test cannot see the sidecar, so the pin lives sidecar-side).
historical	docs/redesign/R12_HAND_TESTING_GUIDE.md:9:The engine underneath (rebuilt in R10, made data-perfect in R11) is one resolver with India-first policy, a screener that runs the whole NSE/BSE universe, a research pipeline that stamps every figure with its basis and as-of date, and a §6.5 safet
historical	docs/redesign/R12_HAND_TESTING_GUIDE.md:36:- **Plugins:** the marketplace and manager work; six plugins load (brokers, example, openbb-mcp, vysted-lenses, vysted-news, yfinance). Tradesa is fully removed — the plugin system is alive without it.
historical	docs/redesign/R12_HAND_TESTING_GUIDE.md:37:- **Orders (the safety showcase):** ask "buy 5 shares of RELIANCE at market." The agent PREPARES the order into a review bar reading "ROUTES TO THE CONFIRM-BEFORE-PLACE DIALOG — NOTHING IS PLACED AUTOMATICALLY." Even if you click Accept, it fails
historical	docs/redesign/verification/R6_REALPIXEL.html:28:        margin: 0;
historical	docs/redesign/verification/R6_REALPIXEL.html:36:      .wrap { max-width: 1180px; margin: 0 auto; }
historical	docs/redesign/verification/R6_REALPIXEL.html:37:      h1 { font-size: 22px; font-weight: 700; margin: 0 0 4px; letter-spacing: -0.005em; }
historical	docs/redesign/verification/R6_REALPIXEL.html:38:      h2 { font-size: 18px; font-weight: 700; margin: 40px 0 4px; }
historical	docs/redesign/verification/R6_REALPIXEL.html:39:      .sub { color: var(--text-2); font-size: 12px; margin: 0 0 24px; }
historical	docs/redesign/verification/R6_REALPIXEL.html:43:      .rule { height: 1px; background: var(--hairline); border: 0; margin: 24px 0; }
historical	docs/redesign/verification/R6_REALPIXEL.html:45:      .lede { background: var(--panel); border: 1px solid var(--border); padding: 16px 18px; margin: 16px 0 8px; }
historical	docs/redesign/verification/R6_REALPIXEL.html:46:      .lede p { margin: 6px 0; color: var(--text-2); }
historical	docs/redesign/verification/R6_REALPIXEL.html:49:      table.buckets { width: 100%; border-collapse: collapse; margin: 16px 0; }
historical	docs/redesign/verification/R6_REALPIXEL.html:58:      .card { border: 1px solid var(--border); background: var(--panel); margin: 18px 0; }
historical	docs/redesign/verification/R6_REALPIXEL.html:61:      .card figure { margin: 0; }
historical	docs/redesign/verification/R6_REALPIXEL.html:64:      .card .notes ul { margin: 6px 0 0; padding-left: 18px; }
historical	docs/redesign/verification/R6_REALPIXEL.html:65:      .card .notes li { margin: 3px 0; color: var(--text-2); }
historical	docs/redesign/verification/R6_REALPIXEL.html:73:      .footer { color: var(--text-3); font-size: 11px; margin-top: 40px; }
historical	docs/redesign/verification/R6_REALPIXEL.html:91:        <ul style="margin:6px 0 0;color:var(--text-2)">
historical	docs/redesign/verification/R6_REALPIXEL.html:129:          <tr><td>Screener / Quant / Macro / SEC / Analyst / Earnings / Backtest / Agent-builder / Node-editor / Marketplace / Broker / Plugin-manager / Settings</td><td><span class="tag manual">Needs-manual</span></td><td>Code-fixed (amber
historical	docs/redesign/verification/R6_REALPIXEL.html:209:          (screener, quant, macro, sec, analyst, earnings, backtest, builders, marketplace, broker,
historical	docs/redesign/verification/R6_REALPIXEL.html:217:        <li>Tier-1 locked files byte-untouched (types, safety/broker models, <code>tauri.conf.json</code>, CI). Safety/broker edits were className/markup only &mdash; no §6.5, audit, kill-switch, or ABC logic touched.</li>
historical	docs/archive/PHASE_8_HANDOFF.md:45:  (620.19 s including kill-switch benchmark). Cargo fmt + clippy strict
historical	docs/archive/PHASE_8_HANDOFF.md:98:- **L9** _(deferred — needs broker paper credentials, Phase 9 manual test)_
historical	docs/archive/PHASE_8_HANDOFF.md:119:  3×S2, 3×S3, 1×S4.** Top findings: 7 broker plugins not in
historical	docs/archive/PHASE_8_HANDOFF.md:212:broker paper-mode connections, axe-core a11y, Lighthouse perf, Mac
historical	docs/archive/PHASE_8_HANDOFF.md:240:exercised on macOS with real broker paper credentials, real BYOK keys,
historical	docs/archive/PHASE_8_HANDOFF.md:253:   broker safety is solid; focus on broker integration UX rather than
historical	docs/archive/PHASE_8_HANDOFF.md:267:- **Broker paper-mode connect:** Alpaca (most likely to have paper creds),
historical	docs/archive/PHASE_8_HANDOFF.md:268:  the 6 other brokers (failure-state UX where no creds — verify the
historical	docs/archive/PHASE_8_HANDOFF.md:304:| `git diff v0.7.0..HEAD -- sidecar/services/broker_base.py sidecar/services/kill_switch.py sidecar/services/audit_log.py sidecar/models/audit_log.py sidecar/tests/test_safety_end_to_end.py` | ✅ empty                  | §6.5 Tier-1 untouched            
historical	docs/archive/PHASE_8_HANDOFF.md:305:| `pytest sidecar/tests/test_safety_end_to_end.py`                                                                                                                                             | ✅ 9/9 PASS               | 620.19 s; kill-switch sub-2 s ben
historical	docs/redesign/R4_BUILD_SEQUENCE.md:19:  `types/broker.ts`, `sidecar/models/{safety,broker,audit_log,kill_switch}.py`,
historical	docs/redesign/R4_BUILD_SEQUENCE.md:20:  `sidecar/services/broker_base.py`, `src-tauri/src/kill_switch.rs`,
historical	docs/redesign/R4_BUILD_SEQUENCE.md:24:- **Orders never auto-apply**; brokers GET-only; secrets keychain-only/per-request/never logged or
historical	docs/archive/PHASE_9.5_MAC_RUNNER.md:106:broker creds → #77 connect,#78. Mark anything still unconfigured DEFERRED-NEEDS-SETUP.
historical	docs/archive/PHASE_9.5_MAC_RUNNER.md:129:drag/canvas items (#8/#9/#27/#28/#32/#71/#72), live broker connect/order placement,
historical	docs/redesign/R7_TRACK_DATA_REPORT.md:371:`docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json` in the
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:28:`test_safety_end_to_end.py` and the tracked `kill-switch-benchmark.json` baseline are
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:32:<details><summary>Original entry (2.5 — kill-switch-benchmark.json no longer dirties the tree on every pytest), kept for history</summary>
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:34:- **What:** `test_safety_end_to_end.py::test_audit_5_kill_switch_under_2s` rewrote the
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:61:  license text promises or mentions live order placement anymore.
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:99:The census held at HEAD `99e2ae3`: the kill switch's only subscriber was
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:100:`BrokerAdapter.__init__` (`broker_base.py:103`), and its only readers were the order
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:102:`kill-switch:requested` event. With no orders left, there was nothing to halt, so the
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:103:mechanism was deleted rather than bound: `kill_switch.rs`, the
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:104:`tauri-plugin-global-shortcut` dependency and its capability, `services/kill_switch.py`,
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:105:the `/safety/kill-switch*` routes, the store slice, and the types. The first-launch
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:113:The paper→live switch (`BrokerConnectPanel.tsx:246-249`), `POST /brokers/{id}/mode`,
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:121:`sidecar/models/safety.py`, `types/safety.ts` and `BrokerAdapter.DEFAULT_LIMITS`. No
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:183:  route or UI to point Vysted at a third-party MCP server (e.g. a broker's read-only MCP,
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:283:- `~/.vysted-terminal/audit_log.db` — a user's own historical order and paper-trade audit
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:285:- OS-keychain `broker:<id>:api_key|api_secret|access_token|client_id` and
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:286:  `broker:<id>:_meta:first-connect-ack` — live BYOK broker secrets, now orphaned.
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:287:- `broker:_meta:first-launch-tos` — the old first-launch-terms ack, superseded by
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:289:- Sidecar plugin-store rows for the 7 broker plugin ids — `plugin-bootstrap` iterates
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:294:  broker credentials" step, plus a CHANGELOG note telling users how to delete `audit_log.db`
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:299:- The dialog's body text changes from "before connecting a broker" framing to research-only
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:300:  terms: data and analysis tool, not investment advice; no brokerage connection, cannot place,
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:301:  route or simulate orders; data may be delayed or wrong; AI output can be wrong; a licence
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:303:  kill-switch line. This is a rewrite of user-facing terms and licence-adjacent wording on a
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:309:- **No durable record of agent writes.** The former append-only `audit_orders` log existed
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:310:  only to record order placement and went with the feature. The surviving read-back
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:313:- **No stop control for AUTO beyond reject or run-cancel.** There is no kill switch and no
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:320:  and the JSDoc examples (`tradesa.kill-switch`, "Tradesa V2 (Bybit testnet)") were **not**
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:328:  broker relationship." The clause is still true (it covers decisions users make elsewhere)
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:331:  instructed not to edit. **No edit was needed:\*\* verified no shortcut, broker, or safety
historical	docs/redesign/DECISIONS_FOR_OPERATOR.md:633:  - **No order row exists to write.** There is no `audit_orders` table any more: D81 removed it
historical	docs/redesign/INTEGRATION_NOTES_R7_HACK.md:229:                "restricted grammar (never eval) and executed in the SIMULATED "
historical	docs/redesign/INTEGRATION_NOTES_R7_HACK.md:273:`read_only=True` rationale: the tool only SIMULATES (backtest engine has no
historical	docs/redesign/R4_DESIGN_LANGUAGE.md:237:**Kill-switch / safety states are _stillness_:** when the kill-switch is active, motion stops, the
historical	docs/archive/PHASE_8_RUST_AUDIT.md:120:Clippy recommends `&tauri::State<'_, ...>` for all three. `kill_switch.rs:90` — `app: AppHandle` and `fired_by: String` both recommended as refs/str slices.  
historical	docs/archive/PHASE_8_RUST_AUDIT.md:121:**Impact:** Minor: `tauri::State` is a reference-counted wrapper; passing by value is slightly less efficient but works correctly. The `AppHandle` by-value case in `kill_switch_emit` is harmless since Tauri clones it cheaply. S3 pedantic noise.  
historical	docs/archive/PHASE_8_RUST_AUDIT.md:122:**Suggested fix path:** Change the three port-getter handlers to `&tauri::State<'_, ...>` and `kill_switch_emit` to `&AppHandle` + `fired_by: &str`. Requires verifying Tauri macro compatibility with reference-type State args (Tauri 2.x docs confirm `
historical	docs/archive/PHASE_8_RUST_AUDIT.md:123:**Files:** `src-tauri/src/lib.rs:46`, `src-tauri/src/openbb_mcp.rs:49`, `src-tauri/src/sec_edgar_mcp.rs:48`, `src-tauri/src/kill_switch.rs:90`
historical	docs/archive/PHASE_8_RUST_AUDIT.md:212:| `tauri-plugin-global-shortcut` | `kill_switch.rs` — `GlobalShortcutExt`, `Modifiers`, `Code`, `Shortcut`, `ShortcutState`   | Active                    |
historical	docs/archive/PHASE_8_RUST_AUDIT.md:215:| `serde_json`                   | `kill_switch.rs:95` — `serde_json::json!({ "firedBy": fired_by })`                         | Active                    |
historical	docs/archive/PHASE_8_RUST_AUDIT.md:227:**No findings.** The formatter check passes cleanly on all five source files (`lib.rs`, `keychain.rs`, `kill_switch.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`). The CI gate is holding.
historical	docs/archive/PHASE_8_RUST_AUDIT.md:242:- `kill_switch_shortcut()` — called from both `build_plugin()` and `register_shortcut()`.
historical	docs/archive/PHASE_8_RUST_AUDIT.md:243:- `emit_kill_switch_requested()` — called from the shortcut handler closure and from `kill_switch_emit`.
historical	docs/archive/PHASE_8_RUST_AUDIT.md:324:- `kill_switch_emit` — defined in `kill_switch.rs`
historical	docs/archive/PHASE_8_RUST_AUDIT.md:333:- `kill_switch::build_plugin()` ✓ (global-shortcut plugin with handler)
historical	docs/archive/PHASE_8_RUST_AUDIT.md:334:- `tauri_plugin_global_shortcut` not registered separately (it is embedded in `kill_switch::build_plugin()`)
historical	docs/archive/PHASE_8_RUST_AUDIT.md:336:One observation: the global-shortcut plugin is initialized inside `kill_switch::build_plugin()` but `register_shortcut()` is called after `.plugin()` registration is complete. This is the correct order per Tauri 2.x docs — the plugin must be register
historical	docs/archive/PHASE_5_HANDOFF.md:3:**Read this first** if you are looking at Phase 5's work. Phase 5 (Broker
historical	docs/archive/PHASE_5_HANDOFF.md:16:- **6 broker SDK pins** in `sidecar/requirements.txt`: `dhanhq==2.1.0`,
historical	docs/archive/PHASE_5_HANDOFF.md:19:- **`types/broker.ts`** — `BrokerId` literal union (Dhan / AngelOne /
historical	docs/archive/PHASE_5_HANDOFF.md:21:  `BrokerMode` (`"paper" | "live"`), `BrokerCapabilities` (with
historical	docs/archive/PHASE_5_HANDOFF.md:22:  `requiresStaticIp` flag — Kite carries `True`), `BrokerOrderSide`,
historical	docs/archive/PHASE_5_HANDOFF.md:23:  `BrokerOrderType`, `BrokerOrderSource` (`"manual" | "ai-agent" |
historical	docs/archive/PHASE_5_HANDOFF.md:24:"workflow"`), `BrokerOrderProposal`, `BrokerOrderResult`,
historical	docs/archive/PHASE_5_HANDOFF.md:25:  `AccountSummary`, `BrokerPosition` (renamed from `Position` to avoid
historical	docs/archive/PHASE_5_HANDOFF.md:27:- **`types/safety.ts`** — `KillSwitchEvent`, `KillSwitchFireResult` (with
historical	docs/archive/PHASE_5_HANDOFF.md:32:- **`sidecar/models/{broker,safety,audit_log}.py`** — Pydantic mirrors.
historical	docs/archive/PHASE_5_HANDOFF.md:39:- **`sidecar/services/kill_switch.py`** — async `KillSwitchBus`.
historical	docs/archive/PHASE_5_HANDOFF.md:42:  returns aggregated `KillSwitchFireResult` with p50/p95/max. Idempotent
historical	docs/archive/PHASE_5_HANDOFF.md:44:- **`sidecar/services/broker_base.py`** — `BrokerAdapter` ABC. The
historical	docs/archive/PHASE_5_HANDOFF.md:46:  kill-switch bus unconditionally. Public surface: `propose_order` →
historical	docs/archive/PHASE_5_HANDOFF.md:48:  time). `_place_confirmed` is the only method that touches the broker
historical	docs/archive/PHASE_5_HANDOFF.md:50:  raised before broker call. Kill-switch handler forces read-only +
historical	docs/archive/PHASE_5_HANDOFF.md:58:  restart). The other two disclaimer kinds (first-launch TOS, per-broker
historical	docs/archive/PHASE_5_HANDOFF.md:63:  `POST /safety/kill-switch` (fire),
historical	docs/archive/PHASE_5_HANDOFF.md:64:  `POST /safety/kill-switch/reset` (requires acknowledged=true),
historical	docs/archive/PHASE_5_HANDOFF.md:65:  `GET /safety/kill-switch/status`,
historical	docs/archive/PHASE_5_HANDOFF.md:70:- **`src-tauri/src/kill_switch.rs`** — registers `CmdOrCtrl+Shift+K` as
historical	docs/archive/PHASE_5_HANDOFF.md:71:  the OS-wide shortcut. Emits a `kill-switch:requested` Tauri event;
historical	docs/archive/PHASE_5_HANDOFF.md:73:  `/safety/kill-switch` route. Splits responsibility: Rust owns the OS
historical	docs/archive/PHASE_5_HANDOFF.md:76:- **`src/lib/keychain.ts`** — `KEYCHAIN_NAMESPACES.broker(id, field)`
historical	docs/archive/PHASE_5_HANDOFF.md:77:  added; secret-id format `broker:<id>:<field>` (e.g.
historical	docs/archive/PHASE_5_HANDOFF.md:78:  `broker:alpaca:api_key`). Persisted disclaimer acks reuse the same
historical	docs/archive/PHASE_5_HANDOFF.md:79:  namespace under `broker:_meta:first-launch-tos` and
historical	docs/archive/PHASE_5_HANDOFF.md:80:  `broker:<broker-id>:_meta:first-connect-ack`.
historical	docs/archive/PHASE_5_HANDOFF.md:85:broker-SDK install: **67.4 MB** (+0.4 MB over v0.4.0's 67 MB; well under
historical	docs/archive/PHASE_5_HANDOFF.md:86:120 MB threshold). **All 7 brokers ship in main sidecar — no subprocess
historical	docs/archive/PHASE_5_HANDOFF.md:88:`openbb_mcp.rs` precedent) stays available for future broker SDKs that
historical	docs/archive/PHASE_5_HANDOFF.md:91:### Teammate I — India brokers + brokers router + Kite static-IP UX (7 commits)
historical	docs/archive/PHASE_5_HANDOFF.md:93:- `sidecar/services/brokers/{dhan,angelone,kite}.py` — three India
historical	docs/archive/PHASE_5_HANDOFF.md:94:  broker adapters inheriting `BrokerAdapter`. Kite carries
historical	docs/archive/PHASE_5_HANDOFF.md:95:  `CAPABILITIES.requires_static_ip=True`; live-mode toggle fetches
historical	docs/archive/PHASE_5_HANDOFF.md:98:- `sidecar/services/brokers/__init__.py` — the canonical registry
historical	docs/archive/PHASE_5_HANDOFF.md:101:- `sidecar/services/brokers/registry.py` — adapter registry + lifecycle.
historical	docs/archive/PHASE_5_HANDOFF.md:102:- `sidecar/routers/brokers.py` — 8-route HTTP surface: connect, account,
historical	docs/archive/PHASE_5_HANDOFF.md:104:- `plugins/brokers/{dhan,angelone,kite}/` — VystedPlugin shells.
historical	docs/archive/PHASE_5_HANDOFF.md:106:  `executeCommand("place-order"|"halt-trading"|"set-read-only")`.
historical	docs/archive/PHASE_5_HANDOFF.md:107:- `src/modules/broker-connect/kite-static-ip-banner.tsx` + test — polls
historical	docs/archive/PHASE_5_HANDOFF.md:109:  live mode; renders loading / ok / mismatch / error variants.
historical	docs/archive/PHASE_5_HANDOFF.md:112:### Teammate G — Global brokers (7 commits)
historical	docs/archive/PHASE_5_HANDOFF.md:114:- `sidecar/services/brokers/{alpaca,ib,oanda}.py` — three global broker
historical	docs/archive/PHASE_5_HANDOFF.md:119:  `docs/BROKER_INTEGRATIONS.md`. OANDA uses `oandapyV20 0.7.2`
historical	docs/archive/PHASE_5_HANDOFF.md:123:- `plugins/brokers/{alpaca,ib,oanda}/` — VystedPlugin shells with 5
historical	docs/archive/PHASE_5_HANDOFF.md:126:- `docs/BROKER_INTEGRATIONS.md` — global broker section concatenated
historical	docs/archive/PHASE_5_HANDOFF.md:127:  with I's India broker section at integration time.
historical	docs/archive/PHASE_5_HANDOFF.md:132:- `sidecar/services/brokers/ccxt_exec.py` — `CcxtExecutionAdapter`
historical	docs/archive/PHASE_5_HANDOFF.md:134:  `kraken`, `coinbase`); the `BROKER_ID` is set to `ccxt-<exchange>`
historical	docs/archive/PHASE_5_HANDOFF.md:138:- `plugins/brokers/ccxt-exec/` — VystedPlugin shell with
historical	docs/archive/PHASE_5_HANDOFF.md:139:  `supportsControlPlane=false` on the plugin (order placement goes
historical	docs/archive/PHASE_5_HANDOFF.md:141:  `/safety/kill-switch`).
historical	docs/archive/PHASE_5_HANDOFF.md:142:- Bybit testnet end-to-end paper-trade produces a full audit trail:
historical	docs/archive/PHASE_5_HANDOFF.md:145:  capture in `docs/screenshots/v0.5.0/teammate-x/paper-trade-audit-trail.json`).
historical	docs/archive/PHASE_5_HANDOFF.md:159:- `src/store/{safety,orders,brokers}.ts` + tests — 23 tests across the
historical	docs/archive/PHASE_5_HANDOFF.md:162:  proposals inbox. `useBrokersStore` is the connection-state aggregator.
historical	docs/archive/PHASE_5_HANDOFF.md:163:- `src/modules/safety/{KillSwitchToolbar,OrderConfirmationDialog,
historical	docs/archive/PHASE_5_HANDOFF.md:164:DisclaimerFlow,AuditLogViewer}.tsx` + tests. KillSwitchToolbar listens
historical	docs/archive/PHASE_5_HANDOFF.md:165:  to the Tauri `kill-switch:requested` event AND has its own click
historical	docs/archive/PHASE_5_HANDOFF.md:168:  surfaces first-launch TOS, per-broker first-connect (both
historical	docs/archive/PHASE_5_HANDOFF.md:171:- `src/modules/broker-connect/{BrokerConnectPanel,BrokerOrderEntry}.tsx`
historical	docs/archive/PHASE_5_HANDOFF.md:172:  - tests — connect list, status badges, mode badges, manual order entry.
historical	docs/archive/PHASE_5_HANDOFF.md:189:| 1   | Paper mode default    | PASS (all 7 brokers + ccxt)                   | paper-default-proof.log                         |
historical	docs/archive/PHASE_5_HANDOFF.md:193:| 5   | Kill switch < 2s      | PASS (max 20.08ms / budget 2000ms; 12 subs)   | kill-switch-benchmark.json                      |
historical	docs/archive/PHASE_5_HANDOFF.md:194:| 6   | AI-order gate         | PASS (no place_order tool; no auto_approve)   | ai-order-gate-proof.log                         |
historical	docs/archive/PHASE_5_HANDOFF.md:195:| 7   | Read-only mode        | PASS (all 7 raise in propose_order)           | read-only-proof.log                             |
historical	docs/archive/PHASE_5_HANDOFF.md:213:   §7 Phase 5 lists Tradesa V2 + 6 brokers + ccxt; operator brief
historical	docs/archive/PHASE_5_HANDOFF.md:214:   de-scoped Tradesa V2 for v0.5.0 in favour of the 7-broker breadth.
historical	docs/archive/PHASE_5_HANDOFF.md:215:   Foundation contracts (kill switch + audit log + executeCommand
historical	docs/archive/PHASE_5_HANDOFF.md:224:4. **All 7 broker SDKs in main sidecar** (Tier-3, F9). Measured 67.4 MB
historical	docs/archive/PHASE_5_HANDOFF.md:226:   Tauri-Rust-spawn helper stays available for future broker SDKs.
historical	docs/archive/PHASE_5_HANDOFF.md:229:   surfaces a banner on mismatch; the order placement path does NOT
historical	docs/archive/PHASE_5_HANDOFF.md:234:6. **Plugin contract held** (Tier-1). `executeCommand` covers broker
historical	docs/archive/PHASE_5_HANDOFF.md:235:   control plane (`"place-order"`, `"halt-trading"`, `"set-read-only"`,
historical	docs/archive/PHASE_5_HANDOFF.md:241:   procedure in `docs/SAFETY_ARCHITECTURE.md` applies — that broker's
historical	docs/archive/PHASE_5_HANDOFF.md:257:3. **Live-mode end-to-end verification** — by design, v0.5.0 ships
historical	docs/archive/PHASE_5_HANDOFF.md:262:   2021-08; documented in `docs/BROKER_INTEGRATIONS.md`. Users monitor
historical	docs/archive/PHASE_5_HANDOFF.md:267:   `docs/BROKER_INTEGRATIONS.md`; when neither is running, the IB
historical	docs/archive/PHASE_5_HANDOFF.md:268:   adapter renders a recovery hint in the broker-connect UI rather than
historical	docs/archive/PHASE_5_HANDOFF.md:277:- **`executeCommand` covers the full broker control plane**:
historical	docs/archive/PHASE_5_HANDOFF.md:278:  `"place-order"`, `"halt-trading"`, `"set-read-only"`, `"set-mode"`.
```

