# rc1-collate — round-5-recheck

Mechanical collation from evidence already on disk. No new judgement, no re-runs.

## Inputs
- `battery/set-*.md` (90 files) — parsed verdict column per id.
- `battery/raw/set-*/` — checked against the harness's shard plan (25 shards, 90 raw dirs) for `<id>*.txt` presence and skip-placeholder first lines.
- `findings/*.json` (27 files) — all empty arrays.
- `drives/*.md` — directory absent entirely; no drive evidence exists for this round.
- `DATAPACK.md` — not found at the evidence root.

## Outputs written
- `OWNER_DRIVE.md` — all 8 expected groups flagged `drive-raw-missing` (no `drives/` dir, no `surface/<group>/rc1/round-5-recheck/` dirs).
- `BATTERY.md` — 90 set rows with holds/regressed/ci_pinned/needs_gui/blocked_env counts (total holds 314, ci_pinned 79, regressed 0, needs_gui 0, blocked_env 0), missing-by-shard section, status line `incomplete`.
- `battery/MISSING_RAW.json` — 11 ids missing raw output, all reason `no_file` (they have sibling `.json` evidence files but no `<id>*.txt`).
- `FINDINGS.json` / `FINDINGS.md` — merged, empty (0 findings across all 27 files).

## Notes
- The 11 missing-raw ids (R15-DATA-020/023/025/056/026/048/054, R15-LEAD-024, R15-AGENT-044, R15-DATA-052/069) each have `.json` evidence files in their raw dir but no file matching `<id>*.txt`, so per the harness's literal `<id>*.txt` rule they count as missing raw output regardless of the `.json` content.
- No files under the evidence root exceed 20MB.
