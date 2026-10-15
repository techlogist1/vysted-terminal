# R16 GUI round: Vysted Terminal 0.10.0-beta.4 (r16-rc2 build)

**Round status: STOPPED, operator present.** At 21:18:52 IST the rig refused mid-batch with exit 3:
`REFUSED: human input detected mid-batch: idle 14.3s but 20.0s since the rig's own last event`.
I stopped as the brief requires. After that I sent no more GUI input and took no more captures.

## Header

- **Build:** `v0.10.0-beta.4`, `Vysted-Terminal-macOS-AppleSilicon.dmg`. `CFBundleShortVersionString` = `0.10.0-beta.4`.
- **dmg sha256:** `b57c05821d54c1acb0b661891ba6c4aada50c047b7f2a387c5a1e713c307f4cb`. SHA256SUMS.txt has the same value: **matches = yes**.
- **App:** `docs/redesign/verification/r16/local/gui-app/Vysted Terminal.app`. It was copied with `ditto` from the read-only mounted dmg and was not installed in /Applications. The gh download has no quarantine flag, so Gatekeeper's "can't verify" prompt did not appear: **NEEDS-MANUAL-CHECK**.
- **Clock (`date`):** started 20:30:43 IST. Batch 1 ran at 20:46:36, batch 2 at 21:01:50 and batch 3 at 21:18:22. The stop came at 21:18:52.
- **Rig idle at start:** 2450.2 s. The away sentinel was valid until 2026-10-15T17:16:24Z.
- **Rig cadence:** every rig process starts with `last_event=None`, so it needs raw idle of at least 900 s. The rig's own synthetic input resets HIDIdleTime. Each batch therefore had to wait about 15 min after the previous batch's last event. I kept the 900 s bar and did not pass `--min-idle`.
- **Pre-existing state:** an earlier GUI attempt (wf_5110316a-670, launched 17:48 IST) had left an instance of the same gui-app .app running. It used profile `/private/var/folders/1s/3bgs17xd07z839yf5kj6mc3m0000gn/T/vysted-profile.v3GSkg` and was still sitting at the terms dialog. Its models dir was empty and it had no captures. I quit it gracefully with `rig.py key cmd+q`, confirmed that no process survived, and ran `fresh-profile.sh wipe` on it (0 keychain items). Then I downloaded the release again with `--clobber` and copied the .app fresh.
- **Overlay click-through:** clicks pass through. I clicked at window point (536,454), which is screen (652,497) and inside the Wispr Flow "Status" rect. The app reacted: the chat header changed from `CONTEXT: PORTFOLIO` to `CONTEXT: EQUITY-OVERVIEW`, because the Equity Overview panel took focus. See `A-local/11-relaunch-ready.png` → `A-local/12-overlay-click-test.png`. The overlay does not swallow clicks. I drove the dialogs from the keyboard anyway (tab, shift+tab, return), following Radix focus-scope order.
- **Capture scale:** the window is 1280×832 pt and the capture is 2560×1664 px, so 2×. `resize 1280 935` is clamped to 1280×862. A relaunch resets the window to 832 pt high.

## Path A: On this computer

Profile A: `/private/var/folders/1s/3bgs17xd07z839yf5kj6mc3m0000gn/T/vysted-profile.yVBoKz`

### A1 Terms dialog: PASS

- **Did:** fresh launch, waited for the sidecar (`Uvicorn running` at 20:34:37), captured, pressed return. The accept button has focus when the dialog opens.
- **Expected:** a terms dialog on a never-run profile.
- **Observed:** "Welcome to Vysted / Please review the terms before you start." The body says "Vysted has no brokerage connection. It cannot place, route or simulate orders." and "source-available under PolyForm Strict 1.0.0 (noncommercial use) or a commercial license — see LICENSING.md." The button reads "I understand — continue". Return dismissed the dialog.
- **Captures:** `A-local/01-terms.png`

### A2 Choice screen: PASS

- **Observed:** "WELCOME / How should Vysted think?" offers three choices: "On this computer" tagged RECOMMENDED, "My own API key" and "Skip for now". A green note reads "Prices, charts and news already work — no account needed…"
- **Captures:** `A-local/02-choose.png`

### A3 Model list: PARTIAL

- **Did:** pressed return. "On this computer" has autofocus, so this selected it.
- **Observed:**
  - "This computer has 16 GB of memory, so Qwen 3.5 4B is the best balance of quality and speed."
  - "This computer: 16.0 GB RAM · 67.7 GB free space".
  - IBM Granite 4.2 3B: "RUNS WELL HERE", "2.1 GB download needs 2.3 GB free", "Licence: Apache License 2.0".
  - Qwen 3.5 4B: "RECOMMENDED", "RUNS WELL HERE", "2.6 GB download needs 2.8 GB free".
  - Footer: "Skip for now", "Download Qwen 3.5 4B (2.6 GB)".
- **Why not PASS:**
  - The list scrolls inside a fixed area. Only rows 1 and 2 are visible, so Granite 8B and Qwen 9B and their fit labels were not seen. Scrolling them into view would have needed a scroll or a focus move that risks the licence links.
  - The dialog is taller than the 832 pt window, so the Download button is cut off. It is only fully visible at 862 pt.
  - Two unexpected elements appear; see Findings F1 and F2:
    - an "Already on this computer" block listing `qwen3:8b (Ollama)`, `qwen2.5:7b (Ollama)` and `llama3.1:8b (Ollama)`, each with "Use this one";
    - a warning on this 16 GB Mac: "This computer is short on free memory for Qwen 3.5 4B. Closing your web browser and other apps before you ask a question will help…"
- **Captures:** `A-local/03-local-models.png`, `A-local/03b-local-models-tall.png`, `A-local/03c-focus-download.png`

### A4 Download starts: PASS

- **Did:** tab then shift+tab put focus on the last control (Download), then return.
- **Observed:** a "Downloading — 1% · about 2 min left" notice with a progress bar. The Continue → button sits below it and is cut off at window height. Continue was reached by keyboard, and the tour opened. The strip behind reads "Downloading Qwen 3.5 4B — 1% · 19 MB/s · abo…" with Pause.
- **Captures:** `A-local/04-downloading.png`, `A-local/04b-focus-continue.png`

### A5 Tour, Try it, strip: PASS

- **Observed:**
  - Card 1 is "1 OF 4 / The assistant" with "Skip the tour" and "Next →".
  - Card 4 is "4 OF 4 / Find anything / Press ⌘K to open a panel, jump to a company or change a setting."
  - The last step reads "TRY IT / Your model is still downloading (11%) — we'll let you know when it's ready. / Then try: "How has Reliance Industries done over the past year?" / Got it".
  - After Got it, the strip reads "Downloading Qwen 3.5 4B — 11% · 26 MB/s · about 2 min left" with Pause.
- **Note:** throughout, the header chip still read "ON THIS COMPUTER · NOT RUNNING — SET UP IN SETTINGS", and the "Add a cloud provider key — or download a model…" banner stayed up (F3).
- **Captures:** `A-local/05-tour-1.png`, `A-local/06-tour-4.png`, `A-local/07-tour-try-it.png`, `A-local/08-strip-downloading.png`, `A-local/09-strip-progress.png`

### A6 Quit at about 78%, relaunch, auto-resume: PARTIAL

- **Observed before quit:** the strip read "Downloading Qwen 3.5 4B — 76% · 25 MB/s · less than a minute left" (`A-local/10-before-quit.png`). I sent `rig.py key cmd+q`.
- **Processes:** `pgrep -fl <profile_dir>` was empty afterwards, so all app processes for this profile exited.
- **Partial file:** `Qwen3.5-4B-Q4_K_M.gguf.part` = 2133735015 bytes, 77.8% of 2740937888. The `.part.json` kept the url, sha256 and etag.
- **Relaunch at 21:03:39:** the log shows `POST /local-models/qwen3.5-4b/download` at 21:05:28, about 1:50 after launch, with no click from me. The `.part` grew from 2133735015 bytes, not from 0, and it became the final `Qwen3.5-4B-Q4_K_M.gguf` (2740937888 bytes) by 21:05:49. `/local-models/installed` reports `"verified":true,"active":true`.
- **Engine:** llama-server started on its own and logged `model loaded` and `listening on http://127.0.0.1:56836`.
- **Relaunch capture (21:18:22):** no terms dialog, no wizard and no download strip. The header chip still read "ON THIS COMPUTER · NOT RUNNING — SET UP IN SETTINGS" and the "Add a cloud provider key…" banner was still showing (F3).
- **Why PARTIAL:** I could not capture the resuming, verifying or starting strip states. The rig's 900 s gate after the quit keystroke opened only after the resume and engine start had finished. The resume itself is proven from the file sizes and the log. The visible "ready" state was NOT seen.
- **Captures:** `A-local/10-before-quit.png`, `A-local/11-relaunch-ready.png`

### A7 Reliance example question: NOT TESTED (operator present)

- **Did:** batch 3 clicked the composer at window (160,798), typed the question and pressed return.
- **Coordinate problem:** the window had gone back to 832 pt on relaunch, so (160,798) probably landed on the composer's "Normal" depth control and not in the text field.
- **Result:** the sidecar log shows no agent invocation. About 20 s later the rig refused with exit 3 (human input detected) and the round stopped. No capture shows the outcome.

### A8 Engine crash mid-answer: NOT TESTED (operator present)

I prepared the kill script but it never fired ("batch ended early"). llama-server was not killed.

### A9 Settings → Models: NOT TESTED (operator present)

### A10 Quit and wipe: NOT TESTED (operator present)

I did not quit or wipe after the presence refusal, and no GUI input was sent. Profile A's app is **still running**: vysted-terminal pid 33963, sidecars 33986 and 34005, llama-server 35208. It holds a fully downloaded 2.7 GB model. The lead needs to quit it once the operator is away, or ask the operator to, and then run `scripts/fresh-profile.sh wipe /private/var/folders/1s/3bgs17xd07z839yf5kj6mc3m0000gn/T/vysted-profile.yVBoKz`.

## Path C: Skip for now

C1 to C4: **NOT TESTED** (operator present). I never launched profile C. The batch is prepared at `scratchpad/bc.json`.

## Path B: My own API key

- B1: **NOT TESTED** (operator present). The batch is prepared at `scratchpad/bb.json`.
- B2: **NEEDS-MANUAL-CHECK.** The own-key success path cannot be tested because there are no real keys on the rig.
- B3: **NOT TESTED.**

## Findings

1. **F1 (medium), A3.** The model step lists the operator's own Ollama models under "Already on this computer": `qwen3:8b (Ollama)`, `qwen2.5:7b (Ollama)` and `llama3.1:8b (Ollama)`, each with "Use this one". The sidecar reads `~/.ollama/models` (`/local-models/installed` paths point there). A fresh profile is therefore not isolated from Ollama data on the machine. It is a label, not an instruction to run ollama, but it puts "Ollama" in first-run UI. Capture: `A-local/03-local-models.png`.
2. **F2 (medium), A3.** On a 16 GB Mac where all visible models read "RUNS WELL HERE", the recommended Qwen 3.5 4B still shows "This computer is short on free memory for Qwen 3.5 4B. Closing your web browser and other apps…". The warning is driven by momentary available RAM, so a stranger gets a contradictory signal on the recommended pick. Capture: `A-local/03-local-models.png`.
3. **F3 (high), A5/A6.** After the model was installed, verified and active, and llama-server had logged `model loaded` and `listening` at 21:05:49, the header chip still read "ON THIS COMPUTER · NOT RUNNING — SET UP IN SETTINGS" at 21:18:22. The "Add a cloud provider key — or download a model that runs on this computer — to turn on the assistant" banner was still showing as well. The chip and banner do not reflect a ready on-computer engine. I did not determine whether the UI's engine state really is not-ready or whether only the chip is stale. Capture: `A-local/11-relaunch-ready.png`; the earlier `A-local/08-strip-downloading.png` and `A-local/10-before-quit.png` show the same during the download.
4. **F4 (medium), A3/A4.** The first-run dialog is taller than the default 1280×832 window and the dialog content does not scroll. The primary "Download Qwen 3.5 4B (2.6 GB)" button and the "Continue →" button are clipped at the bottom edge, and the dialog top sits under the header. Mouse users on a 13–14" MacBook at default size may not be able to reach the primary action. Captures: `A-local/03-local-models.png` (Download clipped), `A-local/04-downloading.png` (Continue clipped), `A-local/03b-local-models-tall.png` (fits at 862 pt).
5. **F5 (low), A3.** Granite 4.2 8B and Qwen 3.5 9B and their fit labels sit below the fold of the scroll area, so I could not verify them. This is a rig coverage gap, not a defect.
6. **F6 (process), rig.** A rig refusal is not only operator presence. Each new rig process needs 900 s of raw idle after the rig's own last keystroke, which limits a round to one batch per ~15 min. Within the sentinel window that is about 8 batches, too few for A+B+C with adaptive steps. The 21:18:52 refusal was a genuine non-rig HID event about 5.7 s after the rig's return key, and I treated it as operator presence.

## Captures

15 evidence captures, all in `A-local/`, all registered by `rig.py capture`. There is also one scratch capture of the stale instance, which is not evidence.

## Lead disposition (21:24 IST, 15 Oct)

- **F3: high, fixed before v0.10.0.** Root cause: `useKeylessReadiness` (`src/lib/provider-validation.ts`) caches a negative probe, and nothing re-runs the probe when that entry expires or when the local engine changes state. The chip and banner therefore kept the answer they got before the engine started. Fix round `wf_f80dc41a-982`.
- **F4: raised to high (a dead end for a mouse user at the default window size), fixed before v0.10.0.** The dialog is now capped to the viewport and scrolls. Same fix round.
- **F7 (lead, from capture 07 + code): high, fixed before v0.10.0.** The tour promises "we'll let you know when it's ready". The ready prompt with "Ask: …" is keyed on `waitingQuestion`, which lived in memory only and was lost on the relaunch in A6. It is now persisted in app-meta. Fix round `wf_082e94c9-e26`.
- **F8 (lead, from the cleanup): medium, already in the 0.10.1 backlog.** At 21:22 the lead sent SIGTERM to profile A's app (pid 33963). The sidecars exited, but llama-server (pid 35208) was left behind with ppid 1. This is live evidence for the backlog item "if the app dies without `RunEvent::Exit`, llama-server is left running". A graceful quit with cmd+q cleans up correctly (A6).
- **F1: by design (rc2 certifier L7).** The app offers models Ollama already has on disk, so they are not downloaded twice. Nothing tells the user to run Ollama.
- **F2: low, filed for 0.10.1.** The fit label is based on total RAM, while the notice is based on RAM free right now.
- **F5, F6: rig coverage limits, not product defects.**
- Steps not driven: A7 to A10, the whole of C and B. They are NOT TESTED because the operator was present from 21:18:52. They are part of the operator's Mac walk (DECISIONS §0).
