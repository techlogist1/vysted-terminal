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

> Command: `cargo clippy --all-targets -- -D warnings`  
> Extended: `cargo clippy --all-targets --all-features -- -D warnings -W clippy::all -W clippy::pedantic -W clippy::nursery`

*(Results populated below after build completes)*

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
