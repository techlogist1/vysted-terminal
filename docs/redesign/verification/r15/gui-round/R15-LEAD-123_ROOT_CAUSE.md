# R15-LEAD-123 — root cause (late main-sidecar bind latched as failed for the session)

- judge: Opus 5.5 (claude-opus-5-5), judgement tier, medium effort; read-only, no advisor.
- sha: ace7dd76 (`src/` and `src-tauri/` identical in the working tree; `git diff --stat ace7dd76 -- src src-tauri` is empty). Line numbers below are at ace7dd76.
- evidence read: `gui-round/R15-LIFECYCLE-001/DRIVE.md` (9368c62 launch 1, ace7dd7 launches A/B/C) and its `raw/ace7dd7-app-stdout-excerpts.txt`; `gui-round/R15-LIFECYCLE-008/DRIVE.md` (launches 1 and 2); `stage-d/bundle-rehearsal/REHEARSAL.md` (idle M1 cold launch).

## Correction to the finding text

The product does **not** SIGTERM the main sidecar. In both drives, the "THE DATA ENGINE STOPPED (SIGNAL 15)" chip came from the verifier's own `kill 4210` / `kill 12824` for LIFECYCLE-001 check 4 (DRIVE.md lines 105-106 and 125-127). The product's own end state in every late-bind launch is the chip **"SIDECAR ERROR — THE DATA ENGINE DID NOT COME UP ON PORT N."** In that state the sidecar is alive and answers `/health` 200 on that port (captures `ace7dd7-05`, `ace7dd7-10`, and 008 `ace7dd7-01`/`-10`). The only kill of the main child is on app exit (`src-tauri/src/lib.rs:769-776`, `RunEvent::Exit`).

The tally is also **5 of 6** loaded launches, not 5 of 5:

| Launch | Main sidecar bound | Outcome |
|---|---|---|
| 9368c62 launch 1 | +103 s | failed |
| ace7dd7 A | +107 s | failed |
| ace7dd7 B | +107 s | failed |
| ace7dd7 C (load 6.61) | +84.8 s | **succeeded** |
| 008 launch 1 | +96 s | failed |
| 008 launch 2 | +108 s | failed |

The register line should be reworded to: "declared failed at 90 s and never recovers although the engine is healthy".

What the product does kill while it is still extracting is the **sec-edgar MCP child**. It was killed at about +91 s in 3 of the loaded launches (`src-tauri/src/sec_edgar_mcp.rs:149-168`; openbb's twin is at `src-tauri/src/openbb_mcp.rs:152-173`). That is an adjacent, degraded-only symptom: the `/sec` routes return 501. It is not this finding.

## 1. Mechanism

Two latches combine. Neither is a kill.

1. **The core settles `Failed` at the end of a fixed 90 s window, and nothing ever moves it back.**
   - `start_main_sidecar` (`lib.rs:382`) spawns the child and starts a wait thread (`lib.rs:441-479`).
   - That thread calls `wait_for_port_with_retries(port, MCP_PORT_WAIT_SECS=45, MCP_PORT_WAIT_ATTEMPTS=2, …)` (`lib.rs:449-460`; constants at `lib.rs:180` and `:186`; helper at `lib.rs:197-212`). If that returns true, it then runs a 15 s `/health` check (`lib.rs:463`).
   - On a timeout it calls `settle_boot(false)` (`lib.rs:471`). That sets `SidecarPhase::Failed` with the reason "The data engine did not come up on port N." (`lib.rs:67-80`).
   - `settle_boot` only moves out of `Starting` (`lib.rs:69-71`), and nothing re-polls afterwards: the thread logs "did not come up" and exits (`lib.rs:477-478`). The only other writer is the Terminated arm (`lib.rs:430-435`), and it can only write `Failed`.
   - So a child that binds at +96 to +108 s binds into a status that already says `Failed`, permanently.
2. **The renderer treats the core's `Failed` as authoritative on every call, so its own recovery loop is disabled.**
   - `resolvePortToBaseUrl` re-reads `get_sidecar_port` and throws `status.reason` whenever `state === "failed"`, without probing (`src/lib/sidecar-client.ts:90-103`, throw at `:98-101`).
   - `resolveAndAwaitReady` calls it once per probe round (`sidecar-client.ts:141-163`). Its own deadline is 120 s (`:143`), so on its own it would have outlasted a 108 s bind. Instead the core's `Failed` at about 90 s aborts it with the core's reason.
   - `getSidecarBaseUrl` re-arms on failure (`:125-135`). The app store's 20 s `/health` re-probe also keeps running while in error (`src/store/app.ts:50-76`, `SIDECAR_REPROBE_MS = 20_000` at `:20`).
   - But every re-probe goes back through `resolvePortToBaseUrl`, which throws at once on the sticky `Failed`. Every panel, the workspace restore (`src/lib/workspace.ts:730`, `:1046`) and Settings → Copy diagnostics all fail the same way.
   - The chip shows `Sidecar error — <reason>` (`src/components/StatusChrome.tsx:233-240`).
   - The drives confirm no webview request reached the late sidecar after it bound (DRIVE 001 line 92).

Why there is no recovery: the renderer's re-probe and re-arm machinery exists and would have worked. But it consults a core status that was latched at 90 s and is never revised. The fixed budget of 90 s + 15 s does not depend on whether the child is still alive and working.

## 2. Is the trigger realistic for a first launch?

What was measured:
- **Idle M1, release bundle (REHEARSAL.md §"Sidecar warm-up"):** the main sidecar listened at about 40 s, and all three at about 60 s. That is about 2.25× headroom against 90 s.
- **Loaded M1** (load 3-6.6, the concurrent rc2 battery also extracting PyInstaller binaries, XProtectService at about 56 % CPU scanning each fresh `_MEI` extraction, per 008 DRIVE line 33): the main sidecar bound at 96-108 s in 5 of 6 launches, and once at 84.8 s. So ordinary contention eats the whole 2.25× margin. The main sidecar is the largest `--onefile` child and was the last to answer in every timeline.

What was not measured, and is plausible: slower Intel Macs (slower decompression and imports), and Windows with Defender real-time scanning of a fresh `_MEI` extraction. Both add work to exactly the phase that overran, but there is no number in the evidence. A machine that is busy at launch (browser, IDE indexing, a container runtime, launch at login) is the measured case in spirit. The drives' load was heavier than typical, and specifically disk-contended because other `--onefile` binaries were extracting at the same time.

**A relaunch is not a reliable workaround.** A `--onefile` binary extracts to a fresh `_MEIxxxxxx` directory on every launch and removes it at exit (the drives record "no _MEI orphan" after each quit). There is no warm `_MEI` to reuse. Only the OS page cache is warm, and every drive launch was already page-cache-warm (no reboot). Under the same load, relaunches recovered 1 time in 3:

- ace7dd7 A → B: both failed.
- 008 launch 1 → launch 2: both failed.
- ace7dd7 B → C: succeeded, by about 5 s of margin, at load 6.6.

Verdict: realistic for a minority of first launches, and for repeat launches on a busy machine. It is not reproduced on an idle M1.

## 3. Severity: **high (confirm the provisional high)**

Reasons, against the register's scale:
- **Core flow broken:** the session is a total loss — no panel data, no workspace restore (the user's saved layout, holdings and notes are not loaded), no diagnostics bundle. The engine is healthy the whole time.
- **No workaround inside the session:** there is no respawn or "reconnect" path. The 20 s re-probe cannot get past the latch.
- **The relaunch workaround is unreliable** (1 in 3 under load, above). The only dependable workaround is to idle the machine and relaunch, and the user is not told that.
- **Realistic share:** measured on a busy M1 at 5 of 6. An idle M1 has only a 2.25× margin. The Intel and Windows-Defender cases are plausible and unmeasured.

The case for medium is that idle machines pass and some relaunches pass. It loses because a relaunch is a coin flip, not a workaround, and the failure mode shows "error" over a working engine.

Confidence: 7/10. The share of real users above a 90 s cold bind is unmeasured. The latch itself is certain.

## 4. Fix shape (smallest correct)

The genuine-exit path is already immediate and independent of the timer. When the child dies, the Terminated arm sets `Failed` with the precise reason at once (`lib.rs:430-435`), and `settle_boot` preserves that reason (`lib.rs:69-71`). So the boot timer only has to stop being shorter than a contended cold extraction. Nothing needs to learn to "kill only on a genuine exit": the main sidecar is never killed on a timeout.

1. **`src-tauri/src/lib.rs`, about +4/-2 lines.** Give the main sidecar its own budget instead of the shared MCP pair, which also drives the MCP kill and the smoke test's `MCP_BIND_TIMEOUT_MS`, pinned by `smoke_bind_budget_matches_supervisor` at `lib.rs:1112-1128`:
   - Add `const MAIN_SIDECAR_WAIT_ATTEMPTS: u32 = 6;`, which is 45 s × 6 = 270 s. That is 2.5× the worst observed 108 s. It needs a `ponytail:` note that a boot slower than 270 s still latches and the real fix is `--onedir` (BLOCKERS "Phase 9.5 UC1").
   - Use it at `lib.rs:449-452`.
   - A crashed child is still reported at once. A hung-but-alive child is now reported at about 285 s instead of about 105 s, and shows "CONNECTING…" until then, which is the honest state.
2. **`src/lib/sidecar-client.ts:143`, 1 line.** Raise the renderer's deadline from `120_000` to `300_000`. It must stay **above** the core's 270 s + 15 s health budget. Otherwise the renderer gives up first, the workspace restore falls back to the default layout, and the core's reason is masked by the generic 503.

Estimated diff: about 6 lines of product code, plus about 40 lines of tests.

**Do not implement it as "flip `Failed` → `Ready` on a late bind" without a second change.** `restoreLastSessionOrDefault` sets `restoreSettled = true` even when the restore could not reach the sidecar (`src/lib/workspace.ts:1013-1035`, settle at `:1027`; the failure is swallowed at `:1061-1063`, which then applies the default layout). Today the sticky `Failed` accidentally protects the user's data, because `flushAutosave` → `workspaceUrl()` throws. If the core recovered after the restore had already fallen back, the first layout change would call `autosaveLayout` (`:1115-1126`), and `buildWorkspacePayload` (`:633-658`) would POST the empty default slices over `__autosave__`. That wipes the saved holdings, watchlist and notes. The budget-sizing fix above never reaches that state, because the core stays `Starting` and the restore keeps waiting. Any recover-from-`Failed` design must first gate `restoreSettled` on the restore having reached the sidecar (a 404 counts; a thrown fetch does not), and re-run the restore on the first reachable transition.

Adjacent, not in scope: the MCP children are still killed at 90 s (`sec_edgar_mcp.rs:149-168`, `openbb_mcp.rs:152-173`). Under load, sec-edgar lost that race in 3 launches, and the main sidecar then reported a stale `"available": true` for the killed child (001 DRIVE lines 42 and 88). It deserves its own low/medium entry.

## 5. Deterministic test shape

- **vitest, `src/lib/sidecar-client.test.ts`** (fake timers, same harness as the existing "a spawn that fails while the probe waits" case):
  - `invoke("get_sidecar_port")` answers `{state:"starting"}` until fake t = 130 s, then `{state:"ready"}`.
  - `fetch("/health")` rejects until t = 130 s, then resolves `ok`.
  - Assert that `getSidecarBaseUrl()` resolves to `http://127.0.0.1:54321` after `advanceTimersByTimeAsync(140_000)`. This fails at ace7dd76, where the old 120 s deadline throws "did not become ready in time".
- **Rust, `src-tauri/src/lib.rs` tests:**
  - (a) A budget-ordering pin in the style of `smoke_bind_budget_matches_supervisor`: `include_str!("../../src/lib/sidecar-client.ts")`, parse the deadline literal, and assert `MCP_PORT_WAIT_SECS * MAIN_SIDECAR_WAIT_ATTEMPTS + 15 < deadline_ms / 1000` and `MCP_PORT_WAIT_SECS * MAIN_SIDECAR_WAIT_ATTEMPTS >= 240`. This keeps the two clocks from drifting back into "core shorter than renderer" or "core shorter than a contended cold bind".
  - (b) Keep `the_boot_wait_keeps_an_earlier_exit_reason` (`lib.rs:1021-1041`) unchanged. It already pins that a Terminated reason survives the later `settle_boot`, which is the "genuine exit wins" half.

## 6. What a GUI verifier must see

- On a loaded machine (reproduce the drives' load: concurrent PyInstaller extractions, load ≥ 3.5), cold-launch the packaged app so the main sidecar binds after 90 s. Record its bind time from the boot timeline; it must be over 90 s for the check to count.
- During the wait the chip reads **"CONNECTING…"** past +90 s. It must never read "did not come up on port N" while the child is alive.
- After the bind the chip turns **CONNECTED** without any input, and the **seeded layout is restored**: the 7-symbol watchlist, AAPL 10 / NVDA 5 in Portfolio, and the note. Capture a populated shot.
- Read back `__autosave__` over HTTP after one layout change. Holdings and the note must still be present, which proves no default-blob overwrite.
- A negative control on the same build: `kill` the main sidecar child during the wait. The chip must show **"The data engine stopped (signal 15)."** within seconds, not after 285 s.
- Optional: one idle launch for baseline timing, and if available one Windows launch with Defender on, to put a number on the unmeasured case.
