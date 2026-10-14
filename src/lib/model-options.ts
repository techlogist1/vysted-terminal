/**
 * Model-dropdown option helpers.
 *
 * Shared by the agent HUD and the settings default-model picker so both render
 * the live catalog identically: tool-calling-capable models surfaced first (an
 * agent that drives tools needs them), non-tool-capable models clearly marked
 * (picking one breaks host-actions), and the currently-selected model always
 * present even if it has dropped out of the catalog.
 */

import type { LLMModelOption } from "../../types/ai";

/** A `<select>` optgroup — `label === null` renders the options ungrouped. */
export interface ModelOptionGroup {
  label: string | null;
  options: LLMModelOption[];
}

/**
 * Partition catalog options into render groups + report whether the selected
 * model is known to lack tool-calling. Groups only when tool-capability is known
 * for some models AND there is a mix worth separating; otherwise a single flat
 * group (e.g. providers whose catalog doesn't report tool support).
 */
export function buildModelGroups(
  options: LLMModelOption[],
  selected: string,
): { groups: ModelOptionGroup[]; selectedIsNoTools: boolean } {
  const hasSelected = !selected || options.some((o) => o.id === selected);
  const all: LLMModelOption[] = hasSelected
    ? options
    : [{ id: selected, label: selected }, ...options];

  const toolCapable = all.filter((o) => o.supportsTools === true);
  const noTools = all.filter((o) => o.supportsTools === false);
  const unknown = all.filter((o) => o.supportsTools !== true && o.supportsTools !== false);

  const worthGrouping = toolCapable.length > 0 && (noTools.length > 0 || unknown.length > 0);

  let groups: ModelOptionGroup[];
  if (worthGrouping) {
    groups = [];
    if (toolCapable.length) groups.push({ label: "Tool-calling", options: toolCapable });
    if (unknown.length) groups.push({ label: "Other", options: unknown });
    if (noTools.length) groups.push({ label: "No tool-calling", options: noTools });
  } else {
    groups = [{ label: null, options: all }];
  }

  const selectedIsNoTools = all.some((o) => o.id === selected && o.supportsTools === false);
  return { groups, selectedIsNoTools };
}

/** A subtle search-capability pip appended to a model's option label (WS5).
 *
 * Reuses the same `<option>`-text convention as the `· no tools` marker (an HTML
 * `<option>` renders text only — no chrome — so a glyph suffix is the honest,
 * dependency-free pip). The `⌕` magnifier reads as "search":
 *   - `native`  → ` · ⌕` (filled): the model runs its OWN server-side search.
 *   - `plugin`  → ` · ⌕?` (outline): no native search, but a billed plugin is
 *     available; searches still fall back to the app's search tool here.
 *   - `none`/unknown → absent: the app's own search tool handles it (the
 *     non-OpenRouter providers leave this unset, so they never grow a pip).
 */
export function modelSearchPip(option: LLMModelOption): string {
  if (option.webSearch === "native") return " · ⌕";
  if (option.webSearch === "plugin") return " · ⌕?";
  return "";
}

/** Option display label — marks a non-tool-capable model so the choice is honest,
 *  plus a subtle native-search pip (WS5). */
export function modelOptionLabel(option: LLMModelOption): string {
  const base = option.supportsTools === false ? `${option.label} · no tools` : option.label;
  return `${base}${modelSearchPip(option)}`;
}
