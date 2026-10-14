import os, sys, tempfile
os.environ["VYSTED_DATA_DIR"] = tempfile.mkdtemp(prefix="ws-probe-")
sys.path.insert(0, os.getcwd())
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers import workspace as ws_router
app = FastAPI(); app.include_router(ws_router.router); c = TestClient(app)
body = {"name":"x","layout":{"grid":{"root":{}},"panels":{}},"enabledModules":{}}
for name in ["मेरा लेआउट", "Q3: earnings/notes (v2)!", "a"*199, "a"*230, "a"*300, "मे"*120]:
    r = c.post("/workspace", json={"name": name, "workspace": body})
    print(repr(name[:24]), len(name), "->", r.status_code, r.text[:140])
r = c.get("/workspace"); print("GET /workspace ->", r.status_code, r.text[:200])
