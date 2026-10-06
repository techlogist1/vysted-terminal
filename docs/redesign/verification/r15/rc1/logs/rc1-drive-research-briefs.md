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

---

# Round 2 — gate round 2, candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`

297 commits landed between round 1's candidate (`4097dac4`) and this one, including
batch-24 (LEAD-035), the figure-grounding module (LEAD-030), and real fixes touching the
research pipeline directly: `sidecar/services/research/{deep,fast,iter,finance,verify}.py`,
`sidecar/services/agent_tools/research.py`, `sidecar/services/correctness_gate.py`. Diffed
every non-doc file between the two shas first (`git diff --name-only 4097dac4 4c6dfe8c --
src sidecar src-tauri types plugins`) to scope what could regress before re-driving.

## Setup

- Fresh `cp -R rc1-seed-data/. scratchpad/rc1-data-rc1-drive-research-briefs-r2` (round 1's
  data dir left untouched).
- Booted `<rc1-cand>/sidecar/.venv/bin/python3 main.py --host 127.0.0.1 --port 52321
  --data-dir <r2 data dir>` under `sleep 86400 | ...`, sleep-pipe pid 59740, worker pid
  59743. `/health` ok in <5s (confirms `openbb-mcp: available`).
- `git rev-parse HEAD` on the `rc1-cand` scratch worktree confirmed
  `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (the RC1 GATE FACTS candidate sha).

## What changed in-scope for this group (file-level, not doc-level)

- `sidecar/services/research/deep.py` — `structured_source_gathered()` added and wired into
  `web_only_floor_note()` (commit `83ec78e8`, filed against **my own round-1 finding**
  `rc1-drive-research-briefs:1`); `leading_token()` gained list-marker/label-word skipping
  (R15-RESEARCH-002/034 first-token convention).
- `sidecar/services/research/verify.py` — `_parse_verdict` reads the leading token only
  (R15-RESEARCH-002, **critical**); a dedicated `_split_claims` no longer eats a leading
  decimal integer or a leading minus sign (R15-RESEARCH-004).
- `sidecar/services/research/finance.py` — IR-host authority tightened, PSL registrable-domain
  check (R15-RESEARCH-007).
- `sidecar/services/research/fast.py` / `iter.py` — snapshot leg timebox is now
  caller-supplied; DEEP/ULTRA/Tier B callers pass 25s instead of FAST's 6s
  (`rc1-battery-4:1`, a battery-round finding from a sibling role).
- `sidecar/services/agent_tools/research.py` — `financial_statements` carries its reporting
  currency (`rc1-scenarios:5`, not in this group's scope but touches a shared tool).
- New `sidecar/services/figure_grounding.py` (369 lines, R15-LEAD-030) — **checked and it is
  wired ONLY into `agent_runtime.py`'s streaming-chat figure guard**, not into
  `research/{deep,fast,iter}.py`'s synthesis path. No brief-pipeline regression surface from
  this module. LEAD-030 is `blocked_tier4` per the operator's Gate Round 2 note — out of
  scope for a fix round; noted here only to rule out a regression path, not reopened.
- `src/lib/host-actions.ts` / `src/modules/chat/streaming.ts` — small unrelated diffs
  (`region` param for chart ticker chips / R15-DATA-002; a new `tool_result` stream-event
  normalizer for the agent bus). Neither touches the brief-ingest/webAvailable logic.
  `src/modules/chat/message-notices.ts` — **0 diff**, byte-identical to round 1.

## Drive (candidate `4c6dfe8c`)

Fresh own sidecar (`127.0.0.1:52321`, data dir `rc1-data-rc1-drive-research-briefs-r2`), same
`harness/turn.py` player, same three repro shapes as round 1 (BDL DEEP paid, CG Power DEEP
local-ollama, Kaynes ULTRA paid), plus direct code-level repros of the register's own repro
commands for the three research-pipeline fixes that landed since round 1:

1. **Direct code repro, no network** — `services.research.verify._parse_verdict` on the
   register's exact three previously-mangled strings ("UNVERIFIED - no source confirms...",
   "...evidence does not support...", "...no matching figure") → all three now parse
   `('unverified', ...)`, never falsely `agree`. **R15-RESEARCH-002 (critical) fixed.**
   `services.research.finance.domain_tier` on the register's exact URLs → Medium/WordPress
   IR-shaped URLs now tier 3 (below Reuters' tier 2, TIER_PRIMARY=1). **R15-RESEARCH-007
   fixed.** `services.research.verify._split_claims` on the register's exact three mangled
   inputs ("1. 40.5% revenue growth", "- -0.4% earnings growth", "2. 67.13953 P/E") → all
   three survive with the sign/leading-digit intact. **R15-RESEARCH-004 fixed.**
   `sidecar/tests/test_research_verify.py`: 25/25 passed.
2. **BDL DEEP, paid gpt-4o-mini** (`r2/1-deep-bdl-4omini.stdout.txt`, 178s) — 32 sources,
   markers `[1]`, `[6]`, `[11]` all resolve to plausible provenance (a live NSE quote page
   for price/mcap/P/E, a filing for revenue growth) — no cross-entity misattribution
   (**R15-RESEARCH-001/003 hold**). `publish_brief` ack `200 {"ok":true}`, id
   `call_...__autobrief` (unique) — **R15-AGENT-046 holds**. No `note` field fired (structured
   snapshot succeeded this run, so the fixed `structured_source_gathered()` branch wasn't
   exercised at its exact race window — code-verified instead, see below).
3. **CG Power DEEP, local ollama llama3.1:8b** (`r2/2-deep-cgpower-llama.stdout.txt`, ~310s
   wall, synthesis latency **45032 ms**) — real synthesis well under the new 150s cap,
   `degraded_reason: null`, honest "order book is not explicitly mentioned in the provided
   sources" instead of the old fabricated-floor text, correctly formatted percentages (14.0%,
   not "0.14%"). **R15-RESEARCH-005 holds**, and markedly cleaner than round 1 (that run
   fabricated raw floats; this one admits the gap honestly). Ack `200 {"ok":true}`, unique id.
4. **Kaynes ULTRA, paid gpt-4o-mini, heavy mode** (`r2/3-ultra-kaynes-4omini.stdout.txt`,
   266s to first publish; killed after capture — same known secondary-research-round
   behaviour as round 1, harmless) — cross-check step: **"checked 5 numeric claim(s): 0
   verified, 5 unverified, 0 disagreement(s)"**, every cited figure intact in both body and
   cross-check (40.5%, ₹9,604.48 million, 5.87%, ₹245.36 billion) — **R15-RESEARCH-002
   (critical) and R15-RESEARCH-004 hold live**, matching the direct code repro. Zero
   model-authored "Merged Sources"/"References" section — **R15-RESEARCH-029 holds**, cleaner
   than round 1 (which still had a stripped bibliography list; this run has none to strip).
5. **`/search/status` + `/search/searxng/status`** on my own sidecar — `searxng/status` still
   reports `state: degraded` with per-engine CAPTCHA/suspension reasons. **R15-RESEARCH-028
   holds** (byte-identical behaviour to round 1).
6. **`--bad-key` on openai** — 401 still maps to "The OpenAI API key was rejected — check it
   in Settings." / "Re-enter the API key in Settings." **R15-AGENT-027 holds.**
7. **R15-UI-054 / R15-LIFECYCLE-005** — code-read only, both files byte-identical to round 1
   (`message-notices.ts` 0 diff; `mcp_client.py`/`streaming.ts`'s EOF handling unchanged
   apart from the unrelated `tool_result` event addition). Not re-triggered live, same budget
   tradeoff as round 1.
8. **R15-RESEARCH-041 / R15-UI-080 (both open, low)** — `host-actions.ts`'s `webAvailable`
   calc and `BriefPanel.tsx`'s `FaviconDot` are functionally unchanged. Confirmed **still
   open**, matches register status, not a regression.
9. **My round-1 finding, `rc1-drive-research-briefs:1`** — **FIXED**, commit `83ec78e8`
   ("web-only coverage note honours researcher-gathered price/fundamentals sources"),
   directly citing my raw id in the commit message. `structured_source_gathered()` now checks
   `findings.structured_sources` (whole-run) in addition to the up-front snapshot before
   appending the web-only-floor note. Code-verified; this round's BDL run didn't hit the
   exact race window live (its up-front snapshot succeeded), so the fix's other branch wasn't
   independently exercised end-to-end this round — the diff itself is unambiguous, and the
   commit message names the exact raw id it closes.

## New finding (round 2, not in the register)

`rc1-drive-research-briefs:2` (medium, new_defect) — the citation-integrity net
(`citecheck.py` `MARKER_RE`, `brief-ingest.ts` `CITE_MARKER_RE`) only recognises a bracket
containing 1-3 bare digits. Two DIFFERENT models, in two DIFFERENT runs this session, each
wrote a bracketed token outside that shape, and both shipped through completely unprocessed:
BDL's brief has four literal `[New findings]` tokens (a synthesis-prompt section label the
model reused as a pseudo-citation); Kaynes's brief has `[2, 3]` and `[2, 4]` (a natural
multi-source citation grouping). Direct repro: `MARKER_RE.findall('[2, 3]')` → `[]` — neither
`strip_invalid_markers` (only touches matches of the same regex) nor
`strip_model_bibliography`'s `_N_LITERAL_RE` (only catches the literal string `"[n]"`) nor
`brief-ingest.ts`'s renderer ever touches these tokens; they print as dead bracket text in
the shipped brief. Same defect CLASS as R15-RESEARCH-029 ("literal `[n] k` markers... the
citation check never inspects them") reappearing in a shape the fix wasn't written against —
filed as its own finding rather than folded into 029 since that entry is `fixed`/closed and
this is a materially different bracket shape. See
`docs/redesign/verification/r15/rc1/findings/rc1-drive-research-briefs.json`.

## Sidecar stopped (round 2)

`kill 59740` (sleep-pipe pid) at end of drive.
