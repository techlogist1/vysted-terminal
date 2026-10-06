# batch-10/W5-chat-search-workflow

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-082 | grep `src/modules/chat/streaming.test.ts`, `ChatSidebar.test.tsx`. | `describe("streaming — spend_usd on the done frame (R15-AGENT-082, C11)", ...)` and two `it(...(R15-AGENT-082))` tests present (a finished message's footer shows tokens/spend; a free model shows ~$0.00, not hidden). | ci_pinned (streaming.test.ts:204, ChatSidebar.test.tsx:1000,1018) |
| R15-AGENT-088 | grep `src/modules/chat/slash-commands.test.ts`. | Comment/tests naming R15-AGENT-088/FR-112 (a lone resolved ticker is an LLM-free fast path) present at line 23, plus a residual-case comment at line 66. | ci_pinned (slash-commands.test.ts:23) |
| R15-RESEARCH-025 | `POST /screener/formula/validate` x5. | `(pe>10)+1` and `(pe>10)*2+1` rejected at position 7 "a boolean expression can't be used in arithmetic"; `abs(pe>10)`/`max(pe>10,1)` rejected "needs a numeric argument, not a boolean expression"; `pe>10 and pb<3` ok, fields `[pe_ratio, price_to_book]`. | holds |
| R15-RESEARCH-028 | `GET /search/searxng/status`. | `{"state":"degraded","detail":"SearXNG is running but its search engines are blocked","reason":"brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA"}` — exact match to cert. | holds |
| R15-CROSS-PLATFORM-003 | `GET /system/hardware` on this M1 Pro. | `ramGib: 16.0`, `estimated: false`, `chip: "Apple M1 Pro"` — exact match to cert. | holds |
| R15-LEAD-013 | Read `sidecar/services/screener_universes/sp500.json` directly (a `screener/run` sort-by-market-cap call truncates to 200 rows, so the pack itself is the faithful repro). | 503 symbols, `snapshot_date: "2026-09-24"`. None of the ~15 previously-flagged delisted names (MMC, FI, ANSS, CTLT, DAY, DFS, HES, HOLX, IPG, JNPR, K, MRO, WBA, CTRA) present. BXP, NVR, UDR all present. | holds |
| R15-LEAD-024 | `GET /macro/WEO%2FUSA.NGDP_RPCH.A?provider=imf`. | 2023 2.93/false, 2024 2.79/false, 2025 2.12/true, 2026 2.32/true, 2031 1.76/true — exact match to cert's is_projection pattern. | holds |

**Set result: 5/7 holds (live), 2/7 ci_pinned.**
