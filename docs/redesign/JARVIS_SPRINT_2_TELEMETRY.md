# JARVIS Sprint 2 — telemetry

_The big-pass run on branch `002-jarvis-intelligence` (base `ae2a499`). Autonomous overnight
sprint: ship-with-everything + ultimate-powerful research (IterResearch) + good engineering +
persistence-bug + aliveness + backlog. Not merged to main; version untouched. Authored by the
lead (Opus 4.8, 1M)._

## Run log

- **00:00 — Foundation.** `caffeinate -dimsu -t 86400` started (display kept awake for live
  pixel-verify — last pass slept and lost Tauri IPC). Confirmed: rig = `tauri dev --features
dev-tools`; sidecar venv 3.13.13; ollama up (`qwen2.5:7b`, `llama3.1:8b`); main sidecar binary
  fresh (Jun 2, 105 MB); base `ae2a499`, tree clean.
- **00:05 — Recon fan-out.** Launched `jarvis-sprint2-recon` workflow (13 read-only agents):
  persistence-bug re-diagnosis, IterResearch web research, research-loop codemap, SearXNG-ship
  design, duplication/failure-state/rough-edge audits, dual-panel axis-lock map, motion plan,
  decompose-surface, OpenCode re-assessment, citation-validation map, §6.5 floor playbook. Run id
  `wf_e37d542e-1a3`.
- **00:05 — Rig launch** started in parallel (Rust compile + next dev).

- **Track 4 — Persistence bug (DONE, rig-verified).** Re-diagnosed from scratch (my trace +
  recon A1 agreed exactly). Root cause was NOT the "missing autosave subscription" the prior
  sprint claimed fixed — that fix is present and works. The real break: the active `copilot`
  agent's boilerplate `defaultProvider:"ollama"` shadows the persisted `defaultProviderId`
  (which sat as the lowest-priority fallback and was never reached). Secondary: the HUD provider
  pick wrote only ephemeral `providerOverride`; and restore pruned any model not in the _static_
  known-model list (silently dropping LIVE-catalog picks). Fixes: generic-agent guard (copilot
  defers; personas keep their pin), HUD pick persists as the default, trusted restore keeps
  live-catalog model ids. **Verification surfaced a deeper latent bug:** concurrent autosaves
  (two `autosaveLayout()` POSTs) raced on a non-atomic `path.write_text`, tearing
  `__autosave__` into invalid JSON → 500 on restore → silent revert to default layout. Fixed
  with atomic temp+`os.replace` write + graceful corrupt-read (404 fallback, not 500).
  **Rig-verified the full reload round-trip:** set DeepSeek + a non-static model →
  autosave persisted → reload → both restored; StatusChrome + HUD show `DeepSeek ·
deepseek-v3.2-exp-live` while the generic Copilot lens is active. Reset to keyless `ollama`
  - repaired the live corrupt blob. §6.5 9/9; Tier-1 diff empty.

- **Track 2 — IterResearch + Heavy (DONE).** New `services/research/iter.py` (additive — `deep.py`
  left byte-for-byte untouched as the proven fallback): `run_iter_research` (central evolving
  `_Report`, per-round workspace reconstruction, real distill step, hard-capped working context)
  and `run_heavy_research` (N parallel explorers each their own report → synthesis agent merges +
  dedupes + renumbers `[n]`). Default deep path now IterResearch; `mode="single"` is the legacy
  fallback; `angles>=2`/`heavy:true` runs the panel; runtime fallback to `run_deep_research` if iter
  ever raises. Live `angle`/`distill` step-stream. 26 new/updated tests prove workspace
  reconstruction (round-3 context drops round-1 raw findings), bounded report, distill resilience,
  budget abort, panel synthesis + crash/dead-LLM survival; catalog⟺MCP parity green. Commit `c30cf86`.
- **Track 1 — Keyless search floor (DONE).** New `services/search/ddg.py` — keyless DuckDuckGo
  backend wired as the unconditional last fallback in `web_search.py` (never dark on a fresh
  install); wired the previously-dead `detect_searxng` autodetect. **Chose the in-sidecar DDG floor
  over bundling SearXNG** (60–90 MB 4th binary + cold-bind race, unverifiable tonight) — the safe
  default that delivers "keyless out of the box." Live smoke: 8 real cited results, zero keys. 28
  tests. Keyless DATA defaults confirmed on out-of-box (rig screenshot: SPY/QQQ YFINANCE·LIVE).
  Commit `9617226`.
- **Track 6 #2 — Decompose plan surface (DONE).** New `LLMAgentPlanEvent` + a compound-only plan
  pre-pass in `invoke_agent` (gated to capable cloud providers; local ollama skipped → preamble
  fallback) + `PlanView` rendering numbered steps with review/research/answer pills. Shown but NOT
  pre-staged (the loop already stages each host-action — avoids double-apply). No order verb → §6.5
  untouched. 4 tests. Commit `9972c0e`.
- **Track 6 #1 — OpenCode → LOGGED (not integrated).** Recon A11 strengthened the Phase-0 FALLBACK:
  OpenCode's `deny` permission gate is a live unfixed SDK bug (#6396 + #16331/#7063/#5965), so the
  §6.5-safe config can't be trusted; the capability is already in-house (`planner.decompose()` +
  the `research_step`→`ResearchActivity` channel). Correct safe call: do not add a 4th subprocess +
  a Tier-4 inversion risk for negative marginal value.
- **Track 6 #5 — Citation validation (DONE, floor-respecting).** Shipped a ready, skipif-gated
  `test_native_search_live.py` (`:online` → `normalize_openai`); validated the OpenRouter KEY PATH
  live through the app (renderer-side keychain → X-LLM-Key, `source:"live"`, 343 user-scoped
  tool-capable models, zero credit) — did NOT extract the key to the shell (floor). The 18 unit
  tests already prove the url_citation parse. Commit `ace28ba`.
- **Track 5 — Aliveness (DONE).** `useTickFlash` hook + watchlist per-row green/red tick-flash (the
  one "feels dead" surface) + news staggered fade-in; reduced-motion aware. Commit (Track 5).
- **Track 3 — Good engineering (high-value slice DONE).** D1 model-list drift-guard (deriving the
  tables hit a circular-import `ci-local` caught → reverted to literals + a drift-guard test, A5's
  named fallback); A6 swallowed-async-failure fixes (portfolio quote
  catch + retry banner; Exa key save error surface; delegate poller staleness badge after 5 fails +
  answer/resume `{ok,error}` returns so the AgentsRail answer form no longer silently dead-ends).
  Plus the workspace atomic-write/graceful-read fix from Track 4 (failure-designed-for). Commit
  (Track 3).
- **Deferred + LOGGED (the safe-default per "don't blow the pass on one item"; full blueprints in
  `docs/redesign/recon/`):**
  - **Track 6 #3 — dual-panel axis-lock (A8):** designed in full (Map&lt;panelId&gt; chart-command
    refactor + axis-lock store + dual-split template). Deferred: heaviest item (store reshape +
    ChartPanel 1150 L + 6 files) and its headline (synced pan/zoom) can't be rig-verified via
    tauri-mcp (isTrusted — needs Playwright trusted events). Overlay-compare fallback still works.
  - **Track 3 polish (A7 rough-edges ui-classes unification; A5 D2/D3 SSE-encoder/registration
    dedup; A5 D5 region-format bug):** lower-value than the de-dup + failure-state items already
    shipped; logged with file:line blueprints.

## Agent activity (cumulative)

| Phase | Workflow / agents         | Tokens | Wall   | Outcome                                           |
| ----- | ------------------------- | ------ | ------ | ------------------------------------------------- |
| Recon | jarvis-sprint2-recon (13) | 1.06M  | ~6 min | all 13 blueprints landed → `docs/redesign/recon/` |

## Gates (floor) — per milestone

| Milestone     | §6.5 audit      | Tier-1 diff | pytest                                | vitest                                     | rig                      |
| ------------- | --------------- | ----------- | ------------------------------------- | ------------------------------------------ | ------------------------ |
| _base_        | (inherited 9/9) | empty       | —                                     | —                                          | —                        |
| Track 4       | 9/9             | empty       | test_workspace 11/11                  | model-sel+workspace 22/22                  | reload round-trip PASS   |
| Track 2       | (n/c)           | empty       | iter+tools+deep+tongyi+catalog+mcp 94 | —                                          | _post-rebuild_           |
| Track 1       | (n/c)           | empty       | ddg+web_search+registry 28            | —                                          | live DDG smoke 8 results |
| Track 6 (A10) | 9/9             | empty       | agent_runtime+planner+catalog+mcp 72  | chat-history 4                             | _post-rebuild_           |
| Track 6 (A12) | (n/c)           | empty       | native_search 22 (+1 skip)            | —                                          | OpenRouter key path live |
| Track 3+5     | (n/c)           | empty       | —                                     | model-sel+workspace+chat+watchlist+news 43 | _post-rebuild_           |
| Final         | 9/9             | empty       | full pytest (ci-local)                | full vitest 871                            | iter+plan surfaces PASS  |

**Final gates:** sidecar rebuilt ×2 → `smoke-test-sidecars` PASS both times ("all sidecars booted
cleanly"). `pnpm ci-local` PASS end-to-end (caught two real misses on the way: a `format:check` slip
on `slash-commands.ts`, and a circular-import from the D1 derivation — both fixed). Adversarial
review (9 agents, 7 dims): **1 confirmed LOW finding** (delegate-runs `pollFailures` reset) — fixed;
no critical/high, no §6.5, no Tier-1 drift.

## Forks taken (fallbacks)

1. Bundled SearXNG → in-sidecar DDG keyless floor (Track 1).
2. IterResearch in-place rewrite → additive `iter.py`, old `deep.py` kept as the runtime fallback (Track 2).
3. OpenCode integration → LOG (live unfixed `deny`-gate SDK bug; capability already in-house) (Track 6 #1).
4. Decompose pre-staging → show-only plan (avoid double-apply / AUTO bad-args) (Track 6 #2).
5. Live citation call with a shell-extracted key → credit-free key-path validation through the app (floor: never extract the BYOK key to the shell) (Track 6 #5).
6. Dual-panel axis-lock → LOG (heaviest; synced-pan unverifiable by the rig's synthetic events) (Track 6 #3).
7. Model-list derive → literals + drift-guard test (circular-import; A5's named fallback) (Track 3 D1).
8. A7 rough-edge unification + A5 D2/D3 sidecar dedup + D5 region-format → LOG (lower value; blueprints in `recon/`).
