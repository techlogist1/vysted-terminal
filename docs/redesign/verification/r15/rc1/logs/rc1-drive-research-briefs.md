# rc1-drive-research-briefs — working log

Candidate: `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (rc1-cand scratch worktree, sidecars
prebuilt). Own sidecar `127.0.0.1:52321`, cwd `<rc1-cand>/sidecar`, data dir
`scratchpad/rc1-data-rc1-drive-research-briefs` (`cp -R` of `rc1-seed-data`, keyless
`dev-keystore.json`, no `audit_log.db`). MCP env pointed at the shared read-only
`:52153`/`:52154` binaries — never restarted, never written through.

## Setup

- `mkdir -p scratchpad/rc1-data-rc1-drive-research-briefs && cp -R rc1-seed-data/. <that dir>`
- Booted `./.venv/bin/python3 main.py --host 127.0.0.1 --port 52321 --data-dir <that dir>`
  under `sleep 86400 | ...`, sleep-pipe pid 69062, worker pid 69066. `/health` ok in <5s.
- `git merge-base --is-ancestor` confirmed all 6 fix-closure commits
  (806a90c, dcbe7ba, c81d879, 6b70230, f407107, 1574ed8) are ancestors of the candidate HEAD.

## What the census left (13 raw findings, all admitted, all mapped to register ids)

Cross-referenced `census/raw/surf-research-briefs.json` (13 findings) against
`vysted-r15-register.json` by `raw_ids`: 11/13 map to `fixed` entries, 2/13
(SURF-RESEARCH-BRIEFS-7 / R15-UI-080, SURF-RESEARCH-BRIEFS-11 / R15-RESEARCH-041) map to
`open` (both low severity, no closure commit — deliberately not fixed this cycle).

## Drive

Read `src/modules/research/BriefPanel.tsx`, `brief-blocks.tsx`, `src/lib/host-actions.ts`
first. Reused the census's exact repro prompts (same symbols/depths) via
`docs/redesign/verification/r15/surface/research-briefs/harness/turn.py` (the same
frontend-accurate turn/ack player census agent A used), pointed at my own sidecar port:

1. **BDL DEEP, paid gpt-4o-mini** — exact repro of SURF-RESEARCH-BRIEFS-1 (citation
   misattribution) and SURF-RESEARCH-BRIEFS-10 (critical: rival company's news cited as
   BDL's own). 178s, $0.0038. Result: brief cites BDL's own ₹811cr MoD contract (not a
   rival's), 8/8 sources, citation markers `[1]-[8]` all in-range, 0 out-of-range markers,
   1 model-written source list stripped by citecheck. **Both fixed.**
2. **CG Power DEEP, local ollama llama3.1:8b** — exact repro of SURF-RESEARCH-BRIEFS-2
   (local-lane 60s synthesis timeout → false 'thin coverage' floor). 359s. Result: real
   synthesis completed in 36.5s (well under the new 150s local-lane cap),
   `degraded_reason: null`, no floor fallback, no raw unformatted floats. **Fixed.**
3. **Kaynes ULTRA (heavy mode, 3 angles + cross-check), paid gpt-4o-mini** — exact repro
   of SURF-RESEARCH-BRIEFS-3 (cross-check mangles every figure) and
   SURF-RESEARCH-BRIEFS-6 (fabricated References/Merged Sources list). ~284s to first
   publish (killed the process after capture — the agent auto-started a SECOND unsolicited
   research round chasing the open order-book question; not needed for verification).
   Result: cross-check step trace says **'checked 5 numeric claim(s): 0 verified, 5
   unverified, 0 disagreement(s)'** (previously falsely said "verified 5"); every cited
   figure survives intact in the Cross-check section (40.47%, ₹38.99 billion, 8.87%, P/E
   68.57 — none mangled to "47%"/"13953"-style fragments); 0 out-of-range markers, 0
   model-written source lists. **Both fixed.**
4. **`/search/searxng/status`** on my own sidecar — SearXNG state now reports `degraded`
   with per-engine CAPTCHA/suspension reasons instead of a false `ready` while every
   engine is blocked. **R15-RESEARCH-028 fixed.**
5. **`--bad-key` on a research-shaped ask (openai)** — 401 now maps to "The OpenAI API key
   was rejected — check it in Settings." / "Re-enter the API key in Settings." (previously
   a generic wrong "try again"). **R15-AGENT-027 fixed** (code table read confirms the
   other rows: 429+`:free`, 400 model_not_found, context_overflow, Ollama-not-running).
6. **Tool-call-id / ack uniqueness (R15-AGENT-046)** — both the BDL (openai) and CG Power
   (ollama) runs' `publish_brief` tool_call_id was `<unique-call-id>__autobrief`, never the
   old constant `__autobrief`; both acks read back `200 {"ok":true}`. Code:
   `agent_runtime.py:1987` mints a uuid on an empty/duplicate provider id;
   `action_ledger.py` `.pop()`s on read (one-shot). **Fixed.**
7. **R15-UI-054 (divergence notice)** — code-read only (`message-notices.ts:63-69` keys on
   `step_kind:"notice"`, pinned test file present); not re-triggered live (would need a
   manufactured stale-ack race, out of budget after 3 DEEP/ULTRA runs).
8. **R15-LIFECYCLE-005 (openbb-mcp child death)** — code-read only
   (`mcp_client.py` `ProviderError` conversion, `streaming.ts` EOF-without-done handling).
   Not induced live — the openbb-mcp process is the SHARED `:52153` binary and the scope
   rules forbid touching it; this item belongs to a lifecycle/induce role with its own
   isolated MCP subprocess, not owner-drive.
9. **R15-RESEARCH-041 / R15-UI-080 (both open, low)** — confirmed still open, byte-identical
   source to census. Not a regression; matches register status.

## New finding

`rc1-drive-research-briefs:1` (medium, new_defect) — the BDL DEEP brief's auto-appended
"Coverage note: ... web sources alone" is FALSE when the up-front price/fundamentals
snapshot times out (6s) but the research loop's own later tool calls populate
`findings.structured_sources` anyway — the brief then cites `vysted://price` for its
headline Stock Price/Market Cap figures while the note claims "web sources alone". Confirmed
NOT present in the CG Power or Kaynes runs (there both the up-front snapshot AND the later
in-loop structured pulls genuinely returned nothing, so the note is accurate there) — this is
a specific race between `structured_feeds_available()` (up-front snapshot only) and the
final `findings.structured_sources` list (whole-run), not a general defect in the note logic.

## Sidecar stopped

`kill 69062` (sleep-pipe pid) at end of drive.
