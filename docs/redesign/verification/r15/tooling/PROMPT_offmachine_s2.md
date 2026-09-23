# PROMPT_offmachine_s2.md — Session-2 addendum (Stage B item 6)

Read `COMMON.md` first and obey it exactly (worker rules, severity scale, out-of-scope-by-decision
list). This file layers session-2 task specs on top of `PROMPT_census.md`; where a section below
says "reuse the X section of PROMPT_census.md" the full spec there applies unchanged — only the
extra notes here are additive.

Before any pnpm/node/cargo command:
`export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH`

**SCOPE FACTS (apply to every item below, restated from the launch brief):**

- Trading is out of the product (operator decision 23 Sep). Any promise, gap or opportunity
  whose subject exists only to connect a broker or place/simulate/gate an order is
  `removed_with_feature` / `dropped by operator decision 23 Sep`, never a defect. The user's
  own tracked portfolio (manual holdings, cost bases, P&L, CSV export, notes, watchlists)
  stays in scope.
- Lanes: local = `llama3.1:8b` via Ollama (`vy.py --provider ollama --model llama3.1:8b`); free
  OpenRouter `:free` slugs are lane 2; OpenAI-direct only for what the local model provably
  cannot do, under the $8 run cap (refuses at $7.50) — anything not driven for money is listed
  NOT TESTED with the cost it would take.
- Each machine-lane item boots its OWN headless sidecar on its own port in 52211-52399 with its
  own copy of the isolated data dir (recipe in `r15/stage0/ISO_STACK.md`); stop it when done.
  No item in this addendum needs its own sidecar boot unless it says so — the intent items may
  make read-only GETs to the shared isolated stack at `:52152` to confirm a route exists.
- GUI lane unavailable: headless evidence only; anything only the GUI can show is NEEDS-GUI.
- Failures are induced only at the app's own edge, never system/Docker/network.
- Raw findings use the standard shape into `census/raw/<prefix>-<id>.json`; verdicts go to
  `census/refute/<same basename>.json`. Every worker returns the fan-out RESULT
  `{model, output_file, summary, count, top}`. Continue from an existing output file, never
  restart.

---

## 1. INTENT chunks (session 2)

Reuse the **INTENT** section of `PROMPT_census.md` verbatim: `<source>`, `<start>`, `<end>` are
given per item. Output files: `CENSUS/intent/ledger-<source>-<start>.json` and
`CENSUS/raw/intent-<source>-<start>.json`, exactly as that section specifies.

Additional note (scope change): a promise about broker order execution, order placement/review,
live/paper switching or the broker plugin is **never** `missing` or `partial` — mark it
`dropped` with `decision_ref: "operator decision 23 Sep — trading removed from product"` and do
not emit a raw finding for it.

If your output ledger/raw file already exists (a prior session-2 attempt died), verify the
existing entries are still sound (spot-check against code at current HEAD) and finish the
remaining indices in your `[start, end)` range — never restart from index 0.

## 2. WORLD compares (session 2)

Reuse the **WORLD-COMPARE** section of `PROMPT_census.md` for topics `harness-context`,
`harness-tools`, `agent-native-ux`. The existing `CENSUS/world/<topic>-COMPARE.md` files for
these three are STUBS (thin placeholders, not a completed comparison pass) — read them, but
treat the task as needing a real pass: read the full research doc (`CENSUS/world/<topic>.md`)
and the real code paths listed in WORLD-COMPARE, and rewrite the COMPARE doc into the real
practice-by-practice table the spec describes. Emit `CENSUS/raw/world-<topic>.json` per the
spec (a raw finding per real gap, do not pad).

## 3. OPP-LEDGER verify (session 2)

Read `CENSUS/OPPORTUNITY_LEDGER.md` and every `CENSUS/world/*.md`. For **every Tier-A**
opportunity entry, re-check it against the current code (open the file:line the entry already
cites, or find the right one if it cites none) and against the world research docs the entry
draws evidence from:

- Still holds as written → leave it, append `verified: 2026-09-2x` inline.
- Holds but a detail is stale (the code moved, the evidence URL is dead, the "one step away"
  module no longer matches) → correct it in place, note what changed and why.
- No longer holds (already built, evidence didn't survive a second look, subject is on the
  trading-removal surface) → strike it: keep the entry but prefix its heading `[STRUCK]` and
  add a one-line reason; do not delete it (the record of what was considered matters).

This is a verification pass on opportunities, not a defect sweep — do not emit raw findings
(opportunities are not defects; `CENSUS/raw/world-table-stakes.json` already covers the
table-stakes gaps and is not reopened here unless you find it factually wrong, in which case
correct it and say so in your return summary).

Output: `CENSUS/OPPORTUNITY_LEDGER.md` edited in place (never rewritten from scratch — preserve
every entry, corrected or struck) plus `CENSUS/opp-ledger-verify.md`: one line per Tier-A entry
- id, verdict (held / corrected / struck), reason. This item has no refute stage (skipped).

## 4. LEDGER assembly (session 2)

Read every `CENSUS/intent/ledger-*.json` file (all 23 chunks across `blueprint`, `spec`,
`pdd-readme`, `deferred` — by the time this item runs, session 2's intent items above should
have filled the remaining chunks; if any chunk is still missing or unverified, say so plainly
rather than silently skipping it). Assemble `CENSUS/PROMISE_LEDGER.md`: a rollup table — one row
per source with counts of delivered / partial / missing / dropped, then a flagged list of every
`missing` or `partial` promise whose severity would matter for a public 0.9.0 release (cross-
reference against `CENSUS/raw/intent-*.json` for the ones that already became raw findings), and
a short section listing every promise `dropped` by the 23 Sep trading-removal decision (informational,
not a defect list). No refute stage for this item.

## 5. IDEATION seats (session 2)

Reuse the **IDEATE** section of `PROMPT_census.md`. Two new seats plus two derivations from
existing seat output:

- `sellside`: a sell-side equity research analyst at a boutique Indian brokerage covering
  small/mid caps — writes initiation reports, models management guidance against delivery
  quarter over quarter, competes for corporate access and channel checks, knows exactly what a
  buy-side client actually pays a report for versus what is filler.
- `designer`: a product designer obsessed with tools that are boring, correct and fast (the
  Linear / Superhuman / early-Bloomberg-terminal school, density minus chrome) — thinks in
  first-open trust signals, receipts-as-UI, and what separates an agent feature that feels
  earned from one that feels like a demo gimmick.

Both write `docs/redesign/verification/r15/invent/ideas/<seat-id>.md` and
`.../ideas/<seat-id>.json` exactly as the IDEATE section specifies. No refute stage.

- `journalist-json`: `docs/redesign/verification/r15/invent/ideas/journalist.md` already exists
  with no matching `.json`. Read it and derive `journalist.json` in the exact array shape the
  other seat json files use (`[{idea_id, name, one_liner, rides_on, new_parts, jarvis_axis,
  size, risk}]`) — do not invent new ideas, only structure the ones already written in the md.
- `bloomberg-md`: `docs/redesign/verification/r15/invent/ideas/bloomberg.json` already exists
  with no matching `.md`. Read it and derive `bloomberg.md` in the same prose shape (name / user
  moment / mechanics / why Jarvis / 60-second demo / lifecycle cost / biggest risk / size, plus
  a closing "strongest idea" paragraph) the other seats' md files use — again, structure only,
  no new ideas invented.

No refute stage for any of the four ideation items.

## 6. JUDGE panel (session 2)

One agent, single stage. Read every `docs/redesign/verification/r15/invent/ideas/*.json` (all
seats: bloomberg, retail, forensic, quant, hn-sceptic, journalist, sellside, designer) and every
surviving (non-struck) Tier-A opportunity in `CENSUS/OPPORTUNITY_LEDGER.md` after the session-2
verify pass. Rank everything together into:

- `docs/redesign/verification/r15/invent/BACKLOG.md` — human-readable, ranked, with for each
  item: size (days, S/M/L mapped to a day count), lifecycle cost (what breaks in six months /
  what it costs to keep alive — carry over from the idea's own lifecycle-cost field where
  present), on/off the design system, on/off the plugin contract, on/off the order-safety
  surface (trading is removed from the product, so this now means: does the idea write to the
  user's tracked-portfolio store, and if so through what gate), and a one-line why it ranks
  where it does.
- `docs/redesign/verification/r15/invent/BACKLOG.json` — the same data, machine-readable, one
  object per ranked item.

No refute stage.

---

## REFUTE (applies to every raw-emitting item above)

Every item that emits a `CENSUS/raw/*.json` file (the intent chunks, the three world compares)
gets a refute stage per `PROMPT_refute.md`, run exactly as that file specifies, against the raw
file the prior stage just wrote. Items that do not emit raw findings (opp-ledger verify, ledger
assembly, the four ideation items, the judge panel) skip the refute stage — this is encoded in
each launch-args file via each item's own stage list or a `"skip"` index, not left to the
worker's judgment.

## RESULT

Every stage returns the standard fan-out RESULT: `{model, output_file, summary, count, top}`,
`model` being the exact model id from your system prompt.
