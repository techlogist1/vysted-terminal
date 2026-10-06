# batch-28/W2-sonnet (set-76, rc1-battery-16)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52356`. Raw output:
`battery/raw/set-76/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-027 | In-process `services.agent_tools.research._research({"query": q, "depth": "normal"})` against the candidate's own `sidecar/.venv`, with `agent_tools.register_v0_5_0_tools()`/`register_v0_6_0_tools()` called first (the same bootstrap `main.py` runs) so the real tool registry (news/price/fundamentals/filings/web) is live, not empty. Register's own repro symbols (Saksoft, Tata Elxsi). | Saksoft: **8.13s**. Tata Elxsi: **8.41s**. Both well under the <=15s FR-070 target and close to batch-28's own fresh-case numbers (KPIT 6.7s, Persistent 8.6s). The per-leg timeout fix is visible in the payload: `structured.price.error: "price timed out after 6s — dropped"`, `structured.fundamentals.error: "fundamentals timed out after 6s — dropped"` — a slow leg is dropped at a stated per-leg budget rather than blocking the whole gather to 33-38s as the pre-fix entry described. | holds |
| R15-DATA-113 | Live `GET /earnings/WIT/estimates` (the register's own literal repro) + `GET /earnings/INFY.NS/estimates` (sanity, single-currency case) | WIT: `"currency":"USD","revenue_currency":"INR"` — `revenue_estimate_mean` 244,747,656,810 is now correctly labelled INR (Wipro's reporting currency; the number is Wipro's real INR revenue scale), separate from the ADS trading currency USD carried by `eps_estimate_mean`. INFY.NS: `currency` and `revenue_currency` both `"INR"` (no mismatch case, as expected — single-currency filer). The response now carries a dedicated `revenue_currency` field distinct from `currency`, exactly the certified fix shape (BABA/KPIT probes hit an unrelated live `provider_error` from yfinance this run — recorded as an environment note, not part of this entry's own WIT repro, which reproduced cleanly). | holds |

COVERAGE: 2/2 ids raw; no raw: none.
