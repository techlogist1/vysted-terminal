# final-drive-portfolio-notes log

head d38b5d1a; own sidecar :52844 (sh 80951, sleep pid 80953), data final-data-final-drive-portfolio-notes; shared :52800 read-only.
- Since rc1 round-2 (4c6dfe8c) the group surface changed in 12 files: fixes R15-UI-079, R15-UI-078, R15-AGENT-091, R15-CROSS-PLATFORM-006, R15-CODE-PLATFORM-050/051/052, R15-DOCS-010, R15-CODE-FRONTEND-024.
- jsdom harness (scratch fdpn/vt, config root final-cand, jsdom url localhost:5173, node_modules symlink): portfolio 9/9, notes 7/7, P8 1/1 run; replays copied to surface/portfolio-notes/final/.
- P2: whitespace-only cost "   " saves as costBasis 0 (validateHolding checks === "" only); "0x10" qty saves as 16.
- P5/P6: an unknown (404) symbol raises the transport-failure banner "Couldn't refresh live quotes"; same at rc1, not in register.
- P8: 100 holdings on own sidecar: 77/100 quote GETs abort at the 30 s client budget (SIDECAR_REQUEST_TIMEOUT_MS, added by R15-LIFECYCLE-027 f1182138 after rc1); census/rc1 had 100/100 200.
- P9: panel-closed store fallback stamps AAPL (USD) as currency INR (fallbackCurrency = region default) -> R15-AGENT-091 repro still mislabels.
- HTTP: /portfolio/positions GET-only (POST 405, PUT/DELETE 404), no order route in openapi.
- 16:41 Ollama lock taken for A1 (AGENT-091 live turn).
- A1 (llama, panel-closed snapshot, correct snake_case wire): "AAPL - 2 shares, cost basis Rs190" -> regression of R15-AGENT-091 confirmed live. A1x/A1y = harness wire-shape mistakes, kept.
- A3 (AUTO, injection-shaped general note): read_notes then a summary; no write tool call. A2 (AUTO, delete TCS with 2 lots): placeholder position_id, staged awaiting review.
- P8b cold 100: 0/100 resolved over 210 s; own-sidecar RELIANCE quote timed out until 16:47:17 (first 200), about 4 min after unmount.
- Findings: 4 (2 high regressions, 1 medium new, 1 low regression). Nothing attached, no KL instance, no NEEDS_GUI entry beyond the listed R15-UI-083/R15-UI-009 export path (already operator-attended).
- 16:48 stopped own sidecar (killed sleep pid 80953; worker 80954 gone; :52844 down). Recovery watch pid 84704 exited on its own.
