"""Disposition-concurrence prompt sets (fresh verifier, batch-23). tag -> prompt."""
# LEAD-035: no-tool phrasings the shipping closed list (014bb7f1) is expected to MISS
MISS = [
 ("m-answer-without", "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds."),
 ("m-do-not-call-a-tool", "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 ("m-curly-dont", "Don’t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 ("m-avoid-functions", "Avoid calling any functions. I bought 40 ITC shares at ₹415, add them to my holdings and tell me what I spent."),
 ("m-skip-tools", "Skip the tools for this one — I hold 12 HDFCBANK at ₹1,600; add 3 more at ₹1,650, what is my average?"),
 ("m-zero-tool-calls", "Zero tool calls please: I want to add 7 INFY at ₹1,500 to my portfolio — just tell me the total cost."),
 ("m-from-given", "I hold 40 HDFCBANK at ₹1,640; answer only from what I gave you: what is my cost basis?"),
 ("m-refrain", "Refrain from calling any tools and restate my 5 TCS at ₹3,100."),
 ("m-without-functions-add", "Without using functions, add 3 HDFCBANK at ₹1,650 to my holdings and tell me the total."),
 ("m-no-function-calls", "No function calls. I bought 15 WIPRO at ₹250; total cost?"),
 ("m-curly-invoke", "Please don’t invoke any tool — record nothing, just tell me 5 × ₹3,100."),
 ("f-hands-off-add", "Hands off the tools: add 20 SBIN at ₹800 to my portfolio."),
 ("f-no-external-record", "No external calls. Record a buy of 5 RELIANCE at ₹1,200 in my portfolio."),
 ("f-dont-look-up-update", "Don't look anything up; I sold 3 INFY at ₹1,010 — update my holdings."),
 ("f-without-function-delete", "Without any function calls, delete my TCS position."),
 ("f-tools-off-price", "Tools off for this one: what is TCS.NS trading at right now?"),
 ("f-dont-touch-price", "Please don't touch any tools, just tell me INFY.NS's current price."),
]
# LEAD-035: batch-23 keep-surface data requests (base keeps them)
KEEP = [
 ("k-blindly", "Don't just use the tools blindly — check the TCS.NS price and explain the move."),
 ("k-twice", "Never call the tools twice for one symbol; get the INFY.NS price."),
 ("k-dont-need", "Don't call functions you don't need, just get me SBIN.NS's latest price."),
 ("k-no-lookups-tcs", "No lookups needed for TCS, I know it; what is ITC.NS trading at?"),
 ("k-search-tools", "Never use the search tools, only the quote: INFY.NS price?"),
 ("k-arith", "Don't use the tools for arithmetic; get the TCS.NS price."),
 ("k-again", "Do not call the tools again for TCS, just get INFY.NS price."),
]
# LEAD-035: explicit data requests the shipping closed list OVER-matches (surface emptied)
OVER = [
 ("o-never-said", "I never said don't use tools — get RELIANCE.NS price."),
 ("o-other-than", "Don't use any tools other than price data: TCS.NS close?"),
 ("o-but-do-fetch", "Don't use tools for the math, but do fetch the TCS.NS price."),
 ("o-except", "No tools except price_data for TCS.NS"),
 ("o-dont-need", "Don't use tools you don't need; get the ITC.NS price."),
 ("o-twice", "Don't call tools twice — what is HDFCBANK.NS at?"),
 ("o-web", "Do not use tools from the web, only the quote: WIPRO.NS price?"),
]
# LEAD-038: no-tool instruction the shipping list MATCHES + a write request
L38 = [
 ("w-without-calling-add", "Without calling any tool, add 10 SBIN at ₹800 to my portfolio and tell me the total."),
 ("w-dont-use-add-infy", "Don't use any tools, add 7 INFY to my holdings"),
 ("w-never-use-add", "Never use tools for this: add 5 TCS at ₹3,000 to my holdings."),
 ("w-caps-sell", "DON'T USE TOOLS. Sell 5 ITC at ₹420 from my portfolio."),
 ("w-no-tool-calls-sold", "no tool calls — I sold 4 TCS at ₹3,200, update my position and tell me what I got."),
 ("w-no-tools-please-buy", "No tools please. I bought 25 WIPRO at ₹165 today — put them in my portfolio."),
 ("w-do-not-call-tools-delete", "Do not call tools. Remove my HDFCBANK holding."),
]
# LEAD-037: current-price asks (price_data kept)
L37 = [
 ("p-sbi-short", "Get the latest price of SBIN.NS and state it in one sentence that calls the company SBI."),
 ("p-tcs-short", "Get the latest price of TCS.NS and state it in one sentence."),
 ("p-infy-now", "What is INFY.NS trading at right now? One line."),
 ("p-itc-current", "Fetch ITC.NS with price_data and tell me its current price."),
 ("p-hdfc-latest", "Latest HDFCBANK.NS price please, just the number and the date."),
 ("p-wipro-now", "Use price_data for WIPRO.NS and give me the current price and today's change."),
]
# Under-matched no-tool phrasing + a write, run with autonomy AUTO (watchlist/chart auto-apply; data-write never does)
AUTO = [
 ("a-skip-watchlist", "Skip the tools for this one — add NVDA to my watchlist."),
 ("a-avoid-chart", "Avoid calling any functions: switch my chart to INFY.NS."),
 ("a-zero-add", "Zero tool calls please: add 7 INFY at ₹1,500 to my portfolio."),
]
