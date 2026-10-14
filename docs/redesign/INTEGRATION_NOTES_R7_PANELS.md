# Integration notes — R7 Track P (panels)

Coordination items for the lead from the panels track. Strict-ownership
exceptions are listed here per the track brief.

## Out-of-ownership touches (review on integration)

- `src/store/llm-providers.ts` — one label string: `"OpenRouter (broker)"` →
  `"OpenRouter"`. The brief assigns the label defect to this track but the
  string lives in the store default, not in `SettingsPanel.tsx`.
- `sidecar/config/model_registry.json` + `sidecar/tests/test_llm_router.py` —
  the sidecar registry DID still carry `"label": "OpenRouter (broker)"`, and
  `useLLMProvidersStore.refresh()` (fired on ChatSidebar mount) overwrites the
  fixed store default with the sidecar label verbatim — so with the sidecar up
  the broker label resurfaced at runtime regardless of the frontend fix. Fixed
  at the source in this branch (registry label → `"OpenRouter"`) and pinned in
  `test_get_providers_returns_all` so it cannot regress. The frontend no-broker
  test alone is NOT sufficient (jsdom never reaches the sidecar).
- `docs/redesign/{LESSONS.md, LEAD_INTEGRATION_TODO.md}` — prettier
  formatting only (they failed `pnpm format:check`, which gates every track).
  Zero content changes.

## Shared-component needs (for the lead)

- **ToggleSwitch**: `PluginManagerPanel.tsx` now carries a local copy of the
  SettingsPanel ToggleSwitch (readable 32px switch, sr-only checkbox keeps
  `role="switch"`). Two copies exist by design — shared components are the
  lead's. Lift into `components/ui` when convenient.
- **DataTable expansion rows**: the earnings calendar keeps a hand-rolled
  table only because its drill-down needs an inline expansion row, which
  DataTable does not support. The hand-rolled table matches the DataTable
  rhythm (micro headers, px-3 py-1.5 cells, right-aligned tabular numerics);
  an `expandedRow` API on DataTable would let it fold in.

## For the lead to eyeball live

- **Greeks dashboard**: result layout at narrow widths (the metric grid steps
  2 → 3 → 5 columns at `md`/`xl`); the EmptyState CTA fires a real compute.
- **Settings**: jump-nav chips scroll to sections; provider-row right cluster
  stays column-aligned across all providers (default badge / Set default /
  key button / remove slots); the new switches and starter-cockpit bracket
  chips at both density knob values.
- **Equity overview**: header baseline with a long company name + a wide
  price; ratings metric strip at `md` (4-up with dividers) vs narrow (2-up).

## NEEDS-MANUAL-CHECK

- Settings `scrollIntoView` smooth-scroll inside the dockview panel scroller
  (jsdom cannot exercise it).
- Keychain-backed flows in Settings (Exa key save/remove, provider key
  dialogs) — wiring untouched, but only a live keychain proves them.
