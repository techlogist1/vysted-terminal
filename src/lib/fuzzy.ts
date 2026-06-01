/**
 * Fuzzy ranking for the command palette (FR-031).
 *
 * The palette must rank a heterogeneous corpus (commands, panels, symbols,
 * agents) by how well each item's label matches the query — plain substring
 * `includes()` is too blunt (it can't surface `"opt prc"` → "Option Pricer",
 * and it has no notion of "this is a better match than that"). This module is
 * a small, dependency-free subsequence ranker:
 *
 *  - `fuzzyScore(query, target)` returns a numeric score (higher = better) or
 *    `null` when `query` is not a subsequence of `target` (no match at all).
 *  - `fuzzyScoreWithIndices(query, target)` returns `{ score, indices }` or
 *    `null` — same scoring, but also returns the matched character positions
 *    so callers can highlight them (see CommandPalette.tsx for the JSX helper).
 *  - `fuzzyRank(query, items, keyFn)` ranks a list, dropping non-matches and
 *    sorting by score (stable for ties, so the caller's input order — e.g.
 *    recents/commands first — is preserved on equal scores).
 *
 * Scoring rewards, in rough order of weight: a full prefix match, matches at a
 * word boundary (start, or after a separator), and runs of contiguous matched
 * characters. Everything is case-insensitive. The algorithm is greedy
 * left-to-right (not a full edit-distance) — fast and good enough for a
 * keystroke-responsive palette over a few hundred items.
 */

/** Score awarded for the first matched character landing on a word boundary. */
const BOUNDARY_BONUS = 10;
/** Score awarded for each additional contiguous matched character. */
const CONTIGUOUS_BONUS = 8;
/** Score awarded when a (non-first, non-contiguous) match lands on a boundary. */
const INNER_BOUNDARY_BONUS = 6;
/** Base score for any matched character. */
const MATCH_BASE = 2;
/** Penalty per skipped (unmatched) character in the target, capped. */
const LEADING_PENALTY = 1;
/** Maximum total leading/gap penalty so a long target can't go negative. */
const MAX_GAP_PENALTY = 12;
/** Bonus when the whole query is a contiguous prefix of the target. */
const PREFIX_BONUS = 40;
/** Bonus when the whole query is a contiguous substring of the target. */
const SUBSTRING_BONUS = 18;
/** Small reward for a shorter target (tie-break toward the tighter label). */
const SHORTNESS_WEIGHT = 6;

/** A character is a word boundary if it's the first char or follows a separator. */
function isBoundary(target: string, index: number): boolean {
  if (index === 0) {
    return true;
  }
  const prev = target[index - 1];
  return (
    prev === " " || prev === "-" || prev === "_" || prev === "/" || prev === "." || prev === ":"
  );
}

/**
 * Score how well `query` fuzzy-matches `target`. Returns `null` when `query` is
 * not a (case-insensitive) subsequence of `target`. An empty query scores `0`
 * (matches everything, neutrally — callers treat empty-query as "show all").
 */
export function fuzzyScore(query: string, target: string): number | null {
  return fuzzyScoreWithIndices(query, target)?.score ?? null;
}

/**
 * Same as `fuzzyScore` but also returns the matched character positions (in the
 * original `target` string, before lowercasing) so callers can highlight them.
 */
export function fuzzyScoreWithIndices(
  query: string,
  target: string,
): { score: number; indices: number[] } | null {
  const q = query.trim().toLowerCase();
  if (q === "") {
    return { score: 0, indices: [] };
  }
  const t = target.toLowerCase();

  // Fast paths that also dominate the score: prefix > substring.
  if (t.startsWith(q)) {
    const indices = Array.from({ length: q.length }, (_, i) => i);
    return {
      score: PREFIX_BONUS + q.length * CONTIGUOUS_BONUS + shortness(target),
      indices,
    };
  }
  const substringAt = t.indexOf(q);
  if (substringAt !== -1) {
    const boundary = isBoundary(t, substringAt) ? BOUNDARY_BONUS : 0;
    const indices = Array.from({ length: q.length }, (_, i) => substringAt + i);
    return {
      score: SUBSTRING_BONUS + boundary + q.length * CONTIGUOUS_BONUS + shortness(target),
      indices,
    };
  }

  // General subsequence walk.
  let score = 0;
  let queryIndex = 0;
  let prevMatchIndex = -2; // so the first match is never "contiguous"
  let gapPenalty = 0;
  const indices: number[] = [];

  for (let targetIndex = 0; targetIndex < t.length && queryIndex < q.length; targetIndex += 1) {
    if (t[targetIndex] !== q[queryIndex]) {
      continue;
    }
    const contiguous = targetIndex === prevMatchIndex + 1;
    const boundary = isBoundary(t, targetIndex);

    score += MATCH_BASE;
    if (queryIndex === 0 && boundary) {
      score += BOUNDARY_BONUS;
    } else if (contiguous) {
      score += CONTIGUOUS_BONUS;
    } else if (boundary) {
      score += INNER_BOUNDARY_BONUS;
    }
    if (queryIndex === 0) {
      // Penalise how far into the target the match begins (prefer earlier).
      gapPenalty += Math.min(targetIndex * LEADING_PENALTY, MAX_GAP_PENALTY);
    }

    indices.push(targetIndex);
    prevMatchIndex = targetIndex;
    queryIndex += 1;
  }

  if (queryIndex < q.length) {
    return null; // not all query chars matched → no subsequence match
  }
  return { score: score - gapPenalty + shortness(target), indices };
}

/** Tie-break reward: shorter targets score slightly higher. */
function shortness(target: string): number {
  return target.length === 0 ? 0 : SHORTNESS_WEIGHT / target.length;
}

/** A scored item — the original plus its fuzzy score, ready to sort. */
interface Scored<T> {
  item: T;
  score: number;
  index: number;
}

/**
 * Rank `items` against `query`, dropping non-matches. `keyFn` extracts the
 * string to score each item against. The sort is descending by score and
 * **stable** for ties (original order preserved) — so an empty query returns
 * the input list unchanged, and equal-scoring items keep their incoming order
 * (the caller front-loads recents/commands).
 */
export function fuzzyRank<T>(query: string, items: readonly T[], keyFn: (item: T) => string): T[] {
  const q = query.trim();
  if (q === "") {
    return [...items];
  }
  const scored: Scored<T>[] = [];
  items.forEach((item, index) => {
    const score = fuzzyScore(q, keyFn(item));
    if (score !== null) {
      scored.push({ item, score, index });
    }
  });
  scored.sort((a, b) => (b.score === a.score ? a.index - b.index : b.score - a.score));
  return scored.map((entry) => entry.item);
}
