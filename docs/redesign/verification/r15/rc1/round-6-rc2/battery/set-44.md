# Set 44 — batch-10/W5-chat-search-workflow (rc1-battery-22, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-082 | UI repro (certified through vitest + done-frame spend_usd); confirmed pins exist, sidecar emits spend_usd (routers/llm.py:166) | ChatSidebar.test.tsx:1140 'footer shows tokens and estimated spend', streaming.test.ts:232 'parses a priced model's spend_usd' present; heavy lane runs them | ci_pinned |
| R15-AGENT-088 | UI repro (certified through vitest); pins exist, ChatSidebar.tsx:749 takes `bare-ticker` result | slash-commands.test.ts:79 'bare base with one suffixed known match resolves…' present | ci_pinned |
| R15-UI-027 | UI repro (certified through vitest); pins exist | keybindings.test.ts:124 'mod+p and meta+p conflict on macOS', :133 'shift+mod+p … does NOT conflict'; keybindings.ts resolveChord at :376 | ci_pinned |
| R15-RESEARCH-028 | live GET /search/searxng/status on :52362 | state 'degraded', detail 'SearXNG is running but its search engines are blocked', reason 'brave: … too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA' (not 'ready') | holds |
| R15-AGENT-063 | in-process build_aliases/enrich (news tool path) + live GET /news?symbols=BTC/USDT,ETH/USDT | BTC/USDT aliases [BTC/USDT,BTC,bitcoin]; 'Bitcoin options expiry looms' -> ['BTC/USDT'] scored negative; Ethereum/Solana headlines tagged ETH/USDT/SOL/USDT; 'Ethereal plans IPO'/'SOLID…Solar' untagged; live route returns tagged+scored item; news_tool.py calls news_provider.enrich | holds |
| R15-CODE-PLATFORM-017 | in-process `code_node.evaluate_code` | round(2.5)=3, round(-2.5)=-3, 2^3=8, 2^3^2=512, -2^2=-4, 2+3*4^2=50, `a > 1 ? 1 : 0`=1, ternary with ^ =4/0 (previously banker's 2 / BinOp error / parse error) | holds |
| R15-CODE-RESEARCH-004 | the entry's grep over sidecar/*.py | only hits are a docstring (base.py:138 'preferredDomains' options note) and test comments/test_search_exports.py (pins removal); no defining module or production caller | holds |

COVERAGE: 7/7 ids raw; no raw: none
