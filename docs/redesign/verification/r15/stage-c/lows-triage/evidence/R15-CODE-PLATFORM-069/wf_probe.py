import os, sys, time, json, asyncio
os.environ.setdefault("VYSTED_DATA_DIR", "/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/probes/data")
sys.path.insert(0, os.getcwd())
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import workflow as wf_router
from services import workflow_engine, workflow_nodes
from services.workflow_nodes import code_node

app = FastAPI(); app.include_router(wf_router.router)
c = TestClient(app)
def frames(resp):
    return [json.loads(l[6:]) for l in resp.text.splitlines() if l.startswith("data: ")]

# --- 065: dangling edge -> how many frames?
spec = {"id":"w1","name":"w","nodes":[{"id":"a","type":"transform.code","position":{"x":0,"y":0},"config":{"expression":"1+1"}}],
        "edges":[{"id":"e1","sourceNode":"a","sourcePort":"value","targetNode":"ghost","targetPort":"in"}]}
r = c.post("/workflow/run", json={"spec":spec})
print("065 dangling-edge status", r.status_code, "frames", frames(r))
# unregistered type
spec2 = {"id":"w2","name":"w","nodes":[{"id":"a","type":"plugin.unknown","position":{"x":0,"y":0}}],"edges":[]}
r = c.post("/workflow/run", json={"spec":spec2})
print("065 unregistered-type status", r.status_code, "frames", frames(r))

# --- 075: resume-from -> full run?
code_node.register()
spec3 = {"id":"w3","name":"w","nodes":[
    {"id":"a","type":"transform.code","position":{"x":0,"y":0},"config":{"expression":"1+1"}},
    {"id":"b","type":"transform.code","position":{"x":0,"y":0},"config":{"expression":"2+2"}}],"edges":[]}
r = c.post("/workflow/run", json={"spec":spec3,"mode":"resume-from","resumeFrom":"b"})
kinds = [(f["kind"], f.get("nodeId")) for f in frames(r)]
print("075 resume-from status", r.status_code, "kinds", kinds)
r = c.post("/workflow/run", json={"spec":spec3,"mode":"resume-from","resumeFrom":"nonexistent"})
print("075 resume-from bogus node status", r.status_code, "kinds", [(f["kind"], f.get("nodeId")) for f in frames(r)])

# --- 066: unbounded pow / list mult, sync on loop
async def t(expr):
    t0 = time.perf_counter()
    try:
        out = await code_node.evaluate_code({}, {"expression": expr}); ok = type(out["value"]).__name__ + (" len=%d" % len(out["value"]) if isinstance(out["value"], list) else "")
    except Exception as e: ok = "ERR " + repr(e)[:80]
    return expr, round(time.perf_counter() - t0, 3), ok
async def main():
    for e in ["7**(10**6)", "[0]*10**7"]:
        print("066", await t(e))
asyncio.run(main())
