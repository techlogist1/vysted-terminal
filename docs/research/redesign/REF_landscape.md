# Landscape reference — AI-native finance terminal

> Research brief for the Vysted redesign. Scope: Bloomberg/Refinitiv UX
> conventions worth borrowing (and avoiding), the "Cursor for X" product
> framing, comparable products, and the hybrid dual-mode (dense pro station +
> JARVIS agent) thesis. Concludes with where Vysted differentiates.
>
> Compiled 2026-05-30 via fan-out web research. Every non-obvious claim is
> sourced inline. Confidence flags per section.

---

## TL;DR

- **Bloomberg's real moat is the command grammar, not the chrome.** Borrow the
  command-line + mnemonic function-code model and keyboard-first determinism.
  Do **not** borrow the hazing UI (black/amber, 86-page manual, friction-as-
  prestige). Bloomberg can charge for pain because it has lock-in; a challenger
  cannot.
- **"Cursor for finance" is a trap if taken literally.** Coding won an unusual
  lottery (objective verifiability, a forkable platform, a tight data flywheel,
  uncompressed margins). Finance shares almost none of those. The transferable
  lesson is *rebuild the workspace around the agent*, not *bolt a chat box on*.
- **The category is already contested, and one competitor is uncomfortably
  close.** OpenBB owns the open-source-AI-finance narrative at the enterprise
  layer. **Fincept Terminal is a near-clone of Vysted's exact positioning** —
  AGPL-3.0 + commercial, named-investor LLM agents, local LLM/BYOK, plugin-ish
  data connectors. Vysted must differentiate on something Fincept and OpenBB
  structurally can't copy fast.
- **The dual-mode thesis is sound but the failure mode is well-documented:**
  the "conversation trap." The agent should do the ambiguous upfront work and
  *hand off to a manipulable dense surface* — chat is the on-ramp, not the
  workspace.

---

## 1. Bloomberg / Refinitiv UX conventions

### 1.1 The command grammar (borrow this)

Bloomberg's interaction model is a **command-line + mnemonic function-code
grammar**, not a menu tree. A canonical command is:

```
TICKER <yellow market key> FUNCTION-CODE <GO>
e.g.  AMZN  <EQUITY>  DES  <GO>   →  Amazon equity description page
```

- `<GO>` is the action/enter key; every command terminates with it. Yellow keys
  scope the asset class (EQUITY, GOVT, CMDTY, CRNCY…); black keys type the
  query; green keys act (`<GO>`, `<MENU>`, `<HELP>`).
  ([NYIT LibGuide](https://libguides.nyit.edu/c.php?g=1054896&p=7662441),
  [FGCU keyboard](https://library.fgcu.edu/bloomberg/keyboard),
  [Cornell](https://guides.library.cornell.edu/bloomberg_intro/keyboard))
- **Each function has a short mnemonic** (`DES`, `GP`, `FA`, `N`, `TOP`) so a
  power user jumps straight to a screen without traversing menus. "Users can
  search by function code directly in the command bar to eliminate menu
  navigation steps." ([NYIT](https://libguides.nyit.edu/c.php?g=1054896&p=7662441))
- The payoff Bloomberg's own designers cite: "Bloomberg's bespoke keyboard and
  command language enable **rapid, deterministic navigation without mousing
  through nested menus**, and shortcuts scale better for power users than menu
  hierarchies." ([UX Magazine](https://uxmag.com/articles/the-impossible-bloomberg-makeover))

**Why it works:** it's a *language*, not a UI. Once internalized, throughput is
muscle-memory and resolution is deterministic — the same keys always reach the
same screen. This is the single most worth-stealing idea, and it maps cleanly
onto a modern command palette (§4.1).

### 1.2 Dense multi-panel layout (borrow selectively)

Bloomberg power users run **multi-monitor, multi-panel** workspaces where many
live data surfaces coexist, optimizing for "moneymaking multi-monitor mayhem"
rather than calm minimalism
([Core77](https://www.core77.com/posts/24893/moneymaking-multi-monitor-mayhem-and-why-some-prefer-interface-design-that-sucks-24893)).
Density is a feature for the target user — a trader scanning ten things at once
does not want whitespace. Borrow the **panel density and the everything-at-a-
glance cockpit**; this is already Vysted's dockview 5-panel model.

### 1.3 What to deliberately NOT copy

The hazing is not the moat — the lock-in is. Specific anti-patterns:

- **Friction-as-prestige.** "The more painful the UI is, the more satisfied
  these users are… the pain inflicted by UI flaws is transformed into the
  rewarding experience of feeling like a hard-core professional."
  ([UX Magazine](https://uxmag.com/articles/the-impossible-bloomberg-makeover)).
  Bloomberg can monetize pain *because it already won*; a challenger that ships
  pain just loses.
- **Hostile onboarding.** Black background + amber/orange text, an "86-page
  manual," and "a week and a few painful hours" to basic competency even for a
  finance-literate user
  ([UX Magazine](https://uxmag.com/articles/the-impossible-bloomberg-makeover)).
  G2 reviewers repeatedly cite "difficult navigation" and "information overload"
  making it "difficult to extract specific answers efficiently"
  ([G2](https://www.g2.com/products/bloomberg-terminal/reviews?qs=pros-and-cons)).
- **Redesign paralysis.** Bloomberg rejected IDEO's 2007 redesign and stays
  "religiously consistent" so "you can see a Bloomberg from a mile away"
  ([UX Magazine](https://uxmag.com/articles/the-impossible-bloomberg-makeover)).
  That is a dominant incumbent's luxury, not a design principle.
- **Price/access wall.** ~$24k–$32k/yr per seat puts it out of reach for
  retail and most small funds
  ([Pineify TV-vs-Bloomberg](https://pineify.app/resources/blog/bloomberg-terminal-vs-tradingview-2025-comparison-for-traders-analysts-and-teams),
  [AlphaSense alternatives](https://www.alpha-sense.com/compare/alternatives-to-bloomberg-terminal/)).
  This is precisely the wedge every open-source alternative attacks.

**Design rule for Vysted:** keep Bloomberg's *grammar and density*; replace its
*discoverability tax* with a command palette that teaches its own shortcuts
(Superhuman model, §4.1) and progressive disclosure so novices aren't gated
behind a manual.

*Confidence: 9/10 — command-grammar and criticism claims are corroborated
across library guides, UX Magazine, and G2.*

---

## 2. The "Cursor for X" framing

### 2.1 What actually made Cursor work

The defensible thesis is **rebuild the tool around AI from the first principle**,
not bolt AI onto an existing tool: "Rather than bolting AI onto an existing
editor through an extension, the thesis was to rebuild the editor around AI from
the start… new capabilities in AI demand new innovation in AI UX (and AI UX can
be a viable moat)."
([Latent Space / Cursor](https://www.latent.space/p/cursor))

The compounding loop ("data flywheel") is the deeper moat: "They have the traces
of the agents… the prompt, the outputs, the edits/acceptances/rejections. Over
time that becomes extremely valuable proprietary training data. Better product →
more usage → more traces → better model → better product."
([Tanay Jaipuria](https://www.tanayj.com/p/ai-applications-and-vertical-integration))

### 2.2 Why "Cursor for X" usually fails to transfer

Coding won an unusual lottery: "Cursor's path can't be cut-and-pasted easily
into other verticals because a **staggering number of tailwinds and lucky breaks
factored in**."
([nextword](https://nextword.substack.com/p/heres-why-cursor-for-x-doesnt-work)).
The breaks that don't transfer to finance:

| Coding tailwind | Finance reality |
|---|---|
| **Objective verifiability** — code runs or it doesn't; tests are ground truth. | Investment outcomes are probabilistic, delayed, and noisy. "When hallucination rates go beyond 30%… users quit even when later outputs improve" ([arXiv 2507.19183](https://arxiv.org/pdf/2507.19183) via search). No compiler to catch a wrong number. |
| **A forkable platform (VSCode).** | No comparable open substrate; you build the workspace yourself. |
| **Tight data flywheel from accept/reject traces.** | Buy-side users won't surface proprietary research as training data; privacy is the *product*, not exhaust. |
| **Uncompressed margins.** | Data licensing and compliance compress the model. |

The transferable conditions a vertical-AI product still needs: **transformative
ROI (not incremental), a clear verification mechanism, and deep workflow
ownership** — "deep vertical specialization with rich domain context… that only
comes from focusing on specific professional communities"
([nextword](https://nextword.substack.com/p/heres-why-cursor-for-x-doesnt-work),
[Tanay Jaipuria](https://www.tanayj.com/p/ai-applications-and-vertical-integration)).

**Implication for Vysted:** lead with "AI-native finance workspace," not
"Cursor for finance." The literal analogy invites the wrong scoring. The thing
to actually copy is the *architecture-first* posture — agent + tools + workspace
co-designed (which Vysted's plugin contract already does), and a verification
surface (citations, audit log, deterministic data) standing in for coding's
compiler.

*Confidence: 8/10 — the headline "Cursor-for-X is hard" piece is partly
paywalled; thesis corroborated by Latent Space and Tanay Jaipuria.*

---

## 3. Comparable products / competitors

### 3.1 The direct threat: Fincept Terminal

**Fincept is the closest thing to Vysted in the wild, and the overlap is
alarming.** Per its README
([GitHub](https://github.com/Fincept-Corporation/FinceptTerminal),
[fincept.in](https://fincept.in/)):

- **Same license posture:** dual-licensed **AGPL-3.0 + Fincept Commercial
  License** — personal/academic free, business/SaaS/hedge-fund use requires a
  paid license (liquidated damages from $50k/org/yr).
- **Same agent gimmick:** ships **37 named-investor LLM agents** — Buffett,
  Graham, Lynch, Munger, Klarman, Marks — across Trader/Investor, economic, and
  geopolitics frameworks. (Vysted's first-party roster is nearly identical:
  Buffett, Dalio, Druckenmiller, Graham, Klarman, Lynch, Marks, Munger…)
- **Same BYOK/local-LLM stance:** OpenAI, Anthropic, Gemini, Groq, DeepSeek,
  OpenRouter, **Ollama (local models)**.
- **Same data breadth:** 100+ connectors (FRED, IMF, World Bank, DBnomics,
  Yahoo, Polygon, Kraken), QuantLib pricing modules, node-editor workflow, MCP
  tool integration, 16 broker integrations incl. Zerodha/IBKR/Alpaca.
- **Different desktop tech:** native **C++20 + Qt6 + embedded Python**, single
  binary (vs. Vysted's Tauri + Next.js + Python sidecar).

**Where Fincept is weak (Vysted's openings):** the GitHub repo shows recurring
load errors (maturity signal); build requires exactly-pinned toolchain versions
(CMake 3.27.7 / Qt 6.8.3 / Python 3.11.9 — "newer or older versions are
unsupported") which throttles contribution; Docker is CI-only; no real-time
data-quality / latency story; roadmap is vague
([GitHub README analysis](https://github.com/Fincept-Corporation/FinceptTerminal)).
The C++/Qt stack is fast but **hostile to a plugin ecosystem and to web-stack
contributors** — the exact friction Vysted's TS/React + Tauri stack avoids.

> This is the most important finding in this brief. Vysted cannot position as
> "the open-source AGPL finance terminal with investor agents" — that slot is
> taken. The differentiation has to be the *plugin platform + dual-mode UX +
> contributor accessibility*, not the agents-and-license combo.

### 3.2 OpenBB — owns the enterprise AI-finance narrative

- Reframed from a Python CLI to an **"Agentic Workspace for Finance"**; the
  **OpenBB Copilot** is "the first AI-powered financial analyst integrated into
  a financial terminal," using **function calling** to read dashboard widgets
  and answer questions about visualized data
  ([OpenBB Workspace](https://openbb.co/products/workspace/),
  [dro-lopes Medium](https://dro-lopes.medium.com/introducing-the-first-ai-financial-terminal-664f8e371d9c)).
- **Bring Your Own Copilot:** firms plug in a fine-tuned/RAG LLM so "research
  queries and data stay securely within your firm's infrastructure"; the
  integration repo is open-sourced
  ([OpenBB docs](https://docs.openbb.co/workspace/bring-your-own-copilot),
  [copilot-for-openbb](https://github.com/OpenBB-finance/copilot-for-openbb)).
- **Data-layer play (ODP):** "connect once, consume everywhere" — exposes data
  to Python, the Workspace, Excel, **MCP servers**, and REST simultaneously
  ([OpenBB blog](https://openbb.co/blog/introducing-the-new-openbb-terminal/)).
- **Validation:** BlackRock's Aladdin Copilot arrived at "remarkably similar"
  conclusions — multi-app support, agent integration, explainable AI, enterprise
  security — but closed; OpenBB frames itself as the open equivalent
  ([Didier Lopes](https://didierlopes.com/blog/2025-03-11-the-10-trillion-openbb-copilot-validation/)).

**OpenBB's gap:** it is **enterprise/cloud-workspace-shaped and data-broker
positioned**, MIT-permissive core, not a local-first desktop app. It is weakest
on **single-user, local-first, keyboard-native desktop** and on a **panel/plugin
sandbox** — those are Vysted-shaped.

### 3.3 The rest of the field

- **BloombergGPT** — a 50B-param finance-domain LLM that "outperforms existing
  open models of similar size on financial tasks by large margins"
  ([Bloomberg press](https://www.bloomberg.com/company/press/bloomberggpt-50-billion-parameter-llm-tuned-finance/)).
  It's a *model*, locked inside the $24k terminal — not a product surface you
  compete with on UX. Relevant only as proof the incumbent is going AI-native.
- **AlphaSense** — enterprise market-intelligence + AI search; "the only tool
  that combines public and private financial data with expert call transcripts,
  broker research, news, and AI search," "Generative Search… with Deep Research,"
  "10+ years of investment in AI"
  ([AlphaSense](https://www.alpha-sense.com/compare/alphasense-vs-perplexity/),
  [alternatives roundup](https://www.alpha-sense.com/compare/alternatives-to-bloomberg-terminal/)).
  Closed, document-intelligence-shaped; not local, not extensible.
- **TradingView** — democratized charting/screeners at **$0–$60/mo**; Pine
  Script + the new **Pine Screener** (scan watchlists with custom scripts) is its
  programmability story; AI is third-party-bolt-on (AI-Signals indicators), not
  native
  ([Pineify](https://pineify.app/resources/blog/tradingview-ai-indicator-revolutionizing-technical-analysis-in-2025),
  [TV Pine Screener](https://www.tradingview.com/pine-screener/)).
  Strong on charts/community, weak on agentic research and fundamentals depth.
- **Koyfin** — budget data-viz ($0 / $15 / $35 / $70 mo), "user-friendly… in-
  depth qualitative data"; no agentic AI story
  ([AlphaSense alternatives](https://www.alpha-sense.com/compare/alternatives-to-bloomberg-terminal/)).
- **Perplexity Finance** — strong live-retrieval Q&A ("94% accuracy on stock
  queries… vs ChatGPT's 81%" per LMSYS testing cited in coverage), but it's a
  *chat answer engine*, not a workspace — no panels, no execution, no plugins
  ([Global GPT](https://www.glbgpt.com/hub/perplexity-finance-review-2025/),
  [NowNews](https://nownews.dev/blog/chatgpt-perplexity-financial-news-investors-2026)).
- **General consensus** across the comparison coverage: the closest *retail*
  approximation of Bloomberg today is the **hybrid** of a specialized data
  platform **+** an AI chatbot — exactly the seam Vysted targets by putting both
  in one app
  ([NowNews](https://nownews.dev/blog/chatgpt-perplexity-financial-news-investors-2026)).

### 3.4 Positioning map

| Product | Open? | Local-first | AI-native | Plugin platform | Keyboard-native | Desktop |
|---|---|---|---|---|---|---|
| Bloomberg | No | Thin client | Bolted (BloombergGPT) | No | **Yes** (grammar) | Yes |
| OpenBB | Core MIT | No (workspace/cloud) | **Yes** (Copilot) | Widgets/data | Partial | No (web) |
| **Fincept** | AGPL+comm | **Yes** | **Yes** (agents) | Connectors | Partial | Yes (Qt) |
| AlphaSense | No | No | **Yes** (search) | No | No | No |
| TradingView | No | No | Bolted | Pine scripts | Partial | Web/app |
| Perplexity Fin | No | No | **Yes** (chat) | No | No | No |
| **Vysted (target)** | **AGPL+comm** | **Yes** | **Yes** | **Full contract** | **Yes (palette)** | **Yes (Tauri)** |

The only row that fills *every* column is Vysted's target — but Fincept is one
weak-stack away from it, so the moat must be the **plugin contract + dual-mode
UX + web-stack extensibility**, not the checklist alone.

*Confidence: 8/10 — Fincept/OpenBB/TradingView claims are first-source; the
Perplexity accuracy figures are second-hand from review aggregators (treat as
directional).*

---

## 4. The hybrid dual-mode thesis (dense pro station + JARVIS agent)

### 4.1 Prior art for the "pro" half: keyboard-first command palette

The modern analogue to Bloomberg's `<GO>` grammar is the **Cmd-K command
palette** — "a keyboard-driven search interface that lets users find and execute
actions without navigating menus," now standard in Linear, Superhuman, Slack,
Figma, Notion
([Mobbin](https://mobbin.com/glossary/command-palette),
[UX Patterns](https://uxpatterns.dev/patterns/advanced/command-palette)).
Superhuman's design lesson is directly applicable: **"one shortcut rules them
all: Cmd+K… do any action — and also learn the shortcut for next time."**
([Superhuman](https://blog.superhuman.com/how-to-build-a-remarkable-command-palette/)).
That last clause is the antidote to Bloomberg's 86-page manual: the palette
*teaches its own mnemonics* instead of gating them behind documentation.

### 4.2 Prior art for the "agent" half: ask vs. agent modes

The two-speed agent split is now a shipped convention. GitHub Copilot
distinguishes **Ask** (answers, never touches your workspace) from **Agent**
(autonomously plans multi-step work, edits, runs, self-corrects)
([GitHub blog](https://github.blog/ai-and-ml/github-copilot/copilot-ask-edit-and-agent-modes-what-they-do-and-when-to-use-them/),
[.NET blog](https://devblogs.microsoft.com/dotnet/ask-mode-vs-agent-mode/)).
ChatGPT exposes Auto/Fast/Thinking modes in the same spirit
([search synthesis](https://www.designative.info/2026/03/23/beyond-the-conversation-trap-designing-for-hybrid-human-agent-interaction-modes/)).

**Pitfall to design around:** mode discoverability. Copilot's mode switcher is "a
tiny dropdown hiding at the bottom… easy to miss," and "most developers pick the
wrong one half the time"
([GitHub blog](https://github.blog/ai-and-ml/github-copilot/copilot-ask-edit-and-agent-modes-what-they-do-and-when-to-use-them/)).
If Vysted ships Ask/Agent modes, the mode must be *obvious and consequence-
explained* at the point of use, not buried.

### 4.3 The central pitfall: the "conversation trap"

The strongest design warning for a JARVIS-style agent is that **pure chat is the
wrong primary surface for complex, manipulable work.** The pattern that works:
*"The agent handles the ambiguous, language-heavy work upfront — gathering
inputs, synthesising context, surfacing a starting point — then hands off to a
visual, manipulable interface for the actual work."*
([Designative](https://www.designative.info/2026/03/23/beyond-the-conversation-trap-designing-for-hybrid-human-agent-interaction-modes/)).

Forcing everything through chat is slow, lossy, and hides state — a trader can't
"scan ten things at once" in a transcript. So the dual-mode is not *chat OR
panels*; it's **chat as the on-ramp that populates and drives the dense panel
cockpit.** The agent should open panels, set the chart, load the watchlist,
stage an order — then step back and let the user manipulate directly. This is the
correct reading of "dense pro station + JARVIS," and it's exactly what OpenBB's
Copilot does (function-calling reads/writes widgets), so it is proven, not
speculative ([OpenBB](https://dro-lopes.medium.com/introducing-the-first-ai-financial-terminal-664f8e371d9c)).

### 4.4 The trust pitfall specific to finance

Finance has a low hallucination tolerance and a regulatory edge: "incorrect
information given by an AI chatbot can constitute a UDAAP violation"
([fin.ai](https://fin.ai/learn/evaluate-ai-agent-compliance-financial-services)),
Deloitte found "38% of executives… made incorrect decisions based on hallucinated
outputs," and trust collapses non-linearly past ~30% error
([arXiv 2507.19183](https://arxiv.org/pdf/2507.19183) and survey coverage).
Mitigations the literature converges on — **enforced source citations,
multi-model consensus, and a verifiable audit trail** — are the agent-era stand-
in for coding's compiler. Vysted already has the audit-log + §6.5 safety layer;
extending **mandatory citation-on-claim** into the chat surface is the matching
trust primitive.

*Confidence: 8/10 — dual-mode and conversation-trap patterns are well-sourced;
the JARVIS-for-finance combination is inferred prior art (OpenBB Copilot is the
nearest shipped instance), not a documented named pattern.*

---

## 5. Where Vysted differentiates

The category is crowded at the edges but the *center* — a **local-first,
keyboard-native, fully-plugin-extensible AI-native desktop terminal** — is
unoccupied. No single competitor holds it: OpenBB is cloud/enterprise-shaped,
Fincept is the same idea on a closed-to-contributors C++/Qt stack, Bloomberg is
the $24k incumbent going AI-native from the inside, and the chatbots (Perplexity,
ChatGPT) have no workspace. Concretely, Vysted should own:

1. **The plugin platform, not the agents.** The named-investor agents and
   AGPL+commercial license are *already cloned by Fincept* — they are table
   stakes, not a moat. The defensible asset is the **six-capability plugin
   contract** (`types/plugin.ts`) on a **web stack any TS/React dev can extend**.
   Fincept's Qt/C++ single-binary is fast but a contributor wall; Vysted's
   sandbox is the ecosystem play OpenBB (data-broker) and Fincept (closed stack)
   can't easily match. *Lead with: "the extensible AI-native terminal."*

2. **Command grammar reborn as a teaching palette.** Steal Bloomberg's
   deterministic command grammar (`TICKER · function · <GO>`), implement it as a
   Cmd-K palette that *teaches its own mnemonics* (Superhuman pattern) — getting
   Bloomberg's power-user throughput **without** the 86-page-manual onboarding
   tax. This is a UX moat per the Cursor thesis (AI-era UX as moat) and no
   competitor in §3 has it: OpenBB/Fincept are mouse-and-widget, the chatbots
   have no grammar.

3. **Dual-mode done right: agent populates, user manipulates.** Ship Ask/Agent
   modes with *obvious* mode switching (avoid Copilot's hidden-dropdown
   pitfall), and make the agent's job to *drive the dense cockpit* — open
   panels, set charts, stage orders — then hand off (escape the conversation
   trap). The agent is the on-ramp to the pro station, not a parallel chat silo.

4. **Local-first + BYOK as the privacy moat.** This is the one place the data
   flywheel *inverts* in the user's favor: where coding-agent value came from
   harvesting traces, buy-side finance value comes from **guaranteeing traces
   never leave the machine.** "Your keys, your model, your data, on your box" is
   a claim OpenBB's cloud workspace and the hosted chatbots structurally cannot
   make, and it's the credible answer to the finance-hallucination/compliance
   anxiety in §4.4 (paired with mandatory citations + the existing audit log).

5. **Verification as the compiler-substitute.** Finance has no compiler, so the
   trust surface *is* the product. Mandatory citation-on-claim, the append-only
   audit log, deterministic data provenance, and the §6.5 execution safety layer
   together form the "verifiability" that the Cursor thesis says a vertical-AI
   product must manufacture when the domain doesn't hand it over for free.

**In short:**
- The "open-source AGPL terminal with investor agents + BYOK" slot is **already
  occupied by Fincept** — do not anchor positioning there.
- Vysted's white space is the **extensible plugin platform on a web stack + a
  teaching command palette + agent-drives-cockpit dual mode + local-first
  privacy/verification** — a combination no competitor holds.
- Frame as **"the AI-native, extensible finance workspace,"** not "Cursor for
  finance" (the literal analogy invites the wrong, verifiability-based scoring).
- Confidence: 8/10 — strong on competitor facts and UX prior art; the Fincept-
  overlap severity is the highest-leverage finding and is first-source.

---

## Sources

**Bloomberg UX**
- [NYIT — Bloomberg keys](https://libguides.nyit.edu/c.php?g=1054896&p=7662441)
- [FGCU — Bloomberg keyboard](https://library.fgcu.edu/bloomberg/keyboard)
- [Cornell — the keyboard](https://guides.library.cornell.edu/bloomberg_intro/keyboard)
- [UX Magazine — The Impossible Bloomberg Makeover](https://uxmag.com/articles/the-impossible-bloomberg-makeover)
- [Core77 — multi-monitor mayhem](https://www.core77.com/posts/24893/moneymaking-multi-monitor-mayhem-and-why-some-prefer-interface-design-that-sucks-24893)
- [G2 — Bloomberg Terminal pros/cons](https://www.g2.com/products/bloomberg-terminal/reviews?qs=pros-and-cons)

**Cursor-for-X / vertical AI**
- [nextword — Why "Cursor for X" doesn't work](https://nextword.substack.com/p/heres-why-cursor-for-x-doesnt-work)
- [Latent Space — Cursor / Aman Sanger](https://www.latent.space/p/cursor)
- [Tanay Jaipuria — AI applications & vertical integration](https://www.tanayj.com/p/ai-applications-and-vertical-integration)

**Competitors**
- [Fincept Terminal — GitHub](https://github.com/Fincept-Corporation/FinceptTerminal) · [fincept.in](https://fincept.in/)
- [OpenBB Workspace](https://openbb.co/products/workspace/) · [Introducing the new OpenBB Workspace](https://openbb.co/blog/introducing-the-new-openbb-terminal/) · [Bring Your Own Copilot docs](https://docs.openbb.co/workspace/bring-your-own-copilot) · [copilot-for-openbb](https://github.com/OpenBB-finance/copilot-for-openbb)
- [Didier Lopes — $10T OpenBB Copilot validation](https://didierlopes.com/blog/2025-03-11-the-10-trillion-openbb-copilot-validation/) · [First AI-financial terminal (Medium)](https://dro-lopes.medium.com/introducing-the-first-ai-financial-terminal-664f8e371d9c)
- [Bloomberg press — BloombergGPT](https://www.bloomberg.com/company/press/bloomberggpt-50-billion-parameter-llm-tuned-finance/)
- [AlphaSense — Bloomberg alternatives](https://www.alpha-sense.com/compare/alternatives-to-bloomberg-terminal/) · [AlphaSense vs Perplexity](https://www.alpha-sense.com/compare/alphasense-vs-perplexity/)
- [TradingView — Pine Screener](https://www.tradingview.com/pine-screener/) · [Pineify — TV vs Bloomberg](https://pineify.app/resources/blog/bloomberg-terminal-vs-tradingview-2025-comparison-for-traders-analysts-and-teams)
- [Global GPT — Perplexity Finance review](https://www.glbgpt.com/hub/perplexity-finance-review-2025/) · [NowNews — ChatGPT/Perplexity for investors](https://nownews.dev/blog/chatgpt-perplexity-financial-news-investors-2026)

**Dual-mode / command palette / trust**
- [Mobbin — Command Palette](https://mobbin.com/glossary/command-palette) · [UX Patterns — Command Palette](https://uxpatterns.dev/patterns/advanced/command-palette) · [Superhuman — remarkable command palette](https://blog.superhuman.com/how-to-build-a-remarkable-command-palette/)
- [GitHub blog — ask/edit/agent modes](https://github.blog/ai-and-ml/github-copilot/copilot-ask-edit-and-agent-modes-what-they-do-and-when-to-use-them/) · [.NET blog — ask vs agent](https://devblogs.microsoft.com/dotnet/ask-mode-vs-agent-mode/)
- [Designative — Beyond the conversation trap](https://www.designative.info/2026/03/23/beyond-the-conversation-trap-designing-for-hybrid-human-agent-interaction-modes/)
- [arXiv 2507.19183 — Agentic AI and hallucinations](https://arxiv.org/pdf/2507.19183) · [fin.ai — AI agent compliance for financial services](https://fin.ai/learn/evaluate-ai-agent-compliance-financial-services)
