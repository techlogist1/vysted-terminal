# batch-10/W8-plugins-dock

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-013 | grep `src/lib/workspace.test.ts`. | `it("never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on (R15-CODE-PLATFORM-013)", ...)` present at line 435, naming the entry directly. | ci_pinned (workspace.test.ts:435) |
| R15-CODE-PLATFORM-017 | In-process: candidate `.venv`, `sidecar.services.workflow_nodes.code_node.evaluate_code` (async) run via `asyncio.run` over the cert's expression set. | `2^3^2` → `512`; `-2^2` → `-4`; `2+3*4^2` → `50`; `round(2.5)` → `3.0`; `round(-2.5)` → `-3.0` (banker's/away-from-zero as certified, not truncation); ternary `a>1?a^2:0` with `a=2` → `4` — exact-power/unary-precedence/round-half and ternary all match cert. | holds |
| R15-AGENT-063 | In-process: candidate `.venv`, `services.news_provider.build_aliases(['BTC/USDT','ETH/USDT','SOL/USDT'])` then `_tag_symbols(NewsItem(...), aliases)` over the cert's 4 headlines. | Aliases: `{'BTC/USDT': ['BTC/USDT','BTC','bitcoin'], 'ETH/USDT': [...,'ETH','ethereum'], 'SOL/USDT': [...,'SOL','solana']}`. Tagging: "Ethereum ETF inflows surge" → `['ETH/USDT']`; "Solana outage" → `['SOL/USDT']`; "Ethereal plans IPO" → `[]` (no false match on the "Eth-" substring); "SOLID results for Solar firm" → `[]` (no false match on the "Sol-" substring) — exact match to cert, no substring false-positive. | holds |

**Set result: 2/3 holds (live/in-process), 1/3 ci_pinned.**

COVERAGE: 3/3 ids raw (R15-CODE-PLATFORM-013 verified by grep line cite, no raw probe file needed for a ci_pinned test-name confirmation; CODE-PLATFORM-017 and AGENT-063 raw output in `raw/set-47/`).
