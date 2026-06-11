# R9 Track D — Settings rebuild

Branch: `worktree-agent-r9-settings` from 004 HEAD. Partition EXCLUSIVE. Push every
deliverable. **Read `docs/redesign/R9_DESIGN_SYSTEM.md` FIRST** — Linear's settings forms
are your density/proportion reference (`docs/redesign/references/r9/`).

## Files you own

`src/components/SettingsPanel.tsx`, `src/store/settings.ts`, their tests.
Team A owns `src/store/search-settings.ts` — they push the new two-tier store contract to
`worktree-agent-r9-tiers` within their first hour; READ IT FROM ORIGIN and build the
Research surface against it (fetch + read-only reference; do not edit their files; if the
contract is missing something, leave a `R9_TRACK_SETTINGS_REPORT.md` note and stub-type it
locally — the lead reconciles at merge).

## D1 — The Research surface (gates 1, 9; defect V9: the operator could not FIND tier

controls after R8)

One section, radio-clear, two visible tiers, beautiful:

- **Tier A — "Unlimited (Local)"** (default): one card. Radio + two-line explanation
  ("Private local search via SearXNG, paired with your active chat model"). Inside:
  the managed SearXNG flow — status chip (Not set up / Pulling / Starting / Ready /
  Stopped — live from `/search/searxng/status`), ONE primary action button per state
  (Set up → Start/Stop), container health line, Docker-missing state with honest copy.
  When not READY: a quiet line "Until set up, research uses limited keyless search."
- **Tier B — "Hosted research model"**: one card. Radio + explanation ("Purpose-built
  internet-native research via OpenRouter — research routes here at every depth
  regardless of chat model"). Inside: key state (reuses the existing OpenRouter key row
  pattern — keychain, never echoed), then THREE per-stop model rows (Normal / Deep /
  Ultra), each a select of the picker models with **verified pricing hints** rendered as
  micro-text from Team A's pricing constant (e.g. "sonar-deep-research — $2/M in · $8/M
  out · $5/1k searches + reasoning"). Disabled state (no key) shows the key CTA, never
  dead controls.
- No third anything. No SearXNG URL field unless it already works perfectly (it's an
  "Advanced" disclosure if kept; kill if half-wired — log the verdict).

## D2 — Settings proportion rebuild (gate 9: zero clipped/truncated text, default AND

narrow; V4)

Rebuild on the law: section jump-nav chips that never clip/wrap awkwardly (collapse ladder:
full → short → overflow), h-8 (32px, now ACTUALLY 32px) form controls, label/control
columns aligned, 24px group rhythm, selects render full option text (designed short forms
where labels are long — extend the model-name formatter: "DeepSeek V4 Flash", never
"DEEPSEEK-V4-FLA…"), the India region row fits, SET DEFAULT never wraps (short form
"Default" + check state), provider rows on one designed grid. Sweep EVERY section
(AI Providers, Research, Region & locale, Interface, Keybindings, Advanced) at 1280 and
at the panel's minimum width.

## D3 — Appearance knobs: VERDICT = KILL (gate 10; V6)

`accentIntensity` and `density` are dead UI (written, never read — verified). The R9 law
defines ONE designed density per surface; a global density toggle fights reference-grade
proportion, and accent intensity contradicts the scarce-accent doctrine. KILL: remove the
controls, the store fields, the blob fields (deserialize guard: silently drop old values),
their tests. Append to the kill list in `verification/R9_DEFECT_CATALOGUE.md`. If some
OTHER Interface-section control is half-wired, same treatment: works perfectly or dies.

## D4 — Stray-item audit (your partition)

Every Settings control demonstrably round-trips (change → persist → reload → applied).
Anything that doesn't: fix or kill, logged.

## Gates (in-worktree)

vitest green, audit script CLEAN on your files, lint+format+typecheck. Visual self-check:
`pnpm dev -- --port 5175`, headless-Chrome captures of every Settings section at 1280 +
minimum panel width → `docs/redesign/verification/r9/settings/` in your worktree. Write
`docs/redesign/R9_TRACK_SETTINGS_REPORT.md`.
