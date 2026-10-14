import json, os, subprocess, time, urllib.request, sys
S=sys.argv[1]; t0=float(open(S+'/boot_t0.txt').read()); out=open(S+'/idle-sampler.jsonl','a')
def get(p):
    try:
        with urllib.request.urlopen('http://127.0.0.1:52225'+p, timeout=10) as r: return json.loads(r.read())
    except Exception as e: return {'err':str(e)[:120]}
def dirsize(d):
    tot={}
    for root,_,fs in os.walk(d):
        for f in fs:
            p=os.path.join(root,f); tot[os.path.relpath(p,d)]=os.path.getsize(p)
    return tot
while time.time()-t0 < 400:
    log=open(S+'/sidecar.log',errors='replace').read()
    ps=subprocess.run(['ps','-o','rss=,%cpu=','-p','44144'],capture_output=True,text=True).stdout.split()
    rec={'t':round(time.time()-t0,1),'rss_kb':ps[0] if ps else None,'cpu':ps[1] if len(ps)>1 else None,
         'log_lines':log.count('\n'),'log_429':log.count('429'),'log_throttl':log.lower().count('throttl'),
         'log_ratelimit':log.lower().count('rate limit')+log.lower().count('ratelimit')+log.lower().count('rate_limited'),
         'log_warn':log.count('WARNING'),'log_err':log.count('ERROR'),
         'provider_health':get('/system/provider-health'),'files':dirsize(S+'/data')}
    out.write(json.dumps(rec)+'\n'); out.flush(); time.sleep(30)
