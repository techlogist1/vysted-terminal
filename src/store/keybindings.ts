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
  /**
   * When true, the app-level dispatcher (`page.tsx`) fires this action even
   * while a text input/textarea/contentEditable is focused. Defaults to
   * false (the dispatcher skips text inputs) — set only for actions that must
   * stay reachable while typing (e.g. opening the palette, toggling the agent
   * dock), matching their pre-dispatcher behaviour.
   */
  global?: boolean;
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
    global: true,
  },
  // The collapsed two-mode surface (R9): Agent infers read/edit intent from
  // the prompt; Delegate runs durably. The legacy four-mode rows (Ask/Edit/
  // Build on alt+1-4) described bindings the shipped handler no longer has.
  "agent.mode.agent": {
    keys: "alt+1",
    label: "Agent mode",
    description: "Interactive agent for this cockpit.",
    category: "agent",
    global: true,
  },
  "agent.mode.delegate": {
    keys: "alt+2",
    label: "Delegate mode",
    description: "Budget-capped autonomous run.",
    category: "agent",
    global: true,
  },
  "agent.toggle": {
    keys: "mod+b",
    label: "Toggle agent panel",
    description: "Show or fully hide the agent column.",
    category: "agent",
    global: true,
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
    set((state) => {
      // Merge over the CURRENT overrides (never a full replace) and reject
      // any action id this build doesn't know about — otherwise a partial or
      // garbled import (an unknown action id, a non-string value) wipes every
      // remap the full replace used to silently drop (R15-UI-058). Normalise
      // on the way in so a persisted blob can't seed a combo that
      // `matchesEvent` would never match (e.g. "K+Mod", uppercase, spaces).
      const overrides = { ...state.overrides };
      for (const [actionId, keys] of Object.entries(map)) {
        if (!(actionId in state.defaults)) {
          continue;
        }
        if (typeof keys === "string" && keys.trim() !== "") {
          overrides[actionId] = normalizeBinding(keys);
        }
      }
      return { overrides };
    }),
  conflicts: () => {
    const { defaults, overrides } = get();
    // Group by the RESOLVED physical chord (R15-UI-027 residual), not the raw
    // string: "mod+p" and "meta+p" are the same key on macOS and must
    // conflict there, while "shift+mod+p" and "mod+p" are genuinely distinct
    // chords and must not.
    const byChord = new Map<string, { keys: string; actionIds: string[] }>();
    for (const actionId of Object.keys(defaults)) {
      const keys = overrides[actionId] ?? defaults[actionId].keys;
      const chord = resolveChord(keys);
      const entry = byChord.get(chord) ?? { keys, actionIds: [] };
      entry.actionIds.push(actionId);
      byChord.set(chord, entry);
    }
    const result: { keys: string; actionIds: string[] }[] = [];
    for (const entry of byChord.values()) {
      if (entry.actionIds.length > 1) {
        result.push(entry);
      }
    }
    return result;
  },
}));

/** Test helper: reset overrides to empty (defaults are immutable). */
export function resetKeybindingsStoreForTests(): void {
  useKeybindingsStore.setState({ overrides: {} });
  actionHandlers.clear();
}

// ---------------------------------------------------------------------------
// Action registry — the single keydown dispatcher's handler table
// ---------------------------------------------------------------------------
//
// Owning components/stores register a handler for a shell action id
// (`palette.open`, `agent.mode.*`, `agent.toggle`, `changes.*`); the one
// `window` keydown listener (`page.tsx`) resolves the effective binding via
// `bindingFor` + `matchesEvent` and calls the registered handler. A module
// command id (e.g. `chart.open`) has no registered handler here — the
// dispatcher runs it through the module command registry instead. Plain
// module state (not Zustand) because handlers are closures, not data the UI
// re-renders on.

type ActionHandler = () => void;

const actionHandlers = new Map<string, ActionHandler>();

/**
 * Register the handler a keybinding action id dispatches to. Returns an
 * unregister function — call it from the owning effect's cleanup so a
 * stale closure (an old `pendingChangeCount`, say) never lingers after the
 * component re-renders with a fresh handler.
 */
export function registerAction(actionId: string, handler: ActionHandler): () => void {
  actionHandlers.set(actionId, handler);
  return () => {
    if (actionHandlers.get(actionId) === handler) {
      actionHandlers.delete(actionId);
    }
  };
}

/** Look up a registered shell-action handler (undefined if none registered). */
export function getRegisteredAction(actionId: string): ActionHandler | undefined {
  return actionHandlers.get(actionId);
}

/**
 * Resolve which `DEFAULT_KEYBINDINGS` action, if any, a keydown event should
 * fire: the first id whose EFFECTIVE (remap-aware) binding matches the event,
 * skipping a non-`global` action while `typing` is true. The single source of
 * truth for "does this keystroke mean this action" — the app-level dispatcher
 * (`page.tsx`) calls it, then runs either the id's registered shell-action
 * handler or its module command.
 */
export function resolveKeyboardAction(
  event: MatchableKeyEvent,
  typing: boolean,
): { actionId: string; def: KeybindingDef } | undefined {
  const { bindingFor } = useKeybindingsStore.getState();
  for (const actionId of Object.keys(DEFAULT_KEYBINDINGS)) {
    const def = DEFAULT_KEYBINDINGS[actionId];
    if (typing && !def.global) {
      continue;
    }
    const combo = bindingFor(actionId);
    if (combo && matchesEvent(combo, event)) {
      return { actionId, def };
    }
  }
  return undefined;
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

/**
 * Resolve a combo to the concrete physical chord it produces on the CURRENT
 * platform (R15-UI-027 residual): `"mod"` collapses to `"meta"` on macOS or
 * `"ctrl"` elsewhere, so `"mod+p"` and `"meta+p"` compare equal on macOS
 * (both are ⌘P) while `"mod+p"` and `"ctrl+p"` compare equal off macOS —
 * `conflicts()` groups on this instead of the raw string.
 */
function resolveChord(keys: string): string {
  const { modifiers, key } = parseBinding(keys);
  const mac = isMacPlatform();
  const resolved = new Set<string>();
  for (const m of modifiers) {
    resolved.add(m === "mod" ? (mac ? "meta" : "ctrl") : m);
  }
  const order = ["ctrl", "alt", "shift", "meta"] as const;
  const ordered = order.filter((m) => resolved.has(m));
  return [...ordered, ...(key ? [key] : [])].join("+");
}

/** True when running on macOS (so `mod`/`meta` render as ⌘). SSR/jsdom-safe. */
export function isMacPlatform(): boolean {
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
  code?: string;
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
  // Shift is STRICT for a plain letter key (R15-UI-027 residual): otherwise
  // "mod+p" also matches a Shift+⌘+P keystroke, shadowing "shift+mod+p" (the
  // first-match dispatcher always wins for the unshifted combo, so the
  // shifted remap silently never fires). Symbol/digit keys stay lenient on a
  // MISSING shift only — many of them (e.g. "?") are typed only by holding
  // Shift, and the combo string encodes the produced character, not the
  // physical shift state.
  const isLetterKey = /^[a-z]$/.test(key);
  if (isLetterKey ? event.shiftKey !== wantShift : wantShift && !event.shiftKey) {
    return false;
  }

  if (normalizeEventKey(event.key) === key) {
    return true;
  }
  // macOS Option rewrites `event.key` (⌥1 → "¡"), so an alt combo also matches
  // on the physical key.
  return wantAlt && /^(?:Digit|Key)(.)$/.exec(event.code ?? "")?.[1].toLowerCase() === key;
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
