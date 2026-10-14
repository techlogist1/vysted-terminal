import { create, all } from "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-1006c6d-fix-int/node_modules/mathjs/lib/esm/index.js";
import fs from "node:fs";
const math = create(all, {});
const ex = JSON.parse(fs.readFileSync("/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/vshard5/exprs.json","utf8"));
for (const [e, scope] of ex) { let v; try { v = math.evaluate(e, {...scope}); v = typeof v === "object" ? math.format(v) : v; } catch (err) { v = "ERR " + err.message; } console.log(JSON.stringify([e, v])); }
