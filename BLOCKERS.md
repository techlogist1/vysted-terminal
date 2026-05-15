# Blockers & Known Issues

Lead-level open items as of v0.3.0. Per-teammate Phase-2 self-reports
(`BLOCKERS-A.md`, `-B.md`, `-C.md`) were aggregated here at integration and
removed; the salient detail is preserved in the v0.3.0 merge commit messages
and in this file. None of the items below blocks the v0.3.0 ship; each is a
deliberate Phase-3 follow-up.

## OpenBB subprocess hangs under `subprocess.Popen` on Windows (Phase-3 follow-up)

**Symptom.** When the main Vysted sidecar lazy-launches the OpenBB
subprocess via `subprocess.Popen(...)`, the subprocess never finishes its
prewarm (`/health` returns 503 indefinitely). The 30-second deadline fires,
the main sidecar terminates the subprocess, and the registry's yfinance
fallback runs. Users still get fundamentals / macro data via that fallback,
so the user-facing data path is intact — the OpenBB subprocess is a dormant
performance optimization that lights up only when this launch path is fixed.

**What works.** The same binary, same flags, same environment, launched
via PowerShell `Start-Process` (or any non-Python parent) reaches HTTP/200 in
~3-4 s. Direct standalone `/quote/AAPL` returns the populated payload in
1.5 s. The bundle itself is correct.

**Investigation done (Teammate C).** Tested every plausible `stdin` /
`creationflags` / `close_fds` combination. Rewrote the subprocess's
stdin-EOF watchdog from `sys.stdin.buffer.read()` to `os.read(fd, ...)`
to rule out the high-level lock. None changed the deadlock.

**Root cause hypothesis.** OpenBB-core uses
`anyio.from_thread.BlockingPortal` to bridge sync/async, which spins an
event loop on a worker thread. PyInstaller `--onefile` extracts to
`_MEIPASS`, which involves additional thread/lock interactions on Windows.
Combined with `subprocess.Popen`'s default Windows handle-inheritance
behavior (different from `Start-Process`'s `CreateProcess` flags), the
prewarm thread deadlocks. This is a Python+PyInstaller+anyio interaction,
not a Vysted bug per se.

**Phase-3 fix candidates.**

1. Spawn the OpenBB subprocess as a sibling to the main sidecar via the
   same `tauri-plugin-shell` mechanism that already supervises the main
   sidecar. That uses Rust's `Command::new(...)` instead of Python's
   `subprocess.Popen`, with different Windows handle semantics.
2. Wrap the OpenBB subprocess launch in a small Rust helper invoked
   through `tauri-plugin-shell` — same idea, narrower surface.

Either approach moves the OpenBB-subprocess lifecycle out of the Python
sidecar entirely, which is a clean separation regardless.

## Drawing-tool on-canvas screenshots not captured via chrome-devtools (cosmetic)

lightweight-charts rejects synthesised mouse events (`isTrusted` check),
so the chrome-devtools MCP `click` action cannot exercise the
click-to-create gesture for drawings. The drawings have full unit-test
canvas-call coverage, and the toolbar UI + drawing-inspector populated
screenshots prove the wiring. A `pnpm tauri dev` end-user session
demonstrates them live.

This is a verification-coverage gap, not a functional bug. Leaving it
documented rather than working around it; the Phase-3 chart visual
regression suite (if added) should use Playwright's real-event mode or
similar.
