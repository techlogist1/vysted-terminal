# Refutation audit: R15-RESEARCH-007 (group research)

- **Verdict:** partial
- **HEAD:** `6741387b` at start, then `91dac548` (docs-only). `finance.py` is unchanged.
- **Certified by:** stage-c batch-3 `VERDICTS.md:146`. Medium and WordPress both returned 3, Reuters 2, `ir.substack.com` and `investor.medium.com` both 3, and `investors.infosys.com` and `ir.tatamotors.com` both 1.
- **Refuted by:** `rc1-verifier:5` (`inproc-refutations.txt`). `www.investors.com` (IBD news), `ir.hotpennypicks.net`, `investors.github.io` and `ir.blogspot.in` all return 1 (PRIMARY), and Reuters returns 2.

## Commands

```
cd sidecar && PYTHONPATH=. .venv/bin/python $SCRATCH/refaudit-research/r007.py
## entry repro
https://medium.com/investor-diary/why-i-bought-xyz -> 3
https://someblog.wordpress.com/ir/2024/hot-tip -> 3
https://reuters.com/markets/x -> 2
https://www.reuters.com/markets/investors-rush -> 2
rank_sources -> ['Reuters', 'Blog']
priority_note -> 'Citation preference — when several sources support a claim, cite the most authoritative: tier-1 press: [1].'
rank_sources wp -> ['Reuters', 'WP'] 'Citation preference — when several sources support a claim, cite the most authoritative: tier-1 press: [1].'
## verifier refutation
https://medium.com/investor-diary/x host= medium.com -> 3
https://www.investors.com/news/technology/nvidia-stock-buy-now/ host= investors.com -> 1
https://ir.hotpennypicks.net/2024/xyz host= ir.hotpennypicks.net -> 1
https://investors.github.io/pump host= investors.github.io -> 1
https://ir.blogspot.in/post host= ir.blogspot.in -> 1
https://investor.apple.com/sec-filings/ host= investor.apple.com -> 1
https://www.reuters.com/markets/x host= reuters.com -> 2
## extra probes (same class)
https://ir.substack.com/p/x -> 3
https://investors.wixsite.com/x -> 1
https://ir.netlify.app/x -> 1
https://investor.bitcoin.com/x -> 1
https://investors.hubpages.com/x -> 1
https://ir.nvidia.com/x -> 1
https://investors.infosys.com/x -> 1
https://tcs.com/investor-relations -> 3
rank -> ['IBD', 'GH', 'Reuters'] 'Citation preference — when several sources support a claim, cite the most authoritative: primary record (exchange/regulator/filings/IR): [2, 3]; tier-1 press: [1].'
```

## Reasoning

**The entry's own repro holds at HEAD.**

- The Medium `/investor-diary/` and WordPress `/ir/` URLs both return 3. Reuters and the `/markets/investors-rush` news path both return 2.
- `rank_sources` puts Reuters first.
- `priority_note` no longer calls the blog "primary record".

The path-marker half of the defect is fixed.

**The verifier's refutation reproduces exactly at HEAD**, and my extra probes extend it:

- `investors.wixsite.com`, `ir.netlify.app`, `investors.hubpages.com` and `investor.bitcoin.com` all return 1.
- With Reuters, IBD (`investors.com`) and `investors.github.io`, `rank_sources` gives `['IBD','GH','Reuters']`, and `priority_note` names `[2, 3]` as the primary record.

This is the entry's stated defect ("... or an 'ir.' host is ranked PRIMARY, so a blog outranks Reuters, owns marker [1]"), hitting through the host-prefix half that the fix kept. It is not a new defect.

The failing cases fall into three sub-causes:

1. **`www.investors.com` → PRIMARY.** `domain_of` strips `www.`, giving the bare host `investors.com`. `_looks_like_ir` (`finance.py:143-148`) runs `host.startswith("investors.")` without requiring the prefix to be a subdomain label. So a registrable domain whose own name is `investors` / `investor` / `ir` qualifies. This is a bug introduced by the fix: a real Tier-2/3 news site is ranked as the regulator-grade record.
2. **Publishing platforms missing from the denylist.** `_IR_PLATFORM_DENYLIST` (`finance.py:79-89`) is suffix-matched on exact registrable names. `blogspot.in` (and every other blogspot ccTLD), `github.io`, `wixsite.com`, `netlify.app` and `hubpages.com` are not on it, so a user-hosted `ir.` / `investors.` page on those platforms is PRIMARY. This is the same class as Medium and WordPress, which the fix shape explicitly named.
3. **`ir.hotpennypicks.net`.** Any registrant can create an `ir.` subdomain on their own domain. This is the inherent ceiling of a host-prefix heuristic, which the fix shape accepted. I note it but do not count it as the failing part.

**Verdict: partial.** The stated repro holds, but the stated `ir.`-host part of the same defect class still reaches TIER_PRIMARY for IBD and for several publishing platforms.

## Root cause

- `sidecar/services/research/finance.py:146`: `host.startswith(prefix)` also matches when the IR label is the registrable name itself (`investors.com`).
- `sidecar/services/research/finance.py:79-89`: the denylist omits common publishing platforms and matches blogspot only on `.com`.

## Acceptance test

Add `test_ir_host_prefix_never_promotes_news_or_platform_hosts` to `sidecar/tests/test_research_finance.py`:

- Each of these must satisfy `domain_tier(u) != TIER_PRIMARY`:
  - `https://www.investors.com/news/technology/nvidia-stock-buy-now/`
  - `https://investors.github.io/pump`
  - `https://ir.blogspot.in/post`
  - `https://investors.wixsite.com/x`
  - `https://ir.netlify.app/x`
  - `https://investors.hubpages.com/x`
- `[s.title for s in rank_sources([IBD, GH, Reuters])][0] == 'Reuters'`
- `priority_note` must not list IBD or GH as the primary record.
- These controls must stay TIER_PRIMARY: `ir.nvidia.com`, `investors.infosys.com`, `investor.apple.com`, `ir.tatamotors.com`.

**Fix direction:** require the IR label to sit on a host with at least 3 labels (`host.count('.') >= 2`), and extend or broaden the platform denylist (`blogspot.*`, `github.io`, `wixsite.com`, `netlify.app`, `hubpages.com`, `vercel.app`, `pages.dev`).
