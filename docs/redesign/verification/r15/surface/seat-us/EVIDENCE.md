# seat-us — bug-bash evidence (R15 wave 2)

Seat: a US-stock user who also holds Indian ADRs (US large/small caps, ETFs, SEC filings +
insider, options/greeks, earnings calendar, USD vs INR, mixed India+US compare/watchlist).

Rig: own sidecar from source on `127.0.0.1:52213`, data dir `/tmp/claude-501/r15-seat-us/data`
(sqlite `.backup` copy of the operator's dir, keyless keystore seed). For parity with the shipped
app (where the Tauri core spawns both MCP children) I ALSO started my own copies of the two
bundled MCP binaries — sec-edgar on `:53213`, openbb on `:53214` — and exported
`VYSTED_SEC_EDGAR_MCP_PORT` / `VYSTED_OPENBB_MCP_PORT` to my sidecar; without them `/sec/*` 501s
and every SEC finding would be a rig artifact. Machine load average was ~380 during the run
(parallel fan-out), so wall-clock latencies here are upper bounds, not product numbers.

Fresh symbols used (none in BATTERY_EXCLUSIONS): COST, LLY, AVGO, JPM (large); CELH, RKLB, HIMS,
IONQ (small/mid); VTI, SCHD, IWM, INDA, EPI, TLT (ETFs); WIT, MMYT, SIFY, YTRA (Indian ADRs /
US-listed Indian cos); WIPRO (NSE side of the WIT pair).

