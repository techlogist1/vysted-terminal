# v0.3.0 Teammate C — OpenBB Plugin visual verification

Per CLAUDE.md visual-verification protocol. Both 1920×1080 and 2560×1440
captures included.

## Why a custom render rather than the live UI

Teammate B's plugin manager UI was not yet merged when these screenshots
were captured (per the brief: "if B isn't merged yet at your screenshot
time, take what you can showing OpenBB endpoints responding"). The render
shows real OpenBB Platform data (AAPL price 298.21, name "Apple Inc.",
exchange NMS, real bid/ask spread) captured by hitting the standalone
subprocess directly with `httpx.get(.../quote/AAPL)` — the same payload
the plugin proxies through the main sidecar's `/openbb` router when the
launch path is healthy.

The OpenBB subprocess is a real PyInstaller `--onefile` binary at
`src-tauri/binaries/vysted-openbb-sidecar-x86_64-pc-windows-msvc.exe`
(44 MB, additive). The data shown is what `RouterLoader.from_extensions()`

- `CommandRunner.sync_run('/equity/price/quote', symbol='AAPL',
provider='yfinance')` returned during this session (the request took
  1.5 s after subprocess prewarm completed at 3.6 s).

See `BLOCKERS-C.md` (worktree root) for:

- the Tier-1 → Tier-2 bundling pivot rationale,
- the known `subprocess.Popen` → bundled-OpenBB launch issue on Windows
  (and why the registry's yfinance fallback insulates users from it),
- the lead's audit items at integration.

## Captures

- `openbb-overview-1920x1080.png` — equity panel populated with AAPL
  data, plugin contract listing the three contributed `DataSource`s, and
  the verification trail (all checks green).
- `openbb-overview-2560x1440.png` — same layout at the high-res target.
