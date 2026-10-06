# New lows draft — P1 adjudication

Census-clerk draft, sourced at HEAD `284e5ead` on `004-r4-experience-rebuild`. The register (`docs/redesign/verification/vysted-r15-register.json`) is untouched by this draft; everything here is for the lead to review and file at the lows P1 adjudication. Machine-readable form: `NEW_LOWS_DRAFT.json`.

## New entries

### R15-DOCS-025

**Title:** SAFETY_ARCHITECTURE.md §2 says AUTO autonomy has no exempt kind now that `order` is gone; two ProposedChangeKinds (data-write, settings) never auto-apply, which is the exact behaviour R15-AGENT-080/R15-CODE-FRONTEND-008 were fixed to guarantee

- **Severity:** low &nbsp;|&nbsp; **Area:** docs &nbsp;|&nbsp; **Subsystem:** host-actions-proposed-changes &nbsp;|&nbsp; **Tier-4:** False &nbsp;|&nbsp; **Status:** open
- **Files:** docs/SAFETY_ARCHITECTURE.md, types/proposed-change.ts, src/store/proposed-changes.ts
- **Repro:** Read docs/SAFETY_ARCHITECTURE.md:42-44 ('Under AUTO autonomy, every kind auto-applies on enqueue — there is no exempt kind, because the one kind that used to be exempt (`order`) no longer exists.') against types/proposed-change.ts:19-27,38-45 (five PROPOSED_CHANGE_KINDS; AUTO_APPLIED_KINDS = ["panel", "chart", "watchlist"], excluding data-write and settings) and src/store/proposed-changes.ts:121-127 (enqueue: `if (autoApplies(change.kind)) { ... } else { ackHostAction(toolCallId, "staged", ...) }` — any other kind stays pending). docs/redesign/verification/r15/stage-d/FACTS.md:179 states the real behaviour: 'a portfolio change (always held for your review, never applied; under AUTO a watchlist or chart change does apply)'.
- **Evidence:** docs/SAFETY_ARCHITECTURE.md:42-44; types/proposed-change.ts:19-27,38-45; src/store/proposed-changes.ts:121-127; sidecar/services/agent_runtime.py:1591-1592 ('AUTO does not skip review for this kind; it waits in the user's review queue').
- **Root cause:** R15-AGENT-080/R15-CODE-FRONTEND-008 (closed c81d879, Stage C batch 3) added AUTO_APPLIED_KINDS to stop data-write/settings from auto-applying under AUTO; SAFETY_ARCHITECTURE.md §2 documents the pre-fix world (only `order` was ever exempt) and was never updated for the two-kind exemption the fix introduced.
- **Fix shape:** Rewrite §2's last two sentences to name the actual AUTO_APPLIED_KINDS set (panel, chart, watchlist) and state that data-write and settings always wait for review under either autonomy setting, matching FACTS.md's wording. No test needed (doc-only).
- **Defect class:** stale-doc
- **Raw ids:** FACTS.md Known-limitations block, stage-d/FACTS.md:179
- **Operator areas:** agent-chat
- **Source:** lead-found stage-c-lows-p1
- **Note:** Census-clerk draft for the P1 lows adjudication (sourced at 284e5ead); not yet reviewed by the lead.

### R15-CODE-PLATFORM-078

**Title:** The shipped (main) sidecar's PyInstaller build venv installs sidecar/requirements-dev.txt, not requirements.txt, so pyinstaller/ruff/pytest/pytest-asyncio ride in the same venv PyInstaller freezes the release binary from

- **Severity:** low &nbsp;|&nbsp; **Area:** code &nbsp;|&nbsp; **Subsystem:** scripts-build &nbsp;|&nbsp; **Tier-4:** False &nbsp;|&nbsp; **Status:** open
- **Files:** scripts/sidecar-specs.mjs, sidecar/requirements-dev.txt, sidecar/requirements.txt
- **Repro:** grep -n 'requirements:' scripts/sidecar-specs.mjs -> line 86 (name: 'vysted-sidecar', kind: 'main') reads `requirements: "requirements-dev.txt"`, while the two MCP specs at lines 110 and 151 read `requirements: "requirements.txt"`. src-tauri/tauri.conf.json:40-44 `bundle.externalBin` ships exactly this 'vysted-sidecar' binary. `cat sidecar/requirements-dev.txt` = `-r requirements.txt` plus `pyinstaller==6.20.0`, `ruff==0.15.12`, `pytest==9.0.3`, `pytest-asyncio==1.3.0`, `httpx==0.28.1` (httpx is already pinned in requirements.txt).
- **Evidence:** scripts/sidecar-specs.mjs:86,110,151; sidecar/requirements-dev.txt:1-5; src-tauri/tauri.conf.json:40-44.
- **Root cause:** The 'main' SIDECAR_SPECS row was never split from its dev/test venv the way the two MCP-subprocess rows were; no test pins which requirements file each kind must build from.
- **Fix shape:** Point the 'main' spec at requirements.txt; install build-only tooling (pyinstaller) outside the frozen venv or via a separate build-only requirements file. sidecar-specs.test.mjs already pins the PyInstaller command byte-for-byte (R15-CODE-PLATFORM-026) — extend it to assert requirements.txt (not -dev) for kind:'main'.
- **Defect class:** build-hygiene
- **Raw ids:** REHEARSAL.md Findings for the register #6, docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:120-123
- **Operator areas:** release
- **Source:** lead-found stage-c-lows-p1
- **Note:** Census-clerk draft for the P1 lows adjudication (sourced at 284e5ead); not yet reviewed by the lead. REHEARSAL.md's own severity call already bounds impact: 'PyInstaller bundles only imported modules and the binary is 87.4 MB, but test tooling sits in the build env.'

### R15-CODE-FRONTEND-038

**Title:** export-artifact.ts's dynamic import of sidecar-client is ineffective (Vite: [INEFFECTIVE_DYNAMIC_IMPORT]) because 40 other modules import it statically, so the production build ships one 2.93 MB main index-*.js chunk

- **Severity:** low &nbsp;|&nbsp; **Area:** code &nbsp;|&nbsp; **Subsystem:** scripts-build &nbsp;|&nbsp; **Tier-4:** False &nbsp;|&nbsp; **Status:** open
- **Files:** src/lib/export-artifact.ts, src/lib/sidecar-client.ts
- **Repro:** src/lib/export-artifact.ts:51 -> `const { getSidecarBaseUrl } = await import("@/lib/sidecar-client");` is the only dynamic import of that module. `git grep -c 'from "@/lib/sidecar-client"' -- src | grep -v test` sums to 40 static import sites (e.g. src/components/StatusChrome.tsx:6, src/modules/chart/ChartPanel.tsx:46, src/store/app.ts:3), so Vite/Rollup cannot split sidecar-client into its own chunk and the dynamic import buys nothing. docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:124-127 records the build's own warning and the resulting size: `pnpm tauri build` prints `index-*.js 2,933.93 kB` and `[INEFFECTIVE_DYNAMIC_IMPORT] src/lib/sidecar-client.ts`.
- **Evidence:** src/lib/export-artifact.ts:51; docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:124-127; 40 static-import call sites incl. src/components/StatusChrome.tsx:6, src/modules/chart/ChartPanel.tsx:46, src/store/app.ts:3.
- **Root cause:** sidecar-client's exports are used pervasively (nearly every panel/store reaches the sidecar), so lazy-loading it from one call site (export-artifact.ts, itself already lazy for html-to-image/jspdf per its own header comment) cannot remove it from the eagerly-loaded graph; there is no route-level code-splitting in this single-page Tauri shell to begin with.
- **Fix shape:** Import getSidecarBaseUrl statically in export-artifact.ts (it costs nothing extra given the module is already eagerly bundled everywhere else) to silence the Vite warning; treat the 2.93 MB chunk size itself as a separate, larger panel-level code-splitting effort, out of scope for this fix. Test: `pnpm tauri build` log has zero [INEFFECTIVE_DYNAMIC_IMPORT] lines.
- **Defect class:** ineffective-code-split
- **Raw ids:** REHEARSAL.md Findings for the register #7, docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:124-127
- **Operator areas:** release
- **Source:** lead-found stage-c-lows-p1
- **Note:** Census-clerk draft for the P1 lows adjudication (sourced at 284e5ead); not yet reviewed by the lead.

### R15-DOCS-026

**Title:** CLAUDE.md's Visual-verification capture-path pointer is stale: /tmp/rigcap.py does not exist and its CGWindow owner-name match string is the wrong string

- **Severity:** low &nbsp;|&nbsp; **Area:** docs &nbsp;|&nbsp; **Subsystem:** release/build &nbsp;|&nbsp; **Tier-4:** True &nbsp;|&nbsp; **Status:** open
- **Files:** CLAUDE.md
- **Repro:** grep -n rigcap CLAUDE.md -> line 325 (current working tree at 284e5ead): 'Quartz path (`/tmp/rigcap.py`, matched on `kCGWindowOwnerName == "vysted-terminal"`) instead'. docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:70-71 records the observed facts from a real release-bundle launch: 'The System Events process name of the release bundle is `vysted-terminal`, but its CGWindow owner name is `Vysted Terminal`' and '`/tmp/rigcap.py` does not exist on this machine.' REHEARSAL.md's own Findings-for-the-register #4 (lines 112-115) files the same two facts against `CLAUDE.md:316`; the line has since drifted to 325 from unrelated Gotchas insertions added above it since the rehearsal's sha.
- **Evidence:** CLAUDE.md:325 (current); docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:70-71,112-115.
- **Root cause:** CLAUDE.md's capture-path note assumed the CGWindow owner name equals the process name (both lowercase-hyphenated); a real release-bundle launch shows the owner name Quartz actually reports is the display name 'Vysted Terminal', and the /tmp/rigcap.py helper it points at was never checked into the repo or otherwise provisioned on a clean machine.
- **Fix shape:** Update the match string to `kCGWindowOwnerName == "Vysted Terminal"` (or match by owner PID via the System Events process name `vysted-terminal` instead, per REHEARSAL.md's working alternative: `screencapture -l <windowid>` with the window id found by owner PID), and either commit /tmp/rigcap.py's real source under scripts/rig/ or drop the dead pointer. No test (doc-only).
- **Defect class:** stale-doc
- **Raw ids:** REHEARSAL.md Findings for the register #4, docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:112-115
- **Operator areas:** (none)
- **Source:** lead-found stage-c-lows-p1
- **Note:** Census-clerk draft for the P1 lows adjudication (sourced at 284e5ead); not yet reviewed by the lead. Tier-1 locked file (CLAUDE.md): per the repo's decision-authority tiers this is Tier-4 (reversing/correcting a Tier-1 file) — the fix must ride the operator's single pre-authorised CLAUDE.md commit, or be deferred to the next one. This entry is a recommendation only; do not apply unilaterally.

### R15-CODE-PLATFORM-079

**Title:** .gitignore has no coverage/ pattern although @vitest/coverage-v8 is installed, so a local `vitest run --coverage` output directory is not excluded from git

- **Severity:** low &nbsp;|&nbsp; **Area:** code &nbsp;|&nbsp; **Subsystem:** scripts-build &nbsp;|&nbsp; **Tier-4:** False &nbsp;|&nbsp; **Status:** open
- **Files:** .gitignore, package.json
- **Repro:** grep -c coverage .gitignore -> 0 (no match anywhere in the file, including the 'Build output' block that already ignores .next/, out/, dist/); grep -n '@vitest/coverage-v8' package.json -> line 70 (devDependency ^4.1.6; the v8 provider's default reportsDirectory is ./coverage, unconfigured in vitest.config.ts); git ls-files coverage | head -> empty (nothing tracked yet, so this is a gap, not a live leak).
- **Evidence:** .gitignore:1-56 (full file, no coverage line); package.json:70.
- **Root cause:** coverage/ was never added to .gitignore when @vitest/coverage-v8 was installed; no test or CI job runs --coverage yet (R15-RELEASE-011, open), so the gap has not produced a tracked-file incident.
- **Fix shape:** Add `coverage/` under the existing 'Build output' block in .gitignore, beside dist/out/.next. Config-only; no test needed.
- **Defect class:** missing-gitignore-entry
- **Raw ids:** census-clerk verification pass, candidate 8 (see caveat in note)
- **Operator areas:** (none)
- **Source:** lead-found stage-c-lows-p1
- **Note:** Census-clerk draft for the P1 lows adjudication (sourced at 284e5ead); not yet reviewed by the lead. Flag for the lead: the task brief for this draft said 'one register entry mentions coverage/', but a case-insensitive scan of every entry's title/repro/evidence/files/note for 'coverage' (20 hits, none about this .gitignore gap) and for 'gitignore' (0 hits) found no such entry — it could not be located, so this is drafted as a fresh finding rather than a duplicate-check. Verify before filing.

### R15-CODE-PLATFORM-080

**Title:** resolve_data_dir has no env-var/CLI override for the app-data directory, so a release rehearsal's only isolation option is a full $HOME override — which leaks WKWebView data into the real ~/Library/WebKit and ~/Library/Caches

- **Severity:** low &nbsp;|&nbsp; **Area:** code &nbsp;|&nbsp; **Subsystem:** scripts-build &nbsp;|&nbsp; **Tier-4:** False &nbsp;|&nbsp; **Status:** open
- **Files:** src-tauri/src/lib.rs
- **Repro:** Read src-tauri/src/lib.rs:186-203 (`resolve_data_dir`): always calls `app.path().app_data_dir()`, falling back only to a temp dir on error — no env var or CLI arg is read. `grep -n 'VYSTED_DATA_DIR' src-tauri/src/lib.rs` finds no hits. lib.rs:277 passes that resolved path to the sidecar as `--data-dir`. docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:58 records the consequence directly: '§7 names no mechanism for a fresh app-data directory. There is no env var for it. ... So I used a HOME= override and exec'd the bundle's binary directly.' REHEARSAL.md's Findings-for-the-register #3 (WKWebView leak into the real user Library) is the measured cost of that workaround.
- **Evidence:** src-tauri/src/lib.rs:186-203,277; docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:58,92.
- **Root cause:** resolve_data_dir hardcodes Tauri's platform default with no override seam, so the only way to get an isolated data dir for a rehearsal or a second profile is to hijack $HOME wholesale, and WKWebView does not honour that override.
- **Fix shape:** Read an optional VYSTED_DATA_DIR env var (or a --data-dir launch arg) before falling back to app_data_dir(); the plumbing to the sidecar already exists (lib.rs:277). Test: a Rust unit test asserting the env var wins over the platform default when set.
- **Defect class:** missing-override-seam
- **Raw ids:** REHEARSAL.md Isolation mechanism + Runbook correction #4, docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:58,92
- **Operator areas:** (none)
- **Source:** lead-found stage-c-lows-p1
- **Note:** Census-clerk draft for the P1 lows adjudication (sourced at 284e5ead); not yet reviewed by the lead.

## Note objects (append to an existing entry, not a new entry)

### Append to R15-DOCS-006

Census-clerk pass at 284e5ead: the PanelHost.tsx SSR/static-export comment this entry cites has drifted — at HEAD it is a single occurrence at src/components/PanelHost.tsx:207-208 (`grep -n 'static-export\|SSR-safe\|prerender' src/components/PanelHost.tsx` finds only line 208), not :118-119,149 as filed. The same false Next.js-static-export invariant also exists outside this entry's file list, in src/lib/marketplace.ts:8-9 ('Static-import note: Next.js static export can't dynamically import arbitrary plugin code') — the repo has been Vite-only since commit 8c2f9ab9 ('feat(shell): migrate Next.js -> Vite 8 + React 19 (WS1)'), so this comment's premise is equally false. Recommend folding src/lib/marketplace.ts:8-9 into this entry's files/evidence and updating the PanelHost.tsx pointer to :207-208 the next time this is worked.

### Append to R15-UI-044

Second trigger, corroborating docs/redesign/DECISIONS_FOR_OPERATOR.md §2.21 (lines 266-268): a `HOME=`-isolated release-bundle launch has no default keychain (errSecNoDefaultKeychain, -25307), so `refreshFirstLaunchAck()` never resolves and the first-launch TOS dialog never renders there either — same DisclaimerFlow hydrate-effect-has-no-catch root cause, not a new defect. Source: docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:79 ('This is the R15-UI-044 failure mode, triggered here by the isolation method rather than by a Deny click.') and REHEARSAL.md's own Findings-for-the-register #1 (lines 100-103), which independently confirms §2.21's 'Second trigger' bullet. §2.21 already states: 'Same fix, not a new entry.'

## Dropped

Candidates from the brief that were checked against HEAD and did not survive as new entries or notes.

- **Candidate 7 (@tiptap/extension-list):** No defect at HEAD. package.json:31 pins @tiptap/extension-list@3.25.0; src/modules/notes/NotesPanel.tsx:33 imports {TaskList, TaskItem} from it and wires both into the editor's extensions array (lines 129-130, TaskItem.configure({nested: true})). This is exactly R15-UI-024's fix (closure_evidence f407107, status fixed) landing correctly — not a new issue and not a duplicate needing a note, simply nothing to report.

