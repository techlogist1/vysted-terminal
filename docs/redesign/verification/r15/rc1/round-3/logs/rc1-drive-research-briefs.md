# rc1 drive — research-briefs (gate round 3)

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52321`
(from `rc1-round-3-cand` source), data dir `rc1-round-3-data-rc1-drive-research-briefs`
(fresh `cp -R` of `rc1-round-3-seed-data`, keyless). Reads to shared `:52152/:52153/:52154`
never touched (no reads issued against the shared stack this drive — every check ran
against my own sidecar). Sidecar sleep pid: 74829 (parent sh 74827), started detached,
health confirmed ok.

Method: `scripts/r15/vy.py invoke` (matches the census/round-1/round-2 owner-drive method),
same exact repro prompts as the register's own repro commands for the register-tracked
entries, run fresh against this candidate. Evidence under
`docs/redesign/verification/r15/surface/research-briefs/rc1/round-3/`.

NOTE on LOCAL-MODEL LOCK: `mkdir /tmp/vysted-r15-ollama.lock` succeeded immediately when
checked (no contention observed from this session's vantage), and the sleep+trap wrapper
was used for every ollama-bound call so the lock would release on exit either way. A later
check from a subsequent tool call found the lock directory already absent while my ollama
process was still running, and `ps aux` at the same moment showed at least two OTHER roles'
`vy.py --provider ollama` processes running concurrently with mine (composer-chat,
rc1-scenarios). This looks like an artifact of per-tool-call sandboxed `/tmp` (mkdir/rmdir
visible only within the invoking call's overlay, not to background processes spawned in
an earlier call) rather than a real logic bug in the lock protocol — flagged as a harness
observation, not a product defect, and not something this role can fix.

## Runs

1. `1-deep-cgpower-llama.jsonl` — ollama llama3.1:8b, DEEP, "CG Power and Industrial
   Solutions — order book, margins, and whether the valuation is justified versus peers."
   Real synthesis (backend keyless-fallback, 259s wall — round overran 90s slice, one
   wind-down round), NOT the old structured-floor fabrication. R15-RESEARCH-005 holds.
   6 in-range `[n]` markers resolve correctly to filing/structured sources (no stale-marker
   bug, R15-RESEARCH-003 holds). **New finding**: 6 literal `[vysted://fundamentals/CGPOWER]`
   brackets ship as dead text in the body — see finding below.
2. `2-deep-bdl-4omini.jsonl` — openai gpt-4o-mini, plain prompt, no context snapshot: the
   model answered directly from `fundamentals`+`corporate_announcements` without ever
   calling the `research` tool, so no brief was published. Not a defect (methodology gap on
   my first attempt — `research_depth` only sets the floor depth used IF `research` is
   called, confirmed by code read of `agent_runtime.py:2752-2763`; it does not force the
   tool). Re-run with `--context` (run 3) below.
3. `3-deep-bdl-4omini-ctx.jsonl` — openai gpt-4o-mini, DEEP, with
   `context_snapshot.bySource.__terminal__.focusedSymbol=BDL` + an explicit "Do a deep
   research brief" phrasing. Real IterResearch brief (backend: native, 163s wall), 7
   sources, citations 1-7 all in-range, `[6]`/`[7]` correctly resolve to
   `vysted://price/BDL` / `vysted://fundamentals/BDL`. No cross-entity news misattribution
   (no rival-company order book claimed as BDL's own — R15-RESEARCH-001 holds); the brief
   honestly says "Current size of BDL's order book remains unavailable" instead of
   fabricating one. One claim was softened by the citation audit to
   "(not confirmed in this run)" — the R8 audit pass is live and working. Zero non-numeric
   bracket tokens this run (the `[vysted://...]` defect is llama3.1:8b-specific in this
   sample, not model-agnostic — still a real defect, see below).
4. `4-ultra-kaynes-4omini.jsonl` — openai gpt-4o-mini, ULTRA (heavy), "Research Kaynes
   Technology in depth...". [continuing below once run completes]
5. `4-search-status.json` / `4-searxng-status.json` — direct probes on my own sidecar:
   `/search/status` tier `t1_keyless`; `/search/searxng/status` state `degraded`, honest
   per-engine reasons (brave/duckduckgo/startpage blocked). R15-RESEARCH-028 holds,
   byte-identical behaviour to round 2.
6. `5-badkey-humanize.txt` — `--bad-key` against openai on my own sidecar: "The OpenAI API
   key was rejected — check it in Settings." R15-AGENT-027 (401 branch) holds.

## Code-read confirmations (register-tracked fixes, this candidate)

- R15-UI-054 (kept_previous notice hidden in trace): `message-notices.ts` now uses
  `isRuntimeNotice(stepKind) => stepKind === "notice"`, a structural check, not the old
  prose `DIVERGENCE_RE`; `agent_runtime.py:1416` documents `step_kind="notice"` (C9). Fixed
  as designed.
- R15-RESEARCH-004 (cross-check mangles digits): `verify.py`'s claim splitting is now its
  own `_split_claims`/`_CLAIM_MARKER` (`^(?:[-*•]|\d+[.)])\s+`, REQUIRES trailing
  whitespace) — separate from `deep._split_subquestions`. "40.5%"/"-0.4%" no longer parse
  as list markers. Fixed.
- R15-RESEARCH-002 (false AGREE over UNVERIFIED): `verify._parse_verdict` defaults to
  UNVERIFIED, requires an explicit leading/standalone verdict word. Fixed.
- R15-AGENT-046 (Ollama '' tool_call_id / constant `__autobrief`): `agent_runtime.py:2894`
  now mints `f"call_{uuid.uuid4().hex}"` for EVERY tool call regardless of provider, before
  any downstream id use (comment cites R15-AGENT-046 by name). The Ollama adapter itself
  (`ollama.py:243`) still emits `''`, but the runtime overwrites it before it can propagate
  — the fix is at the right layer (provider ids are never trusted). Fixed.
- R15-RESEARCH-029 (fabricated Merged Sources/References list):
  `citecheck.ensure_citation_integrity` calls `strip_model_bibliography` then
  `strip_invalid_markers` centrally on every published brief. Fixed.
- R15-UI-080 (vysted:// sources render as external favicon links): `BriefPanel.tsx`
  `SourceRow`/`FaviconDot` unchanged — still renders every source incl. `vysted://` as an
  external anchor + Google favicon lookup. Confirmed still open (low), matches register, not
  a regression.
- R15-RESEARCH-041 (no-web banner can never fire): `host-actions.ts:287`
  `webAvailable = sources.length > 0 || input.web_available === true` unchanged. Confirmed
  still open (low), matches register, not a regression. (The header `ProvenanceBadge` keys
  off actual http(s) URLs, not `webAvailable`, so the low-severity downgrade from round 2's
  correction still applies — no reader-facing regression.)

## New finding — non-numeric bracket citation tokens still ship unprocessed

Same root defect class as round 2's unregistered `rc1-drive-research-briefs:2` (which is
NOT this round's evidence — cited only as the same class, re-derived fresh here): the
citation-integrity net's `MARKER_RE = re.compile(r"\[(\d{1,3})\](?!\()")` in
`sidecar/services/research/citecheck.py:37` and the frontend's identical
`CITE_MARKER_RE` in `src/lib/brief-ingest.ts:396` only ever recognise a bracket holding
1-3 bare digits. `strip_invalid_markers`/`strip_model_bibliography` (the ONLY citation
cleanup pass, `citecheck.py:311-313`) therefore never touches any other bracketed token a
model writes. Live evidence this round: run 1 (CG Power, llama3.1:8b, DEEP) published a
brief with **6 literal instances of `[vysted://fundamentals/CGPOWER]`** in the body
(`### Order Book and Valuation` and `### Financial Performance` sections) — the model wrote
the internal `vysted://` scheme URL directly inside brackets instead of using the correct
numeric marker (`[7]`, which the SAME brief's own sources array maps to
`vysted://fundamentals/CGPOWER`). This ships as dead, confusing bracket text with an
internal URL scheme exposed verbatim to the end user — neither a working citation nor
readable prose. Not reproduced in the BDL DEEP (gpt-4o-mini) or the Kaynes ULTRA runs this
session, so the trigger looks model-quality-dependent (weak local model), but the citation
net's regex gap is unconditional and any brief in any lane can ship the same failure shape.
Medium severity, new_defect (not register-tracked): every-figure-traceable is broken by an
unrecognisable citation exactly like the R15-RESEARCH-029 class, just a different literal
shape (a scheme URL instead of a comma-group or "[New findings]").

## Sidecar

Stop command recorded, run at the end of this drive: `kill 74829`.

### Run 4 completion — Kaynes ULTRA

`4-ultra-kaynes-4omini.jsonl` — openai gpt-4o-mini, ULTRA/heavy (3 parallel angles +
cross-check + merge), 276s wall. Published brief: 31 sources, citations `[1]`-`[31]` all
in-range, ZERO non-numeric bracket tokens, ZERO model-authored bibliography section.
Cross-check section: 5 rows, ALL figures intact — "₹9,604.48 million", "₹38,989.05
million", "₹54,711 million", "₹564.26 million", "₹3,650.0" — none mangled to a truncated
suffix (would have been "604.48"/"38.05"/etc under the old bug). All 5 rows correctly
UNVERIFIED (own-web-search-for-independent-confirmation returned 0 sources this run — an
honest "0 independent source(s) found", not a false AGREE). R15-RESEARCH-002 and
R15-RESEARCH-004 both hold live on a THIRD independent model+depth combination this round
(prior evidence: direct `_split_claims`/`_parse_verdict` code read + the two DEEP runs
above never triggered ULTRA's own cross-check path).

## Spend

Ledger tag `rc1-r3-drive-research-briefs`: 5 calls, $0.011313 total (1 bad-key call
$0, 1 wasted no-context BDL run $0.002443, 1 ollama CG Power $0 (free/local), 1 BDL-ctx
$0.004298, 1 Kaynes ULTRA $0.004572). Well under budget.

## Sidecar

Stopped: `kill 74829` (sleep pid) at end of drive.
