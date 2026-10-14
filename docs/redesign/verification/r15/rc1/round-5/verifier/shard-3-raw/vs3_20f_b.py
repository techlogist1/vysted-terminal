import asyncio, sys, os, re
sys.path.insert(0, os.getcwd())
from services import sec_ownership
async def main():
    for url, pat in [("https://www.sec.gov/Archives/edgar/data/1144967/000119312526322004/d88195d20f.htm", r"principal shareholders"),("https://www.sec.gov/Archives/edgar/data/1103838/000095010326010820/dp249803_20f.htm", r"MAJOR SHAREHOLDERS Shareholding")]:
        t = sec_ownership._text(await sec_ownership._fetch_text(url))
        for m in list(re.finditer(pat, t, re.I))[-2:]:
            print(url.rsplit('/',1)[1], m.start(), repr(t[m.start():m.start()+1800])); print()
asyncio.run(main())
