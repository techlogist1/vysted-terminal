"use client";

/**
 * Custom Agent Builder form — a small, self-contained shape used by both the
 * panel and the tests. The panel renders inputs against this state; the tests
 * exercise validation by driving the same controlled form.
 *
 * Validation lives in `validate()`; the form widget itself only handles
 * controlled-input plumbing, so unit tests can drive `validate()` directly
 * without rendering the JSX.
 */

import { useCallback, useState } from "react";

/** Tool ids the host currently resolves — must match the sidecar allow-list. */
export const KNOWN_TOOL_IDS = [
  "price_data",
  "fundamentals",
  "news",
  "backtest_summary",
  "macro",
] as const;
export type KnownToolId = (typeof KNOWN_TOOL_IDS)[number];

/** Provider ids the form's dropdown surfaces (mirrors `types/ai.ts`). */
export const KNOWN_PROVIDER_IDS = [
  "anthropic",
  "openai",
  "gemini",
  "groq",
  "ollama",
  "deepseek",
  "xai",
] as const;
export type KnownProviderId = (typeof KNOWN_PROVIDER_IDS)[number];

/** Required prefix on custom-agent ids — mirrors the sidecar constant. */
export const CUSTOM_AGENT_ID_PREFIX = "custom:";

/** The form's controlled state. Strings throughout — coerced to typed JSON on submit. */
export interface AgentBuilderFormState {
  /** ID body — the prefix is prepended on submit, never stored in the input. */
  idBody: string;
  name: string;
  philosophy: string;
  systemPrompt: string;
  tools: Set<string>;
  defaultProvider: KnownProviderId;
  defaultModel: string;
  icon: string;
}

/** Build the empty initial state — exported for testability. */
export function emptyFormState(): AgentBuilderFormState {
  return {
    idBody: "",
    name: "",
    philosophy: "",
    systemPrompt: "",
    tools: new Set<string>(),
    defaultProvider: "anthropic",
    defaultModel: "",
    icon: "",
  };
}

/** Validation result — either a fully-formed payload or a map of field errors. */
export type ValidationResult =
  | { ok: true; payload: SubmitPayload }
  | { ok: false; errors: Record<string, string> };

/** The JSON body the form submits to `POST /custom-agents`. */
export interface SubmitPayload {
  id: string;
  name: string;
  philosophy: string;
  system_prompt: string;
  tools: string[];
  default_provider: KnownProviderId;
  default_model: string | null;
  icon: string | null;
}

/**
 * Pure validator over a form state. Used by both the panel's submit handler
 * and the unit tests (so the same code path the panel hits is the one the
 * tests exercise). Returns a typed result rather than throwing.
 */
export function validate(state: AgentBuilderFormState): ValidationResult {
  const errors: Record<string, string> = {};
  const idBody = state.idBody.trim();
  if (idBody === "") {
    errors.idBody = "ID is required.";
  } else if (!/^[a-z0-9][a-z0-9_-]*$/i.test(idBody)) {
    errors.idBody = "ID may contain only letters, digits, dashes, and underscores.";
  }
  const name = state.name.trim();
  if (name === "") {
    errors.name = "Name is required.";
  }
  const philosophy = state.philosophy.trim();
  if (philosophy === "") {
    errors.philosophy = "Philosophy is required.";
  }
  const systemPrompt = state.systemPrompt.trim();
  if (systemPrompt.length < 20) {
    errors.systemPrompt = "System prompt is too short (need at least 20 characters).";
  }
  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    payload: {
      id: `${CUSTOM_AGENT_ID_PREFIX}${idBody}`,
      name,
      philosophy,
      system_prompt: systemPrompt,
      tools: [...state.tools].filter((id): id is KnownToolId =>
        (KNOWN_TOOL_IDS as readonly string[]).includes(id),
      ),
      default_provider: state.defaultProvider,
      default_model: state.defaultModel.trim() === "" ? null : state.defaultModel.trim(),
      icon: state.icon.trim() === "" ? null : state.icon.trim(),
    },
  };
}

/**
 * Tiny custom hook that wraps the controlled-form state and exposes the
 * mutators the panel JSX uses. Lives here (not inline in the panel) so the
 * test file can render the form independently of the network/save plumbing.
 */
export function useAgentBuilderForm(initial?: Partial<AgentBuilderFormState>) {
  const [state, setState] = useState<AgentBuilderFormState>(() => ({
    ...emptyFormState(),
    ...initial,
  }));

  const setField = useCallback(
    <K extends keyof AgentBuilderFormState>(key: K, value: AgentBuilderFormState[K]) => {
      setState((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const toggleTool = useCallback((tool: KnownToolId) => {
    setState((prev) => {
      const next = new Set(prev.tools);
      if (next.has(tool)) {
        next.delete(tool);
      } else {
        next.add(tool);
      }
      return { ...prev, tools: next };
    });
  }, []);

  const reset = useCallback(() => {
    setState(emptyFormState());
  }, []);

  return { state, setField, toggleTool, reset };
}
