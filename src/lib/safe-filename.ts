/**
 * Map a free-text string (e.g. a note's symbol scope) to a filename that is
 * legal on Windows (R15-CROSS-PLATFORM-006). Windows forbids control
 * characters and `<>:"/\|?*`, silently strips trailing dots/spaces (so the
 * file that lands on disk has a different name than the one requested), and
 * reserves CON/PRN/AUX/NUL/COM1-9/LPT1-9 as device names regardless of
 * extension. macOS/Linux allow all of the above, so one mapping is safe
 * everywhere.
 */

// Strips Windows-illegal chars, including control chars 0x00-0x1f.
const ILLEGAL_CHARS_RE = /[<>:"/\\|?*\x00-\x1f]/g;
const TRAILING_DOTS_SPACES_RE = /[. ]+$/;

const RESERVED_DEVICE_NAMES = new Set([
  "CON",
  "PRN",
  "AUX",
  "NUL",
  "COM1",
  "COM2",
  "COM3",
  "COM4",
  "COM5",
  "COM6",
  "COM7",
  "COM8",
  "COM9",
  "LPT1",
  "LPT2",
  "LPT3",
  "LPT4",
  "LPT5",
  "LPT6",
  "LPT7",
  "LPT8",
  "LPT9",
]);

export function safeFilename(name: string): string {
  let out = name.replace(ILLEGAL_CHARS_RE, "_").replace(TRAILING_DOTS_SPACES_RE, "");
  if (out === "") out = "_";

  const base = out.includes(".") ? out.slice(0, out.indexOf(".")) : out;
  if (RESERVED_DEVICE_NAMES.has(base.toUpperCase())) {
    out = `${out}_`;
  }
  return out;
}
