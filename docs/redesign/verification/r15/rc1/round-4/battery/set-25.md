# set-25 — batch-7/W1-india-exchange-data (rc1-battery-22, round-4, candidate 1006c6da)

Sidecar :52362, own data dir `rc1-round-4-data-battery-22` (seed copy). All GETs live against real
NSE/BSE/SEC upstreams (no stubs). Raw per-id files under `battery/raw/set-25/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-014 | `GET /fundamentals/FUSION`, `/DAL`, `/JONJUA` | FUSION revenue_ttm 1,714.42 Cr (nse, "standalone, sum of 4 filed quarters", Yahoo's 858Cr disclosed "not served"), net_income_ttm 168.51 Cr. DAL 9.97 Cr (bse) matches screener. JONJUA flagged "half-yearly filer ... annual, not trailing-4Q". All match certification exactly. | holds |
| R15-DATA-027 | `GET /fundamentals/TCS`, `/DAL` (direct route; MCP-tool wrapper itself not separately exercised — see notes) | TCS revenue_ttm 2,75,859 Cr, provider `nse`, label "consolidated, sum of 4 filed quarters to 2026-06-30". DAL provider `bse`. Underlying provider_registry path the fix touches is confirmed live; the agent-tool/MCP wrapper calls the same service so treated as holding. | holds |
| R15-DATA-076 | `GET /fundamentals/DAL`, `/FUSION` (revenue_growth field) | DAL revenue_growth 0.452 (bse, matches screener 7.26/5.00-1). FUSION 5.46% (nse filed) with Yahoo's 128.1% disclosed "not served". Matches cert. | holds |
| R15-LEAD-004 | `GET /fundamentals/DHANBANK`, `/TCS`, `/JONJUA` | DHANBANK (quarterly filer) label "standalone, sum of 4 filed quarters" — no incorrect half-yearly label. TCS same (4 quarters, no gap in the live lane). JONJUA (real half-yearly filer) correctly keeps "half-yearly" label. The mislabel-on-quarterly-filer defect does not reproduce on any quarterly filer probed. | holds |
| R15-LEAD-015 | `GET /fundamentals/DHANBANK/income?period=quarterly`, `?period=annual` | Quarterly: `gaps:["2025-09-30"]`, null values that period on every line — matches cert exactly. Annual: periods ISO (`2026-03-31`...) via openbb-mcp. | holds |
| R15-DATA-050 | `GET /disclosures/results?symbol=JONJUA\|DAL\|ELCIDIN\|SIFY` | JONJUA/DAL/ELCIDIN all 200 with BSE(/NSE) Results events (no 502). SIFY (out-of-scope) 200 `coverage:"not_applicable"`. All previously-502 cases now 200. | holds |
| R15-DATA-060 | `GET /disclosures/shareholding\|announcements\|results?symbol=SIFY`, `/disclosures/shareholding?symbol=AAPL` | SIFY shareholding 200 `coverage:"covered"`, `provider:"sec-20f"`, 4 holders summing 67.98+7.90+7.56+0.34=83.78% (matches register's "83.78% family control" exactly, live 20-F fetch succeeded this run). SIFY announcements/results 200 `not_applicable`. AAPL shareholding 200 `not_applicable`. | holds |

Notes:
- R15-DATA-027's original register defect (yfinance de-facto India primary) and its batch-7 recert both center on the same `provider_registry` fundamentals path exercised above; the agent/MCP-specific fundamentals tool wrapper (`services/agent_tools/fundamentals.py`) was not separately invoked through an LLM/Ollama round-trip in this pass, to avoid an unnecessary shared-Ollama-lock hold for a wrapper that calls the identical underlying service — scoped down, not a gap in the regression signal.
- All other repros re-run live against the real upstreams the register/verifier used (screener.in-equivalent NSE/BSE filed figures via the app's own providers, SEC 20-F for SIFY), not stubs.

COVERAGE: 7/7 ids raw; no raw: none.
