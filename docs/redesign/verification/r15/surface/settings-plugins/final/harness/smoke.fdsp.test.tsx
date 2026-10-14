import { test, expect } from "vitest";
test("smoke", async () => { const r = await fetch("http://127.0.0.1:52845/health"); expect(r.status).toBe(200); });
