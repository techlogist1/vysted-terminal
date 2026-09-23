# R15 Gate 2 — Evidence Sheet

Read-only verification run, branch `004-r4-experience-rebuild`. This sheet consolidates the
census, the register, the coverage map, the four named lists, the drift report, the battery
diffs and the ranked backlog into the single evidence packet for the Gate 2 decision.

## 0. The "stuck at 77/78 agents" question

Already resolved before this build stage ran — see `docs/redesign/verification/vysted-r15-run-state.md`
entry "L16 (12:36-12:45)". The 77/78 hold was the L6 lifecycle worker (`lifecycle/L6-longsession.md`)
running a slow ~3h20m soak test against its own sidecar (port :52229), sampling in 540s steps — not
a hang. The workflow was stopped and L6 was finished from the soak's log (`lifecycle/L6-longsession.md` §8):
`LIFE-L6-LONGSESSION-1`, a real main-thread CPU burn whose source is measured but not yet
attributed, carried forward as an open finding, not a stall. **Correction (Gate 2 verifier, 13:25 IST):
the soak itself has NOT completed** — pid 64697 is still running detached (`DURATION_S=12000`, ends
≈15:49 IST), `soak-status.json` fresh at cycle 57 / 3,365 s, so it is progressing, not hung; its
sidecar on :52229 sits at ~60% CPU, which is the LIFE-L6-LONGSESSION-1 burn itself. The ≥3 h verdict
in L6 §8 stays pending until the soak ends.

## 1. Census — items done

24/24 Stage-B census items are complete, per the register-rebuild pass (2026-09-23) reflected in
`stage0/CENSUS_COMPLETENESS.md`. Both gaps the prior Gate 2 verifier pass recorded are now closed:
the refute stage for `surf-S2C` (`surf-portfolio-notes`, `surf-settings-plugins`, 8 + 7 raw
findings, closed earlier — `census/refute/surf-portfolio-notes.json`,
`census/refute/surf-settings-plugins.json`), and the **intent census, previously only 13 of 23
chunk ledgers** — the remaining 10 (`blueprint-288`, `deferred-42`, `spec-0`, `spec-45`,
`pdd-readme-90/135/180/225/270/315`) have since landed on disk, non-placeholder (`spec-90`
45/45 rows, `spec-180` 41/41 rows), giving **23/23 intent chunk ledgers** (19 chunks + 4 promise
files). Full item-by-item table: `stage0/CENSUS_COMPLETENESS.md`.

Paths of record: `census/raw/*.json` (99 files, code/data/intent/world/seat findings),
`census/refute/*.json` (98 verdict files; `code-brokers-adapters.json` is the one raw file with
no refute file by design — bulk-closed as removed-with-the-feature per the 23 Sep trading
removal), `census/merge/` + `census/merge-in/` (13 cluster merges), `census/intent/` (23/23 chunk
ledgers: 19 chunks + 4 promise files, `census/PROMISE_LEDGER.md`), `census/world/` (3 research docs + 3
COMPARE docs + `opp-ledger-verify.md`), `invent/ideas/` (8 seats) + `invent/BACKLOG.md`/`.json`
(58 ranked items), `lifecycle/L1-stranger.md`..`L6-longsession.md` (6 stages), `battery/packs/`
+ `battery/collected/` + `battery/diffs/` (24 slots), `surface/*/COVERAGE.json` (8 surface dirs).

## 2. Register — raw / verdict / entry / rejection counts

`vysted-r15-register.json` (rebuilt via `scripts/r15/register.py build` on 2026-09-23 after the
19 remaining intent chunks + assorted delta merges landed; refuses on any unaccounted raw id —
ran clean, 0 unaccounted, 0 phantom):

- **878 raw findings** across 99 files -> **878 explicit refuter verdicts** (98 refute files;
  `code-brokers-adapters.json` findings bulk-closed without a refute file, by design).
- **596 register entries**: critical 16, high 103, medium 265, low 212.
- **75 rejections**: 48 refuted (a refuter verdict of `refuted`, reason carried from the
  refuter) + 24 `removed_with_feature` verdicts (trading removal, operator decision 23 Sep 2026,
  including `code-brokers-adapters.json`) + 3 merger out-of-scope/not-a-defect rejections
  (`INT-blueprint-96-5` dark-only theme; `INT-spec-180-181` and `INT-spec-180-206`, both
  verification-paperwork gaps rather than product defects, surfaced by the newly-landed
  `spec-180` chunk).
- 803 raw ids cited by exactly one entry + 75 rejected = 878; none cited twice, none both.

35 entries are new since the prior build (561 -> 596), all additions, 0 removed: 8 in agent
(`R15-AGENT-080..087`), 6 in code-platform (`R15-CODE-PLATFORM-071..076`), 2 in data
(`R15-DATA-110/111`), 10 in docs (`R15-DOCS-015..024`), 1 in release (`R15-RELEASE-012`), 1 in
research (`R15-RESEARCH-042`), 7 in ui (`R15-UI-083..089`) — drawn from the newly-landed intent
chunks and delta cluster merges.

By flat area: research 53, code 189, data 104, agent 82, ui 108, lifecycle 17, release 16,
docs 27 (sums to 596; code/lifecycle/release/docs are cross-cutting findings that don't carry
one of the operator's four area tags).

By operator area (an entry can carry more than one, see `NAMED_LISTS.md`, regenerated in this
pass): UI and panels 232, Agent and chat 210, Research and web search 128, Data on small or
obscure stocks 106 (125 entries carry no operator-area tag and are excluded from the four lists
by design).

Full severity-ranked view: `docs/redesign/verification/vysted-r15-register.md`.

## 3. Coverage map — cell tallies

`r15/COVERAGE_MAP.json`/`.md`, built from `stage0/COVERAGE_SKELETON.json` (101 surfaces)
enriched by the 8 surface `COVERAGE.json` files, existing repo test files, and explicit
per-surface fallbacks where neither existed:

- **101 surfaces, 288 state-cells.**
- **driven: 243** (evidence-backed — live probe, vitest suite, or a surface census's
  `states_seen`/row-level result).
- **NOT TESTED: 14** (each with a stated reason — no probe, no test file, or a deliberately
  unexercised mutating/live-session endpoint, e.g. the kill switch's `fired` state).
- **NEEDS-MANUAL-CHECK: 22** (genuinely GUI/OS-only: canvas gesture drag, the real OS-global
  kill-switch shortcut, real desktop-notification delivery — for the operator).
- **removed with the feature: 9** (all 4 states of `safety-order-confirmation-dialog`, the
  §6.5 order-confirmation gate, plus the 3 `panel-broker-connect` and 2 `panel-broker-order-entry`
  cells — the surface census already recorded those as removed_with_feature; the first build of
  this map had them as NOT TESTED with the skeleton note as the "reason". Fixed by the Gate 2 verifier,
  which also restored the real NOT TESTED reasons for `charts-toolbar-sync-menu`,
  `market-session-indicator` and `panel-sec-filings` error).

No cell is blank. Full per-surface, per-state detail with evidence paths: `r15/COVERAGE_MAP.md`.

## 4. The four named lists

`r15/NAMED_LISTS.md`, severity-ranked, one-line repro each, drawn straight from the register
(regenerated 2026-09-23 alongside the register rebuild):

- **UI and panels — 232** (critical/high/medium/low breakdown in the doc)
- **Agent and chat — 210**
- **Research and web search — 128**
- **Data on small or obscure stocks — 106**

(These sum to more than 596 because an entry can carry more than one area tag; 125 entries carry
none and are pure code/lifecycle/release/platform findings, excluded from the four lists by
design.)

## 5. Drift report

`r15/DRIFT_REPORT.md` consolidates `stage0/DRIFT_DEPS.md`, `stage0/DRIFT_WORLD.md`, the licence
audit (`surface/licence-audit/*.json`) and what changed since the R13 baseline. Headlines:

- 2 rotted world items needing a code change (Yahoo httpx TLS-fingerprint block on the screener
  fast path; one retired-but-mitigated Sonar model slug), 6 at-risk items, the rest verified
  healthy live.
- Dependency top-10: `@tiptap/core` (1 HIGH + 1 MODERATE, fix available), Python `cryptography`
  2 majors behind (3 HIGH, highest-leverage single bump), `fastmcp` major (only fix path for 3
  HIGH `mcp` SDK CVEs), `anthropic`/`openai` SDKs both a major behind, `google-genai`'s unpinned
  floor (reproducibility gap), `jugaad-data` drift risk, a Windows-specific `starlette` HIGH, a
  Rust `rustls` CVE on the updater path, a `keyring` major (already bit this repo once), and an
  abandoned `autobahn` on the broker path.
- Licence audit: all JS/Rust production dependencies are permissive; the Python sidecar closure
  carries 9 AGPL-3.0 entries from `openbb-mcp`/`sec-edgar-mcp` plus one plain-`GPL` package
  (`Unidecode`, via `sec-edgar-mcp`) — copyleft sidecar binaries shipped inside a core that is now
  PolyForm Strict 1.0.0 (D83, `0c63d46`) + commercial, so this is a Tier-4 licensing question for
  the operator, not "consistent with the project's AGPL track" (stale pre-D83 wording, corrected); several packages carry no
  machine-readable licence metadata and need a manual check before a public release.
- Since R13: the hostile-data battery deliberately sampled 27 *new* names rather than re-testing
  R13's 17; the Tongyi/deepresearch backend documented in CLAUDE.md no longer exists in code
  (docs are stale, not the code); the entire broker/order surface is now scoped out
  (operator decision 23 Sep, after R13); worktree salvage confirmed every R13-era branch with
  live work was already superseded on `004`.

## 6. Battery diff summary

`r15/BATTERY_DIFFS.md`: 24 slots (20 primaries + 4 spares), 943 fields diffed against outside
sources — match 367, app blank 249, mismatch 120, no source truth 115, definitional difference
62, as-of skew 25, not collected 5. The spec-mandated "subtle tier" (as-of dates on 52w
highs/lows, zero-is-real values — the gameable class) shows 2 mismatches + 9 app-blank out of 11
explicitly flagged cells. Every DAT-* raw finding id is cross-referenced per slot in the doc.

## 7. Ranked backlog & promise ledger

- Ranked backlog: `r15/invent/BACKLOG.md`/`.json` — 58 ranked build items from 70 seat ideas (8
  seats) + 6 surviving Tier-A world-opportunities, every input traced in the source index.
- Promise ledger: `r15/census/PROMISE_LEDGER.md` — the spec/blueprint/deferred/pdd-readme
  promise census. **Now complete: 23/23 chunks on disk**, non-placeholder — the 10 that were
  missing (`blueprint-288`, `deferred-42`, `spec-0`, `spec-45`,
  `pdd-readme-90/135/180/225/270/315`) have landed, and `spec-90` (45/45 rows) / `spec-180`
  (41/41 rows) are fully assessed, no longer placeholders. The ledger states its own coverage
  as "All 23 expected intent chunks present and non-placeholder"; trading-removed promises are
  correctly listed under "Dropped by the 23 Sep trading-removal decision", not as missing.

## 8. Known gaps

- **`LIFE-L6-LONGSESSION-1` (main-thread CPU burn during the long-session soak) is measured but
  not attributed** — the root cause read-back explicitly defers attribution to a follow-up
  profiling pass (`lifecycle/L6-longsession.md` §8); carried forward as an open register entry,
  not fixed here.
- **Eleven Python packages across the sidecar/openbb-mcp/sec-edgar-mcp closures carry no
  machine-readable licence metadata** (§5 above) — needs a manual licence check before a public
  release; not resolved in this pass.
- **22 coverage-map cells are NEEDS-MANUAL-CHECK** — genuinely GUI/OS-only surfaces (canvas
  gestures, the real OS-global kill-switch shortcut, real desktop notification delivery) that
  this read-only, no-GUI run cannot close; for the operator.
- **`google-genai`'s unpinned dependency floor** (`>=1.0`) is a live reproducibility gap, not
  fixed in this pass (a `requirements.txt` edit, out of scope for a verification run).
- **Intent census closed this pass** — the remaining 10 of 23 chunks landed and the 2
  placeholder chunks (`spec-90`, `spec-180`) are now fully assessed (§7); the register rebuild
  folded in 35 new entries this surfaced (3 new rejections: `INT-spec-180-181`,
  `INT-spec-180-206`, both verification-paperwork gaps, not product defects) — no longer carried
  forward as a gap.
- Everything else in this sheet is either closed (register unaccounted-raw-ids 0)
  or explicitly labelled with its own reason in the source document — no findings were silently
  dropped to reach these totals.
