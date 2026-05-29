# Phase 10 — Settings UI map + root-cause of two live bugs

Scope: map the rebuilt Settings surface (Phase 9.5 / Track C — 4 sections) and
root-cause (1) the double scrollbar that scrolls into a "blue void", and (2) the
"Set default" control that only renders on the Ollama provider row.

All claims are cited to `file:line` against the actual source at HEAD
(`40746bd feat(ux): panel-freedom layouts + discoverable BYOK settings & onboarding (Track C)`).

---

## 1. Settings UI map

### Entry point + mount chain

- Single component: `src/components/SettingsPanel.tsx`.
- Registered by the platform module as the `settings-panel` panel component:
  `src/modules/platform/index.ts:63-65` (`panelComponents: { "settings-panel": SettingsPanel }`),
  panel id `settings` (`index.ts:28-35`), singleton (`singleton: true`),
  `defaultSize: { w: 4, h: 5 }`.
- Opened three ways: toolbar gear (`src/app/page.tsx:107-115`, `openPanel("settings")`),
  the `platform.open-settings` command (`src/modules/platform/index.ts:37-45`),
  and the onboarding banner's "Add your key →" button
  (`src/components/OnboardingBanner.tsx:44-50`, `openPanel("settings")`).
- Renders inside dockview. `PanelHost` mounts `DockviewReact`
  (`src/components/PanelHost.tsx:76-78`); dockview portals the component directly
  into its content-part element whose class is `dv-content-container`
  (verified in `dockview-core@6.2.2/.../components/panel/content.js:36`
  `this._element.className = 'dv-content-container'`; the React part is a bare
  `ReactDOM.createPortal(node, this.parent, …)` with no extra wrapper div —
  `dockview@6.2.2/.../dist/cjs/react.js:138`).

### The four sections (all in `SettingsPanel.tsx`)

Root layout (`SettingsPanel.tsx:39-60`): outer `div.bg-charcoal-900 h-full w-full
overflow-y-auto` → inner `div.mx-auto max-w-2xl flex-col gap-8 p-6` → header +
`<ProvidersSection/> <LayoutsSection/> <ModulesSection/> <AboutSection/>`.

1. **AI Providers (BYOK)** — `ProvidersSection` (`:68-174`). Reads provider list
   - default + setter from `useLLMProvidersStore` (`:69-71`) and per-provider
     keychain status from `useProviderKeysStore` (`:72-74`). `useEffect`
     re-probes the keychain on mount (`:78-80`). Each row shows label, a `default`
     badge when current (`:109-113`), key status (`:115-125`), a "Set default"
     button (`:128-136`), an Add/Update-key button + Remove (`:137-158`).
     `KeyEntryDialog` is the add/update modal (`:164-171`).
2. **Layouts** — `LayoutsSection` (`:180-305`). Lists saved workspaces (reserved
   names filtered, `:191`), save-current-as form (`:227-253`), reset-to-default
   (`:250-252`), per-layout Load/Delete (`:274-295`), autosave-slot note (`:300-302`).
3. **Modules** — `ModulesSection` (`:311-364`). Enable/disable toggle per
   registered module; platform module locked on (`:326`, `:350`, `:351-353`).
4. **About** — `AboutSection` (`:370-390`). Version (`HOST_VERSION`) + positioning copy.

Shared `SectionHeader` helper: `:396-416`.

### Provider registry

`src/store/llm-providers.ts:31-54` — `DEFAULT_PROVIDERS`: seven providers.
Six are `requiresKey: true` (anthropic, openai, gemini, groq, deepseek, xai);
**only `ollama` is `requiresKey: false`** (`:36-41`). Default provider id is
`"anthropic"` (`:74`). `setDefaultProviderId` just sets state (`:75`).

Key-status store `src/store/provider-keys.ts`: `status` is
`Partial<Record<LLMProviderId, KeyStatus>>` where `KeyStatus =
"configured" | "missing" | "unknown"` (`:22`). `probe()` calls
`getSecret(llm-provider:<id>)` and returns `"configured"` only on a non-empty
value, **`"unknown"` when `getSecret` throws** (`:37-44`). `getSecret` is a Tauri
`invoke("keychain_get", …)` (`src/lib/keychain.ts` `getSecret`), which **rejects
outside the Tauri shell**.

---

## 2. BUG #1 — double scrollbar scrolling into a "blue void"

### Root cause

Two nested scroll containers, and the outer one's scroll region is never painted.

DOM/scroll chain when the Settings panel is open:

```
.dv-view                      dockview.css:2641-2645  position:absolute; height:100%; overflow: AUTO   ← SCROLL #1, NO background
  └─ .dv-groupview            dockview.css:2266-2272  display:flex; height:100%; overflow:hidden; bg = --dv-group-view-background-color (charcoal-900)
       └─ .dv-content-container  dockview.css:2275-2279  flex-grow:1; min-height:0; overflow: VISIBLE (never set); NO background
            └─ SettingsPanel root  SettingsPanel.tsx:41   bg-charcoal-900 h-full w-full overflow-y-auto   ← SCROLL #2
                 └─ inner          SettingsPanel.tsx:42   mx-auto max-w-2xl flex-col gap-8 p-6 (natural content height)
```

Two facts combine:

1. **dockview wraps every leaf group in an `overflow:auto` element.** The
   grid is built from split-view containers; each leaf's `.dv-view` has
   `overflow: auto` and `position: absolute`
   (`node_modules/dockview/dist/styles/dockview.css:2641-2645`). That is scroll
   container #1.
2. **`SettingsPanel` puts its own scroll on the `h-full` root**
   (`SettingsPanel.tsx:41`, `h-full w-full overflow-y-auto`). That is scroll
   container #2.

Because the panel root is `h-full` (= 100% of `.dv-content-container`, which is
`overflow: visible`), the content box of the panel can extend to the full leaf
height with no clipping by the content-container. The combination of the inner
`overflow-y-auto` (root) and the ancestor `overflow:auto` (`.dv-view`) gives two
scrollbars on the same axis — the classic "scroll the inner panel, then the
whole leaf scrolls a few more px" double-scrollbar.

**The "blue void":** only `.dv-groupview` and the `SettingsPanel` root paint a
background (both charcoal-900). The **`.dv-view` scroll box (line 2641) and the
`.dv-content-container` (line 2275) paint nothing.** When the `.dv-view`
`overflow:auto` exposes any over-scroll / extra region beyond the charcoal-painted
`SettingsPanel` box, the unpainted area falls through to the WKWebView default
backdrop. The Tauri window sets `theme: "Dark"` but **no `backgroundColor`**
(`src-tauri/tauri.conf.json` window block has no `backgroundColor` key), and the
app paints `--color-background` only on `html, body`
(`src/app/globals.css:53-56`) — which is occluded by the dockview leaf. With no
background on `.dv-view`, the macOS WKWebView default surface (blue/grey) shows
through. That is the "blue void."

This is consistent with the codebase's own canonical pattern: every data panel
roots as `bg-charcoal-900 flex h-full w-full flex-col` and scrolls an **inner**
body (`PortfolioPanel.tsx:165`, `WatchlistPanel.tsx:126`,
`EquityOverviewPanel.tsx:204`, `EarningsCalendarPanel.tsx:137`,
`AnalystRatingsPanel.tsx:70`, etc.). `SettingsPanel.tsx:41` and
`PluginManagerPanel.tsx:31` are the **two outliers** that put `overflow-y-auto`
directly on the `h-full` root — and they are the two with the nested-scroll/void
exposure. (`PluginManagerPanel` has the same latent bug; not in scope but worth a
follow-up.)

### Minimal fix

Match the canonical pattern: make the root a non-scrolling, background-painting,
overflow-clipping flex column and move the scroll to an inner wrapper with
`min-h-0`. This (a) clips at the charcoal box so nothing falls through to the
`.dv-view` backdrop = kills the void; (b) leaves exactly one scroll container.

`src/components/SettingsPanel.tsx:40-58` — change:

```tsx
// before
<div className="bg-charcoal-900 h-full w-full overflow-y-auto">
  <div className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
    …
  </div>
</div>

// after
<div className="bg-charcoal-900 flex h-full w-full flex-col overflow-hidden">
  <div className="min-h-0 flex-1 overflow-y-auto">
    <div className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
      …
    </div>
  </div>
</div>
```

Why this is the minimal, correct fix:

- `overflow-hidden` on the root clips at the painted charcoal box → no unpainted
  region of `.dv-view` is ever scrollable into = **no blue void**.
- The single inner `overflow-y-auto` (with `min-h-0 flex-1`) is the only scroll
  container in the chain (the `.dv-view` ancestor never overflows because the
  root is clipped to its box) = **one scrollbar**.
- It does NOT touch the locked dockview CSS or `types/plugin.ts`; pure JSX/Tailwind.

Alternative (one-liner, less robust): add `overflow-hidden` to the root and keep
`overflow-y-auto` on it — but Tailwind's `overflow-y-auto` + `overflow-hidden`
on the same element conflict; the two-element form is the clean fix and matches
every other panel. A global belt-and-suspenders option is to paint `.dv-view`
in the Vysted theme (`globals.css`, e.g.
`.dockview-theme-vysted .dv-view { background-color: var(--color-charcoal-900); }`)
so any future panel's over-scroll never shows the WKWebView default — recommended
in addition, since `PluginManagerPanel` shares the latent bug.

---

## 3. BUG #2 — "Set default" only renders on the Ollama row

### Root cause — exact gating condition

`src/components/SettingsPanel.tsx:128`:

```tsx
{(configured || !needsKey) && !isDefault && (
  <button … onClick={() => setDefaultProviderId(provider.id)}>Set default</button>
)}
```

where (`:96-100`):

```tsx
const keyState = status[provider.id] ?? "missing";
const configured = keyState === "configured";
const isDefault = defaultProviderId === provider.id;
const needsKey = provider.requiresKey;
```

The button renders only when `(configured || !needsKey)`:

- **Ollama** — `requiresKey: false` (`llm-providers.ts:39`) → `needsKey === false`
  → `!needsKey === true` → button renders unconditionally (as long as Ollama is
  not already the default). This is the one row where the condition is satisfied
  without a key.
- **The six key-requiring providers** (anthropic, openai, gemini, groq, deepseek,
  xai) — `needsKey === true`, so the button needs `configured === true`, i.e.
  `status[id] === "configured"` (`:97-98`). On a fresh install with no keys
  saved, every one of these is `"missing"`; outside the Tauri shell (`getSecret`
  rejects → `probe` returns `"unknown"`, `provider-keys.ts:41-43`) they are
  `"unknown"`. In neither case is `configured` true.

Result: with no keys configured, **the only provider for which
`(configured || !needsKey)` is true is Ollama** → "Set default" renders only on
the Ollama row. The control to pick a default is gated behind first adding a key,
which is exactly the reported symptom.

This is a logic bug, not a styling bug: the `default`-badge path (`:109-113`)
and the button path (`:128`) use different predicates, so the user can never set,
say, Anthropic as default until they've saved an Anthropic key — even though
`setDefaultProviderId` (`llm-providers.ts:75`) has no such precondition and the
default is initialized to `"anthropic"` anyway (`llm-providers.ts:74`).

### Minimal fix

Decouple "can be made the default" from "has a key configured". The default
picker should be available on every provider that is not already the default.
`src/components/SettingsPanel.tsx:128`:

```tsx
// before
{(configured || !needsKey) && !isDefault && (

// after
{!isDefault && (
```

The `(configured || !needsKey)` clause is the bug — drop it. Choosing a default
provider is a free action (the chat sidebar still won't be able to _use_ a
key-less provider, but that is surfaced by the existing "No key yet" status at
`:122-124`, and the onboarding banner already nudges the user to add a key).

If the product intent is "only let a _usable_ provider be the default," the fix
is the opposite of what shipped — it should gate on `configured || !needsKey`
**but that is what's there**, so the shipped behavior already matches that
stricter reading; the user-reported expectation ("Set default shows on every
row") means the intended design is the looser `!isDefault` gate. Recommend
`!isDefault` (looser) so all six BYOK providers expose the picker; this also
makes the control discoverable before a key exists, matching the "discoverable
control surface" intent of Track C documented in the component header
(`SettingsPanel.tsx:24-37`).

---

## 4. Summary of precise fixes

| Bug                          | File:line                                        | Change                                                                                                                                                                       |
| ---------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Double scrollbar + blue void | `src/components/SettingsPanel.tsx:41` (root div) | Root → `bg-charcoal-900 flex h-full w-full flex-col overflow-hidden`; wrap children in inner `min-h-0 flex-1 overflow-y-auto`. Optionally paint `.dv-view` in `globals.css`. |
| "Set default" Ollama-only    | `src/components/SettingsPanel.tsx:128`           | `{(configured \|\| !needsKey) && !isDefault && (` → `{!isDefault && (`                                                                                                       |

Latent follow-up (out of scope): `src/components/PluginManagerPanel.tsx:31`
shares the identical single-element `h-full … overflow-y-auto` root and would
exhibit the same double-scroll/void; apply the same two-element fix.

No locked file is touched (`types/plugin.ts`, §6.5 safety files, dockview CSS all
untouched). Both fixes are pure frontend JSX/Tailwind.
