import json
from services.agent_runtime import _guard_ratio_claims as g, RATIO_UNAVAILABLE as R
fund = [json.dumps({"ok":True,"fundamentals":{"symbol":"SIFY","name":"Sify Technologies Ltd","sharesOutstanding":144869230,"revenue":46510000000,"currency":"USD","financialCurrency":"INR","pe":22.4}})]
web = [json.dumps({"results":[{"title":"Sify Technologies Ltd ADS (Each Repr 6 Ords)","url":"x"}]})]
cover = [json.dumps({"ok":True,"ads_ratio":{"ordinary_shares_per_ads":6,"statement":"American Depositary Shares, each represented by Six Equity Shares","provenance":{"source":"SEC 20-F cover page","filed":"2025-07-15","url":"https://www.sec.gov/x"}},"fundamentals":{"sharesOutstanding":144869230}})]
cases = [
 # bar GUARDED
 ("R","American Depositary Shares each represent six underlying equity shares."),
 ("R","Each ADR is equivalent to 2 shares of common stock."),
 ("R","The ADR-to-share ratio is 1 ADR : 6 shares."),
 ("R","1 ADR = 6 shares."),
 ("R","One ADR is worth 10 shares of Sify."),
 ("R","A single SIFY ADR gives you 2 shares."),
 # bar KEPT
 ("K","Each ADR closed at 5.20 USD on Friday."),
 ("K","Each ADS's 52-week high was 12.4."),
 ("K","SIFY's ADSs each gained 3 points in 2024."),
 ("K","the ADR traded between 10 and 12 dollars."),
 ("K","Each ADR closed at $12.50 on volume of 40,000 shares."),
 ("K","The PE ratio is 22.4."),
 ("K","Revenue represents 12% of the segment."),
 ("K","SIFY filed its 2024 20-F in July."),
 # batch-14 verifier list
 ("R","Each American depositary receipt is worth four ordinary shares."),
 ("R","The depositary ratio stands at 1-for-6."),
 ("K","SIFY ADR volume was 120,000 shares today."),
 ("R","One SIFY ADS is backed by ten equity shares."),
 ("R","Holders receive 3 ordinary shares per ADS."),
 ("R","According to fundamentals data, the ADR ratio is 1:1."),
 ("R","Each ADS represents two ordinary shares (per fundamentals data)."),
 ("R","SIFY ADRs trade at a 1:2 ratio to ordinary shares."),
 ("R","The ADS-to-ordinary ratio is 1 to 10."),
 ("K","SIFY files a 20-F each year for its ADSs."),
 ("K","TTM revenue was ₹4,651 cr, about USD 556 million; each ADR is listed on Nasdaq."),
 ("R","SIFY American Depositary Shares each represent six underlying equity shares."),
 ("R","For SIFY, one ADR is approximately 144869230 ordinary shares."),
 # FRESH fabrications (verifier's own)
 ("R","Every SIFY depositary receipt stands for 3 underlying shares."),
 ("R","Owning a Sify ADS means you hold eight Sify shares."),
 ("R","SIFY: 4 shares per ADS."),
 ("R","The ADR converts into twelve equity shares at the depositary."),
 ("R","Each ADS represents 6 class A shares."),
 ("R","Each ADS represents 5 Class A ordinary shares."),
 ("R","The depositary ratio is six-to-one."),
 ("R","You need 2 ADRs to get one ordinary share."),
 ("R","Each ADS represents 6 ordinary shares of Rs 10 each."),
 ("R","Per the fundamentals data, SIFY's ADS ratio is 1 ADS to 3 shares."),
 ("R","SIFY ADR ratio: 1:4"),
 # FRESH true prose (verifier's own)
 ("K","SIFY's ADR fell 4 percent after the results."),
 ("K","The ADR has traded on Nasdaq since 2000."),
 ("K","SIFY's ADR market capitalisation is about USD 200 million."),
 ("K","SIFY ADRs rose 7% over 5 sessions."),
 ("K","The ADS ranks 3rd among Indian IT ADRs by volume."),
 ("K","Three analysts cover the ADR."),
 ("K","The ADR's 50-day moving average is 5.8."),
 ("K","SIFY's ADSs have 144,869,230 shares outstanding behind them."),
 ("K","SIFY's ADR is one of the few Indian data-centre listings in the US."),
 ("K","Two of the three analysts covering the ADR rate it a buy."),
]
bad=0
for exp,s in cases:
    out=g(s,fund); rep = R in out
    ok = rep == (exp=="R"); bad += not ok
    print(("ok " if ok else "BAD"), exp, "replaced" if rep else "kept   ", "|", s)
print("-- traced")
for s,src,name in [("The ADR-to-share ratio is 1 ADR : 6 shares.",web,"web"),("Each ADS represents six ordinary shares.",web,"web"),
   ("1 ADR : 6 shares",cover,"cover"),("Each ADS represents six ordinary shares.",cover,"cover"),
   ("Per the SEC 20-F, one SIFY ADS equals 6 equity shares.",cover,"cover-fresh"),
   ("Each ADS represents 10 ordinary shares.",cover,"cover-WRONG"),("Each ADS represents 144869230 ordinary shares.",cover,"cover-WRONG-shares-out")]:
    print(name, "kept" if R not in g(s,src) else "REPLACED", "|", s)
print("-- split sentence")
for t in ["SIFY trades as an ADR on Nasdaq. For SIFY, one ordinary share represents 1 share.",
          "SIFY is listed as an ADS in New York. Each of them is backed by 4 Sify shares.",
          "SIFY trades as an ADR. Its revenue was 46,510 million rupees. Each carries 6 shares."]:
    print(repr(g(t,fund)))
print("bad",bad)
