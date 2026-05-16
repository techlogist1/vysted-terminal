# Teammate-I screenshots — deferred to integration

Per `BLOCKERS-I.md`, the two screenshot deliverables for Teammate I
require Teammate S's `BrokerConnectPanel.tsx` to be merged first. The
lead captures these at integration:

1. **`broker-connect-paper-1920.png`** — `BrokerConnectPanel` with Dhan,
   Angel One, and Kite all connected in paper mode. 1920×1080.
2. **`broker-connect-paper-2560.png`** — same, 2560×1440.
3. **`kite-static-ip-mismatch-1920.png`** — Kite live mode with the
   static-IP banner in the mismatch state. 1920×1080. Temporarily patch
   `services.static_ip_detector.detect_public_ip` to return a fake IP
   that does not match the demo configured static IP.
4. **`kite-static-ip-mismatch-2560.png`** — same, 2560×1440.

Capture via the `chrome-devtools` MCP `resize_page` per the project
visual-verification protocol.
