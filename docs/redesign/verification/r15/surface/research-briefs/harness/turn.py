#!/usr/bin/env python3
"""One chat turn through vy.py, playing the frontend: acks host actions, threads history."""
import argparse, json, subprocess, sys, time, urllib.request, re, os
REPO="/Users/lokavyasingh/Documents/dev/vysted-terminal"
HOST={'add_to_watchlist','arrange_layout','close_panel','focus_panel','open_company_overview','open_panel','portfolio_add_position','portfolio_delete_position','portfolio_update_position','propose_order','publish_brief','remove_from_watchlist','save_layout','save_screen','set_chart_indicators','set_chart_symbol','set_region','write_note','write_screener_filters'}
ap=argparse.ArgumentParser()
ap.add_argument('--port',type=int,required=True); ap.add_argument('--tag',required=True)
ap.add_argument('--prompt',required=True); ap.add_argument('--provider',default='ollama'); ap.add_argument('--model',default='llama3.1:8b')
ap.add_argument('--agent',default='copilot'); ap.add_argument('--autonomy',default='ask'); ap.add_argument('--mode',default='agent')
ap.add_argument('--depth'); ap.add_argument('--history'); ap.add_argument('--context'); ap.add_argument('--out',required=True)
ap.add_argument('--ack',default='applied'); ap.add_argument('--no-ack',action='store_true'); ap.add_argument('--extra-opts',default='{}')
ap.add_argument('--timeout',default='900'); ap.add_argument('--tier',default='tier_a')
a=ap.parse_args()
hist=json.load(open(a.history)) if a.history and os.path.exists(a.history) else []
opts={"history":hist, **json.loads(a.extra_opts)}
if a.depth: opts["research_depth"]=a.depth
cmd=[sys.executable,'-u',f'{REPO}/scripts/r15/vy.py','invoke',a.agent,a.prompt,'--provider',a.provider,'--model',a.model,'--mode',a.mode,'--autonomy',a.autonomy,'--port',str(a.port),'--tag',a.tag,'--out',a.out+'.jsonl','--max-event','50000000','--options',json.dumps(opts),'--timeout',a.timeout,'--tier',a.tier]
if a.context: cmd+=['--context',a.context]
log=open(a.out+'.stdout.txt','w'); acks=[]
t0=time.time()
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,text=True,bufsize=1)
for line in p.stdout:
    log.write(line); log.flush()
    m=re.match(r'\[\s*([\d.]+)s\] tool_use: (.*)$',line.strip())
    if m and not a.no_ack:
        try: ev=json.loads(m.group(2))
        except Exception: continue
        if ev.get('name') in HOST:
            body={"tool_call_id":ev.get('tool_call_id',''),"status":a.ack,"detail":{"action":ev['name'],**({k:v for k,v in (ev.get('input') or {}).items() if k in('symbol','panel') and isinstance(v,str)})}}
            try:
                r=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{a.port}/agents/actions/ack',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST'),timeout=5)
                res=f"{r.status} {r.read().decode()[:200]}"
            except urllib.error.HTTPError as e: res=f"{e.code} {e.read().decode()[:300]}"
            except Exception as e: res=f"ERR {e}"
            acks.append({"t":round(time.time()-t0,1),"tool":ev['name'],"tool_call_id":ev.get('tool_call_id'),"ack_http":res})
            log.write(f"[ACK] {ev['name']} id={ev.get('tool_call_id')!r} -> {res}\n"); log.flush()
p.wait()
log.close()
out=open(a.out+'.stdout.txt').read()
txt=out.split('=== ASSISTANT TEXT ===',1)[1].rsplit('\n=== ',1)[0].strip() if '=== ASSISTANT TEXT ===' in out else ''
if a.history:
    json.dump(hist+[{"role":"user","content":a.prompt},{"role":"assistant","content":txt}],open(a.history,'w'),indent=1)
if acks: json.dump(acks,open(a.out+'.acks.json','w'),indent=1)
print(out[-3500:])
