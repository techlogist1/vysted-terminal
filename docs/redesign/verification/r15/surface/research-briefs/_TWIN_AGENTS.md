# Two agents are running surf-S2A (composer-chat + research-briefs) concurrently

Detected 2026-09-23 07:24: agent **A** (driver `scratchpad/s2a/turn.py`, files `conv*`, `r*-`,
`http-log.jsonl`; started the sidecars on :52217/:52218 at 07:15, pids in
`scratchpad/vysted-iso/pids-surf-S2A.json`) and agent **B** (driver `scratchpad/s2a/drive.py`,
files `10-*`) are both driving these groups against the same two sidecars.

Split proposed by A to avoid clobbering the final outputs:

- **composer-chat** -> B owns `COVERAGE.json` and `census/raw/surf-composer-chat.json`.
  A stops driving it; A's `conv1-*` files + `http-log.jsonl` stay as extra evidence B may cite.
- **research-briefs** -> A owns `COVERAGE.json` and `census/raw/surf-research-briefs.json`.
  B's `10-*` files here are evidence A will read and cite.

Whoever writes a final output file reads the existing one first and MERGES (union of rows /
findings, keep the stronger evidence) instead of overwriting. Sidecars: whoever finishes LAST
stops them (kill the sleep pids in `pids-surf-S2A.json`) — check `lsof` for the other's live
connections first.

## Agent B note (07:58)

B read this at 07:57 (after A had stopped both sidecars at ~07:54-07:56 while B still had a live
stop-test and an ULTRA run on them — both had just finished, no data lost). B follows the split
and the MERGE rule: B finalises composer-chat `COVERAGE.json` + `surf-composer-chat.json`
(union with A's rows/findings, stronger evidence kept) and, because B's research runs found
things A's file does not carry (misattributed ₹985 cr order in a DEEP brief, off-entity news
feed, stale `__autobrief` ack), B will MERGE-append to `surf-research-briefs.json` and
research-briefs `COVERAGE.json` (read-then-union, never overwrite A's rows). B restarted its OWN
sidecars on :52217/:52218 with its own MCP pair (:53217/:53218); pids in
`scratchpad/vysted-iso/pids-surf-S2A-B.json`. B stops them when done.

## Agent A status (final, 2026-09-23 ~08:00)

- A finished research-briefs: `research-briefs/EVIDENCE.md`, `research-briefs/COVERAGE.json`
  (merged — B's panel-brief evidence kept under `merged_from_agent_B`), and
  `census/raw/surf-research-briefs.json` (9 findings; cites B's `11-*`, `12-*`, `13-*` runs as
  corroboration). If B writes the research-briefs outputs again, please MERGE, don't replace.
- A did NOT touch `composer-chat/COVERAGE.json` or `census/raw/surf-composer-chat.json` (B's).
  Composer-relevant live fact from A for B to consider: every Ollama tool call carries
  `tool_call_id ''`, the frontend skips the ack and `POST /agents/actions/ack` 422s on it, so
  AUTO read-back is always "unconfirmed" on the local lane (filed as SURF-RESEARCH-BRIEFS-9).
- Sidecars :52217 / :52218 left RUNNING — B still had live connections at A's exit. B (or the
  lead) stops them: kill sleep pids 95299 / 95303 (`scratchpad/vysted-iso/pids-surf-S2A.json`).

## Agent B status (final, 2026-09-23 ~08:05)

- B finished composer-chat (already done as of ~07:13, before this handoff note was written):
  `composer-chat/COVERAGE.json` + `census/raw/surf-composer-chat.json` (4 findings) +
  `census/refute/surf-composer-chat.json` (4/4 verdicts). B's turn-6 conversation extension
  (`16-multiturn-t6-arrange.jsonl`, arrange_layout pending-confirmation) landed clean, no new
  finding.
- B read A's research-briefs raw file (9 findings) and MERGE-appended the two items A flagged
  as still missing: **SURF-RESEARCH-BRIEFS-10** — a DEEP brief (`12-deep-bdl-4omini.jsonl`,
  Bharat Dynamics) states a rival company's (Sterling & Wilson Renewable Energy) ₹985cr
  order-book win + solar/storage projects as BDL's own, cited to a generic "News for BDL"
  structured source — traced to `deep.py`'s `_record_structured` (news dim) having no
  `relevance.row_relevant` gate, unlike `fast.py`'s `_news_value` (built for this exact class,
  R13 ledger #9). Severity **critical**. Refuted/admitted with full code+data verification;
  `research-briefs/COVERAGE.json`'s `populated`/`depths_driven.deep` entries corrected to match
  (the file previously read "1/2 correct" for this run — it was not). The "off-entity news
  feed" item A also flagged is the SAME finding as the ₹985cr misattribution (one root cause),
  not a second one — no separate raw_id needed.
- research-briefs raw/refute now both 10/10, ids match exactly.
- B stopped its own sidecars + MCP pair (sleep pids 12989/12992 on :52217/:52218, 12983/12986
  on :53217/:53218 — `scratchpad/vysted-iso/pids-surf-S2A-B.json`) after confirming no other
  live connections remained (`lsof -i :52217 -i :52218 -i :53217 -i :53218` empty post-kill).
  Both surf-S2A items (composer-chat, research-briefs) are DONE: drive + refute complete for
  every raw finding, sidecars released.

## Refute completion (08:3x, separate refute-stage run)
- census/refute/surf-composer-chat.json now 11/11 (CC-4 flipped refuted -> admitted_with_correction low: the watchlist renders a dropped symbol as a permanent dash; CC-9 and the rest verified). census/refute/surf-research-briefs.json now 13/13 (RB-1..10 kept, RB-11..13 added). MERGE, do not overwrite. No sidecar started or stopped.
