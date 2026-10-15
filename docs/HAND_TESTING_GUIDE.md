# Hand-testing guide - Vysted Terminal 0.10.0

Two parts. Part R16 is new for 0.10.0 "Easy Install" and comes first: it is a walk on your Mac, from a Mac profile that has never run Vysted, through install, the first-run wizard, a model download, an example question and an update. Part 0.9.0 further down is the older tour; it still applies where a feature still exists. Nothing here needs the source tree except `scripts/fresh-profile.sh`, which you run from a checkout of this repository.

Every expected behaviour in Part R16 ends with the code path it was read from, in parentheses. Where a path says "unit test only", nobody has watched it happen in the packaged app.

## Part R16 - the 0.10.0 Mac walk

Allow about 90 minutes, most of it waiting for downloads. You need: an Apple Silicon Mac, about 7 GB of free disk space, an internet connection, a real API key for one provider (for the "own key" path), and a checkout of this repository for `scripts/fresh-profile.sh`.

### R16-0. Get the dmg and check it

1. Download from the draft release (visible only to repo writers until you publish): `gh release download v0.10.0 --repo techlogist1/vysted-terminal --pattern 'Vysted-Terminal-macOS-AppleSilicon.dmg' --pattern 'SHA256SUMS.txt'`. After you publish, the same files are at `https://github.com/techlogist1/vysted-terminal/releases/latest/download/Vysted-Terminal-macOS-AppleSilicon.dmg` and `.../SHA256SUMS.txt`.
2. Compare `shasum -a 256 Vysted-Terminal-macOS-AppleSilicon.dmg` with the matching line in `SHA256SUMS.txt`. Expected: identical. (The release job writes both; the rc1 run matched them: `docs/redesign/verification/r16/rc1/RC1_PROOF.md`.)

### R16-1. Install and Open Anyway

1. Open the dmg. Expected: a window with the app, an Applications shortcut, and a note about the first open. Drag the app to Applications. (dmg layout: `RC1_PROOF.md`.)
2. Open Vysted Terminal once from Applications. Expected: macOS says it cannot verify the app. The build is not code-signed, by decision. Click Done.
3. System Settings, Privacy & Security, scroll to the Vysted Terminal notice, click **Open Anyway**, confirm. Right-click then Open no longer works on macOS 15 and later.
4. If macOS says the app is damaged instead, run: `xattr -dr com.apple.quarantine "/Applications/Vysted Terminal.app"` and open it again.
5. After you confirm, the app starts once on your normal profile. Quit it with Cmd-Q. The walk uses a separate, never-run profile from here on.

### R16-2. Start a never-run profile

From the repository checkout:

```sh
scripts/fresh-profile.sh launch "/Applications/Vysted Terminal.app"
```

Expected: it prints `profile_dir=`, `service=`, `pid=` and `log=`. Keep the `profile_dir`. The app runs from a new empty folder with its own keychain items, so it behaves like a first install. Your real data and your real keychain entries are never read or changed (`scripts/fresh-profile.sh`, `src-tauri/src/keychain.rs` `service_for`). The log is `<profile_dir>/launch.log`; the app's own log is `<profile_dir>/logs/vysted.log`.

The first start can take a few minutes while the bundled data engine unpacks (see 1a in Part 0.9.0). If the wizard says "Getting things ready — the first launch takes about a minute.", wait; it is the same wait (`src/store/local-models.ts` `WARMING_UP`).

To start over at any point: quit the app, then `scripts/fresh-profile.sh wipe <profile_dir>` (deletes the folder, its downloaded models and its keychain items), then launch again. To relaunch the same profile without wiping, pass the folder: `scripts/fresh-profile.sh launch "/Applications/Vysted Terminal.app" <profile_dir>`.

### R16-3. Terms

Expected: a dialog titled "Welcome to Vysted" saying "Please review the terms before you start." with a button **I understand — continue**. Nothing else opens first. After the click the wizard appears. (`src/modules/safety/DisclaimerFlow.tsx`; the wizard waits for the acknowledgement in `src/components/OnboardingFlow.tsx`, `shouldOpen = tosAcked && ...`.)

### R16-4. The three wizard paths

The wizard asks **How should Vysted think?** It says prices, charts and news already work with no account, and offers three choices. It shows once per profile. Each path below needs its own never-run profile, so wipe and relaunch between them (R16-2). Run path A first, because it carries the download tests.

**Path A - On this computer.**

1. Click **On this computer**. Expected: a line "This computer: N GB RAM · N GB free space", then the four models: IBM Granite 4.2 3B, Qwen 3.5 4B, IBM Granite 4.2 8B, Qwen 3.5 9B. Each row shows a fit label (**Runs well here**, **Tight fit here** or **Too big for this computer**), what the model is for, its download size, how much free space it needs, and a link "Licence: Apache License 2.0". One row is tagged **Recommended** for your memory size: <!-- R16-MEASURE: per-tier recommendation -->. (`src/components/onboarding/LocalStep.tsx`, `sidecar/services/local_models/catalog.py` `catalog_for`.)
2. Click a licence link. Expected: it opens in your browser, not in the app window (`openExternal`, `LocalStep.tsx`). The licence is shown before any download starts.
3. Click **Download <model name> (size)**. Expected: a notice "Downloading — N%" with time left, a thin progress bar, a **Continue →** button, and the line "We'll finish in the background — you can keep going. The bar at the top shows progress."
4. Click **Continue →**. Expected: a short tour of four cards (the assistant, the chart, the watchlist, find anything), each with **Next →**, a "Skip the tour" link, then a last step headed "Try it". Because the model is not ready, the last step says "Your model is still downloading (N%) — we'll let you know when it's ready." and offers **Got it**. Click it. (`src/components/onboarding/TourStep.tsx`.)
5. Look at the bar under the header. Expected: "Downloading <name> — N% · speed · time left" with a **Pause** button and a progress bar. (`src/components/LocalModelStrip.tsx`.)
6. Pause test. Click **Pause** at some percentage. Expected: the bar changes to "The download of <name> is paused at N%." with **Resume**, **Use my own key** and **Cancel download**. The partial file is kept. Click **Resume**; it continues from N%, not from zero. (`LocalModelStrip.tsx` `isStalled`; `sidecar/services/local_models/store.py` `cancel` keeps the `.part` unless discarded, `_fetch` sends a Range header.)
7. Relaunch test. While it downloads, quit with Cmd-Q. Relaunch the same profile (R16-2, with the folder). Expected: the wizard does not return, and the download comes back at about the percentage it had and carries on by itself. It may flash "paused at N%" first. (`OnboardingFlow.tsx` writes `onboarding-complete` when the tour starts; `src/store/local-models.ts` `initLocalModels` resumes each paused download once when the data engine connects; `store.py` `_scan` rebuilds `paused` from the `.part` and `.part.json`.)
8. Let it finish. Expected, in order: "Checking <name>… almost done" (the sha256 check), then "Starting the on-computer model…", then **Your on-computer model is ready.** with a button **Ask: "How has Reliance Industries done over the past year?"**. (`LocalModelStrip.tsx`; `store.py` `_run`; the model is switched on automatically if none was active, `local-models.ts`.)
9. Click the Ask button. Expected: the question goes to the assistant on the left and a tool-backed answer arrives. A small on-computer model is slow; wait. The known limitation for keyless local models (Part 0.9.0 section 2, item 4, and `RELEASE_NOTES.md`) applies: file only new shapes. (`src/components/onboarding/example.ts` `askAgent`.)

**Path B - My own API key.**

1. Click **My own API key**. Expected: a provider grid and a box "Paste your key" with **Check & save →**. Paste a real key. Expected: it is checked with the provider and saved. A wrong key says the provider "didn't accept that key"; with no internet it says "No internet connection. Connect and try again." (`src/components/onboarding/KeyStep.tsx`.)
2. Expected: the tour, then a last step with "Ask your first question." and **Ask: "How has Reliance Industries done over the past year?"**. Click it. Expected: a tool-backed answer from the provider you chose. (`TourStep.tsx`, `path === "key"`.)
3. The key is in the macOS keychain under the profile's own service name, not in a file. Check with `scripts/fresh-profile.sh service <profile_dir>`, then Keychain Access. Wiping the profile removes it. (`CLAUDE.md` Credentials; `scripts/fresh-profile.sh wipe`.)

**Path C - Skip for now.**

1. Click **Skip for now**. Expected: the tour, then a last step "See how Reliance Industries has done — no setup needed." with a button **Show Reliance on the chart**. Click it. Expected: RELIANCE.NS opens in the chart with daily bars and no key. (`TourStep.tsx` `path === "skip"`, `example.ts` `showChartExample`.) You can also open it yourself from the command palette; the tour's "Find anything" card names the shortcut.
2. Expected: charts, prices and news work with no model and no key. Ask the assistant anything. The status line reads "No AI model is set up yet — opening setup. (Quotes, charts, news and screeners already work without one.)" and the wizard opens again, without the tour, so you can pick a path. (`src/modules/chat/ChatSidebar.tsx`, reason `not_configured`.)
3. Settings can change the choice later: Settings, Models for on-computer models, Settings, AI Providers for keys. (`src/components/SettingsPanel.tsx`.)

Every path has a way forward: each screen offers **Use my own key** or **Skip for now** if the model path fails.

### R16-5. The Models page

Settings, then **Models**. Expected: "This computer" with memory, free memory and free disk; the engine line ("Running on this computer: <name>."); "On this computer" with installed models (**In use** badge, remove asks "Remove for good?"); "Downloading"; "Add a model" with the four models and **Recommended for you** on one. If Ollama is running its models are listed too ("Vysted never needs Ollama."). (`src/components/settings/ModelsSection.tsx`.)

### R16-6. Update check

The app checks for an update 15 seconds after launch and every 6 hours. There is no "check now" button. (`src/components/UpdatePrompt.tsx` `FIRST_CHECK_MS`, `RECHECK_MS`.)

1. On the published 0.10.0 build with nothing newer out, wait 20 seconds. Expected: nothing appears. A failed or empty check is silent. (`src-tauri/src/updater.rs` `update_check` answers `available: false` on any error.)
2. To see the strip you need a newer signed build. Use scenario 4 below.

## Four scenario checks

### Scenario 1 - a download dies at about 80%, then relaunch

Setup: start a download from the wizard or Settings, Models. At about 80% force-quit the app (Cmd-Option-Esc, Force Quit) or kill the process printed by `fresh-profile.sh`. For a clean look at the paused state, turn Wi-Fi off before the relaunch and turn it back on after.

Expected:

1. On disk, `<profile_dir>/models/<file>.gguf.part` and `<file>.gguf.part.json` remain, and no finished `.gguf` appears. (`store.py` writes the model file only by `os.replace` after the hash matches.)
2. After the relaunch the model shows **paused at about 80%**: "The download of <name> is paused at N%." with **Resume**. With Wi-Fi off it stays paused, with the reason "No internet connection" (the app tries three times with growing waits, then pauses). (`store.py` `_scan` sets `paused` with "Download was interrupted — resume to continue"; `_run` pauses after `RETRIES = 3`; `_fetch` maps a connection error to `NO_INTERNET`.)
3. With the network on, the app resumes by itself once, or you click **Resume**. It continues from about 80%, not from zero (HTTP Range with the stored etag). (`local-models.ts` `initLocalModels`; `store.py` `_fetch`.)
4. At 100% the bar says "Checking <name>… almost done", then the model starts. The whole file is hashed first; a bad file is deleted and you see "The download was corrupted — try again", and the next try starts clean. The corrupt case is unit test only (`sidecar/tests/test_local_models.py`); to try it by hand, edit one byte of the `.part` file before the relaunch. (`store.py` `_run`, `CORRUPTED`.)

### Scenario 2 - an 8 GB Mac with a browser open

You need an 8 GB Mac for the real thing. On a bigger Mac you cannot reproduce the labels, but the Models page "This computer" line shows what the app measured.

Expected on an 8 GB machine:

1. The app puts it in the "8 GB" tier (a machine that reports 7.5 GiB or more counts as 8 GB). (`sidecar/services/local_models/hardware.py` `tier_for`.)
2. Fit labels depend on **total** memory, not on what is free, so a browser being open does not change them. A model whose minimum memory is within 75 percent of total is **Runs well here**; up to 100 percent is **Tight fit here** (Models page: "A tight fit"); above that **Too big for this computer**. With the shipped catalog on an 8 GB Mac: IBM Granite 4.2 3B and Qwen 3.5 4B read "Runs well here"; IBM Granite 4.2 8B and Qwen 3.5 9B read "Tight fit here". (`catalog.py` `fits`; minimum memory values in `catalog.json`; the arithmetic is unit tested, the 8 GB result is derived, not watched.)
3. The Recommended tag sits on the model chosen for the 8 GB tier: <!-- R16-MEASURE: per-tier recommendation -->. Under 8 GB the wizard stops recommending **On this computer** and tags **My own API key** as Recommended instead. (`ChooseStep.tsx`.)
4. With a browser and other apps open, free memory is low. If free memory is below what the chosen model needs, or the model is a tight fit, the wizard shows a yellow notice: "This computer is short on free memory for <name>. Closing your web browser and other apps before you ask a question will help. Or use your own key — then the thinking happens online, not on this computer." with **Use my own key instead**. It is advice, not a block. (`LocalStep.tsx` `lowRam`.)
5. A too-big model cannot be downloaded: the button is disabled and the text says "<name> is too big for this computer — pick a smaller one." (`LocalStep.tsx`.)
6. Expect slow answers. The engine's context size follows the tier (16384 under 8 GB, 24576 at 8 GB); asking a very long question can end with "The conversation is too long for the on-computer model. Start a new chat." (`src/lib/local-engine.ts` `CTX_SIZE_BY_TIER`; `sidecar/services/errors.py` `_humanize_local`.)
7. Low disk: if free space is less than the model needs, the wizard says "Not enough space on this computer. <name> needs X free and there is Y. Free up space or pick a smaller model." with a button to pick a smaller one. The same check repeats every 256 MB during the download. (`LocalStep.tsx` `shortOnDisk`; `store.py` `DiskSpaceError`, `DISK_CHECK_EVERY`.)

### Scenario 3 - the engine crashes mid-answer

Setup: the on-computer model is ready. Ask a question that takes a while (the Reliance example). While the answer is streaming, in Terminal run `pgrep -fl llama-server` to confirm the process, then `pkill -9 -f llama-server`.

Expected:

1. The answer stops and ends with a plain message: "The on-computer model stopped while answering. It restarts on its own — send your question again in a few seconds." It does not blame your key or your network. (`sidecar/services/errors.py` `LOCAL_STOPPED_ERROR`, chosen in `_humanize_local` for a dropped connection. Unit tested; the live mid-answer kill is what you are checking.)
2. The bar under the header reads "The on-computer model stopped unexpectedly — restarting it…", then "Starting the on-computer model…", then disappears when ready. The Settings, Models engine line shows a similar message. Restart waits are 1 second, then 4, then 10. (`LocalModelStrip.tsx`; `src-tauri/src/local_engine.rs` `on_crash`, `Timings::backoff`.)
3. Ask again. If you ask while it is still starting, the status line says "The on-computer model is starting — send your question again in a moment." (`ChatSidebar.tsx`). Once it is ready, ask again. Expected: it works. No second `llama-server` is left over: `pgrep -fl llama-server` shows one process. (`local_engine.rs`; the live lifecycle test asserts the crashed child is gone.)
4. Crash limit. Wait for "ready" each time (the bar disappears), then kill again. Count only kills made while the model was ready. The 1st, 2nd and 3rd crashes restart it. On the **4th crash within 10 minutes** it stays stopped. The bar shows "The on-computer model couldn't start. The on-computer model stopped 4 times in 10 minutes, so it won't restart on its own. Start it again when you're ready." with **Try again**, **Use a smaller model** and **Use my own key**. Settings, Models shows the same text and a **Try again** button. (`local_engine.rs` `MAX_CRASHES = 4`, `crash_window` 600 s; `LocalModelStrip.tsx` `engine.state === "failed"`; `ModelsSection.tsx`. The button is labelled "Try again", not "Start".)
5. Click **Try again**. Expected: the engine starts fresh, the crash count is zero again, and the next question works. (`local_engine.rs` `start` clears the crash list.)
6. If you kill it while it is still "Starting...", that is not a crash. The start fails with the engine's last message instead. Do not count that kill. (`local_engine.rs` `on_child_event`, `Starting` branch.)

### Scenario 4 - an update arrives during a model download

This needs a newer signed build to offer. Use the two beta builds, as the rc1 proof did (`RC1_PROOF.md`), or any two consecutive signed builds.

Setup:

1. Download the newer build's `latest.json` and its `Vysted-Terminal.app.tar.gz` (and `.sig`) into one folder, e.g. `gh release download v0.10.0-beta.2 --repo techlogist1/vysted-terminal --dir ~/update-test --pattern 'latest.json' --pattern '*.tar.gz*'` (the beta drafts must still exist; otherwise use two builds of your own).
2. Serve it: `node scripts/release/serve-update.mjs --dir ~/update-test --rewrite`. It listens on `127.0.0.1:8787`.
3. Copy the **older** app (from its dmg) to a folder you can write to, e.g. `~/update-test/older/`, because the update replaces the app in place.
4. Launch it on a never-run profile with the test endpoint: `VYSTED_UPDATER_ENDPOINT=http://127.0.0.1:8787/latest.json scripts/fresh-profile.sh launch ~/update-test/older/"Vysted Terminal.app"`. Only `https://` or `http://127.0.0.1:<port>/` addresses are accepted; the signature is still checked against the app's own key, so an unsigned or foreign bundle is refused. (`src-tauri/src/updater.rs` `validate_endpoint`.)
5. Get through the terms and wizard, choose **On this computer** and start a large download (Qwen 3.5 9B is the largest).

Expected:

1. About 15 seconds after launch a bar appears: "Vysted Terminal <version> is available." with **What's new** (the release notes), **Restart to update** and **Later**. (`UpdatePrompt.tsx`.)
2. While the download is running (downloading or checking), the button reads **Update after the download finishes**. (`UpdatePrompt.tsx` `downloadActive`; `src/lib/updater.ts` `hasActiveModelDownload` counts only "downloading" and "verifying".)
3. Click it. The button turns grey and reads "Updating after the download finishes…". Nothing is interrupted. Within about 5 seconds of the download ending the update downloads ("Downloading update… N%"), installs and the app relaunches. It does not install by itself unless you clicked first. (`UpdatePrompt.tsx` `waiting`, poll every `DOWNLOAD_POLL_MS`.)
4. After the relaunch the app shows the new version and no update bar. The model that finished is still installed and still the active one. (`RC1_PROOF.md`: the beta.1 to beta.2 update left no old process behind.)
5. Interrupted case. Repeat from step 5 but, after you clicked the waiting button, turn Wi-Fi off. The download retries three times and then pauses, so it no longer counts as active and the update installs (the update itself comes from your own machine, so it still works). After the relaunch, turn Wi-Fi on. The paused download resumes by itself from where it stopped. (`updater.ts` ignores `paused`; `local-models.ts` `initLocalModels`; `store.py` `_scan`.)
6. **Later** hides the bar until the next 6-hour check. Pressing **Pause** on a download also frees the update to install. (`UpdatePrompt.tsx` `later`; a cancelled download is not active.)
7. If the install fails the bar says "The update could not be installed. Check your connection and try again." (`UpdatePrompt.tsx` `failed`.)

## What to send back

For each step: pass, fail, or "did not see it". For a fail, send the `launch.log` and `logs/vysted.log` from the profile folder, Settings, "Copy diagnostics", macOS version and memory size, and the step number. The rest of this guide's reporting advice (the last section of Part 0.9.0) applies unchanged.

---

## Part 0.9.0 - the earlier tour (Vysted Terminal 0.9.0)

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
