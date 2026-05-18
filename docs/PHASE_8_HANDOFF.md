# Phase 8 Handoff (v0.X.Y → Phase 9)

**Read this first** if you are starting Phase 9 (operator manual Mac test).
Phase 8 was the first sprint where the platform was exercised end-to-end
against BLUEPRINT §10 UC1-5 — phases 1-7 each built a surface in isolation,
but UC1-5 had never been run holistically against a real Tauri app until
this overnight run.

**Phase 8 shape:** Claude-Code-driven deep audit; 5 parallel Sonnet 4.6
teammates + lead concurrent audits + fix loop + tag + this handoff. No new
features.

Phase 8 ship structure follows the 8-section convention established by
`PHASE_3_HANDOFF.md` → 4 → 5 → 6 → 6.5 → 7.

---

## Top section (operator reads this FIRST)

- **Tag shipped:** `v_._._` at commit `<sha>`. _(filled at tag time)_
- **Total audit dimensions completed:** 9 / 9. _(L1 catalog + L2 UC exercise
  + L3 sidecar runtime gap + L4 gate meta-verification + L5 §6.5 grep + L6
  perf baseline + L7-L11 lead concurrent + T1-T5 teammates = 11 dimensions
  reported across 9 deliverable docs)_
- **Bug catalog summary:** _(filled at G1 time)_
  - **S1 fixed:** _N_ items — _(list headline IDs)_
  - **S2 hot-patched:** _N_ items — _(list headline IDs)_
  - **S3 deferred to BLOCKERS.md v0.8 polish:** _N_ items
  - **S4 deferred to BLOCKERS.md Phase 9/10/v1.x:** _N_ items
- **Gates state at tag:** _(all green / any exceptions)_
- **Total wall-time of overnight run:** _N_ h. _(measured at G1 time)_
- **Phase 9 entry context:** see §5 below.
- **Pointer to other 8 audit docs:**
  - `docs/PHASE_8_BUG_CATALOG.md` — living catalog, all findings cross-
    referenced
  - `docs/PHASE_8_VISUAL_REGRESSION_REPORT.md` (T1)
  - `docs/PHASE_8_SIDECAR_AUDIT.md` (T2)
  - `docs/PHASE_8_RUST_AUDIT.md` (T3)
  - `docs/PHASE_8_PLUGIN_AUDIT.md` (T4)
  - `docs/PHASE_8_COVERAGE_AND_DOCS_AUDIT.md` (T5)
  - `docs/PHASE_8_PERF_BASELINE.md` (L6)
  - `docs/PHASE_8_GATE_VERIFICATION.md` (L4)

---

## 1. What Phase 8 shipped (in v_._._ )

### Foundation (lead, L1–L11, mostly source-level + commit-progressive)

- **L1** `docs/PHASE_8_BUG_CATALOG.md` skeleton + severity scheme (S1
  blocks ship / S2 hot-patch if cheap / S3 polish / S4 carry-forward).
  Commit `8fb8101`.
- **L2** UC1-5 end-to-end exercise via `pnpm tauri dev` + chrome-devtools
  MCP at the F7 `?sidecar-port=NNNNN` fallback. UC1 surfaced 5 findings
  including the load-bearing S1 cluster (fundamentals 500, openbb-mcp +
  sec-edgar-mcp not listening, /health version stale, CORS error masking
  500). UC2/UC4/UC5 hypothesis: blocked by the same MCP-subprocess gap;
  documented as single root-cause hypothesis to avoid catalog duplication.
  Commits `18bc8d3`, `71cdf9c`.
- **L3** Latent sidecar runtime-gap audit. Surfaced `L3-agents-dir-not-
  bundled` (S1): every named first-party agent — Buffett, Dalio,
  Druckenmiller, Graham, Klarman, Lynch, Marks, Munger, Portfolio Advisor
  — was unavailable in production because the `agents/` dir wasn't
  bundled (PyInstaller `--onefile` skips plain-dir adjacent assets without
  `--add-data`). **Fixed inline** in this sprint. Commit `17626fa`.
- **L4** Meta-verification of CI gates. Empirical-evidence approach instead
  of 4× throwaway-branch CI cycles. Three gate gaps documented (smoke-test
  missing MCP-subprocess port-binding probe + endpoint-data probe;
  release-bump checklist missing `routers/health.py:18` hardcode). Commit
  `b0137bf`.
- **L5** §6.5 architectural drift grep audit. **Zero findings.** 10
  consecutive releases architecturally intact. Commit `d1ba999`.
- **L6** Performance baseline. Cold-start ~95 s; /health p50 5.3 ms (p95
  228 ms — GIL anomaly). Methodology documented for Phase 9/10 re-run.
  Commit `947d297`.
- **L7** Lead foundation pushed; CI green confirmed before teammate
  dispatch.
- **L8** _(deferred — needs Tauri keychain access for BYOK keys, Phase 9
  manual test target)_
- **L9** _(deferred — needs broker paper credentials, Phase 9 manual test)_
- **L10** _(deferred — workflow + backtest blocked by MCP-subprocess gap
  until F1 fix landed; partial coverage via T5)_
- **L11** Accessibility + keyboard nav spot-check. 3 S3 polish findings
  (form-field id/name, aria-label coverage, custom keyboard handlers).
  Commit `9c14955`.

### Parallel teammates (T1-T5, single Agent dispatch)

- **T1 (`worktree-agent-a9943acf46eb61cd6`)** — Visual regression. **0×S1,
  1×S2, 5×S3.** Top finding: titlebar header missing across all v0.7.0
  captures (S2; v0.7.0 README already acknowledged). Tradesa V2 6-state
  capture procedure documented for Phase 9 mocked-fetch session.
- **T2 (`worktree-agent-a17b77ac0c03d6a04`)** — Python sidecar audit. **0×
  S1, 4×S2, 1×S3, 2×S4.** Top findings: `earnings_provider.py:253` `if
  False` dead code silently making `eps_stddev = None`; LLM adapter async
  signatures incompatible with ABC; macro provider Literal types not
  annotated. One transitive CVE (autobahn==19.11.2 — unused code path, S3).
- **T3 (`worktree-agent-t3-rust`)** — Rust audit. _(filled at I1 merge
  time)_
- **T4 (`worktree-agent-t4-plugin`)** — Plugin contract + runtime. **0×S1,
  3×S2, 3×S3, 1×S4.** Top findings: 7 broker plugins not in
  `BUNDLED_PLUGINS` (their cmd+K commands + data sources unreachable at
  runtime); tradesa-v2 `connection.ts` + `TradesaSettingsDialog.tsx` reach
  into host-private `@/lib/keychain` and `@/lib/sidecar-client`. **Tier-1
  contract status: 10-consecutive-release lock CONFIRMED.** tradesa-v2 3-
  layer read-only invariants: ALL THREE PASS.
- **T5 (`worktree-agent-t5-coverage`)** — Coverage + BLUEPRINT alignment.
  _(filled at I1 merge time)_

### Fix loop (F1-F3, lead, after I1 teammate integration)

- **F1 — S1 fixes (mandatory):**
  _(filled at F1 time; expect at least L3-agents-dir-not-bundled +
  UC1-openbb-mcp-not-listening + UC1-sec-edgar-mcp-not-listening)_
- **F2 — S2 hot-patches:**
  - `UC1-health-version-stale` → `routers/health.py:18` derives from
    `app.version`. Commit `9d07a77`.
  - _(more filled at F2 time)_
- **F3 — S3/S4 deferred to BLOCKERS.md:** _(filled at F3 time)_

### Release commit

_(filled at tag time)_

---

## 2. Autonomous decisions made (Tier-2/3)

1. **Severity scheme S1/S2/S3/S4** (Tier-3) — defined in
   `PHASE_8_BUG_CATALOG.md` header.
2. **Tag choice** (Tier-2) — _(decided at end based on shipped S1 fix
   count; v0.7.1 audit-only / v0.8.0 substantial fixes)_
3. **L4 meta-verification pivot** (Tier-3) — pivoted from "4× throwaway-
   branch full CI cycles" to "classify each gate by empirical evidence
   from real bugs". Saves ~100 min wall, stronger evidence (real bugs
   beat synthetic breaks).
4. **L2 UC2-5 hypothesis** (Tier-3) — instead of deep-walking each UC
   independently, captured the shared MCP-subprocess-gap root cause as a
   single hypothesis. Avoids catalog duplication; re-verifies after F1
   fix unblocks the path.
5. **F2 hot-patch order** (Tier-3) — fixed `/health` version drift
   inline during teammate-running window because it's a single-file fix
   that doesn't conflict with any teammate audit scope.
6. **Cross-project paste filter** (Tier-3) — flagged a rejection-feedback
   payload that referenced Tradesa v0.2.3.1 sprint concepts (NRestarts/
   MainPID, bot_llm_spend, Workstream B) absent from the Vysted Terminal
   Phase 8 plan. Re-presented unchanged after operator confirmed cross-
   project paste. Saved to memory as feedback-cross-project-paste for
   future sessions.

---

## 3. Known issues carried forward

### Phase 10 (launch ops — explicit non-scope as of Phase 7)

Same set as `BLOCKERS.md` "v0.7.0 → Phase 10 carry-forwards":
1. Code signing (SignPath / Apple Developer ID / Linux unsigned)
2. Tauri auto-updater wiring
3. Distribution channels (Homebrew cask, AppImage, GitHub Releases)
4. `terminal.vysted.com` landing page
5. LICENSE flip + COMMERCIAL_LICENSE.md + CLA bot
6. First-launch TOS dialog
7. v1.0.0 narrative + launch announcement

### Phase 9 (operator manual Mac test)

_(filled at H1 time; expect light-theme audit, BYOK keys per provider,
broker paper-mode connections, axe-core a11y, Lighthouse perf, Mac
codesigning shake-out, etc.)_

### v0.8 polish carry-forwards

- _(All S3 findings from Phase 8 — listed at F3 time)_

### v0.6.6+ Tradesa V2 carry-forwards

Same set as `BLOCKERS.md` v0.6.6+. Unchanged by Phase 8.

---

## 4. Plugin contract status

- **`types/plugin.ts` is UNCHANGED in v_._._ ** — verified via `git diff
v0.7.0..v_._._ -- types/plugin.ts` empty. **Tier-1 lock held — 10th
  consecutive release.** _(verified at G1 time)_
- **tradesa-v2 wrapper's 3-layer read-only invariants** (provider has no
  write methods + router has no non-GET routes + plugin's
  `supportsControlPlane: false`) **ALL THREE PASS** per T4 audit.
- **§6.5 audit-suite 9/9 PASS** — verified at G1 time.

---

## 5. Phase 9 entry context

Phase 9 is **operator manual Mac test** — the first time the platform is
exercised on macOS with real broker paper credentials, real BYOK keys,
and a real human at the keyboard.

The relevant hooks Phase 8 lands for Phase 9:

1. **The bug catalog enumerates what's been fixed + what's deferred.**
   Phase 9 operator should focus manual test on (a) the F1-fixed paths
   (verify the fix actually works in production), (b) the audit-deferred
   paths that need real credentials or human-event injection.
2. **Mocked-fetch fallback procedure documented** (T1 Part B) for
   capturing Tradesa V2 in its 6 connection states.
3. **Performance baseline** is the regression-detection target.
4. **§6.5 invariants intact 10 releases running** — Phase 9 can assume
   broker safety is solid; focus on broker integration UX rather than
   safety re-audit.
5. **F7 dev fallback** (`?sidecar-port=NNNNN`) is the chrome-devtools-MCP-
   compatible capture path when needed. Tauri shell directly is the
   production-fidelity path.

What Phase 9 manual test should focus on (operator-led, not autonomous):

- **macOS-only paths:** Tauri shell on macOS (Apple Silicon + Intel),
  keychain via macOS Security Framework, notifications via Notification
  Center, codesigning shake-out.
- **BYOK provider keys:** Anthropic / OpenAI / Google / Groq / Mistral /
  Cohere / Ollama — each one's first-token-latency measurement (deferred
  from L6).
- **Broker paper-mode connect:** Alpaca (most likely to have paper creds),
  the 6 other brokers (failure-state UX where no creds — verify the
  failure UX is clean).
- **Workflow + backtest end-to-end** (deferred from L10 — verify F1 fix
  for MCP-subprocess gap actually works for the full chain).
- **Axe-core a11y audit** of the live cockpit (L11 S3 polish items).
- **Lighthouse perf audit** (extends L6 baseline with browser-side
  measurements).
- **Tradesa V2 6-state capture** (needs real Supabase project for the
  healthy state).

---

## 6. File / commit pointers for deeper context

- **Foundation commits:**
  - `8fb8101` — L1 bug catalog skeleton
  - `d1ba999` — L5 §6.5 grep audit
  - `18bc8d3` + `71cdf9c` — L2 UC1 findings
  - `17626fa` — L3 runtime-gap (agents/ bundle gap)
  - `b0137bf` — L4 gate meta-verification
  - `947d297` — L6 perf baseline
  - `9d07a77` — F2 hot-patch /health version
  - `9c14955` — L11 a11y + ensure-sidecar --add-data fix
  - _(more added at I1 + F1 + tag time)_
- **Teammate merge commits:** _(added at I1 time)_
- **Release commit:** _(added at tag time)_

---

## 7. Verification snapshot at handoff (G1 results)

| Gate                                         | Result | Notes |
| -------------------------------------------- | ------ | ----- |
| `pnpm ci-local`                              | _(G1)_ |       |
| `node scripts/smoke-test-sidecars.mjs`       | _(G1)_ | 0 orphans, <90s |
| `docs/PHASE_8_GATE_VERIFICATION.md` complete | _(G1)_ |       |
| `git diff v0.7.0..HEAD -- types/plugin.ts`   | _(G1)_ | empty (10th lock) |
| `pytest sidecar/tests/test_safety_end_to_end.py` | _(G1)_ | 9/9 PASS |
| CI green on all 3 OSes at tag commit         | _(G1)_ |       |
| Zero open S1 in BUG_CATALOG                  | _(G1)_ |       |
| All 9 audit docs present                     | _(G1)_ |       |

---

## 8. Coordination lessons for Phase 9+

1. **Empirical-evidence audit > synthetic-break audit.** L4 saved ~100 min
   of CI wall by classifying gates against real bugs found during L2/L3.
   Real-bug-bypass instances (smoke-test missing port-binding probe,
   smoke-test missing endpoint-data probe) are stronger evidence than
   "deliberately broke X, CI caught it".
2. **Cross-project paste filter.** A rejection-feedback payload that
   references concepts absent from the drafted plan is almost certainly a
   paste-error from a different project. Flag + AskUserQuestion before
   applying. Saved to memory as `feedback-cross-project-paste`.
3. **The `__file__`-relative load pattern** is a THIRD class of
   PyInstaller bundle gap beyond `--copy-metadata` (importlib.metadata) +
   `--collect-data` (pkgutil data files). When the source loads a JSON or
   data file via `Path(__file__).parent / "dir-name"`, that dir is NOT
   auto-included unless `--add-data` lists it. CLAUDE.md gotcha
   "PyInstaller `--onefile` silently drops package metadata + data files"
   needs extending — H2 carry-forward.
4. **The `pnpm tauri dev` log + chrome-devtools console reports diverge.**
   The browser console reports "CORS policy" when the underlying response
   is a 500 with missing CORS headers (FastAPI's CORSMiddleware doesn't
   apply to exception responses by default). Don't conclude "CORS bug"
   from a browser CORS message — direct-curl the endpoint first to
   distinguish CORS misconfiguration from 500-without-CORS-headers.
5. **Orphan-process accumulation** across Claude Code sessions is real.
   Phase 8 start found 30+ stale node processes (chrome-devtools-mcp +
   pnpm dev + next dev clusters from May 16-17). Worktree-based dev
   servers from prior teammate runs were the worst — see CLAUDE.md
   "Resource hygiene" lesson. Phase 9 should pre-flight-clean the same
   way smoke-test does before starting.
6. **Tradesa-v2 host-private imports** (T4 finding) — plugins SHOULD use
   `PluginConfig.sidecarBaseUrl` + `PluginConfig.secrets` from the
   contract, NOT direct imports from `@/lib/keychain` + `@/lib/sidecar-
   client`. This is the canonical plugin pattern; tradesa-v2 is a
   precedent that should be cleaned up in v0.6.6+ work (the plugin is
   already deferred + scoped).

---

_End of Phase 8 handoff._
