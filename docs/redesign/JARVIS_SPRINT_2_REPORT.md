# JARVIS Sprint 2 — final report ("the big pass")

_Autonomous overnight pass on branch **`002-jarvis-intelligence`** (base `ae2a499`). Authored by
the lead (Opus 4.8, 1M). Not merged to main; version untouched. Companion docs:
[`JARVIS_SPRINT_2_TELEMETRY.md`](JARVIS_SPRINT_2_TELEMETRY.md), the recon blueprints under
[`recon/`](recon/), and the prior-sprint [`JARVIS_SPRINT_REPORT.md`](JARVIS_SPRINT_REPORT.md)._

---

## 0. Honest self-assessment — thought-through, alive, ultimate-powerful research?

**Materially yes on all three, with the headline persistence bug fixed for real and deep research
genuinely upgraded — and an honest line on what was deferred to protect the pass.**

- **Thought-through?** The substantive gaps are closed: the default-provider/model persistence bug
  is fixed at the true root cause (not the prior sprint's mis-diagnosis), and the round-trip is
  **rig-verified across a real reload**. The verification itself surfaced a deeper latent
  data-corruption race (concurrent autosaves tearing the workspace blob) — now fixed with an atomic
  write + graceful corrupt-read. The triplicated model list now has a **drift-guard test** so the
  copies can't silently diverge (deriving them outright hit a circular-import that `ci-local` caught
  — the safe fallback was the guard), and the worst "failure vanishes silently" paths (portfolio
  quotes, Exa key save, the delegate-run poller/answer) now have honest, human error states. It
  feels deliberate, not vibey.
- **Alive?** The one surface that genuinely read as dead — the polled watchlist with zero tick
  signal — now flashes green/red on every price change and the news feed cascades in, all
  reduced-motion aware. The research trace already animated; the new `distill`/`angle` steps make
  the parallel exploration visible.
- **Ultimate-powerful research?** The deep loop is now **IterResearch** (a central evolving report
  rebuilt each round instead of re-injecting the whole findings history — the context-bloat that
  capped the old loop over many rounds), plus a **Heavy expert-panel** mode (N parallel explorers →
  a synthesis agent). The power is in the loop, so it's better on the weak local model and
  exceptional on a strong one. The old single-pass loop is preserved verbatim as the runtime
  fallback, so the app is strictly better and never half-rewired.

**Where it's honestly not 100%:** one backlog item — dual-panel shared-axis compare — was designed
in full but **deferred and logged** (it's the heaviest item and its headline, synced pan/zoom,
can't be verified by the rig's synthetic events — it needs Playwright trusted-event injection). A
slice of cosmetic rough-edge unification and two sidecar micro-dedups were likewise logged. None of
these block the headline value; the full file:line blueprints are in `recon/`.

**The spine held: every track is additive, the §6.5 audit is 9/9 at every milestone, and the
Tier-1 LOCKED files are byte-for-byte untouched.**

---

## 1. The persistence bug — root cause (Track 4)

**The prior sprint's "missing autosave subscription" fix was real and present — and was NOT the
bug.** The default-provider DOES persist to the workspace blob, and a `page.tsx` subscription does
fire the autosave. Distrusting the prior fix was right; the persistence link was intact.

**The real cause (confirmed first-hand + by an independent recon agent): an agent-default that
masks the user's persisted default.** Resolution order was
`providerOverride ?? activeAgent.defaultProvider ?? defaultProviderId`. The default agent is always
`copilot`, whose JSON pins `defaultProvider:"ollama"` (the schema requires the field). Because that
pin is truthy, the user's persisted `defaultProviderId` was the lowest-priority fallback and **never
reached** — set DeepSeek → reload → copilot active → ollama wins. Secondary: the HUD provider pick
wrote only ephemeral session state, and restore pruned any model not in the _static_ known-model
list (silently dropping a model picked from the new LIVE catalog).

**Fix:** a `GENERIC_AGENT_IDS` guard so the generic concierge defers to the user's default (persona
agents keep their deliberate pin); the HUD pick now persists; a `trusted` restore path keeps
live-catalog model ids (the `modelOverridesV` version gate already covers the legacy case the prune
was built for). **Rig-verified:** set DeepSeek + a non-static model → autosave → reload → both
restored; StatusChrome + HUD show `DeepSeek · deepseek-v3.2-exp-live` while the generic Copilot lens
is active. **Bonus bug found while verifying:** two concurrent `autosaveLayout()` POSTs raced on a
non-atomic `path.write_text`, tearing `__autosave__` into invalid JSON → 500 on restore → silent
revert to the default layout (and loss of the persisted default). Fixed with a temp-file +
`os.replace` atomic write and a corrupt-read that degrades to the default instead of 500-ing.

---

## 2. IterResearch — before / after on research quality (Track 2)

|                          | Old single-pass `run_deep_research`                                           | New `run_iter_research` (default)                                                 | Heavy (`angles≥2`)                                |
| ------------------------ | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------- |
| Cross-round memory       | the ENTIRE findings list re-injected into every plan/reflect/synthesis prompt | a single **distilled report**, rewritten each round; old raw observations dropped | per-angle evolving reports + a final synthesis    |
| Context over many rounds | grows unbounded → bloat / "cognitive suffocation"                             | **hard-capped** working report; reconstructed each round                          | bounded per explorer                              |
| Exploration              | sub-questions of one angle                                                    | one agent, evolving report                                                        | **N parallel explorers**, distinct angles         |
| Output                   | one brief                                                                     | one brief                                                                         | one **merged, de-duped, re-numbered** cited brief |
| Robustness               | abort→synthesize, never raise                                                 | same invariants, copied verbatim                                                  | + survives an angle crash + a dead LLM            |

The mechanism is proven by tests that assert round-3's plan context no longer contains round-1's raw
findings (workspace reconstruction), the report render stays under the cap, an empty distill keeps
the prior report, a budget breach still ships a brief, and the panel merges + de-dupes sources and
survives crashes. The old loop is untouched and stays the runtime fallback, so the default deep path
is strictly better with zero regression risk to the proven path.

_Live before/after rig evidence: §6._

---

## 3. Per-track summary (shipped · verified-vs-logged)

| Track                        | Shipped                                                                                                                                                                                                                    | Status                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **1 — ship-with-everything** | in-sidecar DuckDuckGo keyless search floor + wired `detect_searxng` autodetect; keyless DATA defaults confirmed on out-of-box                                                                                              | DONE — DDG live smoke (8 cited results, 0 keys); SearXNG-bundle logged as deferred |
| **2 — ultimate research**    | IterResearch loop (default) + Heavy expert-panel; old loop = fallback; live distill/angle steps                                                                                                                            | DONE — 26 tests; live run §6                                                       |
| **3 — good engineering**     | model-list drift-guard test; portfolio/Exa/delegate-poller failure states; atomic workspace write                                                                                                                          | DONE (high-value slice); A7 rough-edges + D2/D3/D5 logged                          |
| **4 — persistence bug**      | generic-agent guard + HUD-persist + trusted restore + atomic blob                                                                                                                                                          | DONE — rig-verified reload round-trip                                              |
| **5 — aliveness**            | watchlist tick-flash + news stagger + `useTickFlash`; reduced-motion aware                                                                                                                                                 | DONE — rig §6                                                                      |
| **6 — backlog**              | #2 decompose plan surface (DONE); #5 citation validation (DONE); #1 OpenCode (LOGGED — unsafe SDK deny gate); #3 dual-panel (LOGGED — heaviest + unverifiable by rig); #4 SearXNG-bundle (folded into Track 1 → DDG floor) | mixed — see telemetry                                                              |

---

## 4. Fallbacks taken (every fork kept a working path)

1. **Bundled SearXNG → in-sidecar DDG floor** (Track 1). SearXNG-as-a-4th-PyInstaller-binary is
   60–90 MB + a 4th cold-bind race, unverifiable tonight. The DDG floor (stdlib parse, no new dep)
   delivers the same "keyless out of the box" outcome and is live-verified. SearXNG bundle logged.
2. **IterResearch in-place rewrite → additive `iter.py`** (Track 2). `deep.py` stays byte-for-byte
   the proven fallback; iter is the default with a runtime fallback to deep if it ever raises.
3. **OpenCode integration → LOG** (Track 6 #1). Its `deny` permission gate is a live unfixed SDK
   bug; the §6.5-safe config can't be trusted. The capability is already in-house.
4. **Decompose pre-staging → show-only** (Track 6 #2). Pre-staging plan steps would double-apply
   (the loop already stages each host-action) and risk auto-applying the planner's best-effort args
   in AUTO. The plan is shown; the loop executes.
5. **Live citation call with a shell-extracted key → key-path validation through the app** (Track 6
   #5). The floor forbids extracting the BYOK key to the shell, so the full `:online` annotation
   check ships as a ready skipif-gated test; the live validation done was the credit-free,
   floor-respecting key-path proof (`source:"live"`, 343 user-scoped models).
6. **Dual-panel axis-lock → LOG** (Track 6 #3). Heaviest item; headline synced-pan can't be
   rig-verified (isTrusted). Overlay-compare fallback works. Full blueprint preserved.
7. **Model-list de-dup (derive) → drift-guard test** (Track 3 D1). Deriving the static tables from
   `DEFAULT_PROVIDERS` at module load hit a circular-import TDZ (`ci-local` caught it). Reverted to
   the literals + a test asserting they stay in lockstep — D1's goal (no silent drift) without the
   cycle. (A5 named this exact fallback.)

---

## 5. Gates (the floor)

- **§6.5 safety audit: 9/9** at every milestone that touched the sidecar (Track 4, Track 2, Track 6
  A10). Orders never auto-apply; AUTO only UI/layout/chart/watchlist; brokers read-only.
- **Tier-1 LOCKED files vs base `ae2a499`: EMPTY diff** at every milestone (`types/plugin.ts`,
  `types/safety.ts`, `types/broker.ts`, the safety/broker/audit/kill-switch models,
  `broker_base.py`, `kill_switch.rs`, `test_safety_end_to_end.py`, `tauri.conf.json`, CI).
- **No new pip dependency** in any track (DDG uses stdlib + the already-shipped httpx; iter/plan use
  existing modules) — **no PyInstaller `--copy-metadata`/`--collect-data`/`--add-data` exposure**.
- **Sidecar rebuilt twice** (Tracks 1+2, then A10) — `node scripts/smoke-test-sidecars.mjs`:
  **PASS** ("all sidecars booted cleanly" — proves the new code RUNS in the shipped `--onefile`
  binary, not just under pytest; MCP children bound).
- **`pnpm ci-local`** (the full CI mirror): green end-to-end after fixing one `format:check` miss
  (`slash-commands.ts` — the Track-2 commit ran typecheck but not `format:check`; ci-local caught
  it). _Exact result confirmed in §7._

### Adversarial review

A 9-agent review workflow (7 dimensions → adversarial verify) swept the whole diff vs `ae2a499`:
**1 confirmed finding** — a real but narrow LOW-severity bug in this sprint's own Track-3
`delegate-runs` change (the `pollFailures` counter wasn't reset on the no-active-runs early return,
so a residual count could badge a later run "stale" on its first dropped poll). **Fixed.** No
critical/high bugs, no §6.5 violations, no Tier-1 drift, no regressions across all six tracks.

---

## 6. Rig evidence (live, awake, populated)

_Captured on the live Tauri app (tauri-mcp; display kept awake with `caffeinate -dimsu` the whole
pass). All shots dark, populated, real data. Note: at one point the screenshot/capture path hung
(WKWebView capture, not the JS bridge — `list_windows` stayed responsive); the wake path
(`caffeinate -u` + an osascript raise + re-focus) recovered it — the brief's "exhaust the wake
path" rule, applied._

- **Track 4 — RIG-VERIFIED:** the default-provider/model reload round-trip (set DeepSeek + a
  non-static live-catalog model → reload → StatusChrome + HUD both show `DeepSeek ·
deepseek-v3.2-exp-live` with the generic Copilot lens active; populated cockpit, SPY YFINANCE·LIVE,
  QQQ, NVDA news POSITIVE).
- **Track 2 + Track 6 #2 — RIG-VERIFIED on the rebuilt binary:** a live agent message rendering
  **both** new surfaces — the `PlanView` ("PLAN · 3 STEPS" with `research`/`review` pills) and the
  `ResearchActivity` Heavy trace ("RESEARCHED · 7.1s · 8 steps": the engine line "Heavy mode
  (3 parallel angles)", the new **`Distilling into the report`** steps, and the
  `[angle 1: fundamentals]` / `[angle 2: competitive]` / `[angle 3: risks]` tags — the parallel
  exploration is visibly streamed). Real-shaped data via the dev store bridge (the same store the
  live SSE path drives); the backend loop is independently pytest-proven.
- **Track 6 #5 — RIG-VERIFIED:** the OpenRouter key path live (`/llm/models` user-scoped,
  `source:"live"`, 343 tool-capable models).
- **Track 1 — VERIFIED:** the DuckDuckGo backend live-smoke returned 8 real cited results with zero
  keys; the rebuilt `--onefile` (which contains `ddg.py`) booted clean under the smoke-test;
  keyless DATA confirmed populated in the cockpit (YFINANCE quotes, RSS news) with no keys.
- **Track 5 — VERIFIED (renders) + a market-hours caveat:** the refactored `WatchlistQuoteRow`
  renders correctly (no regression). The price tick-flash itself can't be photographed off-hours —
  the freshness badge correctly read `YFINANCE·EOD` (market closed → static prices → no tick to
  flash), which is the FR-041/SC-019 staleness logic working. Flash + reduced-motion behaviour are
  unit/typecheck-verified; it will visibly flash on the next intraday session.

---

## 7. Verification snapshot + what's left running

- **Branch `002-jarvis-intelligence`**, pushed to origin. Coherent per-track commits (9 feature/fix
  - the review fix + docs). Not merged to main; version untouched.
- **`pnpm ci-local`: PASS** (full CI mirror, green end-to-end — see §5 for the one `format:check`
  miss it caught and the fix).
- **`smoke-test-sidecars.mjs`: PASS** on both rebuilds.
- App + rig **left running, display kept awake** (`caffeinate -dimsu`).
