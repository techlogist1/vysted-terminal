# APOSD critique: `frontend-panels-shell-chrome` (Platform Shell & Settings Chrome)

Worker model: `claude-opus-5-5[1m]`. I loaded and followed the `aposd-critique` skill (two personas, 18 principles, file:line evidence). Assessment independence was **degraded (sequential)**: this worker has no sub-agent tool, so I finished and recorded the Strategic pass before running the Tornado scan. I skipped the skill's `.aposd/critique/` snapshot so no untracked file lands in the repo; the R15 output files below are the record.

**Scope.** I read all 4365 LOC in full: `PanelHost.tsx`, `SettingsPanel.tsx` (1890), `DataTable.tsx`, `DataBadges.tsx`, `EmptyState.tsx`, `StatusChrome.tsx`, `app/page.tsx`, `app/globals.css`, `types/panel-context.ts`, `store/panel-context.ts`, and `modules/platform/{WorkspaceDialog,index,workspace-dialog-store}`. I also read callers and collaborators wherever a claim depended on them: `ChartPanel`, `EquityOverviewPanel`, `BacktestResultView`, `SuggestionChips`, `ChatSidebar`, `context-provider`, `store/workspace`, `store/modules`, `store/keybindings`, `store/app`, `lib/region`, `lib/sidecar-client`, `lib/use-sidecar-retry`, `lib/workspace`, `lib/plugin-bootstrap`, `lib/layout-templates`, the marketplace and screener modules, and `agent_runtime._planner_context`.

**Outputs.**
- Raw findings (13): `census/raw/code-frontend-panels-shell-chrome.json`.
- Proof: a scratch vitest run (repo root, scratch include), 1 file with **4 tests, 4 passed**. It proves the context-bus id mismatch (F1, two tests), the dead Marketplace button (F2) and the missed keybinding conflict (F3). The test is kept at `census/code/evidence/frontend-panels-shell-chrome-repro.test.tsx.txt`; nothing was written under `src/`.
- A node one-liner proves the UTC date shift (F9): `TZ=Asia/Kolkata`, `2026-09-24T01:30+05:30` gives `2026-09-23` from `toISOString` but `2026-09-24` locally.

**Deliberately not re-reported (owned elsewhere, already admitted):**
- The `page.tsx:104-181` per-field autosave triggers, the undebounced notes writes, `__autosave__` showing in the Load dialog, and the workspace dialog's copy promising "layout + enabled modules" while load rolls back portfolios. These are `COD-workspace-layout-1/3/5/12`.
- The `sidecarStatus` one-shot boot latch behind StatusChrome's dot. This is `COD-error-layer-14`.
- `charts[0]` shown as "Focused chart" in the preamble. This is `COD-agent-runtime-2`.

F1 below is the *frontend* root cause that sits under that agent-runtime symptom.

## Tactical Tornado verdict (risk: MEDIUM-HIGH)

The primitives are mostly strategic: DataTable owns alignment and the null glyph, EmptyState has 27 adopters, and StatusChrome's formatter and probe are thoughtful. The **joins between modules** are tactical, though. Each one is an untyped string that two sides spell differently and that nothing checks:

- dockview panel ids vs panel-context bus sources (F1, proven broken). Tests fake both sides with `"chart-1"`, so the product is broken while the suite is green.
- panel ids vs component ids (F2, proven dead button). The same slip also appears in `PluginManagerPanel.tsx:71`.
- `mod` vs `meta` in keybinding strings (F3, proven missed conflict).
- the `PANEL_MIN_SIZE` keys vs the registered components (F6: one dead key, one removed-feature key, and the two research surfaces missing).

The most damning pattern is that **the unit tests encode the mismatch away**. `SuggestionChips.test.tsx:65-71` and `ChatSidebar.test.tsx:472-478` hand the publisher and the focus setter the same fake id, so the one integration that matters (PanelHost to bus to consumer) was never exercised.

SettingsPanel is a 1890-line leaf that is fine as layout, but it hides two private sidecar clients (F8) and false copy on the most consequential data setting (F4).

**Red flags found: 14.**
- Information leakage ×4: F1, F2, F6, F9 (duplicate `Freshness`).
- Repetition ×3: 3× ProvenanceBadge, 3× skeleton tables, `unsubscribeEnabled`/`unsubscribeModules` doing identical work at `page.tsx:94-103`.
- Special-general mixture ×1: EmptyState is used for both error and empty.
- Nonobvious or false comments ×4: `SettingsPanel.tsx:1345/1354` "collapse to mod", `:72` "ONE search surface", `PanelHost.tsx:118` SSR rationale, `chart-theme.ts:45` lockstep.
- Temporal decomposition ×2: the grow sweep is tied to boot rather than to `fromJSON` (F6), and the restore is gated on first-party registration (F11).

## Design principles score

| # | Principle | Grade | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | at-risk | Strategic: DataTable owns alignment/tier/null glyph (`DataTable.tsx:143-175`); PanelHost's disposed-api guards (`PanelHost.tsx:166-173,182-184`). Tactical: string joins with no parity test (F1, F2, F6) | Three shipped features are dead in the real app while their tests pass |
| 2 | Deep modules | at-risk | Deep: `formatModelLabel` hides a brand table plus a middle-trim ladder behind one call (`StatusChrome.tsx:124-161`); `useProviderReady` hides TTL caching (`:81-115`). Shallow: EmptyState covers only happy-empty (`EmptyState.tsx:22-42`); DataTable has no loading/empty slot (`DataTable.tsx:101-129`) | Callers re-implement error and skeleton states (F5, F12) |
| 3 | Information hiding | **violate** | `PANEL_MIN_SIZE` is private to a component (`PanelHost.tsx:25-71`) while `layout-templates.ts:363-365,479-480` restates it; `SearxngStatus` is hand-mirrored inside a component (`SettingsPanel.tsx:697-704`); the bus `source` naming is known separately by 6 publishers (`ChartPanel.tsx:885`, `EquityOverviewPanel.tsx:649`, …) | F1, F6, F8 |
| 4 | General-purpose modules | at-risk | DataBadges claims to be "generic so any Pass-B surface can reuse" (`DataBadges.tsx:7-9`), yet two panels shadow it (`EquityOverviewPanel.tsx:286`, `BrokerReadsSection.tsx:109`) | Three badge semantics for one trust concept (F9) |
| 5 | Different layer, different abstraction | at-risk | A formatter lives in a view and is imported by two others (`StatusChrome.tsx:124` → `SettingsPanel.tsx:18`, `ModelControl.tsx:6`); Settings talks raw HTTP (`SettingsPanel.tsx:707-734`) beside `sidecarGet` | Settings bypasses the region/search headers and the error-detail extraction (F8) |
| 6 | Pull complexity downward | **violate** | `openPanel` pushes id-correctness onto every caller and returns silently (`store/workspace.ts:97-100`); the grow-on-restore sits in the boot caller, not in `deserializeWorkspace` (`PanelHost.tsx:174-186` vs `workspace.ts:265`) | Dead Marketplace button (F2); squeezed named loads (F6) |
| 7 | Better together / apart | at-risk | `page.tsx:45-199` is one effect that boots eight subsystems and 12 subscriptions with no ordering contract; restore ordering against plugin bootstrap is implicit (`PanelHost.tsx:214`) | F11 |
| 8 | Define errors out of existence | **violate** | Masked at the wrong level: unknown panel id is a no-op (`store/workspace.ts:97-100`); every Settings fetch failure reads as "sidecar not connected" (`SettingsPanel.tsx:711-716,849-853`); `handleRemove` has no handler (`:424-427`) | Failures render as "nothing happened" (F2, F7, F8) |
| 9 | Design it twice | at-risk | Both designs sit side by side. StatusChrome's probe re-runs on `sidecarStatus` (`StatusChrome.tsx:104-106`); Settings' SearXNG/hardware reads sample once (`SettingsPanel.tsx:792-802,1213-1223`) | Stale "Ready" (F8) |
| 10 | Comments describe the non-obvious | at-risk | Excellent why-comments (`PanelHost.tsx:175-179` setTimeout-not-rAF; `EmptyState.tsx:8-13`) but several are false: `SettingsPanel.tsx:1345,1354`, `:72`, `:1306,1310`; `PanelHost.tsx:118-119`; `region.ts:46` | Readers trust invariants the code does not hold (F3, F4, F13) |
| 11 | Comments first | pass | Contract docs precede bodies: `DataTable.tsx:13-39`, `DataBadges.tsx:1-19`, `types/panel-context.ts:35-56` | — |
| 12 | Names | at-risk | `openPanel(panelId)` accepts component ids at two call sites; `minWidth` on DataTable is a class string, not a width (`DataTable.tsx:123-124,224`); bus `source` means a different id space than the "focused source" | F2 |
| 13 | Modifying existing code | at-risk | Stale phase narration survives edits (`types/panel-context.ts:4-17` "Teammate C/A", the "MUST skip self-echo" rule for a sidebar that never publishes); `PANEL_MIN_SIZE` keeps `chat-sidebar` after the chat moved to AgentDock | Dead rules the next reader must disprove |
| 14 | Consistency | **violate** | Error copy: WorkspaceDialog prefixes every failure with "Could not reach the sidecar —" (`WorkspaceDialog.tsx:181,203,217`) while Settings shows the WorkspaceError text (`SettingsPanel.tsx:1601,1620`); reserved-name filtering exists in Settings (`:1598`) but not the dialog; 27 EmptyState adopters vs 39 bespoke `text-negative` error files | F5, F7 |
| 15 | Code should be obvious | at-risk | Focus join only works for the chart by singleton accident (`context-provider.ts:276-277` falls to `charts[0]`); `DataTable` `cell()` returning `undefined` silently falls back to raw `row[key]` (`DataTable.tsx:153-155`) | F1 |
| 16 | Design for the future | at-risk | Speculative: `selectEventBySource` "for a future watchlist-driven chart" (`store/panel-context.ts:99-109`, zero callers); `PanelContextEvent.kind` is never read by any consumer. Missing the hook evidence demands: a typed panel-id registry | F1, F2, F6 |
| 17 | Performance as design | pass | Probe cache with asymmetric TTLs (`StatusChrome.tsx:51-68`); frozen empty snapshot defeats the re-render loop (`store/panel-context.ts:74-97`); autosave debounce (`PanelHost.tsx:13,188-193`). The only gap is correctness, not speed (F10) | — |
| 18 | Increments are abstractions | at-risk | Each Settings feature landed as its own client, copy and fetch policy (R9 SearXNG, D60 probe, Pass-A region seam) with no shared "sidecar-backed setting row" abstraction | F4, F8 |

**Summary: 2 pass, 12 at-risk, 4 violate (2/18 pass).**

## Overall impression

The visual primitives are careful. DataTable, EmptyState and StatusChrome show real design thought, down to measured collapse ladders. The shell around them is held together by string literals typed in two places. The biggest opportunity is small and mechanical: **make every cross-module id a typed constant owned by the module that defines it.** That covers panel ids, component ids, bus sources and keybinding chords. It would have made F1, F2, F3 and F6 impossible, and none of them needs a redesign to fix.

## What's working

- **PanelHost's lifecycle discipline** (`PanelHost.tsx:135-211`). The api-identity plus `mountedRef` double guard, subscriptions disposed on every exit path, and `setTimeout` chosen over rAF with the reason written down together remove a class of StrictMode/HMR and occluded-window bugs. This cuts unknown unknowns.
- **StatusChrome's honesty contract** (`StatusChrome.tsx:70-115,221-258`). It downgrades only on a *confirmed* failure, positive and negative results cache with different TTLs, and the tooltip always carries the exact ids behind the short form. It hides a real protocol behind one hook.
- **DataTable's null and tier law** (`DataTable.tsx:136-175`). One place decides the null glyph, numeric alignment and tier colours; my scan found no numeric column that relies on the raw `String()` fallback. Changing a formatting rule touches one file.

## Priority issues

- **[P0] Bus join key is a free string: focus and publish use different id schemes** (F1, high). *Principles:* information hiding, obviousness. *Complexity symptom:* unknown unknowns. *Why it matters:* the "this/it" deixis that FR-002/FR-007 promise is broken for chips, badge, planner and equity focus, and the tests hide it. *Fix:* publishers key the bus by `props.api.id`; add one test that drives `setFocusedSource` with the real default-layout ids; later, a typed `PanelId`.
- **[P1] Panel id vs component id namespace, plus a silent `openPanel`** (F2, medium). *Principle:* pull complexity down / define errors. *Symptom:* change amplification. *Fix:* change `openPanel("marketplace")` at both sites; dev-mode `console.error` on an unknown id; modules export their id constants.
- **[P1] Min-size policy trapped in the React host** (F6, medium). *Principle:* information hiding / temporal decomposition. *Symptom:* change amplification (layout-templates restates the numbers). *Fix:* create `lib/panel-sizing.ts`, call the grow sweep from `deserializeWorkspace`, and add a parity test against `collectPanels()`.
- **[P1] EmptyState cannot say "failed"** (F5, medium). *Principle:* general-purpose / consistency. *Symptom:* cognitive load, since users cannot tell a failed load from an empty one. *Fix:* `variant: "error"` with `role="alert"` and a retry cta; migrate the News, Macro and Analyst error sites.
- **[P2] Settings' private sidecar clients** (F8, medium) and **false Region copy** (F4, medium). *Principle:* different layer / comments. *Fix:* add `sidecarPost`, surface the SidecarError reason, refetch on visibility; rewrite the Region hint from `DEFAULT_REGION` and state that region picks market, providers and calendar.

## Persona walkthrough

**Tactical Tornado.** Asked for "focus-aware suggestions", the Tornado wrote `SuggestionChips.useFocusedSymbol` to read `lastEventBySource[focusedSource]` (`SuggestionChips.tsx:47-66`). They tested it by seeding both keys with `"chart-1"` and shipped. `PanelHost.tsx:198` and `ChartPanel.tsx:885` were never opened together. The next feature, the planner's `_planner_context` (`agent_runtime.py:125`), guessed a *third* spelling (`"chart"`, `"equity-overview"`). Each new consumer adds another literal list that has to agree with six publishers.

**Strategic Thinker.** They would make the dockview panel id the bus key, since it is already handed to every panel as `props.api.id`. `PanelHost` would stay the only writer of focus, and publishers would never mint ids. The same move applies to `openPanel`: accept only ids exported by the owning module. For sizing, `PanelHost` would import `panel-sizing.ts` instead of owning it, so `workspace.ts` and `layout-templates.ts` read the same numbers. That is three small typed seams and no new layers.

## Minor observations

- `page.tsx:94-103`: two subscriptions do identical work (`setCommands` on `enabled` or on `modules` change) and could be one. The palette also keeps a *copy* of derived commands that four sites must re-push (`page.tsx:51,91,96,101`); a selector would remove the copy.
- `WorkspaceDialog.tsx:181,203,217`: every load or delete error is prefixed "Could not reach the sidecar —", including a 404 or "The panel layout is not ready yet". Settings shows the plain WorkspaceError text for the same failures (`SettingsPanel.tsx:1601,1620`).
- `EmptyState.tsx:48-49`: `pt-16` is overridden by the later `py-6`/`py-8` under `twMerge`, so it is dead.
- `store/panel-context.ts:99-109`: `selectEventBySource` has zero callers. `PanelContextEvent.kind` is published but never read.
- `page.tsx:288` still mounts `OrderConfirmationDialog`, and `PanelHost.tsx:69` sizes `broker-order-entry`. Both are informational here: they go with the trading removal (operator decision, 23 Sep).
- `SettingsPanel.tsx:1656`: `void resetLayout()` wraps a synchronous function. It is harmless but reads as if the call were async.

## Questions to consider

- What if `PanelSpec.id` were the *only* id a panel ever had, used for dockview, the bus, `openPanel`, sizing and persistence? Which of the six hand-copied tables (see `COD-workspace-layout` on id tables) would disappear?
- Could "unknown panel id" become impossible rather than silent, for example by making `openPanel` take a `PanelId` union generated from the registered modules?
- Should Settings rows that read the sidecar share one `useSidecarResource(path)` hook with the same retry and visibility semantics as `useRetryOnSidecarReady`, instead of each section inventing its own fetch policy?

## Run notes

- Target slug: n/a (persistence skipped by design; R15 outputs are the record).
- Ignore list: none (`.aposd/critique/ignore.md` absent).
- Independence: degraded (sequential).
- Temp files: the scratch test and config live in the session scratchpad only; the evidence copy is under `census/code/evidence/`.
- Findings: 13 (1 high, 7 medium, 5 low).
