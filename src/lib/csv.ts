/**
 * Tiny CSV helpers — shared by the watchlist + portfolio exports (and anywhere
 * else a panel offers "Export CSV"). Quoting follows RFC-4180: a cell containing
 * a comma, double-quote, or newline is wrapped in double-quotes and any embedded
 * double-quote is doubled. `null`/`undefined` become an empty cell.
 *
 * Browser-only (`downloadCsv` touches the DOM) — call it from a click handler in
 * the Tauri webview, never during SSR/static export.
 */

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

/** Trigger a client-side download of `content` as `filename` (text/csv). */
export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
