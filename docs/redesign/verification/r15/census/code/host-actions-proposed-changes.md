# Code critique: host-actions-proposed-changes

R15 Stage B item 2, session 2. Critic model: `claude-opus-5-5[1m]`. HEAD `d6dc63c` on `004-r4-experience-rebuild`.

**Scope.** Owning files: `src/lib/host-actions.ts` (1,572 LOC), `src/store/proposed-changes.ts` (240), `types/proposed-change.ts` (56), `types/safety.ts` (236). Tests read: `src/lib/host-actions.test.ts`, `src/store/proposed-changes.test.ts`. Collaborators opened to check claims: `src/store/{portfolios,notes,screener,agent-autonomy}.ts`, `src/modules/chat/{ChatSidebar,ProposedChangesReview,ComposerPlusMenu}.tsx`, `src/lib/layout-templates.ts`, `sidecar/services/agent_tools/catalog.py`, `sidecar/routers/{portfolio,safety}.py`, `sidecar/services/{kill_switch,action_ledger,broker_base}.py`.

**Trading overlay (PROMPT_code_s2.md).** I critiqued only the non-order gate: panel, chart, watchlist, brief, screener, paper-portfolio writes, notes, saved screens and layouts, and region. The order path (`propose_order` describe, `routeOrderProposal`, `resolveTargetBroker`, the `kind === "order"` branches, and the order-only types in `types/safety.ts`) is recorded as one `removed_with_feature` entry (COD-…-15) and not analysed. I critiqued the kill switch and audit log normally. Finding COD-…-10 states what they gate outside orders. The answer is nothing.

**Method.** I loaded the `aposd-critique` skill and followed it: two personas, 18 principles, and file:line evidence for every claim. No sub-agent tool was available, so the two assessments ran one after the other: Strategic first, then Tactical. Assessment independence is therefore degraded. I skipped the `.aposd/` snapshot because this worker may only write its census outputs. I proved 8 behaviours with a throwaway vitest outside `src/`, all run against the real stores. The test is saved at `evidence/host-actions-proposed-changes-proof.test.ts.txt` and its output at `evidence/host-actions-proposed-changes-proof-output.txt`.

## Tactical Tornado verdict: HIGH risk

The gate is *built* around one sound idea: stage, show a diff, accept, then apply with a truthful label. The code around that idea was grown wave by wave (R8, R9, R10, R13 comments throughout), and it shows the classic tactical marks:

- **Two parallel 300-line switches**, `describeHostAction` (577-867) and `applyHostAction` (880-1248), plus `applyHostActionAsync` (1327-1402) and `HOST_ACTION_NAMES` (66-86). Each one parses the same raw input with different helpers. The comment "the diff must promise exactly what the apply will do" (605-606) is held by discipline, and it fails: P6 shows the diff says `×0` while apply keeps `×10`, and P7b shows the diff says "not open" while apply closes the panel.
- **Casts written for a cross-team wave** that outlived the wave: `as unknown as { saveScreen?: (name, payload) => unknown }` (1216-1218) and `as Parameters<typeof screener.applyFilters>[0]` (1165). Both APIs landed with signatures that ignore what host-actions passes. `save_screen` saves the wrong recipe (P3), and `run: true` never runs (P4). **Both unit tests mock the store and assert the arguments were passed** (`host-actions.test.ts:1079-1124`). That is special-casing to satisfy a test, and CI stays green on two no-ops.
- **Argument semantics re-encoded by hand** against the catalog that CLAUDE.md calls the one source of truth. `write_note` defaults to replace while the catalog says append (P2), and `'global'` becomes a ticker named GLOBAL (P1). `save_layout` without a name should update the active layout; the code writes "Agent layout" instead.
- **The most damning pattern.** The gate stores only the raw `{name, input}` and resolves the *target* twice: once for the diff at enqueue, and again at accept. What the user approved is not bound to what gets mutated. P5 shows it: a delete that was reviewed as portfolio A's `TCS ×10` deleted portfolio B's `TCS ×99` lot.

Flag count: 11 red flags with locations (information leakage ×3, repetition ×2, conjoined methods ×2, comment/code contradiction ×2, special-general mixture ×1, pass-through/dead seam ×1).

## Design principles score: 2 pass, 6 at risk, 10 violate (2/18 pass)

| # | Principle | Grade | Evidence (file:line: pattern) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | violate | `host-actions.ts:1212-1219`: "until the API lands the action returns an honest null"; the API landed and the cast stayed | Two agent actions report success while doing nothing correct (P3, P4) |
| 2 | Deep modules | at-risk | `proposed-changes.ts:77-89`: an 8-method interface over a simple queue is fine, but `enqueue` returns only an id (`:95-122`) and hides the one fact callers need (did it apply?) | Callers rebuild the outcome from the autonomy flag (`ChatSidebar.tsx:965`) |
| 3 | Information hiding | violate | The raw tool `input` is the stored proposal (`proposed-changes.ts:101`). Every consumer (describe, apply, ack) re-parses it | Target and argument resolution drift between diff and apply (-1, -6) |
| 4 | Information leakage | violate | `catalog.py:1388` `"default": "append"` vs `host-actions.ts:1183` `=== "append"`; `catalog.py:1385` `'global'` vs `host-actions.ts:565` `"general"` | Note overwrite and phantom GLOBAL note (P1, P2) |
| 5 | General-purpose = deeper | at-risk | `publishAckStatus` (`:1411-1416`) is generic in name, but the only non-trivial case is `startsWith("Kept")` for one action | A copy edit changes the protocol status (-13) |
| 6 | Different layer, different abstraction | violate | `briefFromInput`/`carryBriefDepth` (`:88-250`: research-brief domain logic), screener parsing (`:340-453`) and portfolio HTTP (`:1254-1317`) all sit inside the gate module | Every family's change touches the 1.5 kLOC gate file (-14) |
| 7 | Pull complexity downward | violate | `screener.ts:200-203`: "the caller MUST follow up with runScreener()"; the caller doesn't (`host-actions.ts:1159-1174`) | `run:true` narrates "running" and never runs (P4) |
| 8 | Better together / apart | violate | describe and apply split one concept (an action's parsed intent) into two switches, `:577` / `:880` | Each new action touches 4-5 places. An unknown name silently becomes kind `panel` (`:865`) |
| 9 | Define errors out of existence | at-risk | `write_note` destructive branch taken on an *omitted* arg (`:1183-1185`); `resolveHolding` guesses by symbol on an id miss (`:555-559`) | Data loss on the default path (-2); wrong-lot mutation (-1) |
| 10 | Design it twice | violate | No evidence of an alternative to "switch on name, re-parse input"; the per-action record `{parse, describe, apply}` would remove -1, -6 and -12 at once | The same bug class recurs per action (the id-drift fixes at `:909-913` and `:1167-1168` missed `:1012`) |
| 11 | Comments describe the non-obvious | pass | `host-actions.ts:1093-1102` (why the same-run shrink guard exists, why never merge markdowns); `proposed-changes.ts:129-131` (why claim synchronously) | These comments carry real invariants that code can't show |
| 12 | Comments first / comment–code agreement | violate | `proposed-changes.ts:113-114` and `agent-autonomy.ts:7-12` say AUTO covers UI/layout/chart/watchlist; the code auto-applies every non-order kind (`:118`). `ChatSidebar.tsx:584` "already gone from `changes`" is false | The user is told AUTO moves panels; it overwrites notes (P8) |
| 13 | Choosing names | at-risk | "paper portfolio" in labels (`:769,783,794,1350,1388`) for the user's real tracked holdings; `kind: "data-write"` vs `"settings"` | Once trading is gone, "paper" misdescribes the surviving portfolio |
| 14 | Modifying existing code | violate | Store seams added *for* this path are unused: `portfolios.ts:223-270` (`addPosition` with a null check), `notes.ts:26-31` (`appendSymbolNote`); host-actions inlines its own versions (`:1185`, `:1342`) | Two append semantics and two add paths drift (-14) |
| 15 | Consistency | violate | `arrange_layout` focus uses raw `getPanel(panel)` (`:1012`); every sibling uses `resolvePanelToken` (`:914,950,967`) | "Focus the screener" fails through one tool and works through another (P7) |
| 16 | Code should be obvious | at-risk | `accept()` claims the change, awaits, then re-pends on failure (`:132-170`); a hung `syncPositionToSidecar` fetch with no timeout (`:1287`) leaves it "accepted" forever | A change can be stuck, neither applied nor pending |
| 17 | Design for the future | at-risk | The auto-apply predicate is a blacklist of the kind being deleted (`kind !== "order"`, `:118`) | After trading removal, AUTO = auto-apply everything (-3) |
| 18 | Performance as design | pass | Sequential `acceptBatch` is deliberate (`:186-196`, ordering matters); the ack is fire-and-forget (`:1462-1485`) and never blocks the gate | Fine at this scale; `changes` grows without bound but is small (-8) |

(Credit that is not a principle pass: `proposed-changes.test.ts` covers claim-before-await and re-pend, and the "no success label without the work" contract at `host-actions.ts:869-879` is a strong interface statement. P3, P4 and P7 show three actions breaking it.)

## Overall impression

The *shape* is right. A staged diff, a single accept point, truthful labels, re-pend on failure, and an ack back to the runtime make up a real trust spine, and the brief shrink guard and stale-run arbitration are carefully reasoned. The trouble is that the gate's unit of truth is the raw tool input rather than a resolved intent. That one decision produces most of the defects: diffs that promise something other than what apply does, targets that move between review and accept, and defaults that differ from the catalog. The single biggest opportunity is to **parse each action once, at enqueue, into a typed Intent with its targets bound**, and have describe, apply and ack all read that Intent.

## What's working

1. **Claim before await** (`proposed-changes.ts:129-136`). A concurrent accept or acceptAll can't double-apply. This defines a race out of existence with one synchronous `set`.
2. **The grounded-narration contract** (`host-actions.ts:869-879`, e.g. the `findOpenPanel` verification at `:936-942`). Apply is required to *prove* the work landed before it returns a label. That lowers unknown unknowns for the runtime's divergence check.
3. **Same-run shrink guard / stale-run arbitration** (`:1093-1126`). It is a whole-brief decision scoped by run_id, and the comments say why it never merges markdowns, so the citation markers stay coherent.

## Priority issues

- **[P0] The approved change is not bound to its target.** Principles: information hiding (3) and define errors out (9). Symptom: unknown unknowns. `proposed-changes.ts:101` stores `action: { name, input }`, and `host-actions.ts:1353` `resolveHolding(input)` re-resolves against `activePortfolio()` at accept time. P5 deleted the wrong portfolio's lot. **Fix:** resolve `{portfolioId, holdingId}` at enqueue, store it on the `ProposedChange`, apply against exactly that pair, and return null when it is gone.
- **[P0] Destructive defaults plus AUTO that covers everything.** Principles: information leakage (4) and comment–code agreement (12). Symptom: unknown unknowns. `host-actions.ts:1183` treats a missing mode as replace (the catalog says append), and `proposed-changes.ts:118` auto-applies every non-order kind. P2 and P8 wiped a note with no review. **Fix:** anything but an explicit `"replace"` appends, and an explicit `AUTO_APPLICABLE = {panel, chart, watchlist}` whitelist is read by the store, the autonomy doc and the UI hint.
- **[P1] Casts that hid two broken APIs, with mocks that bless them.** Principles: strategic (1) and pull complexity down (7). Symptom: change amplification. `host-actions.ts:1216-1229` and `:1159-1165` against `screener.ts:218` and `:302`, with `host-actions.test.ts:1079-1124` mocking both. **Fix:** delete both casts, call the typed store API (`applyFilters` then `saveScreen(name)`, and `runScreener()` when `run`), and test against the real store.
- **[P1] Describe and apply as two switches.** Principles: better together (8) and design it twice (10). Symptom: change amplification plus cognitive load. `:577-867` / `:880-1248` / `:1327-1402`. **Fix:** a `HOST_ACTIONS: Record<name, {parse, describe, apply}>` table. `HOST_ACTION_NAMES` then becomes `Object.keys`, and an unknown name fails loudly instead of becoming kind `panel`.
- **[P2] enqueue hides the outcome.** Principles: deep modules (2). Symptom: cognitive load. `proposed-changes.ts:118-121` (`void get().accept(id)`) against `ChatSidebar.tsx:965` duplicating the predicate and narrating "Applied:" before apply resolves. **Fix:** return `{ id, outcome: Promise<…> }` and narrate from the resolved outcome.

## Persona walkthrough

**Tactical Tornado.** Next wave, someone adds `delete_saved_screen`. They add the name to `HOST_ACTION_NAMES` (`:66`), a `describeHostAction` case that reads `useScreenerStore` and shows "Saved screens: −X", and an `applyHostAction` case with another `as unknown as { deleteScreen?: … }` duck-type "until Team FRONTEND-DATA ships". They add a vitest that `vi.fn()`s `deleteScreen` and asserts it was called. The name is also added to the catalog with `"default"` semantics nobody mirrors. AUTO auto-applies the delete because `kind !== "order"`. Every step copies a pattern already in `:1207-1236`, and the gate grows another place where the diff and the effect can disagree.

**Strategic Thinker.** They keep the queue and the accept point exactly as they are, and replace the switches with one registry entry per action: `parse(input) → Intent | Error` runs once in `enqueue`, and it binds targets (holding id plus portfolio id, resolved panel id, note scope). `describe(Intent)` and `apply(Intent) → {status, label, reason}` read only the Intent. Catalog defaults are imported from one generated JSON, not re-typed. The AUTO policy is a property on the entry (`autoApply: boolean`), so the UI hint can list exactly what AUTO covers. Dead weight is deleted: `syncPositionToSidecar`, the unread `/portfolio/positions` ledger, the order path, and the unused store seams (or host-actions is switched to call them).

## Minor observations

- `types/proposed-change.ts:18-19` says `settings` covers "region + default research depth". Only `set_region` exists.
- `num()` (`:472-475`) turns `"abc"` into `NaN`, and the diff then renders `×NaN`.
- `describeHostAction("open_panel")` always says "not open" (`:611`), even when the panel is open.
- `add_to_watchlist` / `remove_from_watchlist` compare with `toUpperCase()` only, while `baseSymbol` (`:125-130`) exists for suffix-insensitive identity. `RELIANCE.NS` versus `RELIANCE` is reported as "not tracked".
- `noteScope` uppercases but doesn't `baseSymbol` either, so `TCS.NS` and `TCS` are two different notes.

## Questions to consider

- If `ProposedChange` stored a resolved Intent instead of raw input, which of the fifteen findings would still exist?
- With trading gone, what is the gate protecting *against*? If the answer is "the agent destroying user data", should AUTO ever cover `data-write`?
- Should the append-only log that is outliving `audit_orders` become the host-action outcome log (the ack payload already has `{tool_call_id, action, status}`), so the one surviving write gate has a durable record?

## Priority findings (raw file: `census/raw/code-host-actions-proposed-changes.json`)

| raw_id | sev | one line |
|---|---|---|
| -1 | high | Staged portfolio update/delete re-resolves against the active portfolio at accept, so it mutates the wrong portfolio's lot (P5) |
| -2 | high | `write_note` without mode replaces (the catalog says append default), wiping the user's note (P2) |
| -3 | high | AUTO auto-applies all non-order kinds (data-write, settings) despite docs and UI saying "UI changes" (P8) |
| -4 | high | `save_screen` saves the current draft, not the agent's criteria; the cast plus a mocked test hide it (P3) |
| -5 | medium | `write_screener_filters run:true` never runs and narrates "running" (P4) |
| -6 | medium | describe and apply are duplicate switches with different parsing; the diff lies (P6, P7b) |
| -7 | medium | `enqueue` fire-and-forgets the AUTO accept; the transcript says "Applied:" before or despite failure |
| -8 | medium | Pending proposals survive a chat clear; `clear()` has no production caller |
| -9 | medium | The sidecar positions ledger is write-only; PUT/DELETE hit no row; no timeout; `purchased_at` is lost |
| -10 | medium | The kill switch and audit log gate only broker adapters; the surviving gate has no stop and no durable audit |
| -11 | medium | Catalog/apply drift: `'global'` gives a GLOBAL ticker note; `save_layout` without a name gives "Agent layout" (P1) |
| -12 | low | `arrange_layout` focus skips `resolvePanelToken`, so it fails for aliases (P7) |
| -13 | low | Every failure reads "arguments were incomplete"; the ack status is parsed from the label prefix "Kept" |
| -14 | low | Unused store seams are re-implemented inline; 1.5 kLOC multi-layer module |
| -15 | low | `removed_with_feature`: order-proposal path and order-only safety types |
