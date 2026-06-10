/**
 * Chat-transcript markdown hygiene (R8 — law §1/§3).
 *
 * The transcript renders through the shared typed-block renderer
 * (`MarkdownBody`), whose table parse requires a GFM separator row
 * (`|---|---|`) under the header. Models frequently emit pipe tables WITHOUT
 * one — which used to land in the chat as a literal wall of pipes
 * ("| Metric | Value | …"). `normalizePipeTables` repairs that at the seam:
 * any run of two or more pipe rows lacking a separator gets one synthesized
 * under its first row, so the renderer treats it as a real table. Pipes inside
 * fenced code are never touched, and a well-formed table passes through
 * byte-identical (the function is idempotent).
 *
 * `stripTableRows` supports the collapsed "short chat" lead: a sentence lead
 * sliced out of a table would re-introduce raw pipes, so table rows are
 * dropped from the lead text (the full table stays behind the expand toggle).
 */

/** A line that reads as a markdown table row: `| a | b |` — at least two cells. */
function isPipeRow(line: string): boolean {
  const t = line.trim();
  if (t.length < 2 || !t.startsWith("|") || !t.endsWith("|")) {
    return false;
  }
  return t.slice(1, -1).includes("|");
}

/** A `|---|:--:|--:|` separator row (mirrors the renderer's detection). */
function isSeparatorRow(line: string): boolean {
  const t = line.trim();
  if (!t.includes("-") || !t.includes("|")) {
    return false;
  }
  let s = t;
  if (s.startsWith("|")) {
    s = s.slice(1);
  }
  if (s.endsWith("|")) {
    s = s.slice(0, -1);
  }
  return s.split("|").every((cell) => /^:?-+:?$/.test(cell.replace(/\s/g, "")));
}

/** Number of columns in a pipe row (for sizing the synthesized separator). */
function columnCount(line: string): number {
  let s = line.trim();
  if (s.startsWith("|")) {
    s = s.slice(1);
  }
  if (s.endsWith("|")) {
    s = s.slice(0, -1);
  }
  return s.split("|").length;
}

/** Fence opener/closer — the same leading-space tolerance as the renderer. */
const FENCE = /^ {0,3}(```|~~~)/;

/**
 * Ensure every pipe-table run of ≥2 rows carries a GFM separator so the
 * typed-block renderer parses it as a real table — never a wall of pipes.
 * Idempotent; fenced code is left untouched; a lone pipe row (e.g. the first
 * line of a still-streaming table) is left alone until its body arrives.
 */
export function normalizePipeTables(source: string): string {
  if (!source.includes("|")) {
    return source;
  }
  const lines = source.split("\n");
  const out: string[] = [];
  let inFence = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    out.push(line);
    if (FENCE.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) {
      continue;
    }
    const prev = i > 0 ? lines[i - 1] : "";
    const next = i + 1 < lines.length ? lines[i + 1] : "";
    // The first row of a separator-less run becomes the header: a pipe row
    // whose neighbour above is NOT part of a table and whose next row is a
    // pipe row that is not already the separator.
    const startsRun = isPipeRow(line) && !isSeparatorRow(line) && !isPipeRow(prev);
    if (startsRun && isPipeRow(next) && !isSeparatorRow(next)) {
      out.push(`|${Array(columnCount(line)).fill(" --- ").join("|")}|`);
    }
  }
  return out.join("\n");
}

/** Drop table rows (and their separators) from a text — used for the collapsed
 *  lead so a sentence slice never cuts through raw pipes. */
export function stripTableRows(source: string): string {
  if (!source.includes("|")) {
    return source;
  }
  return source
    .split("\n")
    .filter((line) => !isPipeRow(line))
    .join("\n");
}
