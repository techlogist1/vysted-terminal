# triage-b — rc1-vshard-8:1 (tie R15-RESEARCH-007)

Audited 07:27 IST at HEAD bed3b166. The code tree equals 01015033, and the fix round did not touch sidecar/services/research/finance.py.

## Claim (shard 8)
An `ir.`/`investors.` host on a blogging platform that is neither a PSL suffix nor on the denylist still ranks TIER_PRIMARY. It outranks Reuters and is named the "primary record".

## Code at HEAD
In `sidecar/services/research/finance.py:213-229`, `_looks_like_ir` accepts any host that starts with `ir.`/`investor.`/`investors.`, is not blogspot, is not on `_IR_PLATFORM_DENYLIST` (:89-103, ten enumerated platforms) and is a strict subdomain of its PSL registrable domain. In `:232-241`, `domain_tier` then returns TIER_PRIMARY. A user-hostable platform that is not a PSL private suffix and is not enumerated therefore passes. Its registrable domain is the platform itself (ghost.io), and the `investors.` label is a "subdomain" of it.

## Repro at HEAD (in-process)
Command: `cd sidecar && ./.venv/bin/python /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/r007/probe.py`
```
rank_sources sig: (sources: 'list[ResearchSource]') -> 'list[ResearchSource]'
priority_note sig: (sources: 'list[ResearchSource]') -> 'str'
== LITERAL
   3 https://medium.com/investor-diary/why-i-bought-xyz registrable= medium.com
   3 https://someblog.wordpress.com/ir/2024/hot-tip registrable= wordpress.com
   2 https://reuters.com/markets/x registrable= reuters.com
== CONTROL
   1 https://ir.nvidia.com/ registrable= nvidia.com
   1 https://investors.infosys.com/ registrable= infosys.com
   1 https://investor.apple.com/ registrable= apple.com
   1 https://ir.tatamotors.com/ registrable= tatamotors.com
== FRESH
   1 https://investors.ghost.io/x registrable= ghost.io
   1 https://ir.hashnode.dev/x registrable= hashnode.dev
   1 https://investors.beehiiv.com/p/x registrable= beehiiv.com
   1 https://investors.tistory.com/1 registrable= tistory.com
   1 https://ir.livejournal.com/x registrable= livejournal.com
   1 https://ir.over-blog.com/x registrable= over-blog.com
   1 https://ir.quora.com/x registrable= quora.com
   1 https://ir.mystrikingly.com/ registrable= mystrikingly.com
   1 https://ir.webnode.page/ registrable= webnode.page
   1 https://investors.jimdosite.com/ registrable= jimdosite.com
   1 https://ir.site123.me/ registrable= site123.me
   1 https://ir.typepad.com/x registrable= typepad.com
   1 https://investors.blogger.com/x registrable= blogger.com
   1 https://ir.squarespace.com/x registrable= squarespace.com
   1 https://investors.wix.com/x registrable= wix.com
   3 https://ir.carrd.co/x registrable= ir.carrd.co
   1 https://ir.mailchimpsites.com/x registrable= mailchimpsites.com
RANKED ['GhostBlog', 'HashnodeBlog', 'Reuters', 'Medium']
NOTE Citation preference — when several sources support a claim, cite the most authoritative: primary record (exchange/regulator/filings/IR): [1, 2]; tier-1 press: [3].
```
- The entry's literal repro holds. The medium `/investor-diary` and wordpress `/ir/` URLs are both tier 3, and Reuters is tier 2. The controls ir.nvidia.com, investors.infosys.com, investor.apple.com and ir.tatamotors.com are tier 1.
- The shard's fresh hosts all give tier 1 at HEAD: ghost.io, hashnode.dev, beehiiv.com, tistory.com, livejournal.com, over-blog.com, quora.com (spaces), mystrikingly.com, webnode.page, jimdosite.com, site123.me and typepad.com. My own extra, `ir.mailchimpsites.com`, is also tier 1. (I also probed wix.com, squarespace.com and blogger.com, but I DISCARD them as evidence: `investors.wix.com`/`ir.squarespace.com` can be those companies' real IR sites. carrd.co is a PSL suffix and correctly gives 3.)
- `rank_sources([Reuters, investors.ghost.io, ir.hashnode.dev, Medium])` gives `['GhostBlog', 'HashnodeBlog', 'Reuters', 'Medium']`, and `priority_note` gives "primary record (exchange/regulator/filings/IR): [1, 2]; tier-1 press: [3]". The title claim reproduces word for word on a different host.

## Duplicate search
The register scan for `_looks_like_ir`, 'ir.' host, 'primary record' and source-authority found only R15-RESEARCH-007 (source-authority-heuristic) itself.

## Classification: partial on R15-RESEARCH-007
The fix_shape's own acceptance is "a table test of the reproduced URLs asserting none reaches TIER_PRIMARY and Reuters outranks them", for publishing platforms where anyone can host an `ir.`/`investors.` page. The stated repro URLs pass. The class does not pass on fresh user-hostable platforms. This is the third time an enumerated exclusion (the denylist, then denylist plus PSL) has left the class open. The batch-12 verifier's fresh cases were the previous one.

## Severity: medium (lowered from the shard's and the tie's high)
The exposure is now narrow. Only a site whose whole host label is exactly `ir`/`investor`/`investors` on an un-enumerated, non-PSL platform qualifies, which is at most one such name per platform, and it must also surface in the web round for the company in question. When it does hit, the model is told a blog is the primary record and the blog takes marker [1]. The user sees the source URL in the brief, which is a partial workaround. A stated feature (source-authority ranking) is degraded for a narrow input class; no core flow is broken.

## Certification failures
The baseline for R15-RESEARCH-007 is 2: stage-c batch-12 not_certified plus the rc1 round-1 REFUTATION_AUDIT.json partial. Its note has no clause. This partial adds 1, for a total of 3.
