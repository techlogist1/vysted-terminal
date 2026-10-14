# rc1-battery-2 — regression battery shard 2 (round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (verified via `git rev-parse HEAD` in the
scratch worktree before starting). Own sidecar `:52342`, data dir copied from
`rc1-round-5-seed-data` to `rc1-round-5-data-battery-2`. Booted from source
(`sidecar/main.py`), no `VYSTED_OPENBB_MCP_PORT`/`VYSTED_SEC_EDGAR_MCP_PORT` set (not needed —
none of this shard's 16 entries touch openbb-mcp/sec-edgar-mcp live routes; DATA-084's repro is
an in-process stub of `_call_tool` per the register's own repro shape).

Sets covered (batch-8/W4-resolver-exchange-lanes, batch-11/W8-frontend-visual,
batch-13/W3-DOCS-017): 16/16 entries, all re-run against the running candidate, not judged from
diff. 15 holds, 1 ci_pinned (R15-UI-085 — the WCAG ratio math lives only inside
`design-contrast.test.ts`; grep-confirmed no unprefixed readable use of the flagged tokens
outside it, but the numeric floor check itself is vitest-only and this role does not run
vitest/pytest suites). No regressions, no new defects.

One test-methodology snag worth recording for later shards: an in-process script that calls
`services.agent_tools.resolve_symbol._resolve_symbol()` directly (bypassing FastAPI's app
lifespan) sees `former_name: null` on a renamed symbol, because only `app.py`'s boot lifespan
(line 138) calls `nse_symbol_change.schedule_refresh()` — the tool itself never self-activates
the rename lane the way the `/resolve` router does. This is NOT a regression: warming the lane
first (`await nse_symbol_change.schedule_refresh()`) before the tool call reproduces the exact
same payload as the live router. Filed as a methodology note under R15-CODE-DATA-003 in
`battery/set-32.md`, not as a new_defect.

Second note: R15-UI-039's exact repro ticker (`GUJGASLTD` bare prefix `"GUJGAS"`) no longer
matches any row in the bundled NSE/BSE masters — the masters have been regenerated since the
entry was filed and now carry the post-rename symbol `GUJENERGY` directly; `GUJGASLTD` survives
only in `former_names.json`. Verified the fix mechanism (`autocomplete()` running every result
through `_rename_instrument(_enrich_instrument(inst))`) still fires correctly against the
symbols that DO have a live master row (`GUJGASLTD` exact, `GUJEN` prefix) — isin/bse_code/
former_name/board/face_value are all populated, not null. Not a regression; upstream data
movement, noted in `battery/set-32.md`.

Sidecar stopped at the end (killed its own `sleep 86400` holder pid 24815; the `sh -c`-wrapped
convention other roles used was not what I launched with — mine was a bare `sleep 86400 | python3
...` background job, confirmed as the correct pair by matching start-time (`ps -o lstart`) before
killing).

COVERAGE: 16/16 ids raw across all 3 sets; no raw: none.
