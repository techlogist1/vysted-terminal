# RS-1 — research on a micro-cap across lanes (investor lens)

Target: Sunraj Diamond Exports (BSE micro-cap, prompt quoted market cap about ₹6.63 cr). Source sidecar :52381 (final-cand d38b5d1a).
Raw: raw/investor/rs1-openai.*, rs1-ollama-normal.*, rs1-ollama-deep.*.

## OpenAI gpt-4o-mini, normal
Grounded: price ₹12.44 from the quote leg; fundamentals leg rate-limited by Yahoo (429) and the brief says so; no invented figure. Pass.

## Ollama llama3.1:8b, normal
Brief claims news coverage while the news leg returned empty -> known limitation instance investor:kl-2 (R15-LEAD-030, DECISIONS 4.9-4.12).

## Ollama llama3.1:8b, deep
- Escalated in place (IterResearch loop, depth deep). Wall budget is 180 s (research/depth.py); run took 259 s, a 79 s overrun.
  The loop guards new rounds and the audit with remaining_wall but synthesis is not boxed (research/iter.py, deep.py) -> investor:11 (low).
- Brief figures: market cap "₹66.31 cr" vs ₹6.63 cr (10x), "₹45.25 cr [7]", an unverified net profit -> known limitation instance
  investor:kl-1 (R15-LEAD-037). Local-model fabrication is R4, not filed as a defect.

VERDICT RS-1: finding investor:11
