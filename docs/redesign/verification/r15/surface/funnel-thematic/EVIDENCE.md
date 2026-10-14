# funnel-thematic — evidence log (R15 wave 2)

Worker model: claude-fable-5-1. Own sidecar: `127.0.0.1:52223`, source run, data dir
`/tmp/claude-501/r15-funnel-thematic/data` (sqlite `.backup` copies, autosave blob, empty seeded
keystore). Raw SSE streams: `run-*.jsonl` in this folder. Sidecar log:
`/tmp/claude-501/r15-funnel-thematic/sidecar.log`.

## Environment at start (2026-09-19 15:04 IST)

- `GET /search/status` -> `tier: t1_keyless`, ddg/brave/mojeek all `closed` (available), min
  intervals 3.0 / 2.0 / 2.0 s.
- `GET /search/searxng/status` -> `state: not_installed_docker`, "docker CLI found but the daemon
  is not running". So every web_search in this trace rides the keyless floor
  (`backend: keyless-fallback`).
- Hand-started sidecar degradations: openbb-mcp unset (yfinance fallback), sec-edgar unset.
- Machine load average ~380 during the run (22 parallel sidecars from sibling workers). Wall-clock
  numbers below are inflated by that; stage COUNTS are not.

## Runs

(appended as they complete)
