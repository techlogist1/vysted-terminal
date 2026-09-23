import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { useAgentsStore } from "@/store/agents";

import { AgentBuilderPanel } from "./AgentBuilderPanel";
import {
  CUSTOM_AGENT_ID_PREFIX,
  emptyFormState,
  KNOWN_PROVIDER_IDS,
  KNOWN_TOOL_IDS,
  validate,
  type AgentBuilderFormState,
} from "./form";

// --- mocks ----------------------------------------------------------------
// `getSidecarBaseUrl` reaches into the Tauri runtime — stub it so the panel
// just sees a fixed URL.
vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999"),
  };
});

// Global `fetch` mock — each test seeds the responses it expects.
const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  // Default: empty list response on every GET /custom-agents — overrides
  // per test as needed.
  fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
    const url = input.toString();
    if (url.endsWith("/custom-agents/tool-ids")) {
      return new Response(JSON.stringify([...KNOWN_TOOL_IDS]), { status: 200 });
    }
    if (
      url.includes("/custom-agents") &&
      (url.endsWith("/custom-agents") || url.endsWith("custom-agents"))
    ) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response("{}", { status: 200 });
  });
  useAgentsStore.setState({
    firstPartyAgents: [],
    customAgents: [],
    customSummaries: [],
    firstPartyStatus: "idle",
    firstPartyError: null,
    customStatus: "idle",
    customError: null,
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// --- validate() unit tests ------------------------------------------------

function fillState(overrides: Partial<AgentBuilderFormState> = {}): AgentBuilderFormState {
  return {
    ...emptyFormState(),
    idBody: "macro-quant",
    name: "Macro Quant",
    philosophy: "Mean reversion across asset classes.",
    systemPrompt: "You are a macro quant analyst answering with regime first.",
    defaultProvider: "anthropic",
    ...overrides,
  };
}

describe("validate()", () => {
  it("returns ok with a fully-formed payload on a valid form", () => {
    const result = validate(fillState({ tools: new Set(["price_data", "macro_series"]) }));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.id).toBe(`${CUSTOM_AGENT_ID_PREFIX}macro-quant`);
      expect(result.payload.tools).toEqual(["price_data", "macro_series"]);
      expect(result.payload.default_provider).toBe("anthropic");
    }
  });

  it("rejects an empty id body", () => {
    const result = validate(fillState({ idBody: "" }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.idBody).toBeDefined();
    }
  });

  it("rejects an id body with invalid characters", () => {
    const result = validate(fillState({ idBody: "has space" }));
    expect(result.ok).toBe(false);
  });

  it("rejects a short system prompt", () => {
    const result = validate(fillState({ systemPrompt: "too short" }));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.systemPrompt).toBeDefined();
    }
  });

  it("R15-UI-003: payload keeps every selected tool, not just the fallback allow-list", () => {
    // The OLD behaviour filtered against the static fallback array, which
    // silently dropped any tool id the array didn't happen to list — the
    // defect this batch fixes. The sidecar's own POST/PUT route is the one
    // place that validates tool ids now (against the LIVE catalog).
    const state = fillState({ tools: new Set(["price_data", "openrouter_only_tool"]) });
    const result = validate(state);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.tools).toEqual(
        expect.arrayContaining(["price_data", "openrouter_only_tool"]),
      );
    }
  });

  it("nullifies blank optional fields", () => {
    const result = validate(fillState({ defaultModel: "  ", icon: "" }));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.payload.default_model).toBeNull();
      expect(result.payload.icon).toBeNull();
    }
  });
});

// --- panel render tests ---------------------------------------------------

describe("AgentBuilderPanel", () => {
  it("renders the form with the custom: prefix label and known tools", async () => {
    render(<AgentBuilderPanel />);
    await screen.findByText("New custom agent");
    expect(screen.getByText(CUSTOM_AGENT_ID_PREFIX)).toBeInTheDocument();
    for (const tool of KNOWN_TOOL_IDS) {
      expect(screen.getByRole("button", { name: tool })).toBeInTheDocument();
    }
    // R15-UI-003: the provider dropdown reads the LIVE catalog
    // (`useLLMProvidersStore`, `DEFAULT_PROVIDERS` fallback) — which, unlike
    // the old static `KNOWN_PROVIDER_IDS` array, also carries "openrouter".
    const select = screen.getByLabelText("Default provider") as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toEqual([...KNOWN_PROVIDER_IDS, "openrouter"]);
  });

  it("surfaces field errors when submitted empty", async () => {
    render(<AgentBuilderPanel />);
    await screen.findByText("New custom agent");
    const submit = screen.getByRole("button", { name: "Create agent" });
    expect(submit).toBeDisabled();
    // Fill enough to enable the button — but leave system prompt too short.
    fireEvent.change(screen.getByLabelText("Agent ID"), { target: { value: "tinybrain" } });
    fireEvent.change(screen.getByLabelText("Agent name"), { target: { value: "Tiny" } });
    fireEvent.change(screen.getByLabelText("Philosophy"), { target: { value: "Short." } });
    fireEvent.change(screen.getByLabelText("System prompt"), { target: { value: "tiny" } });
    // Button stays disabled because validation still fails.
    expect(submit).toBeDisabled();
  });

  it("POSTs the payload and refreshes the list on save", async () => {
    fetchMock.mockImplementationOnce(async () => {
      return new Response(JSON.stringify([]), { status: 200 });
    });
    render(<AgentBuilderPanel />);
    await screen.findByText("New custom agent");

    // Fill a valid form.
    fireEvent.change(screen.getByLabelText("Agent ID"), { target: { value: "macro-quant" } });
    fireEvent.change(screen.getByLabelText("Agent name"), { target: { value: "Macro Quant" } });
    fireEvent.change(screen.getByLabelText("Philosophy"), {
      target: { value: "Macro regimes drive asset returns." },
    });
    fireEvent.change(screen.getByLabelText("System prompt"), {
      target: {
        value: "You are a macro quant analyst. Reason regime-first; cite drawdown statistics.",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "price_data" }));

    // Capture the POST call.
    fetchMock.mockReset();
    fetchMock.mockImplementation(async (_input, init) => {
      if (init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        expect(body.id).toBe("custom:macro-quant");
        expect(body.tools).toEqual(["price_data"]);
        return new Response(
          JSON.stringify({ id: body.id, ...body, created_at: 1, updated_at: 1 }),
          {
            status: 201,
          },
        );
      }
      // The refreshCustom() call after save.
      return new Response(
        JSON.stringify([
          {
            id: "custom:macro-quant",
            name: "Macro Quant",
            philosophy: "Macro regimes drive asset returns.",
            system_prompt: "x".repeat(40),
            tools: ["price_data"],
            default_provider: "anthropic",
            default_model: null,
            icon: null,
            created_at: 1,
            updated_at: 1,
          },
        ]),
        { status: 200 },
      );
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Create agent" }));
    });

    await waitFor(() => {
      expect(useAgentsStore.getState().customAgents).toHaveLength(1);
    });
    expect(useAgentsStore.getState().customAgents[0]?.id).toBe("custom:macro-quant");
  });

  it("renders existing custom agents in the side list and supports edit", async () => {
    // Override the default empty-list mock so the mount-time refreshCustom()
    // fetches our seeded agent.
    fetchMock.mockImplementation(
      async () =>
        new Response(
          JSON.stringify([
            {
              id: "custom:macro-quant",
              name: "Macro Quant",
              philosophy: "Mean reversion.",
              system_prompt: "x".repeat(40),
              tools: ["macro"],
              default_provider: "anthropic",
              default_model: null,
              icon: null,
              created_at: 1,
              updated_at: 1,
            },
          ]),
          { status: 200 },
        ),
    );
    render(<AgentBuilderPanel />);
    await screen.findByText("Macro Quant");
    // Click the agent → form switches to "Edit" mode.
    fireEvent.click(screen.getByText("Macro Quant"));
    expect(await screen.findByText("Edit custom agent")).toBeInTheDocument();
    // The id input is filled with the body (no prefix) and disabled.
    const idInput = screen.getByLabelText("Agent ID") as HTMLInputElement;
    expect(idInput.value).toBe("macro-quant");
    expect(idInput).toBeDisabled();
  });

  it("R15-UI-003: edit and save round-trips a tool set + provider the fallback arrays don't list", async () => {
    // "research"/"web_search" aren't in the static KNOWN_TOOL_IDS fallback,
    // and "openrouter" isn't in KNOWN_PROVIDER_IDS — the exact shape of the
    // old defect (both got silently stripped/reset on edit). The builder
    // renders from the MOCKED live responses here, not the constants.
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/custom-agents/tool-ids")) {
        return new Response(JSON.stringify(["research", "web_search"]), { status: 200 });
      }
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as {
          tools: string[];
          default_provider: string;
        };
        expect(body.tools).toEqual(expect.arrayContaining(["research", "web_search"]));
        expect(body.default_provider).toBe("openrouter");
        return new Response(
          JSON.stringify({ id: "custom:macro-quant", ...body, created_at: 1, updated_at: 2 }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify([
          {
            id: "custom:macro-quant",
            name: "Macro Quant",
            philosophy: "Mean reversion.",
            system_prompt: "x".repeat(40),
            tools: ["research", "web_search"],
            default_provider: "openrouter",
            default_model: null,
            icon: null,
            created_at: 1,
            updated_at: 1,
          },
        ]),
        { status: 200 },
      );
    });

    render(<AgentBuilderPanel />);
    await screen.findByText("Macro Quant");
    fireEvent.click(screen.getByText("Macro Quant"));
    await screen.findByText("Edit custom agent");

    // Neither tool was stripped on load into the form...
    expect(screen.getByRole("button", { name: "research" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "web_search" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    // ...and the provider select shows "openrouter", not a reset "anthropic".
    const select = screen.getByLabelText("Default provider") as HTMLSelectElement;
    expect(select.value).toBe("openrouter");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    });
    await waitFor(() => expect(screen.queryByText("Updated.")).toBeInTheDocument());
  });

  it("case not written against: a tool id the sidecar lists but the fallback array lacks is selectable", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/custom-agents/tool-ids")) {
        return new Response(JSON.stringify(["brand_new_tool"]), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });
    render(<AgentBuilderPanel />);
    await screen.findByText("New custom agent");

    const button = await screen.findByRole("button", { name: "brand_new_tool" });
    expect(button).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
  });
});
