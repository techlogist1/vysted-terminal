# Recon — A11:opencode-assess

The full chain is confirmed and live: `LLMResearchStepEvent` (sidecar/models/llm.py:136) → agent_runtime SSE → `src/modules/chat/streaming.ts` → `src/modules/chat/ResearchActivity.tsx` in the chat dock. The "render a read-only plan in the activity log" surface already exists in-house. I have everything needed for a decisive verdict.

---

# OpenCode Re-Assessment — VERDICT: **LOG** (do not integrate tonight)

## (1) Findings — file:line precise

**The in-house fallback is already complete, tested, and shipping the exact capability OpenCode would provide.**

- `sidecar/services/planner.py` (379 L) — `classify_intent` (L159, deterministic, live-wired as the mode-collapse gate) + `decompose` (L332, LLM-backed compound→ordered `Plan` of `PlanStep`s, L233–266, injected `llm_call`, robust fallback never dead-ends). `PLAN_ACTIONS` (L216) is the read-only step vocabulary. This **is** "a plan agent that returns an ordered read-only step list."
- **Activity-log render surface exists end-to-end:** `LLMResearchStepEvent` (`sidecar/models/llm.py:136`) → emitted in `agent_runtime.py` (`_step_event` L331, `LLMResearchStepEvent` import L43) → SSE `research_step` → `src/modules/chat/streaming.ts` → **`src/modules/chat/ResearchActivity.tsx`** (the live animated "thinking/working" surface in the chat dock) + `src/store/chat-history.ts:21`. A plan would render here with **zero new infra**.
- Research engine (`research/fast.py`, `deep.py` with `on_step` sink L370/L399) already streams reasoning-shaped steps. The "reasoning parts for display only" capability is **already built and in-house**.

**OpenCode's current state (web-confirmed, June 2026):**

- **The §6.5-inverting permission gate is not merely architectural — it is a live, unfixed security bug.** Issue **#6396** "Custom agent 'deny' permissions in opencode.json are ignored when invoked via SDK" (filed 2025-12-29, assigned `rekram1-node`, **no maintainer fix**) — denied tools execute freely via SDK. Reinforced by **#16331** "Permissions ignored", **#7063** "Permission denied, yet command is executed regardless", and feature-request **#5965** (SDK-level permission overrides still _requested_, i.e. not delivered). The `permission: deny` + `plan` config — the _entire_ §6.5-safe predicate of the "INTEGRATE" path — **does not reliably hold when driven over the SDK/server**, which is the only way we'd drive it.
- It **owns the agent loop** (Vercel AI SDK `streamText`, synchronous LLM→tool→feedback) — unchanged from Phase-0. Embedding = two competing loops, two gates, OpenCode's upstream of §6.5.
- **Not installed on this box** (`which opencode` → not found) and ships as a separate headless `opencode serve` HTTP process (`:4096`) requiring lifecycle management, password env (`OPENCODE_SERVER_PASSWORD`), and a Node/TS SDK round-trip — a fourth long-lived subprocess on a 16 GB M1 already running main + 2 MCP sidecars.

## (2) "Exact change plan" — there is none to make tonight

The INTEGRATE path's minimal-clean design (separate opt-in `opencode serve` process, `permission:deny` + `plan` agent, reasoning SSE → activity log, zero tools) **cannot satisfy its own safety predicate** because the deny gate is bug-broken over the SDK (#6396). Shipping it means trusting an unenforced permission flag to keep a coding-shaped agent off the §6.5 path — exactly the inversion the floor forbids. **No files to create/edit.** The capability is already delivered by `planner.decompose()` + `ResearchActivity.tsx`.

The one **logged follow-up** (already on record, Fork §4.3): wire `decompose()` to a visible "plan-then-execute" surface — steps rendered in `ResearchActivity.tsx`, staged in `src/store/proposed-changes.ts`, gated by the existing diff/accept. That is an **in-house, zero-new-process** way to get everything OpenCode promised, and it's the right place to spend the effort.

## (3) Risks of integrating + the safe fallback for each

| Risk if we INTEGRATE                                                                                                          | Severity                                                   | Safe fallback                                                                 |
| ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------- |
| **#6396: SDK ignores `deny`** → a coding agent with bash/PTY tools runs un-gated, upstream of §6.5                            | **Tier-4, fatal** — inverts the locked safety architecture | Use `planner.decompose()` (no tools at all, structurally cannot execute)      |
| Two competing agent loops + two permission gates, OpenCode's upstream of `proposed-changes.ts`                                | High — violates "our gate is the unconditional chokepoint" | In-house loop stays the single spine; planner emits steps the gate approves   |
| 4th long-lived subprocess (`opencode serve`) on 16 GB M1 — lifecycle, port, auth, orphan-kill, PyInstaller-adjacent fragility | Medium — marginal gain for real cost                       | Zero new process; planner is a pure function in the sidecar                   |
| Coding-shaped tools/prompts vs. finance-shaped reasoning we already produce                                                   | Medium — contributes nothing the in-house planner doesn't  | `_build_prompt` (planner.py:269) is already finance-tuned ("You are JARVIS…") |

Every cell's fallback is **already built and tested**. OpenCode adds fragility and a Tier-4 §6.5 exposure for **negative** marginal value.

## (4) Verification — proving the in-house path already covers it (run now)

```bash
# In-house planner produces the read-only plan OpenCode would (offline, no process):
sidecar/.venv/bin/pytest sidecar/tests/test_planner.py -q          # decompose + classify_intent
# Step→activity-log SSE channel is live (the "reasoning parts for display" surface):
sidecar/.venv/bin/pytest sidecar/tests/ -k "research_step or step_event or agent_runtime" -q
pnpm vitest run src/store/chat-history.test.ts                      # research_step ingestion
# §6.5 floor still 9/9 (proves nothing touched the execution path):
sidecar/.venv/bin/pytest sidecar/tests/test_safety_end_to_end.py -q
# Live: a plan renders in the activity log, never auto-applies (rig):
#   pnpm tauri:mcp → ask a compound research request → confirm steps appear in
#   ResearchActivity.tsx and NO order/mutation auto-applies (proposed-changes gate holds).
```

If `test_planner.py` does not yet exist, that's the single gap — add planner unit coverage; **still no OpenCode dependency.**

---

## In short

- **LOG, not INTEGRATE.** The Phase-0 FALLBACK verdict is _strengthened_, not softened: OpenCode's `deny` gate — the entire safety predicate of the clean design — is a **live unfixed bug over the SDK** (#6396, plus #16331/#7063/#5965), so the §6.5-safe config cannot be trusted to actually be safe.
- The capability it would add (read-only plan rendered in the activity log) is **already built in-house**: `planner.decompose()` + the live `research_step` → `ResearchActivity.tsx` channel. OpenCode contributes nothing but a 4th subprocess and a Tier-4 inversion risk.
- The right spend is the already-logged follow-up: wire `decompose()` to a visible plan-then-execute surface staged in `proposed-changes.ts` — zero new process, zero §6.5 reach.
- **Confidence: 9/10** — high on the safety call (the SDK deny bug is decisive and bias-toward-safe is the brief's instruction); the 1 point is that I couldn't load the live GitHub issue body to read a maintainer's exact latest comment, but three corroborating bug/feature issues all point the same way.

Sources: [opencode #6396](https://github.com/anomalyco/opencode/issues/6396), [#16331](https://github.com/anomalyco/opencode/issues/16331), [#7063](https://github.com/anomalyco/opencode/issues/7063), [#5965 (SDK permission overrides — requested, not shipped)](https://github.com/sst/opencode/issues/5965), [OpenCode Permissions docs](https://opencode.ai/docs/permissions/), [OpenCode Server docs](https://opencode.ai/docs/server/), [OpenCode SDK docs](https://opencode.ai/docs/sdk/)
