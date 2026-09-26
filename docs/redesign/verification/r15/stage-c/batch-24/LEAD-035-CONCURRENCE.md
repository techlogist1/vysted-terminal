REFUSE

# R15-LEAD-035: blocked_tier4 concurrence (batch-24 fresh verifier)

**Ruling: REFUSE.**
- The lead proposes the batch-23 corrected wording **minus its over-match clause**. That wording would be false on
  `d1290f66`:
  - an explicit data request that qualifies tool use still loses every tool;
  - live, the model then states invented prices as fetched.
- This is harm beyond narration, the batch-23 criterion (c).
- A bounded narrowing-only fix exists that I would certify, criterion (b).
- The under-match residual, which is the part the lead asked me to test, **does fail safe**. On that part alone I would
  concur.

Setup: sidecar from `d1290f66` on 127.0.0.1:52310, llama3.1:8b via ollama, keyless, agent mode, autonomy ask. The data
dir was a copy of `vysted-iso/data`. Evidence is in `verifier-evidence/` (`live-full.out`, `live-summary.out`,
`live/*.jsonl`, `v-regex.out`, `v-candidate.out`).

## 1. Under-match fail-safe facts (11 unrecognised no-tool phrasings × 2 = 22 runs): confirmed

The 11 phrasings:
- 8 from the batch-23 MISS set: m-avoid-functions, m-skip-tools, m-zero-tool-calls, m-without-functions-add,
  f-hands-off-add, f-no-external-record, f-without-function-delete and f-dont-touch-price.
- 3 of my own:
  - "Don't use any tools for my calculation: … add them to my portfolio" and "Do not call tools when answering — sell
    4 WIPRO …". The base stripped both; batch-24 keeps both, so this is the fix's new miss.
  - "Leave the tools alone and add 9 SBIN …", which both versions miss.

| outcome | runs |
|---|---|
| Portfolio write **staged** (`host_action` notice "Staged for your review, not applied yet"): add ×13, update ×4, delete ×2 | 19 |
| Write attempted with invalid args, nothing staged (m-without-functions-add r1) | 1 |
| Read only: `price_data`, with the /quotes price stated correctly (f-dont-touch-price ×2) | 2 |
| Write **applied** | **0** |

- `GET /portfolio/positions` was `[]` after every run.
- `portfolio.db positions` had 0 rows.
- `audit_orders` had **0 rows** (opened `mode=ro`).
- No figure was invented in these 22 runs. One piece of narration had bad arithmetic: m-zero-tool-calls r2 gave
  "₹105,000" for 7 × ₹1,500.
- AUTO was not re-run. The batch-23 AUTO fact still stands on this head, because the misses keep the full surface: under
  AUTO a watchlist or chart change applies.

## 2. Why the proposed wording is still wrong: the over-match persists

- Offline (`v-regex.out`), 4 of my 18 fresh explicit data requests still get 0 tools on the int head. The base also
  strips all 4.
- Live ×2 each (`live-summary.out`, the `fo-*` runs):

| request | calls | stated (truth) |
|---|---|---|
| He says don't use tools, but please fetch the TCS.NS price. | `[]` ×2 | "current market price … ₹3,449.15"; "Price: ₹1,023.35 … current market price … as of 2026-09-26" (2082.0) |
| No tools, other than the price lookup: what's SBIN.NS at? | `[]` ×2 | "currently trading at ₹934.10"; "Closing Price: ₹843.50" (983.0) |
| Don't use tools. Just kidding — get me the INFY.NS price. | `[]` ×2 | "The current price of INFY.NS is ₹1,241.05"; ₹1,243.80 (1000.2) |
| Don't use any tools, except price_data for the TCS.NS price. | `[]` ×2 | no price; an off-topic reply |

- **6 of 8 runs state an invented price as fetched or current**, off by up to +66%.
- **Mechanism.**
  - The closed tail treats `,` as a clause end, so "tools, except …" and "tools, other than …" fire.
  - The reported-speech guard covers only `said ` and `say `, so "says" fires.

## 3. The bounded fix I would certify

It is narrowing-only on top of `d1290f66`:
- add `(?<!says )` to the lookbehinds;
- insert `(?!\s*,?\s*(?:except|other than|besides|apart from|beyond|unless)\b)` before the tail lookahead.

Offline (`v-candidate.out`):
- it is a subset of the int head;
- it clears "says", "tools, except" and "tools, other than";
- it loses 0 correct strips across all 97 phrasings.

The "Just kidding" retraction stays stripped. That shape is rarer, and I would accept it as residual. This is a one-line
regex change with pins, and it does not need a Tier-4 deferral.

## 4. Final one-sentence briefing wording

- **Accurate for `d1290f66` as it stands.** I would concur on this wording only once the §3 guard merges, and then with
  the qualifier clause cut back to the retraction case:

  > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an unrecognised no-tool
  > phrasing keeps the tools, so the agent may still read data and propose a portfolio change (always held for your
  > review, never applied; under AUTO a watchlist or chart change does apply) and can occasionally state a price it
  > never fetched, while a data request that qualifies a no-tool instruction after a comma or in reported speech
  > ("Don't use any tools, except price_data …", "No tools, other than the price lookup …", "He says don't use tools,
  > but …") still loses every tool and the agent then usually states an invented price as if fetched.

- **After the §3 guard merges**, the last clause becomes "…while a no-tool instruction the user retracts in the same
  message ("Don't use tools. Just kidding — …") still loses every tool and the agent may then state an invented price".

## Cleanup

- The sidecar and MCP sleep pids were killed.
- The scratch worktree was removed.
- The register, DECISIONS, FACTS and code are untouched. Nothing was committed.
