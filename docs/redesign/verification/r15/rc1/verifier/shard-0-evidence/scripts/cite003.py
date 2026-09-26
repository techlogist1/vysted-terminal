import sys
sys.path.insert(0,'.')
from services.research.deep import _Findings
from services.research.models import ResearchSource
from services.research import iter as it
import inspect
print(inspect.signature(ResearchSource))
def src(u,t): 
    try: return ResearchSource(title=t,url=u,excerpt='e')
    except TypeError: return ResearchSource(t,u)
f=_Findings()
# round 1: general blog + structured price/fundamentals
f.web_sources.append(src('https://someblog.example.com/bluestar','blog'))
f.structured_sources += [src('vysted://price/BLUESTARCO','price'), src('vysted://fundamentals/BLUESTARCO','fundamentals')]
r1=[s.url for s in f.all_sources()]
report_r1 = "Closing Price Rs 1,525.0 [%d]; P/E 61.67 [%d]" % (r1.index('vysted://price/BLUESTARCO')+1, r1.index('vysted://fundamentals/BLUESTARCO')+1)
# round 2: higher-tier exchange + regulator + Tier-1 press arrive (rank ahead of round-1 web)
f.web_sources += [src('https://nsearchives.nseindia.com/corporate/BLUESTARCO_directors.pdf','Change in Directorate'), src('https://www.sebi.gov.in/x','sebi'), src('https://www.reuters.com/y','reuters')]
r2=[s.url for s in f.all_sources()]
import re
for n in map(int, re.findall(r"\[(\d+)\]", report_r1)): print('marker',n,'->',r2[n-1])
print('r1',r1); print('r2',r2)
# heavy path fresh: two angles with local numbering, one cites a structured source that ranks last in merge
from services.research.models import ResearchBrief
a=ResearchBrief(query='q',symbol='BLUESTARCO',mode='deep',markdown='P/E 61.67 [2]. Board change [1].', sources=[src('https://nsearchives.nseindia.com/d.pdf','dir'), src('vysted://fundamentals/BLUESTARCO','fund')])
b=ResearchBrief(query='q',symbol='BLUESTARCO',mode='deep',markdown='Price 1525 [1], per Reuters [2].', sources=[src('vysted://price/BLUESTARCO','price'), src('https://www.reuters.com/y','reuters')])
merged=it._merge_sources([a,b])
for br in (a,b):
    out=it._remap_markers(br.markdown, br.sources, merged)
    print(out, '->', [merged[int(n)-1].url for n in re.findall(r"\[(\d+)\]", out)])
