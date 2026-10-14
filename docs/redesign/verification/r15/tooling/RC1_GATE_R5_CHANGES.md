# rc1 gate, round 5: script changes

Script `rc1-gate.js` (445 lines), dry run `rc1-gate.dryrun.mjs` (unchanged). Round 4 was run at candidate `1006c6da`, and it went FAIL with two harness gaps this round repairs: the battery raw-output check undercounted, and the Gate 8 raw grep dumps could not be pushed to GitHub.

## 1. Battery raw check undercounted: 25 not-run ids, only 3 caught

**Round-4 finding.** `docs/redesign/verification/r15/rc1/round-4/verifier/own/battery-raw-check.txt` (the fresh verifier's own on-disk check) found 25 fixed ids at the round-4 sha whose raw file was never an executed probe — each held a "not run" placeholder because certification for that id existed only as a pinned vitest/pytest test the battery role is forbidden from running. `docs/redesign/verification/r15/rc1/round-4/battery/MISSING_RAW.json`, written by the collator that same round, listed only 3 of those 25.

**Root cause.** The collator's rule (round-4 script, the `BATTERY RAW OUTPUT` paragraph) was "a file whose first line starts `'NOT RUN:'`" — a literal string match. The battery-shard role's own instruction only ever told agents to write `'NOT RUN: <named reason>'`, but in practice the 25 real files opened with variants of that phrase: `'NOT RUN AS A LIVE PROBE: ...'`, `'NOT RUN as a vitest execution: ...'`, `'NOT RUN LIVE: ...'`. All 25 open with the two words "NOT RUN"; only 3 happened to be followed immediately by a colon with no other words in between, so only those 3 matched the literal-string check. The other 22 carried real investigation underneath (a `grep` for the pinned test, a source read confirming the fix_shape) but the pinned test itself was never executed — they are still not-run by the round's own coverage rule, just not matched by the collator's narrow string check.

**Fix** (`rc1-gate.js`):

- **Battery shard role** (the `shardLane` prompt, "COVERAGE FIRST"): a new sentence names the three round-4 phrasings and states, mechanically, that a NOT RUN placeholder is never an acceptable raw file in any phrasing, and that the collator counts it as missing regardless of what grep or source-check the agent adds underneath it.
- **Collator role** (the `BATTERY RAW OUTPUT` paragraph): the check is rewritten as an exact, case-insensitive rule applied to every id's first non-blank line — starts with "NOT RUN", "NOT-RUN" or "SKIPPED" (any phrasing after those opening words) → missing, whatever follows. No file at all → missing. Any other content → present. The rule states explicitly that round 4 matched only the literal `'NOT RUN:'` prefix and missed 22 of 25.
- **`MISSING_RAW.json` reason field**: narrowed from free text to an enum of exactly `'no_file'` (no file exists) or `'not_run'` (a file exists but is a skip placeholder), so the two failure shapes are told apart mechanically instead of by prose.
- **Never capped**: the collator instruction now says explicitly to list every missing id this way, however many there are, and that `count` always equals `missing.length`.
- **Evidence-size check, same collator call**: `find ${EV} -type f -size +20M`, every hit returned in a new `oversize` field (`COLLATE` schema, `oversize: STRS`). The script (`rc1-gate.js`, right after the collator call) turns a non-empty `oversize` into `blockers.push('HARNESS evidence-oversize: ...')`, naming path and size, so the lead sees it before ever trying to push.

## 2. Gate 8: raw grep dumps broke the push

**Round-4 finding.** `docs/redesign/verification/r15/rc1/round-4/gate8/GREP_DUMPS_NOTE.md`: the round-4 Gate 8 role wrote two raw dumps under the evidence dir — a full `rg` output (111.75 MB, 193123 lines) and a classified copy (64.97 MB). GitHub's push rejected the first outright (over the 100 MB hard limit) and would have warned on the second (over 50 MB); both had to be moved to the session scratchpad after the fact and summarised by hand. The `docs/` root alone produced the bulk of the 193k lines, because the search patterns (a short list of common words) hit `docs/archive/` and other historical handoff prose at high volume.

**Fix** (`rc1-gate.js`, Gate 8 role, item (d)): the raw `rg` output for each searched root now goes to `${SCRATCH}/gate8-${ROUND}/<root>.txt` — the run's own scratch directory, never committed, never under the evidence dir — and item (d) tells the agent to name that scratch path in `GATE8.md` so the lead can find it. Only three small, bounded files stay under `${EV}/gate8/`:

- `gate8/grep-summary.json` — per root, `{total, product, historical, false_positive}`.
- `gate8/grep-product-hits.tsv` — every product-surface hit, in full (this class stays small since the relevant product surface was already removed).
- `gate8/grep-examples.tsv` — at most 200 example rows per root for the other two classes, labelled by root and class.

The instruction states the size facts directly (GitHub rejects over 100 MB, warns over 50 MB) and caps every file the role writes under the evidence dir at 20 MB, with an explicit instruction never to narrow a search pattern just to shrink the raw count — cut example rows instead, and say so in `GATE8.md`.

## Dry run

Command: `node rc1-gate.dryrun.mjs` from the tooling dir. Output: `all checks passed` (55 agents planned across the 32 checks; no dry-run expectation needed updating — the harness's `rc1-collate` regex checks (`MISSING_RAW.json`, `## Missing ids by shard`, `## Drive raw output`) and the `rc1-battery-*` id-coverage checks all still match the rewritten prompt text unchanged).

## Not changed, and why

- The Gate 8 prover's existing `${EV}/gate8.json` summary write (routes/tools/mcp/grep counts) is unchanged — it was already small; only the two oversized raw dumps needed moving.
- The battery shard-planning, indexer, drive, scenario, fix-loop and verifier roles are unchanged; round 4 already repaired their harness gaps (see `RC1_GATE_R4_CHANGES.md`).
- No JSON-schema `pattern` on the `reason` enum in `MISSING_RAW.json` (that file is written by the agent, not schema-validated by the script) — the collator instruction states the two allowed values directly instead.
