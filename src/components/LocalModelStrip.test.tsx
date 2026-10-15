import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LocalModelStrip } from "@/components/LocalModelStrip";
import { EXAMPLE_QUESTION } from "@/components/onboarding/example";
import { STOPPED_ENGINE, type EngineStatus } from "@/lib/local-engine";
import { useAgentCommandStore } from "@/store/agent-command";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore } from "@/store/local-models";
import { useOnboardingStore } from "@/store/onboarding";
import type { DownloadState } from "../../types/data";

vi.mock("@/lib/host-actions", () => ({ loadSymbolIntoChart: vi.fn() }));

const MB = 1024 ** 2;
const actions = { download: vi.fn(), cancel: vi.fn(), activate: vi.fn() };

const dl = (over: Partial<DownloadState>): DownloadState => ({
  id: "qwen",
  state: "downloading",
  receivedBytes: 420 * MB,
  totalBytes: 1000 * MB,
  bytesPerSec: 10 * MB,
  error: null,
  retryable: true,
  ...over,
});

function engine(over: Partial<EngineStatus>) {
  useLocalEngineStore.setState({ status: { ...STOPPED_ENGINE, ...over } });
}

const strip = () => screen.getByRole("status", { name: "On-computer model" });

beforeEach(() => {
  for (const fn of Object.values(actions)) fn.mockReset().mockResolvedValue(undefined);
  useLocalModelsStore.setState({
    downloads: {},
    installed: [],
    activeModelId: null,
    catalog: {
      models: [{ id: "qwen", name: "Qwen 3 8B" } as never],
      recommendedId: "qwen",
      tier: "16gb",
      reason: "",
    },
    ...actions,
  });
  useLocalEngineStore.setState({ status: STOPPED_ENGINE });
  useOnboardingStore.setState({ forceOpen: false, forceStep: null, waitingQuestion: null });
  useAgentCommandStore.setState({ command: null });
});

afterEach(cleanup);

describe("LocalModelStrip", () => {
  it("is hidden when nothing is happening", () => {
    render(<LocalModelStrip />);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows download progress with percent, speed, time left and Pause", () => {
    useLocalModelsStore.setState({ downloads: { qwen: dl({}) } });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent(
      "Downloading Qwen 3 8B — 42% · 10 MB/s · less than a minute left",
    );
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42");
    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(actions.cancel).toHaveBeenCalledWith("qwen");
  });

  it("a paused download shows the percent, the plain reason and Resume", () => {
    useLocalModelsStore.setState({
      downloads: {
        qwen: dl({
          state: "paused",
          bytesPerSec: null,
          error: "Download was interrupted — resume to continue",
        }),
      },
    });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent(
      "paused at 42%. Download was interrupted — resume to continue.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Resume" }));
    expect(actions.download).toHaveBeenCalledWith("qwen");
  });

  it("a download the user paused offers Resume, and can be cancelled outright", () => {
    useLocalModelsStore.setState({ downloads: { qwen: dl({ state: "cancelled" }) } });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent("paused at 42%");
    fireEvent.click(screen.getByRole("button", { name: "Cancel download" }));
    expect(actions.cancel).toHaveBeenCalledWith("qwen", true);
  });

  it("a failed download (no internet) offers Try again and Use my own key", () => {
    useLocalModelsStore.setState({
      downloads: { qwen: dl({ state: "failed", error: "No internet connection" }) },
    });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent("stopped. No internet connection.");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(actions.download).toHaveBeenCalledWith("qwen");
    fireEvent.click(screen.getByRole("button", { name: "Use my own key" }));
    expect(useOnboardingStore.getState()).toMatchObject({ forceOpen: true, forceStep: "key" });
  });

  it("a non-retryable failed download still offers Try again, Use my own key and Cancel", () => {
    useLocalModelsStore.setState({
      downloads: {
        qwen: dl({
          state: "failed",
          retryable: false,
          error: "The download link stopped working — try again later",
        }),
      },
    });
    render(<LocalModelStrip />);
    expect(screen.getByRole("button", { name: "Use my own key" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel download" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(actions.download).toHaveBeenCalledWith("qwen");
  });

  it("says the model is starting", () => {
    engine({ state: "starting", modelId: "qwen" });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent("Starting the on-computer model…");
  });

  it("says a crashed model is restarting", () => {
    engine({ state: "crashed", modelId: "qwen", restarts: 1 });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent(/restarting/);
  });

  it("a failed model gives the reason and every next step", () => {
    useLocalModelsStore.setState({ activeModelId: "qwen" });
    engine({ state: "failed", modelId: "qwen", error: "Not enough memory to load it." });
    render(<LocalModelStrip />);
    expect(strip()).toHaveTextContent("couldn't start. Not enough memory to load it.");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(actions.activate).toHaveBeenCalledWith("qwen");
    fireEvent.click(screen.getByRole("button", { name: "Use a smaller model" }));
    expect(useOnboardingStore.getState().forceStep).toBe("local");
    fireEvent.click(screen.getByRole("button", { name: "Use my own key" }));
    expect(useOnboardingStore.getState().forceStep).toBe("key");
  });

  it("tells you when the model is ready and sends the waiting question", () => {
    useOnboardingStore.setState({ waitingQuestion: EXAMPLE_QUESTION });
    engine({ state: "starting", modelId: "qwen" });
    render(<LocalModelStrip />);
    act(() => engine({ state: "ready", port: 4000, modelId: "qwen" }));
    expect(strip()).toHaveTextContent("Your on-computer model is ready.");
    fireEvent.click(screen.getByRole("button", { name: /Ask:/ }));
    expect(useAgentCommandStore.getState().command?.prompt).toBe(EXAMPLE_QUESTION);
    expect(useOnboardingStore.getState().waitingQuestion).toBeNull();
  });

  it("a ready model with no waiting question stays quiet", () => {
    engine({ state: "ready", port: 4000, modelId: "qwen" });
    render(<LocalModelStrip />);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
