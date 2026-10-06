import { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { BudgetConfig, DEFAULT_DELEGATE_BUDGET } from "@/modules/chat/BudgetConfig";
import type { AgentRunBudget } from "@/store/agent-runs";

function Harness({ onBudget }: { onBudget: (b: AgentRunBudget) => void }) {
  const [budget, setBudget] = useState<AgentRunBudget>(DEFAULT_DELEGATE_BUDGET);
  return (
    <BudgetConfig
      budget={budget}
      onChange={(next) => {
        setBudget(next);
        onBudget(next);
      }}
    />
  );
}

describe("BudgetConfig (R15-AGENT-034)", () => {
  afterEach(cleanup);

  it("a cleared or zero box falls back to the default ceiling instead of none", () => {
    let latest: AgentRunBudget = DEFAULT_DELEGATE_BUDGET;
    render(<Harness onBudget={(b) => (latest = b)} />);

    const spend = screen.getByLabelText("Delegate budget — $");
    fireEvent.change(spend, { target: { value: "" } });
    expect(latest.maxSpendUsd).toBeUndefined();
    fireEvent.blur(spend);
    expect(latest.maxSpendUsd).toBe(DEFAULT_DELEGATE_BUDGET.maxSpendUsd);

    const steps = screen.getByLabelText("Delegate budget — steps");
    fireEvent.change(steps, { target: { value: "0" } });
    fireEvent.blur(steps);
    expect(latest.maxSteps).toBe(DEFAULT_DELEGATE_BUDGET.maxSteps);

    fireEvent.change(steps, { target: { value: "4" } });
    fireEvent.blur(steps);
    expect(latest.maxSteps).toBe(4);
  });
});
