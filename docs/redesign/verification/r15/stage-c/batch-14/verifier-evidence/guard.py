import json
from services.agent_runtime import _guard_ratio_claims as g, RATIO_UNAVAILABLE as R
fund = [json.dumps({"symbol":"SIFY","name":"Sify Technologies Ltd","sharesOutstanding":144869230,"revenue":46510000000,"currency":"INR","pe":None})]
web = [json.dumps({"results":[{"title":"Sify Technologies Ltd ADS (Each Repr 6 Ords)","url":"x"}]})]
cases = [
 ("R","Each American depositary receipt is worth four ordinary shares."),
 ("R","The depositary ratio stands at 1-for-6."),
 ("K","SIFY ADR volume was 120,000 shares today."),
 ("R","One SIFY ADS is backed by ten equity shares."),
 ("R","Holders receive 3 ordinary shares per ADS."),
 ("R","1 ADR = 6 shares."),
 ("R","One ADR is worth 10 shares of Sify."),
 ("R","A single SIFY ADR gives you 2 shares."),
 ("R","According to fundamentals data, the ADR ratio is 1:1."),
 ("R","Each ADS represents two ordinary shares (per fundamentals data)."),
 ("R","SIFY ADRs trade at a 1:2 ratio to ordinary shares."),
 ("R","The ADS-to-ordinary ratio is 1 to 10."),
 ("K","Each ADR closed at 5.20 USD on Friday."),
 ("K","Each ADS's 52-week high was 12.4."),
 ("K","SIFY's ADSs each gained 3 points in 2024."),
 ("K","SIFY files a 20-F each year for its ADSs."),
 ("K","TTM revenue was ₹4,651 cr, about USD 556 million; each ADR is listed on Nasdaq."),
 ("K","The PE ratio is 22.4."),
]
bad=0
for exp,s in cases:
    out=g(s,fund); rep = R in out
    ok = rep == (exp=="R")
    bad += not ok
    print(("ok " if ok else "BAD"), exp, "replaced" if rep else "kept   ", "|", s)
print("traced-kept:", g("The ADR-to-share ratio is 1 ADR : 6 shares.", web))
print("traced 1-for-6 web:", g("The depositary ratio stands at 1-for-6.", web))
print("untraced 1:10 vs web:", g("Each ADS represents 10 ordinary shares.", web))
print("bad",bad)
