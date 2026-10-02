# Same BSE lane, same scrip, two direct calls: does the per-quarter split come back identical?
from services import corporate_disclosures as cd
for code in ("544023", "539963"):
    runs = []
    for i in range(2):
        p = cd._bse_shareholding(code)
        runs.append([(str(x.quarter_end), x.promoter_percent) for x in p])
    nulls = [sum(1 for _, v in r if v is None) for r in runs]
    print(code, "n=", [len(r) for r in runs], "null-promoter=", nulls, "identical=", runs[0] == runs[1], flush=True)
