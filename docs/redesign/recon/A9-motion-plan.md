# Recon — A9:motion-plan

Confirmed: no existing count-up/flash utility — that's the core gap. I have everything. Here is the blueprint.

---

# Track 5 — "App Feels Alive" Motion Layer: Implementation Blueprint

## 1. Findings (file:line precise)

**Motion infra already solid.** Single source of truth exists at `src/lib/motion.ts`: `EASE_INSTRUMENT [0.2,0.8,0.2,1]`, `EASE_DETENT`, `DUR {fast:0.16, base:0.22, slow:0.28}`, `tween()`, `SPRING_PILL`. Mirrors CSS `--ease-instrument`/`--ease-detent` (`styles/tokens.css:100-101`). Global gate is live: `<MotionConfig reducedMotion="user">` at `src/app/page.tsx:160`, plus CSS `@media (prefers-reduced-motion: reduce)` collapsing all anim/transition to ~0 (`src/app/globals.css:121-130`). These durations match Vercel's guideline (routine 160-240ms, entrance 240-360ms) — **no token changes needed**, only one addition (flash + count timings).

**Already animated (don't touch, they're good):** `ResearchActivity.tsx` (step stagger `layout` + scanline + radar spin), `ModeBar.tsx:50` (`layoutId="mode-active-pill"` spring + consequence cross-fade), `ChatSidebar.tsx:718-723` (message stagger `opacity/y:6`), `ProposedChangesReview.tsx:32-39/95-102` (section + card enter/exit), `AgentDock.tsx:88-109` (width-slide with `useReducedMotion` guard at :29/:84), `AgentsRail.tsx:94` (running-run `animate-pulse`).

**The dead surfaces (ranked by signal value):**

1. **WatchlistPanel** (`src/modules/watchlist/WatchlistPanel.tsx:242-303`) — polls every 5s (`:15`), prices change with **zero visual signal**. No prev-value tracking, no flash, no tick. This is the single biggest "feels dead" surface — a Bloomberg/finance terminal MUST flash on tick. `formatPrice`/`formatPercent` at :17-36.
2. **Skeletons are static** — `animate-pulse` only: watchlist `:198-205`, news `:259-265`. No shimmer sweep, no list stagger when data lands.
3. **NewsFeedPanel** (`src/modules/news/NewsFeedPanel.tsx:302-306`) — list renders as a hard pop; no staggered fade-in; `NewsRow` is plain `<li>` (:91-128).
4. **Pending cursor** is a CSS `animate-pulse ▋` (`ChatSidebar.tsx:760`) — fine, leave it.
5. **dockview panel mount** (`PanelHost.tsx:222-224`) — no enter motion (dockview owns DOM; out of cheap reach — **skip**, see Risks).
6. **ResearchActivity elapsed timer** (`ResearchActivity.tsx:60-67`) — `tabular-nums` text swap, no count animation; acceptable, low priority.

No existing `useSpring`/`animate()`/count-up/`usePrevious` anywhere in `src/` (grep clean) — the count-up + flash hook must be **created**.

## 2. Exact change plan

### CREATE `src/lib/motion.ts` additions (append, surgical)

Add flash + count tokens alongside existing exports:

```ts
export const FLASH = { duration: 0.6 } as const; // tick highlight fade-out
export const COUNT = { duration: 0.4 } as const; // number roll
export const STAGGER = 0.035; // per-item list cascade
```

### CREATE `src/lib/use-flash-value.ts` (new file — the load-bearing primitive)

A reduced-motion-aware hook that returns a flash direction + an animated display number. Shape:

```ts
import { useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

export function useTickFlash(value: number | null) {
  const reduce = useReducedMotion();
  const prev = useRef(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  useEffect(() => {
    if (value == null || prev.current == null) {
      prev.current = value;
      return;
    }
    if (value !== prev.current) {
      if (!reduce) {
        setFlash(value > prev.current ? "up" : "down");
        const id = setTimeout(() => setFlash(null), 600);
        prev.current = value;
        return () => clearTimeout(id);
      }
      prev.current = value;
    }
  }, [value, reduce]);
  return flash; // null when reduced-motion or unchanged
}
```

Companion `useCountUp(value)` using framer's `useSpring`/`animate` returning a `MotionValue<number>` rendered via `useTransform(mv, v => formatPrice(v))` into `<motion.span>`; when `reduce`, return a static formatted string (no spring).

### EDIT `src/modules/watchlist/WatchlistPanel.tsx` (rank 1)

- Convert the price/change `<td>` content (:272-286) to use `useTickFlash`. Wrap each row's numeric cell: on `flash==="up"` apply a brief `bg-positive/15` (green) overlay, `"down"` → `bg-negative/15`, fading via `transition-colors duration-[600ms]`. The **text color already encodes sign** (`text-positive`/`text-negative` :280-282) — the flash adds the _change_ signal on top, not redundant.
- Wrap each price number in `useCountUp` `<motion.span>` so the value rolls instead of snapping (0.4s, `EASE_DETENT`).
- A row is a separate component (`WatchlistRow`) so each owns its own `useTickFlash`/`useCountUp` hooks (can't call hooks in `.map`).
- Stagger rows on first data-land: `<motion.tr layout initial={{opacity:0}} animate={{opacity:1}} transition={tween(0.18)}` with `transition.delay = i * STAGGER` (cap at ~6 items).

### EDIT `src/modules/news/NewsFeedPanel.tsx` (rank 3)

- Make `NewsRow` a `motion.li` (:91-128): `initial={{opacity:0, y:4}} animate={{opacity:1, y:0}} transition={{...tween(0.2), delay: Math.min(i,8)*STAGGER}}`. Pass `index` from `:303-305`.
- Skeleton (:255-268): keep `animate-pulse` but add a shimmer sweep — a `motion.div` gradient bar overlay (mirror `ResearchActivity.tsx:186-193` scanline) gated so it self-disables under reduced-motion (framer respects `MotionConfig`).

### EDIT `src/app/globals.css` (shimmer utility, optional consolidation)

Add a `.shimmer` component-layer class (CSS keyframe sweep) so skeletons in watchlist AND news share one source — but it MUST be inside a `@media (prefers-reduced-motion: no-preference)` guard (the existing `:121` block only zeroes duration; a sweep that _moves_ should not run at all under reduce). This is the one CSS edit.

### EDIT `src/modules/watchlist/WatchlistPanel.tsx` skeleton (:194-209)

Swap the static `animate-pulse` divs to use the `.shimmer` class for parity with news.

**Do NOT touch:** `ResearchActivity`, `ModeBar`, `ProposedChangesReview`, `AgentDock`, `AgentsRail` — already correct. **Do NOT** add a dockview panel-mount animation (Risks §3).

## 3. Risks + safe fallback

| Risk                                                                                                                                                                                                                    | Fallback                                                                                                                                                                                                                                                                |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Count-up spring on a 5s-polling number that's also re-rendering** could thrash if value updates mid-spring.                                                                                                           | `useCountUp` reads the latest value via `useSpring` (interruptible by design — Vercel "cancelable by input"); if spring stalls, the `MotionValue` still settles to target. Worst case visual: a slightly faster roll. Safe.                                             |
| **Flash overlay fighting `tabular-nums` / column clip** (`:272` `overflow-hidden text-ellipsis`).                                                                                                                       | Flash is a `bg-*` on the `<td>`, not a transform — no layout shift, no reflow (honors Vercel "animate opacity/transform/color only, never width/height").                                                                                                               |
| **dockview panel-mount motion** — dockview owns panel DOM lifecycle; wrapping in `motion.div` fights its gridview sizing + the `setConstraints` sweep (`PanelHost.tsx:75-108`) and the rAF-throttle gotcha (MEMORY.md). | **Don't animate panel mount.** The watchlist/news in-panel stagger already delivers the "content arrives alive" feeling without touching the host. Documented decision.                                                                                                 |
| **Reduced-motion correctness** — `useReducedMotion` returns `null` on first SSR/static-export render.                                                                                                                   | Hook treats `null`/falsy as "animate" but the global `MotionConfig reducedMotion="user"` (`page.tsx:160`) still neutralizes framer animations; the `useTickFlash` early-returns `null` when `reduce` is truthy, so color flash is also suppressed. Belt-and-suspenders. |
| **Per-row hooks** if list is large.                                                                                                                                                                                     | Watchlist is a curated handful (≤~20). No virtualization concern.                                                                                                                                                                                                       |

**Reduced-motion behavior per item (explicit):** Count-up → static formatted string (no spring). Flash → suppressed (`useTickFlash` returns `null`, no bg overlay) — the **sign color stays** so the signal isn't lost, only the motion. List stagger → framer zeroes delay+duration via `MotionConfig`, items appear instantly. Shimmer → CSS `no-preference` guard means the sweep doesn't run; the `animate-pulse` is already zeroed by `globals.css:125`.

## 4. Verification

**vitest (add to `src/modules/watchlist/WatchlistPanel.test.tsx`):**

- Mock `useReducedMotion → true`; assert no `bg-positive/15`/`bg-negative/15` class appears after a price change; assert the number renders as the final formatted string (not mid-roll).
- Mock `false`; advance a poll with a higher price (mock `fetchWatchlistQuotes` twice via `vi.mock`), `act` the 5s interval (`vi.useFakeTimers`), assert flash class applied then removed after 600ms (`vi.advanceTimersByTime(600)`).
- Run: `pnpm test src/modules/watchlist src/modules/news` (and full `pnpm test` before commit).

**Static/type gates:** `pnpm typecheck && pnpm lint && pnpm format:check` (the `useTransform` formatter return type is the likely TS catch).

**Rig (visual proof — chrome-devtools CAN'T do trusted poll-driven repaint, but the poll is real so screenshot suffices):**

- `mcp__tauri-mcp__start_session` → `screenshot` watchlist with populated `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT` (per CLAUDE.md anchors); wait one 5s poll; second `screenshot` should show at least one row mid-flash. Capture dark theme 1920×1080 + 2560×1440 under `docs/screenshots/v<tag>/`.
- `mcp__tauri-mcp__evaluate_script` to set `matchMedia('(prefers-reduced-motion: reduce)')` mock OR toggle OS reduce-motion, reload, confirm no flash classes via `snapshot`.

**Manual sanity:** `curl http://127.0.0.1:<port>/quotes?...` twice to confirm the price field actually moves between polls (so the flash has real data to react to — empty/static data hides the feature, per the visual-verification rule).

**In short:**

- The infra (tokens + global reduced-motion gate) is already done; the gap is **signal motion on live data**, above all the watchlist tick-flash + count-up, which is the one surface that genuinely reads as "dead."
- Net new code is small: one hook file (`use-flash-value.ts`), three token consts, edits to Watchlist + News rows/skeletons, one CSS shimmer class. No Tier-1 files touched.
- Skip dockview panel-mount motion deliberately — in-panel stagger delivers the feeling without fighting the host.
- Confidence: 8/10 — uncertain only on the count-up spring's feel against a 5s poll cadence (may want `DUR.fast` roll instead of 0.4s); the lead should eyeball it in the rig and tune `COUNT.duration`.
