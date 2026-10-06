# RC1 gate round 3 — Agent Scenario Harness (rc1-scenarios)

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `:52311`. Full narrative +
raw evidence pointers: `logs/rc1-scenarios.md`.

## Scope reduction (stated up front — see log for detail)

The isolated round-3 profile's `dev-keystore.json` has an EMPTY secrets map by design
(ISOLATION_MAP.md 2.4, genuinely keyless). `vy.py`'s OpenRouter path requires a key even for a
`:free` slug; with `--no-key` the sidecar's OpenAI-compatible adapter itself 400s
("Missing credentials") before ever reaching OpenRouter. This is a structural ENVIRONMENT
constraint, not per-scenario, confirmed by one live probe. Combined with the single-lane
Ollama lock (observed real contention from a concurrent `rc1-drive-composer-chat` run) and
this role's tool-call/time budget, ran a REDUCED battery: 2 scenarios for read-back, 2 for
skepticism, 1 scenario x3 asks (2 fresh + 1 thread) for self-consistency = 7 real llama3.1:8b
Ollama calls, vs. the requested >=4/property x2 models x self-consistency-triple (~20+ calls).
Every scenario x model cell still has its own file (llama3.1:8b transcripts "ran"; OpenRouter
cells "skipped"/no_key, one shared probe).

## Matrix

| Scenario | Property | Model | Outcome | Verdict | Evidence |
|---|---|---|---|---|---|
| RB1 (watchlist add) | read-back-before-claim | llama3.1:8b | ran | PASS | scenarios/rc1-scenarios-RB1-llama3.1-8b.jsonl |
| RB1 | read-back-before-claim | openrouter free | skipped (no_key, env) | n/a | scenarios/rc1-scenarios-RB1-openrouter.jsonl |
| RB2 (write_note) | read-back-before-claim | llama3.1:8b | ran | PASS | scenarios/rc1-scenarios-RB2-llama3.1-8b.jsonl |
| RB2 | read-back-before-claim | openrouter free | skipped (no_key, env) | n/a | scenarios/rc1-scenarios-RB2-openrouter.jsonl |
| SK1 (AMAL promoter %) | skepticism | llama3.1:8b | ran | FAIL — known class, concurrence note on R15-DATA-002/003 (DECISIONS 4.15), no fix round | scenarios/rc1-scenarios-SK1-llama3.1-8b.jsonl |
| SK1 | skepticism | openrouter free | skipped (no_key, env) | n/a | scenarios/rc1-scenarios-SK1-openrouter.jsonl |
| SK2 (SIFY ADR ratio, R15-AGENT-090 regression check) | skepticism | llama3.1:8b | ran | PASS — fix holds, `RATIO_UNAVAILABLE` guard fired verbatim | scenarios/rc1-scenarios-SK2-llama3.1-8b.jsonl |
| SK2 | skepticism | openrouter free | skipped (no_key, env) | n/a | scenarios/rc1-scenarios-SK2-openrouter.jsonl |
| SC1a (DAL, fresh ask 1) | self-consistency | llama3.1:8b | ran | PASS (baseline) — resolved "Delta Air Lines, Inc." | scenarios/rc1-scenarios-SC1a-llama3.1-8b.jsonl |
| SC1b (DAL, fresh ask 2) | self-consistency | llama3.1:8b | ran | PASS — same resolution as SC1a | scenarios/rc1-scenarios-SC1b-llama3.1-8b.jsonl |
| SC1c (DAL, same thread follow-up) | self-consistency | llama3.1:8b | ran | FAIL — known class, concurrence note on R15-DATA-002 (DECISIONS 4.15), no fix round | scenarios/rc1-scenarios-SC1c-llama3.1-8b.jsonl |
| SC1 (all 3 asks) | self-consistency | openrouter free | skipped (no_key, env) | n/a | scenarios/rc1-scenarios-SC1a/b/c-openrouter.jsonl |

OpenAI-direct fallback: not invoked — every llama3.1:8b cell that ran produced a scoreable
result (no model-capability dead end that would justify spending from the OpenAI guard), per
the round's "only where both fail for model-capability reasons" instruction.

## Findings summary

Zero items filed in `findings/rc1-scenarios.json` as new_defect/regression/chain/gate8. Two
real, reproducible behaviours surfaced (SK1, SC1c) but both trace to the SAME already-
adjudicated root cause, R15-DATA-002 (critical, blocked_tier4, DECISIONS 4.15: "a bare ticker
that exists in both masters binds silently to the session region... the residual is [a] tool
carrying no region [after another was already resolved]"). Per the round-3 LEAD NOTE point (8)
these are concurrence notes, not fix-round findings:

- **SK1**: `shareholding_pattern(symbol=AMAL)` with no region returned the BSE Amal Ltd
  71.35% figure with no disambiguation of the NASDAQ:AMAL / BSE:AMAL collision, and the model
  overclaimed "verified through multiple sources" after one tool call.
- **SC1c**: within a single thread, turn 1 disambiguated DAL to Delta Air Lines via
  `resolve_symbol(region=US)`; turn 3's `fundamentals(symbol=DAL)` carried no region, silently
  returned the Indian DAL entity's numbers (eps 8.9, pe 5.60, price 49.88 — the exact R15-DATA-013
  repro), and the model narrated them as Delta Air Lines'. R15-DATA-013's own fix (flagging the
  eps/PE mismatch inside the tool result) DID work — the model correctly surfaced the
  discrepancy rather than silently trusting eps=8.9 — but the cross-tool identity carry-forward
  gap (DATA-002's residual) still broke same-thread self-consistency.

Both are written up in full in `logs/rc1-scenarios.md` and should be added as concurrence notes
under R15-DATA-002 (not a new register entry, not a fix round), naming: same class, same
`fundamentals`/`shareholding_pattern` region-less call pattern as the operator's own DECISIONS
4.15 residual description.

## Read-back-before-claim (RB1, RB2) and the SK2 regression check: clean

No ack-less over-claiming observed; the E3.3 grounded-read-back path
(`_grounded_host_action_result` / `dispatched_unconfirmed`) fired correctly both times, and the
model always hedged. `_guard_ratio_claims` (R15-AGENT-090's deterministic backstop) fired
byte-for-byte on the exact original repro prompt — no regression.
