import { writeFileSync } from "node:fs";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ScreenerCriteriaBuilder } from "@/modules/screener/ScreenerCriteriaBuilder";
import { useScreenerStore } from "@/store/screener";
const log: unknown[] = [];
afterAll(() => writeFileSync(process.env.U045_OUT!, JSON.stringify(log, null, 1)));
test("flat builder: market_cap 1e11 and roe 0.18", () => {
  useScreenerStore.setState({ advanced: false, group: null, criteria: [{ field: "market_cap", operator: "gt", value: 1e11 }, { field: "roe", operator: "gte", value: 0.18 }] });
  render(<ScreenerCriteriaBuilder />);
  const ops = screen.getAllByLabelText("numeric operator");
  for (const op of ["between", "lte", "between", "gt"]) {
    fireEvent.change(ops[0]!, { target: { value: op } });
    fireEvent.change(screen.getAllByLabelText("numeric operator")[1]!, { target: { value: op } });
    log.push({ flat_after: op, criteria: useScreenerStore.getState().criteria });
  }
  cleanup();
});
test("advanced group: pe_ratio 8 inside a nested group", () => {
  useScreenerStore.setState({ advanced: true, group: { combinator: "and", criteria: [{ combinator: "or", criteria: [{ field: "pe_ratio", operator: "lt", value: 8 }] }] } });
  render(<ScreenerCriteriaBuilder />);
  for (const op of ["between", "gte", "between", "lt"]) {
    fireEvent.change(screen.getAllByLabelText("numeric operator")[0]!, { target: { value: op } });
    log.push({ group_after: op, group: JSON.stringify(useScreenerStore.getState().group) });
  }
  cleanup();
});
