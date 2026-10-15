# R16 "Easy Install" run report (0.10.0)

## Outcome

0.10.0 is built, tested and tagged, and its release is a draft waiting for you. A new user downloads one file per operating system, installs it, accepts the terms and picks one of three paths: a model that runs on the computer, their own API key, or skip. The "on this computer" path downloads a model sized to the machine, with its licence shown first, and the app runs it with a bundled llama.cpp. No Ollama, no key, no account, no terminal. The app updates itself from signed GitHub releases.

Tags:

- `r16-rc1` at `d7a71a46`: the release pipeline and the updater; beta.1 updated itself to beta.2 on this Mac.
- `r16-rc2` at `78d29509`: the artifacts are the `v0.10.0-beta.4` draft, built at `1d624bf3`.
- `v0.10.0` at `5bf74f87`: the merge of PR #4 into `main` (CI 9/9 at `4e77f1a9`). Release run 38772784934 was all green and produced the draft (not a prerelease). It carries the stable and versioned dmg, Setup.exe and AppImage, the app tarball, three `.sig` files, `SHA256SUMS.txt` and `latest.json`. The lead downloaded the three installers: each sha256 matches, and LICENSE and THIRD_PARTY_NOTICES.md are inside every bundle.

What is not proven on screen:

- The first answer from the on-computer model.
- The engine crash mid-answer.
- The Models page.
- The "My own API key" and "Skip for now" paths.
- The update prompt.

Two GUI rounds each stopped when the rig saw input at the keyboard: the first at 21:18 (beta.4) and the second at 23:02 (v0.10.0). The second confirmed the F4 fix on screen. These steps are in your Mac walk (DECISIONS §0, step 1).

## The plain paragraph

**What shipped:**

- One-file installers for macOS (Apple Silicon), Windows x64 and Linux (AppImage), built by GitHub Actions into a draft release with checksums.
- A signed self-updater.
- A bundled llama.cpp engine (build b11429) with a four-model catalog sized to the machine's memory.
- A first-run wizard (terms, then on this computer / own key / skip, then a short tour that ends in an example question).
- Layperson docs, including how to get past the unsigned-app prompts.

**What was measured:** four models on this 16 GB Mac, at 32k context and at 16k context. Qwen 3.5 4B had the best rate of answers with correct tool use and no invented figures, so it is the default on every tier. The 8 GB and 32 GB tiers are inferred from those measurements, not measured.

**What is left for you:**

1. Walk the Mac build (the GUI steps above and Gatekeeper's first-open prompt).
2. Run the Windows checklist on the ROG.
3. Publish the draft release.

## The four scenarios

**1. A download dies at 80% on bad Wi-Fi, then the user relaunches.** Shown on screen. In the GUI round (step A6), the app was quit at 77.8% of Qwen 3.5 4B. The `.part` file was 2,133,735,015 bytes, and every process of that profile exited. On relaunch there was no terms dialog and no wizard. The download picked up from the partial file, not from zero, then verified the sha256 and started the engine, all without a click.

Decisions this changed:

- An unexpected download error now ends in "failed, Try again" instead of a silent stop.
- A non-resumable failure restarts from zero.
- **Fixed after the round (F3):** the header chip and the setup banner kept saying "not running" after the engine was ready. They now re-check when the engine's state changes.
- **Fixed after the round (F7):** the tour's promise "we'll let you know when it's ready" did not survive the relaunch. The waiting question is now stored, so the "ready — Ask: …" prompt appears after a relaunch too.

On a dead connection the strip says the download stopped and offers Try again, Use my own key, and Cancel download.

**2. An 8 GB Mac with a browser open.** From code and tests; there is no 8 GB machine here.

- The machine falls in the `8gb` tier, with a 24k context.
- The wizard recommends Qwen 3.5 4B and labels it "Tight fit here".
- The yellow notice says "This computer is short on free memory for Qwen 3.5 4B. Closing your web browser and other apps before you ask a question will help", and offers "Use my own key instead". The notice shows when the fit is tight, or when the RAM free right now is below the model's measured need (peak RSS plus 1 GiB: 6.7 GB for the 4B).
- The 8B and 9B models read "Too big for this computer".

The decision it changed: the per-model `minRamBytes` values come from measured peak memory, not from guesses. Inferred, not measured: whether 24k context leaves room for a browser on a real 8 GB Mac.

**3. The engine crashes mid-answer.** From code and tests; the GUI step was not reached.

- The core restarts llama-server on its own, with backoff, up to 4 crashes in its window. The Rust test `a_crash_while_ready_restarts_with_backoff_and_no_leak` covers this. After that, the strip offers to start it again.
- The answer in progress ends with "The on-computer model stopped while answering. It restarts on its own — send your question again in a few seconds." There is no stack trace.

The decision it changed: after the F3 fix, the header chip drops to "not running" during the restart and comes back by itself.

Filed for 0.10.1:

- A slow read can be misreported as a crash.
- A force-quit or SIGTERM of the app leaves llama-server running. This was seen live during cleanup, where it was left with ppid 1. A normal Quit cleans up.

**4. An update arrives during a model download.** From code and tests. The update prompt's button reads "Update after the download finishes" while a download runs. If clicked, it waits ("Updating after the download finishes…") and installs when the download ends. Even if the app does restart mid-download, the download resumes from its `.part` file on the next launch (scenario 1).

The decision it changed: the updater never interrupts a download.

Not provable this run: the updater only offers published, non-prerelease releases, so the first real in-app update is 0.10.0 to 0.10.1. Users of 0.9.0 or earlier install 0.10.0 by hand once; the release notes say so.

## Gates

- **r16-rc1:** passed.
- **r16-rc2:** passed with conditions, all met.
  - Certified by a fresh-context Opus agent: `docs/redesign/verification/r16/rc2/CERTIFY.md`.
  - The full chain (int9) was green.
  - PR CI was 9/9 at `78d29509`.
  - Gate 8 (no trading surface): 8 tests passed.
- **v0.10.0:**
  - Docs: done.
  - The final review over v0.9.0..HEAD (`wf_2d30ccd9-766`): its criticals and highs were fixed in one round, and the rest are in `docs/redesign/BACKLOG_0.10.1.md`.
  - The GUI rounds: partial, below the brief's bar (paths B and C, the first answer, the engine crash, the Models page and the update prompt are not on screen). v0.10.0 was tagged anyway because only you can publish, and §0 step 1 makes your Mac walk come before Publish. Round 1 (beta.4) covered path A through the download, the quit at 78% and the relaunch. Round 2 (v0.10.0) covered path A through the download again, with the F4 fix confirmed. Verdicts: `r16/gui/VERDICTS.md`, `r16/gui2/VERDICTS.md`.
  - Three highs from the GUI round were fixed before the tag: F3 (the chip and banner did not show a ready engine), F4 (the first-run dialog was cut off at the default window size, a dead end for a mouse user) and F7 (the example question was lost on relaunch).
  - Verdicts: `docs/redesign/verification/r16/gui/VERDICTS.md`.

## Telemetry (one line per workflow)

Model names are the ones each agent reported running.

| Workflow                               | Agents | Models                                                                                                    | Wall-clock                                                     | Tokens          | Tool calls | Result                                                                                           |
| -------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | --------------- | ---------- | ------------------------------------------------------------------------------------------------ |
| recon (first-run, terms, local models) | 1      | opus-5-5                                                                                                  | 0.8 min                                                        | 95k             | 12         | map of the code paths                                                                            |
| wave 1 `wf_13581ecc-d2f`               | 6      | opus-5-5 ×4; claude-sonnet-5 ×2 (the `sonnet` alias, not 5.5)                                             | 24.2 min                                                       | 1,058k          | 527        | release, updater, llama bundling, engine, models, profile                                        |
| wave 2                                 | 3      | pinned ids (opus-5-5 / sonnet-5-5)                                                                                      | 17.7 min                                                       | 559k            | 240        | wizard, models page, research Advanced                                                           |
| measurement harness                    | 1      | opus-5-5                                                                                                  | 58.4 min                                                       | 238k            | 100        | local-lane battery + invented-figure check                                                       |
| docs wave `wf_14f54fb9-690`            | 3      | sonnet high ×2, haiku medium (notices and the Windows list only)                                             | 7.2 min                                                        | 396k            | 98         | README, release notes, guides                                                                    |
| final review `wf_2d30ccd9-766`         | 8      | opus-5-5 medium                                                                                           | 7.0 min                                                        | 873k            | 159        | criticals and highs verified                                                                     |
| fix round `wf_643d56d8-85e`            | 3      | opus-5-5 ×2, sonnet-5-5                                                                                   | 6.6 min                                                        | 321k            | 104        | review fixes                                                                                     |
| rc2 certification `wf_bd2c8517-89f`    | 1      | opus-5-5 medium                                                                                           | 174 min (includes the usage wall)                              | 259k            | 85         | certified with conditions                                                                        |
| GUI round `wf_5110316a-670`            | 1      | opus-5-5 medium                                                                                           | 214 min (includes the wall)                                    | 298k            | 100        | stopped on operator presence                                                                     |
| GUI fixes `wf_f80dc41a-982`            | 1      | opus-5-5 medium                                                                                           | 4.6 min                                                        | 99k             | 34         | F3, F4                                                                                           |
| GUI fix `wf_082e94c9-e26`              | 1      | sonnet-5-5 high                                                                                           | 3.4 min                                                        | 76k             | 11         | F7                                                                                               |
| GUI round 2 `wf_b5269627-943`          | 1      | opus-5-5 medium                                                                                           | 14.6 min                                                       | 138k            | 34         | stopped on operator presence; F4 confirmed                                                       |
| single agents (Agent tool)             | 7      | Agent-tool aliases `opus` / `sonnet`; the `sonnet` alias was confirmed as claude-sonnet-5 on the coverage writer (Linux AppImage, VC++ runtime, Qwen system-message fix, context fix, coverage, two recons) | coverage 30.4 min, others 0.3–6.6 min | 792k (recorded) | 328        | the coverage writer died at the usage wall and the lead committed its tests; the context-fix agent's usage was not recorded |

Walls and pauses:

- A session limit hit at about 05:20, reset 09:00.
- A session limit before 20:30, reset 20:30; its start was not recorded.

The measurement sweeps ran as detached shell scripts, not agents: sweep1 was stopped, sweep2 ran 09:31–12:04 and sweep3 finished at 17:07.

The Agent tool's `sonnet` alias ran claude-sonnet-5, not 5.5. Workflow scripts with a pinned `claude-sonnet-5-5` ran the right model.
