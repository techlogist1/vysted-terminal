# R15 Census — WORLD-COMPARE: agent-native UX vs the in-app agent

Worker model id: `claude-opus-5-5[1m]` (session 2, Stage B item 6; supersedes the session-1 stub
by `claude-fable-5-1`, whose working notes are folded into rows W-7/W-8 below)
Date: 2026-09-23 · HEAD branch `004-r4-experience-rebuild`
Input research: `census/world/agent-native-ux.md` (patterns W-1 .. W-12).
Raw findings: `census/raw/world-agent-native-ux.json` (prefix `WLD-agent-native-ux`).
Status: COMPLETE.

Code read for this pass (full or the cited ranges): `sidecar/services/agent_runtime.py`
(invoke loop 1229-1631, planner gate 87-115, preamble 376-441, history 469-482),
`sidecar/services/run_manager.py` (full), `sidecar/services/runs_store.py` (1-120),
`sidecar/routers/runs.py` (full), `sidecar/services/agent_tools/catalog.py` (capability ids,
data-write host actions 1303-1395), `src/lib/delegate-runs.ts` (full), `src/store/agent-runs.ts`
(full), `src/modules/chat/AgentsRail.tsx` (full), `src/modules/chat/ChatSidebar.tsx` (690-1300,
1356-1455, 1480-1530), `src/store/proposed-changes.ts` (1-240), `src/store/agent-autonomy.ts`,
`src/modules/chat/ProposedChangesReview.tsx`, `src/modules/chat/PlanView.tsx`,
`src/lib/host-actions.ts` (describe 583-865, apply 1176-1395), `src/modules/chat/context-provider.ts`
(captureTerminalState 220-320), `src/store/research-spaces.ts` (1-60), `src/store/chat-history.ts`,
`types/agent-modes.ts`.

Scope adjustments: trading is removed from the product (operator decision 23 Sep), so the
`propose_order` / §6.5 confirm path is not scored as a permission rule or a gap. The user's
tracked portfolio, notes and watchlist are in scope, and they are exactly the data the agent can
now write (`portfolio_add/update/delete_position`, `write_note`, `add/remove_from_watchlist`).

Legend: **present** (file:line) · **partial** · **absent** · **n/a** (why, for a local BYOK finance
agent). "Filed" = an existing census raw finding already owns the gap; this pass does not re-file
it. "NEW" = a raw finding emitted in this pass.

## Practice-by-practice table

| # | World practice (research row) | Vysted | Evidence (file:line) | Gap owner |
|---|---|---|---|---|
| W-1a | Plan shown before execution | **partial** | Planner pre-pass emits `LLMAgentPlanEvent` for compound, non-read turns on capable providers (`agent_runtime.py:1387-1413`), rendered by `PlanView.tsx` (header doc line 7: "It is ADVISORY"). Skipped on Ollama (`agent_runtime.py:87-90`) and for **every Delegate run** (`_planner_enabled` requires `mode == "agent"`, `agent_runtime.py:110-112`). | NEW WLD-agent-native-ux-4 (Delegate half) |
| W-1b | Plan is a GATE: the human approves or edits it before any action | **absent (by design, largely n/a)** | The plan never blocks: `ChatSidebar.tsx:991-995` ("ADVISORY — the loop below still drives execution"). For foreground turns this is acceptable: reads have no side effects and every mutation is already gated per change (W-2). It matters only where the agent spends unattended, i.e. Delegate. | folded into WLD-agent-native-ux-4 |
| W-1c | Plan as a live checklist (pending / in-progress / done / cancelled) | **partial** | `PlanView` badges steps as staged vs not (`PlanView.tsx:22-30`); it does not track per-step progress as the loop runs. Low value for 1-6 round foreground turns (`_MAX_TOOL_ROUNDS = 6`, `agent_runtime.py:543`). | not filed (would not change a decision) |
| W-2 | Every mutation reviewable as a diff, per-item accept/reject plus bulk | **present** | `enqueue` stages each host-action mutation with `before`/`after` (`proposed-changes.ts:95-111`); `ProposedChangesReview.tsx:27,49-57,130-141` gives per-item Accept/Reject plus Accept all / Reject all; batch = one agent turn (`ChatSidebar.tsx:944-951`). Weakness: `before`/`after` are prose descriptions, not snapshots (`host-actions.ts:790-815`). | AUTO bypass filed: COD-host-actions-proposed-changes-3; stale pending filed: -8 |
| W-3 | Automatic checkpoints / undo, with the undo boundary stated | **absent** | Accept applies and drops out of view: the review panel lists only `status === "pending"` (`ProposedChangesReview.tsx:27`); nothing captures a restorable pre-image. `portfolio_delete_position` removes the holding (`host-actions.ts:1376-1389`); `write_note` replace overwrites the text (`host-actions.ts:1176-1192`); no undo, no version history (`src/store/notes.ts`, `src/store/portfolios.ts` have none). Under AUTO these apply with no click at all (`proposed-changes.ts:118-120`). | NEW WLD-agent-native-ux-2 |
| W-4a | Messages typed mid-run are QUEUED | **present** | While streaming the composer queues (`ChatSidebar.tsx:1287-1292`), visible and removable chips (`QueuedPrompts`, `ChatSidebar.tsx:1356-1380`), FIFO drain after the run (`ChatSidebar.tsx:1094-1127`). | — |
| W-4b | Hard stop | **partial** | Stop control exists and marks the message "stopped" (`ChatSidebar.tsx:899-903`, `onStop` at 1297), but the running tool task keeps executing and spending. | filed: COD-agent-runtime-4, SURF-COMPOSER-CHAT-6 |
| W-4c | Steer at the next step (differentiator) | **absent** | No path injects a user message into a live loop; the only inputs are queue or stop. Differentiator per the research, and a 6-round foreground loop leaves little to steer. | not filed (differentiator, low leverage) |
| W-5 | Context/token consumption shown continuously; compaction near the limit | **absent** | Per-message usage is captured (`chat-history.ts:46-47,213-216`) and **never rendered** (no `.usage` read in any component). History is silently cut to the last 10 display messages (5 exchanges) on the client (`ChatSidebar.tsx:749-753`) and again in the runtime (`agent_runtime.py:482`, "cap at ~10 turns"); tool calls/results never re-enter history. There is no meter, no "older turns dropped" notice, and no summary. | NEW WLD-agent-native-ux-3 (visibility half; the compaction mechanism belongs to the harness-context compare) |
| W-6a | Per-capability permission rules (not one global boolean) | **partial** | Autonomy is one global `ask` / `auto` switch (`agent-autonomy.ts:23,37-40`). The auto-apply predicate is `described.kind !== "order"` (`proposed-changes.ts:118`), so AUTO covers destructive `data-write` and `settings` kinds as well as panel moves. | filed: COD-host-actions-proposed-changes-3 (fix shape = per-kind allow-list, i.e. this practice) |
| W-6b | A floor of rules that cannot be bypassed | **present** | Read intents are stripped to read-only tools server-side (`agent_runtime.py:1276-1306`) so no client or MCP caller can widen them. The order floor is moot now that trading is removed. | intent misclassification filed: SURF-COMPOSER-CHAT-5 |
| W-7a | Background runs are their own product surface with their own lifecycle | **partial** | Durable row plus detached task (`run_manager.py:237-282`, `runs_store.py:54-70`); agents rail with live tokens/$ and cancel (`AgentsRail.tsx:20-137`). But the rail shows only active runs (`AgentsRail.tsx:29-32`), so a finished or failed run vanishes, and nothing fetches the result (`GET /runs/{id}` has no frontend caller). "Bring to foreground" prints a one-line status only (`ChatSidebar.tsx:1177-1188`). | filed: COD-runs-durable-delegate-1, -7 |
| W-7b | Explicit state machine incl. first-class `awaitingInput` and `stale` | **partial** | Statuses `running / paused / done / error / cancelled` (`runs_store.py:21`), but `paused` is unreachable: `pause_run` has no route and no caller (`routers/runs.py:13-18`; `run_manager.py:301-316`), so the rail's answer box (`AgentsRail.tsx:139-183`) is dead. No transition table (`update_run` accepts any status). Client-side staleness exists (`delegate-runs.ts:43-59`, badges after 5 failed polls); there is no server-side stale state and no boot reconcile of orphaned `running` rows. | filed: COD-runs-durable-delegate-5, -6, -10 |
| W-7c | Resume from a failure | **absent in practice** | `resumeDelegateRun` has no caller (`delegate-runs.ts:226`, grep: definition only). The route resumes with `provider=None, model=None, api_key=None` (`routers/runs.py:126-135`, `run_manager.py:401-412`), so a BYOK cloud run cannot resume. | filed: COD-runs-durable-delegate-2, -9; SURF-COMPOSER-CHAT-11 |
| W-8a | Instant acknowledgement | **present** | A local chat note is written the moment Delegate is chosen (`ChatSidebar.tsx:843-850`), and the rail row appears at `startRun` before the POST returns (`delegate-runs.ts:69-77`). | — |
| W-8b | Typed activity stream (thought / action / elicitation / response / error) | **absent** | The driver keeps only text deltas plus a `[tool_use <name>]` string per tool (`run_manager.py:164-181`); research steps, plans, publish_brief and proposed changes are discarded. While a run is in flight the rail shows tokens and $ only (`AgentsRail.tsx:94-108`); `cost.steps` is not rendered. | result half filed: COD-runs-durable-delegate-1; NEW WLD-agent-native-ux-4 (plan + in-flight activity half) |
| W-8c | Rebuild history from frozen activity records, never from editable display text | **partial** | Foreground history is rebuilt from display `content` (`ChatSidebar.tsx:749-753`), which includes UI-only notes written as assistant turns (the Delegate note at `ChatSidebar.tsx:843-850`, the foreground summary at 1178-1188). Tool results are not in history at all. The claims ledger (`agent_runtime.py:331-374`, prior stated values) is the one frozen-record input. | overlaps harness-context; not filed here |
| W-8d | An error is a resumable object carrying remediation | **partial** | Foreground: structured error frame with action/detail/code (`ChatSidebar.tsx:907-912`) plus a Retry button (`ChatSidebar.tsx:1242`, `1428-1455`), so this half is present. Delegate: the error detail is in the row, but the row leaves the rail on the terminal status (`AgentsRail.tsx:29-32`) and resume is uncallable. | filed: COD-runs-durable-delegate-1, -2 |
| W-9 | Follow the agent's attention | **partial / mostly n/a** | The agent drives the cockpit itself: an applied `set_chart_symbol` / `open_panel` moves the surface the user is looking at, which is "follow" by construction. Live research steps stream into the transcript (`ChatSidebar.tsx:978-989`, `ResearchActivity.tsx`). An editor-style crosshair toggle has no analogue with ~6 panels. | not filed |
| W-10 | Memory is a document the user can open and edit, and the agent reads it | **absent** | The agent can WRITE the user's notes (`write_note`, `catalog.py:1373-1395`) but has no capability to read them (no note-read id among the catalog capabilities), and neither `captureTerminalState` (`context-provider.ts:220-320`) nor the preamble (`agent_runtime.py:376-441`) carries note text; the only notes signal anywhere is a character count used for layout (`host-actions.ts:999`). Research-space "memory" is an auto-generated line quoting the last 3 user questions (`research-spaces.ts:33-45`), with no component that shows or edits it (no `.tsx` consumer of `getMemory`). There is no user-level instructions or profile document; only custom-agent system prompts are editable (`AgentBuilderPanel.tsx:304-305`), and they are per-agent. | NEW WLD-agent-native-ux-1 |
| W-11 | Agents run on schedules or triggers, not only on invocation | **absent** | No scheduler, alert or trigger capability; `POST /agents/{id}/runs` is the only start (`routers/runs.py:63`). | filed: WLD-T-1 (critical) |
| W-12a | Metered cost visible for background runs | **partial** | Rail shows tokens and $ for Delegate (`AgentsRail.tsx:103-107`) and a token-only budget bar (`AgentsRail.tsx:77-82,131-138`, so a spend-only or wall-only ceiling shows no bar). The meter itself is wrong in three filed ways: priced on the requested provider string, research LLM calls unmetered, Gemini thinking tokens omitted. | filed: COD-runs-durable-delegate-11, COD-research-extraction-synthesis-2, COD-llm-adapters-2-6, COD-frontend-panels-agent-shell-7 |
| W-12b | Foreground cost visible | **absent (not table stakes)** | Foreground runs record `spendUsd: 0` hard-coded (`ChatSidebar.tsx:919-922`). The research says foreground chat "mostly still hides cost", so this is not scored as a gap. BYOK makes it more pressing than the research implies, but the root cause (research unmetered) is already filed. | covered by COD-research-extraction-synthesis-2 |

## Reading of the table

The foreground loop meets or nearly meets the world bar where it counts for a finance terminal:
per-change review (W-2), queue (W-4a), a server-side read-only floor (W-6b), a visible plan
(W-1a), and a structured error with retry (W-8d). The three NEW gaps are all about **what
survives a turn**, which is exactly where "Jarvis" differs from "chatbot with panels":

1. **Memory (W-10).** The agent writes the user's notes blind and never reads them. The one
   artifact the world treats as the memory surface (a document the user edits) exists in the
   app but has no path into the agent. Its "memory" is an unseen auto-summary.
2. **Undo (W-3).** The agent can delete a tracked holding or replace a note, and neither can be
   undone. That makes AUTO unsafe even after COD-host-actions-3's allow-list fix, and it makes
   ASK-mode mistakes permanent.
3. **Context visibility (W-5).** Five exchanges in, the agent silently forgets the start of a
   research thread, with no meter and no notice. The user has no way to tell forgetting apart
   from a wrong answer.

Delegate (W-7/W-8) is the weakest surface overall, but almost every piece of that gap is already
filed by the durable-delegate code critique (COD-runs-durable-delegate-1/2/5/6/7/10/11). This
pass adds only the unfiled half of the Linear contract (a plan before an unattended spend, and a
typed in-flight activity stream) as WLD-agent-native-ux-4, so the Delegate fix is built as one
contract rather than as a result-delivery patch.

Not filed, deliberately: steer-at-next-step (W-4c, a differentiator with little leverage on a
6-round loop), a plan checklist with progress (W-1c), follow-mode (W-9, the cockpit already
follows), and foreground cost (W-12b, not table stakes; root cause already filed).
