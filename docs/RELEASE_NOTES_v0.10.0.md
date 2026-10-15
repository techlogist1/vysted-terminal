# Vysted Terminal 0.10.0 - release notes

0.10.0 ("R16 Easy Install") is the public launch. Vysted Terminal is a source-available finance terminal under PolyForm Strict 1.0.0. The plugin contract and the example plugin are Apache-2.0 (see `LICENSING.md`). This release is about one thing: getting from a download to a working assistant without a terminal, a Python install or a paid key.

Vysted has no trading of any kind. Nothing it shows is investment advice.

## What is new

- **One-file install.** Download a single file for your system and open it. Mac gets a `.dmg`, Windows gets a setup `.exe`, Linux gets an AppImage. Nothing else needs to be installed first. Each file has a stable download name, and a `SHA256SUMS.txt` lists the expected checksum of each.
- **Models that run on your own computer.** Vysted now bundles llama.cpp's `llama-server` (build b11429, MIT licence). You download a model once, from the first-run question or from **Settings, Models**, and the assistant runs on your machine. Nothing you ask leaves it. The licence is shown before each download. There are four choices, all Apache-2.0: IBM Granite 4.2 3B, Qwen 3.5 4B, IBM Granite 4.2 8B and Qwen 3.5 9B (about 2.1, 2.6, 5.0 and 5.3 GB). Vysted recommends one for your memory size (under 8 GB, 8 GB, 16 GB, 32 GB and more) <!-- R16-MEASURE: per-tier recommendation -->. Ollama models already on the machine are detected and can be used.
- **Downloads you can trust.** A dropped connection or a relaunch resumes the download where it stopped. Vysted checks free disk space before and during the download. The finished file is verified against a known checksum before use. A damaged file is deleted and you are told to try again. If the engine stops by accident, it restarts itself, up to 3 times in 10 minutes. After that it says so plainly and offers **Try again**.
- **A first-run setup.** After the terms, **How should Vysted think?** offers three paths: **On this computer**, **My own API key**, or **Skip for now**. Own keys are stored in the OS keychain and sent only to that provider. Skipping still leaves charts and data working without a key. A short tour follows and ends with an example: "How has Reliance Industries done over the past year?" (or, if you skipped, **Show Reliance on the chart**). Every path has a way forward, and Settings can change the choice later. Research works without a key. Docker and a private SearXNG search are optional, under **Settings, Advanced**.
- **A built-in updater.** Vysted checks 15 seconds after launch and every 6 hours. It shows the new version and its notes, and **Restart to update** installs it. While a model is downloading, the button reads **Update after the download finishes**. Updates are signature-checked with Vysted's own signing key. Self-update was proven end to end on a Mac, from 0.10.0-beta.1 to 0.10.0-beta.2 (`docs/redesign/verification/r16/rc1/RC1_PROOF.md`).

## Install

Pick the file for your computer from the latest release. All of these are unsigned, so the system warns you the first time. The warning is expected.

- **Mac (Apple Silicon only).** Open the `.dmg` and drag **Vysted Terminal** to Applications. Open it. macOS says it cannot verify the app. Click **Done**. Open **System Settings, Privacy & Security**, click **Open Anyway** next to the Vysted Terminal notice, and confirm. On macOS 15 and later, right-click then Open no longer works. If macOS says the app is "damaged", run `xattr -dr com.apple.quarantine "/Applications/Vysted Terminal.app"` once in Terminal.
- **Windows (64-bit).** Run the setup `.exe`. It installs for your user account only. If Windows shows "Windows protected your PC", click **More info**, then **Run anyway**.
<!-- R16-LINUX -->
- **Linux (64-bit, x86_64).** Run `chmod +x Vysted-Terminal-Linux-x86_64.AppImage`, then run the file. On Ubuntu 22.04 and newer, install `libfuse2` first (on 24.04 the package is `libfuse2t64`).
<!-- /R16-LINUX -->

Downloads (these links resolve once the release is published):

- `https://github.com/techlogist1/vysted-terminal/releases/latest/download/Vysted-Terminal-macOS-AppleSilicon.dmg`
- `https://github.com/techlogist1/vysted-terminal/releases/latest/download/Vysted-Terminal-Windows-x64-Setup.exe`
<!-- R16-LINUX -->
- `https://github.com/techlogist1/vysted-terminal/releases/latest/download/Vysted-Terminal-Linux-x86_64.AppImage`
<!-- /R16-LINUX -->

The first launch takes longer than later ones while the built-in data engine unpacks. Wait for the status chip to show that it is connected.

## Checksums

`SHA256SUMS.txt` is attached to the release (`https://github.com/techlogist1/vysted-terminal/releases/latest/download/SHA256SUMS.txt`). It lists a SHA-256 checksum for each download. Compare it with `shasum -a 256 <file>` on a Mac or `certutil -hashfile <file> SHA256` on Windows.

## Known limitations

- **Not code-signed.** Apple and Microsoft signing is out of scope for this release, so the first-open warnings above are expected.
- **Linux is untested on hardware.** The AppImage has not been run on a real Linux machine.
- **Windows has not been hand-tested on real hardware** for this release.
- **Mac is Apple Silicon only.** There is no Intel Mac build.
- **Under 8 GB of memory, the on-computer lane is tight.** It can run out of room on very large answers. On such a machine, an own key is suggested.
- **Small on-computer models can still word things loosely, and in rare cases state a figure they never fetched** (the limitation documented in 0.9.0, `docs/RELEASE_NOTES_v0.9.0.md`). Figures are checked against what the data tools returned, but confirm any figure that matters at the source. Portfolio changes the assistant proposes always wait for your review.
- **On a Mac, each update asks for your login password once per saved API key.** The app is unsigned, so macOS treats every update as a new app. Type your password and click **Always Allow**.

## Licence

Source-available under PolyForm Strict 1.0.0 for the core. Commercial use, modification or redistribution needs a paid licence (`COMMERCIAL_LICENSE.md`). The plugin contract and example plugin are Apache-2.0. The bundled `llama-server` is MIT. The four models are Apache-2.0. See `LICENSING.md`.
