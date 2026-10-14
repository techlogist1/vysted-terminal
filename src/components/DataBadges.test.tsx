import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProvenanceBadge, StalenessBadge } from "./DataBadges";

describe("ProvenanceBadge", () => {
  it("renders the provider label in the neutral tone", () => {
    render(<ProvenanceBadge provider="NewsAPI" />);
    const badge = screen.getByTestId("provenance-badge");
    expect(badge).toHaveTextContent("NewsAPI");
    expect(badge.className).toContain("text-charcoal-300");
    expect(badge.className).not.toContain("text-warning");
  });

  it("composes prefix · provider when a prefix is supplied", () => {
    render(<ProvenanceBadge provider="rss" prefix="EOD" />);
    // `rss` renders its designed short form (R8 §3.1 — formatter, not CSS clip).
    expect(screen.getByTestId("provenance-badge")).toHaveTextContent("EOD · RSS");
  });

  it("renders the designed short form for a long provider id, full id in the tooltip", () => {
    render(<ProvenanceBadge provider="yfinance" />);
    const badge = screen.getByTestId("provenance-badge");
    // The live D3 defect: "yfinance" mid-word clipped to "YFINAN" at narrow widths.
    expect(badge).toHaveTextContent("YF");
    expect(badge).toHaveAttribute("title", "Source: yfinance");
  });

  it("re-colours and re-labels a synthetic value as caution", () => {
    render(<ProvenanceBadge provider="kite" prefix="PAPER" synthetic />);
    const badge = screen.getByTestId("provenance-badge");
    expect(badge).toHaveTextContent("PAPER · synthetic");
    expect(badge.className).toContain("text-warning");
  });

  it("states synthetic in visible text without a prefix, never colour alone (R15-UI-067)", () => {
    render(<ProvenanceBadge provider="kite" synthetic />);
    const badge = screen.getByTestId("provenance-badge");
    expect(badge).toHaveTextContent("synthetic");
    expect(badge.getAttribute("title")).toContain("kite");
  });
});

describe("StalenessBadge", () => {
  it("renders a live badge in the positive tone", () => {
    render(<StalenessBadge freshness="live" />);
    const badge = screen.getByTestId("staleness-badge");
    expect(badge).toHaveTextContent("live");
    expect(badge.className).toContain("text-positive");
  });

  it("renders a stale badge in the caution tone", () => {
    render(<StalenessBadge freshness="stale" />);
    const badge = screen.getByTestId("staleness-badge");
    expect(badge).toHaveTextContent("stale");
    expect(badge.className).toContain("text-warning");
  });

  it("renders unknown as a caution badge, never live", () => {
    render(<StalenessBadge freshness="unknown" />);
    const badge = screen.getByTestId("staleness-badge");
    expect(badge).toHaveTextContent("age unknown");
    expect(badge.className).toContain("text-warning");
  });

  it("formats an EOD readout as an ISO as-of date from epoch ms", () => {
    // 2026-01-15T12:00:00Z
    const epoch = Date.UTC(2026, 0, 15, 12, 0, 0);
    render(<StalenessBadge freshness="eod" asOf={epoch} />);
    expect(screen.getByTestId("staleness-badge")).toHaveTextContent("EOD as of 2026-01-15");
  });

  it("dates EOD in the viewer's local calendar across IST midnight (R15-UI-067)", () => {
    const prevTz = process.env.TZ;
    process.env.TZ = "Asia/Kolkata";
    try {
      // 01:30 IST on the 24th is still the 23rd in UTC — the old UTC slice read a day early.
      render(<StalenessBadge freshness="eod" asOf={Date.parse("2026-09-24T01:30:00+05:30")} />);
      expect(screen.getByTestId("staleness-badge")).toHaveTextContent("EOD as of 2026-09-24");
    } finally {
      if (prevTz === undefined) {
        delete process.env.TZ;
      } else {
        process.env.TZ = prevTz;
      }
    }
  });

  it("degrades to a bare EOD label when no timestamp is given", () => {
    render(<StalenessBadge freshness="eod" />);
    expect(screen.getByTestId("staleness-badge")).toHaveTextContent("EOD");
  });
});
