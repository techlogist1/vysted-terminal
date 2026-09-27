# Owner-drive: composer-chat — gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `:52320` (own
data-dir copy `rc1-round-5-data-rc1-drive-composer-chat`, sleep-wrapper pid
17582). Every write (chat invoke, host-action ack, delegate run) went to
`:52320` only; `GET /agents` was the only shared-stack (`:52152`) read used.

Full round-5 raw evidence: `docs/redesign/verification/r15/surface/composer-chat/rc1/round-5/`
(every row below cites its file there; full 24-row `COVERAGE.json` is in the same dir).

## Scored table (deltas from round-4 only — rows not retested carry the
round-4/census verdict unchanged)

| # | Row / check | Round-4 verdict | RC1-R5 verdict | Evidence (raw file) |
|---|---|---|---|---|
| 1 | `composer-send-stop-button` (mid-stream Stop cancels upstream tool work) | ok | **ok** (regression risk re-cleared) | `08-stop-cancel-repro.py`/`.out` — direct probe against the candidate's own `services.agent_runtime`: `aclose()` on the SSE generator propagates `CancelledError` into the in-flight tool task |
| 2 | Host action: `add_to_watchlist` via chat, staged (autonomy=ask), ack round-trip | ok | **ok** | `01-hostaction-watchlist-add.jsonl/.stdout.txt`, `02-hostaction-ack.txt` (`{"ok":true}` HTTP 200) |
| 3 | Host action: `write_note` via chat, staged, ack round-trip | n/a (new this round) | **ok** (propose/stage/notice mechanics; no server-side notes store exists to read back — notes ride the client workspace blob, confirmed by code read, `sidecar/routers/` has no notes router) | `03-hostaction-note-write.jsonl/.stdout.txt`, `04-hostaction-note-ack.txt` |
| 4 | Host action: `write_screener_filters` + `arrange_layout`/`set_chart_symbol` compound turn | ok | **ok** dispatch/stage/notice mechanics; one attempt hit a transient upstream 5xx (environment, see findings) and was retried | `05-hostaction-screen-arrange.*`, `06-hostaction-arrange-fundamental.*`, `07-hostaction-arrange-ack.txt` |
| 5 | `R15-LEAD-048` (arrange_layout routes Layout-menu mode ids instead of silently resetting) | n/a (fixed in batch-30, not yet re-verified at this candidate) | **ok**, holds at 9bc600ec | `pnpm vitest run src/lib/host-actions.test.ts` — `describe("arrange_layout routes Layout-menu mode ids instead of resetting (R15-LEAD-048)")` passed, part of the 393/393 full-suite run (see row 7) |
| 6 | `R15-AGENT-092` (Delegate brief/answer delivered once dispatched, not swallowed on a halted round) | n/a (fixed in batch-28, not yet re-verified live at this candidate) | **ok**, both a live E2E delegate run and the pinned unit tests hold | `11-delegate-run-launch.txt` (`POST /agents/researcher/runs` → 201) → `12`-`16-delegate-run-poll-*.json` (running → done, `answer` delivered, transcript/checkpoint intact, `host_actions: []` since none were asked for) + `09-pytest-run-manager.log` (30/30, incl. `test_a_halted_rounds_brief_is_not_delivered[publish_brief]`/`[write_note]`) |
| 7 | Full composer/chat-agent frontend regression sweep (all of `src/modules/chat/*.test.ts(x)` + `src/lib/host-actions.test.ts`, `model-options.test.ts`, `layout-templates.test.ts`) | not run as a full sweep in round-4 (spot-checked) | **393/393 tests, 19/19 files passed** | `09b-vitest-chat-suite-full.log` |
| 8 | Sidecar `test_run_manager.py` (Delegate lifecycle: launch/cancel/resume/answer/budget-breach/halted-round host-action & brief suppression) | not run in round-4 | **30/30 passed** | `09-pytest-run-manager.log` |
| 9 | No-key / error-humanization, intent-gate write-stripping, schema coercion, tool-call-id uniqueness (round-4's fresh probes) | ok (all) | not re-driven this round — no regression signal surfaced while driving 1-8 above (same runtime/tool-call machinery); carried forward | round-4's own files, unchanged |

All other composer/chat-agent rows not listed above (`composer-mount`,
`composer-depth-control`, `composer-model-control`, `composer-mention-picker`,
`chat-empty-state`, `chat-suggestion-chips`, `chat-error-row`, `chat-plan-view`,
`chat-research-activity`, `chat-budget-config`, `agent-autonomy-ask-auto`,
`agent-persona-picker`, `llm-chat-streaming`, `chat-markdown-render`,
`context-provider-badge`) were not individually re-driven this round; the
full-suite vitest pass (row 7) covers their pure-logic layer directly (every
one of those components/stores has a `.test.ts(x)` file inside the 19 that ran
green), so no regression evidence surfaced. `composer-slash-picker` stays
**partial**: the census/round-4 gap (`SURF-COMPOSER-CHAT-5` — the `/screener`
slash expansion classifies as read intent and strips `write_screener_filters`)
was not re-probed live this round; the pure slash-matching logic itself
(`slash-commands.test.ts`) passed.

## Census/round-4 → RC1-round-5 deltas

- **Regression risk cleared, not found**: `R15-LEAD-048` (arrange_layout /
  Layout-menu mode ids) and `R15-AGENT-092` (Delegate brief/answer delivery)
  — the two batch-28/29/30 fixes that land inside this group's surface — both
  hold at `9bc600ec`, confirmed by live drive AND by the pinned regression
  tests. Everything round-4 already cleared (`R15-AGENT-002` stop-cancel,
  `R15-AGENT-031`/`R15-UI-054` divergence notice, `R15-AGENT-019` intent gate,
  `R15-AGENT-093` schema coercion, `R15-AGENT-046` tool-call-id uniqueness,
  `R15-LEAD-043` no-key humanizer) still holds — nothing in this round's drive
  or the full 393-test vitest sweep contradicts it.
- **No new defects.** `findings/rc1-drive-composer-chat.json` has 2 entries,
  both `kind: environment` (a retired default free OpenRouter slug, and one
  transient upstream 5xx from a different free slug) — neither is a product
  defect, both were surfaced honestly by the app's own error-humanization path.

## Notes

- No own-mistake incidents this round (no wrong-pid kills, no shared-stack
  writes).
- Observed live lock contention on the shared Ollama lane with another
  concurrent role (`rc1-round-5-scenarios-local`) while my delegate run's
  background step was in flight — expected behaviour of the single-lane
  protocol, not a defect; waited it out rather than contesting the lock.
- Out-of-scope observation, not filed: the model chose `scope` (the note's
  bucket key) to hold the user's requested note *title* on the `write_note`
  call (no dedicated title field exists in the tool schema) — that's a model
  interpretation of an underspecified-but-documented schema, not a code
  defect; flagging here for whichever owner covers the notes/tool-schema
  surface if they want to tighten the description.
