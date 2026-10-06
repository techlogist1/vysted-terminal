//! Persisted diagnostics log (R15-LIFECYCLE-008).
//!
//! A release build has no console (`windows_subsystem = "windows"`), so every
//! Rust, sidecar and MCP-subprocess line is also appended to
//! `<data-dir>/logs/vysted.log`: size-capped, with one rotated backup
//! (`vysted.log.1`). Std only. The sidecar's `GET /system/diagnostics` serves
//! a redacted tail of this file to Settings' "Copy diagnostics".

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

/// Rotate once the live file would pass this size (so at most ~2x on disk).
const MAX_LOG_BYTES: u64 = 2 * 1024 * 1024;

static LOG_PATH: OnceLock<PathBuf> = OnceLock::new();
static WRITE_LOCK: Mutex<()> = Mutex::new(());

/// `println!` that also appends the line to the persisted log.
macro_rules! diag_println {
    ($($arg:tt)*) => {{
        let line = format!($($arg)*);
        println!("{line}");
        $crate::diag_log::log_line(&line);
    }};
}

/// `eprintln!` that also appends the line to the persisted log.
macro_rules! diag_eprintln {
    ($($arg:tt)*) => {{
        let line = format!($($arg)*);
        eprintln!("{line}");
        $crate::diag_log::log_line(&line);
    }};
}

/// Point the log at `<data_dir>/logs/vysted.log`. Lines logged before this
/// (or when the directory cannot be created) go to the console only.
pub fn init(data_dir: &str) {
    let dir = Path::new(data_dir).join("logs");
    match fs::create_dir_all(&dir) {
        Ok(()) => {
            let _ = LOG_PATH.set(dir.join("vysted.log"));
        }
        Err(err) => eprintln!("[vysted] could not create the log directory {dir:?} ({err})"),
    }
}

/// Append one timestamped line. Best-effort: a write failure is dropped (the
/// console copy still exists), never fatal.
pub fn log_line(line: &str) {
    let Some(path) = LOG_PATH.get() else { return };
    let entry = format!("{} {}\n", utc_timestamp(SystemTime::now()), line.trim_end());
    let _guard = WRITE_LOCK
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());
    let _ = append_rotating(path, &entry, MAX_LOG_BYTES);
}

/// Append `entry`, first moving the file to `<name>.1` (replacing the old
/// backup) when the append would take it past `max_bytes`.
fn append_rotating(path: &Path, entry: &str, max_bytes: u64) -> std::io::Result<()> {
    let len = fs::metadata(path).map(|m| m.len()).unwrap_or(0);
    if len > 0 && len + entry.len() as u64 > max_bytes {
        let mut backup = path.as_os_str().to_owned();
        backup.push(".1");
        fs::rename(path, PathBuf::from(backup))?;
    }
    OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?
        .write_all(entry.as_bytes())
}

/// `YYYY-MM-DDTHH:MM:SS.mmmZ` for `now` (std has no calendar formatting).
fn utc_timestamp(now: SystemTime) -> String {
    let since = now.duration_since(UNIX_EPOCH).unwrap_or_default();
    let secs = since.as_secs();
    let (days, rem) = ((secs / 86_400) as i64, secs % 86_400);
    // Civil-from-days (Howard Hinnant), days since 1970-01-01.
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = yoe + era * 400 + i64::from(month <= 2);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}.{:03}Z",
        rem / 3_600,
        rem % 3_600 / 60,
        rem % 60,
        since.subsec_millis()
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn temp_log(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("vysted-diag-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir.join("vysted.log")
    }

    #[test]
    fn a_drained_line_lands_in_the_file() {
        let path = temp_log("append");
        append_rotating(&path, "t [sidecar] INFO boot\n", MAX_LOG_BYTES).unwrap();
        append_rotating(&path, "t [openbb-mcp] ready\n", MAX_LOG_BYTES).unwrap();
        let text = fs::read_to_string(&path).unwrap();
        assert_eq!(text, "t [sidecar] INFO boot\nt [openbb-mcp] ready\n");
    }

    #[test]
    fn rotation_keeps_the_cap_and_one_backup() {
        let path = temp_log("rotate");
        let entry = "0123456789\n"; // 11 bytes
        for _ in 0..10 {
            append_rotating(&path, entry, 40).unwrap();
        }
        let live = fs::metadata(&path).unwrap().len();
        let backup = path.with_file_name("vysted.log.1");
        assert!(live <= 40, "live file {live} bytes exceeds the cap");
        assert!(fs::metadata(&backup).unwrap().len() <= 40);
        let dir_entries = fs::read_dir(path.parent().unwrap()).unwrap().count();
        assert_eq!(dir_entries, 2, "exactly the live file and one backup");
    }

    #[test]
    fn timestamps_are_utc_iso() {
        let at = UNIX_EPOCH + Duration::from_millis(1_727_136_123_456);
        assert_eq!(utc_timestamp(at), "2024-09-24T00:02:03.456Z");
        assert_eq!(utc_timestamp(UNIX_EPOCH), "1970-01-01T00:00:00.000Z");
    }
}
