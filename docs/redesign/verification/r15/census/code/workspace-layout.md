# APOSD critique — `workspace-layout` (Workspace & Layout Persistence)

Worker model: `claude-fable-5-1`. Skill `aposd-critique` loaded and followed (two personas, 18
principles, file:line evidence). Assessment independence: **degraded (sequential)** — no
sub-agent tool in this worker; Strategic pass was completed and recorded before the Tornado scan.

Scope (all read in full, 1977 LOC): `src/lib/workspace.ts`, `src/lib/layout-templates.ts`,
`src/config/default-layout.ts`, `src/store/workspace.ts`, `sidecar/services/workspace_store.py`,
`sidecar/routers/workspace.py`; callers read where a claim depended on them (`src/app/page.tsx`,
`src/components/PanelHost.tsx`, `src/modules/platform/WorkspaceDialog.tsx`,
`src/lib/host-actions.ts`, `src/lib/sidecar-client.ts`, the persisted stores, `catalog.py`).

Raw findings: `docs/redesign/verification/r15/census/raw/code-workspace-layout.json` (14).
Proof artefacts: live `curl` against the isolated sidecar `:52152` (finding 2, 12) and a
2-test vitest repro, **passed 2/2**, kept at
`docs/redesign/verification/r15/census/code/evidence/workspace-layout-repro.test.ts.txt`
(findings 3, 4). The temp copy under `src/lib/` was removed.

## Tactical Tornado verdict — risk: HIGH on the persistence half, LOW on the layout half

The blob grew one bug at a time. Almost every `SerializedWorkspace` field's doc cites the
regression that forced it (`workspace.ts:60` BUG-7, `:100` llama3.1 shadowing, `:411` BUG-4,
`:261` BUG-5) and each came with its own copy-pasted trigger (`page.tsx:108-181`, ten near-identical
subscriptions whose comments each re-explain "does not move the dockview layout, so it needs its
own trigger"). The most damning pattern is **information leakage of the persistence protocol**:
what is persisted (`workspace.ts:198-226`), how it is restored (`:272-370`), and when it is
written (three conventions across `page.tsx`, three stores, two components) are three lists kept in
sync by a CLAUDE.md paragraph. Three fields have already fallen out of sync (finding 5), one store
claims wiring that does not exist (finding 6), and a load-bearing comment is false
(`page.tsx:171` "autosaveLayout is debounced" — it is not, `workspace.ts:541-556`).
Red flags found: 11 (info leakage x4, repetition x2, special-general mixture x1, pass-through x2,
nonobvious code x2). `layout-templates.ts` is the opposite: a pure planner + one general `applyPlan`
— a genuinely strategic design with a few tactical barnacles (4 rAF copies, fossil ids).

## Design principles score

| # | Principle | Grade | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | at-risk | Strategic: single-source payload `workspace.ts:176-182`; atomic write `workspace_store.py:72-94`. Tactical: per-bug trigger copies `page.tsx:108-181` | Each new persisted field is a fresh chance to half-persist (already 4 cases) |
| 2 | Deep modules | pass | `applyPlan` `layout-templates.ts:764-835` serves 6 entry points; `save_workspace` hides temp+rename; only wart: `serializeWorkspace` `workspace.ts:234-236` is a 1-line pass-through | — |
| 3 | Information hiding | **violate** | `workspace.ts:22-38` imports 17 stores and encodes each one's restore guard `:272-347`; name rule only in `workspace_store.py:31`, generator only in `workspace.ts:560-565`; reserved-slot hiding left to callers (`SettingsPanel.tsx:1598` yes, `WorkspaceDialog.tsx:172` no) | Research spaces 400 at the real boundary (F2); `__autosave__` shown in Load dialog (F12) |
| 4 | General-purpose modules | at-risk | Four hand-written "research" plans: `layout-templates.ts:196-221`, `:380-392`, `:652-659`, `:732-760` beside one general applier | Variants drift; menu vs agent vs space disagree on what "research" is |
| 5 | Different layer, different abstraction | pass | Router maps domain errors → HTTP (`routers/workspace.py:45-50`), store knows no HTTP. Wart: `LayoutPlanOptions` threaded through 4 functions then `void opts` (`layout-templates.ts:186`, `:272`) | Dead parameter reads as meaningful |
| 6 | Pull complexity downward | **violate** | Trigger + debounce pushed to every caller: `PanelHost.tsx:187-193` (only debounce), `page.tsx:108-181`, `settings.ts:112`, `brief.ts:103`, `SettingsPanel.tsx:493,627` | Undebounced full-blob POST per notes keystroke; restore-time burst (F3) |
| 7 | Better together / apart | **violate** | Global user data and per-workspace layout share one blob `workspace.ts:198-226`; restore applies all of it on a named load `:283-355` | Loading a layout rolls back holdings/notes (F1, critical) |
| 8 | Define errors out of existence | **violate** | Masked at the wrong level: `workspace.ts:546-555` ignores non-2xx and logs nothing; `workspace_store.py:108-112` corrupt → "missing" → overwritten; name error could not exist if the filename were encoded instead of validated `:42-50` | Silent persistent save failure (F7); unrecoverable corruption (F8) |
| 9 | Design it twice | at-risk | Both designs live side by side: sync appliers `layout-templates.ts:701-709`, `:732-760` (with the comment saying why rAF is wrong `:697-698`) and 4 rAF appliers `:310`, `:341`, `:411`, `:620` | Agent reports an arrangement that has not happened (F9) |
| 10 | Comments describe the non-obvious | at-risk | Excellent why-comments (`workspace_store.py:72-79`, `workspace.ts:489-492`, `layout-templates.ts:774-777`) but several are false or stale: `page.tsx:171`, `screener.ts:224`, `workspace_store.py:4-5` + `routers/workspace.py:27-29` ("layout plus enabled map" — now 18 fields), `workspace.ts:238-244` | Readers trust invariants the code does not hold |
| 11 | Comments first | pass | Contract-style docs precede bodies: `planContentAware` shape `layout-templates.ts:506-513`, `restoreLastSessionOrDefault` "never throws" `workspace.ts:482-493` | — |
| 12 | Names | **violate** | `"single-focus"`/`"compare"` mean different layouts per caller (`layout-templates.ts:188-194` vs `:662-669`, `:638-640` "historical fossils"); `autosaveLayout` saves portfolios; `resetToDefaultLayout` wipes drawings (`store/workspace.ts:154-155`) | F10, F11 |
| 13 | Modifying existing code | at-risk | Migrations are documented and self-retiring (`workspace.ts:435-460`, `:174`), but module docs were never updated as the blob grew (`store/workspace.ts:80-84` still narrates Phase 1.A-2) | Onboarding reader gets the 2-field mental model of an 18-field blob |
| 14 | Consistency | **violate** | 3 trigger conventions; 3 absent-field semantics (`workspace.ts:272-276` reset, `:283` keep-if-nonempty, `:341` key-presence); guard on boot path `:512` but not `loadWorkspace :432`; raw `fetch` x6 vs `sidecarGet`; two rail sets (`store/workspace.ts:31` vs `layout-templates.ts:450-456`) | F4, F13, F14 |
| 15 | Code should be obvious | at-risk | `buildWorkspacePayload` mutates the research store while "building" `workspace.ts:194-197`; restore ordering is a numbered comment `:348-370` | A "serialize" call has side effects; order bugs (F3) |
| 16 | Design for the future | at-risk | Speculative: index signature `workspace.ts:154`, dead non-singleton branch `store/workspace.ts:131-140`, unused `opts`. Missing the one hook evidence demands: a blob schema version (three ad-hoc migrations exist; only `modelOverridesV` is versioned) | Next shape change needs another bespoke sniff |
| 17 | Performance as design | pass | Measured: live `__autosave__` = 5.6 KB (brief 3.8 KB); transcripts capped per space. Whole-blob rewrite is fine at this size | The cost is ordering, not bytes (F3) |
| 18 | Increments are abstractions | at-risk | Fields landed feature-by-feature (FR-003, FR-004, FR-037, FR-074, S-19 …) with no "persisted slice" abstraction first | Root cause of #3, #6, #14 |

**Summary: 4 pass, 8 at-risk, 6 violate (4/18 pass).**

## Overall impression

Two subsystems in one partition. The layout planner is well built. The persistence half works on
the happy path and is badly built around it: one blob holds both "this cockpit" and "this user",
its write path has no owner (anyone may call `autosaveLayout` at any time, including mid-restore),
and its failure paths fail silent or fail destructive. Single biggest opportunity: a
`PERSISTED_SLICES` registry inside `workspace.ts` with a scope tag (`workspace` | `global`) — it
collapses findings 1, 3, 5, 6 and 14 into one table and deletes ~120 lines of subscriptions.

## What's working

- **Plan/apply split** (`layout-templates.ts:182`, `:271`, `:514`, `:764`): pure planners are
  exhaustively testable; one applier owns idempotency, move-vs-add and maximize. Low cognitive load.
- **Atomic, race-documented writes** (`workspace_store.py:69-94`): per-writer temp + `os.replace`,
  with the observed corruption written down. Removes a whole class of torn-file unknowns.
- **Boot restore never throws** and re-checks api liveness across awaits (`workspace.ts:494-534`):
  the StrictMode/HMR hazard is handled in the module, not by callers.

## Priority findings (full set + repro in the raw JSON)

1. **[P0] F1 — named-workspace load rolls back global user data (critical).**
   Principle: better together/apart. Symptom: unknown unknowns. `workspace.ts:283-289`, `:322-355`;
   UI promises "panel layout and enabled modules" (`WorkspaceDialog.tsx:82-84`, `:228-230`).
   Fix: tag slices `workspace`/`global`; `loadWorkspace` applies only `workspace` slices.
2. **[P0] F2 — research spaces cannot be saved (high, proven live: HTTP 400).**
   Principle: information hiding (leak across the sidecar boundary). `workspace_store.py:31` vs
   `workspace.ts:560`. Fix: encode names to filenames sidecar-side instead of rejecting; one contract test.
3. **[P1] F3 — autosave ungated + unserialized (high, proven by test).**
   Principle: pull complexity downward. `workspace.ts:541-556`, `PanelHost.tsx:147,164-166`,
   `page.tsx:108-181`. Fix: `restoreSettled` gate + debounce/single-flight inside `autosaveLayout`.
4. **[P1] F4 — layout failure discards all non-layout state (high, proven by test).**
   Principle: define errors out of existence. `workspace.ts:512-515`, `:262-270`. Fix: restore
   non-layout slices first / on every path; guard inside `deserializeWorkspace`; sidecar `.bak`.
5. **[P1] F5 — three fields with no trigger, three trigger conventions (high).**
   Principle: consistency / change amplification. Fix: the slice registry drives one subscription loop.

Remaining (medium/low): F6 saved screens never persisted; F7 autosave failure invisible; F8 corrupt
blob overwritten with no backup; F9 rAF appliers report success before applying; F10 template ids
mean different layouts + drifted tool description; F11 `resetToDefaultLayout` is a factory reset and
arrange's default; F12 reserved slot leaks into the Load dialog; F13 six id tables, no parity test;
F14 emptied watchlist resurrects defaults.

## Persona walkthroughs

**Tactical Tornado.** Asked to persist "saved screens", the Tornado adds `setSavedScreens` to the
store with a comment saying the lead will wire it (`screener.ts:224`) and moves on — exactly what
happened. Asked why a tier change was lost on relaunch, they paste an eleventh subscription under
`page.tsx:155` *and* a `persist()` into the store (`search-settings.ts:348`), so it now double-posts.
Asked to make arrange work from the menu on an occluded window, they write a second, synchronous
applier (`layout-templates.ts:701`) and leave the four rAF ones alone.

**Strategic Thinker.** Would first ask "whose state is this?" and split the blob contract into a
workspace slice list and a global slice list in `workspace.ts`, each entry
`{key, read, restore, subscribe}`. `buildWorkspacePayload`, `deserializeWorkspace(scope)` and one
trigger loop iterate it; `autosaveLayout` becomes the only writer, internally debounced, gated on
`restoreSettled`, and the only place that knows about `response.ok`. On the sidecar the name rule
disappears (encode, don't validate) and save keeps a `.bak`. In `layout-templates.ts` they would
delete the rAF wrappers, derive `PANEL` from `ARRANGEABLE`, and add the 10-line parity test.
Alternative considered: keep one blob but make named saves omit global keys — smaller diff, but old
named blobs on disk still carry them, so the restore-side scope filter is needed either way.

## Minor observations

- `save_workspace` temp name uses `id(workspace)` (`workspace_store.py:85`); a hard kill leaks
  `*.tmp` files that nothing sweeps (they are not listed, so harmless but unbounded).
- Body `name` and `workspace.name` are two truths (`routers/workspace.py:32-33`,
  `workspace.ts:406`); restore trusts the inner one (`:271`).
- macOS case-insensitive FS: saving "swing" silently overwrites "Swing".
- Circular imports `workspace.ts` ⇄ `store/settings.ts` / `brief.ts` / `search-settings.ts`
  (works only because every use is deferred).
- After every relaunch the active name is forced to "default" (`workspace.ts:519`) even if the
  user was in a named workspace, so Save prefills the wrong name.
- Frontend `WorkspaceError` drops the sidecar's helpful `detail` (`workspace.ts:408-410`).
- Three separate constants all equal 1180 (`layout-templates.ts:363`, `:477`, `:723`).

## Questions to consider

- Should "Load workspace" ever touch money-relevant state? If not, why does the blob carry it?
- If `autosaveLayout` were the *only* writer and owned its own scheduling, which of the ten
  `page.tsx` subscriptions would still need to exist?
- Could the workspace name stop being a filename at all (index file + opaque ids), removing name
  validation, case-collision and reserved-prefix rules in one move?

## Run notes

Target slug / `.aposd/critique` snapshot: skipped on purpose (census files are the archive; no
stray repo dir). Ignore list: none present. Independence: degraded (sequential). Temp files: the
repro test was moved out of `src/` into the evidence folder; scratchpad only otherwise.
