# rc1-battery-1 — regression battery shard 1 (gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Fresh start this round (no prior
`round-5` files under my label existed).

Sets: batch-7/W4-research-funnel (11 ids), batch-10/W3-fundamentals-bse-cache (4 ids),
batch-12/W6-error (1 id). 16 ids total.

## Sidecar

Booted one sidecar for the whole shard: copied `rc1-round-5-seed-data` to
`rc1-round-5-data-rc1-battery-1`, started `sidecar/main.py --port 52341 --data-dir <copy>`
from the candidate worktree's source, `VYSTED_OPENBB_MCP_PORT=52153` /
`VYSTED_SEC_EDGAR_MCP_PORT=52154` pointed at the shared read-only MCP subprocesses. Health
confirmed (`openbb-mcp: available`). Stopped at the end (killed the sleep pid feeding the
process's stdin — clean shutdown, not `kill -9`; confirmed `/health` refused after).

## Method

For each id: read the register entry's own repro + the certifying batch's VERDICTS.md
"per-entry evidence" line, then re-ran that exact repro — in-process against the
candidate's `sidecar/.venv/bin/python3` (importing the real modules: `services.search.*`,
`services.research.relevance`, `services.errors`), live HTTP against my own sidecar
(fundamentals/macro routes), two real outside-world network probes (a live 403 host,
a live bseindia.com host), and frontend source inspection (grep + read, no vitest — the
heavy lane owns that suite; nothing here needed a pinned-test-only verdict).

## Set-27 (batch-7/W4-research-funnel) — 11/11 hold

Ran a single Python driver (`battery1_set27.py`) covering all 11 ids in one process.
Every one reproduced the certified fixed behaviour: BSE AttachLive retry+backoff+AttachHis
fallback present (DATA-075); distinct typed fetch_page errors for a live 403 host and an
SSRF target (RESEARCH-019); a crashed heavy-research explorer now logs + emits a
`ResearchStep` (RESEARCH-033); SearXNG honors `numResults` for both results and citations
(RESEARCH-020); "TICKER <2-3 digit> DMA/high" no longer scores 0.0 (RESEARCH-021); an
"All rights reserved" SERP snippet is kept, only the per-paragraph extractor still flags
boilerplate (RESEARCH-023); `Citation` now carries `domain`/`published_at` end to end
(RESEARCH-024); the keyless breaker counts one failure per engine TURN not per attempt
(RESEARCH-038); Sonar/Perplexity citations badge by URL host first, provenance suffix
second (UI-038); out-of-range `[n]` markers render as a flagged inert chip, never a
silent deletion (UI-092); brief-blocks.tsx now renders money via the shared
`formatInstrumentMoney` (format.ts), with an explicit "currency unknown" label instead
of a bare number (RESEARCH-026).

## Set-41 (batch-10/W3-fundamentals-bse-cache) — 4/4 hold

Live GETs against my sidecar. `roce` + `field_meta.roce` present for
RELIANCE/CREST/AMAL (matches batch-10's certified values exactly: 0.08994 / 0.03686 /
0.22332) with an honest `unavailable` + reason for ELCIDIN (DATA-048). `basis` +
`field_meta.basis` present, "consolidated" for RELIANCE/CREST, honestly `null` +
reason for AMAL/ELCIDIN (DATA-054). `/fundamentals/AAPL/income` and `/ratings` both went
cold (0.26s/0.41s) → warm-cached (0.001s) on repeat, and all four previously-uncached
routes now call the shared `_cached()` helper; `data_cache.py`'s `MAX_ROWS` eviction
DELETE is still in `upsert()` (DATA-096). `/macro/WEO%2FUSA.NGDP_RPCH.A?provider=imf`
returns `is_projection=false` for 2023/2024 and `true` from 2025 on, byte-identical to
the certified split, and `MacroChart.tsx` still renders the dashed-projection legend
(LEAD-024).

## Set-59 (batch-12/W6-error) — 1/1 holds

`services.errors.humanize()` run in-process on 9 synthetic exceptions matching the
register's and verifier's exact repro shapes (OpenAI no-credit 429 vs plain rate-limit
429, OpenAI/Groq context-overflow 400/413, a live `ConnectError` to a closed port for
Ollama, Gemini/xAI bad-key 400s, a decommissioned-model 404, an OpenRouter 402). Each
produced a distinct `code`+message; none collapsed to the register's old
"try again"/"check your network" catch-all (AGENT-027).

## Result

0 regressions, 0 findings. No id needed a `ci_pinned`/`needs_gui`/`blocked_env` verdict
— every repro ran live this round.

COVERAGE: 16/16 ids raw; no raw: (none).
