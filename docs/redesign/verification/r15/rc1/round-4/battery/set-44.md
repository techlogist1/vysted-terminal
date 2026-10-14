# Set 44 — batch-10/W5-chat-search-workflow (rc1-battery-20)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar `127.0.0.1:52360`
(fresh copy of `rc1-round-4-seed-data`). Live-checkable entries re-run directly
against the candidate sidecar/venv; frontend-only entries verified by source
inspection and verdicted `ci_pinned` (vitest/jsdom or GUI required, both out of
scope for this role).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-082 | Source check: `src/modules/chat/ChatSidebar.tsx:984-999,1570-1584` | `onDone` now threads a real `spendUsd` into `cost.spendUsd`/`message.spendUsd`; footer renders "N tok · ~$X.XX" when spendUsd is a number (incl. real 0), omits the segment only when absent | ci_pinned (src/modules/chat/ChatSidebar.test.tsx:1000,1018,1036) |
| R15-AGENT-088 | Source check: `src/modules/chat/slash-commands.ts:95-108`, `ChatSidebar.tsx:427,736` | non-slash input tries `matchBareTicker()` first → `{kind:'bare-ticker', symbol}` consumed with no LLM round-trip; multi-word/unresolved input still `{kind:'raw'}` | ci_pinned (src/modules/chat/slash-commands.test.ts:27,34,48,55,79,86,98) |
| R15-UI-027 | Source check: `src/store/keybindings.ts:370-386` `resolveChord` | `mod` collapses to the platform modifier (`meta` on macOS / `ctrl` elsewhere) before `conflicts()` compares chords — `mod+p`/`meta+p` now collide on macOS, `shift+mod+p` vs `mod+p` do not | ci_pinned (src/store/keybindings.test.ts:124,133,144) |
| R15-RESEARCH-028 | `curl -s http://127.0.0.1:52360/search/searxng/status` | `{"state":"degraded","detail":"SearXNG is running but its search engines are blocked","reason":"brave: Suspended: too many requests; duckduckgo: timeout; startpage: Suspended: CAPTCHA", ...}` — matches the certified "degraded"/engines-blocked state exactly | holds |
| R15-AGENT-063 | Direct call: `services.agent_tools.news_tool._news({"symbols":"BTC/USDT"})` (candidate venv, live network) + `build_aliases`/`_tag_symbols` fresh cases | tool returns 1 enriched item (sentiment 0.802 positive, symbols=['BTC/USDT']); `ETH/USDT→[...,'ethereum']`, `SOL/USDT→[...,'solana']`, `DOGE/USDT→[...,'dogecoin']`; fresh headlines: "Ethereum ETF inflows surge"→['ETH/USDT'], "Solana outage"→['SOL/USDT'], "Ethereal plans IPO"→[], "SOLID results for Solar firm"→[] — all match the batch-10 cert exactly | holds |
| R15-CODE-PLATFORM-017 | Direct call: `services.workflow_nodes.code_node.evaluate_code` (candidate venv) for the 6 original expressions | `2^3^2`=512, `-2^2`=-4, `2+3*4^2`=50, `round(2.5)`=3, `round(-2.5)`=-3, `a>1?a^2:0` (a=2)=4 — all PASS | holds |
| R15-CODE-RESEARCH-004 | `grep -rn -E 'locale_domains\|preferredDomains\|detect_searxng\|KNOWN_BACKENDS\|breaker_status\|untrusted_context_message' --include=*.py sidecar/` | 3 hits total, all in test files/docstrings/comments naming the deletion (`test_web_search.py`, `test_search_exports.py`, `base.py` docstring); zero production callers remain | holds |

COVERAGE: 7/7 ids raw.
