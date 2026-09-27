# set-66 — batch-18/W1-opus (rc1-battery-4)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Sidecar `:52344`. Ollama lock held
per-call (two separate holds, one per turn — release verified between and after).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-033 | Own repro, literal: live two-turn `vy.py invoke copilot` against `:52344`, provider ollama, model llama3.1:8b, mode agent, autonomy ask. Turn 1 "What is AAPL's market cap?" (no history) -> stored as `historyForSend`/`withTrailer` would build it (`"<content>\n\n[tool steps: Using fundamentals]"`, label confirmed live at `ChatSidebar.tsx:293` `readToolLabel` default case). Turn 2 sends that history via `--options '{"history":[...]}'` (rides `AgentInvocationRequest.options.history`, confirmed at `ChatSidebar.tsx:916/1112` `options: {history, ...}`) plus the entry's own turn-2 prompt "Which tool gave you that market cap figure? Show exactly what it returned." | Turn 1: "AAPL's market cap is $4.98T." (`fundamentals` tool called). Turn 2 (198s, called `price_data` then `fundamentals` again rather than trusting history): "The price_data tool returned the market data for AAPL, but it doesn't explicitly mention the market cap. To get the market cap, I will try calling the fundamentals tool. The market cap of AAPL is $4.98T. This figure comes from the fundamentals tool. ..." — zero occurrences of `[tool steps` in the turn-2 log or the raw jsonl (`grep -c` both 0) | holds |

Raw: `battery/raw/set-66/R15-LEAD-033.txt`.

Note: the register's own note on this entry records a round-5 (non-recheck) vshard
refutation of the CLASS claim (filed separately as R15-LEAD-086) while the entry's OWN
stated repro held on that round's re-run too. This round's re-run (above) re-confirms the
same: the entry's own repro (turn-2 trailer echo) does not reproduce on 949c3c9f.

COVERAGE: 1/1 ids raw; no raw: none.
