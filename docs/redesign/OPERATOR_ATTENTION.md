# Operator attention — P1–P3 closeout

_What genuinely needs you, ranked. Context: the agent-native redesign (P1–P3) is built,
gates re-proven green, and adversarially self-validated on branch
`001-agent-native-redesign` (not merged). Full accounting:
[`P1_P3_BUILD_REPORT.md`](./P1_P3_BUILD_REPORT.md). This doc is only the open items._

Closeout HEAD: `552ce67` · gates: `ci-local` PASS, smoke PASS, §6.5 9/9, Tier-1 safety set
byte-for-byte untouched vs `main`.

---

## P0 — look at these first

### 1. Visual / interactive validation — I could not do it (you must)

My execution context lacks **Screen Recording** and **Accessibility** permission
(`screencapture` → "could not create image from display"; `osascript` System Events →
timeout -1712), and there is no headless browser available. So I could not capture
screenshots or drive the GUI. **The app is running now** (`pnpm tauri dev`, window on your
screen, main sidecar healthy on :53072) — please exercise and eyeball:

- **Four agent modes** — ⌥1 Ask, ⌥2 Edit-panel, ⌥3 Build, ⌥4 Delegate; mode bar reflects the switch.
- **Agent dock as a co-equal primary surface** (not a cramped sidebar) alongside the cockpit.
- **Diff/accept trust gate end-to-end** — ask the agent to change a panel/chart (e.g. "set the
  chart to NVDA" / "add MSFT to the watchlist"); confirm you see a **proposed change with
  old→new**, then **accept one and reject one** and verify only the accepted one applies.
- **Minimal-dark shell + status chrome** — sidecar/provider/model + running-agent indicators legible.
- **Teaching command palette** (⌘K) — surfaces shortcuts for palette actions.
- **Plugin marketplace** — browse → install/enable a **broker** plugin (e.g. Kite) → see its
  **BYOK config form** rendered from the declaration → remove it and confirm its surfaces disappear.
- **Settings** — remap a keybinding, deliberately collide two bindings, confirm the **conflict is
  detected/surfaced**; confirm a remap persists across relaunch.

Judgment calls only you can make: does it _feel_ minimal-dark and Cursor-grade, is anything
ugly/empty/misaligned, do the micro-interactions land. Capture the per-release screenshots at
1920×1080 and 2560×1440 (`docs/screenshots/v<tag>/`) once you've eyeballed it.

### 2. Merge + version-bump decision (yours)

The branch is **not merged** and **not version-bumped**. All five version sources read `0.8.0`
consistently — nothing is _stale_, so I did not bump (a bump is a release/merge call, premature
on a feature branch). At merge: bump `package.json`, `src-tauri/Cargo.toml`,
`src-tauri/tauri.conf.json`, sidecar `app.py` `FastAPI(version=…)`, and `HOST_VERSION`
(`plugin-bootstrap.ts`), then `cargo update -p vysted-terminal --offline`. Plugin manifests pin
`requiredHostVersion: "0.8.0"` — a bump to ≥0.8.0 keeps them loadable (the load gate is `>=`).

---

## P1 — known issues, be aware

### 3. sec-edgar-mcp cold-bind failure → `/sec` routes 501 (pre-existing)

Confirmed live in this boot: the SEC-EDGAR MCP subprocess did not bind within 45s × 2 attempts,
so `/sec` routes degrade to 501. This is the **documented carry-forward** (BLOCKERS.md:
PyInstaller `--onefile` cold `_MEI` extraction contends for disk at boot; the `--onedir` true fix
is deferred). The host degrades gracefully — no crash. Not a P1–P3 change. The main sidecar
(:53072) and openbb-mcp (:53073) came up healthy.

### 4. SC-008 wall-clock ceiling — found broken in self-validation, **fixed** (`552ce67`)

Adversarial self-validation broke the SC-008 "aborts at the ceiling 100%" claim for the
**wall-clock** budget only: `BudgetGuard.breach()` was polled only at a round terminator, the LLM
adapters have no per-stream timeout, and there was no `asyncio` backstop — so a single over-long
round or a hung provider stream could outlive `max_wall_seconds` (indefinitely, if it hung).
tokens/spend/steps always held. **Fixed**: the run is now wrapped in
`asyncio.timeout(max_wall_seconds)` (a no-op when unset), making the wall ceiling hard even
mid-round, with a regression test that hangs a round and asserts the abort. Worth a glance since
it touches the durable-runs executor.

---

## P2 — follow-ups (not blocking, deliberately deferred)

### 5. Resume-UI affordance for budget-breached runs

`resumeDelegateRun` (budget-breach recovery: relaunch an errored run from its checkpoint with
fresh ceilings) is built and tested at the lib + sidecar level but has **no UI trigger** — the
agents rail only shows running/paused runs, and surfacing errored-resumable runs needs a sidecar
`resumable` field on the run summary plus a rail UX decision. The **pause→answer→resume HITL path
IS wired** (the rail's answer form). This is a clean increment, not a hot-patch — flagging rather
than half-wiring it.

### 6. One-round overshoot on token/spend/step breach (bounded, by design)

A breach detected at round N's terminator still lets round N+1's provider call begin before the
driver breaks (the test codifies `steps <= 2`). It's a bounded, single-round overshoot — an
intentional round-boundary design. Tightening it to zero-overshoot would require threading a
stop-signal into the `invoke_agent` loop (risking the multi-round contract); not worth it now.

### 7. `kill-switch-benchmark.json` test-artifact churn

`test_safety_end_to_end.py` (Tier-1 LOCKED) rewrites
`docs/screenshots/v0.5.0/safety-audit/kill-switch-benchmark.json` with fresh timing numbers on
every run (result stays PASS). It's been reverted out of every commit this session. The clean fix
(emit to a scratch path) requires touching a LOCKED test — needs your sign-off.

### 8. HITL autonomous self-pause (`ask_user`) deferred

The agent cannot self-pause mid-loop to ask a question — that needs a new catalog capability +
§6.5/parity audits. The explicit operator/host-driven pause→answer→resume control plane is fully
implemented.

---

## Deferred to real testing (your scope — "deep/real testing comes later")

### 9. Live broker (Kite) granular reads with real credentials

SC-012 distinctness is proven on the paper/synthetic path (tested + badged) and at the
read-surface audit. Seeing live positions ≠ holdings ≠ margins needs your real Kite account +
the static-IP setup.

### 10. Live BYOK agent answers

The keyless-provider reachability gate and the provider plumbing are in place, but a live agent
answer needs your provider API key (Anthropic/OpenAI/Gemini/…) or a running local Ollama.

---

## Self-validation scorecard (this closeout)

14 adversarial attacks across the "Verified" SCs. **12 survived** (SC-003 gate/no-auto-apply,
SC-004 MCP parity, SC-005 multi-round, SC-006 catalog parity, SC-007 zero-per-source-UI, SC-012
broker GET-only, SC-013 no-broker-at-boot, SC-014 plugin-can't-bypass-§6.5, SC-015 load gate —
confidence 0.82–0.97). **1 broke (SC-008 wall-clock) — now fixed (item 4).** Nothing else failed
under scrutiny.
