import { describe, expect, it } from "vitest";

import { buildCsv, escapeCsvCell } from "./csv";

describe("csv helpers", () => {
  describe("escapeCsvCell", () => {
    it("passes plain values through unquoted", () => {
      expect(escapeCsvCell("AAPL")).toBe("AAPL");
      expect(escapeCsvCell(42)).toBe("42");
    });

    it("renders null/undefined as an empty cell", () => {
      expect(escapeCsvCell(null)).toBe("");
      expect(escapeCsvCell(undefined)).toBe("");
    });

    it("quotes + escapes cells containing comma, quote, or newline", () => {
      expect(escapeCsvCell("Apple, Inc.")).toBe('"Apple, Inc."');
      expect(escapeCsvCell('a "quoted" word')).toBe('"a ""quoted"" word"');
      expect(escapeCsvCell("line1\nline2")).toBe('"line1\nline2"');
    });
  });

  describe("buildCsv", () => {
    it("joins a header row + data rows with escaping", () => {
      const csv = buildCsv(
        ["Symbol", "Name", "Price"],
        [
          ["AAPL", "Apple, Inc.", 192.5],
          ["MSFT", "Microsoft", null],
        ],
      );
      expect(csv).toBe('Symbol,Name,Price\nAAPL,"Apple, Inc.",192.5\nMSFT,Microsoft,');
    });

    it("emits a header-only string for no data rows", () => {
      expect(buildCsv(["A", "B"], [])).toBe("A,B");
    });
  });
});
