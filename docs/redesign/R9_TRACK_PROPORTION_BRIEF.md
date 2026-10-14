# R9 Track E — App-wide proportion sweep

Branch: `worktree-agent-r9-proportion` from 004 HEAD. Partition: ALL visual surfaces
EXCEPT `src/modules/chat/**`, `src/modules/research/**` (Team C) and
`SettingsPanel.tsx`/`settings.ts` (Team D). Push per-surface (each surface = one commit =
one recovery checkpoint). **Read `docs/redesign/R9_DESIGN_SYSTEM.md` FIRST — especially
§0: standard Tailwind spacing semantics were just restored (D26); 1,897 call sites were
authored against a HALVED convention and now render doubled. Your job is to re-tune every
surface to the law, not to restore the old look (the old look was the bug).**

## Files you own

`src/modules/{chart,notes,watchlist,portfolio,screener,equity-overview,macro,sec,news,
earnings,analyst-ratings,backtest,node-editor,quant,broker-connect,marketplace,
agent-builder,platform,safety,greeks…}/**` (every module except chat/research),
`src/components/**` except SettingsPanel.tsx (PanelHost.tsx min-sizes, dialogs, banners,
ui/ primitives incl. button.tsx), `src/app/globals.css` (the dockview theme block + chrome
sections — coordinate-free zone: lead owns tokens.css only), `plugins/tradesa-v2/**`
components, tests for all of it.

## E1 — The poster child: chart toolbar (gate 9; V3)

Rebuild the row to reference density (Cursor's toolbar — `references/r9/cursor-full.png`):
symbol input FIXED width `w-[8.5rem]` (fits "SAKSOFT.NS"; tokens-ok: justified arbitrary
— add the comment), Load as a proper h-7 labeled button, timeframe as a compact h-7
segmented control (collapse to dropdown below the measured threshold stays), disclosure
buttons (Draw/Indicators/Compare/Sync) on one h-7 ladder with 14px icons, ONE row at panel
widths ≥360, designed collapse below. Kill the two-row sprawl.

## E2 — Surface sweep (gate 9: reference-verifier pass + zero clipped/truncated text at

default AND narrow)

Per surface, in priority order: Notes toolbar (ONE icon ladder — h-7 buttons, 14px icons,
period; V5), panel headers/chrome, watchlist (column tracks + drop priorities re-verified
at new sizes), portfolio, screener (criteria builder + results table), equity overview,
dockview tabs (`minimumTabWidth` so a tab never renders 2–3 chars beside the overflow
chip — V7), node editor, backtest, quant, macro/sec/news/earnings, tradesa plugin panels,
dialogs/onboarding. For each: land on the law's ladders (h-6/h-7/h-8 controls, 12/14/16px
icons, type roles §2, spacing §1), fix the 274-item audit inventory in your partition
(`node scripts/audit-design-tokens.mjs --report` lists them), keep/declare collapse
ladders where rows can starve.

## E3 — Copy fix

FRED keyless error copy: Settings-language ("Add a FRED key in Settings → AI Providers"
class wording), not `FRED_API_KEY` (V8).

## E4 — Stray-item audit (your partition — the big one)

Three passes of rebuilding left debris. Hunt: controls that do nothing, settings nothing
reads, dead menu entries, orphaned panels, commands registered to missing panel ids
(R7's "screener" drift class), unreachable disclosure popovers. Every item works
perfectly or dies. Append kills to `verification/R9_DEFECT_CATALOGUE.md`.

## Gates (in-worktree)

vitest green (full suite — your sweep touches shared primitives), audit script CLEAN for
your partition, lint+format+typecheck. Visual self-check: `pnpm dev -- --port 5176`,
headless-Chrome captures per surface (populated states where reachable headless; note
which need the live app) at 1280 + narrow → `docs/redesign/verification/r9/proportion/`.
Write `docs/redesign/R9_TRACK_PROPORTION_REPORT.md` with a per-surface checklist.
