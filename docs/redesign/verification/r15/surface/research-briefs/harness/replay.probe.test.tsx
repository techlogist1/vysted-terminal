// Replays a LIVE sidecar SSE transcript (jsonl) through the frontend's real streaming
// normalizer + brief lifecycle + publish_brief host action, then renders BriefPanel and
// dumps what the user would see. Scratch-only probe (never in src/).
import { cleanup, render } from "@testing-library/react";
import { readFileSync, writeFileSync } from "fs";
import { afterEach, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn(async () => null) }));
vi.mock("@/lib/sidecar-client", async (orig) => ({
  ...(await orig<Record<string, unknown>>()),
  getSidecarBaseUrl: async () => "http://127.0.0.1:1",
}));
vi.mock("@/lib/search-headers", () => ({ buildSearchHeaders: async () => ({}) }));

import { streamAgentInvocation } from "@/modules/chat/streaming";
import { applyHostAction } from "@/lib/host-actions";
import { useBriefStore, resetBriefStoreForTests } from "@/store/brief";
import { BriefPanel } from "@/modules/research/BriefPanel";
import { dedupeSources, sanitizeCitationMarkers } from "@/lib/brief-ingest";
import { deriveMetrics } from "@/modules/research/brief-blocks";

afterEach(() => cleanup());

const files = (process.env.REPLAY ?? "").split(",").filter(Boolean);
const outPath = process.env.REPLAY_OUT ?? "/dev/null";
const results: Record<string, unknown> = {};

for (const file of files) {
  it(`replay ${file}`, async () => {
    resetBriefStoreForTests();
    const lines = readFileSync(file, "utf8").split("\n").filter((l) => l.trim());
    const frames = lines
      .map((l) => JSON.parse(l))
      .filter((e) => e && typeof e === "object" && "kind" in e)
      .map((e) => `data: ${JSON.stringify(e)}\n\n`)
      .join("");
    globalThis.fetch = vi.fn(async () =>
      new Response(new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode(frames)); c.close(); } }), { status: 200, headers: { "Content-Type": "text/event-stream" } }),
    ) as unknown as typeof fetch;
    const applied: Array<{ name: string; label: string | null; phaseAfter: string }> = [];
    const errors: string[] = [];
    const notices: string[] = [];
    let published = false;
    await streamAgentInvocation(
      "copilot",
      { prompt: "replay", provider: "ollama", model: "x" } as never,
      {
        onEvent: (ev) => {
          if (ev.kind === "tool_use" && ev.name === "publish_brief") {
            const label = applyHostAction("publish_brief", ev.input as Record<string, unknown>);
            published = true;
            applied.push({ name: ev.name, label, phaseAfter: useBriefStore.getState().panel.phase });
          } else if (ev.kind === "error") {
            errors.push(ev.message);
          } else if (ev.kind === "research_step" && ev.stepKind === "engine" && !ev.detail.startsWith("research:begin")) {
            notices.push(ev.detail);
          } else if (ev.kind === "done") {
            if (useBriefStore.getState().panel.phase === "in_flight" && !published) {
              useBriefStore.getState().failRun();
            }
          }
        },
        onError: (e) => errors.push(`transport: ${e.message}`),
      },
    );
    const st = useBriefStore.getState();
    const brief = st.brief;
    const { container } = render(<BriefPanel />);
    const md = brief?.markdown ?? "";
    const markers = [...md.matchAll(/\[(\d{1,3})\](?!\()/g)].map((m) => Number(m[1]));
    results[file] = {
      phase: st.panel.phase,
      applied,
      errors,
      engineNotices: notices,
      brief: brief
        ? {
            symbol: brief.symbol,
            depth: brief.depth,
            mode: brief.mode,
            backend: brief.backend,
            webAvailable: brief.webAvailable,
            webReason: brief.webReason,
            note: brief.note,
            sourceCount: brief.sourceCount,
            sourcesStored: brief.sources.length,
            sourcesRendered: dedupeSources(brief.sources).length,
            markdownLen: md.length,
            markersInBody: markers,
            maxMarker: markers.length ? Math.max(...markers) : 0,
            markersAfterSanitize: [...sanitizeCitationMarkers(md, dedupeSources(brief.sources).length).matchAll(/\[(\d{1,3})\](?!\()/g)].length,
            execution: brief.execution,
            metrics: deriveMetrics(brief.structured),
          }
        : null,
      anchors: [...container.querySelectorAll("a")].map((a) => a.getAttribute("href")),
      renderedText: (container.textContent ?? "").replace(/\s+/g, " ").slice(0, 6000),
    };
    writeFileSync(outPath, JSON.stringify(results, null, 1));
  });
}
