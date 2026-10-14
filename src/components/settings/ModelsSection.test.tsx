import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ModelsSection, engineLine, formatSize } from "@/components/settings/ModelsSection";
import { STOPPED_ENGINE, type EngineStatus } from "@/lib/local-engine";
import { useLocalEngineStore } from "@/store/local-engine";
import { useLocalModelsStore } from "@/store/local-models";
import type { CatalogModel, DownloadState, InstalledModel } from "../../../types/data";

const actions = vi.hoisted(() => ({
  refresh: vi.fn(async () => {}),
  download: vi.fn(),
  cancel: vi.fn(async () => {}),
  remove: vi.fn(async () => {}),
  activate: vi.fn(),
  deactivate: vi.fn(async () => {}),
}));

vi.mock("@/store/local-models", async () => {
  const { create } = await import("zustand");
  return {
    useLocalModelsStore: create(() => ({
      hardware: null,
      catalog: null,
      installed: [],
      ollama: { running: false, models: [] },
      downloads: {},
      activeModelId: null,
      loadError: null,
      ...actions,
    })),
  };
});

vi.mock("@/store/local-engine", async () => {
  const { create } = await import("zustand");
  return {
    useLocalEngineStore: create(() => ({
      status: {
        state: "stopped",
        port: null,
        modelId: null,
        restarts: 0,
        error: null,
        detail: null,
      },
    })),
  };
});

const GIB = 1024 ** 3;

function catalogModel(over: Partial<CatalogModel>): CatalogModel {
  return {
    id: "qwen-small",
    name: "Qwen Small",
    family: "Qwen",
    params: "4B",
    quant: "Q4",
    sizeBytes: 2.5 * GIB,
    diskNeededBytes: 3 * GIB,
    minRamBytes: 8 * GIB,
    licence: { id: "apache-2.0", name: "Apache 2.0", url: "https://example.test/apache" },
    purpose: "Quick answers on modest computers.",
    url: "https://example.test/m.gguf",
    sha256: "x",
    fits: "good",
    ...over,
  };
}

const SMALL = catalogModel({});
const BIG = catalogModel({
  id: "qwen-big",
  name: "Qwen Big",
  sizeBytes: 9 * GIB,
  diskNeededBytes: 10 * GIB,
  fits: "too-big",
  purpose: "Best answers, needs a strong computer.",
});

function installedModel(over: Partial<InstalledModel>): InstalledModel {
  return {
    id: "qwen-small",
    name: "Qwen Small",
    path: "/m/qwen-small.gguf",
    sizeBytes: 2.5 * GIB,
    verified: true,
    active: false,
    ...over,
  };
}

function dl(over: Partial<DownloadState>): DownloadState {
  return {
    id: "qwen-big",
    state: "downloading",
    receivedBytes: 3 * GIB,
    totalBytes: 9 * GIB,
    bytesPerSec: 12 * 1024 ** 2,
    error: null,
    retryable: false,
    ...over,
  };
}

function setModels(patch: Record<string, unknown>) {
  useLocalModelsStore.setState(patch as never);
}

function setEngine(status: Partial<EngineStatus>) {
  useLocalEngineStore.setState({ status: { ...STOPPED_ENGINE, ...status } } as never);
}

beforeEach(() => {
  Object.values(actions).forEach((fn) => fn.mockClear());
  setModels({
    hardware: {
      os: "macos",
      arch: "arm64",
      totalRamBytes: 16 * GIB,
      availableRamBytes: 9.5 * GIB,
      gpu: null,
      freeDiskBytes: 120 * GIB,
      modelsDir: "/m",
    },
    catalog: { models: [SMALL, BIG], recommendedId: "qwen-small", tier: "16gb", reason: "" },
    installed: [],
    ollama: { running: false, models: [] },
    downloads: {},
    activeModelId: null,
    loadError: null,
  });
  setEngine({});
});

afterEach(() => {
  cleanup();
});

describe("ModelsSection", () => {
  it("formats sizes in plain GB / MB and says what this computer has", () => {
    expect(formatSize(2.5 * GIB)).toBe("2.5 GB");
    expect(formatSize(300 * 1024 ** 2)).toBe("300 MB");
    render(<ModelsSection />);
    expect(screen.getByTestId("models-computer").textContent).toBe(
      "16.0 GB of memory (9.5 GB free) · 120.0 GB of free disk space",
    );
    expect(actions.refresh).toHaveBeenCalled();
  });

  it("shows size, disk needed and a linked licence BEFORE the Download button, plus fit and recommended", () => {
    render(<ModelsSection />);
    const row = screen.getByTestId("catalog-qwen-small");
    expect(within(row).getByText("Recommended for you")).toBeInTheDocument();
    expect(within(row).getByText("Runs well here")).toBeInTheDocument();
    expect(within(row).getByText("Quick answers on modest computers.")).toBeInTheDocument();
    const info = within(row).getByText(/2\.5 GB download · needs 3\.0 GB of free disk space/);
    const link = within(info).getByRole("link", { name: "Apache 2.0" });
    expect(link).toHaveAttribute("href", "https://example.test/apache");
    const button = within(row).getByRole("button", { name: "Download Qwen Small" });
    // Document order: the licence paragraph comes before the button.
    expect(info.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      within(screen.getByTestId("catalog-qwen-big")).queryByText("Recommended for you"),
    ).toBeNull();
    expect(screen.getByText("Too big for this computer")).toBeInTheDocument();
    // Recommended sorts first.
    const rows = screen.getAllByTestId(/^catalog-/);
    expect(rows[0]).toBe(row);
  });

  it("Download calls the store and a disk-space refusal shows its plain message", async () => {
    actions.download.mockRejectedValueOnce(
      new Error("Not enough disk space (needs 10.0 GB, 2.0 GB free)"),
    );
    render(<ModelsSection />);
    fireEvent.click(screen.getByRole("button", { name: "Download Qwen Big" }));
    expect(actions.download).toHaveBeenCalledWith("qwen-big");
    expect(await screen.findByRole("alert")).toHaveTextContent("Not enough disk space");
  });

  it("lists installed models, marks the active one and switches with Use this", async () => {
    setModels({
      installed: [
        installedModel({ id: "qwen-small", active: true }),
        installedModel({ id: "ollama:llama3", name: "llama3", sizeBytes: 4 * GIB }),
      ],
      activeModelId: "qwen-small",
    });
    actions.activate.mockResolvedValue({ ...STOPPED_ENGINE, state: "starting" });
    render(<ModelsSection />);
    const mine = screen.getByTestId("installed-qwen-small");
    expect(within(mine).getByText("In use")).toBeInTheDocument();
    expect(within(mine).queryByRole("button", { name: "Use this" })).toBeNull();
    const theirs = screen.getByTestId("installed-ollama:llama3");
    expect(within(theirs).getByText("from Ollama")).toBeInTheDocument();
    // Not removable here.
    expect(within(theirs).queryByRole("button", { name: /Remove/ })).toBeNull();
    fireEvent.click(within(theirs).getByRole("button", { name: "Use this" }));
    await waitFor(() => expect(actions.activate).toHaveBeenCalledWith("ollama:llama3"));
    fireEvent.click(within(mine).getByRole("button", { name: "Turn off" }));
    await waitFor(() => expect(actions.deactivate).toHaveBeenCalled());
  });

  it("Remove needs an in-page confirm; the active one says it stops first", async () => {
    setModels({ installed: [installedModel({ active: true })], activeModelId: "qwen-small" });
    render(<ModelsSection />);
    const row = screen.getByTestId("installed-qwen-small");
    fireEvent.click(within(row).getByRole("button", { name: "Remove Qwen Small" }));
    expect(actions.remove).not.toHaveBeenCalled();
    const confirm = within(row).getByRole("button", { name: /Confirm: this cannot be undone/ });
    expect(confirm).toHaveTextContent("Stop and remove?");
    fireEvent.click(confirm);
    await waitFor(() => expect(actions.remove).toHaveBeenCalledWith("qwen-small"));
  });

  it("shows the Ollama note only while Ollama is running", () => {
    const { rerender } = render(<ModelsSection />);
    expect(screen.queryByText(/Ollama is running/)).toBeNull();
    setModels({ ollama: { running: true, models: ["llama3"] } });
    rerender(<ModelsSection />);
    expect(
      screen.getByText("Ollama is running — its models are listed too. Vysted never needs Ollama."),
    ).toBeInTheDocument();
  });

  it("an in-flight download shows progress and Pause / Cancel; Cancel keeps the partial file", async () => {
    setModels({ downloads: { "qwen-big": dl({}) } });
    render(<ModelsSection />);
    const row = screen.getByTestId("download-qwen-big");
    expect(within(row).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "33");
    expect(row).toHaveTextContent("3.0 GB of 9.0 GB · 12 MB/s");
    // The catalog row no longer offers a second Download for it.
    expect(screen.queryByRole("button", { name: "Download Qwen Big" })).toBeNull();
    fireEvent.click(within(row).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(actions.cancel).toHaveBeenCalledWith("qwen-big"));
  });

  it("a paused download offers Resume and a confirmed Discard that deletes the partial file", async () => {
    setModels({
      downloads: {
        "qwen-big": dl({ state: "paused", error: "No internet connection", retryable: true }),
      },
    });
    actions.download.mockResolvedValue(dl({}));
    render(<ModelsSection />);
    const row = screen.getByTestId("download-qwen-big");
    expect(row).toHaveTextContent("No internet connection");
    fireEvent.click(within(row).getByRole("button", { name: "Resume" }));
    await waitFor(() => expect(actions.download).toHaveBeenCalledWith("qwen-big"));

    fireEvent.click(within(row).getByRole("button", { name: "Discard Qwen Big" }));
    expect(actions.cancel).not.toHaveBeenCalled();
    fireEvent.click(within(row).getByRole("button", { name: /Confirm: this cannot be undone/ }));
    await waitFor(() => expect(actions.cancel).toHaveBeenCalledWith("qwen-big", true));
  });

  it("Pause stops the transfer (partial kept) and the row then reads Paused", async () => {
    setModels({ downloads: { "qwen-big": dl({}) } });
    render(<ModelsSection />);
    fireEvent.click(
      within(screen.getByTestId("download-qwen-big")).getByRole("button", { name: "Pause" }),
    );
    await waitFor(() => expect(actions.cancel).toHaveBeenCalledWith("qwen-big"));
    setDownloadState("cancelled");
    await waitFor(() =>
      expect(screen.getByTestId("download-qwen-big")).toHaveTextContent("Paused"),
    );
    expect(screen.getByRole("button", { name: "Resume" })).toBeInTheDocument();
  });

  it("the engine status line speaks plainly for every state", () => {
    expect(engineLine(STOPPED_ENGINE, null).text).toBe("No model is running right now.");
    expect(engineLine({ ...STOPPED_ENGINE, state: "starting" }, null).text).toMatch(
      /Starting the model/,
    );
    expect(engineLine({ ...STOPPED_ENGINE, state: "ready", port: 1 }, "Qwen Small").text).toBe(
      "Running on this computer: Qwen Small.",
    );
    expect(
      engineLine(
        { ...STOPPED_ENGINE, state: "failed", error: "Not enough memory to load this model" },
        null,
      ),
    ).toEqual({ text: "Not enough memory to load this model", tone: "bad" });
    expect(engineLine({ ...STOPPED_ENGINE, state: "crashed", error: null }, null).text).toBe(
      "The model stopped unexpectedly. Trying again…",
    );
  });

  it("a failed engine shows its reason and Try again re-activates the chosen model", async () => {
    setModels({ installed: [installedModel({})], activeModelId: "qwen-small" });
    setEngine({ state: "failed", error: "Not enough memory to load this model" });
    actions.activate.mockResolvedValue(STOPPED_ENGINE);
    render(<ModelsSection />);
    expect(screen.getByTestId("models-engine-line")).toHaveTextContent(
      "Not enough memory to load this model",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(actions.activate).toHaveBeenCalledWith("qwen-small"));
  });

  it("surfaces the store's load error in plain words", () => {
    setModels({ loadError: "Vysted is still starting. Try again in a moment." });
    render(<ModelsSection />);
    expect(screen.getByTestId("models-load-error")).toHaveTextContent("still starting");
  });
});

function setDownloadState(state: DownloadState["state"]) {
  setModels({ downloads: { "qwen-big": dl({ state }) } });
}
