# R16 GUI round 2: Vysted Terminal 0.10.0 (v0.10.0 draft release)

**Round status: STOPPED, operator present.** At 23:02:31 IST the rig refused mid-batch with exit 3:
`REFUSED: human input detected mid-batch: idle 12.6s but 92.5s since the rig's own last event`.
I stopped as the brief requires. No GUI input or capture was sent after that. Steps from A2 onward could not be driven.

## Header

- **Build:** `v0.10.0`, `Vysted-Terminal-macOS-AppleSilicon.dmg`, `CFBundleShortVersionString` = `0.10.0`.
- **dmg sha256:** `f8f494fcfdc3327f5396b4024d6a6e9be854ff794ba8b35b37d61a931e368a7e`, which matches SHA256SUMS.txt: **yes**.
- **App:** `docs/redesign/verification/r16/local/gui-app2/Vysted Terminal.app`. It was copied with `ditto` from the dmg, which was mounted read-only and then detached. It was not installed in /Applications.
- **Clock (`date`):** I started at 22:49:38 IST and launched profile A at 22:53:37. Batch 1 started at 23:00:30 with idle at 908.0 s and was refused at 23:02:31.
- **Rig idle at start:** 264.0 s at 22:49. The away sentinel was valid until 2026-10-15T20:00:00Z.
- **Capture scale:** the window is the default 1280×832 pt and captures are 2560×1664 px, so the scale is 2×. I did not resize the window.
- **Overlays:** not tested this round because batch 1 was keyboard-only. Round 1 had already shown that clicks pass through the Wispr Flow overlay.

## Path A: On this computer

Profile A: `/private/var/folders/1s/3bgs17xd07z839yf5kj6mc3m0000gn/T/vysted-profile.cuCesj`

### A1 Terms, choice, model step (F4 check), download, Continue, tour: PASS

- **Did:** pressed return on the terms dialog and return on "On this computer". Pressed tab then shift+tab to focus Download, then return. Pressed tab, shift+tab, shift+tab to focus Continue, then return. Went through the tour with return, and pressed tab, tab, return on "Got it".
- **Terms and choice:** both appeared as they did in round 1 (`01-terms.png`, `02-choose.png`).
- **F4 check at the default 1280×832 window:**
  - The model dialog now has its own vertical scrollbar along the right edge and is capped to the viewport.
  - With focus on "Download Qwen 3.5 4B (2.6 GB)", the dialog did **not** scroll that button fully into view. Only its top edge shows at the bottom of the dialog (`04-focus-download-default-size.png`).
  - Return on it still started the download.
  - After the download started, focusing Continue did scroll the dialog. "Downloading — 3% · about 2 min left", "We'll finish in the background — you can keep going. The bar at the top shows progress.", "Continue →" and "Skip for now" were all fully visible (`06-focus-continue.png`).
  - A mouse user can now reach both buttons by scrolling the dialog. The dead end from round 1 is gone.
- **Model step text:**
  - "This computer has 16 GB of memory, so Qwen 3.5 4B is the best balance of quality and speed."
  - "This computer: 16.0 GB RAM · 64.6 GB free space"
  - Granite 4.2 3B and Qwen 3.5 4B are both tagged "RUNS WELL HERE".
  - The "Already on this computer" block lists 3 Ollama models (F1, by design).
  - The memory notice reads "This computer is short on free memory for Qwen 3.5 4B…" (F2, filed for 0.10.1).
- **Tour:** card 1 of 4 appeared, then card 4 of 4. The TRY IT step read "Your model is still downloading (9%) — we'll let you know when it's ready. Then try: “How has Reliance Industries done over the past year?”" with "Got it".
- **Strip:** "Downloading Qwen 3.5 4B — 13% · 22 MB/s · about 2 min left", with Pause.
- **Captures:** `A-local/01-terms.png` to `A-local/10-strip-downloading.png`.
- **Note:** F4 is fixed in substance. One small residual remains: keyboard focus on Download does not scroll it into view (R2-F1).

### A2 F3 check, ready state after download: NOT TESTED (operator present)

- **Seen before the stop:**
  - 23:01:47 (`11-wait-30s.png`) and 23:02:17 (`11-wait-60s.png`): "Downloading Qwen 3.5 4B — 65% · 23 MB/s · less than a minute left".
  - While downloading, the chip read "ON THIS COMPUTER · NOT RUNNING — SET UP IN SETTINGS" and the "Add a cloud provider key — or download a model…" banner was shown. That is expected before the engine is ready.
- **From the log after the stop (not GUI):**
  - The `.gguf` was finalised at 23:02.
  - llama-server logged `model loaded` and `listening on http://127.0.0.1:59460`.
  - The sidecar logged `PUT /local-models/engine` 200 at 23:02:58.
- **Not verified:** whether the chip, banner and "Your on-computer model is ready." strip update within 30 s. This is the F3 fix check and **remains unverified**.

### A3 Reliance answer: NOT TESTED (operator present)

### A4 Engine crash mid-answer: NOT TESTED (operator present)

No kill was sent.

### A5 Settings → Models: NOT TESTED (operator present)

### A6 Quit and wipe: NOT TESTED (operator present)

- No cmd+q was sent and the profile is not wiped.
- **Still running:**
  - vysted-terminal pid 44265
  - sidecars and MCPs 44283, 44285, 44288, 44289
  - llama-server pid 45333, holding a verified 2.7 GB model
- I did not SIGTERM the app, because a SIGTERM orphans llama-server (round-1 F8).
- **Cleanup:** when the operator is away, quit the app with cmd+q, then run `scripts/fresh-profile.sh wipe /private/var/folders/1s/3bgs17xd07z839yf5kj6mc3m0000gn/T/vysted-profile.cuCesj`.

## Path C: Skip for now

C1 and C2: **NOT TESTED** (operator present). Profile C was never launched.

## Path B: My own API key

- B1: **NOT TESTED** (operator present). Profile B was never launched.
- B2: **NEEDS-MANUAL-CHECK.** There are no real keys on the rig.

## Findings

1. **R2-F1 (low), A1.** Round-1 F4 is fixed. At 1280×832 the model dialog is capped to the viewport and scrolls, and Continue scrolls into view on focus. One residual: keyboard focus on "Download Qwen 3.5 4B (2.6 GB)" leaves the button mostly below the dialog's visible edge. Activation still works, and a mouse user can scroll to it. Capture: `A-local/04-focus-download-default-size.png`.
2. **R2-F2 (process), rig.** The round stopped on a genuine non-rig HID event at 23:02:31, 92.5 s after the rig's last keystroke. The fixes for F3 (chip and banner after the engine is ready) and F7 (persisted waiting question / ready prompt) have no GUI evidence from this round. Paths C and B were not reached.
3. Round-1 F1 (Ollama models listed, by design) and F2 (free-memory notice next to "RUNS WELL HERE", 0.10.1) reproduce unchanged in `A-local/03-models-default-size.png`.

## Captures

12 captures, all in `A-local/` and all registered by `rig.py capture`: `01-terms` to `10-strip-downloading`, `11-wait-30s` and `11-wait-60s`.
