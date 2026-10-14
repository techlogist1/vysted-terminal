import json, urllib.request
def spec():
    n=lambda i,t:{"id":i,"type":t,"position":{"x":0,"y":0},"config":{}}
    e=lambda i,s,t,sp,tp:{"id":i,"sourceNode":s,"sourcePort":sp,"targetNode":t,"targetPort":tp}
    return {"id":"vs2-branch","name":"vs2 branch probe","nodes":[n("branch","logic.branch"),n("notify","action.notify_desktop"),n("log","action.log"),n("log2","action.log")],
            "edges":[e("e1","branch","notify","true_path","value"),e("e2","branch","log","false_path","value"),e("e3","notify","log2","message","value")]}
for v in ["false","no","0","off"," OFF ","False","","true","yes"]:
    body=json.dumps({"spec":spec(),"inputs":{"value":v}}).encode()
    req=urllib.request.Request("http://127.0.0.1:52602/workflow/run",data=body,headers={"Content-Type":"application/json"})
    raw=urllib.request.urlopen(req,timeout=60).read().decode()
    st={}
    for line in raw.splitlines():
        if line.startswith("data:"):
            try: ev=json.loads(line[5:])
            except Exception: continue
            k=ev.get("kind"); nid=ev.get("nodeId") or ev.get("node_id")
            if k in("node-start","node-skipped","node-complete","node-error") and nid: st.setdefault(nid,[]).append(k)
            if k in ("run-complete","run-end","run-done"): st["_run"]=ev.get("status")
    print(repr(v), st)
