import asyncio, sys
sys.path.insert(0, ".")
from services.budget_guard import BudgetGuard
from models.llm import LLMUsage

async def fake_llm_call(messages):
    # Mirrors deep_research._run_native's llm_call closure shape.
    return "some completion text"

async def main():
    budget = BudgetGuard(max_tokens=600_000, max_wall_seconds=600)

    async def llm_call(messages):
        text = await fake_llm_call(messages)
        usage = LLMUsage(input_tokens=1000, output_tokens=200)
        budget.add_usage(usage, "gpt-4o-mini", "openai")
        return text

    for _ in range(5):
        await llm_call([{"role": "user", "content": "x"}])

    cost = budget.cost()
    print("cost after 5 metered llm_call()s:", cost)
    assert cost["tokens"] == 6000, f"expected 6000 tokens, got {cost['tokens']}"
    assert cost["spend_usd"] > 0.0, "expected nonzero spend_usd estimate"
    print("PASS: BudgetGuard.add_usage accumulates real tokens/spend through the llm_call seam")

asyncio.run(main())
