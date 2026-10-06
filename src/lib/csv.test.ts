import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/export-artifact", () => ({
  saveTextArtifact: vi.fn(async (subdir: string, filename: string) => ({
    path: `/data/exports/${subdir}/${filename}`,
    fellBack: false,
  })),
}));

import { saveTextArtifact } from "@/lib/export-artifact";
import { buildCsv, downloadCsv, escapeCsvCell } from "./csv";

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

    it("R15-UI-079: prefixes a formula-trigger leading char so no text cell opens a live formula", () => {
      expect(escapeCsvCell('=HYPERLINK("http://example.invalid","x")')).toBe(
        '"\'=HYPERLINK(""http://example.invalid"",""x"")"',
      );
      expect(escapeCsvCell("+1")).toBe("'+1");
      expect(escapeCsvCell("-1")).toBe("'-1");
      expect(escapeCsvCell("@x")).toBe("'@x");
      expect(escapeCsvCell("\tx")).toBe("'\tx");
      expect(escapeCsvCell("\rx")).toBe('"\'\rx"');
    });

    it("R15-UI-079: leaves a plain numeric VALUE unprefixed (not text a spreadsheet parses as a formula)", () => {
      expect(escapeCsvCell(-12.5)).toBe("-12.5");
      expect(escapeCsvCell(42)).toBe("42");
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

  describe("downloadCsv", () => {
    it("R15-UI-009: saves through saveTextArtifact, never a Blob + <a download> (WKWebView blocks it)", async () => {
      const result = await downloadCsv("out.csv", "A,B\n1,2");
      expect(saveTextArtifact).toHaveBeenCalledWith("csv", "out.csv", "A,B\n1,2");
      expect(result.path).toBe("/data/exports/csv/out.csv");
    });
  });
});
