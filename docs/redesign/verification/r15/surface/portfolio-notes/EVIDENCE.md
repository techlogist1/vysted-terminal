# portfolio-notes: owner-drive evidence (R15 Stage B item 4, surf-S2C, agent P)

Worker: claude-opus-5-5[1m] ("the other agent" / "P" in `_TWIN_AGENTS.md`; twin agent Q owns
settings-plugins). Date 2026-09-23, 09:00-09:30 IST. Headless only.

## Rig

- Sidecar `127.0.0.1:52221`: source run, data dir `$SCRATCH/vysted-iso/seat-portfolio-notes/data`
  (`*.db` copied, `data_cache.db` via `sqlite3 .backup`, keyless `dev-keystore.json`), MCP pair
  `:53221/:53222`. Both agents launched identical boots one second apart. The :52221 worker (31096,
  feeder sleep 31095) and the MCP pair (feeders 31089/31092) belong to Q. P's own worker is :52222
  (31126, feeder 31125). P killed only its own losing duplicates (31116/31119/31122). The corrected
  pid record is at `$SCRATCH/vysted-iso/pids-surf-S2C.json`.
- `harness/*.s2c.test.tsx` + `harness/vitest.s2c.config.mjs` is a scratch config. Nothing was
  written under `src/`. The harness renders the REAL `PortfolioPanel` and `NotesPanel` (Tiptap v3.25)
  in jsdom. The real `sidecar-client` reaches the live sidecar through `?sidecar-port=52221`, and a
  fetch wrapper records every request. Only `downloadCsv` is mocked, so the CSV text can be captured.
  Outputs: `10-portfolio-panel-replay.json` (P1-P9), `20-notes-panel-replay.json` (N1-N6),
  `21-notes-toolbar-replay.json`.
- The sidecar ledger was driven directly: `11-portfolio-routes-http.jsonl` (P's pass), plus Q's
  `http-log.jsonl` L01-L18 (driver `harness/pn.py`), which Q handed over for merging.
- Agent lane: `scripts/r15/vy.py invoke copilot ... --provider ollama --model llama3.1:8b --autonomy
  auto --context A0-context-portfolio-panel-open.json` (A0 is the snapshot shape the OPEN panel
  publishes, with no ids). Result: `A1-*` and `A2-*`. $0 spent.
- Seeded evidence: no seat transcript touched portfolio or notes, and `seat-breaker/http-log.jsonl`
  has 0 portfolio/notes calls. Composer-chat drove one `write_note` prompt, which the intent gate
  stripped (SURF-COMPOSER-CHAT-5). Heavy prior CODE coverage exists (COD-portfolio-1..15,
  COD-host-actions-proposed-changes-*, COD-frontend-panels-data-surfaces-1/2/10/11/14). This drive
  reproduces those live and raises only NEW defects as raw findings.

## 1. Portfolio panel (`10-portfolio-panel-replay.json`)

| Drive | Result | Score |
|---|---|---|
| P1: empty | EmptyState 'This portfolio is empty' with CTA; Export disabled; 0 network calls | ok |
| P2: form validation | empty, qty 0, qty -3, cost -1 and 'abc' are rejected with copy. A **blank cost is saved as 0**, qty `1e20` is saved, and '1,000' gets the 'required' copy | partial, see **-6** |
| P3: INR book (RELIANCE 10@1200, TCS 5@2500) | Panel: 'Market value ₹22,929.00 · Total P&L -₹1,571.00 (-6.41%) · Concentration 54.1%'. Independent `/quotes` gives 1240.40/2105.00, so MV 22,929, P&L -1,571, -6.412%, weight 54.10%. Exact match. The bus publishes totalValue 22929 | ok |
| P4: create 'Second', add TCS, click trash | holdings unchanged (`['TCS.NS']`). Edit works. Delete works in the mount-time portfolio (control). A fresh mount on 'Second' deletes (P4b) | **broken, -3** |
| P5: ZZZZNOTREAL only | '**Market value ₹0.00 · Total P&L ₹0.00 (0.00%) · Concentration 0.0%** · 1 without a live quote'; bus `totalValue: 0`. The sidecar answered 502 `'PriceHistory' object has no attribute '_dividends'` (a yfinance internal error in place of an unknown-symbol answer) | **broken, -1** |
| P5: BTC/USDT, Crypto | `GET /quotes/BTC%2FUSDT` returns **404** in 1 ms. Row shows '₹60,000.00 — — — —' and the same ₹0 summary. BTCUSDT prices ($86,700, ccxt:binance) | **broken, -2** |
| P6: RELIANCE + AAPL + ZZZZ | per-currency 'Market value ₹12,404.00 + $1,019.25', Wt column dropped, 'mixed currencies' note; bus totalValue null + note | ok |
| P6: CSV export | quoting ok; unresolved row blank; **Weight % 92.41/7.59 across INR+USD** (COD-portfolio-5 live); no currency column; `=HYPERLINK(...)` note written as a formula | partial, see **-7** |
| P7: quote fetch fails (induced TypeError) | no 'Couldn't refresh live quotes' banner (COD-portfolio-4 live); ₹0 summary | broken (known + -1) |
| P8: 100 holdings (nse-all first 100) | 101 rows rendered, 10th row HINDUNILVR.NS present, select 'Big · 100'. 100 parallel `/quotes/{sym}` calls, all 200; the last landed **124 s** after mount (cells show '—' until then) | ok (latency noted) |
| P9: agent context + host actions | see section 3 | broken, -4 |

The sidecar ledger (`11-*.jsonl`, twin L01-L18): qty/cost/date validation holds (0 / 1e13 / -1 /
null / 'yesterday' all 422). Empty and whitespace symbols, a 300-char symbol, an HTML symbol and
`asset_class:"options"` are accepted (201). Q adds: `cost_basis: Infinity` is accepted and reads
back `null`, and a NaN body returns 500. The host-action shapes PUT/DELETE `/portfolio/positions`
(collection) return **405**, a store id `h-…` returns 422, and a HDFCBANK row deleted in the store
persists in the ledger. That is COD-portfolio-2/3 and COD-host-actions-proposed-changes-9 live.
Nothing reads this ledger, so none of this reaches a user. No new raw finding.

## 2. Notes panel (`20-notes-panel-replay.json`, `21-notes-toolbar-replay.json`)

| Drive | Result | Score |
|---|---|---|
| N1: mount | General note loads; chips 'General · RELIANCE · [+] symbol'; RELIANCE chip loads 'rel thesis' | ok |
| N1: type then 600 ms | store = 'seed line typed-by-user' | ok |
| N1: clear all | editor empty, **store still holds the old text** (COD-fe-data-2 live) | broken |
| N1: type then switch scope inside 100 ms | ' fast-edit' lost from RELIANCE (COD-fe-data-2 live) | broken |
| N2: agent `write_note` append into the OPEN scope | store gets the appended text, **editor still shows 'user thesis v1'**; one keystroke later the store holds 'user thesis v1!' and the agent's text is gone (COD-fe-data-1 live) | broken |
| N2: scope 'global' | label 'Wrote the GLOBAL note'; `bySymbol.GLOBAL` created (COD-host-actions-11 live) | broken |
| N2: no mode | RELIANCE note replaced by 'replaced?' (COD-host-actions-2 live) | broken |
| N2: whitespace text | `null` (honest failure) | ok |
| N3: 1.97 M-char note | load 1.7 s, keystroke ~0.2 s (a full `getMarkdown` of 2 MB on every update), 1.99 MB blob POST `/workspace` 200 and reads back | ok |
| N4: injection-shaped note | `<img onerror>` and `<script>` not rendered; `javascript:` href emptied; window flags untouched. Nothing sends notes to the agent (code-read: `context-provider.ts`, `ChatSidebar.tsx` never read `useNotesStore`). MCP `get_workspace` calls `/workspaces`, which 404s (router prefix `/workspace`) | ok |
| N5: slash menu | 10 items; '/tab' filters to Table; 9/10 commands apply; **Task List TypeError** (COD-fe-data-10 live) | partial |
| N5: wikilink '[[' | picker lists KAYNES (has note) + watchlist; pick inserts plain '[[RELIANCE.NS]]', serialised `\[\[RELIANCE.NS\]\]`; a watchlist symbol added after mount never appears | **broken, -8** |
| Toolbar | H1-H3, bold, italic, code, lists, quote and code block all apply and press. Link throws 'window.prompt is not a function' when no prompt exists (COD-fe-data-11). **Insert [[wikilink]] replaces the selected word** | partial, see -8 |
| N6: Export .md outside Tauri | Blob fallback, status 'Downloaded .md'; Tauri path NEEDS-GUI | partial |

## 3. Agent paths (P9, A1, A2, `30-intent-gate-portfolio-notes.txt`)

- **Open-panel snapshot has no ids.** `captureTerminalState().portfolio.holdings` from the open panel
  has no `id`. The closed-panel store fallback does. With lots TCS x5 and TCS x20, `portfolio_update_position
  {position_id:'2', symbol:'TCS.NS', quantity:25}` updated the **x5** lot. The review diff reads
  'TCS.NS: ×5 @ ₹2,500 -> ×25'. Its ledger mirror sent PUT `/portfolio/positions/2`. A direct PUT
  `/positions/3` overwrote an unrelated ledger row (200). See **-4**.
- `portfolio_add_position` with a negative cost is applied ('@ ₹-1,500'); the sidecar 422 is
  ignored. A string quantity returns `null` (honest). See **-6**.
- **Intent gate** (pure `classify_intent`, 15 phrasings): 'Delete TCS from my portfolio', 'Update my
  RELIANCE cost basis', 'I bought … track it', 'Put … in my paper portfolio', 'Save/Append/Write/
  Replace … note' are all classified `read`. 'Add …', 'Change …', 'remove …' and 'Log a buy' are `edit`.
  Live, 'Delete TCS from my portfolio' produced no tool_use; llama printed the call as text (A1, 65 s).
  Control 'Add 10 INFY.NS at 1500 to my portfolio' produced a correct `portfolio_add_position` tool_use (A2, 54 s).
  Its narration says 'awaiting your review in the proposal bar' under AUTO, while the tool result
  said 'dispatched'. That is model narration, not a product defect. See **-5**.

## 4. What was not driven

- GUI-only: drop-ladder column shedding at real widths, the WKWebView CSV/.md save, slash/wikilink
  keyboard navigation, the Tauri `write_text_atomic` note mirror. These are marked NEEDS-GUI in `COVERAGE.json`.
- Paid lane: none needed. The local model completed the add and proved the gate on delete. $0.

## Raw findings (`census/raw/surf-portfolio-notes.json`)

| id | sev | title |
|---|---|---|
| SURF-PORTFOLIO-NOTES-1 | high | Unpriced portfolio renders a ₹0 market value / 0.00% P&L and publishes `totalValue: 0` to the agent |
| SURF-PORTFOLIO-NOTES-2 | medium | Crypto 'BTC/USDT' holdings never price (`/quotes/BTC%2FUSDT` 404); cost shown in ₹ |
| SURF-PORTFOLIO-NOTES-3 | medium | Holding Delete is dead in any portfolio not active at mount (stale memoised closure) |
| SURF-PORTFOLIO-NOTES-4 | medium | Open panel publishes no holding ids; agent update/delete hits the first lot of the symbol |
| SURF-PORTFOLIO-NOTES-5 | medium | Intent gate strips portfolio write tools for 'delete/update/bought/put/track' phrasings |
| SURF-PORTFOLIO-NOTES-6 | low | Validation differs by entry path (blank cost -> 0, 1e20 qty, negative cost via agent) |
| SURF-PORTFOLIO-NOTES-7 | low | CSV export writes '=', '+', '-', '@' cells verbatim (formula injection) |
| SURF-PORTFOLIO-NOTES-8 | low | Wikilink picker frozen at mount; toolbar button deletes the selection; links saved escaped |
