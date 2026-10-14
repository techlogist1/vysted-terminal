# UPGRADE-080 (gui-close-2): fresh GUI verification

- verifier: close-verify-UPGRADE-080, Opus 5.5, fresh context
- sha: 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056
- inputs: DRIVE.md, the 40 captures and raw/ in this folder, ../../CAPTURES.jsonl, ../presence.log, and code at the sha (`src/store/portfolios.ts`, `src/modules/portfolio/PortfolioPanel.tsx`, `src/lib/format.ts`)

## Capture registration
All 40 PNGs (`1fddb2b-01` .. `1fddb2b-40`) have a sha256 match in CAPTURES.jsonl with tool `scripts/rig/rig.py capture`, window_owner `Vysted Terminal`, frontmost `Vysted Terminal`. Each batch has a presence.log line before its first capture: pre-b01 09:15:34Z, pre-b02 09:16:55Z, pre-b03 09:32:09Z, pre-b04 09:48:43Z, pre-b05 10:04:48Z, pre-b06 10:20:00Z. All idle values are at or above 900 except the superseded 09:18:16Z line (idle 77), which was followed by a fresh 910.0 line before b03 ran. The sentinel ran until 12:57:00Z. No capture is unregistered. I opened all 40.

## Per part

| Part | Evidence | What it shows | Ruling |
|---|---|---|---|
| Boot, CONNECTED, cockpit | 01 | Header CONNECTED; Chat 1, Chart/Equity Overview, Watchlist and News loading, Portfolio "Portfolio · 81", AAPL 10 | holds |
| Portfolio: symbols, quantities and cost bases | 03, 04, 05-14, 17 | AAPL 10 @ $150.00 (04, 05). T001-T080 read on screen with qty n+1 and cost 10n (₹10.00..₹800.00), matching before.txt rows 1 and 5-84. Every T row appears in some capture except **T054**, which falls between 10 (ends at T053) and 11 (starts at T055) and is not legible in 17. | holds for the 81 rows shown, but T054 is seen only in the HTTP cross-check |
| Portfolio count vs before.txt | 01-14, 39, 40 ("Portfolio · 81"); raw/after-http.txt (ledger 84, 0 rows differ) | **81 of 84** rows are shown. These three AAPL rows are missing: id 2 and id 4 (qty 1e15 @ 1e-8) and id 3 (qty −50 @ −10). No notice appears in any capture. | **defect**: see finding 1 |
| Settings -> Advanced -> Layouts lists phase9test | 15, 16, 36, 37, 38 | 37 and 38: Layouts card with one row `phase9test` LOAD / ×, plus the autosave-slot note. This matches before.txt (one named layout). | holds |
| Loading phase9test restores its panels | 38 -> 39, 40; raw/phase9test-layout.txt | Before (38): Chart, Equity Overview, Settings, Portfolio. After (39): Chart, Equity Overview, Option Pricer, "2 more", Settings active; right column Watchlist / News / Portfolio. Option Pricer and Watchlist reappear. 40 is unchanged 5 s later, with no error. The saved grid's `chat` group has no dock panel because chat is the left agent pane in 0.9.0, and Chat 1 is present. | holds (the missing dock chat is a design change, not data loss) |
| Notes | raw/before.txt `notes/: absent` | The profile has no notes, so there is nothing to show | n/a |
| AI Providers configured/not-configured, no value | 18, 35 (also 19-34) | Anthropic, OpenAI, Gemini, Groq and xAI: "No key yet". Ollama: "No key required (local)" ✓ DEFAULT. DeepSeek and OpenRouter: "✓ Key configured". No key value appears anywhere. The rows are unchanged across the Tab/Shift+Tab walk in 19-34, and no dialog opened. | holds |
| Real dir mtime unchanged after quit | DRIVE.md (1790978102 before and after); my own `stat` at 10:26Z = 1790978102 | unchanged | holds |

## Driver findings
1. **Legacy import silently drops 3 of 84 positions with no notice.** CONFIRMED, **medium** (driver said low). The captures show "Portfolio · 81", and after-http.txt shows the ledger at 84. At the sha, `seedDefaultPortfolio` -> `setAll` -> `normalizeHolding` returns null for any row that fails `validateHolding` (qty > `MAX_HOLDING_QUANTITY` 1e12, qty ≤ 0, cost < 0) and filters it out. Nothing in that path surfaces a count or a notice. These fixture rows are hostile, but the same rule silently hides any negative-quantity row (a short lot) a real 0.8.0 user had. The migrated blob then takes precedence, so the row never comes back on screen. This is not data loss: the ledger keeps all 84. The workaround is to re-add the row by hand, so I rate it medium rather than critical.
2. **Dock layout proportions changed between batches with no input.** NOT CONFIRMED as stated. The change itself is visible: 16 at 09:32:53Z shows narrow Settings with the "2 more" chip and a wide Portfolio; 17 at 09:49:05Z shows wide Settings and a narrow Portfolio. But "no input" is not established. presence.log pre-b04 idle 907.8 at 09:48:43Z puts the last HID event at about 09:33:35Z, roughly 40 s after b03's last step. Also, b04's step 0 click and the rig's activate-Vysted step ran before capture 17. The cause is unknown and the claim stays plausible. Low.
3. **Settings clips buttons at narrow group width.** CONFIRMED, **low**. In 16, "Open Market[place]" is cut at the group edge and the Layouts Save button is off-edge. In 04-15, the AI Providers "Add key" button is cut to "Ac" and a horizontal scrollbar appears. At wide widths (37) the buttons are complete. Cosmetic.
4. **AAPL EOD quote flickers in and out of the Portfolio summary.** CONFIRMED, **low**. 05 (09:32:14Z) shows "Market value $3,336.90 · 80 without a live quote". Four seconds later, 06 (09:32:18Z) shows "— (no live quotes) · 81 without a live quote", and 07-16 stay that way. The value is back in 17-36 and gone again in 38-40. The summary never shows a wrong figure, only the value or "—". It is inconsistent, but it is not shown as fact.

## Missed by the driver
None at defect level. Two observations: unquoted T-symbols show cost in ₹ because unresolved equities take the region currency (`formatMoney` / `lotMoney`, region IN), and the legacy ledger carries no currency, so this is the documented default and not a defect. Also, `^NSEI` shows 22,421.95 in 02 and UNAVAILABLE in 39, the same intermittent-quote pattern as finding 4, outside this item.

## Verdict
**failed**, on one named part. The check requires the Portfolio panel to show the 84 positions from before.txt, and the captures show 81, with 3 rows silently dropped (finding 1, medium). Every other part holds on registered captures:
- cockpit
- 81 rows matching symbol, quantity and cost (T054 via HTTP only)
- phase9test listed and loaded
- AI Providers state shown with no values on screen
- real dir mtime unchanged
