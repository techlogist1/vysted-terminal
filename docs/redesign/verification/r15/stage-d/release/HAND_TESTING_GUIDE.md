# Hand-testing guide - Vysted Terminal 0.9.0

For someone coming back cold. Allow 30 to 45 minutes after the first boot. Report what you find using the last section. Nothing here needs the source tree.

## Before you start

- Install: open `Vysted Terminal_0.9.0_aarch64.dmg` (<<BUNDLE_BYTES>> bytes, sha256 <<BUNDLE_SHA256>>; verify with `shasum -a 256`), drag the app to Applications. If the build is unsigned, right-click the app and choose Open, then confirm. If macOS says it is damaged: `xattr -dr com.apple.quarantine "/Applications/Vysted Terminal.app"`.
- For a clean test, move aside `~/Library/Application Support/com.vysted.terminal` (<<CHECK: exact data directory name on this build>>) first; for the quit-and-relaunch step you need the data you create.
- Keys: a hosted provider key (OpenAI, Anthropic, Gemini or OpenRouter) in Settings, stored in the OS keychain. For the keyless lane, Ollama with `llama3.1:8b` running. Docker or OrbStack running gives research its SearXNG tier; without it research uses the keyless scraper tier (DECISIONS 2.2).
- Known so far: the open items in `RELEASE_NOTES.md`; do not re-file those.

## First launch

The first launch can take **up to a few minutes**: the bundled data engine unpacks itself on every launch and the app waits up to 270 s for it (R15-LEAD-123). Expect the window to paint within seconds and take input while the engine is still starting. Good: the status chip goes from starting to connected, typically after 90 to 110 s on a cold start, and panels then fill with data. Bad: the chip stays red past about 5 minutes, or panels say the data engine could not start. Record the time from launch to connected.

## The tour

1. **Terms and onboarding.** Accept the first-launch terms (research-only wording plus a licence line), complete onboarding. Good: no dead end; if a keychain prompt appears, answer it. Bad: a dialog that never renders.
2. **Watchlist.** Add AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT. Good: each row shows a price and a freshness label that matches whether that market is open; the US names read as stale or end-of-day while only Indian hours are live (known open item: freshness is stamped against your local calendar, R15-UI-090). Try adding a bare ticker that exists in both US and Indian markets (for example AMAL) and pick a listing; note which listing the chart uses (R15-DATA-002 is a known partial).
3. **Chart.** Load SPY, add a few indicators and VWAP. Good: the candles render, indicators draw, pan and zoom work. Try the drawing tools (trendline, horizontal line, Text, lock): this is R15-UI-022; the check still needed is a trendline clicked twice in empty space right of the last bar must render.
4. **Research a small Indian stock.** Run research on a small cap such as KPIT Technologies or Cochin Shipyard. Good: a brief appears with metric cards and cited sources; dividend yield and market cap are plausible against screener.in. Bad: a figure 10 to 100 times off.
5. **Chat on a hosted key.** Open the agent chat, ask for the price of a stock you know and for research on one name. Good: figures match the panel, and any change it proposes to your portfolio, watchlist or panels appears as a proposed change that waits for you (watchlist, chart and panel changes may auto-apply only if you set the autonomy to AUTO).
6. **Chat on the keyless local lane (Ollama, llama3.1:8b).** Ask the same. Good: tool calls happen and numbers match. **Known limitation (do not file as new):** with a keyless local model the agent can still state an invented figure as if a tool returned it; see the quoted block in `RELEASE_NOTES.md`. Also try "do not use any tools, add TCS to my portfolio": nothing is written or queued, but the reply may say it was. File only shapes that are not described in that block.
7. **Portfolio.** Add one position by hand (symbol, quantity, average cost). Good: market value and unrealised P&L compute; Export CSV shows a saved path under the app data `exports/csv/` folder (R15-UI-009 is fixed; please confirm).
8. **Notes.** Create a note, use the slash menu and the link popover on selected text, scroll the slash menu to check no row clips (R15-UI-025 and R15-UI-050 fixed, please confirm).
9. **Brief export.** Export a research brief as PDF and PNG (R15-UI-083, WKWebView).
10. **Agent dock.** Widen the window to a large display if you have one and try to maximise the agent dock (R15-UI-084).
11. **Settings and diagnostics.** Open Settings, scroll to the bottom, use "Copy diagnostics". Good: a preview shows version, status and a redacted log tail with no keys or queries; then the text is on the clipboard (R15-LIFECYCLE-008). Check `logs/vysted.log` under the app data directory for timestamped lines.
12. **Quit and relaunch.** Quit with Cmd-Q, relaunch. Good: the layout, watchlist, holdings and notes are all back, after the same first-boot wait. If the relaunch lands in a failed state, note machine load and the time waited (R15-LEAD-123).
13. **Origin check (R15-CODE-AGENT-001).** While the app runs, confirm every panel loaded in step 2 to 11 without an error banner; this is the click-through the register is waiting on for macOS packaged.

## Where to file what you find

- Open a GitHub issue on `techlogist1/vysted-terminal` (<<CHECK: issues enabled on the public repository>>) with: version (0.9.0), build sha (<<LAUNCH_SHA>>), macOS version, steps, expected, actual, and the output of Settings, "Copy diagnostics" (it is redacted).
- Severity guide: wrong money figures or lost data = high; a dead control or a clipped label = medium or low. Anything in the known-limitation block or the open items is already filed for 0.9.1.
- The 0.9.1 list is `BACKLOG_0.9.1.md`.
