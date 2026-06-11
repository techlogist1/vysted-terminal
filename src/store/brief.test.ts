import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The store self-persists via `autosaveLayout`. Mock it so a setter call in a
// unit test (no dockview) is observable and never touches the network.
vi.mock("@/lib/workspace", () => ({
  autosaveLayout: vi.fn(() => Promise.resolve()),
}));

import { autosaveLayout } from "@/lib/workspace";
import { briefBundle, resetBriefStoreForTests, useBriefStore } from "@/store/brief";
import type { ResearchBriefData } from "../../types/brief";

const autosaveMock = vi.mocked(autosaveLayout);

function sampleBrief(overrides: Partial<ResearchBriefData> = {}): ResearchBriefData {
  return {
    query: "What is Apple's moat?",
    symbol: "AAPL",
    mode: "DEEP",
    markdown: "Apple's moat is its ecosystem [1] and brand [2].",
    sources: [
      { url: "https://sec.gov/aapl", title: "10-K", excerpt: "Risk factors…", domain: "sec.gov" },
      { url: "https://example.com/brand", title: "Brand study", excerpt: "Loyalty…" },
    ],
    sourceCount: 2,
    cost: { tokens: 12400, spendUsd: 0.03 },
    webAvailable: true,
    steps: [{ kind: "plan", detail: "Decompose the query", latencyMs: 120, status: "ok" }],
    createdAt: 1_700_000_000_000,
    ...overrides,
  };
}

describe("brief store", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    autosaveMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("starts with no brief", () => {
    expect(useBriefStore.getState().brief).toBeNull();
    expect(briefBundle()).toBeNull();
  });

  it("setBrief stores the brief and triggers persistence", () => {
    const brief = sampleBrief();
    useBriefStore.getState().setBrief(brief);

    expect(useBriefStore.getState().brief).toEqual(brief);
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("setBrief replaces a prior brief (latest run wins)", () => {
    useBriefStore.getState().setBrief(sampleBrief({ query: "first" }));
    useBriefStore.getState().setBrief(sampleBrief({ query: "second" }));

    expect(useBriefStore.getState().brief?.query).toBe("second");
    expect(autosaveMock).toHaveBeenCalledTimes(2);
  });

  it("clearBrief resets to empty and triggers persistence", () => {
    useBriefStore.getState().setBrief(sampleBrief());
    autosaveMock.mockClear();

    useBriefStore.getState().clearBrief();

    expect(useBriefStore.getState().brief).toBeNull();
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("toBundle / briefBundle snapshot the persistence shape", () => {
    const brief = sampleBrief();
    useBriefStore.getState().setBrief(brief);

    expect(briefBundle()).toEqual(brief);
    expect(useBriefStore.getState().toBundle()).toEqual(brief);
  });

  it("fromBundle round-trips a serialised brief and triggers persistence", () => {
    const brief = sampleBrief();
    const bundle = brief; // what would ride SerializedWorkspace.brief

    useBriefStore.getState().fromBundle(bundle);

    expect(useBriefStore.getState().brief).toEqual(brief);
    expect(briefBundle()).toEqual(bundle);
    expect(autosaveMock).toHaveBeenCalledTimes(1);
  });

  it("fromBundle(null) restores the empty state", () => {
    useBriefStore.getState().setBrief(sampleBrief());

    useBriefStore.getState().fromBundle(null);

    expect(useBriefStore.getState().brief).toBeNull();
  });

  it("fromBundle rejects a garbled/partial bundle by restoring to empty", () => {
    useBriefStore.getState().setBrief(sampleBrief());

    // Missing the load-bearing markdown/sources fields — must not half-populate.
    useBriefStore.getState().fromBundle({ query: "broken" } as unknown as ResearchBriefData);

    expect(useBriefStore.getState().brief).toBeNull();
  });

  it("persists a webAvailable=false brief faithfully (honest no-web state)", () => {
    const brief = sampleBrief({
      webAvailable: false,
      note: "No web-search backend configured.",
      sources: [],
      sourceCount: 0,
      cost: undefined,
    });
    useBriefStore.getState().setBrief(brief);

    const round = briefBundle();
    expect(round?.webAvailable).toBe(false);
    expect(round?.note).toBe("No web-search backend configured.");
    expect(round).toEqual(brief);
  });

  it("round-trips the transient webReason so the banner picks honest copy (WS3)", () => {
    // A transient throttle: webAvailable false BUT the reason is rate_limited, so
    // the panel shows "rate-limited, retrying" — never the false "no backend".
    const brief = sampleBrief({
      webAvailable: false,
      webReason: "rate_limited",
      note: "Web search was rate-limited — retry in a moment",
      sources: [],
      sourceCount: 0,
      cost: undefined,
    });
    useBriefStore.getState().setBrief(brief);

    const round = briefBundle();
    expect(round?.webReason).toBe("rate_limited");
    expect(round?.webAvailable).toBe(false);
    expect(round).toEqual(brief);

    // Survives a full serialize → restore cycle (rides the workspace blob).
    useBriefStore.getState().fromBundle(round);
    expect(useBriefStore.getState().brief?.webReason).toBe("rate_limited");
  });
});

// ── lifecycle state machine (R10, D39) ──────────────────────────────────────

describe("brief lifecycle state machine (R10 D39)", () => {
  beforeEach(() => {
    resetBriefStoreForTests();
    autosaveMock.mockClear();
  });

  function published(overrides: Partial<ResearchBriefData> = {}): ResearchBriefData {
    return sampleBrief({
      execution: { runId: "run-1", requestedDepth: "deep", loop: "iter" },
      ...overrides,
    });
  }

  it("starts empty", () => {
    expect(useBriefStore.getState().panel).toEqual({ phase: "empty" });
  });

  it("beginRun → in_flight, carrying the published brief as prior", () => {
    useBriefStore.getState().publish(published());
    useBriefStore.getState().beginRun({ runId: "run-2", query: "go deeper", depth: "heavy" });
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("in_flight");
    if (panel.phase === "in_flight") {
      expect(panel.runId).toBe("run-2");
      expect(panel.depth).toBe("heavy");
      expect(panel.prior?.query).toBe(sampleBrief().query);
    }
    // The legacy mirror keeps serving the prior so unrelated surfaces render.
    expect(useBriefStore.getState().brief?.query).toBe(sampleBrief().query);
  });

  it("a publish matching the in-flight run publishes; a mismatched one is stale", () => {
    useBriefStore.getState().beginRun({ runId: "run-2", query: "q", depth: "deep" });
    const stale = useBriefStore
      .getState()
      .publish(published({ execution: { runId: "run-OLD", requestedDepth: "deep", loop: "iter" } }));
    expect(stale).toBe("stale_run");
    expect(useBriefStore.getState().panel.phase).toBe("in_flight");

    const ok = useBriefStore
      .getState()
      .publish(published({ execution: { runId: "run-2", requestedDepth: "deep", loop: "iter" } }));
    expect(ok).toBe("published");
    expect(useBriefStore.getState().panel.phase).toBe("published");
  });

  it("a record-less publish while a run is in flight never replaces the live run", () => {
    useBriefStore.getState().beginRun({ runId: "run-2", query: "q", depth: "deep" });
    const result = useBriefStore.getState().publish(sampleBrief());
    expect(result).toBe("stale_run");
    expect(useBriefStore.getState().panel.phase).toBe("in_flight");
  });

  it("failRun restores the prior as archived(run_failed), or empties", () => {
    useBriefStore.getState().publish(published());
    useBriefStore.getState().beginRun({ runId: "run-2", query: "q", depth: "deep" });
    useBriefStore.getState().failRun();
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("archived");
    if (panel.phase === "archived") {
      expect(panel.reason).toBe("run_failed");
      expect(panel.brief.query).toBe(sampleBrief().query);
    }

    resetBriefStoreForTests();
    useBriefStore.getState().beginRun({ runId: "run-3", query: "q", depth: "quick" });
    useBriefStore.getState().failRun();
    expect(useBriefStore.getState().panel).toEqual({ phase: "empty" });
  });

  it("the watchdog archives a run older than its depth wall + slack", () => {
    useBriefStore.getState().publish(published());
    useBriefStore.getState().beginRun({ runId: "run-2", query: "q", depth: "deep" });
    // Inside the budget — nothing settles.
    useBriefStore.getState().watchdogTick(Date.now() + 60_000);
    expect(useBriefStore.getState().panel.phase).toBe("in_flight");
    // Past the 120s iter wall + 60s slack — the run is dead, the prior returns.
    useBriefStore.getState().watchdogTick(Date.now() + 181_000);
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("archived");
    if (panel.phase === "archived") {
      expect(panel.reason).toBe("run_failed");
    }
  });

  it("appendRunStep feeds the in-flight trace and no-ops outside a run", () => {
    useBriefStore
      .getState()
      .appendRunStep({ kind: "search", detail: "ignored — no run", status: "ok" });
    expect(useBriefStore.getState().panel.phase).toBe("empty");

    useBriefStore.getState().beginRun({ runId: "run-2", query: "q", depth: "deep" });
    useBriefStore.getState().appendRunStep({ kind: "search", detail: "web round", status: "ok" });
    const panel = useBriefStore.getState().panel;
    expect(panel.phase === "in_flight" && panel.steps).toEqual([
      { kind: "search", detail: "web round", status: "ok" },
    ]);
  });

  it("fromBundle ALWAYS lands archived('restored') — a reboot never serves current", () => {
    useBriefStore.getState().fromBundle(published());
    const panel = useBriefStore.getState().panel;
    expect(panel.phase).toBe("archived");
    if (panel.phase === "archived") {
      expect(panel.reason).toBe("restored");
    }
    // The mirror + bundle still round-trip the plain brief shape.
    expect(useBriefStore.getState().brief?.query).toBe(sampleBrief().query);
  });

  it("a re-begin while in flight keeps the ORIGINAL prior (abandoned runs carry nothing)", () => {
    useBriefStore.getState().publish(published());
    useBriefStore.getState().beginRun({ runId: "run-2", query: "q2", depth: "deep" });
    useBriefStore.getState().beginRun({ runId: "run-3", query: "q3", depth: "heavy" });
    const panel = useBriefStore.getState().panel;
    expect(panel.phase === "in_flight" && panel.runId).toBe("run-3");
    expect(panel.phase === "in_flight" && panel.prior?.query).toBe(sampleBrief().query);
    useBriefStore.getState().failRun();
    expect(useBriefStore.getState().brief?.query).toBe(sampleBrief().query);
  });
});
