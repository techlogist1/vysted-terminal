import { vi, test } from "vitest";
import fs from "fs";
vi.mock("@/lib/sidecar-client", async (orig) => {
  const real: any = await orig();
  return { ...real, getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:52219") };
});
import { applyHostAction } from "@/lib/host-actions";
import { useScreenerStore } from "@/store/screener";

test("replay agent write_screener_filters", async () => {
  const lines = fs.readFileSync("/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/surface/screener/20-agent-screen-llama.jsonl", "utf8").trim().split("\n").map((l) => JSON.parse(l));
  const ev = lines.find((e: any) => e.kind === "tool_use" && e.name === "write_screener_filters");
  const out: Record<string, unknown> = {};
  useScreenerStore.getState().__resetForTests();
  let label: unknown; let err: unknown = null;
  try { label = applyHostAction("write_screener_filters", ev.input); } catch (e) { err = String(e); }
  const s1 = useScreenerStore.getState();
  out.captured = { input: ev.input, applyLabel: label ?? null, threw: err, store_after: { universe: s1.universe, criteria: s1.criteria, formula: s1.formula } };
  // Same args with criteria as a real array (what the tool schema asks for)
  useScreenerStore.getState().__resetForTests();
  const arr = { ...ev.input, criteria: JSON.parse(ev.input.criteria) };
  let label2: unknown; let err2: unknown = null;
  try { label2 = applyHostAction("write_screener_filters", arr); } catch (e) { err2 = String(e); }
  const s2 = useScreenerStore.getState();
  out.array_variant = { applyLabel: label2 ?? null, threw: err2, store_after: { universe: s2.universe, criteria: s2.criteria } };
  const res = await useScreenerStore.getState().runScreener();
  const s3 = useScreenerStore.getState();
  out.array_variant_run = { status: s3.status, error: s3.error, result_count: res?.result_count ?? null, evaluated: res?.evaluated_count ?? null, top: res?.rows.slice(0, 5).map((r) => [r.symbol, r.pe_ratio, r.roe, r.debt_to_equity]) ?? null };
  fs.writeFileSync("/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/surface/screener/21-agent-screen-replay.json", JSON.stringify(out, null, 1));
});
