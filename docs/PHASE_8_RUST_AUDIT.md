# Phase 8 — Rust Audit (T3-rust)

**Date:** 2026-05-18  
**Baseline commit:** 947d297 (docs(phase-8/L6): performance baseline)  
**Auditor:** Sonnet 4.6 teammate t3-rust  
**Branch:** worktree-agent-t3-rust  
**Host triple:** x86_64-pc-windows-msvc  
**Rust toolchain:** rustc 1.94.1 (e408947bf 2026-03-25) / cargo 1.94.1  
**cargo-audit:** 0.22.1  

## Severity scheme

- **S1** — unsafe-block bug, UB risk, runtime breakage, security-critical CVE in reachable code path
- **S2** — real bug surface, MEDIUM CVE, unused dep, formatter drift across multiple files
- **S3** — clippy::pedantic / clippy::nursery noise, low-impact advisory, dead code inside live module
- **S4** — cosmetic

---

## Angle 1 — `cargo audit` (RustSec)

> Command: `cargo audit` (advisory DB 1090 entries, Cargo.lock 575 crates)

### Finding T3-gtk3-unmaintained: GTK3 bindings cluster unmaintained [S3] [status: open]

**Tool:** cargo audit  
**Detection:** RUSTSEC-2024-0411 through RUSTSEC-2024-0420 (10 advisories) — `atk`, `atk-sys`, `gdk`, `gdk-sys`, `gdkwayland-sys`, `gdkx11`, `gdkx11-sys`, `gtk`, `gtk-sys`, `gtk3-macros` all flagged unmaintained (date 2024-03-04). All route through `wry 0.55.1 → tauri-runtime-wry 2.11.1 → tauri 2.11.1`.  
**Impact:** Linux-only compile path (GTK3 is the Linux webview backend for wry/tao). No impact on Windows or macOS production builds. GTK4 migration is a wry/Tauri upstream concern; Vysted cannot independently upgrade these. All are `Warning: unmaintained`, not `Vulnerability`.  
**Suggested fix path:** Track tauri/wry upstream for GTK4 migration. No direct action possible; suppress in `audit.toml` with a rationale comment once Tauri 2.x officially moves to GTK4.  
**Files:** `src-tauri/Cargo.lock` — `wry 0.55.1`, `tao 0.35.2`

---

### Finding T3-glib-unsound: `glib` VariantStrIter unsoundness [S2] [status: open]

**Tool:** cargo audit  
**Detection:** RUSTSEC-2024-0429 — `glib 0.18.5` "Unsoundness in `Iterator` and `DoubleEndedIterator` impls for `glib::VariantStrIter`". Date 2024-03-30. Reaches Vysted via `wry 0.55.1 → gtk → glib`.  
**Impact:** Linux-only (GTK path). `glib::VariantStrIter` is not used in Vysted Rust source directly — it is a transitive dependency of wry's Linux backend. The unsoundness is only reachable if Vysted's Rust code creates a `glib::VariantStrIter`; static analysis shows no Vysted source does this. Real UB risk is in the gtk3-rs internals on Linux. Advisory is rated `Warning: unsound`.  
**Suggested fix path:** Track `glib` upgrade in wry upstream (glib 0.19+ has the fix). No direct action. Add to `audit.toml` ignore list with rationale.  
**Files:** `src-tauri/Cargo.lock` — `glib 0.18.5`

---

### Finding T3-rand-unsound: `rand 0.8.5` unsoundness [S2] [status: open]

**Tool:** cargo audit  
**Detection:** RUSTSEC-2026-0097 — `rand 0.8.5` "Rand is unsound with a custom logger using `rand::rng()`". Date 2026-04-09. Reaches Vysted via `keyring 3.6.3 → secret-service 4.0.0 → zbus 4.4.0 → rand 0.8.5`.  
**Impact:** Linux-only path (`secret-service` is the Linux freedesktop credential-store backend for `keyring`). The unsoundness triggers only if a `log` crate subscriber calls `rand::rng()` — an extremely narrow condition. Vysted does not define a custom logger that would trigger this. No direct production risk on Windows/macOS. `rand 0.9.x` is the fix.  
**Suggested fix path:** Track `keyring → zbus → rand` upgrade chain. `rand 0.9.4` is already in the lock file (used by `tauri-plugin-notification`); the blocker is `zbus 4.4.0` pinning `rand 0.8.5`. Add to `audit.toml` ignore list pending upstream resolution.  
**Files:** `src-tauri/Cargo.lock` — `rand 0.8.5` (via `secret-service 4.0.0 → zbus 4.4.0`)

---

### Finding T3-unic-unmaintained: `unic-*` crate cluster unmaintained [S3] [status: open]

**Tool:** cargo audit  
**Detection:** RUSTSEC-2025-0075, -0080, -0081, -0098, -0100 — `unic-char-range`, `unic-common`, `unic-char-property`, `unic-ucd-version`, `unic-ucd-ident` all flagged unmaintained (date 2025-10-18). Route through `tauri-utils 2.9.1 → urlpattern 0.3.0`.  
**Impact:** Build/proc-macro dependency of `tauri-utils`. No runtime exposure; these are Unicode data tables consumed at build time inside urlpattern. Tauri upstream must upgrade `urlpattern`.  
**Suggested fix path:** Track Tauri upstream. No direct action.  
**Files:** `src-tauri/Cargo.lock` — `tauri-utils 2.9.1`

---

### Finding T3-proc-macro-error-unmaintained: `proc-macro-error 1.0.4` unmaintained [S3] [status: open]

**Tool:** cargo audit  
**Detection:** RUSTSEC-2024-0370 — `proc-macro-error 1.0.4` flagged unmaintained (date 2024-09-01). Reaches Vysted via `gtk3-macros 0.18.2 → glib-macros 0.18.5`.  
**Impact:** Linux-only compile path. Proc-macro crate; zero runtime exposure.  
**Suggested fix path:** Track glib upstream upgrade. No direct action.  
**Files:** `src-tauri/Cargo.lock` — `proc-macro-error 1.0.4`

---

**Angle 1 summary:** 0 vulnerabilities, 18 warnings. No CVEs in the `tauri`, `tauri-plugin-*`, `keyring`, `serde`, or `tokio` primary dependencies. All findings are transitive, Linux-only, or warning-level. The `glib` unsoundness (S2) and `rand` unsoundness (S2) are the highest-priority advisories but both require Linux execution paths not exercised on Windows.

---

## Angle 2 — `cargo clippy` strict

> Standard CI command: `cargo clippy --all-targets -- -D warnings` — **passed cleanly** (exit 0)  
> Extended command: `cargo clippy --all-targets --all-features -- -W clippy::all -W clippy::pedantic -W clippy::nursery`

**CI gate verdict:** Standard clippy passes. Extended pass surfaced 19 lib warnings across `clippy::pedantic` and `clippy::nursery`. No `clippy::correctness` (S1) or `clippy::suspicious` (S2) warnings found.

### Finding T3-significant-drop-scrutinee: MutexGuard held across `if let` scrutinee — potential deadlock [S2] [status: open]

**Tool:** cargo clippy — `clippy::significant_drop_in_scrutinee` (nursery)  
**Detection:**
```
src/openbb_mcp.rs:128   if let Some(child) = state.0.lock().unwrap().take()
src/sec_edgar_mcp.rs:126 if let Some(child) = state.0.lock().unwrap().take()
src/lib.rs:140          if let Some(child) = state.0.lock().unwrap().take()
```
"this might lead to deadlocks or other unexpected behavior — temporary lives until end of `if let` expression"  
**Impact:** The `MutexGuard` returned by `.lock().unwrap()` has a `Drop` impl that releases the lock. Clippy's nursery lint flags that the guard's drop is deferred to the end of the `if let` expression rather than immediately after `.take()`. In practice — since `child.kill()` does not attempt to re-acquire the same lock — this is not a live deadlock. However if a future code change inside the block calls any path that tries to re-lock the same mutex (e.g. a Tauri event handler that queries state), it will deadlock silently. It is also a correctness smell clippy::nursery flags as "unexpected behavior". Affects all three shutdown kill paths.  
**Suggested fix path:** Extract to a local binding before the `if let`:
```rust
let value = state.0.lock().unwrap().take();
if let Some(child) = value { let _ = child.kill(); }
```  
**Files:** `src-tauri/src/openbb_mcp.rs:128`, `src-tauri/src/sec_edgar_mcp.rs:126`, `src-tauri/src/lib.rs:140`

---

### Finding T3-needless-pass-by-value: Tauri command state args passed by value [S3] [status: open]

**Tool:** cargo clippy — `clippy::needless_pass_by_value` (pedantic)  
**Detection:**
```
src/lib.rs:46         fn get_sidecar_port(port: tauri::State<'_, SidecarPort>) -> u16
src/openbb_mcp.rs:49  pub fn get_openbb_mcp_port(port: tauri::State<'_, OpenbbMcpPort>) -> u16
src/sec_edgar_mcp.rs:48 pub fn get_sec_edgar_mcp_port(port: tauri::State<'_, SecEdgarMcpPort>) -> u16
```
Clippy recommends `&tauri::State<'_, ...>` for all three. `kill_switch.rs:90` — `app: AppHandle` and `fired_by: String` both recommended as refs/str slices.  
**Impact:** Minor: `tauri::State` is a reference-counted wrapper; passing by value is slightly less efficient but works correctly. The `AppHandle` by-value case in `kill_switch_emit` is harmless since Tauri clones it cheaply. S3 pedantic noise.  
**Suggested fix path:** Change the three port-getter handlers to `&tauri::State<'_, ...>` and `kill_switch_emit` to `&AppHandle` + `fired_by: &str`. Requires verifying Tauri macro compatibility with reference-type State args (Tauri 2.x docs confirm `&State<'_, T>` is supported).  
**Files:** `src-tauri/src/lib.rs:46`, `src-tauri/src/openbb_mcp.rs:49`, `src-tauri/src/sec_edgar_mcp.rs:48`, `src-tauri/src/kill_switch.rs:90`

---

### Finding T3-unnecessary-wraps: `spawn()` return type unnecessary [S3] [status: open]

**Tool:** cargo clippy — `clippy::unnecessary_wraps` (pedantic)  
**Detection:** `openbb_mcp.rs:59` and `sec_edgar_mcp.rs:59` — both `spawn` functions return `tauri::Result<()>` but the only early returns are `Ok(())` and the terminal path also returns implicitly `()`. Clippy notes the `Result` wrapper adds no information since the functions never return an `Err` variant.  
**Impact:** The `spawn` signature is called from `lib.rs` via `openbb_mcp::spawn(app.handle())?` — the `?` operator propagates a hypothetical error to the `setup` closure. Removing the `Result` wrapper would require removing the `?` at call-site and changing the function signatures, which is a meaningful refactor. S3 polish.  
**Suggested fix path:** Suppress with `#[allow(clippy::unnecessary_wraps)]` on both `spawn` fns if the `Result` return is intentionally kept for future fallibility (e.g. if the binary presence check is moved to return `Err`). Otherwise remove the `Result` wrapper and the `?` at call-sites.  
**Files:** `src-tauri/src/openbb_mcp.rs:59`, `src-tauri/src/sec_edgar_mcp.rs:59`

---

### Finding T3-semicolon-pedantic: Missing semicolons in `build.rs` and `main.rs` [S4] [status: open]

**Tool:** cargo clippy — `clippy::semicolon_if_nothing_returned` (pedantic)  
**Detection:** `build.rs:2` (`tauri_build::build()`) and `main.rs:4` (`vysted_terminal_lib::run()`) both missing trailing `;`.  
**Impact:** Cosmetic. Standard Rust style omits `;` for void tail expressions; the pedantic lint disagrees. No runtime impact.  
**Suggested fix path:** Add `;` to both lines.  
**Files:** `src-tauri/build.rs:2`, `src-tauri/src/main.rs:4`

---

### Finding T3-match-same-arms: Redundant match arms in `keychain_delete` [S3] [status: open]

**Tool:** cargo clippy — `clippy::match_same_arms` (pedantic)  
**Detection:** `keychain.rs:38-39`:
```rust
Ok(()) => Ok(()),
Err(keyring::Error::NoEntry) => Ok(()),
```
Both arms return `Ok(())`. Clippy suggests merging to `Ok(()) | Err(keyring::Error::NoEntry) => Ok(())`.  
**Impact:** Zero runtime impact. The separation is arguably more readable (documents the intent: "missing key is not an error"). S3 style.  
**Suggested fix path:** Merge the arms or suppress with `#[allow(clippy::match_same_arms)]`.  
**Files:** `src-tauri/src/keychain.rs:38-39`

---

### Finding T3-doc-markdown: Module-doc backtick style in `openbb_mcp.rs` [S4] [status: open]

**Tool:** cargo clippy — `clippy::doc_markdown` (pedantic)  
**Detection:** 5 instances in `openbb_mcp.rs` and 1 in `sec_edgar_mcp.rs` — words like `OpenBB`, `FastAPI`, `PyInstaller` in `//!` doc comments not wrapped in backticks.  
**Impact:** Cosmetic documentation formatting. No runtime impact.  
**Suggested fix path:** Wrap the identified words in backticks or suppress with `#[allow(clippy::doc_markdown)]` at module level.  
**Files:** `src-tauri/src/openbb_mcp.rs:3,5,9,24`, `src-tauri/src/sec_edgar_mcp.rs:4`

---

### Finding T3-equatable-if-let: `if let RunEvent::Exit = event` pattern [S4] [status: open]

**Tool:** cargo clippy — `clippy::equatable_if_let` (nursery)  
**Detection:** `lib.rs:138` — `if let RunEvent::Exit = event` should be `if matches!(event, RunEvent::Exit)` per clippy nursery.  
**Impact:** Cosmetic style difference. `if let` with a unit variant is idiomatic Rust; `matches!` is preferred by the nursery lint. No correctness impact.  
**Suggested fix path:** Rewrite as `if matches!(event, RunEvent::Exit)` or suppress.  
**Files:** `src-tauri/src/lib.rs:138`

---

### Finding T3-missing-panics-doc: `pub fn run()` missing `# Panics` section [S3] [status: open]

**Tool:** cargo clippy — `clippy::missing_panics_doc` (pedantic)  
**Detection:** `lib.rs:51` — `pub fn run()` contains multiple `.expect(...)` calls but has no `# Panics` rustdoc section.  
**Impact:** Documentation completeness. S3 pedantic. The function does genuinely panic on critical setup failures (failed sidecar spawn, failed port allocation) — these are intentional hard failures. Documenting them is a reasonable ask.  
**Suggested fix path:** Add `/// # Panics\n/// Panics if the application data directory cannot be resolved, the sidecar cannot be spawned, or Tauri initialization fails.` to `run()`.  
**Files:** `src-tauri/src/lib.rs:51`

---

**Angle 2 summary:** Standard clippy (`-D warnings`) — **clean**. Extended clippy — 19 lib warnings, 2 binary warnings. One S2 finding (significant-drop-in-scrutinee deadlock risk in 3 locations). Zero S1 findings. Remaining are S3/S4 pedantic/cosmetic.

---

## Angle 3 — `cargo udeps`

*(Results populated below — requires nightly)*

---

## Angle 4 — `cargo fmt --check`

> Command: `cargo fmt --check` (run from `src-tauri/`)  
> Result: **No output — format is clean.**

**No findings.** The formatter check passes cleanly on all five source files (`lib.rs`, `keychain.rs`, `kill_switch.rs`, `openbb_mcp.rs`, `sec_edgar_mcp.rs`). The CI gate is holding.

---

## Angle 5 — Dead-code (nightly rustc)

*(Results populated below — requires nightly)*

---

## Special attention modules

*(Populated below after code review)*

---

## Summary

*(Populated in final commit)*
