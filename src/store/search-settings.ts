/**
 * Search-settings store — the ONE web-search preference surface (R9 two-tier).
 *
 * R9 collapses the three research tiers into two (`researchTier`):
 *  - `tier_a` — "Unlimited (Local)": the managed SearXNG instance as retrieval
 *    paired with whatever chat model is active running the built-in research
 *    loop. THE default. When SearXNG is not READY the sidecar silently serves
 *    the keyless engines and stamps `backend="keyless-fallback"` on the result
 *    so the UI can render an honest nudge — never an error state, and never a
 *    user-facing "keyless tier".
 *  - `tier_b` — "Hosted research model": an internet-native research model via
 *    OpenRouter owns research at ALL depth stops regardless of the chat model
 *    (per-stop models in `researchModels`, defaults below, user-swappable).
 *    Chat stays on the user's chat model; ONLY research routes to the research
 *    model. Requires the OpenRouter key (keychain-only, rides requests as the
 *    `X-Vysted-Openrouter-Key` header, never logged or persisted).
 *
 * Pre-R9 blobs migrate on restore via {@link migrateSearchSettings}:
 * native / t1_local / local-searxng / t2_searxng → `tier_a`;
 * t3_hosted / the Exa-direct sub-mode (legacy `byok-exa`) → `tier_b` when an
 * OpenRouter key is configured, else `tier_a` (the key presence is confirmed
 * asynchronously by {@link reconcileMigratedTierB} — keychain reads cannot be
 * synchronous). The legacy `tier` / `hostedEngine` / `exaDirect` fields are
 * consumed by migration and DROPPED — they no longer ride the bundle.
 *
 * No secrets here: the OpenRouter BYOK key lives ONLY in the OS keychain (read
 * at request time and sent as a header), never in this bundle (FR-036/SC-010).
 *
 * Persistence mirrors the region/model-selection pattern: the bundle rides the
 * workspace blob (`SerializedWorkspace.searchSettings`), and because a tier
 * change does not move the dockview layout, the store self-persists by calling
 * `void autosaveLayout()` from each setter — exactly like `store/settings`.
 *
 * SSR-safe: no `window`/`navigator` at module load; `autosaveLayout` no-ops
 * before the dockview layout mounts (so a setter in a unit test is a silent
 * no-op).
 */

import { create } from "zustand";

import { getSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { autosaveLayout } from "@/lib/workspace";

/**
 * The R9 research tiers. Mirrors `sidecar/config.py
 * KNOWN_RESEARCH_SEARCH_TIERS` by hand (the `types/data.ts ⇄ sidecar/models/`
 * discipline). Rides requests as the `X-Vysted-Research-Tier` header.
 */
export type ResearchTier = "tier_a" | "tier_b";

/** The complete, ordered tier set — for the Settings radio and validation. */
export const RESEARCH_TIERS: readonly ResearchTier[] = ["tier_a", "tier_b"];

/** A fresh install starts on Unlimited (Local) — never a surprise paid route. */
export const DEFAULT_RESEARCH_TIER: ResearchTier = "tier_a";

/** Type guard for restoring a persisted research tier (garbled blobs → default). */
export function isResearchTier(value: unknown): value is ResearchTier {
  return typeof value === "string" && (RESEARCH_TIERS as readonly string[]).includes(value);
}

/** The three composer depth stops a Tier B research model is configured per. */
export type ResearchStop = "normal" | "deep" | "ultra";

/** The complete, ordered stop set — for the Settings rows and validation. */
export const RESEARCH_STOPS: readonly ResearchStop[] = ["normal", "deep", "ultra"];

/**
 * The Tier B per-stop research-model map. Rides tier_b requests as the
 * `X-Vysted-Research-Models` header (see `encodeResearchModels` in
 * `src/lib/search-headers.ts`); the sidecar mirrors the parse in
 * `config.parse_research_models`.
 */
export interface ResearchModelMap {
  normal: string;
  deep: string;
  ultra: string;
}

/**
 * The Tier B per-stop defaults — verified live on OpenRouter 2026-06-11.
 * Model-agnostic everywhere downstream: the lead may re-pin these slugs at
 * integration without touching any routing code.
 */
export const DEFAULT_RESEARCH_MODELS: Readonly<ResearchModelMap> = Object.freeze({
  normal: "perplexity/sonar",
  deep: "perplexity/sonar-reasoning-pro",
  ultra: "perplexity/sonar-deep-research",
});

/**
 * One pickable Tier B research model + its pricing hint (rendered as
 * micro-text by the Settings per-stop selects — Team D consumes this).
 */
export interface ResearchModelOption {
  /** The OpenRouter model slug (what rides the wire). */
  id: string;
  /** Human display name for the select row. */
  label: string;
  /** Pricing hint micro-text (an ESTIMATE source, never a billed amount). */
  priceHint: string;
  /** True when the pricing was verified live on OpenRouter (2026-06-11). */
  priceVerified: boolean;
}

/**
 * THE one frontend constant for the Tier B model picker — every per-stop
 * select renders this same list (the per-stop slots differ only in which
 * default is pre-selected). Pricing on ALL eight models was verified live
 * on OpenRouter 2026-06-11 (re-pinned by the lead at integration).
 */
export const RESEARCH_MODEL_OPTIONS: readonly ResearchModelOption[] = [
  {
    id: "perplexity/sonar",
    label: "Perplexity Sonar",
    priceHint: "$1/M in · $1/M out · $5/1k searches",
    priceVerified: true,
  },
  {
    id: "perplexity/sonar-reasoning-pro",
    label: "Perplexity Sonar Reasoning Pro",
    priceHint: "$2/M in · $8/M out · $5/1k searches",
    priceVerified: true,
  },
  {
    id: "perplexity/sonar-deep-research",
    label: "Perplexity Sonar Deep Research",
    priceHint: "$2/M in · $8/M out · $5/1k searches · $3/M reasoning",
    priceVerified: true,
  },
  {
    id: "perplexity/sonar-pro",
    label: "Perplexity Sonar Pro",
    priceHint: "$3/M in · $15/M out · $5/1k searches",
    priceVerified: true,
  },
  {
    id: "perplexity/sonar-pro-search",
    label: "Perplexity Sonar Pro Search",
    priceHint: "$3/M in · $15/M out · $18/1k searches (agentic)",
    priceVerified: true,
  },
  {
    id: "openai/o4-mini-deep-research",
    label: "OpenAI o4-mini Deep Research",
    priceHint: "$2/M in · $8/M out · $10/1k searches",
    priceVerified: true,
  },
  {
    id: "openai/o3-deep-research",
    label: "OpenAI o3 Deep Research",
    priceHint: "$10/M in · $40/M out · $10/1k searches",
    priceVerified: true,
  },
  {
    id: "x-ai/grok-4.3",
    label: "xAI Grok 4.3",
    priceHint: "$1.25/M in · $2.50/M out · $5/1k searches",
    priceVerified: true,
  },
];

/** Accepts any plausible OpenRouter slug — routing stays model-agnostic. */
const MODEL_SLUG_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;

/** True for a plausible (sane-charset, bounded) OpenRouter model slug. */
export function isResearchModelId(value: unknown): value is string {
  return typeof value === "string" && MODEL_SLUG_PATTERN.test(value.trim());
}

/** Restore a persisted per-stop map, flooring garbled entries to the default. */
function sanitizeResearchModels(value: unknown): ResearchModelMap {
  const raw = (value ?? {}) as Partial<Record<ResearchStop, unknown>>;
  const out = { ...DEFAULT_RESEARCH_MODELS };
  for (const stop of RESEARCH_STOPS) {
    const candidate = raw[stop];
    if (isResearchModelId(candidate)) {
      out[stop] = candidate.trim();
    }
  }
  return out;
}

/**
 * The serialisable search-preference bundle — exactly what rides the workspace
 * blob's `searchSettings` field. NO secrets (the OpenRouter key is
 * keychain-only).
 */
export interface SearchSettingsBundle {
  /** The authoritative R9 research tier (`X-Vysted-Research-Tier`). */
  researchTier: ResearchTier;
  /**
   * An optional custom SearXNG instance URL ("Advanced"). Empty string = use
   * the one-click managed instance. Sent as the `X-Vysted-Searxng-Url` header
   * when set (omitted when empty) — retrieval is one local lane, so it applies
   * under either tier.
   */
  searxngUrl: string;
  /** The Tier B per-stop research models (`X-Vysted-Research-Models`). */
  researchModels: ResearchModelMap;
}

/** The immutable seed — what a fresh install (or a reset) starts from. */
export const DEFAULT_SEARCH_SETTINGS: Readonly<SearchSettingsBundle> =
  Object.freeze<SearchSettingsBundle>({
    researchTier: DEFAULT_RESEARCH_TIER,
    searxngUrl: "",
    researchModels: DEFAULT_RESEARCH_MODELS,
  });

/**
 * What restore/import accepts: a current bundle OR any older persisted shape.
 * The legacy fields are consumed by {@link migrateSearchSettings} only and
 * never survive into the live state or a re-serialized bundle.
 */
export interface SearchSettingsInput {
  researchTier?: unknown;
  searxngUrl?: unknown;
  researchModels?: unknown;
  /** LEGACY pre-R8 tier (`native` / `byok-exa` / `local-searxng`). */
  tier?: unknown;
  /** LEGACY R7/R8 t3 hosted-engine choice (firecrawl/exa) — dead, dropped. */
  hostedEngine?: unknown;
  /** LEGACY R8 t3 "Exa direct" sub-mode — dead, dropped. */
  exaDirect?: unknown;
}

/** The R7/R8 tier ids + the pre-R8 legacy ids that fold into `tier_a`. */
const LEGACY_TIER_A_VALUES = new Set(["native", "local-searxng", "t1_local", "t2_searxng"]);
/** The legacy ids that fold into `tier_b` — conditional on a configured key. */
const LEGACY_TIER_B_VALUES = new Set(["byok-exa", "t3_hosted"]);

/** The result of folding an arbitrary persisted blob into the R9 vocabulary. */
export interface MigratedSearchSettings {
  /** The full, validated R9 bundle (every field populated). */
  bundle: SearchSettingsBundle;
  /**
   * True when a LEGACY hosted/Exa selection landed on `tier_b` provisionally —
   * the caller must confirm an OpenRouter key exists (async keychain read) and
   * demote to `tier_a` when none is configured ({@link reconcileMigratedTierB}).
   * Never true for a blob that already carried an R9 tier (authoritative).
   */
  tierBNeedsKeyConfirmation: boolean;
}

/**
 * Fold ANY persisted search-settings shape into the R9 two-tier vocabulary.
 * Pure + synchronous (returns new objects; never mutates the input):
 *
 *  - a blob already carrying a valid R9 `researchTier` is authoritative;
 *  - a legacy `researchTier` (t1_local/t2_searxng → tier_a, t3_hosted →
 *    provisional tier_b) or, failing that, a pre-R8 `tier` (native/
 *    local-searxng → tier_a, byok-exa → provisional tier_b) is folded in;
 *  - everything else (absent/garbled) seeds `tier_a` — never a surprise paid
 *    route.
 *
 * Provisional tier_b is confirmed against the keychain by the caller (see
 * {@link MigratedSearchSettings.tierBNeedsKeyConfirmation}); legacy fields are
 * dropped, and `searxngUrl`/`researchModels` are validated field-wise.
 */
export function migrateSearchSettings(input: SearchSettingsInput): MigratedSearchSettings {
  let researchTier: ResearchTier = DEFAULT_RESEARCH_TIER;
  let needsKeyConfirmation = false;

  if (isResearchTier(input.researchTier)) {
    researchTier = input.researchTier;
  } else {
    const legacy = [input.researchTier, input.tier].find(
      (value): value is string =>
        typeof value === "string" &&
        (LEGACY_TIER_A_VALUES.has(value) || LEGACY_TIER_B_VALUES.has(value)),
    );
    if (legacy !== undefined && LEGACY_TIER_B_VALUES.has(legacy)) {
      researchTier = "tier_b";
      needsKeyConfirmation = true;
    }
    // LEGACY_TIER_A_VALUES (and absent/garbled) keep the tier_a default.
  }

  return {
    bundle: {
      researchTier,
      searxngUrl: typeof input.searxngUrl === "string" ? input.searxngUrl : "",
      researchModels: sanitizeResearchModels(input.researchModels),
    },
    tierBNeedsKeyConfirmation: needsKeyConfirmation,
  };
}

/** The LLM-provider keychain slot the Tier B OpenRouter key lives in — the
 * SAME slot Settings → AI Providers writes, so one key lights up both. */
const OPENROUTER_KEYCHAIN_ACCOUNT = KEYCHAIN_NAMESPACES.llmProvider("openrouter");

/**
 * Confirm a MIGRATED provisional `tier_b` against the keychain: when no
 * OpenRouter key is configured (missing, empty, or the keychain is
 * unreachable — it could not serve a request either), the selection demotes to
 * `tier_a` and the demotion is logged once as a migration note (never a user
 * error). A no-op when the live tier is no longer `tier_b` (the user already
 * switched). Exported for tests and for `setAll`'s fire-and-forget call.
 */
export async function reconcileMigratedTierB(): Promise<void> {
  let key: string | null = null;
  try {
    key = await getSecret(OPENROUTER_KEYCHAIN_ACCOUNT);
  } catch {
    key = null;
  }
  if (key && key.length > 0) {
    return;
  }
  const state = useSearchSettingsStore.getState();
  if (state.researchTier !== "tier_b") {
    return;
  }
  console.info(
    "[search-settings] migrated hosted/Exa research selection demoted to " +
      "Unlimited (Local): no OpenRouter key is configured (legacy-blob migration).",
  );
  state.setResearchTier("tier_a");
}

interface SearchSettingsState extends SearchSettingsBundle {
  setSearxngUrl: (url: string) => void;
  setResearchTier: (tier: ResearchTier) => void;
  /** Swap one depth stop's Tier B research model (garbled ids are ignored). */
  setResearchModel: (stop: ResearchStop, modelId: string) => void;
  /** Replace the entire bundle (workspace restore + import); migrates old blobs. */
  setAll: (bundle: SearchSettingsInput) => void;
  /** Snapshot the current preferences as a plain bundle (for serialize/export). */
  toBundle: () => SearchSettingsBundle;
}

/** Clone the seed so no caller can mutate the frozen default in place. */
function seed(): SearchSettingsBundle {
  return {
    researchTier: DEFAULT_SEARCH_SETTINGS.researchTier,
    searxngUrl: DEFAULT_SEARCH_SETTINGS.searxngUrl,
    researchModels: { ...DEFAULT_SEARCH_SETTINGS.researchModels },
  };
}

/**
 * Self-persist a preference change into the autosave slot. Fire-and-forget —
 * `autosaveLayout` is best-effort and no-ops before the layout mounts.
 */
function persist(): void {
  void autosaveLayout();
}

export const useSearchSettingsStore = create<SearchSettingsState>((set, get) => ({
  ...seed(),

  setSearxngUrl: (url) => {
    set({ searxngUrl: url });
    persist();
  },

  setResearchTier: (researchTier) => {
    set({ researchTier });
    persist();
  },

  setResearchModel: (stop, modelId) => {
    if (!RESEARCH_STOPS.includes(stop) || !isResearchModelId(modelId)) {
      return;
    }
    set({ researchModels: { ...get().researchModels, [stop]: modelId.trim() } });
    persist();
  },

  setAll: (bundle) => {
    // Fold ANY older blob into the R9 vocabulary first; migration returns a
    // FULL validated bundle (merged over the seed), so a partial blob can't
    // strip a field and a garbled value falls back to the default.
    const { bundle: migrated, tierBNeedsKeyConfirmation } = migrateSearchSettings(bundle ?? {});
    set(migrated);
    persist();
    if (tierBNeedsKeyConfirmation) {
      // A legacy hosted/Exa selection landed on tier_b provisionally — confirm
      // the OpenRouter key exists (async keychain read) and demote to tier_a
      // when it does not. Fire-and-forget: restore must stay synchronous.
      void reconcileMigratedTierB();
    }
  },

  toBundle: () => {
    const s = get();
    return {
      researchTier: s.researchTier,
      searxngUrl: s.searxngUrl,
      researchModels: { ...s.researchModels },
    };
  },
}));

/** Non-reactive snapshot of the search-preference bundle (for serialize/export). */
export function searchSettingsBundle(): SearchSettingsBundle {
  return useSearchSettingsStore.getState().toBundle();
}

/** Test helper: reset the search-settings store to its seed (defaults). */
export function resetSearchSettingsStoreForTests(): void {
  useSearchSettingsStore.setState(seed());
}
