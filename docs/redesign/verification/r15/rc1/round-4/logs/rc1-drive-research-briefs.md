# rc1 drive — research-briefs (gate round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (worktree
`rc1-round-4-cand`, HEAD verified before starting). Own sidecar
`127.0.0.1:52321`, data dir `rc1-round-4-data-rc1-drive-research-briefs`
(fresh `cp -R` of `rc1-round-4-seed-data`, keyless). Sleep pid on boot: 58058
(worker 58061); stopped at end of drive (`kill 58058` then `kill 58061` —
the sleep pid alone didn't tear the worker down this time, worker killed
directly). Reads to the shared `:52152/:52153/:52154` stack were not needed —
every check ran against my own sidecar. Raw evidence:
`docs/redesign/verification/r15/surface/research-briefs/rc1/round-4/`.

## Step 0 — code-diff scope check (before spending any live budget)

`git diff 5903f373..1006c6da` (round-3's certified fix candidate → this
round's candidate) touches exactly two sidecar files outside test/doc
churn: `sidecar/services/agent_tools/fundamentals.py` (2 lines,
R15-LEAD-040 — routes `resolve()`/`resolve_async()` off the shared
`to_thread` pool) and `sidecar/services/agent_tools/resolve_symbol.py` (3
lines, same). `sidecar/services/research/*.py` (deep.py, iter.py,
citecheck.py, verify.py), `src/modules/research/*`, `src/lib/host-actions.ts`,
`src/lib/brief-ingest.ts`, `types/brief.ts` are **byte-identical** to the
round-3 certified candidate. This means every round-3 live-or-code verdict on
this surface (11/13 register items `ok`, 2/13 correctly `open`) cannot have
regressed by code change alone — the only way any of them could differ this
round is an environment/data change (SearXNG state, upstream API behaviour),
which the live checks below rule out.

`R15-DATA-117` (the one register-tracked fix this round that touches
fundamentals) withholds `price_to_book`/`book_value` to `null` on a mixed
trading/statement-currency basis (`yfinance_provider.py`,
`_withhold_mixed_basis_ratios`). Read `brief-blocks.tsx` `equityItems`
(`makeItems().push`, drops any card whose formatted value is `"—"`, i.e. a
`null`/`NaN` field renders **no card**, never a fabricated one — this is
pre-existing Constitution-VI behaviour, unchanged) — a withheld P/B on an
ADR-class symbol degrades gracefully to "no Price/Book card," not a crash or
a wrong number. No live ADR run was spent confirming this given the null path
is a pure, already-unit-tested formatter (`brief-blocks.test.ts`) with no
async/data branching — code read is sufficient evidence, not spending
ollama-lane budget on it.

## Live runs

1. `01-deep-cgpower-llama.jsonl` — ollama llama3.1:8b, DEEP, same repro as
   round 2 and round 3's owner-drive ("Do a deep research brief on CG Power
   and Industrial Solutions — order book, margins, and whether the valuation
   is justified versus peers.", `context_snapshot.focusedSymbol=CGPOWER`).
   First attempt (`--out` file, manual `nohup ... &` backgrounding) was
   externally SIGTERM'd around the 6-7 minute mark with an empty `--out` file
   — re-run using the Bash tool's own `run_in_background` (not manual nohup)
   completed cleanly, 199.2s wall, `RUN_EXIT=0`.
   - Real synthesis (`backend: keyless-fallback`, `execution.degraded_reason:
     null`) — NOT the old structured-floor fabrication. **R15-RESEARCH-005
     holds.**
   - `[7]` marker on "Price to book ratio ... 17.506767" resolves correctly
     to `sources[6]` = `vysted://fundamentals/CGPOWER` (`price_to_book:
     17.506767` in the same structured payload — exact match).
     **R15-RESEARCH-003 holds.**
   - Zero non-numeric bracket tokens this run (no `[vysted://...]` literal —
     the defect round 3's CG Power run hit on the SAME repro did not
     reproduce here; model-output-dependent, as round 3 already noted). No
     RESEARCH-043 concurrence note needed from this run.
   - R8 audit / softening still live: "Recent closing price ... INR 886.0
     (not confirmed in this run)" — the claim-audit pass softened an
     unconfirmed claim rather than shipping it bare. Matches round 3.
   - The end-of-stream `research_step` "The brief panel did not confirm the
     publish" (`step_kind: notice`, `status: error`) at 199.2s is the SAME
     harness artifact round 3 documented (`vy.py`'s CLI ack-parser, not the
     real frontend — `applyHostAction`/`message-notices.ts` un-touched code
     path). Not a product finding.
   - **Observation, not filed:** the brief's "Facts Established" section
     states "Assembled total book value (as of June 30, 2026): 53.00 Crore
     [1]" — `[1]` resolves to a real NSE filing, but 53 crore does not
     arithmetically reconcile with the structured `book_value` (₹50.609/share
     × ~157.5cr shares ≈ ₹7,970cr, not ₹53cr). Attempted to fetch the cited
     PDF directly to check its actual text (`curl` to
     `nsearchives.nseindia.com`) — connection failed (HTTP/2 stream reset),
     not pursued further. This reads as the same class the census already
     logged as a non-defect ("model narration on the local lane misreads
     fractions/units," round-1 `EVIDENCE.md` "Other observations") — a weak
     local-model arithmetic/narration error on a citation the integrity net
     legitimately resolved, not a product citation-integrity bug. Not filed
     as a raw finding; flagged here for the record only, per DECISIONS
     4.9-4.12 (local-model-figure-with-no-tool-call-behind-it class — this
     one DOES have an ok tool call behind it, it's the model's arithmetic
     that's wrong, so strictly outside even that class, but the same
     "known local-model narration noise" bucket).

2. `02-search-status.json` / `03-searxng-status.json` — direct probes,
   own sidecar. `/search/status` tier `t1_keyless`; `/search/searxng/status`
   `state: degraded`, honest per-engine reasons (brave "Suspended: too many
   requests", duckduckgo "CAPTCHA", startpage "Suspended: CAPTCHA").
   **R15-RESEARCH-028 holds**, byte-identical shape to round 3.

3. `04-badkey-humanize.txt` — `--bad-key` against openai on my own sidecar:
   "The OpenAI API key was rejected — check it in Settings." **R15-AGENT-027
   (401 branch) holds.**

## Code-read confirmations (no live call needed, files unchanged since round 3)

- `sidecar/services/research/citecheck.py:39` `MARKER_RE` and
  `src/lib/brief-ingest.ts:396` `CITE_MARKER_RE` — still `\[(\d{1,3})\](?!\()`
  on both sides, byte-identical. Confirms **R15-RESEARCH-043 stays
  blocked_tier4** as documented (DECISIONS 4.14) — no fix round, matches the
  lead's instruction; not re-litigated.
- `src/lib/host-actions.ts:287` `webAvailable = sources.length > 0 ||
  input.web_available === true` — unchanged. **R15-RESEARCH-041 stays open
  (low)**, not a regression.
- `src/modules/research/BriefPanel.tsx` `SourceRow`/`FaviconDot` — unchanged,
  still an external `<a>` + favicon for every source incl. `vysted://`.
  **R15-UI-080 stays open (low)**, not a regression.
- `sidecar/services/agent_runtime.py:2894` `f"call_{uuid.uuid4().hex}"` for
  every tool call — unchanged. **R15-AGENT-046 holds.**
- `sidecar/services/research/verify.py` `_split_claims`/`_parse_verdict` —
  unchanged. **R15-RESEARCH-002/004 hold** (not re-run live this round;
  round 3 already reconfirmed them on THREE independent model/depth
  combinations, and the file is byte-identical).
- `sidecar/services/research/deep.py` `_LLM_CALL_TIMEOUT_SECS = 60.0` — same
  constant round 2/3 read.

## R15-LIFECYCLE-005 (openbb-mcp child death → silent SSE death)

Not re-induced live this round (shared `:52153` is out of owner-drive scope,
read-only, never restarted). No diff to `mcp_client.py`/`streaming.ts` in
this candidate vs the round-3 certified one. Register status `fixed`,
unchanged.

## Spend

Ledger tag none needed — every call this round was `ollama` (free/local) or
a direct GET/`--bad-key` probe (no LLM spend). $0.00 against the budget.

## Sidecar

Boot: sleep pid 58058 (worker 58061), health confirmed ok twice (before and
after the live DEEP run). Stopped: `kill 58058` (no-op, job already reaped)
then `kill 58061` (worker), confirmed down via a failed `/health` connect.
