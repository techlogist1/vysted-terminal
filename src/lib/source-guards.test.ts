import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../..");
const SRC = path.join(REPO_ROOT, "src");

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [full] : [];
  });
}

const relative = (file: string) => path.relative(REPO_ROOT, file);

/** Every string the file renders or passes around — literals, template chunks
 *  and JSX text. Comments are not nodes, so they are never visited. */
function userVisibleStrings(file: string): string[] {
  const source = ts.createSourceFile(
    file,
    fs.readFileSync(file, "utf-8"),
    ts.ScriptTarget.Latest,
    true,
    file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const out: string[] = [];
  const visit = (node: ts.Node) => {
    if (
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      ts.isTemplateHead(node) ||
      ts.isTemplateMiddle(node) ||
      ts.isTemplateTail(node) ||
      ts.isJsxText(node)
    ) {
      out.push(node.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return out;
}

describe("source guards", () => {
  // R15-CROSS-PLATFORM-009: a hardcoded ⌘ hint is wrong on Windows/Linux and
  // ignores a remapped chord; render `formatBinding(bindingFor(action))`.
  it("no string or JSX text under src/ contains ⌘ outside src/store/keybindings.ts", () => {
    const offenders = sourceFiles(SRC)
      .filter((file) => relative(file) !== "src/store/keybindings.ts")
      .flatMap((file) =>
        userVisibleStrings(file)
          .filter((text) => text.includes("⌘"))
          .map((text) => `${relative(file)}: ${JSON.stringify(text.trim())}`),
      );
    expect(offenders).toEqual([]);
  });

  // R15-DOCS-006: the frontend is a Vite SPA (src/main.tsx createRoot) — there
  // is no static export or prerender pass, so a comment justifying code by
  // "SSR safety" states a false invariant. Files outside this fix's scope that
  // still carry the claim are a ratchet: each must still match (delete the
  // entry when its comment is fixed) and no new file may add one.
  const STALE_SSR_CLAIM_ALLOWLIST = new Set([
    "src/lib/marketplace.ts",
    "src/lib/export-artifact.ts",
    "src/lib/dev-mcp-bridge.ts",
    "src/lib/use-sidecar-retry.ts",
    "src/lib/sidecar-client.ts",
    "src/lib/menu-bridge.ts",
    "src/modules/notes/NotesPanel.tsx",
    "src/store/settings.ts",
    "src/store/agent-command.ts",
    "src/store/search-settings.ts",
    "src/store/keybindings.ts",
  ]);
  const SSR_CLAIM = /static[- ]export|SSR[- ]safe/i;

  it("no 'static-export'/'SSR-safe' claim under src/ outside the shrinking allowlist", () => {
    const claiming = sourceFiles(SRC)
      .filter((file) => SSR_CLAIM.test(fs.readFileSync(file, "utf-8")))
      .map(relative);
    expect(claiming.filter((file) => !STALE_SSR_CLAIM_ALLOWLIST.has(file))).toEqual([]);
    expect([...STALE_SSR_CLAIM_ALLOWLIST].filter((file) => !claiming.includes(file))).toEqual([]);
  });
});
