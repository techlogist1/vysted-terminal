# rc1 drive — research-briefs (gate round 3)

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52321`
(rc1-round-3-cand source), fresh data dir `rc1-round-3-data-rc1-drive-research-briefs`
(cp of rc1-round-3-seed-data, keyless). Reads to the shared `:52152/:52153/:52154` stack
were not needed — every check this drive ran against my own sidecar. Full log:
`docs/redesign/verification/r15/rc1/round-3/logs/rc1-drive-research-briefs.md`. Raw
evidence: `docs/redesign/verification/r15/surface/research-briefs/rc1/round-3/`.

## Scored table — every register-tracked item this surface owns, census → round 3

| # | Item | Register id | Severity | Round 3 score | Round 3 evidence |
|---|---|---|---|---|---|
| 1 | DEEP/ULTRA citations point at wrong documents | R15-RESEARCH-003 | high | **ok** | BDL DEEP (ctx): 7 sources, `[6]`/`[7]` correctly resolve to vysted://price/fundamentals; CG Power DEEP: 6 in-range markers resolve to filing/structured sources |
| 2 | Local-lane DEEP/ULTRA hits per-call cap, silently ships thin-coverage floor | R15-RESEARCH-005 | high | **ok** | CG Power (ollama llama3.1:8b): real synthesis, `degraded_reason: null`, honest figures (P/E 111.17, market cap ₹139,586cr) — NOT the old "Web coverage... is thin" floor text |
| 3 | ULTRA cross-check mangles every figure that starts a claim line | R15-RESEARCH-004 | high | **ok** | Kaynes ULTRA: 5/5 cross-check figures intact (₹9,604.48 million, ₹38,989.05 million, ₹54,711 million, ₹564.26 million, ₹3,650.0) — none truncated to a suffix |
| 4 | ULTRA cross-check prints AGREE for UNVERIFIED claims | R15-RESEARCH-002 | critical | **ok** | Kaynes ULTRA: all 5 rows correctly UNVERIFIED with an honest "0 independent source(s) found" reason, never a false AGREE |
| 5 | DEEP states rival's order-book win as target's own (critical) | R15-RESEARCH-001 | critical | **ok** | BDL DEEP (ctx): no cross-entity news misattribution; brief honestly states "Current size of BDL's order book remains unavailable" rather than fabricating one |
| 6 | SearXNG reports 'ready' while all engines CAPTCHA-blocked | R15-RESEARCH-028 | medium | **ok** | `/search/searxng/status` on my sidecar → `state: degraded`, per-engine reasons (brave/duckduckgo/startpage blocked), never a false "ready" |
| 7 | 'kept previous' divergence notice not recognised by chat | R15-UI-054 | medium | **ok (code)** | `message-notices.ts` now keys `isRuntimeNotice` on structural `step_kind === "notice"`, not the old prose regex; `agent_runtime.py:1416` emits that step_kind by design. Not re-triggered live (vy.py harness has no ack round-trip for a kept_previous status; same budget tradeoff as prior rounds) |
| 8 | ULTRA ships fabricated References/Merged Sources list | R15-RESEARCH-029 | medium | **ok** | Kaynes ULTRA: 0 model-authored bibliography sections; code read confirms `citecheck.ensure_citation_integrity` calls `strip_model_bibliography` centrally on every published brief |
| 9 | vysted:// sources render as external favicon links | R15-UI-080 | low | **broken (open, expected)** | `BriefPanel.tsx` `SourceRow`/`FaviconDot` unchanged — still an external `<a>` + Google favicon lookup for every source incl. `vysted://`. Register status is `open`; not a regression |
| 10 | Free-model 429 told as "wait a minute" (wrong for shared-pool) | R15-AGENT-027 | medium | **ok** | `--bad-key` openai on my sidecar: "The OpenAI API key was rejected — check it in Settings." (401 branch; 429/free-pool branch not re-induced this round, code path unchanged) |
| 11 | Ollama tool_call_id `''` / constant `__autobrief` breaks host-action acks | R15-AGENT-046 | medium | **ok** | Code read: `agent_runtime.py:2894` mints `f"call_{uuid.uuid4().hex}"` for EVERY tool call regardless of provider before any downstream id use — the Ollama adapter still emits `''` (`ollama.py:243`) but the runtime overwrites it first. Structurally fixed at the correct layer |
| 12 | no-web-honest-banner can never fire | R15-RESEARCH-041 | low | **broken (open, expected)** | `host-actions.ts:287` `webAvailable = sources.length > 0 \|\| input.web_available === true` unchanged. Register status is `open`; not a regression. Header `ProvenanceBadge` still keys off real http(s) URLs (unchanged low-severity mitigation) |
| 13 | openbb-mcp child death → 500 + silent SSE death | R15-LIFECYCLE-005 | high | **ok (code)** | Not re-induced live this round (shared MCP `:52153/:52154` is out of owner-drive scope, read-only); register status `fixed`, no diff to `mcp_client.py`/`streaming.ts` between round-2 and round-3 candidates in this surface's touched-file set |

**11/13 live-or-code-verified ok, 2/13 correctly still open (low severity, no regression).**

## New finding (not in the register)

`rc1-drive-research-briefs:1` (medium, new_defect) — the citation-integrity net's
`MARKER_RE`/`CITE_MARKER_RE` (`\[(\d{1,3})\](?!\()`) only ever recognises a bracket holding
1-3 bare digits. Live this round: CG Power DEEP (llama3.1:8b) published a brief with 6
literal `[vysted://fundamentals/CGPOWER]` tokens — the model wrote the source's internal
scheme URL directly in brackets instead of the correct numeric marker `[7]` — which ships
through both the sidecar's `strip_invalid_markers`/`strip_model_bibliography` pass and the
frontend's identical regex completely unprocessed, exposing an internal URL scheme as dead
text to the user. Not reproduced on the two gpt-4o-mini runs this session (model-dependent
trigger), but the regex gap itself is model-agnostic. Same defect class as
R15-RESEARCH-029 and (independently, not cited as this round's evidence) a prior gate
round's un-register-tracked finding — three distinct non-numeric bracket shapes now
observed across rounds, confirming the fix needs to cover the general case (any bracket a
model writes that isn't a bare in-range integer), not just the specific literal strings
seen so far. See
`docs/redesign/verification/r15/rc1/round-3/findings/rc1-drive-research-briefs.json`.

## Methodology note (not a finding)

The first BDL attempt (`2-deep-bdl-4omini.jsonl`, no context snapshot, generic prompt
phrasing) had gpt-4o-mini answer directly from `fundamentals`+`corporate_announcements`
without ever calling the `research` tool, so no brief published at all —
`options.research_depth` only sets the depth FLOOR used if/when `research` is called
(confirmed by code read, `agent_runtime.py:2752-2763`); it does not force the tool. Re-run
with an explicit "Do a deep research brief" phrasing + a `context_snapshot` naming the
symbol (matching the register's own repro shape, which specifies `symbol=BDL`) reliably
triggered the `research` tool on the retry (`3-deep-bdl-4omini-ctx.jsonl`).

## Environment observation (not a product finding)

The LOCAL-MODEL LOCK protocol (`mkdir /tmp/vysted-r15-ollama.lock`) appeared to not
serialize ollama access across concurrently-running roles in this session: `mkdir`
succeeded immediately when I checked, and my sleep+trap wrapper released it correctly on
exit, but a later check (while my own ollama call was still in-flight) found the lock
directory already absent, and `ps aux` at that moment showed at least two other roles'
`vy.py --provider ollama` processes running at the same time as mine (composer-chat,
rc1-scenarios). This looks like an artifact of per-tool-call sandboxed `/tmp` (each Bash
call's mkdir/rmdir is visible only within that call's own overlay, not to background
processes spawned by an earlier call, nor to other agents' shells) rather than a logic bug
in the lock protocol as specified. Flagged for the lead/harness; not something this role
can fix, and not a product defect.

## Sidecar

Stopped (`kill 74829`, sleep pid) at end of drive.
