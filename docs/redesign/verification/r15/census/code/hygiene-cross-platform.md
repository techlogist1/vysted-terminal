# hygiene-cross-platform: static cross-platform sweep (R15 Stage B item 2, session 2)

Model: claude-opus-5-5[1m]. Scope follows the HYGIENE SWEEP section of PROMPT_code_s2.md: a static read of
`src-tauri/src/`, `sidecar/`, `scripts/` and `src/`, with no live Windows or Linux run. The APOSD skill
is not used and there is no principle-grade table. This item has no entry in CODE_PARTITION.json. The raw
findings are in `census/raw/hygiene-cross-platform.json` (HYG-1..12).

## Narrative

Most of the code handles cross-platform concerns well. The historical Windows traps have all been dealt with:
- Subprocesses are spawned through Tauri, not `Popen`.
- A stdin-EOF watchdog reaps the PyInstaller worker.
- `--add-data` uses the right separator per OS and is quoted for cmd.exe.
- `copyWithRetry` handles Defender locks.
- The smoke test tree-kills with `taskkill /T` on Windows and uses a POSIX process group elsewhere.
- Every production `open()`/`read_text()` passes `encoding="utf-8"`.
- `get_data_dir` is driven by `--data-dir`.
- Nothing under `~/Library` is hardcoded outside a dev docstring.
- `tzdata` reaches the Windows bundle through pyinstaller-hooks-contrib's `hook-zoneinfo`.
- uvicorn 0.46 picks the Proactor loop on Windows, so `asyncio.create_subprocess_exec` (searxng/docker) works.
- The dev-sign runner and `codesign` are scoped to Darwin targets.
- The key-binding store is platform-aware.

The real risk is **process, not code**. The 3-OS CI matrix exists, but it has not run since
2026-05-30 (HYG-1). This branch is 655 commits ahead of `main` and has no PR, so no Windows or Linux job has
ever built it. One Windows failure is already proven to be waiting (HYG-2: a pytest fixture that cp1252 cannot
decode).

The two product-level gaps are:
- Windows device detection returns a hardcoded 8 GiB profile. The local-model recommendation is scored against it and presented as measured (HYG-3).
- The deterministic layout modes exist only in the macOS native menu (HYG-4).

The rest are low-severity rough edges. Most of them are one-line or few-line fixes (`cheap_fix: true`).

The kill-switch shortcut (HYG-5) is a wrong-chord bug on every OS: it requires Ctrl+Super+Shift+K. It is graded
low because the switch currently gates only broker adapters, which the trading removal deletes. Fix or delete it
together with that removal.

Checked and cleared (not findings): `write_*_atomic` path joins (Windows accepts mixed separators); the Rust test's
`/tmp` literal (the parent comparison still holds on Windows); `beforeDevCommand` `&&` (Tauri runs it through
`cmd /C`); docker `-v C:\...:/etc/searxng` (passed as a list argument, no quoting); `hardware_fit` `sysctl`
(Darwin-only branch); keyring backend features (all three present); the smoke test's ownership probe (PowerShell
on Windows, not the removed `wmic`).

## Findings

| id | sev | where | trap | consequence | cheap |
|---|---|---|---|---|---|
| HYG-1 | medium | .github/workflows/test.yml:3-6 (+build, lint) | 3-OS CI triggers only on push:main / PR; branch has no PR | 655 commits never built or tested on Windows/Linux; last run 2026-05-30 | yes |
| HYG-2 | medium | sidecar/tests/test_search_extract.py:464 | `read_text()` with no encoding on a UTF-8 fixture | Windows pytest raises `UnicodeDecodeError` (byte 0x9d), so the CI gate goes red | yes |
| HYG-3 | medium | sidecar/services/hardware_fit.py:182-197, 208-215 | no Windows detector; the fallback hardcodes 8 GiB | onboarding recommends models from a fixed fiction on every Windows box | no |
| HYG-4 | medium | src-tauri/src/lib.rs:349, 497; src/lib/menu-bridge.ts:33 | layout modes exist only as `cfg(macos)` menu items | Windows/Linux can't switch Fundamental/Technical/Macro/Compare deterministically | no |
| HYG-5 | low | src-tauri/src/kill_switch.rs:34-39 | `SUPER \| CONTROL \| SHIFT` registered together | the documented Cmd/Ctrl+Shift+K never fires on any OS (Ctrl+Win+Shift+K on Windows) | yes |
| HYG-6 | low | src/modules/notes/notes-persistence.ts:67 | sanitiser strips only `/` and `\` | on Windows, `NSE:RELIANCE` or `CON` notes silently never get their .md | yes |
| HYG-7 | low | sidecar/services/workspace_store.py:88; src-tauri/src/lib.rs:309, 341 | `os.replace`/`rename` with no sharing-violation retry | intermittent autosave 500s on Windows (AV/indexer); the Rust version leaks the tmp file | yes |
| HYG-8 | low | src-tauri/src/openbb_mcp.rs:95; sec_edgar_mcp.rs:95; lib.rs:472-485 | `set_var` from parallel threads | POSIX getenv/setenv data race; rare boot crash on Linux | yes |
| HYG-9 | low | src/app/page.tsx:233, 251; ProposedChangesReview.tsx:51, 59 | hardcoded ⌘ glyphs | Windows users are told to press keys that don't exist on their keyboard (Win+K opens Cast) | yes |
| HYG-10 | low | scripts/ensure-sidecar.mjs:98 (+2 MCP scripts) | ambient `python`/`python3`, no version check | on Windows the Store stub breaks the build; elsewhere it may build on 3.11/3.12 instead of 3.13 | yes |
| HYG-11 | low | src-tauri/src/keychain.rs:62-89, 224; src/store/onboarding.ts:38-54 | no fallback when Linux has no Secret Service | keys can't be saved, onboarding repeats every launch, dev build waits 140 s | no |
| HYG-12 | low | src-tauri/src/lib.rs:116-134 | `app_data_dir` is Roaming on Windows | regenerable SQLite caches get synced by roaming profiles | no |

## Priority

1. **HYG-1 + HYG-2 before the ROG session.** Open a draft PR (or add `workflow_dispatch`) and set
   `PYTHONUTF8=1` or explicit encodings in the tests. That gives the Windows session a real CI baseline instead of a
   manual hunt.
2. **HYG-3.** Add a `ctypes` `GlobalMemoryStatusEx` detector and an `estimated` flag. Windows is the operator's
   primary rig, so this is the first number a Windows user sees in onboarding.
3. **HYG-4.** Add command-palette entries for the layout modes (platform-neutral) and keep the macOS menu as sugar.
4. The cheap batch (HYG-5..10) fits in one small PR. Decide HYG-5 together with the trading removal.
5. HYG-11 and HYG-12 are storage-location decisions that are cheap now and turn into migrations later.
