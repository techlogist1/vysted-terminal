# R15 Stage C — Trading Removal Plan (D81)

- **Decision:** D81 (`docs/redesign/DECISIONS.md`), operator Tier-4 sign-off 23 Sep 2026. Trading is
  out of the product permanently.
- **Baseline:** branch `004-r4-experience-rebuild` @ `99e2ae38a8e493b1feefdcf17ea3c14725715987`.
  Working tree at plan time: only `CLAUDE.md` is modified (an operator edit). **No writer touches it.**
- **Author:** removal planner (Opus). Every row below was checked in the repo with grep, imports,
  route tables, catalog introspection (`sidecar/.venv/bin/python`), manifests and tests. Nothing is
  assumed.
- **Rule applied to every item:**
  - **GOES**: it exists only to connect a broker, place or simulate an order, or gate order execution.
  - **STAYS**: another feature depends on it. The dependent feature is named in the row.
  - **UNSURE**: remove it from every surface, keep the code, and list it in DECISIONS_FOR_OPERATOR.
  - Delete; never stub.
- **Gate 8 (new):** no order, broker or simulated-account path exists anywhere (surfaces, tools,
  routes, docs), and the tracked portfolio is intact. It is pinned by the new
  `sidecar/tests/test_no_trading_surface.py` (§3.5).

---

## 0. Verified facts that decide the plan

| Fact | Evidence (at HEAD) |
| --- | --- |
| The kill-switch bus has exactly **one subscriber: `BrokerAdapter.__init__`** | `sidecar/services/broker_base.py:103` is the only `.subscribe(` in non-test sidecar code |
| `is_fired` is read **only by the order gates** | `broker_base.py:251` (`propose_order`), `broker_base.py:345` (`confirm_and_place`). The other readers are the `/safety/kill-switch*` routes (`routers/safety.py:122,138,145`). |
| **Nothing in the UI fires the kill switch or listens for `kill-switch:requested`** | grep of `fireKillSwitch`, `resetKillSwitch`, `refreshKillSwitchStatus`, `killSwitchFired` and `kill-switch:requested` outside `src/store/safety*.ts` finds only the type declaration at `types/safety.ts:230` |
| `tauri-plugin-global-shortcut` exists **only for the kill switch** | used only by `src-tauri/src/kill_switch.rs`. No JS global-shortcut package is installed. `tauri.conf.json` has no shortcut configuration. |
| **Every `audit_orders` writer is a trading path** | `audit_log.append` appears only in `broker_base.py` (12 sites), `brokers/kite.py:160` and `disclaimer_session.py:39` (the first-live-order ack). The kill-switch fire and reset write no row. The only readers are `/safety/audit-log*` and `AuditLogViewer.tsx`. |
| The broker layer is **self-contained** | Outside the trading files, broker modules are imported only by `models/__init__.py` (re-exports) and `agent_tools/broker_portfolio.py` |
| The tracked portfolio has **no broker dependency** | `src/store/portfolios.ts`, `src/modules/portfolio/*`, `routers/portfolio.py`, `services/portfolio_db.py` and `models/portfolio.py` import nothing from the broker, safety or order layers |
| **Catalog today:** 50 capabilities (29 read_handler, 19 host_action, 2 per_invocation). 28 are projected to MCP. | `catalog.CAPABILITY_CATALOG` introspection |
| **Catalog trading entries:** `broker_portfolio` (read_handler, MCP) and `propose_order` (host_action) | `catalog.py:909-930`, `catalog.py:1065-1089` |
| **MCP surface today:** 36 tools. `broker_portfolio` is the only trading tool. | `mcp_server.get_mcp_server().list_tools()` |
| **Sidecar routes today:** 117 unique paths. **23 are trading**: 15 under `/brokers*` and 8 under `/safety/*`. | `create_app().routes` |
| **Agent roster:** 13 agents. **No agent JSON is deleted**, so roster counts do not change. | `sidecar/agents/*.json` |

---

## 1. Ownership sets (three writers, disjoint files)

| Set | Writer | Owns |
| --- | --- | --- |
| **A** | sidecar | `sidecar/**` (code, agents JSON, `requirements.txt`, and every Python test including the new Gate-8 test) and `scripts/**` (no script needs an edit, see §4) |
| **B** | frontend | `src/**`, `types/**`, `plugins/**`, every TS/TSX test, and `src-tauri/**` (`src/lib.rs`, `src/kill_switch.rs`, `Cargo.toml`, `Cargo.lock`, `capabilities/default.json`) |
| **C** | docs | `README.md`, `CONTRIBUTING.md`, `BLOCKERS.md`, `CHANGELOG.md`, `.prettierignore`, `docs/**` (including `docs/screenshots/**` deletions and the `docs/redesign/*` decision logs), `specs/**`, `.specify/**` |

**Shared or mirrored files: each has exactly one writer.**

| Pair | Owner | Instruction to the other writer |
| --- | --- | --- |
| `types/data.ts` ↔ `sidecar/models/market.py` | B owns `types/data.ts`. A owns `models/market.py`. | Both edit **one comment only**. Neither changes a type. Both use this exact wording: `in_eod_only = BSE/NSE serve end-of-day data only; no intraday/realtime lane exists for this listing`. (B: `types/data.ts:43`. A: `models/market.py:56-57`.) |
| `types/ai.ts` ↔ `sidecar/models/agent.py` | B / A respectively | Comment-only on both sides (`types/ai.ts:30,264`, `models/agent.py:90,95`). Delete the `propose_order` / "orders always need confirmation" clauses. No field changes. |
| `types/broker.ts`, `types/broker-reads.ts`, `types/safety.ts` ↔ `models/broker.py`, `models/broker_reads.py`, `models/safety.py` | B deletes the TS side. A deletes the Python side. | Delete both sides. Neither writer touches the other side's files. |
| `src/lib/host-actions.ts` `HOST_ACTION_NAMES` (B) is read by `sidecar/tests/test_toolbelt_integrity.py` (A) | B | A **must not** edit `host-actions.ts`. A's updated test passes only after B's removal of `propose_order` lands. The integrator runs pytest after merging both. |
| The Gate-8 test (A) scans B's files | A | The test is red until B lands. **Merge order: B, then A, then C.** Alternatively merge all three, then run the gates once. |
| `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json` is written by `test_safety_end_to_end.py` (A deletes the test) | C deletes the file | A must not touch `docs/**`. |
| `CLAUDE.md` | **Nobody.** It is Tier-1 and holds an uncommitted operator edit. | C appends the exact edits to `docs/redesign/CLAUDE_MD_PROPOSAL.md` (§3.7). |
| `docs/redesign/DECISIONS.md`, `DECISIONS_FOR_OPERATOR.md`, `CHANGELOG.md` | C | A and B record nothing there. C records every Tier-3 decision listed in §3.10. Use the next free D-number at write time; parallel runs may have taken some. |

---

## 2. Inventory — every item, one row

Verdict key:

- **GOES**: delete the whole file.
- **EDIT**: the file stays because another feature depends on it; the trading parts inside it go. The dependent feature is named.
- **STAYS**: no change needed.
- **UNSURE**: see §4.

### 2A. Sidecar (owner A)

| Path | Kind | Verdict | Evidence | Owner |
| --- | --- | --- | --- | --- |
| `sidecar/routers/brokers.py` | router (15 routes: connect, state, account, positions, holdings, **margins**, disconnect, orders propose/confirm/cancel, mode, read-only, kite static-ip, kite session) | GOES | Its only purpose is broker connectivity and orders. Mounted at `app.py:27,91`. | sidecar |
| `sidecar/routers/safety.py` | router (8 routes: audit-log, audit-log csv, kill-switch fire/reset/status, disclaimer-status/ack, static-ip-status) | GOES | Every route gates or records orders (§0). Mounted at `app.py:46,87`. | sidecar |
| `sidecar/services/brokers/__init__.py`, `alpaca.py`, `angelone.py`, `ccxt_exec.py`, `dhan.py`, `ib.py`, `kite.py`, `oanda.py`, `registry.py` | broker adapters and registry (includes the Kite session exchange and the simulated paper fills and accounts) | GOES | They are imported only by the brokers router, `broker_portfolio.py` and the broker tests | sidecar |
| `sidecar/services/broker_base.py` | order-gate ABC (paper mode, PositionLimits, kill-switch subscription) | GOES | Its only importers are the adapters, `broker_portfolio.py` and the broker tests | sidecar |
| `sidecar/services/kill_switch.py` | kill-switch bus | GOES | Its sole subscriber is `broker_base.py:103` (§0) | sidecar |
| `sidecar/services/audit_log.py` | append-only order log | GOES | Every writer is a trading path (§0) | sidecar |
| `sidecar/services/disclaimer_session.py` | first-live-order session ack | GOES | Used only by `routers/safety.py`, and it writes `audit_orders` | sidecar |
| `sidecar/services/static_ip_detector.py` | Kite static-IP check | GOES | Used only by `routers/safety.py:197` and `brokers/kite.py:44` | sidecar |
| `sidecar/services/agent_tools/broker_portfolio.py` | agent tool | GOES | It reads `brokers_registry` (lines 18, 26) | sidecar |
| `sidecar/services/agent_tools/registry_v0_6_5.py` | empty aggregator | GOES | A no-op slot reserved for Tradesa v0.6.6 "write capability" (docstring; `app.py:203-214`). Its docstring exists to keep the §6.5 order grep at zero. Trading-bot writes are gone. | sidecar |
| `sidecar/models/broker.py`, `broker_reads.py`, `safety.py`, `audit_log.py` | models (BrokerId/Mode/Order*, granular reads with margins, KillSwitch*, AuditLog*, **PositionLimits** `maxPercentOfAccount` / `dailyLossCircuitBreaker`, Disclaimer*, StaticIpStatus, AUDIT_LOG_DDL with triggers) | GOES | Imported only by the trading files and by `models/__init__.py` | sidecar |
| `sidecar/models/__init__.py` | re-exports | EDIT | Delete the imports and `__all__` entries from `models.audit_log`, `models.broker` and `models.safety` (lines 26, 39-48, 75-84, and the matching names). Delete the "Phase 5 broker/safety" lines in the docstring. | sidecar |
| `sidecar/app.py` | app factory | EDIT | Drop `brokers` and `safety` from the router import and from `_ROUTERS` (lines 27, 46, 87, 91). Delete the FR-051 comment (320-323). Delete `_register_v0_6_5_runtime_extensions` (203-214) and its call (338). | sidecar |
| `sidecar/main.py` | stdio/HTTP entry | EDIT | Delete the FR-051 broker comment (48-51) and the v0.6.5 aggregator call (63-68) | sidecar |
| `sidecar/services/agent_tools/__init__.py` | tool registry | EDIT | Remove `broker_portfolio` from the import, the `.register()` call and the log line (113-118) | sidecar |
| `sidecar/services/agent_tools/catalog.py` | **single source of truth** | EDIT | Delete the `broker_portfolio` cap (909-930) and the `propose_order` cap (1065-1089). Remove `"brokers"` from `Domain` (47) and from `TIMEOUT_HINTS` (1579). Reword the module docstring (19-23), the data-write header comment (1303-1307) and the `agent_selectable_tool_ids` docstring (1525) so they no longer mention orders. Reword the portfolio descriptions (1312-1314, 1340-1341, 1366) to "Edits the user's local tracked portfolio (manual holdings). Vysted has no brokerage connection." Also drop the "§6.5: no order path is reachable" and "no broker or order side effects" phrasing at 713 and 867. **Keep `FORBIDDEN_TOOL_SUBSTRINGS`.** | sidecar |
| `sidecar/services/agent_tools/schemas.py` | derived projection | EDIT (docstring) | Lines 13-21 describe `propose_order` and `confirm_and_place`. Replace them with a statement that host actions drive the cockpit and data writes, and that no trading tool exists. | sidecar |
| `sidecar/services/agent_runtime.py` | runtime | EDIT | **(a)** `_make_host_action` (1190-1200): delete the `propose_order` branch; the remaining autonomy logic is unchanged. **(b)** Read-back condition (1590-1596): drop `and tool_call.name != "propose_order"`. **(c)** `TERMINAL_CAPABILITIES_PREAMBLE` (170-178): replace the "Orders are never placed by you…" sentence with: `Vysted has no brokerage connection: you cannot place, stage or simulate trades. If the user asks to buy or sell, say so plainly and offer to research it or to track the holding in their local portfolio (portfolio_add_position).` Also line 164: "LOCAL paper portfolio" becomes "LOCAL tracked portfolio". **(d)** Comments at 74, 202-204, 1165-1170 and 1295: remove the order clauses. | sidecar |
| `sidecar/services/planner.py` | intent classifier | EDIT | In `_EDIT_SIGNALS`, **delete** `r"\b(market\|limit\|stop) order\b"` and `r"\bplace (an? )?order\b"`; they exist only to reach `propose_order`. **Keep** `buy(ing)?` and `sell(ing)?` because they keep the tracked-portfolio write tools available on "sell half my INFY position" (§4, Tier-3). Rewrite the comment at 76-79. | sidecar |
| `sidecar/models/agent.py`, `custom_agent.py`, `run.py`, `services/budget_guard.py`, `services/run_manager.py`, `models/llm.py:192` | comments | EDIT (comment) | Each mentions `propose_order` or orders as the reason a surface is safe (Gate-8 dry run, §3.5). Reword to "no trading path exists". | sidecar |
| `sidecar/agents/copilot.json` | first-party agent | EDIT | `tools`: remove `broker_portfolio` (9) and `propose_order` (42). `systemPrompt`: delete rule "4. PREPARE, NEVER PLACE, orders…" and renumber 5 to 4. Delete the sentence "ORDERS are the one exception … never claim you placed an order." Add one line: "Vysted has no brokerage connection; if asked to trade, say so and offer to research or track it." | sidecar |
| `sidecar/agents/portfolio_advisor.json` | first-party agent | EDIT | `tools`: remove `broker_portfolio` (11). It still reads holdings through `get_portfolio` and `get_terminal_state`, which are default-granted. | sidecar |
| `sidecar/services/bse_provider.py`, `india_provider.py`, `nse_provider.py` | India EOD providers | EDIT (copy) | The `ProviderError` text tells users to "add a BYOK broker (Kite / Upstox / Dhan)" (bse:395, india:177, nse:464, plus docstrings bse:21, india:14-15, nse:9). No broker lane exists any more, so change it to `…is not available keyless — BSE/NSE serve end-of-day data only`. Register R15-DATA-077 asks for this copy change now. Also reword `bse_provider.py:185` "(e.g. a region kill-switch)" to "(e.g. a region gate)"; the Gate-8 token grep would flag it. | sidecar |
| `sidecar/routers/history.py:21`, `sidecar/models/market.py:56-57`, `sidecar/services/bar_loader.py:32` | comments | EDIT (comment) | Remove "needs a BYOK broker" and "Phase 5 broker integrations" (mirror wording in §1) | sidecar |
| `sidecar/routers/portfolio.py`, `services/portfolio_db.py`, `models/portfolio.py` | **tracked-portfolio ledger** | STAYS (docstrings EDIT) | Written by `host-actions.ts` `syncPositionToSidecar` on every agent portfolio write. Delete "broker connection is Phase 5" (router:3-5, db:3, model:3-4). No code change. | sidecar |
| `sidecar/services/workspace_store.py` | workspace persistence (holds the portfolios) | EDIT (add) | R15-LIFECYCLE-002 fix shape ("ship it WITH the trading-removal change"): before `os.replace` in `save_workspace` (69-95), keep one `<name>.json.bak` of the previous content. Pin it with a test in `test_workspace.py`. Defense in depth for §3.1. | sidecar |
| `sidecar/requirements.txt` | deps | EDIT | Delete the "Phase 4 + 5 — broker execution SDKs" block (39-56): `dhanhq`, `smartapi-python`, `kiteconnect`, `alpaca-py`, `ib_async`, `oandapyV20`. **Keep `ccxt`**: `routers/crypto.py` and `services/ccxt_provider.py` use it for crypto data. No other module imports these SDKs or their transitive packages (checked). | sidecar |
| `sidecar/tests/gen_audit_trail.py` | capture generator | GOES | It writes the paper-trade audit JSON and imports `services.brokers` | sidecar |
| Python tests: see §3.6 and the StructuredOutput lists | tests | GOES / EDIT | 17 files deleted outright (**244 collected tests**). 9 files updated. 1 new file. | sidecar |

### 2B. Frontend, types, plugins, Rust (owner B)

| Path | Kind | Verdict | Evidence | Owner |
| --- | --- | --- | --- | --- |
| `src/modules/broker-connect/` (all 9 files: `BrokerConnectPanel.tsx`, `BrokerOrderEntry.tsx`, `BrokerReadsSection.tsx`, `broker-reads.ts`, `kite-static-ip-banner.tsx`, `index.ts`, and their 3 tests) | panels: Connections, Order Entry, paper/live mode switch, credential dialogs | GOES | Only purpose is broker connect and orders. Registered at `src/modules/index.ts:5,72`. | frontend |
| `src/modules/safety/OrderConfirmationDialog.tsx` (+test) | order review dialog (the review bar's terminus) | GOES | Mounted at `page.tsx:19,288`. Fed only by `useOrdersStore`. | frontend |
| `src/modules/safety/AuditLogViewer.tsx` (+test) | audit-log panel | GOES | Reads only `/safety/audit-log` | frontend |
| `src/modules/safety/index.ts` | module registration | EDIT | Delete `safetyModule` (the audit-log panel and its command) and the `OrderConfirmationDialog`, `AuditLogViewer` and `BrokerFirstConnectDialog` exports. Keep only `export { DisclaimerFlow, FirstLaunchTosDialog } from "./DisclaimerFlow";`. | frontend |
| `src/modules/safety/DisclaimerFlow.tsx` | first-launch terms | EDIT (STAYS) | It is the onboarding gate: `OnboardingFlow.tsx:104,125` waits on `firstLaunchTosAcked`. It is also the product's **only** "not investment advice" notice (grep). Delete `BrokerFirstConnectDialog` and `brokerHandle`. Replace `TOS_BODY`, following R15-UI-041's fix shape, with research terms: data and analysis tool, not investment advice; no brokerage connection, it cannot place, route or simulate orders; data may be delayed or wrong; AI output can be wrong; licence line (PolyForm Strict 1.0.0 noncommercial or a commercial licence, see LICENSING.md). **No kill-switch line.** The DialogDescription changes from "before connecting a broker" to "before you start". | frontend |
| `src/store/safety.ts` | store | EDIT (STAYS, trimmed) | Keep only `firstLaunchTosAcked`, `refreshFirstLaunchAck`, `ackFirstLaunchTos` and `resetSafetyStoreForTests`. Delete the kill-switch, audit, broker-first-connect, session-ack and static-IP slices, `EMPTY_STATIC_IP_STATUS`, and the `types/safety`/`types/broker` imports. Keychain account becomes `KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")`. New terms are a new key, so every user re-acks the research terms once (Tier-3, §3.10). Rewrite the header. | frontend |
| `src/store/orders.ts` (+test), `src/store/brokers.ts` (+test) | stores | GOES | Importers are only the host-actions order path and the broker-connect and safety components | frontend |
| `src/app/page.tsx` | shell | EDIT | Drop `OrderConfirmationDialog` (19, 288) and rewrite the comment at 285-287. **Keep** `<DisclaimerFlow />` and `<OnboardingFlow />`. | frontend |
| `src/modules/index.ts` | module registry | EDIT | Remove `brokerConnectModule` and `safetyModule` (imports 5 and 16; list 72-73) and their docstring paragraphs (50-58) | frontend |
| `src/lib/host-actions.ts` | host-action layer (tracked-portfolio writes live here) | EDIT | Delete `"propose_order"` from `HOST_ACTION_NAMES` (76), the `describeHostAction` case (728-741), `resolveTargetBroker` and `routeOrderProposal` (1500-1572), and the imports of `useBrokersStore`, `useOrdersStore` and `types/broker` (39, 42, 49). Fix the header docs (6-14, 62, 877). Change user-visible "paper portfolio" to "portfolio" at 769, 783, 795, 1350 and 1388; update the comments at 532 and 1254 to match (Tier-3, §3.10). **Every portfolio case is unchanged.** | frontend |
| `src/store/proposed-changes.ts` | the trust gate (STAYS) | EDIT | Delete the `routeOrderProposal` import (20). In `enqueue`, the auto-apply condition becomes `useAgentAutonomyStore.getState().autonomy === "auto"`. `accept` always runs `applyHostActionAsync` and `ackHostAction`; delete the order branch (139-146). `ackRejectedHostActions` acks every rejected change; delete the skip at 57-59. Rewrite the header (8) and the comment at 78. | frontend |
| `types/proposed-change.ts` | gate kinds | EDIT | `ProposedChangeKind` drops `"order"`. It is now `panel \| chart \| watchlist \| data-write \| settings`. Rewrite the header (1-20). | frontend |
| `src/modules/chat/ProposedChangesReview.tsx` | review bar (STAYS for the remaining kinds) | EDIT | Delete the `change.kind === "order"` notice (116-120) and the header sentence (17-18) | frontend |
| `src/modules/chat/ChatSidebar.tsx` | chat | EDIT | Line 965: `…autonomy === "auto"` (drop `&& change?.kind !== "order"`). Reword the comments at 361, 569-570, 960-963 and 1015. | frontend |
| `src/modules/chat/ComposerPlusMenu.tsx` | autonomy menu | EDIT | Line 185 hint becomes `"Changes apply instantly"`. Comment at 20. | frontend |
| `src/modules/chat/streaming.ts:173-176`, `src/store/agent-autonomy.ts:11-17`, `src/store/agent-command.ts`, `src/lib/plugin-agents.ts`, `src/modules/chat/SuggestionChips.tsx`, `src/modules/quant/index.ts:15` | comments | EDIT (comment) | Remove the order and broker clauses. Generic "§6.5 gate" wording may stay because §6.5 keeps its number (§3.7). | frontend |
| `types/broker.ts`, `types/broker-reads.ts`, `types/safety.ts` | TS contracts | GOES | Mirrors of the deleted models. Importers: stores and components that go, plus `types/marketplace.ts` (EDIT). | frontend |
| `types/marketplace.ts` | marketplace contract | EDIT | `MarketplaceCategory` drops `"broker"`. `secretNamespace` becomes `"plugin"` only. Delete `brokerId` and the `BrokerId` import (14, 17, 55, 60-63). | frontend |
| `plugins/brokers/**` (7 plugins × `index.ts`, `manifest.json`, `*.test.ts` = 21 files) | broker plugins | GOES | Imported only by `src/lib/marketplace.ts:21-34` | frontend |
| `src/lib/marketplace.ts` | catalog rows | EDIT | Delete the broker imports (21-34), `keySecretFields()` (69-75; only broker rows use it) and the 7 broker rows (185-326). Rewrite the headers (4, 11-12, 80). | frontend |
| `src/store/marketplace.ts` | marketplace store | EDIT | Delete the `secretNamespace === "broker"` branch (26-28) and the broker-disconnect helper (32-45) | frontend |
| `src/modules/marketplace/MarketplacePanel.tsx`, `src/modules/marketplace/index.ts`, `src/components/PluginManagerPanel.tsx:67` | marketplace UI | EDIT | Delete the "broker" category tab (16-18). Replace the credential-form footer (305-306) with "Stored in your OS keychain — never written to disk or logs." Remove "brokers" from the copy at 32-36, 65, index 7 and 31, and PluginManagerPanel 67. | frontend |
| `src/components/SettingsPanel.tsx` | settings | EDIT (copy) | Advanced hint (1538): drop "Broker integrations". Integrations subsection (1571, 1576): "Data providers, agent packs and panels are managed in the Marketplace." Line 1849: "API keys stay in your OS keychain". **No limits UI exists**: `maxPercentOfAccount` and `dailyLossCircuitBreaker` live only in `types/safety.ts:126-137`, which is deleted. | frontend |
| `src/lib/layout-templates.ts` | panel registry and aliases | EDIT | Delete `broker-connect`, `order-entry` and `audit-log` (51-53); the aliases `broker`, `brokers`, `connections`, `orders`, `broker-order-entry` and `audit` (84-89); and `"audit-log"` from `RAIL_PANELS` (453) | frontend |
| `src/components/PanelHost.tsx` | dockview constraints | EDIT | Delete `audit-log-viewer` (54), `broker-connect-panel` (68) and `broker-order-entry` (69) | frontend |
| `src/lib/workspace.ts` | **workspace blob, which persists the portfolios** | EDIT (required) | **R15-LIFECYCLE-002.** Today, a saved layout that references an unregistered component (after this batch: any autosave with a broker or audit panel docked) skips `deserializeWorkspace` entirely (`workspace.ts:512-515`). **The user's holdings, watchlist and notes are then lost, and the next autosave overwrites the blob.** See §3.1 for the required shape. | frontend |
| `src/lib/keychain.ts` | keychain namespaces | EDIT | Delete the `KEYCHAIN_NAMESPACES.broker` namespace (37-46). In `devKeystoreMigrationAccounts`, delete the brokers and broker-fields loops (103-115) and replace `"broker:_meta:first-launch-tos"` with `KEYCHAIN_NAMESPACES.appMeta("first-launch-terms")`. Fix the comment at 87. | frontend |
| `src/components/OnboardingFlow.tsx` | onboarding | STAYS | Still sequences on `firstLaunchTosAcked`. Comments 17-18 stay valid; only the word "§6.5 TOS" becomes "first-launch terms". | frontend |
| `src/modules/agent-builder/form.tsx:37` | custom-agent tool list | EDIT | Remove `"broker_portfolio"`. Stored custom agents that still list it degrade safely: `schemas._known` filters unknown ids, and the form's save payload filters to `KNOWN_TOOL_IDS` (`form.tsx:139-141`). | frontend |
| `src/modules/chart/ChartPanel.tsx:388` | chart empty state | EDIT (copy) | Change to "No EOD data for this symbol. BSE/NSE serve end-of-day data only; intraday/realtime is not available for this listing." (R15-DATA-077) | frontend |
| `src/modules/portfolio/PortfolioPanel.tsx:818` | portfolio empty state | EDIT (copy) | Drop "— no broker connection required", which implies a connection could exist | frontend |
| `src/components/DataBadges.tsx:7-8,33`, `src/lib/plugin-bootstrap.ts:8,217`, `src/lib/plugin-runtime.ts:303`, `src/store/portfolios.ts:10`, `src/lib/workspace.ts:72`, `types/data.ts:43`, `types/ai.ts:30,264` | comments | EDIT (comment) | Remove references to broker-connect, brokers, orders and "BYOK broker". The `ProvenanceBadge` itself stays: research, chart and watchlist use it. | frontend |
| `src-tauri/src/kill_switch.rs` | OS-wide kill-switch shortcut | GOES | It emits `kill-switch:requested`, which no listener receives (§0) | frontend |
| `src-tauri/src/lib.rs` | Tauri core | EDIT | Delete `mod kill_switch;` (2), `.plugin(kill_switch::build_plugin())` (395), `kill_switch::kill_switch_emit` in `generate_handler!` (416) and `kill_switch::register_shortcut(...)` plus its comment (443-446). Rust tests are unaffected: `kill_switch.rs` has none, so the cargo count stays at 13. | frontend |
| `src-tauri/Cargo.toml:31` and `Cargo.lock` | deps | EDIT | Delete `tauri-plugin-global-shortcut = "2"`. Re-resolve the lock offline (`cargo check --manifest-path src-tauri/Cargo.toml --offline`) and commit the pruned `Cargo.lock`. | frontend |
| `src-tauri/capabilities/default.json:8` | capability | EDIT | Delete `"global-shortcut:allow-is-registered"`; the permission would dangle once the plugin is gone. **This is not `tauri.conf.json`.** The Tier-1 list names only `tauri.conf.json`, which needs no edit (checked: no shortcut or plugin config). `gen/schemas` is git-ignored. | frontend |
| `src-tauri/src/keychain.rs:491,506` | dev-keystore migration test fixture | STAYS | The opaque account string `"broker:_meta:first-launch-tos"` is test data for a generic migration; nothing reads it. It is not in the Gate-8 token list. | frontend |
| TS tests: see §3.6 and the StructuredOutput lists | tests | GOES / EDIT | 14 files deleted outright (**100 vitest cases**). About 12 files updated. 2 new tests. | frontend |

### 2C. Docs and specs (owner C)

| Path | Kind | Verdict | Evidence | Owner |
| --- | --- | --- | --- | --- |
| `docs/BROKER_INTEGRATIONS.md` | broker guide | EDIT → one paragraph | Replace all 272 lines with: "Broker integrations were removed permanently (D81, 23 Sep 2026). Vysted has no broker connectivity, order placement or simulated account. Your manually tracked portfolio remains (Portfolio panel). History: CHANGELOG.md." The stub keeps the historical links from archive docs resolvable. | docs |
| `docs/SAFETY_ARCHITECTURE.md` | safety doc | REWRITE | It becomes the **agent-write safety model**. Outline in §3.7. All 8 order non-negotiables, the revert procedure and the file map (lines 18-246) are deleted. | docs |
| `docs/BLUEPRINT.md` | blueprint | EDIT | §2 table, §3.3 note, §4 module 29 and "Broker & Trading Plugins", §6.4, §6.5, §7 Phase 5 and 6.5, §8, §9, §10 UC1/UC6/UC7. Exact scope in §3.7. | docs |
| `docs/CURRENT_STATE.md` | baseline | EDIT | Add a dated top block "§0.x Trading removed (D81)". Update §0.5 (write surface: 18 host actions), §1 (124-131), §2 diagram (146, 156), §3.1 (211-248), the §3.2 route rows (310-315), §3.4 (416-419), §3.5 (reduce to one line), §3.6 (rewrite as the agent-write model), §3.10, §3.11 (657), the §4 tool table (729-759), §5 (784-816), §7 and §8. Also closes the doc half of R15-DOCS-016. | docs |
| `README.md` | readme | EDIT | Delete the "Read-only broker connect" bullet (42-44). Change the status line (51-52) from "§6.5 9/9 safety audit" and "BYOK/live-broker round-trip" to the Gate-8 no-trading test. Change line 183 from "broker read-only + §6.5 safety" to "agent-write safety". Add "manual tracked portfolio with P&L and CSV export" to the Portfolio mention. | docs |
| `CONTRIBUTING.md:9`, `docs/README.md:25-30`, `docs/MCP_INTEGRATION.md:118`, `docs/PLUGIN_DEVELOPMENT.md:264-360`, `docs/DESIGN_SYSTEM.md:123`, `docs/redesign/KEYCHAIN_DEV_SIGNING.md:52,183,221`, `docs/redesign/PRODUCT_DESIGN_DECISIONS.md:93,195` | current docs | EDIT | Drop broker, §6.5-execution and `broker_portfolio` mentions. In PLUGIN_DEVELOPMENT §4, the "Trading-system wrapper" becomes "Read-only wrapper plugin (external data systems)"; **the three-layer read-only rule stays**. The KEYCHAIN key name becomes `app-meta:first-launch-terms`. | docs |
| `specs/001-agent-native-redesign/spec.md` | active spec | EDIT | See §3.7 for the per-requirement edits. | docs |
| `specs/001-agent-native-redesign/plan.md` | active plan | EDIT | Lines 46, 65-68, 110, 138-139, 165, 214, 232 and 249: every "§6.5 audit 9/9" gate becomes "Gate-8 no-trading test green". The locked-file list drops the broker, safety and kill-switch files. | docs |
| `.specify/memory/constitution.md` | constitution | EDIT (**MAJOR 2.0.0**) | See §3.7. | docs |
| `BLOCKERS.md` | carry-forwards | EDIT | Close every broker, kill-switch or order item as "removed with feature (D81)". These are Phase-8 item 2 (54-59) and T5-safety-store-reset-ks, T5-broker-base-invalid-order-type, T4-brokers-not-registered, T4-connection-keychain (216-245); also the UC7 multi-broker stretch (283) and the "Write capability — Tier-4" item (442-450). Do not rewrite the history text. | docs |
| `CHANGELOG.md` | history | EDIT (append) | New top entry "R15 Stage C — trading removed (D81, 2026-09-23)": what went, what stayed, the numbers from §3.6, the register ids closed (§5), and the Tier-3 decisions (§3.10) | docs |
| `docs/redesign/DECISIONS_FOR_OPERATOR.md` | operator log | EDIT | Close 2.3, 2.4 and 2.5; supersede 1.2 (drafted text in §3.8). Add the new items listed in §3.8 and §4. | docs |
| `docs/redesign/DECISIONS.md` | decision log | EDIT (append) | One entry per Tier-3 decision in §3.10 | docs |
| `docs/redesign/CLAUDE_MD_PROPOSAL.md` | sign-off queue | EDIT (append) | Section "2026-09-23 proposal — trading removed (D81)" with the exact CLAUDE.md edits (§3.7) | docs |
| `docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json` | benchmark capture | GOES | It is the kill-switch benchmark; its test is deleted | docs |
| `docs/screenshots/v0.5.0/teammate-x/paper-trade-audit-trail.json` | paper-trade capture | GOES | Output of `gen_audit_trail.py` (deleted) | docs |
| `docs/screenshots/v0.5.0/teammate-g/README.md`, `teammate-i/README.md`, `teammate-x/README.md` | broker capture placeholders | GOES | Each describes broker-connect or paper-trade captures only | docs |
| `docs/screenshots/v0.5.0/safety-audit/*.log` (8 files) | untracked, git-ignored captures | GOES (local only) | Ignored by `.gitignore:33 *.log`; delete the directory | docs |
| `.prettierignore:32` | ignore entry | EDIT | Delete the `kill-switch-benchmark.json` line | docs |
| `docs/archive/**`, `docs/research/**`, `docs/PHASE_10_HANDOFF.md`, `docs/redesign/R*_*.md`, `REBUILD_*`, `INTEGRATION_NOTES_*`, `HANDOFF_VERIFIED.md`, `CODEBASE_AND_DESIGN_INVENTORY.md`, `docs/redesign/verification/**`, `docs/screenshots/v0.6.0/teammate-f/*`, and the historical CHANGELOG entries | history | STAYS | These are history records, not current-state claims. The CLAUDE.md rule "history belongs in CHANGELOG" applies. Gate 8 covers current surfaces and current-state docs. | docs |
| `LICENSING.md`, `LICENSE`, `COMMERCIAL_LICENSE.md` | licensing | STAYS / BLOCKED | Tier-1. `COMMERCIAL_LICENSE.md:36-48` "No warranty for trading losses" stays true (it covers decisions users make elsewhere) and makes no claim that Vysted places orders. The "broker relationship" sentence can only change on the operator's call (§3.9). | — |

---

## 3. Special-care sections

### 3.1 The tracked portfolio survives. Shared modules and their shape after removal.

**No broker dependency exists** (§0). The portfolio uses these modules, and each keeps working as follows:

| Module | What it does for the portfolio | After removal |
| --- | --- | --- |
| `src/store/portfolios.ts` | named portfolios, manual holdings, cost bases | unchanged |
| `src/modules/portfolio/{PortfolioPanel.tsx,metrics.ts,api.ts,index.ts}` | P&L and weight on live quotes, per-currency subtotals, CSV export (`PortfolioPanel.tsx:466-504` via `src/lib/csv.ts`) | unchanged except one line of empty-state copy |
| `src/lib/workspace.ts` | persists `portfolios`, watchlist and notes in the workspace blob | **must change (R15-LIFECYCLE-002)**; see the required shape below |
| `src/lib/host-actions.ts` | `portfolio_add/update/delete_position` describe and apply, and `syncPositionToSidecar` | only the order code and the broker imports go; portfolio cases unchanged; "paper portfolio" labels become "portfolio" |
| `src/store/proposed-changes.ts` | stages the portfolio writes as `data-write` | order branches go; the data-write flow is unchanged |
| `src/modules/chat/context-provider.ts` | puts the holdings into the `__terminal__` snapshot | unchanged |
| `sidecar/services/agent_runtime.py` `_build_local_tools` | `get_portfolio` returns the snapshot (1181-1182); portfolio host actions return staged or dispatched | only the `propose_order` branch goes |
| `sidecar/services/agent_tools/catalog.py` | `get_portfolio` (per_invocation) and the three `portfolio_*` host actions, domain `portfolio`, all default-granted | unchanged ids and schemas; descriptions reworded |
| `sidecar/routers/portfolio.py`, `services/portfolio_db.py`, `models/portfolio.py`, and `types/data.ts` `Position`/`PositionInput` | the secondary SQLite ledger, written on every agent portfolio write | unchanged except docstrings |
| `sidecar/services/workspace_store.py` | stores the blob | add the `.bak` on overwrite (R15-LIFECYCLE-002 fix shape) |

**Required `workspace.ts` shape (B):**

1. Split `deserializeWorkspace` into two parts: the non-layout slices (enabled modules, name, drawings, default provider, **watchlist, portfolios**, agent mode, autonomy, dock, models, notes, settings, research memory) and the dockview layout.
2. Restore the non-layout slices **first**, and never make them depend on `api.fromJSON` succeeding.
3. In `restoreLastSessionOrDefault`, the unknown-component skip path (512-515) and the catch path both restore the non-layout slices, then apply the default layout.
4. Move the unknown-component guard into the shared path so `loadWorkspace` (417-433) gets it too.
5. Optional, per the register: strip unknown panel ids from the layout instead of abandoning it. If B does not do this, the one-time layout reset is recorded in CHANGELOG.
6. **Pin:** a vitest that feeds a blob containing an unregistered `broker-connect-panel` plus holdings, notes and a watchlist, and asserts every non-layout slice is restored and no default-state POST is issued.

**Proof the portfolio keeps working.** These tests stay green and untouched:

- Python: `sidecar/tests/test_portfolio.py`
- Frontend: `src/modules/portfolio/PortfolioPanel.test.tsx` (add, edit, delete, P&L from a live quote, currencies, rename, multi-portfolio), `src/modules/portfolio/metrics.test.ts`, `src/store/portfolios.test.ts`, `src/lib/csv.test.ts`, `src/modules/chat/context-provider.test.ts`, and the `host-actions.test.ts` "portfolio host actions" block (from 946; one label regex updated)

**New tests:**

- B: `PortfolioPanel.test.tsx` "exports the active portfolio to CSV". Today no test covers the export button, and D81 lists CSV export under STAYS.
- B: the workspace restore pin above.
- A: the Gate-8 file's portfolio round trip (§3.5).

### 3.2 The proposed-changes gate: which action kinds go and which stay

| Kind | Host actions (catalog, `kind == host_action`) | Verdict |
| --- | --- | --- |
| **`order`** | `propose_order` | **GOES**. The kind leaves `ProposedChangeKind`, `describeHostAction`, `accept`, `enqueue`, the reject acks, ChatSidebar narration, ProposedChangesReview and `_make_host_action`. |
| `panel` | `open_panel`, `close_panel`, `focus_panel`, `arrange_layout`, `open_company_overview`, `publish_brief`, `write_screener_filters` | STAYS |
| `chart` | `set_chart_symbol`, `set_chart_indicators` | STAYS |
| `watchlist` | `add_to_watchlist`, `remove_from_watchlist` | STAYS |
| `data-write` | `portfolio_add_position`, `portfolio_update_position`, `portfolio_delete_position`, `write_note`, `save_layout`, `save_screen` | STAYS (tracked portfolio, notes, screens, layouts) |
| `settings` | `set_region` | STAYS |

**Totals:** 19 host actions become 18. `HOST_ACTION_NAMES` must equal the catalog set (`test_toolbelt_integrity`).

**Behaviour note for the docs:** after removal, AUTO autonomy auto-applies **every** kind (there is no exempt kind left). This is exactly today's behaviour for non-order kinds, so nothing changes, but SAFETY_ARCHITECTURE must say it plainly (R15-CODE-FRONTEND-008 and R15-DOCS-016 stay open for the policy question).

### 3.3 Kill switch: goes (the census holds at HEAD)

**Subscribers and readers at HEAD:**

- Sidecar: `broker_base.py:103` (the only subscriber); `broker_base.py:251,345` (readers); `routers/safety.py:122,138,145` (routes).
- Frontend: `src/store/safety.ts` (state and actions, never called by any component); `types/safety.ts` (types).
- Rust: `kill_switch.rs` shortcut → event `kill-switch:requested` (**no listener anywhere**); `kill_switch_emit` command (never invoked from TS).
- Terms: `DisclaimerFlow.tsx:45` promises Cmd/Ctrl+Shift+K.

**Finding:** no non-order dependency exists. The workflow engine, run manager, agent runtime and bse_provider never subscribe; the bse_provider "region kill-switch" is a comment.

**Verdict: GOES.** That covers `sidecar/services/kill_switch.py`, the `/safety/kill-switch*` routes, the `KillSwitch*` models and types, the store slice, `kill_switch.rs`, the `lib.rs` wiring, the global-shortcut dependency and its capability, and the promise in the terms.

**What the docs must now say:** "There is no kill switch; there is nothing to halt. The agent's only mutations are the staged host actions; a running Delegate run is stopped with `POST /runs/{id}/cancel`."

### 3.4 `audit_orders` goes (trading-only writers, confirmed)

**Goes:** the DDL, both `RAISE(ABORT)` triggers, the indices, `AUDIT_LOG_DB_FILENAME` and `AUDIT_LOG_NAMESPACE` (`models/audit_log.py`); `services/audit_log.py`; the `/safety/audit-log*` routes; `AuditLogViewer`; the `test_audit_log.py` suite and the audit-4 test; the `kill-switch-benchmark.json` and `paper-trade-audit-trail.json` captures and the 8 local `.log` proofs.

**Stays on users' disks:** existing `audit_log.db` files. See §4 UNSURE-1.

**The gap SAFETY_ARCHITECTURE must name** (R15-CODE-FRONTEND-013): the surviving agent-write gate has no durable record. `services/action_ledger.py` is process memory with a 10-minute TTL.

### 3.5 Replacement for the safety grep-audit: `sidecar/tests/test_no_trading_surface.py` (A)

**Why a replacement.** Nothing in `test_safety_end_to_end.py` survives: all 9 tests exercise broker adapters, the kill switch, the audit DB, disclaimers or static IP. The one generic half (no `auto_approve` / `place_*` / `submit_*` / `execute_*` id) is already held by `test_capability_catalog.test_no_forbidden_order_placing_ids_in_catalog` via `FORBIDDEN_TOOL_SUBSTRINGS` and by the per-module registry checks in the quant, analyst, sec, macro, screener and action tool tests, all of which stay. The file is deleted and replaced by one Gate-8 file.

**Path helpers:**

- Repo root via `Path(__file__).resolve().parents[2]`, the same precedent as `test_no_tradesa.py` and `test_toolbelt_integrity.py`.
- Always skip `.venv`, `node_modules`, `src-tauri/target`, `sidecar/build`, `sidecar/dist`, `.next`, `out`, `.claude`.

**Tests in the file:**

1. **`test_no_trading_routes_mounted`**
   - Build `create_app()` and collect every `route.path`.
   - Assert none matches `re.compile(r"/(brokers?|orders?|margins|safety|kill-switch|audit-log|disclaimer-[a-z-]+|static-ip[a-z-]*)(/|$)")`. Checked: today it hits exactly the 23 trading paths and no other path.
   - Assert `/portfolio/positions` serves GET and POST, and `/portfolio/positions/{position_id}` serves PUT and DELETE.

2. **`test_no_trading_capability_in_catalog_or_registry`**
   - `ID_RE = re.compile(r"(^|_)(orders?|brokers?|margins?|trades?|trading|paper|kill_?switch|audit)(_|$)")`. Checked: no surviving id matches.
   - Assert no key of any of these matches `ID_RE` or contains a `FORBIDDEN_TOOL_SUBSTRINGS` entry: `CAPABILITY_CATALOG`, `TOOL_SCHEMAS`, `models.custom_agent.KNOWN_TOOL_IDS`, `agent_tools.registered_tools()` (after `register_v0_5_0_tools()` and `register_v0_6_0_tools()`).
   - Assert `"brokers" not in typing.get_args(catalog.Domain)` and `"brokers" not in catalog.TIMEOUT_HINTS`.
   - Positive: `{"get_portfolio", "portfolio_add_position", "portfolio_update_position", "portfolio_delete_position"}` ⊆ catalog, with kinds `per_invocation` / `host_action`, and ⊆ `default_grant_tool_ids()`.

3. **`test_no_trading_tool_on_mcp_surface`**
   - List tools the same way as `test_mcp_catalog_parity._mcp_tools()`.
   - Assert no name matches `ID_RE`.
   - Assert the count equals `len(mcp_tool_ids()) + 8 runtime-only tools` (35 after removal).

4. **`test_trading_modules_are_gone`**
   - `importlib.util.find_spec(name) is None` for each of: `services.brokers`, `services.broker_base`, `services.kill_switch`, `services.audit_log`, `services.disclaimer_session`, `services.static_ip_detector`, `services.agent_tools.broker_portfolio`, `services.agent_tools.registry_v0_6_5`, `models.broker`, `models.broker_reads`, `models.safety`, `models.audit_log`, `routers.brokers`, `routers.safety`.

5. **`test_trading_files_absent`**
   - These paths must not exist: `plugins/brokers`, `src/modules/broker-connect`, `src/modules/safety/OrderConfirmationDialog.tsx`, `src/modules/safety/AuditLogViewer.tsx`, `src/store/orders.ts`, `src/store/brokers.ts`, `types/broker.ts`, `types/broker-reads.ts`, `types/safety.ts`, `src-tauri/src/kill_switch.rs`, `docs/screenshots/v0.5.0/safety-audit`.

6. **`test_no_trading_identifiers_in_source`**
   - Scan: `sidecar/**/*.py`, `sidecar/agents/*.json`, `sidecar/requirements.txt`, `src/**/*.{ts,tsx}`, `types/*.ts`, `plugins/**/*.{ts,json}`, `src-tauri/src/**/*.rs`, `src-tauri/Cargo.toml`, `src-tauri/capabilities/*.json`.
   - Exclude `sidecar/tests/**` and `*.test.*`.
   - Exempt exactly **one** file, `types/plugin.ts`, with the reason in-line: Tier-1 locked, holds a `tradesa.kill-switch` JSDoc example and the `"trading-bot"` PluginType, BLOCKED-FOR-OPERATOR.
   - Fail on any of these case-sensitive literal tokens: `propose_order`, `confirm_and_place`, `_place_confirmed`, `routeOrderProposal`, `BrokerAdapter`, `BrokerOrder`, `BrokerState`, `BrokerId`, `BrokerConnect`, `BrokerFirstConnect`, `broker_portfolio`, `brokers_registry`, `useBrokersStore`, `useOrdersStore`, `OrderConfirmation`, `AccountSummary`, `margins_info`, `holdings_info`, `positions_info`, `KillSwitch`, `kill_switch`, `killSwitch`, `kill-switch`, `global_shortcut`, `global-shortcut`, `audit_orders`, `AuditLog`, `audit_log`, `PositionLimits`, `maxPercentOfAccount`, `dailyLossCircuitBreaker`, `first-live-order`, `/brokers/`, `/safety/`, `static_ip`, `StaticIp`, `kiteconnect`, `dhanhq`, `smartapi`, `alpaca-py`, `ib_async`, `oandapyV20`.
   - `place_order`, `submit_order` and `execute_order` are deliberately **not** tokens here, because `FORBIDDEN_TOOL_SUBSTRINGS` must spell them. They are covered at the id level in test 2.
   - A dry run of this scanner at HEAD (planner scratchpad) flags only files this plan already edits or deletes. The complete list of surviving hits the writers must clear: `copilot.json`, `portfolio_advisor.json`, `app.py`, `main.py`, `models/__init__.py`, `models/agent.py`, `models/custom_agent.py`, `models/run.py`, `requirements.txt`, `agent_runtime.py`, `agent_tools/__init__.py`, `catalog.py`, `schemas.py`, `bse_provider.py:185`, `budget_guard.py`, `planner.py`, `run_manager.py`, `Cargo.toml`, `capabilities/default.json`, `lib.rs`, `page.tsx`, `host-actions.ts`, `marketplace.ts` (both lib and store), `agent-builder/form.tsx`, `modules/index.ts`, `modules/safety/{DisclaimerFlow,index}.tsx?`, `agent-autonomy.ts`, `proposed-changes.ts`, `store/safety.ts`, `types/ai.ts`, `types/marketplace.ts`, `types/proposed-change.ts`.

7. **`test_proposed_change_kind_has_no_order`**
   - Regex-extract the `ProposedChangeKind` union from `types/proposed-change.ts` and assert `"order"` is absent.
   - Assert `{"panel","chart","watchlist","data-write","settings"}` are present.

8. **`test_tracked_portfolio_roundtrip`**
   - Using `temp_data_dir` and `client`: POST `/portfolio/positions` `{symbol:"AAPL",quantity:10,cost_basis:150}` returns 201; GET lists it; PUT (quantity 12) returns 200; DELETE returns 204; GET is empty.
   - This makes the second half of Gate 8 provable from this one file.

### 3.6 Roster, parity and count assertions: old → new

| Assertion | Before | After | Change needed |
| --- | --- | --- | --- |
| Agent roster (`test_agent_runtime.py:95,212`, `test_agents_router.py:41`, `test_mcp_server.py:132`, smoke `/agents > 0`) | 13 | 13 | **none** |
| Catalog size / internal / default_grant | 50 | 48 | none hard-coded |
| `read_handler_ids()` (registry parity, `test_capability_catalog`) | 29 | 28 | derived; passes once the handler and the cap are both gone |
| Catalog→MCP projection (`test_mcp_catalog_parity`) | 28 | 27 | derived; none |
| MCP `tools/list` (smoke prints `toolCount`; `test_mcp_server.py:40` asserts `>= 8`) | 36 | 35 | none (the new Gate test pins 35 through the derivation) |
| Host actions (`test_toolbelt_integrity.FINAL_HOST_ACTION_IDS`, `host-actions.test.ts:43-66`) | 19 | 18 | **update both lists**: drop `propose_order` |
| `copilot.json` tools list | includes `broker_portfolio` and `propose_order` | without them | edit the JSON |
| `portfolio_advisor.json` tools list | includes `broker_portfolio` | without it | edit the JSON |
| Frontend `agent-builder` `KNOWN_TOOL_IDS` | 20 | 19 | the test is derived; none |
| `test_agent_runtime._COPILOT_MUTATORS` | `{open_panel, set_chart_symbol, add_to_watchlist, propose_order}` | replace `propose_order` with `portfolio_add_position` (still 4 mutators, still a default grant) | update |
| `test_capability_catalog.py:164-165` | `CAPABILITY_CATALOG["propose_order"].read_only is False` | `…["portfolio_delete_position"].read_only is False` (the most destructive surviving mutation) | update |
| `test_no_tradesa.test_plugin_system_alive` | ≥5 ids from `plugins/*` and `plugins/brokers/*` manifests | ≥5 from `plugins/*` only (exactly 5 remain: example, openbb-mcp, vysted-lenses, vysted-news, yfinance) | drop the brokers glob and the dead `sidecar/services/audit_log.py` exemption; the threshold is **not** lowered |
| Sidecar routes | 117 unique paths | 94 | none hard-coded |
| pytest total | baseline | −244 (deleted files) −4 (individual order tests and param cases) +8 (Gate 8) +1 (workspace .bak) | report the actual numbers at the gate |
| vitest total | baseline | −100 (deleted files) −15 (order, kill-switch, audit, session, static-IP and broker cases in updated files) +3 (terms body, workspace restore, CSV export) | report the actual numbers at the gate |
| cargo tests | 13 | 13 | none |

### 3.7 Docs rewrite scope (C)

**BLOCKED-FOR-OPERATOR items are listed in §3.9, not here.**

#### SAFETY_ARCHITECTURE.md → "Vysted Terminal — Agent-Write Safety (BLUEPRINT §6.5)"

1. **What the terminal can and cannot change.**
   - It cannot connect to a broker or place, stage or simulate orders, and it has no simulated account. This is pinned by `sidecar/tests/test_no_trading_surface.py` (D81).
   - It can run the 18 catalog host actions (table by kind, §3.2).
2. **The proposed-changes gate.**
   - Files: `src/store/proposed-changes.ts`, `src/lib/host-actions.ts`, `ProposedChangesReview.tsx`.
   - ASK stages everything. AUTO applies every kind on enqueue.
   - A persisted AUTO restores with the workspace (`workspace.ts`).
3. **Honest narration and read-back.** `agent_runtime._build_local_tools` (`awaiting_user_review` vs `dispatched`), `action_ledger` (`/agents/actions/ack`), the divergence notice.
4. **Read-intent strip.** `planner.classify_intent` plus `_READ_SAFE_PANEL_ACTIONS`; `read_only` comes from the catalog.
5. **No hands on its own leash.** `test_toolbelt_integrity` forbidden substrings; `FORBIDDEN_TOOL_SUBSTRINGS`.
6. **Spend ceiling.** `BudgetGuard` for Delegate runs; `POST /runs/{id}/cancel`.
7. **Plugins.** Host-enforced; the read-only-wrapper three-layer rule for data plugins (no mutating methods, GET-only routers, `supportsControlPlane=false`).
8. **Secrets.** Keychain BYOK and loopback.
9. **Accepted gaps, stated explicitly:** no durable record of agent writes; no stop control for AUTO beyond reject or run-cancel (R15-CODE-FRONTEND-013, R15-CODE-FRONTEND-008).
10. **History.** The order non-negotiables were removed by D81; see CHANGELOG and git before the removal commit.

#### BLUEPRINT.md

- **TL;DR / v1.0 scope:** drop Tradesa and trading claims.
- **§2:** replace the "Broker execution" row with `Trading | None — no broker connectivity, order placement or simulated account (D81, operator, 23 Sep 2026)`. **Drop it outright; never write "deferred".**
- **§3.3:** the `pluginType` line mirrors the locked `types/plugin.ts`, so leave it and add a note that it is BLOCKED.
- **§4:** delete module "29. Paper trading sandbox engine"; set Portfolio & Risk to (2); fix the module totals; delete the "Broker & Trading Plugins" subsection (287-309).
- **§6.4:** becomes "Liability". Keep "tool, not financial advice", no warranty, and "Vysted is not a broker". Delete "places live orders".
- **§6.5:** retitle it "Agent-write safety" and **keep the §6.5 number**, because 60+ code comments say "§6.5 gate" for the proposed-changes gate. Make it a short summary that points to SAFETY_ARCHITECTURE.
- **§7:** collapse Phase 5 to "shipped v0.5.0; removed permanently by D81 (23 Sep 2026) — history in CHANGELOG". Phase 6.5 (Tradesa) gets the same treatment ("removed (E11/D81)").
- **§8:** delete the Tradesa criterion; change "All 38 modules" to 37.
- **§9:** delete "Additional broker plugins" (v1.1) and "Multi-bot plugins (Forge Bot…)" (v2.0).
- **§10:** in UC1, drop the Tradesa step. Reframe UC6 as data and analytics plugin authors. Delete UC7 (Multi-Broker).

#### spec.md

- FR-010: drop "order".
- FR-011: REMOVED (D81).
- FR-012: becomes "agent-write safety model + Tier-1 files preserved unless operator-ratified; the Gate-8 test is a hard gate".
- FR-042, FR-051, FR-052 and SC-012: REMOVED (D81).
- FR-050: drop "brokers".
- FR-055: "no plugin can bypass the host agent-write gate; read-only wrapper rule". Remove paper mode, the kill switch, position limits and the audit log from it.
- SC-013: "a plugin (data-source, panel, agent)" instead of "a broker".
- SC-014: drop "order placement".
- Clarifications (lines 17, 74-117), US10 (525-528) and line 714: remove the broker and order text.

#### constitution.md: MAJOR 2.0.0

- Principle II: line 29 drops "brokers" from the capability list. Line 35 changes "finance agents and trade-bots" to "finance agents and research tools".
- Principle III loses the audit-log, type-gated-execution and kill-switch bullets and "Orders never auto-apply". It keeps: read-only default; the preview→applied diff gate; the read-only wrapper rule; BudgetGuard; and "no trading path exists (D81)".
- Principle VI line 81 changes from "Every mutation lands in the append-only audit trail" to the true statement: acked to the action ledger; durable record is an accepted gap.
- Line 113: drop "paper".
- Line 130: drop "Kite".
- Line 134: "broker order execution is out of the product permanently (D81)".
- Add a v2.0.0 amendment comment citing D81 as the operator ratification.
- Propagate to spec.md.

#### CLAUDE_MD_PROPOSAL.md: exact CLAUDE.md edits to queue

- **Layout:** `src-tauri/` drops "kill-switch". `plugins/` becomes "(openbb-mcp, yfinance, vysted-news, vysted-lenses, example)".
- **Decision authority, Tier 1:** the ⚠️ sentence becomes "Trading (broker connectivity, orders, simulated accounts) was removed permanently by D81 (23 Sep 2026)."
- **Tier-1 invariants:** replace the four §6.5 bullets (audit log, type gate + grep, kill switch, read-only trading wrappers) with "§6.5 agent-write safety model (docs/SAFETY_ARCHITECTURE.md) — proposed-changes gate, read-intent strip, no-trading invariant pinned by `sidecar/tests/test_no_trading_surface.py`".
- **Plugin contract:** "trading-wrapper" becomes "wrapper"; the rule itself stays.
- **Gotchas → Copilot:** drop "orders still never auto-apply" from the research auto-publish bullet.
- **Gotchas → Broker & credentials:** rename to "Credentials". Delete the "Kite Connect read-only login" and "Granular broker reads" bullets. In the BYOK bullet, change "read-only plugins" to "plugins".
- **Gotchas → Frontend:** add "`deserializeWorkspace` restores non-layout slices independently of the dockview layout — an unknown panel never costs user data (R15-LIFECYCLE-002)".
- **Reference docs:** drop BROKER_INTEGRATIONS.md.

### 3.8 DECISIONS_FOR_OPERATOR: closing text (C pastes it verbatim)

> **2.3 — CLOSED: removed with the feature (D81, 23 Sep 2026).** The census held at HEAD `99e2ae3`:
> the kill switch's only subscriber was `BrokerAdapter.__init__` (`broker_base.py:103`), and its only
> readers were the order gates (`:251,:345`). No UI component fired it. Nothing listened for the Rust
> `kill-switch:requested` event. With no orders left, there was nothing to halt, so the mechanism was
> deleted rather than bound: `kill_switch.rs`, the `tauri-plugin-global-shortcut` dependency and its
> capability, `services/kill_switch.py`, the `/safety/kill-switch*` routes, the store slice and the
> types. The first-launch terms no longer promise Cmd/Ctrl+Shift+K. They are now research-only terms
> (R15-UI-041). This also closes R15-CODE-PLATFORM-001/006/007/008/009/031/032/033, R15-CROSS-PLATFORM-005
> and R15-LIFECYCLE-016. **Undo:** revert the removal commits (this restores the whole trading layer).
>
> **2.4 — CLOSED: removed with the feature (D81).** The paper→live switch
> (`BrokerConnectPanel.tsx:246-249`), `POST /brokers/{id}/mode`, the Connections panel and paper mode
> itself (synthetic fills, the placeholder account) are deleted. There is no mode left to confirm.
>
> **2.5 — CLOSED: removed with the feature (D81).** `PositionLimits` (`maxOrderValueAccountCurrency`,
> `maxPercentOfAccount`, `maxPositionSizePerSymbol`, `dailyLossCircuitBreaker`) is deleted from
> `sidecar/models/safety.py`, `types/safety.ts` and `BrokerAdapter.DEFAULT_LIMITS`. No settings surface
> ever exposed it, and there are no orders left to limit.
>
> **1.2 — SUPERSEDED (D81).** `test_safety_end_to_end.py` and the tracked
> `kill-switch-benchmark.json` baseline are both deleted with the feature, and
> `VYSTED_REFRESH_SAFETY_CAPTURES` no longer exists. There is nothing to revert.

**New entries C adds:**

- UNSURE-1 (user-side leftovers, §4).
- The first-launch terms rewrite plus the new keychain account. This is operator review of text on a formerly §6.5 surface, including licence wording (R15-UI-041 flagged it Tier-4).
- The accepted agent-write gaps (R15-CODE-FRONTEND-013).
- Every BLOCKED item in §3.9.

### 3.9 BLOCKED-FOR-OPERATOR (Tier-1): no edit is planned

| Item | Why it is blocked | What the operator would decide |
| --- | --- | --- |
| `types/plugin.ts` | Locked plugin contract. `PluginType = "trading-bot" \| …` (line 28). JSDoc examples `tradesa.kill-switch`, `tradesa kill`, "Tradesa V2 (Bybit testnet)" (lines 80-223). | Keep the `"trading-bot"` literal and the examples, or remove them (a contract change that breaks plugins). The Gate-8 scan exempts this file only. |
| `CLAUDE.md` | Tier-1; holds an uncommitted operator edit | Apply the queued `CLAUDE_MD_PROPOSAL.md` section (§3.7) |
| `COMMERCIAL_LICENSE.md:36-48` | Licensing | Optional: drop "responsible for their own broker relationship". The clause is still true, so no change is required. |
| `src-tauri/tauri.conf.json`, `.github/**`, `LICENSE*`, `r15-fanout.js` | Tier-1 or instructed not to edit | **No edit is needed.** Verified: no shortcut, broker or safety content. Listed so the "no Tier-1 edit" claim is checkable. |

### 3.10 Tier-3 decisions made in this plan (C records each in DECISIONS.md and CHANGELOG)

1. **The first-launch terms dialog stays and is rewritten** as the onboarding gate. The new keychain account `app-meta:first-launch-terms` means everyone re-acks once, because the terms changed. This follows the R15-UI-041 fix shape.
2. **Planner:** keep the `buy` and `sell` edit signals (they serve tracked-portfolio edits); delete the order-phrase signals.
3. **Wording:** "paper portfolio" becomes "portfolio" in user-visible labels and agent-facing descriptions. After D81, "paper" would read as a simulated brokerage account. The tool ids are unchanged.
4. **BLUEPRINT keeps §6.5 as the number** for the agent-write safety model.
5. **`registry_v0_6_5.py` is deleted:** it was an empty slot reserved for trading-bot writes.
6. **The R15-LIFECYCLE-002 restore fix ships with the removal:** workspace.ts restore order plus the sidecar `.bak`.
7. **India EOD-only copy no longer points at a broker** (the copy half of R15-DATA-077).
8. **No automatic purge of user-side leftovers.** This is an operator item (§4).

---

## 4. STAYS (with reasons) and UNSURE

**STAYS.** Each item has another feature depending on it, or is not a trading path:

- **Tracked portfolio.** The whole §3.1 set: portfolios store, PortfolioPanel with P&L and CSV, metrics, context provider, the portfolio router/db/models (the secondary ledger written by `syncPositionToSidecar`), the `get_portfolio` and `portfolio_*` capabilities, and the `data-write` kind.
- **The proposed-changes gate and review bar**, for the panel, chart, watchlist, data-write and settings kinds (§3.2).
- **`FORBIDDEN_TOOL_SUBSTRINGS`** and every test that uses it: `test_capability_catalog`, and the quant, analyst, sec, macro, screener and action tool tests. They still guard that no placement tool id ever appears.
- **`test_toolbelt_integrity._FORBIDDEN_SURFACE_SUBSTRINGS`** (`broker_config`, `kill_switch`…). It guards against a capability over the agent's own leash, which still matters.
- **The read-only-wrapper plugin rule** (three layers). Operator instruction: it is the contract rule for future data plugins.
- **`supportsControlPlane` and the control-plane capability.** They are used by `plugins/example` (`supportsControlPlane: true`), and the contract is Tier-1.
- **`first-launch` terms dialog and the trimmed `src/store/safety.ts`.** Onboarding sequences on the ack, and the dialog is the only in-app not-advice notice.
- **`DataBadges.ProvenanceBadge`** (`synthetic`, `prefix`). Research, chart and watchlist render it.
- **`ccxt`.** Crypto quotes, history and stream (`routers/crypto.py`).
- **Backtest engine and strategies.** Historical research, not order placement (R15-DATA-009 says so explicitly); no broker import.
- **`action_ledger.py`.** The host-action read-back.
- **`budget_guard.py` / `run_manager.py`.** Only their comments change.
- **Planner `buy` and `sell` signals.** They keep the portfolio write tools available.
- **`scripts/git-hooks/pre-push` `broker-secret-literal` and `scripts/r15/history_secrets_scan.py`.** Generic `api_secret`/`access_token` secret scans over history, which still contains broker code.
- **`scripts/r15/route_fuzz.py` denylist** (`/orders`, `/kill-switch` …). It self-asserts a denylist, not route existence, so it is inert once the routes are gone. `scripts/r15/register.py` is census tooling.
- **`scripts/smoke-test-sidecars.mjs`.** No count is hard-coded; it will print `toolCount=35`.
- **`src-tauri/src/keychain.rs` test fixture string.**
- **The OpenRouter "broker" wording** (`models/llm.py:25`, `llm/__init__.py:43`, `native_search.py`, `openrouter_catalog.py`, `SettingsPanel.test.tsx:294`). It means a model broker; this is a false positive.
- **Every "margins" hit in fundamentals, screener, yfinance and company_narrative.** These are profit margins; false positives.
- **Historical docs** (§2C last rows).

**UNSURE.** Removed from every surface; code kept (none here); listed in DECISIONS_FOR_OPERATOR.

- **UNSURE-1 — user-side leftovers after upgrade.** This is data, not code. No code reads any of it after removal, so nothing is user- or agent-facing. The items:
  - `~/.vysted-terminal/audit_log.db`: the user's own historical order and paper audit rows.
  - OS-keychain `broker:<id>:api_key|api_secret|access_token|client_id` and `broker:<id>:_meta:first-connect-ack`: live BYOK broker secrets, now orphaned.
  - `broker:_meta:first-launch-tos` (the old ack).
  - Sidecar plugin-store rows for the 7 broker plugin ids. `plugin-bootstrap` iterates `CATALOG_ROWS` only, so they are ignored.

  Deleting a user's secrets and audit history automatically is destructive and irreversible, so **this batch adds no purge code.** Recommendation for the operator: approve a one-time "remove leftover broker credentials" step, plus a CHANGELOG note telling users how to delete `audit_log.db` and the keychain entries by hand.

No code item was left UNSURE. Every code path was decidable against the rule.

---

## 5. Register entries this batch closes or touches

**Closed by deletion:**

- R15-CODE-PLATFORM-001, -006, -007, -008, -009, -031, -032, -033
- R15-CROSS-PLATFORM-005
- R15-LIFECYCLE-016
- R15-DATA-091
- R15-UI-042, R15-UI-043
- R15-DOCS-001 (SAFETY_ARCHITECTURE rewritten)
- R15-CODE-FRONTEND-013: resolved by deletion, with the gap accepted in writing.
- The `broker_portfolio` half of R15-AGENT-067.
- The broker half of R15-DOCS-015.

**Fixed in this batch:**

- R15-UI-041 (terms rewrite and shortcut deletion)
- R15-LIFECYCLE-002 (restore order)
- The copy half of R15-DATA-077

**Still open:**

- R15-UI-044 (surviving terms-dialog hydrate catch)
- R15-CODE-FRONTEND-008
- R15-DOCS-016 (partially addressed by the CURRENT_STATE edits)
- The vendor half of R15-DATA-077

---

## 6. Integration gate (run after A, B and C merge)

`export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`, then:

1. `cargo check --manifest-path src-tauri/Cargo.toml --offline` to prune `Cargo.lock`.
2. `pnpm ci-local` in the background, tracked by job id. It must be green.
3. `node scripts/smoke-test-sidecars.mjs`. Expect 13 agents and `toolCount=35`.
4. `cd sidecar && .venv/bin/python -m pytest tests/test_no_trading_surface.py tests/test_portfolio.py tests/test_toolbelt_integrity.py tests/test_capability_catalog.py tests/test_mcp_catalog_parity.py -q`.
5. `git grep -nE 'propose_order|kill_switch|audit_orders|/brokers/' -- ':!docs/archive' ':!docs/research' ':!docs/redesign/verification' ':!CHANGELOG.md' ':!sidecar/tests'`. It must return only `types/plugin.ts` (BLOCKED) and the history docs that §2C marks STAYS.
