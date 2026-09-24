# Baseline: small typed text decisions today

This file is verification evidence only. The machine-readable copy is `BASELINE.json`. Paths are relative to the repo root. `null` or "unknown" means no source measured the value. It does not mean zero.

**Units.** A *turn* is one composer message. A *DEEP run* is one DEEP research brief. The totals use a *session* of one composer turn that runs one DEEP research brief.

## Spot-check of the scouts

I opened every site listed below.

- **Kept:**
  - `resolution_policy.py:119`
  - `relevance.py:522`
  - `planner.py:178`
  - `slash-commands.ts:65`
  - `verify.py:120`, as an analogue only
- **Corrected:** `decompose` is defined at `planner.py:350`, not `:353`. I also traced its `llm_call`, which the code scout had not done. It is `oneshot.complete` on the turn's own provider, model and key (`agent_runtime.py:1608-1615`). It runs only when three things hold: the turn is compound, the turn is not read-only, and the provider is in `_PLANNER_PROVIDERS` (`agent_runtime.py:101, 1712`). Ollama is not in that set.
- **Reclassified:** `relevance.py:623 gate_news` matches news to the bound research target, not to portfolio holdings. It moved to entity_match, and holding_relevance now has no site.
- **Dropped:**
  - `semantics.py:542`: a numeric divergence between two feeds, not a text decision.
  - The evidence scout's 60014 ms latency: a synthesis-step timeout (`surface/research-briefs/EVIDENCE.md:30`).
  - The $0.003777 cost (`spend-ledger.jsonl:43`): it covers a whole DEEP turn. Neither number belongs to any of the four decisions.

## Per decision type

| Type | Sites | Per session | Latency | Cost / session | Keyless |
| --- | --- | --- | --- | --- | --- |
| entity_match | see below | ≥13 per DEEP run (lower bound) | unknown | $0 (0 paid calls) | yes |
| composer_intent | see below | 1 per turn, plus 1 paid planner call on a compound turn | unknown | $0 for the classification; compound turn ≤ $0.001399 | yes (planner skipped) |
| holding_relevance | none | unknown (not implemented) | unknown | unknown | unknown |
| thesis_contradiction | none | unknown (not implemented) | unknown | unknown | unknown |

### entity_match: heuristic, keyless

**Sites**

- `sidecar/services/resolution_policy.py:119` (`decide`)
- `sidecar/services/research/relevance.py:522` (`entity_match`)
- `sidecar/services/research/relevance.py:593` (`row_relevant`)
- `sidecar/services/research/deep.py:725` (web-row gate)
- `sidecar/services/research/relevance.py:623` (`gate_news`), called from `sidecar/services/research/fast.py:482` and `sidecar/services/research/deep.py:889`

**Count.** Every web row that becomes a source passes `row_relevant` once: `deep.py:725` calls `relevance.py:601`, which calls `entity_match`. `r2-deep-cgpower` captured 13 web URLs (`surface/research-briefs/EVIDENCE.md:30, :73`). So there are at least 13 calls per DEEP run. Rows that were scored and dropped are not logged, and news items are not counted, so the real count is higher and unknown.

**Latency.** Never timed. It is a pure in-process function (`relevance.py:12`).

**Cost.** $0. There is no LLM call (`relevance.py:12`; `resolution_policy.py:119` "pure and deterministic").

**Known misses.** "BAJFINANCE 200 DMA breakout as stock nears record" and "INFY 1500 target: brokerages raise view" both score 0.0 and are dropped (`census/code/research-retrieval-relevance.md:146, 148`).

### composer_intent: heuristic, keyless; paid planner on compound turns

**Sites**

- `sidecar/services/planner.py:178` (`classify_intent`)
- `sidecar/services/agent_runtime.py:1651` (gates the turn's tool surface)
- `sidecar/services/agent_runtime.py:1604` (compound check)
- `src/modules/chat/slash-commands.ts:65` (`matchBareTicker`, LLM-free)
- `sidecar/services/planner.py:350` (`decompose`, paid)

**Count.** `classify_intent` runs once per agent-mode turn (`agent_runtime.py:1651`). The probes show one `IntentResult` per message: `surface/composer-chat/52-intent-gate-probe.txt` and `surface/portfolio-notes/30-intent-gate-portfolio-notes.txt`. A compound turn adds a second `classify_intent` call and one paid `decompose` call (`agent_runtime.py:1604, 1617`).

**Latency.** `classify_intent` is never timed. The planner call is capped at 20 s (`agent_runtime.py:1007`), and its own latency is unknown. A whole compound turn on gpt-4o-mini took 5.6 s (`spend-ledger.jsonl:54`).

**Cost.** The classification costs $0. A compound turn cost $0.001399 in total (`spend-ledger.jsonl:54`, tag `s2a-cc-plan-4omini`; `surface/composer-chat/EVIDENCE.md:60`). The planner's share of that is unknown.

**Keyless.** The classification runs keyless. On the local ollama path, the planner pre-pass is skipped entirely (`agent_runtime.py:98-101`).

**Known miss.** "Write a note on Cochin Shipyard…" was classified as `read` with no signals, and the probe build sent 37 of 50 tools (`52-intent-gate-probe.txt:10`). The current gate strips write tools only on a positive read cue (`agent_runtime.py:1653-1656`).

### holding_relevance: not implemented

No code decides whether a news item concerns a portfolio holding. The closest reusable code is `gate_news` (`relevance.py:623-643`). It has the same shape, but it is scoped to the research target and only to Indian equities. The scout also found no evidence of this decision in r15 (`laya/baseline/evidence.json`).

### thesis_contradiction: not implemented

No code compares a filing sentence with a written thesis. It exists only as a backlog idea: `invent/BACKLOG.md:56` (BL-09) and `invent/ideas/quant.json:185` (quant-9).

The nearest shape in the code is the numeric cross-check at `sidecar/services/research/verify.py:120` (`_parse_verdict`, AGREE/DISAGREE/UNVERIFIED). It runs only on profiles with `cross_check` set (`agent_tools/deep_research.py:302`). It makes 1 extract call and at most 5 verdict calls (`verify.py:80`) on the run's own model, and the ledger does not meter those calls (`surface/research-briefs/EVIDENCE.md:147-148`). These calls are not counted in the totals.

## Totals and business case

A session, meaning one composer turn that runs one DEEP brief, makes at least 14 of these decisions: 1 composer_intent and at least 13 entity_match. Today all of them cost **0 paid calls and $0**, and their latency is unknown because in-process heuristics are never timed. The only paid call in scope is the planner on a compound turn. That is 1 call, capped at 20 s, and the whole turn costs at most $0.001399 on gpt-4o-mini (`spend-ledger.jsonl:54`).

Some decisions are skipped entirely:

- holding_relevance and thesis_contradiction are never made, keyless or paid.
- The planner is skipped on the keyless ollama path.

So a local model would not save money per session today. The case rests on three other things:

1. **Quality of the free heuristics.** On-entity headlines are dropped at 0.0 (`census/.../research-retrieval-relevance.md:146, 148`), and a write request was classified as `read` (`52-intent-gate-probe.txt:10`).
2. **Enabling the two decisions nobody makes today.** Making them with a paid model would add a round-trip per item.
3. **Giving keyless users a planner.**

Whether a local encoder beats the heuristics is the question for the measure phase. This baseline does not answer it.
