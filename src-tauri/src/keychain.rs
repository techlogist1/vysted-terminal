//! OS keychain integration — BYOK credentials live here, never on disk or in
//! browser storage. Backed by the `keyring` crate, which routes to macOS
//! Keychain, Windows Credential Manager, and the freedesktop Secret Service on
//! Linux. Every Vysted secret is stored under the service name `"vysted-
//! terminal"`; the account string is the secret id (e.g. `"llm-provider:
//! anthropic"`, `"mcp-server:openbb"`) namespaced by the frontend wrapper in
//! `src/lib/keychain.ts`.
//!
//! Errors from `keyring::Error` are flattened to `String` so the frontend gets
//! a simple Result<T, string>. A missing entry is NOT an error — `get` returns
//! `Ok(None)` and `delete` returns `Ok(())`, so the frontend can treat
//! "secret never set" the same way every time.

use keyring::Entry;

const SERVICE: &str = "vysted-terminal";

#[tauri::command]
pub async fn keychain_set(account: String, secret: String) -> Result<(), String> {
    let entry = Entry::new(SERVICE, &account).map_err(|e| e.to_string())?;
    entry.set_password(&secret).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn keychain_get(account: String) -> Result<Option<String>, String> {
    let entry = Entry::new(SERVICE, &account).map_err(|e| e.to_string())?;
    match entry.get_password() {
        Ok(p) => Ok(Some(p)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

#[tauri::command]
pub async fn keychain_delete(account: String) -> Result<(), String> {
    let entry = Entry::new(SERVICE, &account).map_err(|e| e.to_string())?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // The `keyring` crate's mock backend lets us exercise the wrapper without
    // touching the real OS credential store. Mock is auto-selected when the
    // crate's default features are off; in CI we run with default features so
    // these tests use the system store. Skip if the runner has no usable store.

    #[tokio::test]
    async fn roundtrip_set_get_delete() {
        let account = "vysted-test:roundtrip".to_string();
        // Clean up any leftover from a prior run.
        let _ = keychain_delete(account.clone()).await;

        // Get before set returns None.
        let before = keychain_get(account.clone()).await;
        match before {
            Ok(None) => {}
            Ok(Some(_)) => panic!("expected None before set"),
            // Runner without a usable credential store — skip rather than fail.
            Err(_) => return,
        }

        // Set, then get returns the value.
        if keychain_set(account.clone(), "secret-value".into())
            .await
            .is_err()
        {
            // Runner without writable store — skip.
            return;
        }
        let after = keychain_get(account.clone()).await.expect("get after set");
        assert_eq!(after, Some("secret-value".to_string()));

        // Delete, then get returns None again.
        keychain_delete(account.clone()).await.expect("delete");
        let final_get = keychain_get(account.clone())
            .await
            .expect("get after delete");
        assert_eq!(final_get, None);
    }
}
