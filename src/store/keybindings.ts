/**
 * Keybindings store — the host-side keymap (FR-031 teaching surface, the
 * foundation FR-039's remappable-keybindings settings build on).
 *
 * The plugin `CommandSpec` contract is Tier-1 LOCKED and has no `keybinding`
 * field, so a command's keyboard mnemonic can't ride the command itself. The
 * mnemonics live here instead — a host-side companion keymap, the same pattern
 * as `PLUGIN_COMPANIONS`: a serializable contract (`CommandSpec`) plus a
 * host-owned side table keyed by a stable id.
 *
 * An action's id is either:
 *  - a synthetic shell action (e.g. `"palette.open"`, `"agent.mode.ask"`,
 *    `"changes.acceptAll"`), or
 *  - a module command's `CommandSpec.id` (e.g. `"platform.save-workspace"`),
 *    so the palette can teach the binding next to that command.
 *
 * Design for FR-039 (do NOT remove without checking the settings panel):
 *  - `defaults` is immutable; user remaps live in a separate `overrides` map so
 *    a reset is just "drop the override", and the workspace blob persists only
 *    the overrides (not the whole keymap).
 *  - `conflicts()` surfaces two actions bound to the same combo so the settings
 *    UI can warn before saving a remap.
 *  - `matchesEvent` / `formatBinding` are pure helpers exported standalone so
 *    callers (the palette, the future settings panel) don't have to read store
 *    state just to render or match a combo.
 *
 * SSR-safe: no `window`/`navigator` access at module load. Platform detection
 * (for `⌘` vs `Ctrl`) is computed lazily inside `formatBinding`, guarded for
 * jsdom/SSR.
 *
 * Binding string grammar: lowercase tokens joined by `+`, modifiers first, the
 * key last — e.g. `"mod+k"`, `"alt+1"`, `"mod+enter"`, `"mod+shift+p"`.
 * `"mod"` is the platform-primary modifier (⌘ on macOS, Ctrl elsewhere).
 */

import { create } from "zustand";

/** Functional grouping for the keybindings settings UI. */
export type KeybindingCategory = "palette" | "agent" | "changes" | "workspace" | "panels" | "tools";

/** A single bindable action's metadata + its default combo. */
export interface KeybindingDef {
  /** Combo string in the binding grammar (e.g. `"mod+k"`). */
  keys: string;
  /** Short human label shown in the settings list and the palette. */
  label: string;
  /** One-line description of what the action does. */
  description: string;
  /** Functional grouping. */
  category: KeybindingCategory;
}

/**
 * Default keymap. The synthetic shell actions are seeded explicitly; per-module
 * command bindings are merged in from `MODULE_COMMAND_BINDINGS` below so the
 * palette can teach a binding for a discovered command id.
 */
const SHELL_DEFAULTS: Record<string, KeybindingDef> = {
  "palette.open": {
    keys: "mod+k",
    label: "Open command palette",
    description: "Open the fuzzy command palette.",
    category: "palette",
  },
  "agent.mode.ask": {
    keys: "alt+1",
    label: "Agent: Ask",
    description: "Switch the agent to read-only Ask mode.",
    category: "agent",
  },
  "agent.mode.edit": {
    keys: "alt+2",
    label: "Agent: Edit panel",
    description: "Switch the agent to Edit mode (surgical change to the focused panel).",
    category: "agent",
  },
  "agent.mode.build": {
    keys: "alt+3",
    label: "Agent: Build",
    description: "Switch the agent to Build mode (compose multiple panels).",
    category: "agent",
  },
  "agent.mode.delegate": {
    keys: "alt+4",
    label: "Agent: Delegate",
    description: "Switch the agent to Delegate mode (autonomous background task).",
    category: "agent",
  },
  "agent.toggle": {
    keys: "mod+b",
    label: "Toggle agent panel",
    description: "Show or fully hide the agent column (hands the full cockpit back).",
    category: "agent",
  },
  "changes.acceptAll": {
    keys: "mod+enter",
    label: "Accept all proposed changes",
    description: "Apply every staged proposed change.",
    category: "changes",
  },
  "changes.rejectAll": {
    keys: "mod+backspace",
    label: "Reject all proposed changes",
    description: "Discard every staged proposed change.",
    category: "changes",
  },
};

/**
 * Per-module command bindings (best-effort mnemonics for first-party module
 * command ids). Keyed by `CommandSpec.id`. These are *defaults the palette
 * teaches* — the actual ⌥1–4 dispatch and the panel-opening dispatch live in
 * their owning components; this table only supplies the mnemonic + lets FR-039
 * remap them. Kept deliberately small (only the high-traffic "open" commands
 * get a digit/letter combo) so we don't invent dozens of unmemorable chords.
 */
const MODULE_COMMAND_BINDINGS: Record<string, KeybindingDef> = {
  "platform.save-workspace": {
    keys: "mod+s",
    label: "Save workspace",
    description: "Save the current workspace layout.",
    category: "workspace",
  },
  "platform.load-workspace": {
    keys: "mod+o",
    label: "Load workspace",
    description: "Load a saved workspace layout.",
    category: "workspace",
  },
  "platform.open-settings": {
    keys: "mod+,",
    label: "Open settings",
    description: "Open the settings panel.",
    category: "panels",
  },
  "chart.open": {
    keys: "mod+1",
    label: "Open chart",
    description: "Open or focus the chart panel.",
    category: "panels",
  },
  "watchlist.open": {
    keys: "mod+2",
    label: "Open watchlist",
    description: "Open or focus the watchlist panel.",
    category: "panels",
  },
  "news.open": {
    keys: "mod+3",
    label: "Open news",
    description: "Open or focus the news panel.",
    category: "panels",
  },
  "portfolio.open": {
    keys: "mod+4",
    label: "Open portfolio",
    description: "Open or focus the portfolio panel.",
    category: "panels",
  },
};

/** The frozen, merged default keymap — synthetic shell actions + module commands. */
export const DEFAULT_KEYBINDINGS: Readonly<Record<string, KeybindingDef>> = Object.freeze({
  ...SHELL_DEFAULTS,
  ...MODULE_COMMAND_BINDINGS,
});

interface KeybindingsState {
  /** Immutable seed keymap. */
  defaults: Readonly<Record<string, KeybindingDef>>;
  /** User remaps, keyed by action id. Only these persist to the workspace blob. */
  overrides: Record<string, string>;
  /** The effective combo for an action (override beats default; `""` if unknown). */
  bindingFor: (actionId: string) => string;
  /** The full def for an action (with the effective `keys`), or `undefined`. */
  defFor: (actionId: string) => KeybindingDef | undefined;
  /** Remap an action to a new combo. */
  setBinding: (actionId: string, keys: string) => void;
  /** Drop an action's override, reverting it to its default. */
  resetBinding: (actionId: string) => void;
  /** Replace the whole overrides map (workspace/settings restore). */
  setOverrides: (map: Record<string, string>) => void;
  /** Action ids whose effective combo collides (≥2 actions share a combo). */
  conflicts: () => { keys: string; actionIds: string[] }[];
}

export const useKeybindingsStore = create<KeybindingsState>((set, get) => ({
  defaults: DEFAULT_KEYBINDINGS,
  overrides: {},
  bindingFor: (actionId) => {
    const { defaults, overrides } = get();
    return overrides[actionId] ?? defaults[actionId]?.keys ?? "";
  },
  defFor: (actionId) => {
    const { defaults, overrides } = get();
    const base = defaults[actionId];
    if (!base) {
      return undefined;
    }
    const override = overrides[actionId];
    return override ? { ...base, keys: override } : base;
  },
  setBinding: (actionId, keys) =>
    set((state) => ({ overrides: { ...state.overrides, [actionId]: normalizeBinding(keys) } })),
  resetBinding: (actionId) =>
    set((state) => {
      if (!(actionId in state.overrides)) {
        return state;
      }
      const next = { ...state.overrides };
      delete next[actionId];
      return { overrides: next };
    }),
  setOverrides: (map) =>
    set(() => {
      // Normalise on the way in so a persisted blob can't seed a combo that
      // `matchesEvent` would never match (e.g. "K+Mod", uppercase, spaces).
      const overrides: Record<string, string> = {};
      for (const [actionId, keys] of Object.entries(map)) {
        if (typeof keys === "string" && keys.trim() !== "") {
          overrides[actionId] = normalizeBinding(keys);
        }
      }
      return { overrides };
    }),
  conflicts: () => {
    const { defaults, overrides } = get();
    const byCombo = new Map<string, string[]>();
    for (const actionId of Object.keys(defaults)) {
      const keys = overrides[actionId] ?? defaults[actionId].keys;
      const list = byCombo.get(keys) ?? [];
      list.push(actionId);
      byCombo.set(keys, list);
    }
    const result: { keys: string; actionIds: string[] }[] = [];
    for (const [keys, actionIds] of byCombo) {
      if (actionIds.length > 1) {
        result.push({ keys, actionIds });
      }
    }
    return result;
  },
}));

/** Test helper: reset overrides to empty (defaults are immutable). */
export function resetKeybindingsStoreForTests(): void {
  useKeybindingsStore.setState({ overrides: {} });
}

// ---------------------------------------------------------------------------
// Pure binding helpers (exported standalone — no store read needed)
// ---------------------------------------------------------------------------

/** Recognised modifier tokens, in canonical display/order priority. */
const MODIFIER_ORDER = ["mod", "ctrl", "alt", "shift", "meta"] as const;
type ModifierToken = (typeof MODIFIER_ORDER)[number];
const MODIFIER_SET = new Set<string>(MODIFIER_ORDER);

/** Parsed combo: the modifier tokens present plus the single non-modifier key. */
interface ParsedBinding {
  modifiers: Set<ModifierToken>;
  key: string;
}

function parseBinding(keys: string): ParsedBinding {
  const tokens = keys
    .toLowerCase()
    .split("+")
    .map((t) => t.trim())
    .filter((t) => t !== "");
  const modifiers = new Set<ModifierToken>();
  let key = "";
  for (const token of tokens) {
    if (MODIFIER_SET.has(token)) {
      modifiers.add(token as ModifierToken);
    } else {
      key = token; // last non-modifier token wins
    }
  }
  return { modifiers, key };
}

/** Canonicalise a combo string (lowercase, modifiers first in fixed order). */
export function normalizeBinding(keys: string): string {
  const { modifiers, key } = parseBinding(keys);
  const orderedMods = MODIFIER_ORDER.filter((m) => modifiers.has(m));
  return [...orderedMods, ...(key ? [key] : [])].join("+");
}

/** True when running on macOS (so `mod`/`meta` render as ⌘). SSR/jsdom-safe. */
function isMacPlatform(): boolean {
  if (typeof navigator === "undefined") {
    return false;
  }
  // `navigator.platform` is deprecated but still the most reliable signal in a
  // Tauri WKWebview; fall back to userAgent for environments that null it out.
  const platform = navigator.platform ?? "";
  const ua = navigator.userAgent ?? "";
  return /mac/i.test(platform) || /mac os x/i.test(ua);
}

/** Human-readable symbol for a key token (e.g. "enter" → "↵"). */
function displayKey(key: string): string {
  switch (key) {
    case "enter":
      return "↵";
    case "backspace":
      return "⌫";
    case "escape":
    case "esc":
      return "Esc";
    case "delete":
      return "⌦";
    case "tab":
      return "⇥";
    case "space":
      return "Space";
    case "arrowup":
      return "↑";
    case "arrowdown":
      return "↓";
    case "arrowleft":
      return "←";
    case "arrowright":
      return "→";
    case "":
      return "";
    default:
      return key.length === 1 ? key.toUpperCase() : key.charAt(0).toUpperCase() + key.slice(1);
  }
}

/**
 * Render a combo for display: `"mod+k"` → `"⌘K"` on macOS, `"Ctrl+K"`
 * elsewhere. `"alt+1"` → `"⌥1"` (mac) / `"Alt+1"`. Pure + SSR-safe.
 */
export function formatBinding(keys: string): string {
  const { modifiers, key } = parseBinding(keys);
  const mac = isMacPlatform();
  const parts: string[] = [];
  // Render in a stable, conventional order.
  if (modifiers.has("ctrl")) {
    parts.push(mac ? "⌃" : "Ctrl");
  }
  if (modifiers.has("alt")) {
    parts.push(mac ? "⌥" : "Alt");
  }
  if (modifiers.has("shift")) {
    parts.push(mac ? "⇧" : "Shift");
  }
  if (modifiers.has("mod") || modifiers.has("meta")) {
    parts.push(mac ? "⌘" : "Ctrl");
  }
  const keyLabel = displayKey(key);
  if (keyLabel) {
    parts.push(keyLabel);
  }
  // On macOS the symbols read as a tight glyph run (⌘K); elsewhere join with +.
  return mac ? parts.join("") : parts.join("+");
}

/** A minimal KeyboardEvent shape — enough to match without DOM lib coupling. */
interface MatchableKeyEvent {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
}

/**
 * True when `event` satisfies the combo `keys`. `"mod"` matches ⌘ on macOS and
 * Ctrl elsewhere; `"meta"` always means ⌘/Win; `"ctrl"` always means Ctrl.
 * The non-modifier key is compared case-insensitively against `event.key`.
 */
export function matchesEvent(keys: string, event: MatchableKeyEvent): boolean {
  const { modifiers, key } = parseBinding(keys);
  if (key === "") {
    return false;
  }

  const mac = isMacPlatform();
  // Required modifier state, derived from the combo.
  const wantMeta = modifiers.has("meta") || (modifiers.has("mod") && mac);
  const wantCtrl = modifiers.has("ctrl") || (modifiers.has("mod") && !mac);
  const wantAlt = modifiers.has("alt");
  const wantShift = modifiers.has("shift");

  if (event.metaKey !== wantMeta) {
    return false;
  }
  if (event.ctrlKey !== wantCtrl) {
    return false;
  }
  if (event.altKey !== wantAlt) {
    return false;
  }
  // Shift is only required if the combo asked for it; a Shift held for an
  // uppercase letter (combos are lowercase) shouldn't break a no-shift combo,
  // so only enforce when explicitly requested.
  if (wantShift && !event.shiftKey) {
    return false;
  }

  return normalizeEventKey(event.key) === key;
}

/** Map a `KeyboardEvent.key` to a binding-grammar key token. */
function normalizeEventKey(eventKey: string): string {
  const k = eventKey.toLowerCase();
  switch (k) {
    case " ":
    case "spacebar":
      return "space";
    case "esc":
      return "escape";
    default:
      return k;
  }
}
