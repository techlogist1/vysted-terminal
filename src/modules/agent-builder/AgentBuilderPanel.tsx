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
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { isCustomAgent, useAgentsStore } from "@/store/agents";

import type { AgentSpec } from "../../../types/plugin";
import {
  CUSTOM_AGENT_ID_PREFIX,
  emptyFormState,
  KNOWN_PROVIDER_IDS,
  KNOWN_TOOL_IDS,
  useAgentBuilderForm,
  validate,
  type AgentBuilderFormState,
  type KnownToolId,
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
    tools: new Set(agent.tools),
    defaultProvider: (KNOWN_PROVIDER_IDS as readonly string[]).includes(agent.defaultProvider)
      ? (agent.defaultProvider as (typeof KNOWN_PROVIDER_IDS)[number])
      : "anthropic",
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
  const response = await fetch(url.toString(), {
    method: mode === "create" ? "POST" : "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const json = (await response.json()) as { detail?: unknown };
      if (typeof json.detail === "string") {
        detail = json.detail;
      }
    } catch {
      // body wasn't JSON; fall through to a generic message
    }
    throw new Error(detail ?? `request failed (${response.status})`);
  }
}

async function deleteCustomAgent(agentId: string): Promise<void> {
  const base = await getSidecarBaseUrl();
  const url = new URL(`/custom-agents/${encodeURIComponent(agentId)}`, base);
  const response = await fetch(url.toString(), { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`delete failed (${response.status})`);
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

  useEffect(() => {
    void refreshCustom();
  }, [refreshCustom]);

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
      // Replace the tool set wholesale.
      for (const tool of KNOWN_TOOL_IDS) {
        const want = next.tools.has(tool);
        const has = state.tools.has(tool);
        if (want !== has) {
          toggleTool(tool);
        }
      }
      setEditingId(agent.id);
      setSaveStatus("idle");
      setSaveMessage(null);
      setErrors({});
    },
    [customSummaries, setField, state.tools, toggleTool],
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
                className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-r-control text-body h-8 flex-1 border px-2 font-mono outline-none focus:ring-1 focus:ring-amber-400"
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
              className="bg-charcoal-800 text-charcoal-100 rounded-control text-body h-8 px-2 font-mono outline-none focus:ring-1 focus:ring-amber-400"
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
            className="bg-charcoal-800 text-charcoal-100 rounded-control text-body h-8 px-2 font-mono outline-none focus:ring-1 focus:ring-amber-400"
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
            className="bg-charcoal-800 text-charcoal-100 rounded-control text-caption min-h-[8rem] resize-y p-2 font-mono leading-relaxed outline-none focus:ring-1 focus:ring-amber-400"
          />
          {errors.systemPrompt !== undefined && (
            <p className="text-negative text-micro font-mono">{errors.systemPrompt}</p>
          )}
        </label>

        {/* Tools */}
        <div className="flex flex-col gap-1">
          <span className="text-charcoal-400 text-micro font-mono uppercase">Tools</span>
          <div className="flex flex-wrap gap-1">
            {KNOWN_TOOL_IDS.map((tool) => {
              const active = state.tools.has(tool);
              return (
                <button
                  type="button"
                  key={tool}
                  onClick={() => toggleTool(tool as KnownToolId)}
                  aria-pressed={active}
                  className={cn(
                    "rounded-control text-micro border px-2 py-1 font-mono transition-colors",
                    active
                      ? "border-amber-500 bg-amber-500/15 text-amber-300"
                      : "border-charcoal-700 text-charcoal-400 hover:border-charcoal-600 hover:text-charcoal-200",
                  )}
                >
                  {tool}
                </button>
              );
            })}
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
              onChange={(e) =>
                setField("defaultProvider", e.target.value as (typeof KNOWN_PROVIDER_IDS)[number])
              }
              className="bg-charcoal-800 text-charcoal-100 border-charcoal-700 rounded-control text-caption h-8 border px-2 font-mono outline-none focus:ring-1 focus:ring-amber-400"
            >
              {KNOWN_PROVIDER_IDS.map((id) => (
                <option key={id} value={id}>
                  {id}
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
              className="bg-charcoal-800 text-charcoal-100 rounded-control text-body h-8 px-2 font-mono outline-none focus:ring-1 focus:ring-amber-400"
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
            className="bg-charcoal-800 text-charcoal-100 rounded-control text-body h-8 px-2 font-mono outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>

        {/* Save / cancel row */}
        <div className="flex flex-col gap-1.5 pt-2">
          <div className="flex items-center gap-2">
            <Button
              type="submit"
              size="sm"
              variant="outline"
              disabled={saveStatus === "saving" || !liveValidation.ok}
            >
              {saveStatus === "saving" && <Loader2 className="size-3 animate-spin" />}
              {saveStatus === "saving" ? "Saving…" : isEditing ? "Save changes" : "Create agent"}
            </Button>
            {isEditing && (
              <Button type="button" size="sm" variant="ghost" onClick={handleCancelEdit}>
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
                className="text-caption shrink-0 font-mono text-amber-400 underline hover:text-amber-300"
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
                className="text-micro text-left font-mono text-amber-400 underline hover:text-amber-300"
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
