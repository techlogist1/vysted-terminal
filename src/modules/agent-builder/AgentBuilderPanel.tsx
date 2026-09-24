"use client";

/**
 * Custom Agent Builder panel — Module 36 (BLUEPRINT) / Phase 3 Teammate C.
 *
 * The user fills in identity (id + name), philosophy, system prompt, tool
 * allow-list (multi-select against the host's known tool ids), and a default
 * provider/model. On save, the form POSTs `/custom-agents` and refreshes the
 * shared `useAgentsStore` so the chat sidebar's picker (Teammate A) sees the
 * new agent.
 *
 * The panel also lists existing custom agents on the right, with one-click
 * edit / delete. Custom-agent ids always carry the `custom:` prefix — the
 * input only takes the body, the prefix is rendered as a non-editable label
 * so the user understands the convention without being able to type past it.
 *
 * No localStorage — all persistence flows through the sidecar
 * (`POST/PUT/DELETE /custom-agents`).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  extractSidecarDetail,
  getSidecarBaseUrl,
  SidecarError,
  sidecarFetch,
} from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { isCustomAgent, useAgentsStore } from "@/store/agents";
import { useLLMProvidersStore } from "@/store/llm-providers";

import type { AgentSpec } from "../../../types/plugin";
import {
  CUSTOM_AGENT_ID_PREFIX,
  emptyFormState,
  KNOWN_TOOL_IDS,
  useAgentBuilderForm,
  validate,
  type AgentBuilderFormState,
  type SubmitPayload,
} from "./form";

type SaveStatus = "idle" | "saving" | "saved" | "error";

/**
 * Build an initial form state from an existing agent so "Edit" populates
 * every field. The id body strips the `custom:` prefix — the form input
 * only manages the body. An optional `defaultModel` override allows passing
 * the value from AgentSummary (which carries it from the wire) since AgentSpec
 * does not have a defaultModel field.
 */
function formStateFromAgent(agent: AgentSpec, defaultModel?: string | null): AgentBuilderFormState {
  const idBody = agent.id.startsWith(CUSTOM_AGENT_ID_PREFIX)
    ? agent.id.slice(CUSTOM_AGENT_ID_PREFIX.length)
    : agent.id;
  return {
    idBody,
    name: agent.name,
    philosophy: agent.philosophy,
    systemPrompt: agent.systemPrompt,
    // R15-UI-003: the agent's FULL tool set and its own provider, verbatim —
    // gating either against a static fallback list is what silently stripped
    // tools / reset the provider to "anthropic" on edit.
    tools: new Set(agent.tools),
    defaultProvider: agent.defaultProvider,
    defaultModel: defaultModel ?? "",
    icon: agent.icon ?? "",
  };
}

/** POST/PUT helper — keeps the panel handlers terse. */
async function writeCustomAgent(payload: SubmitPayload, mode: "create" | "update"): Promise<void> {
  const base = await getSidecarBaseUrl();
  const url =
    mode === "create"
      ? new URL("/custom-agents", base)
      : new URL(`/custom-agents/${encodeURIComponent(payload.id)}`, base);
  // The update endpoint does not accept ``id`` in the body — strip it.
  const body =
    mode === "create"
      ? payload
      : ((): Omit<SubmitPayload, "id"> => {
          const { id: _id, ...rest } = payload;
          void _id;
          return rest;
        })();
  const response = await sidecarFetch(url.toString(), {
    method: mode === "create" ? "POST" : "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await throwUnlessOk(response, `request failed (${response.status})`);
}

async function deleteCustomAgent(agentId: string): Promise<void> {
  const base = await getSidecarBaseUrl();
  const url = new URL(`/custom-agents/${encodeURIComponent(agentId)}`, base);
  const response = await sidecarFetch(url.toString(), { method: "DELETE" });
  await throwUnlessOk(response, `delete failed (${response.status})`);
}

/** A non-2xx as the sidecar's own sentence: a string `detail`, or `field: msg`
 *  for a 422 array (which used to collapse to the fallback). */
async function throwUnlessOk(response: Response, fallback: string): Promise<void> {
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new SidecarError(response.status, extractSidecarDetail(body, fallback));
  }
}

/**
 * The panel component. Self-contained — no props, like every other first-
 * party module's panel.
 */
export function AgentBuilderPanel() {
  const { state, setField, toggleTool, reset } = useAgentBuilderForm();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const customAgents = useAgentsStore((s) => s.customAgents);
  const customSummaries = useAgentsStore((s) => s.customSummaries);
  const refreshCustom = useAgentsStore((s) => s.refreshCustom);
  const setCustomAgents = useAgentsStore((s) => s.setCustomAgents);
  const customStatus = useAgentsStore((s) => s.customStatus);
  const customError = useAgentsStore((s) => s.customError);
  // R15-UI-003: providers come from the live catalog (already fetched
  // app-wide, `DEFAULT_PROVIDERS` fallback baked into the store itself).
  const providers = useLLMProvidersStore((s) => s.providers);
  // Tool ids come from the sidecar's OWN vocabulary (`GET
  // /custom-agents/tool-ids` == `agent_selectable_tool_ids()`) — the static
  // `KNOWN_TOOL_IDS` array is only the pre-fetch fallback.
  const [toolIds, setToolIds] = useState<string[]>([...KNOWN_TOOL_IDS]);

  useEffect(() => {
    void refreshCustom();
  }, [refreshCustom]);

  useEffect(() => {
    let cancelled = false;
    // Built with getSidecarBaseUrl() + fetch() directly (mirrors
    // writeCustomAgent/deleteCustomAgent below), not the sidecarGet()
    // helper — sidecarGet resolves the base URL through its OWN
    // module-internal binding, which does not pick up a per-test
    // getSidecarBaseUrl override.
    void (async () => {
      try {
        const base = await getSidecarBaseUrl();
        const response = await fetch(new URL("/custom-agents/tool-ids", base).toString());
        if (!response.ok) {
          return;
        }
        const ids: unknown = await response.json();
        // A malformed response (older sidecar build, transient network
        // error surfaced as an HTML body, etc.) keeps the static fallback
        // rather than rendering a broken tool list.
        if (!cancelled && Array.isArray(ids) && ids.every((id) => typeof id === "string")) {
          setToolIds(ids);
        }
      } catch {
        // Fetch rejected — keep the fallback.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const isEditing = editingId !== null;

  // Stable validation result for the current form state — recomputed on each
  // render but the value is memoised so the JSX comparison is a pointer check.
  const liveValidation = useMemo(() => validate(state), [state]);

  const handleEdit = useCallback(
    (agent: AgentSpec) => {
      if (!isCustomAgent(agent)) {
        return;
      }
      // Look up defaultModel from customSummaries since AgentSpec doesn't carry it.
      const summary = customSummaries.find((s) => s.id === agent.id);
      const next = formStateFromAgent(agent, summary?.defaultModel);
      setField("idBody", next.idBody);
      setField("name", next.name);
      setField("philosophy", next.philosophy);
      setField("systemPrompt", next.systemPrompt);
      setField("defaultProvider", next.defaultProvider);
      setField("defaultModel", next.defaultModel);
      setField("icon", next.icon);
      // R15-UI-003: replace the tool set WHOLESALE, not by toggling each
      // known id — a loop over a (possibly stale) known-id list silently
      // drops any tool id the list doesn't happen to carry.
      setField("tools", next.tools);
      setEditingId(agent.id);
      setSaveStatus("idle");
      setSaveMessage(null);
      setErrors({});
    },
    [customSummaries, setField],
  );

  const handleDelete = useCallback(
    async (agentId: string) => {
      setSaveStatus("saving");
      try {
        await deleteCustomAgent(agentId);
        // Optimistic local update so the picker reflects the change instantly.
        setCustomAgents(customAgents.filter((a) => a.id !== agentId));
        if (editingId === agentId) {
          reset();
          setEditingId(null);
        }
        setSaveStatus("saved");
        setSaveMessage("Deleted.");
      } catch (error: unknown) {
        setSaveStatus("error");
        setSaveMessage(error instanceof Error ? error.message : "Delete failed.");
      }
    },
    [customAgents, editingId, reset, setCustomAgents],
  );

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const result = validate(state);
      if (!result.ok) {
        setErrors(result.errors);
        setSaveStatus("idle");
        return;
      }
      setErrors({});
      setSaveStatus("saving");
      try {
        await writeCustomAgent(result.payload, isEditing ? "update" : "create");
        await refreshCustom();
        setSaveStatus("saved");
        setSaveMessage(isEditing ? "Updated." : "Created.");
        if (!isEditing) {
          // Successful create — reset the form so the user can immediately
          // define another agent without clearing fields by hand.
          reset();
        }
      } catch (error: unknown) {
        setSaveStatus("error");
        setSaveMessage(error instanceof Error ? error.message : "Save failed.");
      }
    },
    [isEditing, refreshCustom, reset, state],
  );

  const handleCancelEdit = useCallback(() => {
    setEditingId(null);
    reset();
    setErrors({});
    setSaveStatus("idle");
    setSaveMessage(null);
  }, [reset]);

  return (
    <div
      className="bg-charcoal-900 grid h-full w-full grid-cols-1 lg:grid-cols-[1fr_minmax(220px,260px)]"
      data-testid="agent-builder-panel"
    >
      {/* --- form column --- */}
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-col gap-3 overflow-y-auto p-4">
        <header className="flex items-baseline justify-between">
          <h2 className="text-charcoal-100 text-panel-title font-mono tracking-wide uppercase">
            {isEditing ? "Edit custom agent" : "New custom agent"}
          </h2>
          <span className="text-charcoal-500 text-micro font-mono uppercase">
            module 36 · BLUEPRINT
          </span>
        </header>

        {/* Identity row */}
        <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-micro font-mono uppercase">ID</span>
            <div className="flex items-stretch">
              <span className="bg-charcoal-850 text-charcoal-400 border-charcoal-700 rounded-l-control text-caption inline-flex items-center border border-r-0 px-2 font-mono">
                {CUSTOM_AGENT_ID_PREFIX}
              </span>
              <input
                aria-label="Agent ID"
                value={state.idBody}
                onChange={(e) => setField("idBody", e.target.value)}
                placeholder="macro-quant"
                spellCheck={false}
                className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-r-control text-body focus:ring-charcoal-500 h-8 flex-1 border px-2 font-mono outline-none focus:ring-1"
                disabled={isEditing}
              />
            </div>
            {errors.idBody !== undefined && (
              <p className="text-negative text-micro font-mono">{errors.idBody}</p>
            )}
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-micro font-mono uppercase">Name</span>
            <input
              aria-label="Agent name"
              value={state.name}
              onChange={(e) => setField("name", e.target.value)}
              placeholder="Macro Quant"
              className="bg-charcoal-800 text-charcoal-100 rounded-control text-body focus:ring-charcoal-500 h-8 px-2 font-mono outline-none focus:ring-1"
            />
            {errors.name !== undefined && (
              <p className="text-negative text-micro font-mono">{errors.name}</p>
            )}
          </label>
        </fieldset>

        {/* Philosophy */}
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro font-mono uppercase">Philosophy</span>
          <input
            aria-label="Philosophy"
            value={state.philosophy}
            onChange={(e) => setField("philosophy", e.target.value)}
            placeholder="One-line lens (e.g. 'Mean reversion across macro asset classes.')"
            className="bg-charcoal-800 text-charcoal-100 rounded-control text-body focus:ring-charcoal-500 h-8 px-2 font-mono outline-none focus:ring-1"
          />
          {errors.philosophy !== undefined && (
            <p className="text-negative text-micro font-mono">{errors.philosophy}</p>
          )}
        </label>

        {/* System prompt */}
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro font-mono uppercase">System prompt</span>
          <textarea
            aria-label="System prompt"
            value={state.systemPrompt}
            onChange={(e) => setField("systemPrompt", e.target.value)}
            placeholder="You are a macro quant analyst. Reason from regime first; cite drawdown statistics when answering."
            rows={8}
            className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption focus:ring-charcoal-500 min-h-24 resize-y p-2 font-mono leading-relaxed outline-none focus:ring-1"
          />
          {errors.systemPrompt !== undefined && (
            <p className="text-negative text-micro font-mono">{errors.systemPrompt}</p>
          )}
        </label>

        {/* Tools */}
        <div className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro font-mono uppercase">Tools</span>
          <div className="flex flex-wrap gap-1">
            {toolIds.map((tool) => {
              const active = state.tools.has(tool);
              return (
                <button
                  type="button"
                  key={tool}
                  onClick={() => toggleTool(tool)}
                  aria-pressed={active}
                  className={cn(
                    "rounded-control text-micro border px-2 py-1 font-mono transition-colors",
                    active
                      ? "border-charcoal-600 bg-charcoal-700/15 text-charcoal-300"
                      : "border-charcoal-700 text-charcoal-400 hover:border-charcoal-600 hover:text-charcoal-200",
                  )}
                >
                  {tool}
                </button>
              );
            })}
            {/* R15-UI-003: a selected tool the live vocabulary doesn't (yet)
                list — e.g. the fetch hasn't resolved, or the id is stale —
                renders read-only so it's still visibly part of the agent and
                still SUBMITTED (validate() no longer filters), never
                silently dropped the way toggling only known ids did. */}
            {[...state.tools]
              .filter((tool) => !toolIds.includes(tool))
              .map((tool) => (
                <span
                  key={tool}
                  title="Not in the current tool catalog — kept as-is, not editable here."
                  className="rounded-control text-micro border-charcoal-700 text-charcoal-500 border border-dashed px-2 py-1 font-mono"
                >
                  {tool}
                </span>
              ))}
          </div>
        </div>

        {/* Provider + model */}
        <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-micro font-mono uppercase">
              Default provider
            </span>
            <select
              aria-label="Default provider"
              value={state.defaultProvider}
              onChange={(e) => setField("defaultProvider", e.target.value)}
              className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-control text-caption focus:ring-charcoal-500 h-8 border px-2 font-mono outline-none focus:ring-1"
            >
              {/* R15-UI-003: an agent's own provider that the live catalog
                  doesn't list (e.g. "openrouter" against the old static
                  7-provider array) still renders as its own option, rather
                  than the select silently showing nothing selected. */}
              {!providers.some((p) => p.id === state.defaultProvider) &&
                state.defaultProvider !== "" && (
                  <option value={state.defaultProvider}>
                    {state.defaultProvider} (unrecognized)
                  </option>
                )}
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-charcoal-400 text-micro font-mono uppercase">
              Default model (optional)
            </span>
            <input
              aria-label="Default model"
              value={state.defaultModel}
              onChange={(e) => setField("defaultModel", e.target.value)}
              placeholder="e.g. claude-opus-4-8"
              className="bg-charcoal-800 text-charcoal-100 rounded-control text-body focus:ring-charcoal-500 h-8 px-2 font-mono outline-none focus:ring-1"
            />
          </label>
        </fieldset>

        {/* Icon */}
        <label className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro font-mono uppercase">
            Icon (Lucide name, optional)
          </span>
          <input
            aria-label="Icon"
            value={state.icon}
            onChange={(e) => setField("icon", e.target.value)}
            placeholder="e.g. brain"
            className="bg-charcoal-800 text-charcoal-100 rounded-control text-body focus:ring-charcoal-500 h-8 px-2 font-mono outline-none focus:ring-1"
          />
        </label>

        {/* Save / cancel row */}
        <div className="flex flex-col gap-2 pt-2">
          <div className="flex items-center gap-2">
            <Button
              type="submit"
              variant="outline"
              disabled={saveStatus === "saving" || !liveValidation.ok}
            >
              {saveStatus === "saving" && <Loader2 className="animate-spin" />}
              {saveStatus === "saving" ? "Saving…" : isEditing ? "Save changes" : "Create agent"}
            </Button>
            {isEditing && (
              <Button type="button" variant="ghost" onClick={handleCancelEdit}>
                Cancel
              </Button>
            )}
            {saveStatus === "saved" && saveMessage !== null && (
              <span className="text-positive text-caption font-mono">{saveMessage}</span>
            )}
          </div>
          {saveStatus === "error" && saveMessage !== null && (
            <div className="flex items-center gap-2">
              <span className="text-negative text-caption overflow-hidden font-mono text-ellipsis">
                {saveMessage}
              </span>
              <button
                type="submit"
                className="text-caption text-charcoal-300 hover:text-charcoal-100 shrink-0 font-mono underline"
              >
                Try again
              </button>
            </div>
          )}
        </div>
      </form>

      {/* --- list column --- */}
      <aside className="border-charcoal-700 flex min-h-0 flex-col border-t lg:border-t-0 lg:border-l">
        <header className="border-charcoal-700 flex items-center justify-between border-b px-3 py-2">
          <span className="text-charcoal-200 text-caption font-mono uppercase">Your agents</span>
          <span className="text-charcoal-500 text-micro font-mono uppercase">
            {customAgents.length}
          </span>
        </header>
        <div className="flex-1 overflow-y-auto">
          {customStatus === "loading" && (
            <div className="flex flex-col gap-2 px-3 py-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="bg-charcoal-800 h-8 animate-pulse rounded-none" />
              ))}
            </div>
          )}
          {customStatus === "error" && (
            <div className="flex flex-col gap-1 px-3 py-3">
              <p className="text-negative text-micro font-mono">
                {customError ?? "Failed to load agents."}
              </p>
              <button
                type="button"
                onClick={() => void refreshCustom()}
                className="text-micro text-charcoal-300 hover:text-charcoal-100 text-left font-mono underline"
              >
                Retry
              </button>
            </div>
          )}
          {customStatus === "ready" && customAgents.length === 0 && (
            <div className="flex flex-col items-start gap-1 px-3 py-3">
              <p className="text-charcoal-400 text-caption font-mono">No custom agents yet.</p>
              <p className="text-charcoal-500 text-micro font-mono">
                Fill the form to create your first.
              </p>
            </div>
          )}
          <ul>
            {customAgents.map((agent) => (
              <li
                key={agent.id}
                className={cn(
                  "border-charcoal-800 flex items-start justify-between gap-2 border-b px-3 py-2",
                  editingId === agent.id && "bg-charcoal-850",
                )}
              >
                <button
                  type="button"
                  onClick={() => handleEdit(agent)}
                  className="flex w-full min-w-0 flex-1 flex-col items-start gap-0.5 text-left"
                >
                  <span className="text-charcoal-100 text-caption font-mono">{agent.name}</span>
                  <span className="text-charcoal-400 text-micro w-full truncate font-mono">
                    {agent.id}
                  </span>
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${agent.name}`}
                  onClick={() => handleDelete(agent.id)}
                  className="text-charcoal-400 hover:text-negative text-micro font-mono"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}

// Re-export the empty form state so the test file can use it without
// importing from ``./form`` directly — keeps the test surface narrow.
export { emptyFormState };
