# Phase 8 — Bug Catalog (Living Document)

**Sprint:** Phase 8 — Claude-Code-driven deep audit against the v0.7.0 surface.
**Baseline commit:** `005a8d0` (housekeeping `5325528` on top of v0.7.0 release
commit `3f4c9de`).
**Sprint window opened:** 2026-05-18.

This document is updated progressively as audit dimensions surface findings.
Skeleton first; commit per dimension as findings land. If the session dies or
auto-compacts, the catalog survives in git history and is the canonical
re-orientation surface (`git log -- docs/PHASE_8_BUG_CATALOG.md` shows the
order of arrival).

---

## How to use this document

Every audit dimension (L1–L11 lead + T1–T5 teammates) appends findings to its
own section using a single canonical entry format:

```
### Finding <prefix>-<id>: <title> [S<severity>] [status: <state>]

**Repro:** <minimum steps to surface the issue>
**Impact:** <what the user sees / what's broken / what's at risk>
**Suggested fix:** <one paragraph — the specific intervention>
**Files:** <path:line references>
**Notes:** <optional caveats, links to related findings, etc.>
```

- `<prefix>` is the audit dimension tag: `UC1`–`UC5` for the use-case exercise,
  `L3`/`L4`/`L5`/`L6` for the lead audit dimensions producing findings here,
  `L8`–`L11` for the lead's concurrent dimensions, `T1`–`T5` for teammate
  audits (cross-referenced — primary detail lives in their own doc), `X` for
  cross-cutting / audit-introduced findings.
- `<id>` is a short stable slug (`fastmcp-runtime`, `kill-switch-toggle-react-warn`,
  etc.) chosen at write-time. Numbering is fine too (`UC1-01`, `UC1-02`).
- Severity `S1`–`S4` per the scheme below.
- Status starts `open`; transitions to `fixed <sha>` / `hot-patched <sha>` /
  `deferred-S3` / `deferred-S4` / `no-repro` / `wontfix` as the fix loop
  progresses.

The **Fix log** at the bottom maps each commit SHA back to its finding(s) for
easy audit during the morning operator review.

---

## Severity scheme

| Level  | Definition                                                                              | Action this sprint                |
| ------ | --------------------------------------------------------------------------------------- | --------------------------------- |
| **S1** | Blocks ship — broken UC flow, runtime crash, §6.5 violation, contract violation, gate-bypass | **Fix this sprint** (mandatory)   |
| **S2** | Visible-to-user bug, broken non-load-bearing feature, hot-patch-worthy audit finding    | Fix if cheap (<30 min, no Tier-1) |
| **S3** | Polish, technical debt, low-impact UX defect, strict-lint-mode noise                    | BLOCKERS.md → v0.8.x backlog      |
| **S4** | Carry-forward to Phase 9 manual Mac test / Phase 10 launch ops / v1.x                   | BLOCKERS.md → matching section    |

**Automatic-S1 categories** (any finding here is S1 regardless of triviality):

- §6.5 architectural drift (L5 findings)
- Tier-1 LOCKED file would be modified (route via BLOCKERS.md → next phase)
- Gate that should have caught a class of bug doesn't (L4 findings on a missed
  gate)
- Plugin contract Tier-1 (`types/plugin.ts`) violation
- Runtime crash on sidecar-tool exercise

## Tag-selection criterion

Tier-2 decision deferred to end of fix loop. Count of S1 fixes (`git log --oneline
v0.7.0..HEAD | grep -c '^[a-f0-9]\+ fix(phase-8/'`) determines the tag prefix:

- **0 S1 fixes** → `v0.7.1` (audit-only release; value is the documentation +
  meta-verification proof + carry-forward list)
- **1+ S1 fixes** → `v0.8.0` (substantial S1 fixes shipped)

---

## §10 UC1 — Solo Founder's Quant Day

Exercise: Tradesa V2 wrapper panels (READ-ONLY) → AI Risk Analyst review →
backtest a strategy.

**Exercise environment:** `pnpm tauri dev` (PID 69468) + Chrome via
chrome-devtools MCP at `http://localhost:3000/?sidecar-port=54108`
(F7 fallback path). Main sidecar `127.0.0.1:54108`; openbb-mcp claimed at
`:54109`; sec-edgar-mcp claimed at `:54111`; ports per `[openbb-mcp]
subprocess spawned on 127.0.0.1:54109` log line at boot.

### Finding UC1-fundamentals-500 [S1] [status: fixed-downstream-degraded]

**Repro:**
1. `pnpm tauri dev`, wait for `[vysted] Python sidecar healthy on
   127.0.0.1:NNNNN` log line.
2. In any webview (Tauri or Chrome at `?sidecar-port=NNNNN`), open Equity
   Overview tab, enter `AAPL`, click Load.
3. Equity Overview header populates (price+change from `/quotes/AAPL`).
4. **All 5 fundamentals sections (Valuation Ratios, Analyst Ratings, Income
   Statement, Balance Sheet, Cash Flow) show "Unavailable".**
5. `curl http://127.0.0.1:NNNNN/fundamentals/AAPL` returns **HTTP 500
   Internal Server Error** with body `Internal Server Error`.
6. Sidecar log shows full traceback: `routers/fundamentals.py:45 → services/
provider_registry.py:62 → services/openbb_mcp_provider.py:364 →
openbb_mcp_provider.py:244 _call_tool → services/mcp_client.py:165
call_tool → 124 _ensure_session → 111 _open → asyncio/tasks.py:507
wait_for → mcp/client/session.py:171 initialize → mcp/shared/session.py:
292 send_request → anyio/streams/memory.py:125 receive → asyncio/locks.py:
213 wait → **`asyncio.exceptions.CancelledError: Cancelled via cancel
scope`**.`
7. Secondary error: `RuntimeError('Attempted to exit cancel scope in a
   different task than it was entered in')`.

**Impact:** Every fundamentals-using surface broken — Equity Overview empty,
AI Risk Analyst (UC1) can't use fundamentals tool, Research Workflow (UC2)
fails, Academic Researcher (UC4) partial, Screener (Phase 6) likely fails.
This is a Tier-S1 blocker for UC2 + downstream of UC1's AI Risk Analyst
flow.

**Suggested fix:** The `mcp_client._open()` call to openbb-mcp's `:54109/mcp`
hangs because **the openbb-mcp subprocess is not actually listening on its
assigned port** (see UC1-openbb-mcp-not-listening below — the two findings
are linked). Fix the subprocess-port-binding root cause; verify the
`mcp_client._open()` survives the post-binding retry; consider tightening
the `_open` timeout so a stuck MCP subprocess surfaces as a 503/504 instead
of a 500 CancelledError after the request-handler-timeout fires.

**Files:**
- `sidecar/routers/fundamentals.py:45,51,57,69` — 4 endpoints, all 500
- `sidecar/services/openbb_mcp_provider.py:244,364`
- `sidecar/services/mcp_client.py:111,124,165`

**Notes:** Same anyio cancel-scope pattern documented in CLAUDE.md gotcha
"Spawn subprocess servers via Tauri Rust `Command::new`, not Python
`subprocess.Popen`" — but spawn-via-Rust is already in place here; the
deadlock is downstream of spawn (the binding step). The subprocess itself
is alive (PIDs 47292+64484 per `Get-Process vysted-openbb-mcp-sidecar`),
just not bound to its port.

### Finding UC1-openbb-mcp-not-listening [S1] [status: fixed-by-bb1c300 (port-bind probe; underlying deadlock = v0.8.x carry-forward)]

**Repro:**
1. After `pnpm tauri dev` boots, sidecar log claims `[openbb-mcp] subprocess
   spawned on 127.0.0.1:54109`.
2. `Get-Process vysted-openbb-mcp-sidecar` shows 2 processes alive
   (bootloader + worker child — normal PyInstaller `--onefile` shape).
3. `Get-NetTCPConnection -State Listen -LocalPort 54109` returns **empty**
   — nothing listening on the claimed port.
4. `curl http://127.0.0.1:54109/health` returns
   `Failed to connect to 127.0.0.1 port 54109 after 2039 ms: Could not
connect to server`.
5. `curl http://127.0.0.1:54108/openbb-mcp/status` returns
   `{"available":true,"endpoint":"http://127.0.0.1:54109/mcp",
"lastToolCallOk":null,"lastError":null}` — the **main sidecar lies** about
   subprocess health; "available" returns true even though the subprocess
   is not actually serving.

**Impact:** Direct cause of UC1-fundamentals-500. Every MCP-routed feature
(fundamentals, ratings, macro, earnings, options, screener, bonds, yield
curve, analyst ratings) likely broken. Same likely applies to sec-edgar-mcp
(see UC1-sec-edgar-mcp-not-listening below). Phase 6 modules (Macro / SEC /
Earnings / Analyst Ratings / Screener / Quant) all affected. **UC2, UC4,
UC5 cannot complete; UC1 AI Risk Analyst tool-use partial; UC3 earnings
calendar fails.**

**Suggested fix:** Two paths to investigate:
1. **MCP subprocess deadlocks during port-bind.** Add a `--port` arg-echo
   on startup so the subprocess prints `[openbb-mcp] bound on port NNNN`
   only AFTER successful bind, and Tauri Rust polls for that line before
   declaring spawn success.
2. **Health-probe the subprocess from Tauri Rust** before returning from
   spawn. Rust currently spawns and trusts; should poll the subprocess's
   `/mcp` endpoint up to ~10 s.

The `/openbb-mcp/status` "available" check should ALSO probe the
subprocess's port, not just `subprocess.poll() is None` (or whatever the
shallow check is).

**Files:**
- `src-tauri/src/openbb_mcp.rs` (Rust spawn lifecycle)
- `sidecar/services/openbb_mcp_provider.py` (status probe)

**Notes:** Smoke-test in `scripts/smoke-test-sidecars.mjs` only checks "is
alive after 10 s" — doesn't probe binding. This finding is also a gap in
the smoke-test gate; **L4 meta-verification should add a `verify-port-
binding` step** (per Phase 8 plan). Also flagged: F2 candidate for smoke-
test enhancement.

### Finding UC1-sec-edgar-mcp-not-listening [S1] [status: fixed-by-bb1c300 (port-bind probe; underlying deadlock = v0.8.x carry-forward)]

**Repro:**
1. After `pnpm tauri dev` boot, sidecar log shows `[sec-edgar-mcp]
   subprocess spawned on 127.0.0.1:54111`.
2. `Get-Process vysted-sec-edgar-mcp-sidecar` shows 2 processes alive
   (bootloader + worker child).
3. `Get-NetTCPConnection -State Listen -LocalPort 54111` returns empty.
4. `curl http://127.0.0.1:54111/mcp` connection refused.

**Impact:** SEC filing fetches (Phase 6 SEC module) fail. UC4 Academic
Researcher (custom agent + SEC + sentiment) **cannot complete** because the
SEC tool can't be invoked through the agent.

**Suggested fix:** Same root cause + fix as UC1-openbb-mcp-not-listening.
Same `src-tauri/src/sec_edgar_mcp.rs` (analogous to `openbb_mcp.rs`) needs
the post-bind health probe.

**Notes:** sec-edgar-mcp doesn't have an HTTP `/status` endpoint exposed
through the main sidecar — `/sec-edgar-mcp/status` returns 404. That's
itself a minor S3 (asymmetry with `/openbb-mcp/status`) but the L9 broker
section / a separate cross-cutting entry is the right place.

### Finding UC1-health-version-stale [S2] [status: fixed pending-rebuild]

**Repro:** `curl http://127.0.0.1:54108/health` returns
`{"status":"ok","service":"vysted-sidecar","version":"0.2.1",...}`. Project
is at v0.7.0+. **Version drift = 5 releases.**

Root cause: `sidecar/routers/health.py:18` hardcodes `"version": "0.2.1"`.
The CLAUDE.md release-bump checklist names `sidecar/app.py FastAPI(version=
...)` — that string IS at 0.7.0 (correct) — but the actual `/health`
endpoint returns from `routers/health.py:18` which is independent and was
never bumped.

**Impact:** Any consumer reading `/health.version` (CI smoke-test, an
operator's diagnostic curl, the auto-updater, a third-party plugin) sees a
stale version. The auto-updater isn't wired yet (Phase 10) so the immediate
blast radius is small but the misreport is misleading.

**Suggested fix:** One-line change in `routers/health.py` — replace
hardcoded string with dynamic lookup from `app.version` (inject via
`Depends` or `request.app.version`). One-commit hot-patch candidate (F2).

**Files:**
- `sidecar/routers/health.py:18` (the stale hardcode)
- `sidecar/app.py:140` (the correct, current source of truth)

**Notes:** CLAUDE.md release-bump checklist should be **extended** to
"…sidecar/app.py FastAPI(version=…) AND sidecar/routers/health.py:18
hardcode…" so the next release lead bumps both. H2 carry-forward.

### Finding UC1-cors-error-masks-500 [S3] [status: open]

**Repro:** Browser console reports `Access to fetch at 'http://127.0.0.1:
54108/fundamentals/AAPL' from origin 'http://localhost:3000' has been
blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
on the requested resource.`

Root cause: the underlying response IS a 500. FastAPI's `CORSMiddleware`
(configured at `sidecar/app.py:145-149` with `allow_origins=["*"]`)
**does not add CORS headers to exception/error responses** by default. The
500 response has no `Access-Control-Allow-Origin`, so the browser
classifies it as a CORS rejection. The actual cause (500 from
`fundamentals` openbb-mcp deadlock) is hidden behind this misleading CORS
message.

**Impact:** Diagnostic delay — operator sees "CORS error" + assumes
fallback-path CORS bug; actually backend 500. Adds ~10 min to root-cause
analysis. **Found this myself in the L2 walk** — could affect Phase 9
operator manual test.

**Suggested fix:** FastAPI's CORS middleware can be configured to also
handle errors via custom exception handler that returns CORS headers. Or
swap the order of middleware so CORS wraps every response including 500s.
Or document the gotcha in CLAUDE.md so the next operator doesn't get
fooled. The first is a real fix; the third is an acceptable S3 mitigation.

**Files:**
- `sidecar/app.py:145-149` (CORSMiddleware config)

**Notes:** This is purely a developer-experience issue — once Tauri webview
runs in production it doesn't see the CORS error because the Tauri shell's
fetch behavior differs from raw Chrome. S3 because operator-only.

### Finding UC1-tradesa-v2-fallback-invoke-error [S3] [status: open]

**Repro:** In the F7 dev fallback (Chrome at `?sidecar-port=NNNNN`), open
Command Palette (Ctrl+K) → "Tradesa V2: Open Positions". Panel mounts but
the status strip shows:
- Status: "Supabase error"
- Message: "Cannot read properties of undefined (reading 'invoke')"
- Alert: "Supabase unreachable — Cannot read properties of undefined
  (reading 'invoke')"

Root cause: the Tradesa V2 connection adapter tries to read the Supabase
URL + service-role key from the OS keychain via the Tauri command
`invoke('keychain_get', ...)`. In standalone Chrome, `__TAURI_INTERNALS__`
is undefined and the `invoke` accessor throws.

**Impact:** Audit-environment only. The Tauri shell itself shows different
state (the canonical "unauthenticated" or "healthy" state depending on
whether the operator has set the Supabase creds). For the Chrome F7
fallback path, the UX surface is a JavaScript runtime error rather than a
clear "Keychain unavailable — open in Tauri shell" message.

**Suggested fix:** In `plugins/tradesa-v2/connection.ts` (or the
keychain-reading helper), wrap the `invoke()` call in a try/catch that
detects "running outside Tauri" (already gated via `__TAURI_INTERNALS__`
in `sidecar-client.ts` — same pattern needed here) and produces a
user-friendly status: "Keychain unavailable (running outside Tauri)".

**Files:**
- `plugins/tradesa-v2/connection.ts` (where it calls `invoke`)
- Reference for the pattern: `src/lib/sidecar-client.ts:52-62` (F7 fallback
  gate)

**Notes:** Same `__TAURI_INTERNALS__` guard pattern as the F7 sidecar
fallback could be extended to plugin-level keychain access; would also
benefit any future BYOK plugin reaching for OS keychain. S3 because the
Tauri shell shipped product doesn't have this issue.

### Finding UC1-ai-help-renders-correctly [no finding, observation]

`/help` slash command in AI Assistant renders the full cheat-sheet:

```
/ask <prompt> — raw chat with the default provider
/agent <id> <prompt> — invoke a specific agent with focused-panel context
/provider <id> — switch the default provider (anthropic, openai, …)
/key set <provider> — store a BYOK API key in the OS keychain
/clear — clear the current conversation
/help — show this cheat-sheet
```

Slash-command system works in the F7 fallback (rendering layer; the BYOK
provider routes require Tauri keychain so `/ask` itself would fail without
keys — covered in L8).

### Finding UC1-canvas-chart-renders [no finding, observation]

Chart panel renders SPY 1d data via lightweight-charts canvas. 3 indicators
(MA / VWAP / Bollinger Bands) activate via toolbox buttons without error.
Canvas drawing tools rendered in toolbox but per CLAUDE.md gotcha
"chrome-devtools MCP cannot synthesize trusted user events" cannot be
exercised headless — covered by Playwright real-event suite (v0.5.1+
carry-forward per BLOCKERS.md).

### Hypothesis: UC2 / UC4 / UC5 cannot complete due to MCP-subprocess gap

UC2 Research Workflow depends on `/fundamentals/*` (broken per
UC1-fundamentals-500). UC4 Academic Researcher needs `/sec/*` (depends on
sec-edgar-mcp subprocess which isn't listening per
UC1-sec-edgar-mcp-not-listening). UC5 Macro Thesis Watcher needs
`/macro/*` and other openbb-mcp-routed endpoints (depends on openbb-mcp
which isn't listening per UC1-openbb-mcp-not-listening).

**These 3 UCs cannot pass until the MCP-subprocess port-binding root cause
is fixed.** F1 fix loop will attempt the fix; if it requires multi-file
Rust changes (likely `src-tauri/src/openbb_mcp.rs` + `sec_edgar_mcp.rs`),
this becomes a tag-defining S1.

Recording as a single hypothesis here so the catalog doesn't accumulate
3× redundant findings for the same root cause. Per-UC verification will
add cross-references in their respective sections only if a NEW finding
surfaces beyond the MCP gap.

## §10 UC2 — Research Workflow

Exercise: cmd+K → "Research XYZ" → AI Researcher pulls data → chart + news in
adjacent panels → backtest dividend strategy → save workspace.

_(empty — L2 fills)_

## §10 UC3 — Earnings Playbook

Exercise: node-editor workflow → AI thesis per earnings name → alert on entry
trigger → desktop notification → review thesis.

_(empty — L2 fills; Phase 7 F8 desktop-notification bridge is the new
load-bearing surface here)_

## §10 UC4 — Academic Researcher

Exercise: custom agent → workflow pulls SEC + sentiment → outputs to chart →
workspace becomes reproducible dissertation methodology.

_(empty — L2 fills; v0.7.0 sec-edgar-mcp `--collect-data=edgar` is the new
load-bearing surface)_

## §10 UC5 — Macro Thesis Watcher

Exercise: yield curves + central bank tracker + commodity dashboard → AI Macro
Researcher monitors news → notifications on thesis-confirming events.

_(empty — L2 fills; Phase 6 macro module is the substrate)_

---

## L3 — Sidecar runtime-gap findings

Smoke-test catches BOOT crashes; this dimension catches RUNTIME crashes
(sidecar boots, dies on first tool call because of dynamic file path that only
resolves at runtime). Scans for `importlib.resources`, `pkgutil.get_data`,
`__file__`-relative path joins, `pkg_resources.resource_*` in the main
sidecar + openbb-mcp + sec-edgar-mcp + their transitive deps.

### Finding L3-agents-dir-not-bundled [S1] [status: fixed-by-9c14955 (--add-data + ensure-sidecar.mjs); verified runtime — 12 agents served instead of 0]

**Repro:**
1. `curl http://127.0.0.1:54108/agents` returns **`[]`** (empty list).
2. `ls sidecar/agents/` shows **10 agent JSON files**: `buffett.json,
dalio.json, druckenmiller.json, graham.json, klarman.json, lynch.json,
marks.json, munger.json, portfolio_advisor.json, _schema.json`.
3. `agent_runtime.py:49` constructs `AGENTS_DIR = Path(__file__).resolve().
parent.parent / "agents"`. In PyInstaller `--onefile`, `__file__` lives
   inside `_MEI*/services/`, so `.parent.parent + "agents"` resolves to
   `<_MEI>/agents/`.
4. The PyInstaller invocation in `scripts/ensure-sidecar.mjs` has **NO
   `--add-data=agents:agents`** or equivalent. The `agents/` directory is
   not a Python package (no `__init__.py`), so PyInstaller's auto-discovery
   skips it.
5. At runtime, `agents_dir.exists()` returns False (line 68 of
   `agent_runtime.py`) → `_discover_specs` returns `{}` → `/agents`
   endpoint returns `[]`.

**Impact:** **Every named first-party agent is unavailable in production.**
This is the AI Risk Analyst from UC1, the AI Researcher from UC2, the
Strategy Critic from the backtest flow, every named agent the operator
or user expects to invoke. The agent picker in the chat sidebar shows
"No agent (raw chat)" as the only option. Slash commands `/agent <id>`
fail with "agent not found".

This is the **third silent-runtime-broken-release** pattern after v0.6.5
fastmcp + v0.7.0 sec-edgar data files. The smoke-test gate boots the
binary + curls /health → 200 OK; an empty /agents response does not
look like a "crash", so the gate misses it.

**Suggested fix:** Add `--add-data` (or `--add-data` equivalent path
syntax for the PyInstaller invocation) to copy the agents JSON files:

```javascript
// scripts/ensure-sidecar.mjs, near the hidden/copyMeta blocks:
const addData = [
  ["agents", "agents"],   // src:dest pair; src is sidecar/agents, dest is bundled root
].map((p) => `--add-data=${p[0]}${isWin ? ";" : ":"}${p[1]}`).join(" ");
// then add ${addData} to the run() command above.
```

Note: PyInstaller's `--add-data` syntax differs between Windows
(`SOURCE;DEST`) and POSIX (`SOURCE:DEST`). Use `isWin` to pick the right
separator.

**Files:**
- `sidecar/services/agent_runtime.py:49` (the `__file__`-relative lookup)
- `sidecar/services/agent_runtime.py:62-99` (`_discover_specs` silently
  empty path)
- `sidecar/agents/*.json` (the 10 files that need bundling)
- `scripts/ensure-sidecar.mjs` (the fix target — add `--add-data`)
- `sidecar/tests/test_agent_runtime.py:54` (test computes
  `_REAL_AGENTS_DIR` from source layout — passes in source mode, but
  doesn't exercise the bundled binary's `_MEI` resolution)

**Notes:** Pattern in CLAUDE.md gotcha "PyInstaller `--onefile` silently
drops package metadata + data files" is the precedent. The bullet lists
"importlib.metadata.version(...)" (→ `--copy-metadata`) and "non-Python
data files loaded via pkgutil" (→ `--collect-data`) — but plain-dir-
adjacent JSON files via `__file__`-relative lookup is a THIRD pattern not
covered by the existing gotcha. CLAUDE.md needs an extension for `--add-
data` cases. H2 carry-forward.

The agent_runtime audit-test `test_agent_runtime.py:54` uses a
`_REAL_AGENTS_DIR` that's computed differently than the production path
- so the test passes but doesn't catch the bundle gap. **L4 meta-
  verification should add a deliberate-break case for this gap**: temporarily
  remove `sidecar/agents/buffett.json`, push, verify the test catches it,
  revert. If the test doesn't catch it, the test gap is itself S2.

### Finding L3-smoke-test-empty-data-gap [S2] [status: open]

**Repro:** the smoke-test in `scripts/smoke-test-sidecars.mjs` checks for
two states:
1. **Main sidecar:** binds + `/health` returns 200 within 60 s ✅ (the
   v0.6.5 fastmcp regression class)
2. **MCP subprocesses:** alive after 10 s ✅ (very shallow — doesn't even
   check port binding per UC1-openbb-mcp-not-listening)

Neither check verifies that load-bearing endpoints return non-empty,
correct data. `/agents` returning `[]` is "OK" by the current gate.

**Impact:** The smoke-test only catches the narrow class of bugs where the
binary outright crashes during boot. Soft failures — endpoint returns
empty list / 500 / wrong data — pass the gate.

**Suggested fix:** Extend `scripts/smoke-test-sidecars.mjs` to also probe:
- `/agents` returns at least 1 agent (count > 0)
- `/openapi.json` includes specific route prefixes (`/fundamentals/`,
  `/sec/`, `/macro/`, etc.)
- `/openbb-mcp/status` returns `available: true` **AND** the claimed
  endpoint actually listens (TCP probe to `<endpoint>/mcp`)
- `/sec-edgar-mcp/status` (currently 404 — needs to be added per
  UC1-sec-edgar-mcp-not-listening notes) returns analogous status with
  TCP probe

This is the **L4 meta-verification recommendation made concrete**: when
the next class of silent-runtime regression ships, this smoke-test
strengthening is what catches it.

**Files:**
- `scripts/smoke-test-sidecars.mjs:248-300` (the main-sidecar probe)
- `scripts/smoke-test-sidecars.mjs:302-339` (the MCP-subprocess probe —
  has the shallowest check)

### Finding L3-screener-universes-status [no finding, observation]

`sidecar/services/screener_universes/__init__.py` is a Python package with
3 JSON files (`crypto_top50.json`, `nifty50.json`, `sp500.json`) and uses
`importlib.resources` to load. PyInstaller's `--onefile` auto-discovers
imported packages and includes their data files via its `pkgresources`
hook by default. **No finding here** — package-data-bundled-with-package
works correctly out of the box (different from the `agents/` plain-dir
case above).

Verified: `curl /screener/universe` doesn't 404 on the wrong path (just
returns the same "Not Found" pattern); the actual screener route prefix
is `/screener/run` and `/screener/universe`. Not exercised this session.

### Finding L3-fastmcp-fastmcp-slim-double-pin [S3] [status: open]

**Repro:** `scripts/ensure-openbb-mcp-sidecar.mjs:142-154` includes both
`fastmcp` and `fastmcp-slim` in `--copy-metadata`. The two are aliases —
`fastmcp-slim` was an older split that's now the same package. Either
both will succeed redundantly (low cost) or one will raise
`PackageNotFoundError` and the build will fail.

The build succeeded May 16 so currently fine. But the redundant pin adds
fragility — if `fastmcp-slim` is removed from PyPI or marked stale, this
breaks.

**Impact:** Cosmetic / cleanup. S3.

**Suggested fix:** Remove `fastmcp-slim` from the `--copy-metadata` list.

**Files:**
- `scripts/ensure-openbb-mcp-sidecar.mjs:143-144`

### Hypothesis carry-forward to L4

L3 found one new class of runtime gap (`--add-data` for plain dirs not
covered by CLAUDE.md gotcha). L4 meta-verification should deliberately
break the `agents/` bundle inclusion + verify smoke-test catches it. If
smoke-test doesn't catch (which it currently won't), this becomes a
forcing-function S1 for extending the gate.

## L4 — Meta-verification gate findings

Deliberate breakages on a throwaway branch; each gate must fail loud with a
clear error. Detail lives in `docs/PHASE_8_GATE_VERIFICATION.md`; any gate
that DIDN'T fire when it should have → finding here as automatic-S1.

_(empty — L4 fills)_

## L5 — §6.5 architectural drift

Grep-based audit of the broker-execution surface. Per CLAUDE.md "Defense-in-
depth for safety-critical surfaces": type-level gate + DB-enforced invariant +
grep-able audit check. This dimension is the grep-able audit; any finding is
automatic-S1.

**Audit complete — zero findings, architectural surface clean.**

Patterns checked (each grep + manual analysis):

1. **New public methods on `broker_base.py`?** No. Public surface = 11 documented members:
   - Properties: `mode`, `read_only`, `connected`, `state()`
   - State mutators (all audit-logged): `set_mode`, `set_read_only`, `connect`
   - Read-only: `account_info`
   - Order entry: `propose_order` (sync), `confirm_and_place` (async — sole `_place_confirmed` caller)
   - Order management: `cancel_order`

   _Note: my plan-doc listed `set_position_limits` as expected — that method does not exist; per-broker position limits are enforced at `propose_order` time via the per-adapter `CAPABILITIES` / position-limit class var. Spec misremember on my part, not a finding._

2. **New `_place_confirmed` call sites outside `confirm_and_place`?** No. Single production call site at `sidecar/services/broker_base.py:365` (inside `confirm_and_place`). All other matches are either definitions in the 7 per-broker overrides, docstrings, the test audit suite (`test_safety_end_to_end.py::test_audit_2_no_bypass_path_to_place_confirmed`), or comments. The grep-time audit at `test_safety_end_to_end.py:178` runs a recursive grep + filters out signatures + comments and asserts the suspicious-call-sites list is empty.

3. **New `audit_orders` UPDATE/DELETE write paths?** No. Only matches are intentional test paths at `tests/test_audit_log.py:141,156` and `tests/test_safety_end_to_end.py:268,274` that explicitly verify the SQLite triggers fire and raise `IntegrityError`. The append-only DDL (`sidecar/models/audit_log.py::AUDIT_LOG_DDL`) plus `PRAGMA query_only=ON` on the reader connection enforce the invariant; tests prove it.

4. **New backend-internal `confirm_and_place(human_confirmed=True)` paths with no UI surface?** No. All non-test matches resolve to `sidecar/routers/brokers.py:225` (the UI route handler) which passes `human_confirmed=request.human_confirmed` — the value comes from the UI POST body, not a backend hardcode. All other matches are inside the `sidecar/tests/` tree.

5. **New imports of broker internals from outside the broker package?** No. All matches are allowed callers:
   - `sidecar/routers/brokers.py:46,47,48` — the broker router
   - `sidecar/services/brokers/{registry,oanda,kite,ib,dhan,ccxt_exec,angelone,alpaca}.py` — inside-package adapters
   - `sidecar/tests/*` — test suite
   - `sidecar/services/audit_log.py:156` — false-positive match on a docstring quoting `from services.audit_log import` as text, not an actual import.

**§6.5 architectural invariants are intact 10 releases after the v0.5.0 audit.**

### Adjacent observation (NOT a §6.5 finding — separate dimension)

`brokers_registry.bootstrap_default_adapters()` only registers the 3 India
brokers (Dhan, AngelOne, Kite). The 4 non-India adapters (Alpaca, IB, OANDA,
ccxt-exec) exist as classes and are imported in
`sidecar/services/brokers/__init__.py` but no production code path
instantiates + registers them. The `registry.py` docstring claims "Other
teammates' adapters (Alpaca, IB, OANDA, ccxt-*) are wired through their own
`bootstrap_*` entrypoints" — those entrypoints do not exist. This is not a
§6.5 violation (safety enforcement is upstream of registry membership) but
**may surface as a UC1/L9 broker-connect finding**: any `/brokers/<non-India-
id>/...` request would raise `KeyError`. Recorded below in the cross-cutting
section for L9 to confirm at exercise time.

## L6 — Performance baseline anomalies

Detail lives in `docs/PHASE_8_PERF_BASELINE.md`. Findings here are
**anomalous** measurements only — a panel that takes 30 s to render, a
sidecar that 5×'es its memory in 60 s of polling, etc. Baseline numbers
themselves belong in the perf doc, not here.

_(empty — L6 fills if anomalies surface)_

## L8 — BYOK AI-agent end-to-end

Per-provider verification of the chat sidebar + tool-use round trip.

_(empty — L8 fills)_

## L9 — Broker connect + §6.5 cycle

Paper-mode broker exercise (whatever credentials are available on the
operator's machine) + failure-state UX for the brokers without credentials.
The full §6.5 propose → confirm → place → cancel cycle must produce an audit
log entry visible in the Audit Log panel.

_(empty — L9 fills)_

## L10 — Workflow + backtest cross-cutting

Every workflow template in the registry must run. Strategy Critic comments.
Equity curve. Trade log.

_(empty — L10 fills)_

## L11 — Accessibility + keyboard nav

Tab nav, screen-reader sanity, color-contrast WCAG AA spot-check on dark
theme.

**Approach:** spot-check via grep + chrome-devtools console messages. Full
a11y audit (axe-core, lighthouse, screen-reader walk-through) is deferred
to Phase 9 operator manual test where the Tauri shell can run with
real-event tooling.

### Finding L11-form-fields-missing-id-name [S3] [status: open]

**Repro:** chrome-devtools console at app boot reports
`[issue] A form field element should have an id or name attribute
(count: 10)`. 10 form fields (textboxes, comboboxes) across the cockpit
lack the basic `id` or `name` attribute that screen readers depend on for
labeling.

**Impact:** Screen reader users hear "Edit" or "Combobox" without the
context of what field it is. WCAG 2.1 SC 1.3.1 (Info and Relationships)
+ SC 4.1.2 (Name, Role, Value). S3 because no functional break + dark
theme + the visible field is usually adjacent labeled.

**Suggested fix:** Audit each `<input>`, `<textarea>`, `<select>` in
`src/components/*.tsx` + `src/modules/*/`. Add either `id` (matching a
sibling `<label htmlFor>`) or `name` (matching the semantic field name).
Shadcn/UI `Input` should auto-thread the `id` from the parent `Label`
context — check that's wired correctly.

**Files:** likely candidates per grep:
- Watchlist "Add symbol" textbox (`src/modules/watchlist/`)
- Portfolio entry form (5 textboxes — Symbol/Quantity/Cost basis/Class/Note)
- Equity Overview Symbol textbox
- Chart Compare textbox
- AI Assistant Chat input
- Command Palette search

### Finding L11-aria-label-coverage-low [S3] [status: open]

**Repro:** `grep -r 'aria-label=' src/components/` returns 4 matches across
~30 components (PluginManagerPanel, CommandPalette, KeyEntryDialog,
SettingsPanel). Many interactive elements rely on default semantics or
visible text. While `<button>X</button>` IS keyboard-accessible by
default, complex composite widgets (combobox + listbox, dialog with no
title, tab panels) need explicit ARIA labels.

**Impact:** Composite widgets without aria-label or aria-labelledby may
not announce themselves correctly. WCAG 2.1 SC 4.1.2. S3 because
shadcn/Radix UI components mostly provide good default ARIA semantics.

**Suggested fix:** Audit composite widgets (dialogs without explicit
titles, dropdowns, tab panels). Add `aria-label` or `aria-labelledby`
where shadcn/Radix's defaults don't suffice. Run an axe-core scan in
Phase 9 to find the specific gaps.

### Finding L11-keyboard-handlers-minimal [S3] [status: open]

**Repro:** `grep -r 'onKey(Down|Up|Press)=' src/components/` returns 1
match (CommandPalette). `grep -r 'tabIndex=' src/` returns 1 match
(`dialog.tsx`).

**Impact:** Custom keyboard behaviors (e.g. arrow-key nav in tab strips,
type-to-search in long lists) likely missing. Browser-default keyboard
nav (Tab to next focusable, Enter to activate) IS available, so users
can interact, but enhanced shortcuts (vim-style, J/K, arrow-key tab
strips) are not implemented.

**Impact:** S3 — default behaviors work; enhanced behaviors absent.

**Suggested fix:** Phase 9 / 10 polish — implement arrow-key nav in
tab strips (chart/equity-overview/tradesa-v2 tab group), arrow-key
navigation in watchlist/news lists. Not a v1.0 blocker.

### Finding L11-color-contrast-not-audited [no finding, observation]

WCAG AA color-contrast spot-check on dark theme: visible Tradesa V2 P&L
green/red on dark needs a contrast-ratio audit (tooling: WebAIM
contrast checker, axe-core, or Lighthouse). **Not run this session** —
deferred to Phase 9 with axe-core / Lighthouse against the live Tauri
shell.

### Summary

3 a11y findings, all S3 polish. No S1/S2 a11y blockers found. v1.0
ships with default-keyboard-and-aria-accessibility; v1.1+ polish should
address the form-field labeling + composite-widget ARIA + arrow-key nav.

---

## Teammate cross-references (T1–T5)

Each teammate's audit has a dedicated doc. Findings here are 1-line
cross-references with severity + status; primary detail lives in the
teammate's doc.

### T1 — Visual regression (`docs/PHASE_8_VISUAL_REGRESSION_REPORT.md`)

**Result: 0×S1, 1×S2, 5×S3.** All polish. Tier-1 contract: n/a (visual).

- **T1-header-absent [S2]:** OS titlebar `Vysted Terminal — vX.Y.Z —
  <Surface>` missing across all v0.7.0 captures. Already in v0.7.0 README
  acknowledged; Phase 9 closes.
- 5×S3: Equity Overview "Unavailable" hero (yfinance intermittency at
  capture); AAPL last in watchlist not first (BLOCKERS.md v0.8 #2);
  cockpit/ solo-Chart shot lacks 5-panel context + 2560 partner; non-hero
  pair shows empty Equity Overview.
- **Tradesa V2 6-state capture procedure** documented in Part B —
  Phase 9 reference.

### T2 — Python sidecar audit (`docs/PHASE_8_SIDECAR_AUDIT.md`)

**Result: 0×S1, 4×S2, 1×S3, 2×S4.** No yanked packages. One transitive
CVE (autobahn==19.11.2, S3, unused code path).

- **T2-dead-earnings-ternary [S2]:** `earnings_provider.py:253` has
  `eps_stddev = _num(row.get("growth")) if False else None` — literal
  dead code; `eps_stddev` always `None`, silently falling back to high/low
  approximation. Affects Strategy Critic input quality.
- **T2-mypy-llm-override [S2]:** 4 LLM adapters declare `async def
stream_chat(...) -> AsyncIterator`; ABC returns `Coroutine[..., AsyncIterator]`.
  Incompatible override. Fix: remove `async` from ABC.
- **T2-mypy-macro-provider-literal [S2]:** 4 macro providers declare
  `PROVIDER = "<string>"` as untyped `str`, but `MacroCatalogEntry.provider`
  expects `Literal["fred"|"ecb"|"imf"|"world-bank"]`. Annotate.
- **T2-mypy-fred-frequency-literal [S2]:** `fred_provider.py` passes raw
  `str | None` where `Literal[frequency]` is expected.

### T3 — Rust audit (`docs/PHASE_8_RUST_AUDIT.md`)

**Result: 2×S1 (addressed by F1), 3×S2, 7×S3, 3×S4.** cargo audit
**CLEAN** (0 CVEs). cargo clippy strict CLEAN. cargo udeps CLEAN. cargo
fmt CLEAN. nightly rustc -W dead_code CLEAN.

- **T3-openbb-spawn-incomplete + T3-sec-edgar-spawn-incomplete [S1]:**
  **ADDRESSED in F1 commit `bb1c300`** — port-bind probe before declaring
  subprocess healthy. Same as catalog finding
  UC1-openbb-mcp-not-listening + UC1-sec-edgar-mcp-not-listening.
- **T3-significant-drop-scrutinee [S2]:** 3 `kill()` closures hold
  `MutexGuard` through `if let Some(...) = state.0.lock().unwrap().take()`
  body. Not a live deadlock; clippy::nursery footgun. One-line fix each.
- **T3-glib-unsound + T3-rand-unsound [S2]:** Linux-only transitive
  advisories (wry→gtk via glib; keyring→secret-service→zbus via rand
  0.8.5). Awaiting upstream fixes; no Vysted source triggers either.

### T4 — Plugin contract + plugin runtime (`docs/PHASE_8_PLUGIN_AUDIT.md`)

**Result: 0×S1, 3×S2, 3×S3, 1×S4.** **Tier-1 contract `types/plugin.ts`
lock CONFIRMED — 10th consecutive release.** tradesa-v2 3-layer
read-only invariants **ALL THREE PASS** (provider no-write methods,
router no-non-GET routes, `supportsControlPlane: false`).

- **T4-brokers-not-registered [S2]:** all 7 broker plugins (alpaca,
  angelone, ccxt-exec, dhan, ib, kite, oanda) absent from
  `BUNDLED_PLUGINS` in `src/lib/plugin-bootstrap.ts`. Their cmd+K
  commands + data sources silently unavailable. **Same root cause as
  catalog X-broker-bootstrap-india-only** — the broker plugins exist but
  aren't bootstrapped at runtime. Cross-reference: also affects
  `bootstrap_default_adapters` (only India brokers).
- **T4-connection-keychain + T4-settings-dialog-keychain [S2]:**
  `plugins/tradesa-v2/connection.ts` + `TradesaSettingsDialog.tsx`
  import from host-private `@/lib/keychain` + `@/lib/sidecar-client`.
  Should use `PluginConfig.sidecarBaseUrl` + `PluginConfig.secrets`
  from contract. v0.6.6+ Tradesa V2 carry-forward.
- T4-ccxt-executecommand-dead, T4-bare-commandids,
  T4-kite-manifest-unknown-field [S3], T4-host-version-stale [S4].

### T5 — Coverage + docs truth-alignment (`docs/PHASE_8_COVERAGE_AND_DOCS_AUDIT.md`)

**Part A coverage:** 20 findings (3×S1, 10×S2, 7×S3). Frontend coverage
report enabled (`@vitest/coverage-v8` added as devDep). Sidecar pytest
coverage 92% overall.

- **T5-safety-store-reset-ks [S1]:** `src/store/safety.ts:230`
  `resetKillSwitch()` entirely untested. POST body field `reAck: true`
  never asserted; camelCase/snake_case drift would permanently lock the
  kill switch with no test catching it. **§6.5-adjacent finding —
  automatic-S1.**
- **T5-broker-base-invalid-order-type [S1]:** `propose_order()`
  raises `BrokerError` on invalid `order_type` but test only covers
  invalid `side` + zero quantity. Refactor changing
  `"stop-limit"`→`"stop_limit"` would reach live broker undetected.
  **§6.5-adjacent finding.**
- **T5-openbb-mcp-provider-fallback-paths [S2]:** yfinance fallback
  when openbb-mcp raises `ProviderError` untested at registry level.
  Fundamentals 500 confirms this is the production path.
- Plus `services/quant/monte_carlo.py` 0% covered (48 lines, no test
  file). vitest.config.ts has no `coverage` block — recommended
  follow-up.

**Part B BLUEPRINT drifts:** 10 drifts (1×S1, 4×S2, 5×S3).

- **D-7 [S1]:** §10 UC2/UC4 imply end-to-end fundamentals + SEC
  functionality, but the MCP subprocess gap is not disclosed in BLUEPRINT.
  UC2 fundamentals 500s in v0.7.0 dev.
- **D-4 [S2]:** §4 Module 7 "dark default + light option" — light theme
  not implemented (v1.1 carry per CLAUDE.md).
- **D-3 [S3]:** `src/lib/plugin-bootstrap.ts:39` `HOST_VERSION = "0.6.5"`
  stale vs `package.json` 0.7.0. Same finding as T4-host-version-stale.

---

## Cross-cutting / audit-introduced findings (X)

Findings that don't slot cleanly into any single audit dimension — usually
discovered while pursuing another dimension and recorded here so they don't
get lost.

### Finding X-broker-bootstrap-india-only [S? — confirm at L9] [status: open]

**Repro:** `sidecar/services/brokers/registry.py::bootstrap_default_adapters`
only registers `DhanAdapter`, `AngelOneAdapter`, `KiteAdapter`. The 4
non-India adapters (`AlpacaAdapter`, `IBAdapter`, `OandaAdapter`,
`CcxtExecutionAdapter`) are imported in `services/brokers/__init__.py:27-33`
but never instantiated + registered by any production code path. The
`registry.py` docstring (lines 13-14, 97-103) implies these adapters have
their own `bootstrap_*` entrypoints; `grep -rn 'def bootstrap_' sidecar/
services/brokers/` returns only `bootstrap_default_adapters`.

**Impact:** At sidecar startup, a `POST /brokers/alpaca/connect` (or `/ib/`,
`/oanda/`, `/ccxt-*/`) would raise `KeyError: no broker adapter registered
for id='alpaca'` via `brokers_registry.get`. UC1 paper-mode broker connect
through Alpaca is the most likely operator path; L9 will exercise.

**Suggested fix:** Either (a) extend `bootstrap_default_adapters` to register
all 7 broker classes guarded by a feature flag per broker, OR (b) make the
broker-connect router lazy-register on first request when the broker's
plugin is enabled. (b) is closer to the plugin-architecture spirit but is
more invasive; (a) is one-commit cheap.

**Files:**
- `sidecar/services/brokers/registry.py:97-112` — `bootstrap_default_adapters`
- `sidecar/services/brokers/__init__.py:27-33` — adapter class imports

**Notes:** Severity deferred to L9. If L9 confirms the broker-connect UX
gracefully degrades ("broker not bootstrapped — connect through the broker
plugin first" or similar), S3. If L9 sees a raw `KeyError` 500 response or a
React crash, S2 (or S1 if it blocks UC1 entirely).

---

## Fix log

Commit SHA → finding ID(s) mapping. Each S1 fix lands as one commit with
message `fix(phase-8/<finding-id>): <summary>`; this section lists them in
the order they shipped.

| Commit SHA | Finding ID(s) | One-line summary |
| ---------- | ------------- | ---------------- |
| _(empty)_  | _(empty)_     | _(empty)_        |

---

## Sprint summary (filled at G1 / handoff time)

- **Audit dimensions completed:** _(N / 9)_
- **Total findings:** S1: _N_ • S2: _N_ • S3: _N_ • S4: _N_
- **Fix outcomes:** S1 fixed: _N_ • S2 hot-patched: _N_ • S3 deferred: _N_ •
  S4 deferred: _N_
- **Tag shipped:** _(v0.7.1 or v0.8.0)_ at commit _(SHA)_
- **Tier-1 lock status:** _types/plugin.ts diff vs v0.7.0 = (empty / non-empty)_
- **§6.5 audit status at tag:** _9/9 PASS_
- **CI status at tag:** _green on N/3 OSes_
- **Sprint wall-time:** _(hours)_

---

*Living document — update progressively, never batch.*
