# Hand-testing guide - Vysted Terminal 0.9.0

For someone coming back cold. Allow 45 to 60 minutes total: the three items in section 1 below (fresh install, the 0.8.0 upgrade, and the two owed GUI checks) come first because nobody has clicked through them yet — the final adversarial pass's GUI half was not tested at the launch head (`DECISIONS_FOR_OPERATOR.md` 5.15). Sections 2 and 3 are the rest of the tour, for when you have more time. Report what you find using the last section. Nothing here needs the source tree.

## Before you start

- Keys: a hosted provider key (OpenAI, Anthropic, Gemini or OpenRouter) in Settings, stored in the OS keychain. For the keyless lane, Ollama with `llama3.1:8b` running. Docker or OrbStack running gives research its SearXNG tier; without it research uses the keyless scraper tier (DECISIONS 2.2).
- Known so far: the open items in `RELEASE_NOTES.md`; do not re-file those.
- Data directory on macOS: `~/Library/Application Support/com.vysted.terminal` (confirmed from `src-tauri/src/lib.rs` `app_data_dir`, which uses Tauri's default resolver keyed on the app identifier `com.vysted.terminal`; `VYSTED_DATA_DIR` overrides it if you need an isolated profile).

## 1. The three items nobody has clicked through yet

### 1a. Fresh install and first launch

1. Download `Vysted Terminal_0.9.0_aarch64.dmg` from the draft release (`gh release download v0.9.0 --repo techlogist1/vysted-terminal --pattern '*.dmg'` — GitHub names it `Vysted.Terminal_0.9.0_aarch64.dmg`; the run's local build copy lived in a session scratch folder that may be gone) (228,480,607 bytes, sha256 `9940d41b7ed6725aaabb6bb1709dc48b4f8ec51facd0696e376c68401139bc53`; verify with `shasum -a 256`) onto a clean or representative Mac — ideally one that has never run a Vysted Terminal build, so you see what a real first-time user sees.
2. Open the dmg, drag the app to Applications. If the build is unsigned, try to open it once, then System Settings → Privacy & Security → **Open Anyway**, and confirm (right-click → Open no longer works on macOS 15+). If macOS says it is damaged: `xattr -dr com.apple.quarantine "/Applications/Vysted Terminal.app"`. If a login-keychain consent prompt (SecurityAgent) appears at this point or at first launch and you have no prior `vysted-terminal` keychain items on this Mac, that is unexpected — note it (if you do have prior items from an older build, this is the known R15-LEAD-143, not a new bug: Deny or Allow either way).
3. Launch. The first launch can take **up to a few minutes**: the bundled data engine unpacks itself on every launch and the app waits up to 270 s for it (R15-LEAD-123). Expect the window to paint within seconds and take input while the engine is still starting. Good: the status chip goes from starting to connected, typically after 90 to 115 s on a cold start, and panels then fill with data. Bad: the chip stays red past about 5 minutes, or panels say the data engine could not start. Record the time from launch to connected.
4. Accept the first-launch terms (research-only wording plus a licence line), complete onboarding. Good: no dead end; if a keychain prompt appears, answer it. Bad: a dialog that never renders.

### 1b. The 0.8.0 upgrade, app side

This checks that a real user's data survives an in-place upgrade. If you have a locally built `v0.8.0` app or dmg on hand, use it; otherwise build one from the `v0.8.0` tag using the same recipe as `docs/RELEASE_RUNBOOK.md` applied to that tag — there is no published 0.8.0 release artifact to download (R15-RELEASE-002).

1. Install and launch the 0.8.0 build. Add a watchlist symbol, one manual portfolio position, and one note. Quit.
2. Install 0.9.0 over it (same Applications folder, same data directory — do not move the app aside first). Launch.
3. Good: the watchlist symbol, the portfolio position and the note are all still there, and the version in Settings/diagnostics now reads 0.9.0. Bad: any of the three is missing, or the app fails to launch at all against the 0.8.0-shaped data. This exercises the now-fixed R15-LIFECYCLE-024 (schema versioning and a pre-touch backup of the data dir) — a failure here would be a regression on a fixed register entry, not a new open item.
4. The sidecar half of this upgrade is already proven headless (`docs/redesign/verification/r15/stage-d/upgrade-0.8.0/UPGRADE.md`: PASS — positions, custom agent, workflow, notes and plugin config seeded by the 0.8.0 sidecar all survived the 0.9.0 sidecar's first boot). It never drove the app, so the app-side check above is still the one only a human can run.

### 1c. Two GUI checks the register is waiting on

- **R15-LIFECYCLE-008 (diagnostics).** Open Settings, scroll to the bottom, use "Copy diagnostics". Good: a preview shows version, status and a redacted log tail with no keys or queries; then the text is on the clipboard. Check `logs/vysted.log` under the app data directory (above) for timestamped lines.
- **R15-UI-022 (chart drawing tools).** On any chart, try each drawing tool (trendline, horizontal line, Text, lock). Good: a trendline clicked twice in empty space right of the last bar renders where you clicked, not snapped to the last bar's close; Text lets you type a real label, not a fixed "label" placeholder; Lock actually prevents the drawing from being moved or deleted. Bad: any anchor snaps to the bar close instead of your click, a click past the last bar commits an invisible drawing, or Lock does nothing.

## 2. The rest of the tour

1. **Watchlist.** Add AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT. Good: each row shows a price and a freshness label that matches whether that market is open; the US names read as stale or end-of-day while only Indian hours are live (known open item: freshness is stamped against your local calendar, R15-UI-090). Try adding a bare ticker that exists in both US and Indian markets (for example AMAL) and pick a listing; note which listing the chart uses (R15-DATA-002 is a known partial — the agent-add leg specifically, not the pick-a-listing UI flow you just exercised).
2. **Research a small Indian stock.** Run research on a small cap such as KPIT Technologies or Cochin Shipyard. Good: a brief appears with metric cards and cited sources; dividend yield and market cap are plausible against screener.in. Bad: a figure 10 to 100 times off.
3. **Chat on a hosted key.** Open the agent chat, ask for the price of a stock you know and for research on one name. Good: figures match the panel, and any change it proposes to your portfolio, watchlist or panels appears as a proposed change that waits for you (watchlist, chart and panel changes may auto-apply only if you set the autonomy to AUTO).
4. **Chat on the keyless local lane (Ollama, llama3.1:8b).** Ask the same. Good: tool calls happen and numbers match. **Known limitation (do not file as new):** with a keyless local model the agent can still state an invented figure as if a tool returned it; see the quoted block in `RELEASE_NOTES.md`. Also try "do not use any tools, add TCS to my portfolio": nothing is written or queued, but the reply may say it was. File only shapes that are not described in that block.
5. **Portfolio.** Add one position by hand (symbol, quantity, average cost). Good: market value and unrealised P&L compute; Export CSV shows a saved path under the app data `exports/csv/` folder.
6. **Notes.** Create a note, use the slash menu and the link popover on selected text, scroll the slash menu to check no row clips.
7. **Brief export.** Export a research brief as PDF and PNG (WKWebView).
8. **Agent dock.** Widen the window to a large display if you have one and try to maximise the agent dock (R15-UI-084, an open low: the dock is capped at 1200px with no maximize mode).
9. **Quit and relaunch.** Quit with Cmd-Q, relaunch. Good: the layout, watchlist, holdings and notes are all back, after the same first-boot wait. If the relaunch lands in a failed state, note machine load and the time waited (R15-LEAD-123).
10. **Origin check (R15-CODE-AGENT-001, macOS half).** While the app runs, confirm every panel loaded above without an error banner; the macOS packaged app and `pnpm tauri:dev` are both already confirmed live — this is a sanity re-check, not the owed item (the owed item is the Windows packaged app, see `WINDOWS_MANUAL_CHECK.md`).

## 3. Where to file what you find

- Open a GitHub issue on `techlogist1/vysted-terminal` (**Operator to confirm:** whether issues are enabled on the public repository) with: version (0.9.0), build sha (`1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056`), macOS version, steps, expected, actual, and the output of Settings, "Copy diagnostics" (it is redacted).
- Severity guide: wrong money figures or lost data = high; a dead control or a clipped label = medium or low. Anything in the known-limitation block or the open items is already filed for 0.9.1.
- The 0.9.1 list is `BACKLOG_0.9.1.md`.
