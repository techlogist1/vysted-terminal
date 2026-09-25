# rc1 drive — research-briefs

Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`. Own sidecar `127.0.0.1:52321`
(rc1-cand source), reads to shared `:52152`/`:52153`/`:52154`, all writes to my own
sidecar only. Full log: `docs/redesign/verification/r15/rc1/logs/rc1-drive-research-briefs.md`.
Raw evidence: `docs/redesign/verification/r15/surface/research-briefs/rc1/`.

## Scored table — every census SURF-RESEARCH-BRIEFS finding, census → rc1

| # | Census finding | Register id | Severity | Census verdict | rc1 score | rc1 evidence |
|---|---|---|---|---|---|---|
| 1 | DEEP/ULTRA `[n]` citations point at wrong documents | R15-RESEARCH-003 | high | broken | **ok** | BDL DEEP: markers `[1]-[8]` all in-range, 0 stripped out-of-range; Kaynes ULTRA: 0 out-of-range of 21 sources |
| 2 | Local-lane DEEP/ULTRA hits 60s cap, silently ships thin-coverage floor | R15-RESEARCH-005 | high | broken | **ok** | CG Power (ollama): real synthesis 36.5s (new 150s cap), `degraded_reason: null`, no floor |
| 3 | ULTRA cross-check mangles every figure | R15-RESEARCH-004 | high | broken | **ok** | Kaynes ULTRA: 40.47%, ₹38.99bn, 8.87%, P/E 68.57 all intact; trace says "0 verified, 5 unverified" (was falsely "verified 5") |
| 4 | SearXNG reports 'ready' while all engines CAPTCHA-blocked | R15-RESEARCH-028 | medium | broken | **ok** | `/search/searxng/status` → `state: degraded`, per-engine reasons |
| 5 | 'kept previous' divergence notice not recognised by chat | R15-UI-054 | medium | broken | **ok** (code) | `message-notices.ts:63-69` keyed on `step_kind:"notice"`; pinned test file present. Not re-triggered live (budget) |
| 6 | ULTRA ships fabricated References/Merged Sources list | R15-RESEARCH-029 | medium | broken | **ok** | citecheck stripped 1 list in BDL/CGPower; Kaynes ULTRA had 0 present, 0 to strip |
| 7 | vysted:// sources render as external favicon links | R15-UI-080 | low | broken | **broken (open, expected)** | `FaviconDot` unchanged — register status is `open`, no closure commit. Not a regression. |
| 8 | Free-model 429 told as "wait a minute" (wrong for shared-pool) | R15-AGENT-027 | medium | broken | **ok** | code table confirms 429+`:free`/`shared_pool` row; live-confirmed the 401-auth row instead (bad-key → honest "API key rejected") |
| 9 | Ollama tool_call_id `''` breaks host-action acks | R15-AGENT-046 | medium | broken | **ok** | both openai + ollama runs: unique `<call-id>__autobrief`, ack 200 ok |
| 10 | DEEP states rival's order-book win as BDL's own (critical) | R15-RESEARCH-001 | critical | broken | **ok** | BDL DEEP: news citation `[8]` = BDL's own ₹811cr MoD contract, Economic Times, on-entity only |
| 11 | no-web-honest-banner can never fire (vysted:// counts as web) | R15-RESEARCH-041 | low | broken | **broken (open, expected)** | `host-actions.ts:287` unchanged — register status is `open`, no closure commit. Not a regression. |
| 12 | Ollama constant `__autobrief` ack id false-confirms later briefs | R15-AGENT-046 | medium | broken | **ok** | same fix as #9 — id is now unique per run, not a shared constant |
| 13 | openbb-mcp child death → 500 + silent SSE death | R15-LIFECYCLE-005 | high | broken | **ok** (code) | `mcp_client.py` ProviderError conversion + `streaming.ts` EOF-without-done handling read; not induced live (shared MCP, out of owner-drive scope) |

**11/13 fixed and verified (9 live-driven, 2 code-verified only), 2/13 correctly still open
(low severity, no regression).**

## New finding (not in census)

`rc1-drive-research-briefs:1` (medium) — the DEEP brief's auto-generated "Coverage note:
... web sources alone" is provably FALSE on the BDL run: the up-front structured snapshot
timed out (correctly triggering the note), but the research loop's own later tool calls
independently populated `findings.structured_sources`, and the brief's headline Stock
Price/Market Cap figures cite `vysted://price` directly — contradicting the note in the same
document. Not present in the CG Power or Kaynes runs (there the loop genuinely found no
structured data either, so the note held). See
`docs/redesign/verification/r15/rc1/findings/rc1-drive-research-briefs.json`.

## Sidecar

Stopped (`kill 69062`, sleep-pipe pid) at end of drive.
