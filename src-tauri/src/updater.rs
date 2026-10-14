//! Self-update (R16). `update_check` asks the configured endpoint (or a
//! validated `VYSTED_UPDATER_ENDPOINT` override) for `latest.json`;
//! `update_download_and_install` downloads, verifies the minisign signature
//! against the configured `plugins.updater.pubkey`, installs, and relaunches.
//! Signature verification is done by the plugin on every path and is never
//! switched off here.

use serde::Serialize;
use tauri::{AppHandle, Emitter, Url};
use tauri_plugin_updater::{Update, UpdaterExt};

const ENDPOINT_ENV: &str = "VYSTED_UPDATER_ENDPOINT";

#[derive(Serialize)]
pub struct UpdateInfo {
    available: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    notes: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    date: Option<String>,
}

#[derive(Clone, Serialize)]
struct Progress {
    downloaded: u64,
    total: Option<u64>,
}

/// Accept only `https://<host>/...` or `http://127.0.0.1:<port>/...`.
fn validate_endpoint(raw: &str) -> Option<Url> {
    let url = Url::parse(raw.trim()).ok()?;
    match url.scheme() {
        "https" if url.host_str().is_some_and(|h| !h.is_empty()) => Some(url),
        "http" if url.host_str() == Some("127.0.0.1") && url.port().is_some() => Some(url),
        _ => None,
    }
}

/// The env override, when set and valid. An invalid value is logged and ignored.
fn endpoint_override() -> Option<Url> {
    let raw = std::env::var(ENDPOINT_ENV)
        .ok()
        .filter(|v| !v.trim().is_empty())?;
    let url = validate_endpoint(&raw);
    if url.is_none() {
        diag_eprintln!(
            "[vysted] ignoring {ENDPOINT_ENV}: only http://127.0.0.1:<port>/ or https:// URLs are honoured"
        );
    }
    url
}

/// Called on the context before `Builder::build`: the plugin refuses a non-TLS
/// endpoint in release builds unless `dangerousInsecureTransportProtocol` is set,
/// and exposes no per-builder switch. Set it ONLY for this process and ONLY when
/// the validated override is loopback http; the configured endpoint stays https
/// and the pubkey/signature check is untouched.
pub fn allow_loopback_override<R: tauri::Runtime>(context: &mut tauri::Context<R>) {
    if endpoint_override().is_some_and(|u| u.scheme() == "http") {
        if let Some(cfg) = context
            .config_mut()
            .plugins
            .0
            .get_mut("updater")
            .and_then(|v| v.as_object_mut())
        {
            cfg.insert(
                "dangerousInsecureTransportProtocol".into(),
                serde_json::Value::Bool(true),
            );
            diag_println!("[vysted] updater using loopback test endpoint from {ENDPOINT_ENV}");
        }
    }
}

async fn find_update(app: &AppHandle) -> Result<Option<Update>, String> {
    let teardown = app.clone();
    // The Windows installer exits the process itself, skipping RunEvent::Exit.
    let mut builder = app
        .updater_builder()
        .on_before_exit(move || crate::teardown_children(&teardown));
    if let Some(url) = endpoint_override() {
        builder = builder.endpoints(vec![url]).map_err(|e| e.to_string())?;
    }
    let updater = builder.build().map_err(|e| e.to_string())?;
    updater.check().await.map_err(|e| e.to_string())
}

/// Offline, a 404, or no release yet all answer `{ available: false }`.
#[tauri::command]
pub async fn update_check(app: AppHandle) -> UpdateInfo {
    match find_update(&app).await {
        Ok(Some(update)) => UpdateInfo {
            available: true,
            version: Some(update.version.clone()),
            notes: update.body.clone(),
            date: update
                .raw_json
                .get("pub_date")
                .and_then(|v| v.as_str())
                .map(str::to_string),
        },
        Ok(None) => UpdateInfo {
            available: false,
            version: None,
            notes: None,
            date: None,
        },
        Err(err) => {
            diag_eprintln!("[vysted] update check found nothing ({err})");
            UpdateInfo {
                available: false,
                version: None,
                notes: None,
                date: None,
            }
        }
    }
}

#[tauri::command]
pub async fn update_download_and_install(app: AppHandle) -> Result<(), String> {
    let update = find_update(&app)
        .await?
        .ok_or_else(|| "No update is available any more.".to_string())?;
    let mut downloaded: u64 = 0;
    let emitter = app.clone();
    update
        .download_and_install(
            move |chunk, total| {
                downloaded += chunk as u64;
                let _ = emitter.emit("updater://progress", Progress { downloaded, total });
            },
            || {},
        )
        .await
        .map_err(|e| {
            diag_eprintln!("[vysted] update install failed ({e})");
            e.to_string()
        })?;
    diag_println!("[vysted] update {} installed, relaunching", update.version);
    app.restart()
}

#[cfg(test)]
mod tests {
    use super::validate_endpoint;

    #[test]
    fn accepts_loopback_http_and_https() {
        assert!(validate_endpoint("http://127.0.0.1:8787/latest.json").is_some());
        assert!(validate_endpoint("https://example.com/latest.json").is_some());
    }

    #[test]
    fn rejects_everything_else() {
        for bad in [
            "http://example.com/latest.json",
            "http://localhost.evil:8787/latest.json",
            "http://127.0.0.1.evil.com:8787/latest.json",
            "http://127.0.0.1@evil.com:8787/latest.json",
            "http://127.0.0.1/latest.json",
            "http://localhost:8787/latest.json",
            "file:///tmp/latest.json",
            "ftp://127.0.0.1:21/latest.json",
            "",
            "   ",
            "not a url",
        ] {
            assert!(validate_endpoint(bad).is_none(), "accepted {bad:?}");
        }
    }
}
