import asyncio, sys, os
sys.path.insert(0, os.getcwd())
from services import sec_filings_provider, sec_ownership
async def main():
    for s in sys.argv[1:]:
        try:
            lst = await sec_filings_provider.list_filings(s, form_type="20-F", limit=5)
            print(s, "filings:", [(f.form_type, f.filed_date, f.accession) for f in lst.filings][:5])
            f = next((f for f in lst.filings if f.form_type=="20-F"), None)
            if f:
                idx = await sec_ownership._fetch_text(f"{f.edgar_url}{f.accession}-index.htm")
                url = sec_ownership._primary_document(idx); print(" primary:", url)
                doc = await sec_ownership._fetch_text(url)
                h, a = sec_ownership.parse_major_shareholders(doc)
                print(" parsed:", [(x.holder, x.percent) for x in h], a)
                t = sec_ownership._text(doc)
                import re
                for m in re.finditer(r"major shareholders", t, re.I):
                    print("  anchor@", m.start(), repr(t[m.start():m.start()+700]))
        except Exception as e:
            print(s, "ERR", type(e).__name__, e)
asyncio.run(main())
