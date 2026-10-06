/**
 * Tiny CSV helpers — shared by the watchlist + portfolio exports (and anywhere
 * else a panel offers "Export CSV"). Quoting follows RFC-4180: a cell containing
 * a comma, double-quote, or newline is wrapped in double-quotes and any embedded
 * double-quote is doubled. `null`/`undefined` become an empty cell.
 */

import { saveTextArtifact, type ExportResult } from "@/lib/export-artifact";

/** A leading `=`, `+`, `-`, `@`, tab, or CR opens a live formula in
 *  Excel/Sheets/LibreOffice (CSV formula injection, R15-UI-079) — e.g. a
 *  holding note the agent wrote from web text. */
const FORMULA_TRIGGER = /^[=+\-@\t\r]/;

/** Escape a single CSV cell value per RFC-4180, and neutralize a leading
 *  formula-trigger character on TEXT cells with a single-quote prefix (the
 *  spreadsheet-standard escape) — a plain numeric value like -12.5 is never
 *  parsed as a formula, so it is left unprefixed. */
export function escapeCsvCell(value: unknown): string {
  const s = value === null || value === undefined ? "" : String(value);
  const guarded = typeof value !== "number" && FORMULA_TRIGGER.test(s) ? `'${s}` : s;
  return /[",\n\r]/.test(guarded) ? `"${guarded.replace(/"/g, '""')}"` : guarded;
}

/** Build a CSV string from a header row + data rows (each an array of cells). */
export function buildCsv(headers: string[], rows: readonly unknown[][]): string {
  const lines = [headers.map(escapeCsvCell).join(",")];
  for (const row of rows) {
    lines.push(row.map(escapeCsvCell).join(","));
  }
  return lines.join("\n");
}

/**
 * Save `content` as `filename` (text/csv) — via the Rust atomic-write path
 * (`saveTextArtifact`), never the Blob + `<a download>` primitive: WKWebView
 * does not implement it, so it silently no-ops in the desktop app
 * (R15-UI-009). Falls back to a browser Blob download outside Tauri.
 */
export async function downloadCsv(filename: string, content: string): Promise<ExportResult> {
  return saveTextArtifact("csv", filename, content);
}
