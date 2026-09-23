import { test } from "vitest";
import fs from "fs";
import { render, screen } from "@testing-library/react";
import { useScreenerStore } from "@/store/screener";
import { ScreenerFormulaLeaf } from "@/modules/screener/ScreenerFormulaLeaf";
test("formula leaf states", () => {
  const out: Record<string, unknown> = {};
  for (const f of ["pe < 20 and roe > 15%", "roe > 0.2 and de < 0.5", "roce > 0.15", "pe + (roe > 0.1) > 5"]) {
    useScreenerStore.getState().__resetForTests();
    useScreenerStore.setState({ formula: f });
    const { container, unmount } = render(<ScreenerFormulaLeaf />);
    const errEl = container.querySelector('[data-testid="screener-formula-error"]');
    out[f] = { error: errEl ? (errEl.textContent ?? "").replace(/\s+/g, " ") : null, text: (container.textContent ?? "").replace(/\s+/g, " ").slice(0, 400) };
    unmount();
  }
  fs.writeFileSync("/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/surface/screener/22-formula-leaf-states.json", JSON.stringify(out, null, 1));
});
