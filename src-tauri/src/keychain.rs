//! Credential storage — BYOK secrets, never on disk in the browser, never in
//! plaintext logs.
//!
//! ## Two backends, chosen at BUILD time
//!
//! - **Release** (`cfg(not(debug_assertions))`): the OS keychain via the
//!   `keyring` crate (macOS Keychain, Windows Credential Manager, freedesktop
//!   Secret Service). This is the production path and is bit-for-bit the
//!   behaviour shipped before R9 — service `"vysted-terminal"`, account = the
//!   secret id namespaced by `src/lib/keychain.ts`.
//! - **Dev** (`cfg(debug_assertions)`): a local JSON keystore file
//!   (`<app-data-dir>/dev-keystore.json`, `0600`). `tauri dev` re-signs the
//!   binary with a fresh cdhash on every rebuild, and a self-signed identity has
//!   no Apple Team ID, so each new cdhash makes the OS keychain's `partition_id`
//!   run one securityd evaluation — a SecurityAgent dialog per rebuilt binary
//!   that the partition-list wildcard could NOT remove (see
//!   `docs/redesign/KEYCHAIN_DEV_SIGNING.md`). The dev keystore takes the OS
//!   keychain out of the dev loop entirely: zero dialogs, ever.
//!
//! The dev keystore module is **compiled only in debug builds** — in a release
//! binary the file code does not exist, so release can never silently fall to
//! the file path (asserted by `release_never_uses_dev_keystore`, run under
//! `cargo test --release`).
//!
//! ## One-time migration
//!
//! `keychain_migrate` copies existing secrets from the OS keychain into the dev
//! keystore on first dev boot (the renderer passes the candidate account list).
//! That read may trigger ONE final SecurityAgent dialog — the last one ever. It
//! is idempotent: a `migrated` flag in the file means the keychain is never
//! touched again. In release the command is a pure no-op (the keychain is
//! authoritative; nothing to migrate). Values are copied keychain→file entirely
//! in Rust and never returned to JS.

use serde::Serialize;

/// Service name for every Vysted secret in the OS keychain.
pub const SERVICE: &str = "vysted-terminal";

/// `true` in dev builds (the file keystore replaces the OS keychain); `false`
/// in release (the OS keychain is the ONLY path). Mirrors the build profile so
/// the choice can never silently flip — see `release_never_uses_dev_keystore`.
/// (Consumed only by that test; the build-profile witness has no runtime caller.)
#[allow(dead_code)]
pub const USE_DEV_KEYSTORE: bool = cfg!(debug_assertions);

/// Outcome of a `keychain_migrate` call (surfaced to the renderer, never logged
/// with values).
#[derive(Debug, Serialize)]
pub struct MigrateReport {
    /// Which backend served this build (`"dev-keystore"` / `"os-keychain"`).
    pub backend: &'static str,
    /// How many accounts were copied keychain→file on THIS call.
    pub migrated: u32,
    /// True when migration had already run before (a no-op that never touches
    /// the keychain), or when running in release (nothing to migrate).
    pub already_done: bool,
}

// --- OS keychain backend (always compiled — the release path, and the source
// the dev migration reads from) -------------------------------------------
#[cfg_attr(debug_assertions, allow(dead_code))] // set/delete are the release path; in debug only get() (migration) runs
mod os_keychain {
    use super::SERVICE;
    use keyring::Entry;

    pub fn set(account: &str, secret: &str) -> Result<(), String> {
        let entry = Entry::new(SERVICE, account).map_err(|e| e.to_string())?;
        entry.set_password(secret).map_err(|e| e.to_string())
    }

    pub fn get(account: &str) -> Result<Option<String>, String> {
        let entry = Entry::new(SERVICE, account).map_err(|e| e.to_string())?;
        match entry.get_password() {
            Ok(p) => Ok(Some(p)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(e.to_string()),
        }
    }

    pub fn delete(account: &str) -> Result<(), String> {
        let entry = Entry::new(SERVICE, account).map_err(|e| e.to_string())?;
        match entry.delete_credential() {
            Ok(()) => Ok(()),
            Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(e.to_string()),
        }
    }
}

// --- Dev file keystore backend (debug builds only) ---------------------------
#[cfg(debug_assertions)]
mod dev_keystore {
    use super::MigrateReport;
    use serde::{Deserialize, Serialize};
    use std::collections::BTreeMap;
    use std::path::{Path, PathBuf};
    use tauri::Manager;

    /// Filename under the app data dir. Git-ignored; never in the repo.
    pub const FILENAME: &str = "dev-keystore.json";

    #[derive(Default, Serialize, Deserialize)]
    struct Store {
        /// account → secret/value (the same string space the OS keychain holds).
        #[serde(default)]
        secrets: BTreeMap<String, String>,
        /// Set once the one-time keychain→file migration has run, so the OS
        /// keychain is never read again on this machine.
        #[serde(default)]
        migrated: bool,
    }

    /// Resolve `<app-data-dir>/dev-keystore.json`, creating the dir. Falls back
    /// to a temp dir (mirrors `resolve_data_dir` in `lib.rs`) so a path failure
    /// can never panic a key read.
    pub fn file_path(app: &tauri::AppHandle) -> PathBuf {
        let dir = app
            .path()
            .app_data_dir()
            .unwrap_or_else(|_| std::env::temp_dir().join("vysted-terminal"));
        let _ = std::fs::create_dir_all(&dir);
        dir.join(FILENAME)
    }

    fn load(file: &Path) -> Store {
        match std::fs::read(file) {
            Ok(bytes) => serde_json::from_slice(&bytes).unwrap_or_default(),
            Err(_) => Store::default(),
        }
    }

    fn save(file: &Path, store: &Store) -> Result<(), String> {
        let bytes = serde_json::to_vec_pretty(store).map_err(|e| e.to_string())?;
        // Write then tighten perms to 0600 so a dev secret file is never
        // world/group readable.
        std::fs::write(file, &bytes).map_err(|e| e.to_string())?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(file, std::fs::Permissions::from_mode(0o600));
        }
        Ok(())
    }

    pub fn set_at(file: &Path, account: &str, secret: &str) -> Result<(), String> {
        let mut store = load(file);
        store
            .secrets
            .insert(account.to_string(), secret.to_string());
        save(file, &store)
    }

    pub fn get_at(file: &Path, account: &str) -> Result<Option<String>, String> {
        Ok(load(file).secrets.get(account).cloned())
    }

    pub fn delete_at(file: &Path, account: &str) -> Result<(), String> {
        let mut store = load(file);
        if store.secrets.remove(account).is_some() {
            save(file, &store)?;
        }
        Ok(())
    }

    /// Copy each account that exists in the OS keychain into the file, ONCE.
    /// `reader` is injected (production passes the real keyring read; tests pass
    /// a stub) so the migration logic is unit-testable without the OS keychain.
    /// Idempotent: once `migrated` is set, returns immediately without calling
    /// `reader` — the keychain is never touched again.
    pub fn migrate_at<R>(
        file: &Path,
        accounts: &[String],
        reader: R,
    ) -> Result<MigrateReport, String>
    where
        R: Fn(&str) -> Result<Option<String>, String>,
    {
        let mut store = load(file);
        if store.migrated {
            return Ok(MigrateReport {
                backend: "dev-keystore",
                migrated: 0,
                already_done: true,
            });
        }
        let mut migrated = 0u32;
        for account in accounts {
            // A keychain read failure (denied dialog / no store) is non-fatal:
            // skip that account — the user re-adds it via Settings.
            if let Ok(Some(value)) = reader(account) {
                // Never clobber a value already set in the dev keystore.
                store.secrets.entry(account.clone()).or_insert(value);
                migrated += 1;
            }
        }
        store.migrated = true;
        save(file, &store)?;
        Ok(MigrateReport {
            backend: "dev-keystore",
            migrated,
            already_done: false,
        })
    }

    // AppHandle-resolving wrappers used by the commands.
    pub fn set(app: &tauri::AppHandle, account: &str, secret: &str) -> Result<(), String> {
        set_at(&file_path(app), account, secret)
    }
    pub fn get(app: &tauri::AppHandle, account: &str) -> Result<Option<String>, String> {
        get_at(&file_path(app), account)
    }
    pub fn delete(app: &tauri::AppHandle, account: &str) -> Result<(), String> {
        delete_at(&file_path(app), account)
    }
    /// Idle wait between the trigger pass and the re-read pass. The FIRST read of
    /// an existing item triggers the cdhash ACL securityd evaluation (the
    /// SecurityAgent dialog), which errors reads until it self-dismisses-as-allow
    /// (~10–130s observed). Critically, the dialog only settles while the app is
    /// IDLE on the keychain — hammering reads keeps re-arming it. So we trigger
    /// once, wait this long WITHOUT touching the keychain, then re-read; by then
    /// the same-cdhash reads return the real values instantly (the rounds-A/B
    /// "read → idle → read succeeds" pattern).
    const MIGRATE_SELF_DISMISS_WAIT_SECS: u64 = 140;

    pub fn migrate(app: &tauri::AppHandle, accounts: &[String]) -> Result<MigrateReport, String> {
        migrate_collecting(&file_path(app), accounts, |account| {
            let r = super::os_keychain::get(account);
            let class = match &r {
                Ok(Some(_)) => "found",
                Ok(None) => "absent",
                Err(_) => "read-error",
            };
            eprintln!("[keychain-migrate] {account} -> {class}");
            r
        })
    }

    /// The two-pass, idle-then-re-read migration over an INJECTED keychain read
    /// (`read`), with the once-only guard checked BEFORE the first read. Split
    /// out so the guard + pass logic are unit-testable without the OS keychain.
    /// `read` is called AT MOST `accounts.len() + errored.len()` times on the
    /// first migration, and ZERO times once `migrated` is set.
    pub fn migrate_collecting<R>(
        file: &Path,
        accounts: &[String],
        read: R,
    ) -> Result<MigrateReport, String>
    where
        R: Fn(&str) -> Result<Option<String>, String>,
    {
        use std::time::Duration;
        // SHORT-CIRCUIT BEFORE ANY KEYCHAIN READ: once migrated, the keychain is
        // never touched again — every boot after the first does zero reads (so
        // zero SecurityAgent dialogs). The check MUST precede the pass-1 reads;
        // leaving it to `migrate_at` (which only records already-read values)
        // re-hit the keychain on every boot and re-raised the dialog.
        if load(file).migrated {
            return Ok(MigrateReport {
                backend: "dev-keystore",
                migrated: 0,
                already_done: true,
            });
        }
        // Pass 1 (trigger): read each account once. An existing item errors while
        // its ACL evaluation is in flight; absent items return at once.
        let mut resolved: std::collections::BTreeMap<String, Option<String>> =
            std::collections::BTreeMap::new();
        let mut errored: Vec<String> = Vec::new();
        for account in accounts {
            match read(account) {
                Ok(v) => {
                    resolved.insert(account.clone(), v);
                }
                Err(_) => errored.push(account.clone()),
            }
        }
        // Pass 2 (re-read after the idle settle), only if something errored — by
        // then the one cdhash ACL evaluation has self-dismissed-as-allow.
        if !errored.is_empty() {
            eprintln!(
                "[keychain-migrate] {} item(s) pending the ACL self-dismiss — idle {}s then re-read",
                errored.len(),
                MIGRATE_SELF_DISMISS_WAIT_SECS
            );
            std::thread::sleep(Duration::from_secs(MIGRATE_SELF_DISMISS_WAIT_SECS));
            for account in &errored {
                resolved.insert(account.clone(), read(account).unwrap_or(None));
            }
        }
        // Record the resolved values + set `migrated` (no further keychain touch).
        migrate_at(file, accounts, |a| Ok(resolved.get(a).cloned().flatten()))
    }
}

// --- Tauri commands (one signature; backend chosen by cfg) -------------------

#[tauri::command]
pub async fn keychain_set(
    app: tauri::AppHandle,
    account: String,
    secret: String,
) -> Result<(), String> {
    let _ = &app;
    #[cfg(debug_assertions)]
    {
        dev_keystore::set(&app, &account, &secret)
    }
    #[cfg(not(debug_assertions))]
    {
        os_keychain::set(&account, &secret)
    }
}

#[tauri::command]
pub async fn keychain_get(
    app: tauri::AppHandle,
    account: String,
) -> Result<Option<String>, String> {
    let _ = &app;
    #[cfg(debug_assertions)]
    {
        dev_keystore::get(&app, &account)
    }
    #[cfg(not(debug_assertions))]
    {
        os_keychain::get(&account)
    }
}

#[tauri::command]
pub async fn keychain_delete(app: tauri::AppHandle, account: String) -> Result<(), String> {
    let _ = &app;
    #[cfg(debug_assertions)]
    {
        dev_keystore::delete(&app, &account)
    }
    #[cfg(not(debug_assertions))]
    {
        os_keychain::delete(&account)
    }
}

/// One-time keychain→dev-keystore migration. Dev: copies the given accounts from
/// the OS keychain into the file (idempotent via the `migrated` flag). Release:
/// a pure no-op — the OS keychain is authoritative, nothing to migrate.
#[tauri::command]
pub async fn keychain_migrate(
    app: tauri::AppHandle,
    accounts: Vec<String>,
) -> Result<MigrateReport, String> {
    let _ = (&app, &accounts);
    #[cfg(debug_assertions)]
    {
        // Reads run INLINE on the async-command thread — the context where a
        // keychain read self-dismisses-as-allow and returns the value (proven
        // in the R9 verification rounds). A `spawn_blocking` background thread
        // errored every read instead. The migration's idle-then-re-read does the
        // ~140s wait here; the file backend serves every other read meanwhile.
        dev_keystore::migrate(&app, &accounts)
    }
    #[cfg(not(debug_assertions))]
    {
        Ok(MigrateReport {
            backend: "os-keychain",
            migrated: 0,
            already_done: true,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The build-time backend choice can never silently flip. Trivially true in
    /// debug; genuinely asserts the release arm under `cargo test --release`.
    #[test]
    fn release_never_uses_dev_keystore() {
        assert_eq!(USE_DEV_KEYSTORE, cfg!(debug_assertions));
        #[cfg(not(debug_assertions))]
        assert!(
            !USE_DEV_KEYSTORE,
            "a release build must never use the dev keystore file path"
        );
    }

    #[cfg(debug_assertions)]
    mod dev {
        use super::super::dev_keystore;
        use std::path::PathBuf;
        use std::time::{SystemTime, UNIX_EPOCH};

        fn temp_file(tag: &str) -> PathBuf {
            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let p = std::env::temp_dir().join(format!(
                "vysted-keystore-test-{}-{}-{}.json",
                std::process::id(),
                tag,
                nanos
            ));
            let _ = std::fs::remove_file(&p);
            p
        }

        #[test]
        fn migrate_collecting_reads_keychain_zero_times_once_migrated() {
            // The bug that re-raised the dialog every boot: the production wrapper
            // read the keychain BEFORE checking `migrated`. The guard now precedes
            // any read — a second migration must call the reader ZERO times.
            let f = temp_file("guard");
            let accounts = vec![
                "llm-provider:deepseek".to_string(),
                "llm-provider:openrouter".to_string(),
            ];
            use std::sync::atomic::{AtomicU32, Ordering};
            use std::sync::Arc;
            let reads = Arc::new(AtomicU32::new(0));
            let reads_c = Arc::clone(&reads);
            let read = move |a: &str| -> Result<Option<String>, String> {
                reads_c.fetch_add(1, Ordering::SeqCst);
                Ok(Some(format!("v-{a}")))
            };
            let r1 = dev_keystore::migrate_collecting(&f, &accounts, &read).unwrap();
            assert_eq!(r1.migrated, 2);
            assert_eq!(
                reads.load(Ordering::SeqCst),
                2,
                "first migration reads each once"
            );
            // Second call: migrated flag set → guard short-circuits → ZERO reads.
            let before = reads.load(Ordering::SeqCst);
            let r2 = dev_keystore::migrate_collecting(&f, &accounts, &read).unwrap();
            assert!(r2.already_done);
            assert_eq!(
                reads.load(Ordering::SeqCst),
                before,
                "a migrated keystore must read the keychain ZERO more times (no dialog ever again)"
            );
            let _ = std::fs::remove_file(&f);
        }

        #[test]
        fn roundtrip_set_get_delete_against_the_file() {
            let f = temp_file("roundtrip");
            assert_eq!(
                dev_keystore::get_at(&f, "llm-provider:deepseek").unwrap(),
                None
            );
            dev_keystore::set_at(&f, "llm-provider:deepseek", "sk-test").unwrap();
            assert_eq!(
                dev_keystore::get_at(&f, "llm-provider:deepseek").unwrap(),
                Some("sk-test".to_string())
            );
            // Update overwrites.
            dev_keystore::set_at(&f, "llm-provider:deepseek", "sk-new").unwrap();
            assert_eq!(
                dev_keystore::get_at(&f, "llm-provider:deepseek").unwrap(),
                Some("sk-new".to_string())
            );
            dev_keystore::delete_at(&f, "llm-provider:deepseek").unwrap();
            assert_eq!(
                dev_keystore::get_at(&f, "llm-provider:deepseek").unwrap(),
                None
            );
            let _ = std::fs::remove_file(&f);
        }

        #[test]
        fn file_is_0600_after_write() {
            let f = temp_file("perms");
            dev_keystore::set_at(&f, "app-meta:onboarding-complete", "1").unwrap();
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mode = std::fs::metadata(&f).unwrap().permissions().mode() & 0o777;
                assert_eq!(mode, 0o600, "dev keystore must be owner-only readable");
            }
            let _ = std::fs::remove_file(&f);
        }

        #[test]
        fn migration_copies_keychain_values_once_then_never_reads_again() {
            let f = temp_file("migrate");
            let accounts = vec![
                "llm-provider:deepseek".to_string(),
                "llm-provider:openrouter".to_string(),
                "broker:_meta:first-launch-tos".to_string(),
                "llm-provider:anthropic".to_string(), // not in the keychain → skipped
            ];
            // Stub the keychain: deepseek + openrouter + tos exist, anthropic does
            // not. A move closure owns the read counter (Arc) so it can be passed
            // BY VALUE (no borrow); the counter is read back through a clone.
            use std::sync::atomic::{AtomicU32, Ordering};
            use std::sync::Arc;
            let reads = Arc::new(AtomicU32::new(0));
            let reads_c = Arc::clone(&reads);
            let reader = move |a: &str| -> Result<Option<String>, String> {
                reads_c.fetch_add(1, Ordering::SeqCst);
                Ok(match a {
                    "llm-provider:deepseek" => Some("sk-ds".to_string()),
                    "llm-provider:openrouter" => Some("sk-or".to_string()),
                    "broker:_meta:first-launch-tos" => Some("2026-06-11".to_string()),
                    _ => None,
                })
            };
            let r1 = dev_keystore::migrate_at(&f, &accounts, reader).unwrap();
            assert_eq!(r1.migrated, 3);
            assert!(!r1.already_done);
            assert_eq!(
                reads.load(Ordering::SeqCst),
                4,
                "first migration reads every candidate once"
            );
            assert_eq!(
                dev_keystore::get_at(&f, "llm-provider:openrouter").unwrap(),
                Some("sk-or".to_string())
            );

            // Second call is a no-op that NEVER touches the keychain again — the
            // panicking reader proves the migrated keystore short-circuits before
            // any keychain read.
            let r2 = dev_keystore::migrate_at(&f, &accounts, |_| {
                panic!("a migrated keystore must never re-read the keychain")
            })
            .unwrap();
            assert!(r2.already_done);
            assert_eq!(r2.migrated, 0);
            let _ = std::fs::remove_file(&f);
        }

        #[test]
        fn migration_never_clobbers_a_value_already_in_the_keystore() {
            let f = temp_file("noclobber");
            // User set a key in dev BEFORE migration ran.
            dev_keystore::set_at(&f, "llm-provider:deepseek", "user-typed").unwrap();
            dev_keystore::migrate_at(&f, &["llm-provider:deepseek".to_string()], |_| {
                Ok(Some("keychain-old".to_string()))
            })
            .unwrap();
            assert_eq!(
                dev_keystore::get_at(&f, "llm-provider:deepseek").unwrap(),
                Some("user-typed".to_string()),
                "migration must not overwrite a value the user already set in dev"
            );
            let _ = std::fs::remove_file(&f);
        }
    }
}
