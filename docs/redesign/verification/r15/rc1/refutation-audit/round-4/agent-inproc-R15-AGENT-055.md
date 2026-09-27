# R15-AGENT-055 (rc1-verifier:7) — same layout id, different panel set per entry point

Auditor: refutation audit round 4, group agent-inproc. HEAD 35cf5580 (docs-only commits after 33586c21;
`git diff --name-only 01015033 HEAD | grep -v '^docs/'` prints nothing). The fix round (01015033) touched no layout file.

## Verdict: regression_confirmed (id half never fixed), severity lowered medium -> low

## 1. The entry
- repro: "'single-focus': agent path = ONE maximized chart (planLayout) but menu path = chart + watchlist + news; 'compare':
  agent = one maximized chart, menu = chart + equity overview, tool description = 'dual charts side by side'; 'macro-scan'
  description = 'heatmap + chart + screener' ...; 'single-focus' description = 'full-width chart + stats'".
- fix_shape: "Rename plan keys to real roles with fossil ids mapped once, and generate the catalog's per-template panel list
  from planLayout(). Test: for each template id, the agent and menu paths produce the same panel set and the description
  names exactly those panels."
- Certified in batch-8 (68bb7aa4, commit 963991a5): "The menu now speaks modes (fundamental, technical, macro, compare-desk).
  Its historical payload ids are mapped once in MENU_PAYLOAD_TO_MODE." No not_certified row, no earlier audit verdict.

## 2. Entry's own repro at HEAD (scratch vitest over the real modules, no repo file written)
Command (config /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/vt/vitest.config.mts, root = main worktree, cacheDir in scratch):
`PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$PATH node_modules/.bin/vitest run --config /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/vt/vitest.config.mts`
Test /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-agent-inproc/vt/agent055.test.ts computes planLayout(id) (the agent path) and applyLayoutMode(api, MENU_PAYLOAD_TO_MODE[id])
(the menu path: src-tauri/src/lib.rs:464-477 emits `layout:<id>` -> menu-bridge.ts -> dispatchLayoutMenuCommand(id)):
```
single-focus: agent=["chart"] (maximize chart) | menu payload -> mode technical = ["chart","watchlist","news"] | same set: false
research-cockpit: agent=["chart","equity-overview","brief","news"] | menu payload -> mode fundamental = ["chart","equity-overview","brief"] | same set: false
compare: agent=["chart"] (maximize chart) | menu payload -> mode compare-desk = ["chart","equity-overview"] | same set: false
macro-scan: agent=["macro","chart","screener-panel"] | menu payload -> mode macro = ["macro","chart","screener-panel"] | same set: true
```
single-focus and compare reproduce the entry's repro verbatim (the same panel sets the entry was filed on); research-cockpit
also differs (news only on the agent path). Only macro-scan agrees.

## 3. The verifier's refutation re-run
Its own evidence (docs/redesign/verification/r15/rc1/round-4/verifier/own/adv-agent055-ui015.txt) is a code read of the same
tables at 68d5573 (= HEAD's code for these files). Re-read at HEAD: src/lib/layout-templates.ts:189 and :203 (single-focus,
compare maximize the chart), :627-677 MODE_PLANS + MENU_PAYLOAD_TO_MODE, src/store/command-palette.ts:163-189 (palette runs
the same payloads). It holds.
The description half is fixed and I confirm it: sidecar/config/layout_templates.json drives both planLayout and the
arrange_layout description (no dual charts, heatmap or stats).

## 4. Why not verifier_error / not_a_defect
The batch-8 fix renamed only the MENU's internal plan keys; no panel set changed, and the id that enters the menu path is
still the template id (`layout:single-focus`, `layout:compare`). The fix_shape's own test ("for each template id, the agent
and menu paths produce the same panel set") fails for 3 of 4 ids at HEAD, and the certifying test was replaced by one that
asserts the menu modes differ (src/lib/layout-templates.test.ts:545-568). The code comment calling this intended
(layout-templates.ts:607-617) has no operator decision or CHANGELOG trail behind it. So the entry's id half was never fixed.

## 5. Severity: low (was medium)
The user-visible labels differ for two of the three mismatches (menu "Technical Analysis"/"Fundamental Analysis" vs agent
"single-focus"/"research-cockpit"). The one user-visible collision is "Compare": the menu item "Compare" and the palette
"Layout: Compare" give chart + equity overview, while `/layout compare` (ChatSidebar.tsx:699-704, "Switch to a named
workspace layout") and the agent's compare give one maximized chart. No data is wrong; both are chart-centred compare views.

Root cause: src/lib/layout-templates.ts:672-677 (MENU_PAYLOAD_TO_MODE keys are the agent template ids and map single-focus,
research-cockpit and compare to modes with different panel sets), fed by src-tauri/src/lib.rs:464-477 (menu ids are the
template ids; menu label "Compare" = agent "compare").
Fix shape: make the menu path stop claiming the agent template ids: lib.rs emits the mode ids (layout:fundamental,
layout:technical, layout:macro, layout:compare-desk), MENU_PAYLOAD_TO_MODE and LAYOUT_MENU_LABELS are keyed by those, and the
menu/palette "Compare" becomes "Compare Desk", so no id or user-visible name maps to two panel sets. MODE_PLANS and planLayout
stay as they are (the menu's full cockpits are the deliberate Bug-4 behaviour). No lib.rs change is Tier-1 (only
tauri.conf.json is).
Acceptance: src/lib/layout-templates.test.ts "one plan per template id (R15-AGENT-055)": for every id in LAYOUT_TEMPLATE_IDS,
dispatchLayoutMenuCommand(id) either returns false or places exactly planLayout(id)'s panel set; and every
`MenuItem::with_id(h, "layout:<x>"` id in lib.rs is a key of MENU_PAYLOAD_TO_MODE (or "default"). Live re-proof: the scratch
vitest above prints "same set: true" or no menu payload for every id.

Certification-failure count: 1. Register note: no 'certification failures so far' clause (entry has no note). batch-*/VERDICTS.json
not_certified: 0 (batch-8 certified). refutation-audit/REFUTATION_AUDIT.json and round-2/REFUTATION_AUDIT.json: 0
regression_confirmed/partial. Baseline 0 (matches the known baseline) + 1 for this regression_confirmed.
