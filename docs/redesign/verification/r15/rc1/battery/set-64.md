# batch-13/W2-w2

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-RESEARCH-007 | In-process `domain_tier(url)` against the candidate's own venv (`sidecar/services/research/finance.py`), replaying batch-12's exact acceptance/regression URL list (18 adversarial hosts across the original heuristic gap, the 9-platform denylist gap, and the ccSLD-registrable-domain gap; plus the 4 first-party IR controls) | All 18 adversarial URLs (`investors.com` news path, `investors.github.io`, `ir.blogspot.in`, `investors.wixsite.com`, `ir.netlify.app`, `investors.hubpages.com`, `ir.firebaseapp.com`, `investors.web.app`, `ir.azurewebsites.net`, `ir.onrender.com`, `ir.fly.dev`, `ir.glitch.me`, `investors.notion.site`, `ir.webflow.io`, `ir.herokuapp.com`, `investors.co.uk`, `ir.co.in`, `investors.com.au`) return tier `3` (not `TIER_PRIMARY`); all 4 controls (`ir.nvidia.com`, `investors.infosys.com`, `investor.apple.com`, `ir.tatamotors.com`) return tier `1` (`TIER_PRIMARY`) — matches batch-14's certified PSL-backed fix exactly, including the ccSLD (`.co.uk`/`.co.in`/`.com.au`) and private-PSL-suffix (`github.io`, `web.app`, `herokuapp.com`, etc.) cases that batch-3 and batch-12 both failed on | holds |

Evidence: `raw/set-64/R15-RESEARCH-007-live.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
