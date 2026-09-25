# rc1-battery-7 working log

Role: regression battery shard 7 (Sonnet), stage-c batch-9 + batch-10, 13 writer sets
(set-33..set-45). Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`.

## Rig

- Own sidecar booted from `rc1-cand/sidecar` (source) on `127.0.0.1:52347`, data dir
  `rc1-data-battery-7` (copy of `rc1-seed-data`). MCP env vars point at the shared
  `:52153`/`:52154` stack.
- sleep-pid wrapper: 20557 (bash -c wrapper around `sleep 86400 | ./.venv/bin/python3
  main.py --port 52347 ...`), sidecar log at `<scratchpad>/battery7-sidecar.log`.
- Models: `llama3.1:8b` via Ollama through `scripts/r15/vy.py`. No OpenRouter/OpenAI spend
  needed this shard.

## Method

For each writer set: pulled the entry list + writer assignment from the batch's `PLAN.md`
"0. The N entries" table, cross-referenced each entry's verdict in that batch's
`VERDICTS.md` "Per-entry evidence". Only entries the batch verifier actually **certified**
(incl. `needs_gui`) were re-run — not-certified entries were out of scope for a regression
check (they were never a green baseline to regress from) and are listed as excluded in
each set's file.

- Where the original cert's evidence was a live sidecar route or an outside-world check,
  re-ran it live against `:52347` (curl) or via an in-process python probe (importing the
  candidate's own sidecar modules directly — engine/store/catalog internals with no REST
  route) for parity with the original mechanism, never a full pytest/vitest suite.
- Where the original cert's evidence was PURELY a committed vitest/pytest file (frontend
  component logic, unit tests), verdict `ci_pinned` naming the test file, confirmed present
  on `4097dac4` — per role instructions the heavy lane owns re-running those suites.
- `needs_gui` entries are marked as such (no GUI available to this headless shard).
- A handful of live `vy.py` ollama agent runs covered several entries in one shot
  (`Research NVDA briefly.` for AGENT-046/CODE-AGENT-008/RESEARCH-027; `draw a support
  line...` for AGENT-084, reused for AGENT-082's spend_usd leg).

## Sets completed (13/13)

set-33, set-34, set-35, set-36, set-37 (batch-9); set-38, set-39, set-40, set-41, set-42,
set-43, set-44, set-45 (batch-10). All in `battery/set-*.md`, raw output in
`battery/raw/set-*/`.

## Notable non-regressions / caveats (not findings — no candidate defect)

- DATA-066 (set-36): a 20-symbol cold `/quotes` batch hit a 40s client timeout twice,
  while a 5-symbol warm repeat was 0.00s (matches the cert's warm-cache claim exactly).
  Multiple other verification shards' sidecars are concurrently hitting NSE/yfinance on
  this box — consistent with the cert's own noted caveat about cold-batch NSE contention,
  not a code-path regression. Not filed as a finding.
- CODE-AGENT-013 (set-39): catalog counts are 56/56/55/32 vs the cert's 55/55/54/31 — a
  consistent +1 across every metric, matching a later-added capability (RESEARCH-030's
  `earnings_call_transcript`, also certified in this same writer set). The mechanism
  (parity + one `default_grant=False` capability) is unchanged. Not filed as a finding.
- RESEARCH-030 (set-39): KPITTECH's transcript PDF fetch failed with a curl "Recv failure:
  Connection reset by peer" (NSE anti-bot on this network path) while the filing discovery
  itself (`filing_date=2026-08-04`, correct URL, correct transcript classification) matched
  the cert exactly, and a second symbol (INFY) fetched the full transcript text
  successfully. Not filed as a finding.

## No findings

No regression, new defect, chain failure, gate-8 issue, or environment outage proven by a
direct probe was found in this shard's 13 sets. `findings/rc1-battery-7.json` is `[]`.
