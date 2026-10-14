import { readFileSync, writeFileSync } from "node:fs";
import { render, screen, cleanup } from "@testing-library/react";
import { ScreenerResultsTable } from "@/modules/screener/ScreenerResultsTable";
import { useScreenerStore } from "@/store/screener";
const out: Record<string, string> = {};
afterAll(() => writeFileSync(process.env.U055_OUT!, JSON.stringify(out, null, 1)));
for (const f of ["u055-custom0.json", "u055-custom.json"]) {
  test(f, () => {
    const payload = JSON.parse(readFileSync(process.env.U055_DIR + "/" + f, "utf8"));
    useScreenerStore.setState({ lastResult: payload, status: "ready" });
    const { container } = render(<ScreenerResultsTable />);
    out[f] = (container.textContent ?? "").replace(/\s+/g, " ").slice(0, 600);
    cleanup();
  });
}
