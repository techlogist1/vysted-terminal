import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BriefBody } from "@/modules/research/brief-blocks";
import type { ResearchBriefData } from "../../../types/brief";

const brief: ResearchBriefData = {
  query: "Is AAPL cheap?",
  mode: "FAST",
  markdown: [
    "## Take",
    "",
    "A long paragraph of reading prose that would otherwise run the full width.",
    "",
    "- a list point",
    "",
    "| Metric | Value |",
    "| --- | --- |",
    "| P/E | 31.5 |",
  ].join("\n"),
  sources: [],
  sourceCount: 0,
  webAvailable: false,
  createdAt: Date.UTC(2026, 8, 24),
};

describe("BriefBody reading measure (R15-UI-074)", () => {
  it("caps heading, prose and list blocks at max-w-prose but lets a table use the panel width", () => {
    const { container } = render(<BriefBody brief={brief} onCite={() => {}} />);
    const capped = (el: Element | null) => {
      expect(el).not.toBeNull();
      return el?.closest(".max-w-prose") ?? null;
    };
    expect(capped(screen.getByText("Take"))).not.toBeNull();
    expect(capped(screen.getByText(/A long paragraph of reading prose/))).not.toBeNull();
    expect(capped(container.querySelector("ul, ol"))).not.toBeNull();
    expect(capped(container.querySelector("table"))).toBeNull();
  });
});
