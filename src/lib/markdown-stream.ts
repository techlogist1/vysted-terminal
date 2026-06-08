/**
 * Streaming-markdown token completer.
 *
 * While a long assistant message streams in token-by-token, the buffer is
 * frequently mid-token: a `**` with no closing `**`, an open inline backtick, or
 * a ``` fence that hasn't seen its close yet. Rendering that raw makes the live
 * view flicker between "broken markdown" and "fixed markdown" on every delta.
 *
 * These PURE functions repair only the *trailing* incomplete token so the
 * in-flight buffer parses cleanly; an already-balanced (complete) input passes
 * through byte-for-byte unchanged — including a literal `*` / `**` that lives
 * inside a balanced `…` inline-code span (emphasis parity skips code spans, so
 * "the `**kwargs` argument" is never corrupted). No dependency, no allocation
 * beyond the returned string.
 *
 * Ported as original code from vercel/streamdown's `remend`/`parse-incomplete`
 * heuristics (Apache-2.0, https://github.com/vercel/streamdown). The fence walk
 * follows CommonMark §4.5 (fenced code blocks): a fence is a run of >=3 of the
 * SAME char (` ` ` or `~`) starting a line with <4 leading spaces; the closing
 * fence must use the same char and be at least as long, with no info string.
 */

/** A leading run of up to 3 spaces (4+ would be an indented code block, not a fence). */
const FENCE_RE = /^( {0,3})(`{3,}|~{3,})(.*)$/;

interface OpenFence {
  char: "`" | "~";
  len: number;
}

/**
 * Walk the buffer line-by-line tracking the single open fence (fences don't
 * nest in CommonMark). Returns the still-open fence at end-of-buffer, or null.
 */
function openFenceAt(text: string): OpenFence | null {
  const lines = text.split("\n");
  let open: OpenFence | null = null;
  for (const line of lines) {
    const m = FENCE_RE.exec(line);
    if (!m) {
      continue;
    }
    const char = m[2][0] as "`" | "~";
    const len = m[2].length;
    if (open) {
      // A close must match the opener's char, be >= its length, and carry no
      // info string (trailing content disqualifies it as a closer).
      if (char === open.char && len >= open.len && m[3].trim() === "") {
        open = null;
      }
      // Otherwise it's literal content inside the open block — ignore it.
    } else {
      open = { char, len };
    }
  }
  return open;
}

/** True when the buffer ends inside an unbalanced ``` / ~~~ fenced code block. */
export function hasIncompleteCodeFence(text: string): boolean {
  return openFenceAt(text) !== null;
}

/**
 * Count how many of `marker` are "open" (odd run-aware) OUTSIDE inline code, so
 * a literal `*` / `**` inside a `…` span never trips emphasis parity. We only
 * need the parity to decide whether the trailing marker dangles.
 *
 * Backtick parity (`marker === "`"`) is measured on the raw text — the count of
 * single backticks IS what tells us a code span dangles, so it must not skip
 * itself. For `*` / `**` we walk inline-code spans and ignore any emphasis
 * marker between a backtick run and its matching close run (CommonMark §6.1: an
 * inline code span is delimited by equal-length backtick runs, and its contents
 * are literal). A still-open trailing backtick run swallows the rest as code, so
 * emphasis after it is also literal and correctly excluded.
 */
function isUnbalanced(text: string, marker: "**" | "*" | "`"): boolean {
  // Backticks: a flat run-unaware count is exactly the dangling-span signal.
  if (marker === "`") {
    let count = 0;
    for (let i = 0; i < text.length; i++) {
      if (text[i] === "`") {
        count++;
      }
    }
    return count % 2 === 1;
  }

  let count = 0;
  let i = 0;
  // Length of the backtick run that opened the inline-code span we're inside,
  // or 0 when outside code. A literal emphasis marker inside code is ignored.
  let openTickRun = 0;
  while (i < text.length) {
    if (text[i] === "`") {
      // Consume the whole backtick run (`` `` `` etc. delimit a single span).
      let run = 0;
      while (i < text.length && text[i] === "`") {
        run++;
        i++;
      }
      if (openTickRun === 0) {
        openTickRun = run; // entering a code span
      } else if (run === openTickRun) {
        openTickRun = 0; // matching close — back outside code
      }
      // A non-matching run inside code is literal content; stay inside.
      continue;
    }
    if (openTickRun > 0) {
      i += 1; // inside inline code — emphasis markers are literal
      continue;
    }
    if (marker === "**") {
      if (text.startsWith("**", i)) {
        count++;
        i += 2;
        continue;
      }
    } else if (text[i] === "*") {
      count++;
      i += 1;
      continue;
    }
    i += 1;
  }
  return count % 2 === 1;
}

/**
 * Close a dangling `**`, `*`, or `` ` `` at end-of-buffer and append a synthetic
 * close fence when the buffer ends inside an open code block. Order matters: the
 * fence is resolved first (emphasis inside a fence is literal, so it must not be
 * "closed"), then inline markers on the already-fence-safe text.
 *
 * Complete (balanced) input is returned unchanged.
 */
export function completeIncomplete(text: string): string {
  if (text === "") {
    return text;
  }

  // 1) Open fence wins — close it and stop (its body is literal markdown).
  if (hasIncompleteCodeFence(text)) {
    const open = openFenceAt(text);
    const fence = (open?.char ?? "`").repeat(open?.len ?? 3);
    const sep = text.endsWith("\n") ? "" : "\n";
    return `${text}${sep}${fence}`;
  }

  let out = text;

  // 2) Inline code backtick (single ` `). Resolve before emphasis so a dangling
  //    backtick doesn't get mis-read as part of an emphasis run.
  if (isUnbalanced(out, "`")) {
    out += "`";
  }

  // 3) Bold (`**`) before italic (`*`): a lone trailing `**` is a bold opener,
  //    not two italics. Closing bold first leaves no spurious single `*`.
  if (isUnbalanced(out, "**")) {
    out += "**";
  } else if (isUnbalanced(out, "*")) {
    out += "*";
  }

  return out;
}
