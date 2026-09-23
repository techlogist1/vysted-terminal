/**
 * Tiny CSV helpers — shared by the watchlist + portfolio exports (and anywhere
 * else a panel offers "Export CSV"). Quoting follows RFC-4180: a cell containing
 * a comma, double-quote, or newline is wrapped in double-quotes and any embedded
 * double-quote is doubled. `null`/`undefined` become an empty cell.
 */

import { saveTextArtifact, type ExportResult } from "@/lib/export-artifact";

/** Escape a single CSV cell value per RFC-4180. */
export function escapeCsvCell(value: unknown): string {
  const s = value === null || value === undefined ? "" : String(value);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
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
