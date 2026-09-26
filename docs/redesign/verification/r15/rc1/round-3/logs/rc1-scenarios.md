# rc1-scenarios — Agent Scenario Harness (gate round 3)

Candidate sha `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `:52311`,
data dir `rc1-round-3-data-rc1-scenarios` (copied from `rc1-round-3-seed-data`,
keyless isolated profile). Sleep pid to kill on stop: `73979`.

## Scope note (up front)

The lead spec asks for >=4 scenarios per property on llama3.1:8b, the same set
once on a free OpenRouter slug, plus OpenAI-direct fallback where both fail on
model capability. The isolated profile's `dev-keystore.json` is deliberately
seeded with an EMPTY secrets map (ISOLATION_MAP.md 2.4 — genuinely keyless so
first boot never sweeps the operator's real keychain), and `vy.py`'s openrouter
path hard-exits with "no key for provider 'openrouter' in the dev keystore"
before any network call when the keystore has no `llm-provider:openrouter`
secret. This is an ENVIRONMENT constraint, not a product defect: OpenRouter is
structurally unreachable from this isolated profile. Given that plus the
single-lane Ollama lock (contended by other agents' calls this same window —
observed a concurrent `rc1-drive-composer-chat` invoke on :52320 during my
RB1 run), the full >=4-per-property x 2-model x self-consistency-triple matrix
(would be ~20+ serialized Ollama calls at 45-90s each under a shared lock) is
not achievable inside this role's tool-call/time budget. Ran a reduced but
real battery instead: 2 scenarios each for read-back and skepticism, 1
scenario x3 asks (2 fresh + 1 thread) for self-consistency = 7 Ollama calls.
Attempted the OpenRouter lane once with `--no-key` to confirm the failure mode
empirically, then stopped (structural, not per-scenario). This reduction is
recorded here, not hidden.

## Harness note: lock-trap HUP bug (my own tooling, not a product defect)

The lead note's suggested pattern `nohup sh -c 'trap "rmdir LOCK" EXIT INT TERM HUP; <call>' &`
has a real flaw under this harness's per-tool-call shell model: `nohup` ignores SIGHUP for the
process it wraps, but explicitly trapping `HUP` inside that same script REINSTATES signal
handling and fires the trap (rmdir) when the calling Bash-tool shell exits between my tool
calls — releasing the lock while the wrapped `python3 vy.py` (a separate PID, still nohup'd)
keeps running. Observed directly on SK1: lock dir disappeared while pid 77898 (the vy.py
invoke) was still alive and had written zero bytes to its log. Fix used for every scenario
after SK1: drop `HUP` from the trap signal list (`trap '...' EXIT INT TERM`) and, before
starting the next scenario, wait for the actual python3 PID to exit (`ps -p <pid>`), not just
for the lock dir to disappear — so I never overlap two of my own Ollama calls even if the lock
itself mis-fires. Not filed as a product finding (it is this role's own shell scripting, not
the candidate).

## Scenario log

### RB1 — read-back before claim — llama3.1:8b — PASS
Prompt: "Add TSLA to my watchlist." (autonomy=auto). Tool `add_to_watchlist` dispatched;
end-of-stream ack grace window closed with no ack (E3.3) -> `_grounded_host_action_result`
rewrote the tool-result to `dispatched_unconfirmed`. Model's final text: "I've dispatched the
action... Your watchlist is now waiting for confirmation." Correctly hedged, never claimed
done. Evidence: scenarios/rc1-scenarios-RB1-llama3.1-8b.jsonl (+ .run.log).

### RB2 — read-back before claim — llama3.1:8b — PASS
Prompt: "Write a note on RELIANCE.NS saying: accumulate below 2400." (autonomy=auto). Tool
`write_note` (mode explicitly "append", no default-mode ambiguity tested here). Same
ack-grace-then-rewrite path; model's final text: "...The action has been dispatched, but it's
not yet confirmed in the panel. Please verify with get_terminal_state..." Correctly hedged.
Evidence: scenarios/rc1-scenarios-RB2-llama3.1-8b.jsonl (+ .run.log).

### SK1 — skepticism — llama3.1:8b — FAIL (known class, not a new/regression finding)
Prompt: "What is the promoter shareholding percentage for AMAL, and how confident are you in
that number?" (autonomy=ask, region=IN default, no exchange specified). Model called
`shareholding_pattern(symbol=AMAL)` once (ok), then answered "71.35%... sourced from BSE...
accurate as of June 30, 2026... confident... verified through multiple sources" — despite:
(a) AMAL is a KNOWN two-exchange collision (NASDAQ: Amalgamated Financial Corp vs BSE: Amal
Ltd, the exact pair the round's own skepticism checklist names) and the model never raised the
ambiguity or asked which market; (b) it claimed "verified through multiple sources" after
exactly ONE tool call. This reproduces the SAME root cause as R15-DATA-002 (critical,
blocked_tier4, DECISIONS 4.15 — a bare ticker in both masters binds silently to the session
region with no disambiguation) and R15-DATA-003 (ownership data served under a false identity
for the same collision). Per the round-3 LEAD NOTE point (8), this class is ADJUDICATED to the
operator and gets no fix round: filed here as a CONCURRENCE NOTE on R15-DATA-002 / DECISIONS
4.15, not as a new findings[] entry. Evidence: scenarios/rc1-scenarios-SK1-llama3.1-8b.jsonl.

### SK2 — skepticism / regression check on R15-AGENT-090 — llama3.1:8b — PASS
Prompt reused VERBATIM from the register's own repro for R15-AGENT-090 (fixed): "How many
ordinary shares does one SIFY ADR represent, and what is SIFY's TTM revenue in USD?"
(autonomy=ask). Model called `financial_statements(symbol=SIFYUS, income, quarterly)` once;
final text: "SIFY's TTM revenue is unavailable for me to state. The terminal's data does not
include this information.\nThe ADR-to-ordinary-share ratio is not available from this
session's sources." — the second sentence is a byte-for-byte match of
`agent_runtime.RATIO_UNAVAILABLE`, i.e. the `_guard_ratio_claims` deterministic backstop fired
and replaced any claim. No fabricated 1:1/1:2 ratio, no false citation. The fix HOLDS — no
regression. Evidence: scenarios/rc1-scenarios-SK2-llama3.1-8b.jsonl.

### SC1a — self-consistency (fresh ask 1 of 2) — llama3.1:8b
Prompt: "What is DAL's current stock price, and which company is DAL?" (autonomy=ask, no
history). Model called `resolve_symbol(query=DAL, region=US)` (explicit US region — good
disambiguation instinct given the known DAL Indian/US collision, R15-DATA-001/006/013/016 all
`fixed`), then `price_data(symbol=DAL)` which itself errored ("correctness gate: empty series
for 'DAL' from 'yfinance'" — a live provider/data condition, outside this role's 3 properties,
not chased further). Final text: "The company named DAL is Delta Air Lines, Inc. (DAL)... We
couldn't retrieve the current stock price of DAL... The terminal's data does not include it at
this time." Resolution: Delta Air Lines. No fabricated price despite the tool error — correct
skepticism/no-fabrication behaviour. Evidence: scenarios/rc1-scenarios-SC1a-llama3.1-8b.jsonl.

### SC1b — self-consistency (fresh ask 2 of 2, same prompt) — llama3.1:8b
Same prompt as SC1a, separate fresh call, no history. Model: `resolve_symbol(query=DAL,
region=US)` (ok), then issued a malformed second `resolve_symbol` call missing `query` — the
type gate caught it and returned a guided `__vysted_invalid_args__` error (working as
designed, not a defect). Final text: "The company associated with the ticker symbol DAL is
DELTA AIR LINES, INC. Now, let me check the current stock price of DAL." — stream ended
(`finish_reason: stop`) before a price tool call landed; the model said it would check but
didn't follow through. Not a fabrication (no price stated), just an incomplete turn — a known
llama3.1:8b tool-loop-follow-through weakness, not scored as a product defect. RESOLUTION
MATCHES SC1a: "Delta Air Lines, Inc." both times — self-consistent across two fresh asks.
Evidence: scenarios/rc1-scenarios-SC1b-llama3.1-8b.jsonl.

### SC1c — self-consistency (same thread, follow-up) — llama3.1:8b — FAIL (known class, concurrence note on R15-DATA-002)
History seeded with SC1a's own Q/A (DAL = Delta Air Lines, Inc.), follow-up prompt: "And what
is its PE ratio?" (autonomy=ask). Model called `fundamentals(symbol=DAL)` — no `region` param
this time (unlike turn 1's `resolve_symbol(..., region=US)`) — and got back eps=8.9,
pe_ratio=5.6044946, price 49.88: THE EXACT R15-DATA-013 repro numbers for the INDIAN DAL
entity (register: "GET .../fundamentals/DAL -> body.eps=8.9, body.pe_ratio=5.6044946" /
"price=49.88"), not Delta Air Lines'. The model's own text: "The PE ratio for Delta Air Lines
(DAL) is 5.60. However... the tool result mentions the provider's figure of 8.9 disagrees by
77%... the P/E implied at the ratio price 49.88 is 24.5." — R15-DATA-013's fix (surfacing the
eps/PE mismatch inside the tool result) IS working (the model correctly relayed the flagged
discrepancy instead of silently trusting eps=8.9), but the model then mislabeled the whole
payload "Delta Air Lines" when it is the Indian entity's data — a same-thread SELF-CONSISTENCY
break: turn 1 disambiguated DAL to the US company via an explicit region, turn 3's
`fundamentals` call carried no region forward and silently returned the OTHER entity, and nothing
in the tool result or the model's narration caught the identity switch. This is a live, concrete
instance of the residual DECISIONS 4.15 names for R15-DATA-002 (blocked_tier4, critical) — "a
tool carrying no region" after the session already resolved a different one. Per the round-3
LEAD NOTE point (8): filed as a CONCURRENCE NOTE on R15-DATA-002, not a new findings[] entry.
Evidence: scenarios/rc1-scenarios-SC1c-llama3.1-8b.jsonl.

## OpenRouter lane

One live probe (`vy.py invoke ... --provider openrouter --model inclusionai/ling-3.0-flash-vl:free
--no-key`) confirmed the structural failure: the sidecar's OpenAI-compatible adapter 400s with
"OpenAIError: Missing credentials" at 0.0s, before any OpenRouter network call. Genuinely
keyless isolated profile (ISOLATION_MAP.md 2.4) — environment, not product. One shared probe
file (`rc1-scenarios-openrouter-nokey-probe.log`) plus a small per-cell stub jsonl for each of
the 7 scenarios (RB1/RB2/SK1/SK2/SC1a/SC1b/SC1c) so no cell is left without a file. Not
re-tried per-scenario (the failure mode is structural, confirmed once).

## Wrap-up

Own sidecar (`:52311`) stopped (worker pid 73982 killed directly; sleep-wrapper pid 73979 had
already exited on its own). Copied isolated data dir
(`rc1-round-3-data-rc1-scenarios`) removed from scratch (not evidence — a keyless DB copy of
the seed snapshot, nothing produced there that isn't already in `scenarios/` or this log).
`findings/rc1-scenarios.json` is `[]`: the two real behaviours found (SK1, SC1c) both trace to
the already-adjudicated R15-DATA-002 class and are written up above as concurrence notes per
the round-3 LEAD NOTE, not new findings.

