/**
 * Provider readiness (R15-UI-013, contract C4) — the one reader of
 * `POST /llm/keys/validate`.
 *
 * The answer says WHY a provider is not usable, so each caller can route on it:
 * `not_configured` (no key → set one up), `invalid` (the key was rejected),
 * `unreachable` (the provider, the local daemon or the data engine itself did
 * not answer) and `model_not_pulled` (Ollama is up but the model is not
 * downloaded). A bounded 15 s wait: a hanging endpoint never holds a dialog.
 */

import { useEffect, useState } from "react";

import { extractSidecarDetail, getSidecarBaseUrl } from "@/lib/sidecar-client";
import { useAppStore } from "@/store/app";
import { useLocalEngineStore } from "@/store/local-engine";

export type ProviderReason = "invalid" | "not_configured" | "unreachable" | "model_not_pulled";

export interface ProviderValidation {
  ok: boolean;
  reason: ProviderReason | null;
  detail: string | null;
}

export const VALIDATION_TIMEOUT_MS = 15_000;

const ENGINE_DOWN = "The data engine is not responding — it may have stopped. Restart Vysted.";

/**
 * Validate a provider (and, for a keyless local provider, the model about to be
 * used). Never rejects except when the caller's own `signal` aborts it (a
 * Cancel), which rejects with that abort.
 */
export async function validateProvider(
  provider: string,
  opts: { apiKey?: string | null; model?: string | null; signal?: AbortSignal } = {},
): Promise<ProviderValidation> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, VALIDATION_TIMEOUT_MS);
  const onCallerAbort = () => controller.abort();
  opts.signal?.addEventListener("abort", onCallerAbort, { once: true });
  // getSidecarBaseUrl can wait out a cold boot; the bound covers it too.
  const aborted = new Promise<never>((_, reject) => {
    controller.signal.addEventListener("abort", () => reject(new DOMException("", "AbortError")));
  });
  if (opts.signal?.aborted) {
    controller.abort();
  }
  try {
    const base = await Promise.race([getSidecarBaseUrl(), aborted]);
    const response = await fetch(new URL("/llm/keys/validate", base).toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider,
        api_key: opts.apiKey?.trim() || null,
        model: opts.model ?? null,
      }),
      signal: controller.signal,
    });
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Not JSON — the status line below still names the failure.
    }
    if (!response.ok) {
      return {
        ok: false,
        reason: "unreachable",
        detail: extractSidecarDetail(body, `The data engine answered ${response.status}.`),
      };
    }
    const result = (body ?? {}) as Partial<ProviderValidation>;
    const ok = result.ok === true;
    return {
      ok,
      reason: ok ? null : (result.reason ?? "invalid"),
      detail: result.detail ?? null,
    };
  } catch (err) {
    if (opts.signal?.aborted) {
      throw err;
    }
    return {
      ok: false,
      reason: "unreachable",
      detail: timedOut
        ? `No answer within ${VALIDATION_TIMEOUT_MS / 1000} s — the provider or the data engine is not responding.`
        : ENGINE_DOWN,
    };
  } finally {
    clearTimeout(timer);
    opts.signal?.removeEventListener("abort", onCallerAbort);
  }
}

// --- Readiness probe cache (D60) ---------------------------------------------
// The status chip and the onboarding banner ask the same question ("is the
// keyless default lane usable?"). The answer is cached at module level so
// re-mounts never hammer the sidecar: a positive holds for 5 minutes, a negative
// re-probes after 30 s (so starting Ollama heals the chrome without a restart).
// Provider `local` also re-probes whenever the engine's state reaches the sidecar.
export const PROBE_TTL_OK_MS = 300_000;
export const PROBE_TTL_FAIL_MS = 30_000;
const probeCache = new Map<string, { result: ProviderValidation; at: number }>();
// Bumped on every drop, so a probe already in flight cannot write a stale answer back.
let probeGeneration = 0;
let lastLocalSync = 0;

/** Test seam — clears the module-level probe cache between tests. */
export function __resetProviderProbeCacheForTests(): void {
  probeCache.clear();
  probeGeneration += 1;
  lastLocalSync = 0;
}

function dropProvider(provider: string): void {
  for (const key of probeCache.keys()) {
    if (key.startsWith(probeKey(provider, ""))) {
      probeCache.delete(key);
    }
  }
  probeGeneration += 1;
}

function probeKey(provider: string, model: string | null | undefined): string {
  return `${provider}\u0000${model ?? ""}`;
}

/** A cached probe still within its TTL (positives live longer). */
export function cachedReadiness(
  provider: string,
  model?: string | null,
): ProviderValidation | undefined {
  return msUntilExpiry(provider, model) > 0
    ? probeCache.get(probeKey(provider, model))?.result
    : undefined;
}

/** Milliseconds a cached probe stays fresh (0 = none or expired). */
function msUntilExpiry(provider: string, model: string | null | undefined): number {
  const cached = probeCache.get(probeKey(provider, model));
  if (!cached) {
    return 0;
  }
  const ttl = cached.result.ok ? PROBE_TTL_OK_MS : PROBE_TTL_FAIL_MS;
  return Math.max(0, cached.at + ttl - Date.now());
}

/** Validate a keyless lane through the cache (a fresh entry is served as-is). */
export async function probeReadiness(
  provider: string,
  model?: string | null,
): Promise<ProviderValidation> {
  const fresh = cachedReadiness(provider, model);
  if (fresh) {
    return fresh;
  }
  const generation = probeGeneration;
  const result = await validateProvider(provider, { model });
  if (generation === probeGeneration) {
    probeCache.set(probeKey(provider, model), { result, at: Date.now() });
  }
  return result;
}

/**
 * Readiness of a keyless lane, probed fire-and-forget so the caller renders at
 * once. `null` = not known yet (or not a keyless lane). The sidecar status is a
 * dependency: a probe that failed while the engine was still binding re-runs
 * once it connects. An entry re-probes when its TTL lapses, and for provider
 * `local` each confirmed engine sync drops the cached answer and re-probes (so
 * a model finishing loading heals at once, and a crash downgrades at once).
 */
export function useKeylessReadiness(
  provider: string | null | undefined,
  model: string | null | undefined,
  keyless: boolean,
): ProviderValidation | null {
  const sidecarStatus = useAppStore((state) => state.sidecarStatus);
  const localSync = useLocalEngineStore((state) => (provider === "local" ? state.syncCount : 0));
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!provider || !keyless) {
      return;
    }
    if (provider === "local" && localSync !== lastLocalSync) {
      lastLocalSync = localSync;
      dropProvider("local");
    }
    let cancelled = false;
    const rerender = () => {
      if (!cancelled) {
        setTick((t) => t + 1);
      }
    };
    const fresh = msUntilExpiry(provider, model);
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (fresh > 0) {
      timer = setTimeout(rerender, fresh);
    } else {
      void probeReadiness(provider, model).then(rerender);
    }
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [provider, model, keyless, sidecarStatus, localSync, tick]);

  if (!provider || !keyless) {
    return null;
  }
  return cachedReadiness(provider, model) ?? null;
}
