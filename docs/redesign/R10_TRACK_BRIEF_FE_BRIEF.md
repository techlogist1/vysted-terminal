# R10 Track FRONTEND-BRIEF — brief lifecycle, depth UI, chat honesty

Branch: `worktree-agent-r10-frontend`. Read first: `verification/R10_DEFECT_CATALOGUE.md`
(E2, E3, E9-render, E10), DECISIONS D38/D39/D43, the contracts commit (types/brief.ts
BriefExecution/BriefDisambiguation/BriefDerivedMetrics; types/proposed-change.ts new
kinds), `R9_DESIGN_SYSTEM.md` (THE visual law — 8pt grid, 11/13/16/19/23/28 scale,
zinc + scarce peach, depth heat lume/peach/ember).

## Files you own (exclusive)

`src/store/brief.ts`, `src/lib/host-actions.ts`, `src/lib/brief-ingest.ts`,
`src/modules/research/**`, `src/modules/chat/**` (ChatSidebar.tsx, streaming.ts,
context-provider.ts, message components), `src/lib/workspace.ts` (+ its test),
`src/store/proposed-changes.ts`, and their vitest files. Do NOT touch
`src/store/screener.ts`/`src/modules/screener` (Team FRONTEND-DATA), `src/lib/
marketplace.ts`/`keychain.ts` (Team ERRORS), types/\* (frozen contracts), sidecar.

## 1. Brief state machine — `src/store/brief.ts` (E3 dead)

```ts
type BriefPanelState =
  | { phase: "empty" }
  | {
      phase: "in_flight";
      runId: string;
      query: string;
      symbol?: string;
      depth: BriefDepth;
      startedAt: number;
      steps: BriefStep[];
      prior?: ResearchBriefData;
    }
  | { phase: "published"; brief: ResearchBriefData }
  | {
      phase: "archived";
      brief: ResearchBriefData;
      archivedAt: number;
      reason: "restored" | "superseded" | "run_failed";
    };
```

Transitions: `beginRun` (from the runtime's `research:begin {run_id} …` engine step —
parse it in streaming.ts and call the store; prior published → carried as `prior`);
`publish` (publish_brief applied; if `execution.run_id === inFlight.runId` or no run
in flight → published; previous published → archived(superseded)); `fail` (stream
error / done-without-publish / watchdog: in_flight older than depth wall + 60s →
restore prior as archived(run_failed) or empty); restore from workspace → ALWAYS
archived(reason "restored"). Keep a `brief` selector for legacy consumers
(published || archived brief) so unrelated surfaces keep rendering, but the PANEL
distinguishes phases. Persisted shape in the workspace blob stays ResearchBriefData
(+ a persisted `archived` marker is NOT needed — restore always archives by rule).

## 2. Carry killed — `src/lib/host-actions.ts`

`briefFromInput`: structured/backend/depth carry-over ONLY when
`input.execution?.run_id` (snake_case wire → camel map in brief-ingest) matches the
in-flight/prev brief's `execution.runId` AND base symbols match-or-one-absent. DELETE
`prevRecent`, the 20s clock, and the recency branch of `carryBriefDepth`. Mode/depth:
when `execution` present, derive from `execution.loop` (fast→FAST/quick, iter→DEEP/
deep, heavy→DEEP/heavy, research-model→stop-based per requested_depth) — ignore the
wire `mode`. Legacy inputs (no execution): keep today's derivation but the resulting
brief renders ARCHIVED (no execution = archival by definition). D33 shrink guard:
scope to same run_id; when it keeps the richer brief, the apply path must report
`kept_previous` (see §4). Ingest `disambiguation` verbatim onto the brief data.

## 3. New write-action apply/describe cases — host-actions.ts + proposed-changes.ts

Add HOST_ACTION_NAMES + describeHostAction + applyHostAction cases (catalog ids from
Team RUNTIME's brief — keep EXACT names): `portfolio_add_position` /
`portfolio_update_position` / `portfolio_delete_position` (POST/PUT/DELETE
`/portfolio/positions[/{id}]` via the sidecar client, then refresh the portfolio
store), `write_note` (notes store; mode replace|append), `remove_from_watchlist`,
`save_layout`, `save_screen` (delegate to the screener store's saved-screens API —
Team FRONTEND-DATA ships `useScreenerStore.saveScreen(name, …)`; call it, don't
implement it), `write_screener_filters` gains `formula?` + `run?` passthrough to
`applyFilters`, `set_region` (settings store). Kinds: portfolio/notes/screen-save →
"data-write"; region → "settings"; watchlist-remove → "watchlist". proposed-changes:
the auto-apply branch condition (`kind !== "order"`) is UNTOUCHED — new kinds
auto-apply under AUTO; orders never. Extend describe titles/diffs so the review bar
reads humanly ("Add 5 RELIANCE @ ₹1,263 to the paper portfolio").

## 4. Publish ack — read-back to the sidecar

After applyHostAction("publish_brief", …) resolves (applied | kept_previous | failed),
`POST /agents/actions/ack {tool_call_id, status, brief:{run_id, created_at, symbol,
source_count}}` (fire-and-forget with catch). Render the runtime's end-of-stream
divergence notices as a quiet system chip in the transcript (13px caption, zinc).

## 5. Panel surfaces — `src/modules/research/`

- IN-FLIGHT: designed skeleton within the R9 law — zinc-850 pulse blocks on the 8pt
  grid, caption line "Researching — DEEP · 42s" (live timer + depth from store), the
  live ResearchActivity steps. NEVER a broken empty panel mid-run.
- ARCHIVED: a quiet banner strip "ARCHIVED · produced <date>" (micro-11 eyebrow),
  metric cards at reduced opacity, a Refresh affordance → escalateResearchDepth at
  the brief's depth.
- DISAMBIGUATION: "Which did you mean?" — candidate chips (caption-13 cards:
  symbol + name + exchange) → click re-runs research with the yahoo_symbol.
- DERIVED METRICS: render `structured.derived` cards FIRST (drawdown "Below 52w high
  −21.6%" AND "52w change" as separate cards; dividend with basis; growth with basis
  suffix); `conflicts[]` render as a caption-13 flag row ("Sources disagree on
  dividend: 0.55% (yield) vs ₹1/share — not reconciled"). Null values render nothing.

## 6. Chat — `src/modules/chat/`

- streaming.ts: parse `research:begin` engine steps → briefStore.beginRun; structured
  error frames `{message, action, detail, code}` (Team ERRORS contract) → typed error
  on the message.
- ChatSidebar.tsx: (a) the go-deeper/refresh agent-command subscriber overrides the
  send's depth with `command.depth` (map quick→normal/deep→deep/heavy→ultra via a
  `depthTierToWire` helper in brief-ingest.ts) so refresh depth rides the
  deterministic options floor — E2's UI leg; (b) error rendering: plain message +
  action line + a "Details" disclosure showing raw `detail` (13px caption, negative
  color for message, charcoal for detail; Retry button stays); legacy plain-string
  errors render as today.
- context-provider.ts: TerminalState gains `brief: {phase, runId?, symbol?,
createdAt?, sourceCount?, depth?}` so get_terminal_state answers panel truth.
- E10 — the streaming-line/header clip: reproduce at narrow widths/long status lines
  (the transcript header area "VYSTED COPILOT"); fix the layout (reserve height /
  clip-safe container per R8 §3.3 descender rule); pin with a vitest on the
  container classes + capture evidence at 1280 and 960 in your report.

## 7. workspace.ts

Restore path: brief always lands archived("restored"). Older blobs (no execution)
restore fine. Update workspace.test.ts accordingly. NOTE: Team ERRORS will report a
tradesa panel-id reference in workspace.test.ts — delete that fixture line when you
touch the file (coordinate via your report if it's not there).

## Gates before you push

`pnpm lint`, `pnpm typecheck`, `pnpm format:check`, FULL vitest green. Granular
commits, push at each green milestone. Screenshot evidence of skeleton/archived/
disambiguation states is the LEAD's gate-battery job — your job is the states render
under test (vitest + storybook-less component tests).
