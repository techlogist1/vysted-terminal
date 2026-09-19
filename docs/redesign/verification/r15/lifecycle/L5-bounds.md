# L5-bounds — do logs and caches stay bounded on the hundredth day?

Worker: claude-fable-5-1. Status: IN PROGRESS (file written as-you-go; continue from here if the
attempt died).

Method: code-read every store that grows + read-only measurement of the operator's real dir
(`~/Library/Application Support/com.vysted.terminal`, sizes / row counts / key namespaces only —
no values read) + an induced growth test on my OWN sidecar (port 52235, data dir
`/tmp/claude-501/r15-L5-bounds/data`).

## 1. Operator's real dir — measured (read-only, 2026-09-19)

Total 54 MB.

| Path | Size | Note |
|---|---|---|
| `exports/` | 43.3 MB (7 files) | 3 research PDFs = 38 MB (one is 8.5 MB for a 3.2 KB markdown brief) |
| `data_cache.db` + `-wal` + `-shm` | 2.66 + 4.12 + 0.03 MB | logical 1387 pages = 5.7 MB; main file last checkpointed Jun 11 |
| `fundamentals_cache.db` | 2.69 MB | 5,157 rows, one per symbol (PRIMARY KEY symbol) |
| `workspaces/` | 220 KB | live autosave 8.2 KB; a past autosave (`bak-r9-gates`) reached 129 KB |
| `delegate_runs.db` | 20 KB | 2 rows |
| `audit_log.db` | 24 KB | 0 rows |
| others (`portfolio`, `plugins`, `custom_agents`, `notes`, `searxng`) | ≤12 KB each | |
| `~/Library/Caches/vysted-terminal` | 38 MB | WKWebView cache (outside the data dir, OS-managed) |
| `~/.vysted-terminal` (fallback dir) | 3.5 MB | written by any sidecar started without `--data-dir` |

### data_cache.db rows by namespace (`sqlite3 file:…?mode=ro`, aggregate only)

| namespace | rows | MB | oldest | newest |
|---|---|---|---|---|
| `nse_bhavcopy:<yyyymmdd>` | 16 | 2.35 | 2026-07-08 | 2026-09-18 |
| `screener:fundamentals` / `:quote` / `:pair` | 2,678 | 1.94 | 2026-06-04 | 2026-06-11 |
| `nse_symbol_change:<yyyymmdd>` | 6 | 0.47 | 2026-07-09 | 2026-09-19 |
| `ratings`, `disclosures`, `sec`, `macro`, `earnings` | 38 | 0.26 | 2026-06-02 | 2026-09-13 |
| **total** | **2,738** | **5.03** | | |

Staleness: 2,730 rows (4.22 MB) older than 7 d; 2,722 (3.19 MB) older than 30 d; **2,706 rows
(2.21 MB, 99% of rows) older than 90 d**. Nothing has ever deleted a row.

