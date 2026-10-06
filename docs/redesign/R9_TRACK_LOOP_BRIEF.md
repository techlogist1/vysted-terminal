# R9 Track B — Loop integrity: extraction, relevance, assembly, cross-verification

Branch: `worktree-agent-r9-loop` from 004 HEAD. Partition is EXCLUSIVE. Push every
concrete deliverable.

## Files you own

`sidecar/services/research/` (iter.py, deep.py, fast.py, verify.py, relevance.py,
models.py, depth.py, citecheck.py and siblings), `sidecar/services/search/extract.py`,
their tests. NOTHING else — Team A owns web_search/deep_research/registry/config/native_search;
consume A's native-search interface (`native_search_available(...)` + channel callable),
which A pushes early on `worktree-agent-r9-tiers` — read it from origin.

## Workstreams

### B1 — Filing extraction robustness (gate: fresh SAKSOFT deep run surfaces real Q4 FY26

quarterly figures from the primary outcome filing)
The lead's diagnosis findings are in `docs/redesign/R9_SAKSOFT_DIAGNOSIS.md` (committed
before your dispatch — read it FIRST; it has the root cause, the real attachment URLs,
their content nature, and ground-truth figures). Make extraction robust across the real
diversity of NSE/BSE outcome formats: multi-attachment outcomes (cover letter vs results
annexure as separate PDFs — iterate attachments, prefer the one whose pages score finance
keywords), table layouts (pypdf layout mode where it wins), scanned-vs-text detection
(image-only pages → honest "scanned filing" note + assembly from secondary sources rather
than a false "not parsed"), page-selection keyword coverage for Indian quarterly results
("standalone", "consolidated", "quarter ended", "year ended", lakhs/crores variants).
Regression payloads: R8's archived briefs live in `docs/redesign/verification/r8/`.

### B2 — Last-mile relevance (gate: zero off-entity sources in fresh SAKSOFT + ROUTE runs)

relevance.py: partial-token leaks (Coromandel/Tea Post rode into SAKSOFT; Nestle/Zomato
cluster into ROUTE). Tighten entity matching so an off-entity source NEVER counts as a
source: require a strong-name or symbol match (not generic-token overlap), keep the tiered
floors so thin micro-caps still finish. Replay R8 regression payloads + add fixtures from
the operator's failing runs.

### B3 — Assembly completeness (gate: fresh ROUTE deep run nails Q4 numbers AND assembles

the ₹11/share FY26 dividend total its secondary sources carry)
The synthesis step must assemble the complete picture ACROSS sources, not transcribe the
primary filing's literal text. Adopt (from the June-2026 frontier scan, D30):

1. **CK-Pro structured progress state**: restructure the iter distill/working-report step
   into fixed sections — facts-established (with per-fact source indices), open questions,
   dead ends ("BSE search empty for X — don't retry"), planned next. Cuts wasted re-queries
   on weak models.
2. **Raw-evidence store**: keep full extracted page text per source index in-memory for the
   run; citecheck's spot-audit verifies claims against the cited source's FULL text (today:
   title+excerpt only). Measure: unsupported-claim verdicts should drop on the regression set.
3. **WebWeaver-lite (heavy/ultra only)**: synthesis emits an outline first, each section
   bound to explicit source indices, then writes per-section against only those sources.
   Cross-source numeric assembly: when multiple sources carry components of one metric
   (interim + final dividends), the working report holds them as separate facts and synthesis
   is prompted to compute/state the assembled total WITH all component citations.

### B4 — Cross-verification rule (gate 5)

On tier_a, when the active chat model has native web search (A's interface): the loop runs
BOTH channels — SearXNG retrieval AND native search — and cross-verifies claims between
them before the brief renders (extend verify.py: numeric claims appearing in one channel
only get flagged/cross-checked; agreements strengthen confidence; disagreements surface
honestly in the brief). No native search → SearXNG alone exactly as today. Tier B never
enters your loops' cross-verify (A suppresses). Bound the cost: one cross-verify pass,
within existing depth walls. ULTRA wall on slow chat models: keep the honest skip; you may
rebalance the ultra profile wall if evidence supports it (log in your report).

### B5 — Depth honesty

depth.py profiles stay deterministic. The composer slider remains the FLOOR (R7's
test_composer_slider_is_the_floor_model_may_escalate stays green).

## Gates (in-worktree)

`PATH=sidecar/.venv/bin:$PATH` — ruff check+format sidecar, FULL pytest (1978+ tests stay
green), new regression tests for B1–B4 pinned. Write `docs/redesign/R9_TRACK_LOOP_REPORT.md`.
You cannot run live research in the worktree — pin everything with fixtures; the lead
drives live SAKSOFT/ROUTE gates post-merge.
