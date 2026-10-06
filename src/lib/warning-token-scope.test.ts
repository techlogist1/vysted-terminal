import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// R15-UI-073: --color-warning is reserved for DATA signal (stale/synthetic/
// partial/throttled market data) — infra, plugin/run lifecycle and config
// nags use --color-caution instead (same value today; the split is semantic
// so the two can diverge later without a call-site hunt). This pins the
// split: any `text-warning`/`bg-warning`/`border-warning` Tailwind class
// outside this allowlist means a new site reused the data-signal token for
// something that isn't a data-provenance/freshness/completeness signal.

const REPO_ROOT = path.resolve(__dirname, "../..");
const SRC_ROOT = path.join(REPO_ROOT, "src");

// Files that legitimately render a data-provenance/freshness/completeness
// signal (stale quotes, synthetic/paper data, partial or throttled screener
// results, missing comparison data, cross-source conflicts, a failed quote
// refresh). Everything else in src/ must not use the warning-token classes.
const PROVENANCE_FILES = new Set(
  [
    "components/DataBadges.tsx",
    "components/DataBadges.test.tsx",
    "modules/research/BriefPanel.tsx",
    "modules/research/brief-blocks.tsx",
    "modules/screener/ScreenerPanel.tsx",
    "modules/screener/ScreenerResultsTable.tsx",
    "modules/chart/ChartPanel.tsx",
    "modules/backtest/BacktestResultView.tsx",
    "modules/portfolio/PortfolioPanel.tsx",
    "modules/equity-overview/EquityOverviewPanel.tsx",
  ].map((p) => path.join(SRC_ROOT, p)),
);

const WARNING_CLASS = /\b(?:text|bg|border)-warning\b/;

function listSourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...listSourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

describe("--color-warning stays a data-provenance-only token (R15-UI-073)", () => {
  it("no file outside the provenance allowlist uses text/bg/border-warning", () => {
    const offenders = listSourceFiles(SRC_ROOT)
      .filter((file) => !PROVENANCE_FILES.has(file))
      // This file names the classes in its own comments and regex.
      .filter((file) => file !== path.join(SRC_ROOT, "lib/warning-token-scope.test.ts"))
      .filter((file) => WARNING_CLASS.test(fs.readFileSync(file, "utf-8")))
      .map((file) => path.relative(REPO_ROOT, file));
    expect(offenders).toEqual([]);
  });

  it("the provenance allowlist itself still exists and still uses the token", () => {
    // Catches the allowlist rotting stale (a listed file renamed/deleted, or
    // no longer actually using the token it was allowlisted for).
    for (const file of PROVENANCE_FILES) {
      expect(fs.existsSync(file), `${path.relative(REPO_ROOT, file)} is missing`).toBe(true);
      expect(
        WARNING_CLASS.test(fs.readFileSync(file, "utf-8")),
        `${path.relative(REPO_ROOT, file)} no longer uses text/bg/border-warning`,
      ).toBe(true);
    }
  });

  it("--color-caution exists in tokens.css alongside --color-warning", () => {
    const tokens = fs.readFileSync(path.join(REPO_ROOT, "styles/tokens.css"), "utf-8");
    expect(tokens).toMatch(/--color-warning:\s*#[0-9a-fA-F]{6}/);
    expect(tokens).toMatch(/--color-caution:\s*#[0-9a-fA-F]{6}/);
  });
});
