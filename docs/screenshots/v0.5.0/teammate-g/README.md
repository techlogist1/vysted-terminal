# Teammate G — global broker screenshots (v0.5.0)

Coordination note: per the v0.5.0 mega-sprint plan, populated
broker-connect screenshots require Teammate S's `BrokerConnectPanel`
to be present in the integrated build. Teammate G owns the three
global broker adapters and plugin shells; the broker-connect UI is
S-owned.

**Capture protocol (deferred to lead integration):**

At lead-merge time, after Teammates G + I + X + S worktrees are
integrated and `pnpm tauri dev` runs cleanly:

1. Connect Alpaca in paper mode (uses free paper keys).
2. Connect OANDA in demo mode (uses free fxTrade demo).
3. Attempt IB connection without TWS / IB Gateway running — the panel
   should render the graceful "TWS or IB Gateway not detected on
   127.0.0.1:7497 — start TWS (or IB Gateway) and retry" message
   surfaced by `IBAdapter._connect`. The UX shape is the deliverable;
   a live IB connection is NOT required for the screenshot.
4. Capture the `BrokerConnectPanel` at **1920×1080** and **2560×1440**
   via chrome-devtools MCP `resize_page`. File names:
   - `alpaca-paper-connected-1920x1080.png`
   - `alpaca-paper-connected-2560x1440.png`
   - `oanda-demo-connected-1920x1080.png`
   - `oanda-demo-connected-2560x1440.png`
   - `ib-tws-not-detected-1920x1080.png`
   - `ib-tws-not-detected-2560x1440.png`

Per CLAUDE.md visual-verification protocol: panels must show
populated state, not empty defaults. For brokers, "populated" means
the connection status row + the account-summary placeholder (or the
TWS-not-detected error for IB) is rendered with real text.

Per CLAUDE.md screenshot-organisation rule: this folder is the
canonical record for the Teammate-G surface at the v0.5.0 release;
do not overwrite these files on a future patch — create a sibling
folder `v0.5.0-<descriptor>` instead.
