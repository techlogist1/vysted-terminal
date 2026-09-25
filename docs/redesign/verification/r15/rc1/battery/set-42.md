# batch-10/W5-chat-search-workflow (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 7 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-082 | live `vy.py invoke copilot` (ollama llama3.1:8b) done frame (reused from set-39's AGENT-084 run) | `"done", "usage": {...}, "spend_usd": 0.0` present in the frame — free/ollama run correctly prices to a real zero, not an absent field | holds |
| R15-AGENT-088 | test file presence: `src/modules/chat/slash-commands.test.ts` (cert evidence was purely this vitest, no live route) | file present on `4097dac4` | ci_pinned |
| R15-UI-027 | test file presence: `src/store/keybindings.test.ts` (cert evidence was purely this vitest) | file present | ci_pinned |
| R15-RESEARCH-028 | live `GET /search/searxng/status` on `:52347` | `{"state":"degraded","detail":"SearXNG is running but its search engines are blocked","reason":"brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA"}` — exact match to cert | holds |
| R15-AGENT-063 | in-process `news_provider.build_aliases(['BTC/USDT','ETH/USDT','SOL/USDT'])` + `_tag_symbols` on 4 fresh headlines | aliases exact match to cert (`BTC/USDT→[BTC/USDT,BTC,bitcoin]` etc); "Ethereum ETF inflows surge"→`[ETH/USDT]`, "Solana outage"→`[SOL/USDT]`, "Ethereal plans IPO"→`[]`, "SOLID results for Solar firm"→`[]` — all 4 match cert exactly (live `/news?symbols=BTC/USDT` returned 0 items today, a content-freshness fact, not tested — the alias mechanism is the certified behaviour) | holds |
| R15-CODE-PLATFORM-017 | in-process `workflow_nodes.code_node.evaluate_code` | `2^3^2=512`, `-2^2=-4`, `2+3*4^2=50`, `round(2.5)=3`, `round(-2.5)=-3`, `a>1?a^2:0` with a=2 → 4 — exact match to cert | holds |
| R15-CODE-RESEARCH-004 | `grep -rn "autodetect\|locale" sidecar/services/search` | 0 hits on "autodetect"; the 3 "locale" hits are legitimate region-bias comments in `brave.py`/`ddg.py`/`searxng.py`, none referencing the removed autodetect/metadata code — no caller outside `searxng_manager` comments | holds |

Raw output: `battery/raw/set-42/*`.
