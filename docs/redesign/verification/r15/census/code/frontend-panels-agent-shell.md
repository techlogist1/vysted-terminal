# CRITIQUE — `frontend-panels-agent-shell`

**Subsystem:** Frontend Panels: Agent & Chat Shell (`CODE_PARTITION.json` entry `frontend-panels-agent-shell`)
**Owning files:** 26 (7,312 LOC) — `src/modules/chat/*`, `src/modules/agent-builder/*`,
`src/components/{AgentDock,CommandPalette,OnboardingBanner,OnboardingFlow,KeyEntryDialog}.tsx`.
`message-notices.ts` / `streaming.ts` in the same directory belong to `error-layer` and were read
only as callers, never graded here.
**Method:** `aposd-critique` skill invoked and followed. **Assessment independence: degraded
(sequential)** — no sub-agent tool is available in this worker, so Assessment A (Strategic Thinker)
was completed and recorded before Assessment B (Tactical Tornado) was run. Snapshot persistence
skipped (no `.aposd/` tree in this repo; the census file is the artifact).
**Read:** every non-test file in the partition in full, plus the callees the claims depend on
(`src/store/proposed-changes.ts`, `src/store/provider-keys.ts`, `src/store/active-agent.ts`,
`src/lib/delegate-runs.ts`, `src/lib/hardware-fit.ts`, `sidecar/services/budget_guard.py`,
`sidecar/services/agent_tools/catalog.py`, `sidecar/models/custom_agent.py`).

---

## Tactical Tornado verdict

**Risk: medium-high, and localized.** The chat core (`ChatSidebar.tsx`, `mentions.ts`,
`slash-commands.ts`, `chat-markdown.ts`, `composer-collapse.ts`) is the opposite of tornado code —
it is heavily reasoned, every non-obvious branch carries a comment naming the bug it fixes, and the
pure parsing layers are genuinely deep. The tornado lives at the **edges**, in exactly the places a
bug hunt walks past because they work:

| # | Red flag | Where |
|---|---|---|
| 1 | **Information leakage** — the host tool catalog re-declared by hand on the frontend | `src/modules/agent-builder/form.tsx:21-42` (20 ids) vs `sidecar/services/agent_tools/catalog.py` → `agent_selectable_tool_ids()` (50 ids) |
| 2 | **Information leakage** — the provider registry re-declared by hand | `form.tsx:46-54` (7) vs `types/ai.ts:43-51` + `model_registry.provider_ids()` (8; `openrouter` missing) |
| 3 | **Duplicated truth** — the auto-apply policy re-derived at two call sites | `ChatSidebar.tsx:583-589`, `ChatSidebar.tsx:963-970` vs the authority at `src/store/proposed-changes.ts:118-120` |
| 4 | **Repetition** — "the focused symbol" extracted three ways | `ChatSidebar.tsx:2053-2061`, `SuggestionChips.tsx:47-67`, `context-provider.ts:276-278` |
| 5 | **Comment holding an invariant the structure could hold** | `form.tsx:16-20` ("Update this list whenever catalog.py gains a new read_handler"), `SuggestionChips.tsx:45-46` ("mirroring `describeContext`") |
| 6 | **Comment contradicts code** | `CommandPalette.tsx:121-122` "rebuilt on each render" on a `useMemo(..., [])`; `CommandPalette.tsx:20-22` "resolves the `palette.open` binding" on a hardcoded `⌘K` |
| 7 | **Special-casing to satisfy a test** | `agent-builder.test.tsx:137,143` asserts the UI against the very constants it is meant to guard |
| 8 | **Swallowed failure → wrong message** | `OnboardingFlow.tsx:74-90` collapses network/sidecar/500/invalid into one `false` |
| 9 | **Network call with no timeout** | `KeyEntryDialog.tsx:175-189`, `OnboardingFlow.tsx:74-90` |
| 10 | **Magic-string coupling** | `ChatSidebar.tsx:1191` compares against the sentinel minted at `ChatSidebar.tsx:2044` |
| 11 | **Dead conditional** | `ResearchActivity.tsx:158-159`, `MentionPicker.tsx:66`, `SlashCommandPicker.tsx:56` — both ternary arms identical |
| 12 | **Destructive action with no confirmation** | `AgentBuilderPanel.tsx:172-191` + `:484-491` |

The most damning pattern is #1/#2: the Agent Builder — the product's "define your own analyst"
surface — hand-copies an allow-list the sidecar deliberately made *derived* (`custom_agent.py:28-38`
says so explicitly, naming the previous hand-maintained set as the bug it fixed). The frontend then
re-introduced the same bug one layer up, and the test that should have caught it asserts the copy
against itself.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line — pattern) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **pass** | `ChatSidebar.tsx:99-142` — `GENERIC_AGENT_IDS` + `usableAgentProviderPreference` encode *why* a persona pin defers, not just *that* it does | Provider resolution is one rule in one place; the R8 dead-provider regression can't return |
| 2 | Deep modules | **pass** | `mentions.ts:119-135,149-164` — `matchMention`/`insertMentionToken`: 3-arg interfaces hiding caret/token-boundary/whitespace-parity logic, shared by the picker *and* the plus menu | Typing-parity is structural, not convention |
| 3 | Information hiding | **at-risk** | `CommandPalette.tsx:184` — `item.id.replace(/^agent:/, "")` re-parses an id encoded at `store/command-palette.ts:221`, while `item.agentSummary.id` sits unused on the same object | Change the id scheme and the agent row silently switches to a bogus persona |
| 4 | Information leakage | **violate** | `form.tsx:21-42` vs `catalog.py:1520-1528` (20 vs 50 ids); `form.tsx:46-54` vs `types/ai.ts:43-51` (missing `openrouter`) | Custom agents can't be granted `research`/`web_search`/`publish_brief`; editing one strips what it had (P0/P1 below) |
| 5 | General-purpose deeper | **pass** | `composer-collapse.ts:31-64` — width→step→plan is a pure two-function ladder with no component knowledge | Re-skinning the composer cannot break the overlap guarantee |
| 6 | Different layer, different abstraction | **at-risk** | `ChatSidebar.tsx:960-970` — a *presentation* layer re-deriving the *store's* apply decision instead of reading the outcome | The transcript can contradict the gate (P1 below) |
| 7 | Pull complexity downward | **violate** | `BudgetConfig.tsx:40-46` — an empty field yields `undefined`, pushed straight to the wire; `JSON.stringify` drops it; `budget_guard.py:152-156` reads `None` as *no ceiling* | The component documented as "the trust gate for autonomous spend" can silently remove the spend ceiling |
| 8 | Better together / apart | **pass** | `ChatSidebar.tsx:1129-1349` + `Composer` (`:1577-1911`) split at the send/render seam; pickers extracted as pure presentational lists | 2,064 LOC, but each piece is separately readable |
| 9 | Define errors out of existence | **violate** | `OnboardingFlow.tsx:74-90` — `Promise<boolean>`; every failure mode is `false`, rendered as `:408-411` "That key wasn't accepted by OpenRouter" | First-run tells a user with a valid key that it's bad (P1) |
| 10 | Design it twice | **at-risk** | `slash-commands.ts:15-99` (legacy verbs) and `:113-305` (curated registry) coexist; `ChatSidebar.tsx:689-699` tries one then the other | Two parsers, one input; `/export`'s `[fmt]` arg (`:209-215`) is advertised and silently dropped (`ChatSidebar.tsx:596-623`) |
| 11 | Comments describe non-obvious | **pass** | `ChatSidebar.tsx:243-249` (E10 negative-margin clip rule), `:1023-1027` (raw-chat history regression) — each names the failure it prevents | Genuinely best-in-repo commentary |
| 12 | Comments first | **pass** | `context-provider.ts:50-68` — `totalValue: number \| null` documented as "NEVER 0 as a stand-in for unknown" before the field | The honesty contract is legible at the type |
| 13 | Choosing names | **pass** | `usableAgentProviderPreference`, `lastSentDepth`, `enqueueSlashChange`, `briefPublished` — each says what it is | — |
| 14 | Modifying existing code | **at-risk** | `ChatSidebar.tsx:100` redefines `DEFAULT_AGENT_ID = "copilot"` although the file already imports from `store/active-agent.ts:13`, which exports the identical constant | Two truths; a change to the concierge id lands in one |
| 15 | Consistency | **violate** | `AgentDock.tsx:68-78` honours `bindingFor("agent.toggle")`; `CommandPalette.tsx:75-84` hardcodes `⌘K` for the equally-rebindable `palette.open` (`store/keybindings.ts:59`). `writeCustomAgent` (`AgentBuilderPanel.tsx:90-101`) surfaces the server `detail`; `deleteCustomAgent` (`:104-111`) throws it away | A rebound palette key is dead config; delete failures are unexplainable |
| 16 | Code should be obvious | **at-risk** | `ChatSidebar.tsx:1191` `contextBadge !== "Context: none"` — a behaviour gate on a sentence minted 850 lines away (`:2044`) | Reword the sentinel → the badge is gone forever, silently |
| 17 | Design for the future | **at-risk** | `form.tsx:46-54` hardcodes providers while the sidecar's list is *config-driven by design* (`model_registry.json`) | Every new provider ships a stale builder and a silent rewrite (P0) |
| 18 | Performance as design | **pass** | `ChatSidebar.tsx:186` `NOOP_CITE` module constant to keep `MarkdownBody`'s `useMemo` stable; `:426-432` three primitive bus slices instead of one object selector | Streaming render cost is deliberately managed |

**Summary: 9 pass, 5 at risk, 4 violate (9/18 pass).**

---

## Overall impression

This is careful code with a soft rim. The parts a reviewer would stress-test — stream lifecycle,
abort/queue/drain, the diff gate, markdown repair, the collapse ladder — are the strongest in the
partition, and their comments are load-bearing rather than decorative. The failures cluster in the
**configuration boundaries**: three separate places where a frontend list hand-mirrors a list the
sidecar deliberately derives, and two places where the UI re-derives a decision a store already
made. Every one of them works today and drifts tomorrow, and two of them are already drifted.

The single biggest complexity win is to stop re-declaring the host's vocabulary on the frontend:
serve the tool ids and provider ids the same way `knownModels` is already served
(`types/ai.ts:75-77` proves the pattern exists in this codebase), and the Agent Builder's three
worst findings collapse into one deletion.

## What's working

- **`mentions.ts` + `insertMentionToken` is a genuinely deep module.** One insert path
  (`mentions.ts:149-164`) is shared by the typed `@` picker (`ChatSidebar.tsx:1720-1735`) and the
  plus menu (`ComposerPlusMenu.tsx:316-320`), so "the menu and typing produce byte-identical text"
  is a structural fact, not a test. Cognitive load: the caller never thinks about whitespace parity.
- **The composer collapse ladder is a pure function** (`composer-collapse.ts:31-64`): width → step →
  plan, with the components consuming only the plan (`ChatSidebar.tsx:1627,1883,1897`). Change
  amplification is near zero — a density change is one `switch` arm.
- **`buildPlusMenuSections` derives from the catalog** (`ComposerPlusMenu.tsx:49-56`), so adding a
  static mention appears in both the picker and the menu with one edit. This is exactly the pattern
  `form.tsx:21-42` should have used and didn't — the codebase already knows better one directory
  over.
- **Honest-unknown discipline in `context-provider.ts`** (`:50-68,166-188,246-258`): `totalValue`
  is `number | null`, never a fabricated `0`, with the reason (`totalValueNote`) threaded through.

---

## Priority issues

### [P0] The Agent Builder hand-copies a catalog the sidecar derives — and it has drifted

- **Principle:** 4 (Information leakage), 17 (Design for the future)
- **Complexity symptom:** Change amplification + unknown unknowns
- **Evidence:** `src/modules/agent-builder/form.tsx:21-42` declares 20 tool ids with the comment
  "must match the sidecar allow-list … verified by `test_capability_catalog.py`".
  `sidecar/models/custom_agent.py:28-38` derives its allow-list from the catalog *precisely because*
  a hand-maintained set had rotted before. Running it:
  `agent_selectable_tool_ids()` → **50** ids. The 20 in the UI are all valid; **30 are missing**,
  including `research`, `web_search`, `news`, `publish_brief`, `market_overview`,
  `corporate_announcements`, `shareholding_pattern`, `get_portfolio`, `get_terminal_state` and every
  host action.
- **Why it matters:** A user-defined agent **cannot be granted the product's headline capability**.
  "Build your own analyst" ships an analyst that cannot research, cannot search the web, cannot read
  the terminal and cannot publish a brief. `test_capability_catalog.py` does not cover this list —
  it audits the Python registry⟺catalog pair; nothing asserts the TS copy.
- **Fix:** Serve the ids. `GET /agents/tool-ids` (or add a field to the existing providers/agents
  payload — `types/ai.ts:75-77` already does exactly this for `knownModels`) and render
  `KNOWN_TOOL_IDS` from the response, with the static array kept only as a pre-sidecar fallback.
  Same for `KNOWN_PROVIDER_IDS` (`form.tsx:46-54`) against `GET /llm/providers`.

### [P0] Editing a custom agent silently strips tools and rewrites its provider

- **Principle:** 4 (Information leakage), 9 (Define errors out of existence)
- **Complexity symptom:** Change amplification (silent user-data loss)
- **Evidence:** `AgentBuilderPanel.tsx:157-163` reconciles the tool set by looping **only over
  `KNOWN_TOOL_IDS`**, so an agent's ids outside that 20 never enter form state; `form.tsx:139-141`
  then filters the payload to the same 20 on submit. Independently,
  `AgentBuilderPanel.tsx:61-63` falls back to `"anthropic"` whenever
  `agent.defaultProvider` is not in the hardcoded seven — and `openrouter` is a first-class provider
  (`types/ai.ts:51`; `model_registry.provider_ids()` → 8 ids including `openrouter`).
- **Failure scenario:** a custom agent with `tools: ["research","web_search"]` and
  `default_provider: "openrouter"` (creatable today via `POST /custom-agents`, which the sidecar
  accepts) → user clicks **Edit**, changes only the display name, clicks **Save changes** →
  `PUT /custom-agents/{id}` writes `tools: []` and `default_provider: "anthropic"`. No warning, no
  diff, no undo.
- **Fix:** Carry unknown tool ids through untouched — keep the agent's full `tools` set in form
  state (`setField("tools", next.tools)` instead of the toggle loop; render unknown ids as
  read-only chips) and drop the `filter` at `form.tsx:139-141` (the sidecar already validates).
  Replace the `"anthropic"` fallback with the agent's own value.

### [P1] The transcript claims "Applied:" before the apply can fail

- **Principle:** 6 (Different layer, different abstraction), 15 (Consistency)
- **Complexity symptom:** Cognitive load — two surfaces state contradictory facts
- **Evidence:** `ChatSidebar.tsx:963-970` writes `Applied: ${title}` synchronously from
  `useAgentAutonomyStore.getState().autonomy === "auto"`, re-deriving the decision that
  `store/proposed-changes.ts:118-120` actually made. `accept()` is **async** and can fail:
  `proposed-changes.ts:150-153` (`applyHostActionAsync` → `null`) and `:163-167` **re-pend** the
  change with a `detail`, which `ProposedChangesReview.tsx:121-125` renders as
  "Couldn't apply: … — try again." The transcript line is already written and never corrected.
- **Failure scenario:** AUTO mode, agent calls `set_chart_symbol` with incomplete args → chat says
  "Applied: Chart NVDA" while the gate below says the change failed. The transcript — the durable
  record the user *and* the sidecar's divergence check read back — carries the false one.
  `enqueueSlashChange` (`ChatSidebar.tsx:583-589`) has the same defect and additionally omits the
  `kind !== "order"` half of the store's predicate.
- **Fix:** Make `enqueue` return the outcome (or have `accept` resolve to `applied | staged |
  failed`) and write the step line from that one value at both call sites — never from a re-derived
  autonomy read.

### [P1] First-run tells a user their valid key is bad whenever anything else is wrong

- **Principle:** 9 (Define errors out of existence), 15 (Consistency)
- **Complexity symptom:** Unknown unknowns — the user cannot distinguish "wrong key" from "app not
  ready"
- **Evidence:** `OnboardingFlow.tsx:74-90` `validateKey` returns `Promise<boolean>`: a non-`ok`
  HTTP response → `false`; any throw (sidecar still booting, no network, DNS) → `false`.
  `:348-351` maps that single `false` to `status: "invalid"`, rendered at `:408-411` as
  "That key wasn't accepted by OpenRouter. Check it and try again." The **sibling dialog does this
  correctly** — `KeyEntryDialog.tsx:175-189` returns `{ok, detail}` and surfaces
  `sidecar returned ${status}` / the provider's own reason (`:148-153`).
- **Why it matters:** this is the first-run headline path, and the sidecar's own boot is the most
  likely thing to be unready at that moment. The user retypes a correct key repeatedly and concludes
  the product is broken.
- **Fix:** Delete `validateKey` and call the existing `postValidate` shape (lift it out of
  `KeyEntryDialog.tsx` into `lib/`); distinguish `invalid` (provider said no) from `unreachable`
  (transport/sidecar) and add an `AbortSignal.timeout(…)` to both.

### [P1] The Delegate budget editor can remove the ceiling it exists to enforce

- **Principle:** 7 (Pull complexity downward)
- **Complexity symptom:** Change amplification into a money path
- **Evidence:** `BudgetConfig.tsx:40-46` — clearing a field gives
  `n === undefined` → `Number.isFinite(undefined)` is `false` → the key is set to `undefined`.
  `lib/delegate-runs.ts:97-102` puts it on the wire, where `JSON.stringify` **omits** the key, so
  the sidecar receives no `max_spend_usd`; `sidecar/services/budget_guard.py:152-156` guards every
  ceiling behind `if self.max_X is not None` — absent means **no ceiling**. The component's own
  docstring (`BudgetConfig.tsx:5-6,15-19`) says the opposite: "bounded … so an autonomous run can
  never overrun unbounded … the trust gate for autonomous spend."
- **Failure scenario:** user clears the `$` box (a plausible "I don't want to cap dollars, I'm
  capping tokens" action, and the empty box reads as a default, not as *off*) → the durable
  background run has unlimited spend on a BYOK key.
- **Fix:** Clamp in the editor — an empty/non-finite/negative input falls back to the
  `DEFAULT_DELEGATE_BUDGET` value for that key (`BudgetConfig.tsx:8-13`) rather than `undefined`.
  One line each; the "no ceiling" state then has no UI path at all.

---

## Minor observations

- `CommandPalette.tsx:121-122` — `useMemo(() => buildPaletteCorpus(), [])` under the comment
  "rebuilt on each render from live Zustand stores". It is built once per palette open (Radix
  unmounts the body), and `buildPaletteCorpus` reads via `getState()` so it would not be reactive
  even without the memo. Fix the comment, or drop the memo and say why it's per-open.
- `CommandPalette.tsx:75-84` vs `AgentDock.tsx:68-78` — the palette ignores the rebindable
  `palette.open` binding (`store/keybindings.ts:59`) that its own docstring (`:20-22`) says it
  resolves. A user who rebinds it gets silence.
- `ChatSidebar.tsx:1191` / `:2044` — `contextBadge !== "Context: none"` couples a render gate to a
  user-facing sentence. Return a discriminated value (`{kind:"none"} | {kind:"panels", text}`) and
  the badge can't be lost by a copy edit.
- `ChatSidebar.tsx:765` then `:788-806` — `appendUser(prompt)` runs *before* the API-key gate, so a
  missing key leaves an orphaned user turn in the transcript with no assistant bubble and no error
  row; the only signal is the ephemeral status line. Gate before appending, or append a failed
  assistant message so the transcript stays a faithful record.
- `AgentBuilderPanel.tsx:172-191,484-491` — `×` deletes a custom agent immediately, no confirm, no
  undo. `deleteCustomAgent` (`:104-111`) also discards the server's `detail` that
  `writeCustomAgent` (`:90-101`) carefully surfaces.
- `OnboardingBanner.tsx:32,49-53` + `store/provider-keys.ts:58-62` — `hasAnyKey()` counts only
  key-requiring providers, so a user who completed the "private & free" local path
  (`OnboardingFlow.tsx:266-273`) is told forever that they need a key to "unlock … research tools",
  contradicting `OnboardingFlow.tsx:249-253` ("web research run right now"). Dismissal is a plain
  `useState` (`:26`), so it returns every relaunch.
- `KeyEntryDialog.tsx:161,175-189` — Cancel is disabled while `status === "validating"` and the
  validate fetch has no timeout; a hung provider leaves the dialog with both buttons disabled.
- `agent-builder.test.tsx:137,143` — asserts the rendered UI against `KNOWN_TOOL_IDS` /
  `KNOWN_PROVIDER_IDS`, i.e. the constants it should be guarding. It cannot fail on drift. Assert
  against a fixture snapshot of the sidecar's list instead.
- Dead ternaries (both arms identical): `ResearchActivity.tsx:158-159`, `MentionPicker.tsx:66`,
  `SlashCommandPicker.tsx:56`.
- `slash-commands.ts:209-215` advertises `/export [fmt]`; `ChatSidebar.tsx:596-623` ignores `args`
  and always writes markdown. Drop the `argHint` or honour it.
- `ChatSidebar.tsx:100` redefines `DEFAULT_AGENT_ID` although `store/active-agent.ts:13` exports it
  and the file already imports from that module (`:96`).
- `AgentDock.tsx:112-128` — `role="separator"` resize handle is pointer-only: no `tabIndex`, no
  arrow-key handler, no `aria-valuenow`. Keyboard users cannot resize the agent column.

## Persona walkthrough

**Tactical Tornado.** They wrote `form.tsx:21-42`: the fastest path to a working Tools picker is to
paste the ids you happen to need today and leave a comment telling the next person to keep it in
sync. Then they wrote the test that reads the same constant (`agent-builder.test.tsx:137`) so CI is
green, and `AgentBuilderPanel.tsx:61-63`'s `?? "anthropic"` so an unexpected value never crashes the
form. Each move is locally reasonable and one minute cheaper than the alternative; together they
produced a builder that cannot grant 30 of 50 capabilities, silently deletes the ones it doesn't
know, and has a test that certifies it. Left alone, the next tornado adds `openrouter` to the array
and the cycle restarts.

**Strategic Thinker.** They would notice that this repo *already solved this*: `knownModels` rides
`GET /llm/providers` (`types/ai.ts:75-77`) precisely so the frontend never re-declares a
config-driven list, and `buildPlusMenuSections` (`ComposerPlusMenu.tsx:49-56`) derives its menu from
one catalog so a new entry needs one edit. They would serve `agent_selectable_tool_ids()` and
`model_registry.provider_ids()` the same way, keep the static arrays as a pre-sidecar fallback only,
make the Edit path carry unknown ids through untouched, and delete the `filter` and the
`?? "anthropic"` — both of which exist only to paper over the stale copy. Three findings, one
deletion. They would apply the same lens to `ChatSidebar.tsx:963-970`: the store already knows
whether the change applied, so the transcript should *read* that outcome rather than *re-derive* it.

## Questions to consider

- `types/ai.ts` already serves `knownModels` from config so the frontend never guesses a model list.
  What stopped tool ids and provider ids from riding the same wire — and is anything else in this
  shell still guessing at the sidecar's vocabulary?
- Could the auto-apply narration error be defined out of existence by having `enqueue` return
  `"applied" | "staged"` (and `accept` resolve to the real outcome), so no caller can ever be wrong
  about what happened?
- The empty BudgetConfig field currently means "no ceiling". Is there any user for whom that is the
  intended reading — and if not, should the state exist at all?
