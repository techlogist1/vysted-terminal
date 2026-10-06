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

---

# Round 2 — gate round 2

Candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (297 commits past round 1's `4097dac4`,
including batch-24/LEAD-035 and real research-pipeline fixes). Own sidecar `127.0.0.1:52321`
(rc1-cand source, fresh data dir `rc1-data-rc1-drive-research-briefs-r2`), reads to shared
`:52152`/`:52153`/`:52154`. Full log:
`docs/redesign/verification/r15/rc1/logs/rc1-drive-research-briefs.md` (round 2 section).
Raw evidence: `docs/redesign/verification/r15/surface/research-briefs/rc1/r2/`.

## Scored table — round 1 → round 2 (candidate → candidate)

| # | Item | Register id | Severity | Round 1 (`4097dac4`) | Round 2 (`4c6dfe8c`) | Round 2 evidence |
|---|---|---|---|---|---|---|
| 1 | DEEP/ULTRA `[n]` citations point at wrong documents | R15-RESEARCH-003 | high | ok | **ok** | BDL DEEP: 32 sources, `[1]`/`[6]`/`[11]` all resolve to plausible provenance, no cross-entity mix-up |
| 2 | Local-lane DEEP/ULTRA hits 60s cap, silent thin-coverage floor | R15-RESEARCH-005 | high | ok | **ok** | CG Power (ollama): synthesis 45.0s, `degraded_reason:null`, honest "not explicitly mentioned" instead of a fabricated floor (cleaner than round 1) |
| 3 | ULTRA cross-check mangles every figure | R15-RESEARCH-004 | high | ok | **ok** | Direct `_split_claims` repro + live Kaynes run: 40.5%, ₹9,604.48M, 5.87%, ₹245.36bn all intact |
| 4 | ULTRA cross-check prints AGREE for UNVERIFIED claims | R15-RESEARCH-002 | **critical** | (not separately scored r1) | **ok** | Direct `_parse_verdict` repro on the register's 3 exact strings: all `unverified`, never falsely `agree`; live Kaynes: "0 verified, 5 unverified" |
| 5 | IR-host heuristic ranks Medium/WordPress as PRIMARY | R15-RESEARCH-007 | high | (not separately scored r1) | **ok** | Direct `domain_tier` repro on the register's exact URLs: Medium/WordPress tier 3, below Reuters (tier 2) |
| 6 | SearXNG reports 'ready' while all engines CAPTCHA-blocked | R15-RESEARCH-028 | medium | ok | **ok** | `/search/searxng/status` → `state: degraded`, per-engine reasons, byte-identical to r1 |
| 7 | 'kept previous' divergence notice not recognised by chat | R15-UI-054 | medium | ok (code) | **ok (code)** | `message-notices.ts` 0 diff between candidates; not re-triggered live (budget), same as r1 |
| 8 | ULTRA ships fabricated References/Merged Sources list | R15-RESEARCH-029 | medium | ok | **ok** | Kaynes ULTRA: 0 model-authored bibliography sections (cleaner than r1, which still stripped one) |
| 9 | vysted:// sources render as external favicon links | R15-UI-080 | low | broken (open, expected) | **broken (open, expected)** | `FaviconDot` unchanged; register status still `open`. Not a regression. |
| 10 | Free-model 429 told as "wait a minute" | R15-AGENT-027 | medium | ok | **ok** | `--bad-key` openai: "API key was rejected — check it in Settings." |
| 11 | Ollama tool_call_id `''` breaks host-action acks | R15-AGENT-046 | medium | ok | **ok** | BDL (openai) + CG Power (ollama): unique `<call-id>__autobrief`, both ack `200 ok` |
| 12 | DEEP states rival's news as target's own (critical) | R15-RESEARCH-001 | critical | ok | **ok** | BDL DEEP: all citations on-entity, no rival-company contamination |
| 13 | no-web-honest-banner can never fire | R15-RESEARCH-041 | low | broken (open, expected) | **broken (open, expected)** | `host-actions.ts` webAvailable calc unchanged; register status still `open`. Not a regression. |
| 14 | openbb-mcp child death → 500 + silent SSE death | R15-LIFECYCLE-005 | high | ok (code) | **ok (code)** | Files byte-identical to r1 apart from an unrelated `tool_result` event addition in `streaming.ts` |
| 15 | **[round 1 own finding]** Coverage note false when snapshot times out but researcher-gathered data lands later | rc1-drive-research-briefs:1 | medium | **new_defect (broken)** | **FIXED** | Commit `83ec78e8` names the raw id directly; `structured_source_gathered()` wired into `web_only_floor_note()`. Code-verified (exact race window not re-hit live this round). |

**14/14 register-tracked items hold (12 ok/fixed incl. 2 critical, 2 correctly-still-open low
severity); 1/1 of round 1's own new finding is now fixed.**

## New finding (round 2, not in the register)

`rc1-drive-research-briefs:2` (medium) — the citation-integrity net only recognises a bracket
holding 1-3 bare digits. Two different runs this session, two different models, each wrote a
bracketed token outside that shape and both shipped through completely unprocessed: BDL's
brief has four literal `[New findings]` pseudo-citations (reused from the internal
"New findings this round:" working-report label); Kaynes's brief has `[2, 3]`/`[2, 4]`
multi-source groupings. `MARKER_RE.findall('[2, 3]')` → `[]` on both `citecheck.py` and
`brief-ingest.ts` — neither the out-of-range stripper, the model-bibliography stripper, nor
the panel's citation-chip renderer ever touches these tokens; they print as dead bracket text
in the shipped brief. Same defect class as R15-RESEARCH-029, a shape its fix wasn't written
against. See `docs/redesign/verification/r15/rc1/findings/rc1-drive-research-briefs.json`.

## Sidecar (round 2)

Stopped (`kill 59740`, sleep-pipe pid) at end of drive.
