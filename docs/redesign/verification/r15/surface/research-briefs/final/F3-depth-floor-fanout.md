# F3 — With the ULTRA slider, one user turn fans out into N sequential full ULTRA runs (N x spend, N x wall), each replacing the last brief

Head d38b5d1a. Own source sidecar :52344, OpenAI-direct gpt-4o-mini through vy.py's spend guard.
Command: `turn.py --port 52344 --provider openai --model gpt-4o-mini --depth ultra --prompt "Research Data Patterns (India) Limited — latest quarterly results, order book, valuation and peer comparison."`
(`03b-ultra-datapatterns-4omini.{jsonl,stdout.txt,runner.log}`).

Excerpt:
```
[3.1s] tool_use research {"query": "Data Patterns (India) Limited — latest quarterly results", "depth": "quick"}
[3.1s] tool_use research {"query": "Data Patterns (India) Limited — order book", "depth": "quick"}
[3.1s] tool_use research {"query": "Data Patterns (India) Limited — valuation", "depth": "quick"}
[3.1s] tool_use research {"query": "Data Patterns (India) Limited — peer comparison", "depth": "quick"}
[3.1s] research:begin e3920ca7... depth=ultra ... Heavy mode (3 parallel angles + cross-check)
[288.1s] publish_brief (results)   cost {'tokens': 540840, 'spend_usd': 0.324504, 'steps': 46}
[288.1s] research:begin 9aa8042f... depth=ultra query=... order book   (Heavy mode again)
[~590s]  publish_brief (order book) cost {'tokens': 500219, 'spend_usd': 0.300131, 'steps': 47}
[~593s]  3rd run (valuation) starts Heavy mode ...
```
I stopped my client at 604 s (pid) to cap shared spend; the sidecar stopped calling OpenAI within 2 s (AGENT-002 holds).
Projected for the turn: 4 x ~290 s = ~19 min, 4 x ~$0.31 = ~$1.25, three of the four briefs replaced on the panel by the next.

Mechanism (d38b5d1a): `sidecar/services/agent_tools/research.py:314-323` takes max(model depth, slider) PER CALL, so every
call the model emits in the turn is lifted to ULTRA (the model asked for 'quick' four times); nothing in
`sidecar/services/agent_runtime.py` limits or coalesces research calls per turn (`_RESEARCH_TOOLS` at :777 is the only
research-specific symbol), and each ok result auto-publishes a brief for the same symbol.
The copilot prompt asks for one research call per turn (`sidecar/agents/copilot.json`: "research(X)"; "never start at
'heavy'"); the product enforces neither. Not covered by any register entry (searched parallel/concurrent/fan + research).
