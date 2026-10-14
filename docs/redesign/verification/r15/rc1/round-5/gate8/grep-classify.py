import re, json, sys, collections
G = sys.argv[1]
I = re.I
FP = [
  (re.compile(r"public_suffix_list\.dat:"), "public-suffix-list data (broker TLD / Fidelity registrant)"),
  (re.compile(r"resolver_masters/.*\.json:|fixtures/.*\.(json|htm):"), "instrument master / filing fixture data: company names and filing text"),
  (re.compile(r"openrouter.{0,80}broker|broker.{0,80}openrouter|model[- ]routing|broker for every model|BROKER with", I), "OpenRouter described as a model broker (LLM routing), not a brokerage"),
  (re.compile(r"(share|stock|commodity|shares &)\s*(and\s+stock\s+)?(stock)?brokers?\b|stockbrokers|stock/ commodity brokers", I), "listed company / sector name (e.g. 'Share and Stock Brokers Ltd')"),
  (re.compile(r"live.?models?|live model", I), "'live model' (LLM model catalog), not live trading"),
  (re.compile(r"order book (covers|is)|order ?book of|orderbook", I), "corporate order book (revenue backlog), not an exchange order book"),
]
MARGIN = re.compile(r"margin", I)
TRADE_CTX = re.compile(r"broker|kite|order|trad|margins_info|/margins|account|demat|paper|kill|upstox|zerodha|dhan|alpaca", I)
SIMUL = re.compile(r"simulat", I)
SIM_TRADE_CTX = re.compile(r"account|order|paper|broker|kill|trad", I)
REMOVAL = re.compile(r"no brokerage|no broker|removed|\bD81\b|not a (registered )?broker|cannot (place|connect)|never a broker|no order|not.{0,20}broker|no .{0,30}(order|broker|kill)|forbidden|_FORBIDDEN|FORBIDDEN_TOOL|absent|is gone|are gone|deleted|superseded|historical", I)
HIST_PATH = re.compile(r"^docs/(redesign/verification|archive|screenshots|research)/|^docs/redesign/[^/]+\.md:|^docs/PHASE_\d+_HANDOFF\.md:")
TEST_PATH = re.compile(r"(^sidecar/tests/|\.test\.tsx?:|^src-tauri/src/keychain\.rs:(491|506):)")

OVERRIDE = {
  "src/store/agent-autonomy.ts:16:": ("historical", "statement that no host action can place, stage or simulate a trade (D81)"),
  "sidecar/services/provider_registry.py:547:": ("false_positive", "financial-metric margins (screener field)"),
  "sidecar/services/llm/native_search.py:62:": ("false_positive", "OpenRouter described as a model broker (LLM routing), not a brokerage"),
  "sidecar/models/llm.py:25:": ("false_positive", "OpenRouter described as a model broker (LLM routing), not a brokerage"),
  "sidecar/services/agent_tools/screener_tools.py:11:": ("historical", "docstring naming the forbidden order-id grep guard (absence check)"),
  "sidecar/services/agent_tools/quant_tools.py:10:": ("historical", "docstring naming the forbidden order-id grep guard (absence check)"),
  "sidecar/services/agent_tools/catalog.py:20:": ("historical", "catalog docstring: no capability id carries an order verb (D81 guard)"),
  "sidecar/services/agent_tools/run_custom_backtest.py:7:": ("false_positive", "historical-data backtest simulation; states it never touches order paths"),
  "sidecar/agents/researcher.json:5:": ("false_positive", "persona prompt: gross/operating/net-interest margin (financial metrics)"),
  "sidecar/agents/soros.json:5:": ("false_positive", "persona prompt: corporate margins (financial metric)"),
  "sidecar/agents/graham.json:5:": ("false_positive", "persona prompt: margin-of-safety principle"),
  "sidecar/agents/buffett.json:5:": ("false_positive", "persona prompt: margin of safety / marginal improvement"),
  "sidecar/agents/strategy_critic.json:5:": ("false_positive", "persona prompt: critiques how a strategy might fail in live trading; research only, no execution path"),
  "docs/BLUEPRINT.md:511:": ("historical", "Phase 5 roadmap heading; body says removed permanently by D81"),
}
DOC_REMOVAL_FILES = ("docs/SAFETY_ARCHITECTURE.md:", "docs/BROKER_INTEGRATIONS.md:", "docs/CURRENT_STATE.md:")

def classify(line):
    path = line.split(":", 1)[0]
    for k, v in OVERRIDE.items():
        if line.startswith(k): return v
    if line.startswith(DOC_REMOVAL_FILES) and not (MARGIN.search(line) and not TRADE_CTX.search(line)):
        return "historical", "current-state doc describing the D81 removal (the file is a removal record; read in full)"
    for rx, why in FP:
        if rx.search(line): return "false_positive", why
    if MARGIN.search(line) and not TRADE_CTX.search(line):
        return "false_positive", "financial-metric / CSS / 'marginal' use of margin"
    if REMOVAL.search(line):
        if TEST_PATH.search(line): return "historical", "test pinning the D81 removal (asserts absence)"
        return "historical", "statement that trading/brokers do not exist or were removed (D81)"
    if SIMUL.search(line) and not SIM_TRADE_CTX.search(line):
        return "false_positive", "'simulate' in a non-account sense (backtest over history, test harness, clock)"
    if HIST_PATH.search(line):
        return "historical", "dated run record / verification evidence / archived phase doc / past-release screenshot demo (pre-D81 or about the removal)"
    if TEST_PATH.search(line):
        return "historical", "test code (guards the removal or uses the word in a fixture); not a product surface"
    return "UNCLASSIFIED", ""

summary, product, examples, uncl = {}, [], collections.defaultdict(list), []
for root in ["src", "sidecar", "src-tauri", "plugins", "docs"]:
    c = collections.Counter()
    for line in open(f"{G}/{root}.txt", encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        cls, why = classify(line)
        c[cls] += 1
        if cls == "UNCLASSIFIED": uncl.append((root, line))
        elif len(examples[(root, cls)]) < 200: examples[(root, cls)].append((root, cls, why, line[:400]))
    summary[root] = dict(total=sum(c.values()), product=c["product"], historical=c["historical"], false_positive=c["false_positive"], unclassified=c["UNCLASSIFIED"])
json.dump(summary, open(f"{G}/summary-draft.json", "w"), indent=1)
json.dump(uncl, open(f"{G}/unclassified.json", "w"), indent=1)
with open(f"{G}/examples-draft.tsv", "w") as f:
    f.write("root\tclass\treason\thit\n")
    for rows in examples.values():
        for r in rows: f.write("\t".join(x.replace("\t", " ") for x in r) + "\n")
print(json.dumps(summary)); print(len(uncl))
