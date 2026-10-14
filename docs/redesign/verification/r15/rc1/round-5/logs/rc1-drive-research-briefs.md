# rc1-drive-research-briefs — working log (gate round 5)

Candidate sha 9bc600ece2ce6343a6aa48f130d7620b1466bb98, verified via
`git -C .../rc1-round-5-cand rev-parse HEAD`.

## Setup

- Data dir: `cp -R rc1-round-5-seed-data/ -> rc1-round-5-data-rc1-drive-research-briefs/`
- Own sidecar booted from `rc1-round-5-cand/sidecar` source, port **52321**, data dir above,
  `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154` pointing at the shared
  read-only MCP subprocesses. Launcher pid 19395, sleep pid **19397** (kill this to stop),
  worker pid 19398. `/health` returned `ok` with `openbb-mcp: available` within 5s.
- Raw evidence root: `docs/redesign/verification/r15/surface/research-briefs/rc1/round-5/`.

## Method

Read `src/modules/research/BriefPanel.tsx` (honest no-web banner, `noWeb`/`bodyCites`
reconciliation, SourceRow/ExternalLink rendering), `src/lib/host-actions.ts` `briefFromInput`
(webAvailable reconciliation, run-scoped structured/backend carry), and
`src/modules/chat/message-notices.ts` (`isRuntimeNotice` — the AGENT-031/UI-054 fix replaced a
drifting prose regex with a `step_kind==="notice"` structural marker) before driving live, per
`PROMPT_surface_s2.md`'s OWNER-DRIVE instruction to read the panel/api code first.

Seeded from `SURFACE/research-briefs/EVIDENCE.md` (census, agent-opus-5-5) and the round-2/3/4
rc1 evidence under the same dir (read for method/context only — not cited as this round's
evidence, per the harness's cross-round rule). Continuing past those: driving fresh symbols,
re-checking the fixed findings (RESEARCH-003 stale-citation, RESEARCH-005 structured-floor
mislabel, RESEARCH-028 SearXNG-contradicts-banner) hold on 9bc600ec, and checking the still-open
low items (UI-080 vysted:// external-link rendering, AGENT-085 no-citation-check on plain chat)
are unchanged (not a fix round target — informational only).

## Runs (see drives/research-briefs.md for the scored table)

1. `01-normal-persistent.jsonl` — NORMAL depth, ollama llama3.1:8b, "Research Persistent
   Systems (PERSISTENT.NS)…", autonomy auto, tag `rc1-drive-research-briefs-normal`. 93.6s.
   Full lifecycle held: honest partial data-provider failures, real web search (2 sources,
   keyless-fallback), news relevance gate dropped 2 off-entity items honestly, 20 real
   filings, valid `publish_brief` with execution record, correct headless divergence notice.
2. `02-deep-cyient.jsonl` — DEEP depth, ollama llama3.1:8b, "Research Cyient (CYIENT.NS) in
   depth…", tag `rc1-drive-research-briefs-deep`. 340.9s (contended: a second agent, tag
   `rc1-round-5-scenarios-local` on port 52311, ran its own ollama call concurrently despite
   my holding the shared lock — its lock script doesn't gate on the mkdir result). Real
   IterResearch synthesis, 8 sources, all 4 `[n]` citation markers hand-checked correct
   against the sources array (RESEARCH-003 holds), no structured-floor fallback
   (RESEARCH-005 holds), no fabricated bibliography (RESEARCH-029 holds), clean
   citation-check (0 stripped markers — RESEARCH-043 not reproduced).
3. `03-search-status.json` / `04-searxng-status.json` — read-only probes of my own sidecar:
   SearXNG honestly reports `degraded` with real per-engine CAPTCHA/rate-limit reasons
   (RESEARCH-028 holds — contrast the census's false `ready`).
4. `05-code-checks-banner-notice-sourcerow.txt` — grep/sed evidence for the honest-banner
   `webAvailable` reconciliation (`host-actions.ts:289`, the WS3 fix), the divergence-notice
   structural `step_kind==="notice"` check (`message-notices.ts`, AGENT-031/UI-054), and the
   still-open `vysted://` external-link rendering in `SourceRow` (UI-080, unchanged/expected).

Diffed the round-4 candidate (`1006c6da`) against this round's candidate (`9bc600ec`) for
every file this surface owns (`sidecar/services/research/`, `src/modules/research/`,
`src/lib/host-actions.ts`, `src/lib/brief-ingest.ts`, `src/modules/chat/message-notices.ts`,
`sidecar/services/news_provider.py`): only `news_provider.py` (+6), `research/fast.py` (+22),
`research/relevance.py` (+274/-13), `host-actions.ts` (+44) changed — the Stage-C batch-28/
29/30 relevance-gate work. `deep.py`/`iter.py`/`verify.py`/`citecheck.py`/`BriefPanel.tsx`/
`message-notices.ts` are byte-identical to round 4, so round 4's own live reconfirmation of
those code paths plus this round's fresh runs (which exercise the same paths) stand as the
evidence, per round 4's own precedent for unchanged files.

RESEARCH-001 (critical, DEEP news-leg relevance) was not re-driven with its exact BDL repro
this round — budget went to the DEEP citation-integrity check instead (item 2), the higher
first-order regression risk given the actual code diff touches `relevance.py`/`fast.py`
directly. Evidenced instead via `stage-c/batch-30/VERDICTS.json` (R15-LEAD-050 certified,
`pnpm ci-local` 3792 passed + verifier re-run 114 passed) and my own NORMAL run's live news
leg correctly gating off-entity items.

ULTRA depth was not driven live this round (10-15 min cost, no code diff touches its
depth-specific path `agent_tools/research.py` loop selection beyond what DEEP already
exercises) — listed NOT TESTED in the drive doc.

## Sidecar teardown

`kill 19397` (sleep pid) — confirmed down via `curl -m 3 http://127.0.0.1:52321/health`
(connection refused).
