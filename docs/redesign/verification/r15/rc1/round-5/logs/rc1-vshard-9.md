# rc1-vshard-9 working log (round 5)

- Checkout 633f844071d972b337f4c3526d86555c80df0568 (read-only worktree); own sidecar :52609; shared stack GET-only (two 429 GETs on :52152 /fundamentals/PDD,TSM).
- 16:35 curl1 batch (earnings/fundamentals/quotes) → Yahoo 429 across the board (sidecar circuit OPEN).
- FE vitest (scratchpad/v9-fe): FE-017, UI-015 hold; clearSearch residual reproduced.
- /workflow/run POSTs to own sidecar: PLATFORM-017 holds.
- In-process: AGENT-092/094 hold; AGENT-095 refuted (DD-Mon-YYYY); RESEARCH-022 refuted (DDG 200 challenge); RESEARCH-027 refuted (web-only branch un-boxed); DATA-114 holds + truncated-zip adjacent.
- 16:44-16:48 curl2 disclosures batch: DATA-003 and DATA-024 hold; sec-edgar-mcp 60 s timeouts (environment).
- In-process AGENT-010 (stub/raising/black-hole proxy) holds; LEAD-040 cold 12-way holds.
- LEAD-044 scratch pytest: region threading holds, store guard absent → not certified.
- LEAD-045: pinned tests pass; live curl_cffi batch 3/3 ok.
- Retried Yahoo-dependent entries in-process: estimates/.info still 429 → LEAD-039, DATA-113, DATA-008, DATA-055 inconclusive (fixtures support). Live v7 rows for DATA-117 → holds.
- No Ollama call made (no lock taken). Sidecar stopped by killing sleep pid 87417 only.
