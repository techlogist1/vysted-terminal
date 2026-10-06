# Law Digest — R15 Stage 0

Digest of docs/redesign/DECISIONS.md (D14–D80), BLOCKERS.md, docs/SAFETY_ARCHITECTURE.md,
docs/redesign/R12_HAND_TESTING_GUIDE.md, docs/redesign/R9_DESIGN_SYSTEM.md,
docs/redesign/CLAUDE_MD_PROPOSAL.md, docs/CURRENT_STATE.md, docs/redesign/verification/R12_RUN_REPORT.md.
All eight read in full. Model: claude-sonnet-5.

---

## (a) ACTIVE RULES a new lead must obey — NOT already in CLAUDE.md

1. **Operator-presence protocol**: before any GUI-driving leg, check frontmost app + HIDIdleTime;
   if the operator is actively at the machine, suspend ALL GUI driving immediately; resume only
   after ≥25 min sustained idle; hard-stop on any return. Any private-session capture caught by
   accident is deleted immediately, unseen-by-repo, never committed. — DECISIONS.md D63.
2. **Presence check is per-GUI-leg, not per-run** — R12 checked once at run start and a later leg
   (~35 min on) drove while the operator had returned; the fix is a fresh check before *every*
   individual GUI leg, not once per session. — DECISIONS.md D75 ("HONEST FAILURE LOG").
3. **The §6.5 "byte-identical to 393e8e5" claim has a specific, narrower path set than the Tier-1
   locked-file list in CLAUDE.md/CURRENT_STATE.md** — see (b) below for the exact paths and a
   live re-verification. This path set (not documented in CLAUDE.md) is what R10–R13 actually ran.
4. **`smoke-test-sidecars.mjs`'s pre-flight must never be a blanket `pgrep/pkill vysted-*`** near
   a live operator session — it must use a scoped PID ledger + child-marker env that only reaps
   processes it itself spawned, ephemeral throwaway ports, and held stdin. CLAUDE.md's current
   description of this script (line 301-302) still describes the OLD, unsafe pre-flight behavior.
   — DECISIONS.md D80; proposed CLAUDE.md text sits unapplied in CLAUDE_MD_PROPOSAL.md "R13 proposal".
5. **Long-standing uncommitted "sacred" files must never be touched via a blanket `git add`/commit**
   — verify by sha256/diff against the last recorded value before staging explicit paths only.
   (`enrich_nse_sectors.py` was one for R10–R13; R15's ground-truth notes it and
   `kill-switch-benchmark.json` were retired/fixed this run — see (b).) — DECISIONS.md D59/D62;
   BLOCKERS.md kill-switch-benchmark note; R15_BRIEF.md ground-truth section.
6. **Resolver bind policy (not documented anywhere in CLAUDE.md today)**: bind only at band ≥
   PREFIX (score ≥ ~0.72 for the auto-bind case); 0.5–0.72 disambiguates; <0.5 is unresolved. A
   bare-substring match (band 1, always 0.8) must NEVER auto-bind. An engine-level tie guard
   disambiguates exact (band, score) ties instead of an arbitrary iteration-order pick. —
   DECISIONS.md D37, D46, D58.
7. **Agent-drivable settings are allow-listed, not implicit**: only region + default research
   depth are agent-settable; autonomy level, API keys, broker config, kill switch, and search-tier
   billing are human-only by construction (asserted by test). — DECISIONS.md D45.
8. **Conflict doctrine (recurring product philosophy, not stated as a rule anywhere in CLAUDE.md)**:
   when two sources that both claim the same basis disagree, the app must flag BOTH values and
   pick NEITHER — never silently substitute a "corrected" number. Applies to growth (D66),
   dividends (D56), instrument identity/renames (D67), and retrieval emptiness (D74 — an
   up-but-empty SearXNG that returns HTTP 200 + `results: []` must cross-check the keyless floor
   before the pipeline is allowed to narrate "no results," because the existing degrade rule (D25)
   only fires on `unreachable`, not on `empty`).
9. **Order-intent classification must include buy/sell/place-order verbs** or the read-only
   intent path silently strips `propose_order` and the whole §6.5 prepare→review→confirm dialog
   becomes unreachable from chat (fails closed, so not a safety hole, but a dead designed UX
   path with zero warning). Check this whenever the NL intent classifier's vocabulary changes.
   — DECISIONS.md D68.
10. **An agent tool's capability is exactly what its `TOOL_SCHEMAS`/catalog prose documents** —
    a real, working capability with incomplete prose (e.g. the screener's sector/industry filter
    before D64) is invisible to the model, which will silently invent a lossy workaround (sweep +
    client-side post-filter) rather than report the gap. Any catalog edit must audit prose
    completeness, not just schema correctness. — DECISIONS.md D64.
11. **Model-routing must be explicitly recorded per agent/teammate, never assumed inherited** —
    routing has silently inherited the parent/lead model before; every dispatched worker
    self-reports its actual model id. — R12_RUN_REPORT.md "Loop telemetry"; reiterated as a hard
    rule in R15_BRIEF.md.
12. **A META-class relevance leak (4-char symbols matching a foreign namesake) is deliberately
    NOT fixed by widening the short-symbol corroboration gate to ≤4 chars** — doing so was proven
    to regress INFY-class Indian marquee names far more broadly. Do not "fix" this without
    re-deriving a corroboration signal that separates the two classes. — DECISIONS.md D78.
13. **Bank growth-conflict notes are an accepted, by-design false-positive class**, not a bug —
    yfinance's Indian-bank revenue-growth scalar rides a different revenue definition than the
    statements, so D66's cross-check will flag it on essentially every bank brief. Don't chase it
    as a defect during triage. — R12_HAND_TESTING_GUIDE.md "Honest edges"; DECISIONS.md D66.

---

## (b) The §6.5 "byte-identical to 393e8e5" path set — reconstructed, command run, result TODAY

Every run report (R10-VERIFY, R11, R12, R13) states this claim in prose only ("the whole
broker/order/audit/kill-switch surface") without repeating the path list inline in the run
reports read for this digest. The **one place the actual path list is spelled out** is
`docs/redesign/verification/R10_VERIFY_REPORT.md:52`:

> `git diff 393e8e5 HEAD` over `sidecar/services/brokers/`, `models/audit_log.py`,
> `models/broker.py`, `routers/brokers.py`, `routers/safety.py`, `services/kill_switch.py`,
> `src-tauri/src/kill_switch.rs` → **empty**.

Resolved to full repo-relative paths and re-run today (2026-09-19, HEAD `0112a0c`):

```
git diff 393e8e5 HEAD -- \
  sidecar/services/brokers/ \
  sidecar/models/audit_log.py \
  sidecar/models/broker.py \
  sidecar/routers/brokers.py \
  sidecar/routers/safety.py \
  sidecar/services/kill_switch.py \
  src-tauri/src/kill_switch.rs
```

**Result: 0 lines of output.** The claim holds today, exactly as it has held through R10–R13
(each of which re-ran an equivalent check and got the same empty diff — D70, R11 §6.5 line,
R12_RUN_REPORT.md "Final gate chain", R13 D71/D69).

I additionally spot-checked `sidecar/services/broker_base.py` (the actual `BrokerAdapter` ABC
carrying all 8 enforcements, and the file CURRENT_STATE.md §5/§3.6 and SAFETY_ARCHITECTURE.md
both call the Tier-1-locked *core* of the safety surface) — also **0 lines**, empty diff vs
`393e8e5`. Good: the narrower R10-VERIFY path list happens to still be sufficient, because
`broker_base.py` independently hasn't moved either.

**Is `sidecar/tests/test_safety_end_to_end.py` inside the verified surface? NO.**

- It is **not** in the R10-VERIFY path list above, and never has been in any run's
  "byte-identical" check — the checked surface is the *implementation*, not the audit suite.
- It **is** listed as a Tier-1 LOCKED file in `docs/CURRENT_STATE.md:505` ("§3.6 Tier-1 LOCKED
  files") and is the canonical §6.5 audit file per `docs/SAFETY_ARCHITECTURE.md:245`.
- It **has** diverged from `393e8e5`: `git diff 393e8e5 HEAD -- sidecar/tests/test_safety_end_to_end.py`
  → 8 insertions / 1 deletion. This is exactly the lead's own commit `0112a0c` ("kill-switch
  benchmark capture is opt-in"), which adds an `import os` and changes
  `test_audit_5_kill_switch_under_2s` to write the `kill-switch-benchmark.json` capture to the
  test's temp dir unless `VYSTED_REFRESH_SAFETY_CAPTURES=1` is set — **no assertion changed**
  (confirmed by inspecting the diff directly), and it's already self-disclosed in
  `docs/redesign/DECISIONS_FOR_OPERATOR.md` §1.2 as a Tier-4 reversal-for-the-operator with a
  one-line revert.
- **Net**: the "byte-identical §6.5 surface" claim is true and still holds for the *enforcement*
  code; it was never a claim about the test file, so 0112a0c does not violate any standing
  claim — but the claim's scope has quietly narrowed over five runs without anyone restating it,
  and CLAUDE.md/CURRENT_STATE.md's broader "Tier-1 locked files" framing (which DOES include the
  test file) could mislead a future lead into thinking 0112a0c needed sign-off it already got
  (via DECISIONS_FOR_OPERATOR.md) or, worse, into thinking the byte-identical check would have
  caught it (it would not have).

---

## (c) DEFERRED / NEEDS-MANUAL-CHECK / open BLOCKER items — deduplicated

### Still explicitly live per the most recent (R12/R13/DECISIONS) source

| Item | Source | Status |
|---|---|---|
| MCP cold-bind ~34s isolated (worse under I/O contention); real fix is PyInstaller `--onedir` for the two MCP sidecars (needs a Tier-1 `tauri.conf.json` `externalBin`→resource-folder change + Rust spawn change `ci-local` cannot verify) | BLOCKERS.md "Phase 9.5 UC1"; DECISIONS.md D76; CLAUDE.md "Deferred/carry-forward" | **Open** — D76 explicitly re-affirmed as shipped workaround (45s×2 wait) for R13; not attempted |
| BSE rename lane (bundled masters predate BSE-side renames, e.g. CDG→Jujhar Logistics) — only the NSE symbolchange lane (D67) exists; BSE stopgap is an honesty-surface note (`identity_note`/`identity_conflict`), not a real fetcher | DECISIONS.md D79 | **Open, explicitly deferred** as of R13 |
| In-webview drags (dockview tab reorder, node-editor palette→canvas) — no rig on this Mac can synthesize a trusted HTML5 drag event | BLOCKERS.md (v0.5.0 §4, "Playwright real-event suite"); R12_HAND_TESTING_GUIDE.md "Your personal checklist" #1; R12_RUN_REPORT.md NEEDS-MANUAL-CHECK | **Permanent NEEDS-MANUAL-CHECK** until a real-event (Playwright) suite exists — R15_BRIEF says test rig limits live "rather than inherit them" (July limits may be stale, re-verify) |
| ~960px narrow-width / clipped-text sweep — the design-token audit passes statically but is not a substitute for an eyeball pass | R12_HAND_TESTING_GUIDE.md #2; R12_RUN_REPORT.md NEEDS-MANUAL-CHECK | **Open**, operator/hand-check only |
| Screener throttle-chip re-shot (PARTIAL badge, "DATA PROVIDER IS THROTTLING THIS IP", per-tier freshness) — R11 captured it live; R12 did not re-shoot | R12_HAND_TESTING_GUIDE.md #3; R12_RUN_REPORT.md NEEDS-MANUAL-CHECK | **Open**, cosmetic/evidence-freshness only, feature itself proven live |
| "The taste pass" — persona voice, micro-interactions, feel | R12_HAND_TESTING_GUIDE.md #4 | Explicitly operator-only, not delegable |
| `resetKillSwitch()` (`src/store/safety.ts:230`) entirely untested — a camelCase/snake_case drift on the `reAck` body field would silently permanently lock the kill switch | BLOCKERS.md S1 #1; CURRENT_STATE.md §5 "Known §6.5-adjacent test gaps" | **Still open** — no DECISIONS entry claims this was fixed in R7–R13 |
| `propose_order()` invalid-`order_type` path untested (only invalid `side`/zero-qty covered) | BLOCKERS.md S1 #2; CURRENT_STATE.md §5 | **Still open**, same caveat |
| Non-India broker adapters (Alpaca/IB/OANDA/ccxt-exec) implemented but never registered in `BUNDLED_PLUGINS`/`bootstrap_default_adapters` | BLOCKERS.md S2 #5; CURRENT_STATE.md §7 | **Status unclear** — not mentioned as fixed in any R7–R13 DECISIONS entry; worth a fresh check, since D44 (Tradesa removal) and P2 in CURRENT_STATE's 0.5 update ("no broker registered at boot") changed broker-bootstrap behavior around this exact code path since this BLOCKERS entry was written |
| Kite `request_token` Rust-loopback auto-capture (v1 ships manual paste only) | BLOCKERS.md Phase 10 #4 | **Still deferred**, no contradicting decision found |
| Light theme (dark-only ships; Tier-4 blocker until v1.1) | BLOCKERS.md S2 #10, S4; CURRENT_STATE.md §7 | **Still deferred** |
| Launch ops: code signing, auto-updater wiring (`createUpdaterArtifacts:false`), distribution channels, `terminal.vysted.com`, LICENSE flip + CLA bot, first-launch TOS dialog, v1.0.0 announcement | BLOCKERS.md "v0.7.0 → Phase 10 carry-forwards" | **Still open** — R15_BRIEF's own Stage-2 "release-ready" gate (rc2) is explicitly built to close exactly this list; nothing in R7–R13 touches launch ops |
| Realtime SSE proxy (replace panel polling) | BLOCKERS.md "Phase 6.5 → v0.6.6"; also generic across panels | **Superseded/moot for Tradesa specifically** (Tradesa fully removed, D44) but the general "replace polling with SSE/WS push" idea is untouched elsewhere (e.g. audit-log tail is still 2s polling per CURRENT_STATE.md §3.6) |
| CI runtime budget: PyInstaller `--onefile` cold-cache builds make each CI workflow ~20-25 min; binaries uncached | BLOCKERS.md "v0.7.0 → v0.8 polish #5" | **Status unknown**, not addressed in DECISIONS.md D14-D80 |
| `--onedir` also removes the CI-runtime-budget pain (same root cause as the MCP cold-bind item) | cross-referenced, not stated together in source | note only |

### Likely STALE / MOOT (superseded by R7–R13 work but still physically present in BLOCKERS.md — flag for BLOCKERS.md cleanup)

| Item | Why it's likely moot | Source |
|---|---|---|
| All "Tradesa V2" carry-forwards (realtime SSE proxy, write capability, MCP tool exposure for brain-decision log, anon-key/Auth migration, Bybit Demo enrichment, live screenshot pass) | **Tradesa V2 is removed completely** — plugin dir, sidecar provider/router/model/tests, types, marketplace row, keychain namespace all deleted; the plugin *system* was re-proven post-strip instead | DECISIONS.md D44 vs BLOCKERS.md "Phase 6.5 → v0.6.6 carry-forwards" (all 6 sub-items), "v0.6.x" Tradesa sections |
| "Live copilot demo needs a BYOK key" / Gemini-Ollama tool-path confidence-6-7 | R11+ batteries ran live against funded OpenRouter keys (glm-5.2, kimi-k2.6) extensively; the specific framing ("needs a key") is outdated even if per-adapter confidence hasn't been re-scored | BLOCKERS.md "Phase 10 carry-forwards" #2 vs R11/R12 loop telemetry |
| "Copilot roster depth — deferred" (`GET /agents/roster`, 3-pane panel, hard `delegate_to_persona`) | Not contradicted by any R7-R13 decision — likely still genuinely open, listed here as NOT stale, included for completeness | BLOCKERS.md Phase 10 #5 |
| S3 polish items referencing `HOST_VERSION = "0.6.5"` / specific old line numbers | Version drift item itself may be stale bookkeeping (see (d) — version strings are still 0.8.0 everywhere per a live grep) | BLOCKERS.md S3 |

### Open BLOCKER-shaped items surfaced inside DECISIONS.md itself (not in BLOCKERS.md at all — dedupe against the table above)

- D76 MCP `--onedir` (duplicate of BLOCKERS Phase 9.5 entry above — same item, restated live).
- D79 BSE rename lane (duplicate of above).
- No open BLOCKER-class item in D50–D80 that isn't already captured in the tables above or in
  (a)'s active-rules list.

---

## (d) CLAUDE_MD_PROPOSAL.md — what it proposes, and CLAUDE.md staleness against CURRENT_STATE.md/R9-R13

### What the proposal file contains (compact)

`docs/redesign/CLAUDE_MD_PROPOSAL.md` is explicitly a **sign-off-only file — apply on review**;
none of it has an operator sign-off recorded and CLAUDE.md still doesn't contain it (verified
below). It proposes, section by section:

1. **Stack**: replace "Next.js 16 (App Router, static export)" with "Vite 8 + React 19 +
   TypeScript (single-page shell: `index.html` + `src/main.tsx`; static build to `out/`)"; note
   JetBrains Mono self-hosted via `@fontsource`; dev server is `vite` on `127.0.0.1:5173`.
2. **Gotchas → Frontend**: Vite watcher must ignore `.claude/**`, `out/**`, `sidecar/**`,
   `src-tauri/**`, `graphify-out/**`; the tauri-plugin-mcp bridge wedges after Vite HMR reruns
   bridge init (needs a dev-stack restart); WKWebView serves stale JS via `location.reload()`
   (needs cache-dir wipe for a true live-verify); `layout-templates.ts` panel ids must be
   REGISTERED module ids.
3. **Gotchas → Copilot & sidecar**: frontend control keys (research_depth, deepResearchBackend,
   modelWebSearch, history) must never reach adapter kwargs (filtered in two places — must add a
   new control key in both); composer depth slider → `config.set_request_research_depth`;
   search-tier headers (`X-Vysted-Research-Tier` etc.); `transform.code` workflow node
   grammar-compatibility; `save_workflow` MCP-only tool; keyless-India BSE master details
   (4,873 rows, `bse_provider` scrip-code routing, `nse_direct` rank).
4. **Versioning & process**: macOS dev-signing cert disappearance during R7 (this is now
   superseded — R9's "preconditions" section in DECISIONS.md documents stable dev-signing as a
   *precondition already met*, so this specific proposal entry is itself stale relative to its
   own file's later content).
5. **R8 proposal**: update the sidecar-spawn gotcha line to name `wait_for_port_with_retries`
   (45s × 2) instead of the old flat-15s `wait_for_port`.
6. **R13 proposal**: rewrite the smoke-test-sidecars.mjs verification-gate line to describe the
   attended-safe pre-flight (scoped PID reaping, TCP MCP-bind probe, `/health` version +
   `/agents` count + `/mcp/status` asserts) instead of the old blanket-pkill description.

### Confirmed: NONE of this has been applied to the live CLAUDE.md

Direct diff of claims vs the live file:

- **Stack line is stale.** `CLAUDE.md:28` still reads `**Frontend:** Next.js 16 (App Router,
  **static export**) + React 19 + TypeScript`, and `CLAUDE.md:5`/`CLAUDE.md:38` still say
  "Next.js UI" / "Next.js frontend". But the repo has already migrated: `package.json` has
  `"dev": "vite"`, `vite.config.ts` exists (no `next.config.*`), and
  `src-tauri/tauri.conf.json:8-9` has `"devUrl": "http://localhost:5173"` +
  `"beforeDevCommand": "...pnpm dev"` — i.e. the Vite migration DECISIONS.md D6 scoped is DONE,
  and CLAUDE.md was never updated to match. **This is the single highest-value staleness fix.**
- **Plugin roster line is stale.** `CLAUDE.md:45` still lists `plugins/` as "bundled plugins
  (Tradesa V2, openbb-mcp, brokers, example)". Confirmed live: `ls plugins/` →
  `brokers example openbb-mcp vysted-lenses vysted-news yfinance` — **no `tradesa-v2` directory
  at all**, consistent with DECISIONS.md D44 ("Tradesa V2 is removed completely"). CLAUDE.md
  never picked up the two new first-party plugins (`vysted-lenses`, `vysted-news`) either.
- **Smoke-test description is stale**, exactly as CLAUDE_MD_PROPOSAL.md's own R13 section
  already flags: `CLAUDE.md:301-302` still says the script "spawns each built sidecar, polls
  `/health`, checks MCP subprocesses survive" — no mention of the D80 attended-safe pre-flight,
  the TCP MCP-bind probe, or the `/agents` count / `/mcp/status` asserts it now performs.
- **`amber-*` accent color note is stale/contradicted.** `CLAUDE.md:231-237` and `:323` describe
  the design-token accent as "`amber-*`→**cool-indigo**" and a "**zinc near-black + cool-indigo**
  shell". But `styles/tokens.css:54` (`--color-amber-400: #fab283`) and `R9_DESIGN_SYSTEM.md`
  §4/D28 are unambiguous: R9's single scarce accent is a **warm peach** (`#fab283`, OpenCode-style),
  not cool-indigo, and it's directly reused as the DEEP step of the depth-heat family
  (`styles/tokens.css:91`). Either CLAUDE.md predates R9's accent decision and was never updated,
  or "cool-indigo" describes something else CLAUDE.md never disambiguates from the accent — either
  way this is a real, verified conflict a new lead doing UI/color triage would trip on.
- **`--onedir`/MCP-cold-bind deferred line is NOT stale** — CLAUDE.md's existing text matches
  D76's re-affirmation almost verbatim; no fix needed there.
- **Version strings**: CLAUDE.md's "Versioning & process" section is generic guidance (not
  claiming a specific version) so it isn't stale per se, but a live grep shows `package.json`,
  `sidecar/app.py`, and `HOST_VERSION` (`src/lib/plugin-bootstrap.ts:37`) are all still `"0.8.0"`
  despite 7 full R-numbered passes (R7-R13) landing on `004-r4-experience-rebuild` — worth a
  version-bump pass before any release tag (R15_BRIEF's own rc2 gate already plans this).

---

## (e) R9 design system non-negotiables (≤15 lines)

- **Spacing**: 8px base grid; 4px half-step anywhere; 2px quarter-step ONLY for intra-control
  optical gaps (never padding/rhythm). Allowed px: 2\*,4,8,12,16,20,24,28†,32,40,48,64,80,96
  (Tailwind: `0.5* 1 2 3 4 5 6 7† 8 10 12 16 20 24`). Anything else (`gap-1.5`, `px-[7px]`,
  `mt-9`) is off-grid and fails `scripts/audit-design-tokens.mjs`.
- **Type — one modular scale, six sizes**: 11 / 13 / 16 / 19 / 23 / 28px only. 12/15/18/22 are
  dead. `text-micro`=11 (floor, nothing renders smaller), `text-caption`/`text-body`/
  `text-panel-title`=13 (differ by weight/transform), `text-prose`=16 (wide panels only),
  `text-section`=19, `text-overview`=23, `text-hero`=28 (first-run only). Hierarchy below 16px
  comes from weight (400/500/700) + color, never size.
- **Controls**: chrome chips/buttons h-6 (24px) · inputs/toolbar h-7 (28px) · form controls h-8
  (32px). Icons 12px in h-6, 14px in h-7/h-8, 16px only for composer primary actions. One icon
  size per surface. Symbol inputs are FIXED width (`w-[8.5rem]`), never flex-greedy.
- **Color**: pure-neutral zinc field; ONE scarce accent = peach `amber-400 #fab283`; depth-heat
  family (research escalation only) = normal `#f7f7f7` → deep `#fab283` → ultra `#f08a4b`,
  distinct from negative-red `#e5544b`. Prefer background-step/spacing over borders.
- **"Clipped text" here means**: any surface where a 32px-intent control renders visibly smaller
  (the root cause R9 fixed — halved `--spacing-N` tokens made `h-7` render taller than `h-8`),
  or text truncated/overlapping at the 1280px AND 960px capture widths — not a subjective "looks
  tight" call. Conformance is judged by side-by-side screenshot vs. Linear/Cursor/Claude desktop
  references by a **fresh-context verifier**, never the implementing agent's own eyeball.

---

## Notes on method

- All eight source documents were read in full (line counts: DECISIONS.md 135(+1 header row
  quirk)/BLOCKERS.md 620/SAFETY_ARCHITECTURE.md 252/R12_HAND_TESTING_GUIDE.md 52/
  R9_DESIGN_SYSTEM.md 138/CLAUDE_MD_PROPOSAL.md 66/CURRENT_STATE.md 977/R12_RUN_REPORT.md 69).
- Every code/repo-state claim above (Vite migration, Tradesa removal, tokens.css accent value,
  the §6.5 diff) was verified directly against the live tree (`git diff`, `grep`, `ls`) at HEAD
  `0112a0c` on branch `004-r4-experience-rebuild`, not inferred from the docs alone.
- No live sidecar/GUI interaction was needed for this task; none was performed.
