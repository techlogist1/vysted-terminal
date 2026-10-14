# rc1-battery-7 — regression battery shard 7

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98 (verified via
`git -C .../rc1-round-5-cand rev-parse HEAD` before starting). Own sidecar booted on :52347,
source run, data dir `rc1-round-5-data-battery-7` (copy of the isolated seed profile), sleep pid
39841 (worker pid ~39842). `/health` returned ok immediately.

Sets covered (4 writer sets, 16 register entries total):
- batch-5/W3-agent-runtime-chat (set-17): AGENT-020, 025, 026, 031, 033, 040, 048, RESEARCH-014, UI-054
- batch-28/W1-opus (set-74): AGENT-001, 092, 094, 095, LEAD-014
- batch-11/W6-options-chain (set-52): DATA-079
- batch-18/W1-opus (set-65): LEAD-033

Method: for each id, read the register entry + the certifying batch's VERDICTS.md "per-entry
evidence" first, then re-ran the SAME mechanism live against the candidate — either a direct curl
against the own sidecar (DATA-079), or an in-process python call into the real candidate module
(`sidecar/.venv/bin/python3`) reproducing the register's own repro shape (AGENT-001, AGENT-092
[via source trace of the exact undispatched-dict mechanism, no LLM needed], AGENT-094, AGENT-095,
LEAD-033), or a source read against the exact functions/constants the certifying batch cited,
for entries whose original repro was itself "design, verified in code" (AGENT-020, 025, 026, 031,
033, 040, 048, UI-054, LEAD-014, RESEARCH-014) — none of these needed an LLM call, so nothing in
this shard touched the Ollama lock or a hosted key.

Result: all 16/16 hold. No regressions, no new defects, no chain failures, no gate8/needs_gui/
blocked_env in this shard.

Notable: R15-AGENT-001's in-process probe (`model_view()` on a synthetic COCHINSHIP/KPITTECH-shaped
fundamentals payload) reproduced the certifying batch's EXACT percent strings ("0.82%", "2.40%",
"-19.37%", "16.45%", "12.25%", "8.84%") — strong confirmation, not just a source read. R15-DATA-079's
live curl against a fresh day's NSE F&O bhavcopy naturally returned a slightly different contract/OI
count (276/244) than the cert's snapshot (276/238) — expected day-over-day data drift, not a
regression (same route, same provider label, same shape, OI still market-observed and present).

Sidecar stopped at end of shard (kill 39841; kills the sleep-piped python process cleanly).

COVERAGE: 16/16 ids raw; no raw: none.
