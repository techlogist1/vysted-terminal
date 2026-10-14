import { compileScreenerExpr } from "@/lib/screener-expr";
import fs from "fs";
test("ts compile corpus", () => {
  const f: string[] = JSON.parse(fs.readFileSync("/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2b/formulas.json", "utf8"));
  const out = f.map((src) => { const r = compileScreenerExpr(src.trim()); return { src, ok: r.ok, error: r.ok ? null : r.error, position: r.ok ? null : r.position, fields: r.ok ? (r as any).fields ?? null : null }; });
  fs.writeFileSync("/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/s2b/formula-ts.json", JSON.stringify(out, null, 1));
});
