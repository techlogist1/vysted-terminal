# APOSD critique — `safety-audit` (Safety Model & Audit Log, §6.5)

Worker model: `claude-fable-5-1`. Skill `aposd-critique` loaded and followed. Read-only sweep: no
product file was touched. Raw findings: `../raw/code-safety-audit.json` (14, prefix
`COD-safety-audit-`). All 13 owning files (2,540 LOC) read in full, plus the integration points
in `services/broker_base.py`, `services/brokers/registry.py`, `routers/brokers.py`,
`src/lib/host-actions.ts`, `src-tauri/src/lib.rs`.

Proofs were run in a temp data dir (never the operator's, never `:52152`):
`scratchpad/sa/proof.py`, `proof2.py`. Output:

```
P1 hung subscriber -> is_fired after 0.3s: False
P2 unknown fired_by -> ValidationError | is_fired: False
P3 fire+reset with 0 subscribers -> audit rows: 0
P6 trigger raises: IntegrityError
P4 one unknown-action row -> tail raises ValidationError
P5 100 appends: 3.4 ms each
proof2: subscribers after replace: 0 | callbacks hit: []
```

## Tactical Tornado verdict — MEDIUM-HIGH risk

The two DB-level pieces (append-only triggers, `query_only` reader) are strategic work and they
hold. Everything wrapped around them shows the tornado's signature: the most damning pattern is
**a safety layer edited by subtraction** — the kill-switch UI was deleted in a craft pass and the
author left the OS-wide shortcut registered (`src-tauri/src/lib.rs:446`), the event emitted to
nobody (`kill_switch.rs:96`), a 50-line store slice with zero callers
(`src/store/safety.ts:196-243`), the TOS bullet promising the control
(`DisclaimerFlow.tsx:45`), and three comments announcing the mechanism is "dormant, not gone" —
while Order Entry and the live-mode route stayed reachable. 11 red flags: information leakage ×3
(action list ×3 copies, broker list ×3, firedBy ×4), conjoined methods ×1
(subscribe-overwrite / unsubscribe-by-name / `registry.register`), special-general mixture ×1
(three read functions, three SQL builders, the needed one missing), comment-is-wrong ×4,
dead code ×2.

## Design principles score — 5 / 18 pass (8 at-risk, 5 violate)

| #   | Principle                        | Grade   | Evidence (file:line : pattern)                                                                                                                                                                                                                                  | Consequence                                                                                                                  |
| --- | -------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1   | Strategic over tactical          | at-risk | `src/store/safety.ts:13-17`, `src/modules/safety/index.ts:10-12` : "removed the kill-switch UI … mechanism is dormant, not gone"                                                                                                                                | A §6.5 layer has no trigger while the path it guards is live (COD-1)                                                          |
| 2   | Deep modules                     | pass    | `sidecar/services/audit_log.py:122,152,191,248` : 4 verbs hide connection roles + triggers + WAL; `kill_switch.py:63,102,146` : subscribe/fire/reset                                                                                                              | Callers never see SQL or locks                                                                                               |
| 3   | Information hiding               | violate | action list `models/safety.py:63-76` = `types/safety.ts:81-93` = `AuditLogViewer.tsx:40-53`; firedBy `models/safety.py:29`, `routers/safety.py:91`, `types/safety.ts:39`, `kill_switch.rs:59`; `registry.py:91` : `existing._unsubscribe()  # noqa: SLF001`        | One new action/broker = 4-file edit, no parity test; a miss 422s the halt (COD-7) or bricks the viewer (COD-8)               |
| 4   | General-purpose modules          | at-risk | `audit_log.py:169-188` `range_` (no caller) vs `:199-216` own WHERE builder vs `:152` tail(limit only)                                                                                                                                                          | The query the UI needs does not exist, so filtering moved to the client over 200 rows (COD-10)                               |
| 5   | Different layer, different abstr | at-risk | `disclaimer_session.py:30` `has_session_ack` : zero production callers; `routers/safety.py:133` : gate is a caller-set boolean                                                                                                                                   | Sidecar stores the ack, never enforces it — the layer is one React `if` (COD-11)                                             |
| 6   | Pull complexity downward         | violate | `broker_base.py:442-457` : subscribers write the bus's own `kill-switch-fired` row; `routers/safety.py:126-139` reset writes nothing; `audit_log.py:154,176,205` : every reader must remember `_ensure_initialized()`                                             | Fire with 0 brokers + every reset leave no trace (COD-5)                                                                     |
| 7   | Better together / apart          | at-risk | `kill_switch.py:70` overwrite + `:73-75` pop-by-name + `registry.py:87-94` replace order                                                                                                                                                                        | Three pieces only correct in an order no caller can produce (COD-4)                                                          |
| 8   | Define errors out of existence   | violate | `routers/safety.py:88-93` `extra="forbid"` + Literal on the halt request; `kill_switch.py:114-118` event validated before dispatch; `audit_log.py:106-119` strict read model on an immutable table                                                               | The emergency stop can 422; one row makes the log unreadable forever (COD-7, COD-8)                                          |
| 9   | Design it twice                  | at-risk | `kill_switch.py:54-56,146-152` : fired state = 3 attrs                                                                                                                                                                                                          | The obvious second design (derive from the durable log) was never weighed; restart silently un-halts (COD-6)                 |
| 10  | Comments describe non-obvious    | violate | `types/safety.ts:42-44` "Adapters cancel all open orders" (they do not); `audit_log.py:13` "OperationalError" (is IntegrityError); `kill_switch.rs:20,30,75` "CmdOrCtrl+Shift+K" (is Ctrl+Cmd+Shift+K); `kill_switch.rs:47,70,78` "toolbar button still works"   | Wrong comments on the Tier-1 contract file (COD-2, COD-13)                                                                   |
| 11  | Comments first                   | pass    | `routers/safety.py:60-66` : contract for half-set range stated before code; `audit_log.py:73-81` : reader role contract                                                                                                                                          | Interfaces are described as contracts, not narrations                                                                        |
| 12  | Choosing names                   | pass    | `_writer_connection` / `_reader_connection` (`audit_log.py:52,74`), `range_` justified at `:172-174`                                                                                                                                                            | Minor: `count()` reads through the _writer_ (`:255`)                                                                         |
| 13  | Modifying existing code          | violate | `lib.rs:395,416,446` still wires plugin + command + shortcut; `safety.ts:196-243` dead slice; `kill_switch.py:216-217` `_unused()`; `docs/SAFETY_ARCHITECTURE.md:243` KillSwitchToolbar                                                                          | The removal left the design worse than either "kept" or "deleted"                                                            |
| 14  | Consistency                      | at-risk | `OrderConfirmationDialog.tsx:124-140` catch→setError vs `:164-171` try/finally; `DisclaimerFlow.tsx:62-76` vs `:55-60`, `:148-156`; `safety.ts:199` `sidecarGet` vs `:214,234,318` raw `fetch`                                                                   | Failures vanish on the handlers that lack the catch (COD-12)                                                                 |
| 15  | Code should be obvious           | at-risk | `kill_switch.py:131-135` : `_fired = True` AFTER `gather`; `:146-152` reset leaves adapters latched (`broker_base.py:441`)                                                                                                                                      | Reader assumes "fire" means fired; status says `fired:false` while nothing can trade (COD-3, COD-6)                          |
| 16  | Design for the future            | at-risk | `models/audit_log.py:56-58` "reserved for future"; `kill_switch.py:216` "keeps Any import for future"                                                                                                                                                           | Hooks for hypotheticals, while the one certain future (a new action literal) is the one that breaks (COD-8)                  |
| 17  | Performance as design            | pass    | `audit_log.py:61-68` connect + WAL + DDL per call — measured 3.4 ms/append (P5)                                                                                                                                                                                 | Fine at this volume. Note: each 2 s UI poll opens 2 connections + runs the DDL (`:102`, `:155`)                              |
| 18  | Increments are abstractions      | pass    | `models/audit_log.py:40-50` triggers; `audit_log.py:85` `PRAGMA query_only=ON`                                                                                                                                                                                  | The guarantee was built as a structure first, features on top                                                                |

## Overall impression

The subsystem's _core promise_ (rows cannot be mutated) is held by structure and proven by tests.
Its _second_ promise (you can always halt) is held by comments. The single biggest opportunity:
make the audit log the source of truth for halt state — the bus appends its own `_meta`
fire/reset rows and boot derives `fired` from the last one. That one move closes COD-5 and COD-6
and removes the "who logs the fire?" question from every adapter.

## What's working

1. **DB-enforced append-only** (`models/audit_log.py:40-50`) + a physically read-only reader
   (`audit_log.py:85`). Removes an entire class of unknown-unknowns: no code review has to ask
   "could this path rewrite history?".
2. **Subscription forced in the constructor** (`broker_base.py:100-103`) plus an independent
   `is_fired` re-check at propose and confirm (`:251`, `:345`). Two layers catching different
   failures — it is why COD-4 is medium and not critical.
3. **`export.csv` rejects a half-set range** (`routers/safety.py:67-71`) with the reason written
   into the contract. An error defined carefully at the boundary; the client simply does not use
   it well (COD-10).

## Priority issues

- **[P0] A §6.5 layer with no trigger, guarding a path that is still live** — COD-1 + COD-2.
  Principle: strategic over tactical / modifying existing code. Symptom: unknown unknowns.
  `src/store/safety.ts:13-17` says nothing listens; `src/modules/broker-connect/index.ts:26-47`
  still ships Order Entry; `kill_switch.rs:36` registers the wrong chord anyway. Two designs:
  (a) re-wire — `listen("kill-switch:requested")` → `fireKillSwitch` + fired banner in
  `page.tsx`, fix the modifiers with `cfg(target_os)`; (b) finish the removal — unregister the
  shortcut, hide Order Entry + live toggle, drop the TOS bullet. (a) is ~15 lines and keeps the
  Tier-1 promise; (b) is a Locked-decision reversal. **Tier-4: operator picks.**
- **[P1] `fire()` flips the flag last and waits forever** — COD-3. Principle: obviousness /
  define errors out. Symptom: unknown unknowns. `kill_switch.py:131-135`. Fix: set `_fired`
  before dispatch; `asyncio.wait_for(cb(event), ACK_BUDGET_NS / 1e9)`. Alternative considered:
  fire-and-forget tasks — rejected, it loses the ack timings gate 8 asserts.
- **[P1] The halt is rejectable and unrecorded** — COD-7 + COD-5 + COD-6. Principle: define
  errors out / pull complexity down. Symptom: change amplification (4 copies of `firedBy`).
  `routers/safety.py:88-93`, `kill_switch.py:114-118`. Fix: coerce unknown `fired_by`; bus
  appends `_meta` fire/reset rows; boot derives state from the last one.
- **[P1] Immutable table, intolerant reader** — COD-8 (+ COD-9 makes it invisible). Principle:
  define errors out. Symptom: unknown unknowns. `audit_log.py:106-119`. Fix: `action`/`source`
  are `str` on the read model; Literals stay on `AuditLogAppendRequest`.
- **[P2] Live-order gate defaults to the unsafe value** — COD-11. Principle: different layer,
  different abstraction. `OrderConfirmationDialog.tsx:89` `?? "paper"`. Fix: `?? "live"` now;
  stamp `mode` on the proposal at propose time as the real fix.

Remaining raw findings (COD-4, -9, -10, -12, -13, -14) are in the JSON with repro + fix shape.

## Persona walkthroughs

**Tactical Tornado.** Asked to "remove the kill-switch toolbar, the app is read-only", the
tornado deletes the component and its mount, sees `cargo test` and vitest stay green (nothing
tests that a listener exists, nothing tests `kill_switch_shortcut()` against its own doc
string), writes "dormant, not gone" in three comments (`safety.ts:16-17`, `index.ts:10-12`,
`modules/index.ts:52-54`) and moves on. The same hand wrote `_unused()` (`kill_switch.py:216`)
rather than delete an import, and copied `KNOWN_ACTIONS` into the viewer
(`AuditLogViewer.tsx:40`) rather than derive it. Each is locally harmless; together they are
why a halt can 422 and an audit log can go blank.

**Strategic Thinker.** Would ask one question first: _what is the source of truth for "are we
halted"?_ Answer: the append-only log, because it is the only durable, tamper-evident thing in
the subsystem. Then `KillSwitchBus` shrinks to: append `_meta` row → set flag → notify with a
budget; `reset` appends the inverse and broadcasts; boot reads the last row. Adapters stop
writing the bus's forensic record. On the read side: one `_select(filters)` behind `tail` and
`export_csv`, a tolerant row mapper, and the viewer's option lists derived from data. Net
change is a deletion: `range_`, `_ensure_initialized` call sites, `KNOWN_*`, `_unused`, two
unused TS interfaces.

## Minor observations

- `export_csv` docstring says "Stream" (`audit_log.py:192`); it builds the whole string and the
  route returns `Response(content=body)`. Unbounded, fine at personal-terminal volume.
- `record_session_ack` mutates `_session_acks` before `audit_log.append`
  (`disclaimer_session.py:38-39`): an append failure 500s with the ack already recorded.
  Swap the two lines.
- `reset_bus_for_tests` rebinds the module global (`kill_switch.py:212-213`); safe only because
  every consumer calls `get_bus()`. One `from services.kill_switch import bus` breaks isolation.
- `describeSource` probes `agentName` → `originatorName` → `workflowId`
  (`OrderConfirmationDialog.tsx:48-52`) although the contract names exactly one key
  (`types/safety.ts:213`).
- `services/action_ledger.py` (flagged in the partition) is clean: lock discipline is stated
  and held, TTL-bounded, no findings.

## Questions to consider

- If the app is "read-only, nothing to halt", why does the command palette still offer
  "Open Order Entry" — and which of the two statements is the release telling the user?
- Could `fired` stop being state at all and become a query over the last `_meta` row?
- Should the audit viewer's filters be a server query, given forensics is its only job?

## Run notes

Target: 13 files + 5 integration files, all read fully. Ignore list: none
(`.aposd/critique/ignore.md` absent). Assessment independence: **degraded (sequential)** — no
sub-agent tool in this worker; A recorded before B. Snapshot to `.aposd/critique/`: **skipped**
on purpose (would drop an untracked dir into a repo with a stray-capture push guard; this file
is the archive). No tests run beyond the two proof snippets; no full pytest/cargo.
