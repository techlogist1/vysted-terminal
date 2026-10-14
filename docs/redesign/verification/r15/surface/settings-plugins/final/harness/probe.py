import json, sys, time, urllib.request, urllib.error, urllib.parse
BASE = "http://127.0.0.1:52845"
OUT = sys.argv[1]
def req(tag, method, path, body=None, headers=None, redact=()):
    h = {"Content-Type": "application/json", "Origin": "http://localhost:5173"}
    h.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    t = time.time()
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            st, txt, hdr = resp.status, resp.read().decode(errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        st, txt, hdr = e.code, e.read().decode(errors="replace"), dict(e.headers)
    except Exception as e:
        st, txt, hdr = "EXC", repr(e), {}
    b = dict(body) if isinstance(body, dict) else body
    if isinstance(b, dict) and "api_key" in b: b["api_key"] = "<canary redacted>"
    hh = {k: ("<canary redacted>" if k.lower().startswith("x-vysted") else v) for k, v in (headers or {}).items()}
    rec = {"tag": tag, "m": method, "path": path, "req": b, "req_headers": hh, "status": st, "ms": int((time.time()-t)*1000),
           "x_news_sources": hdr.get("X-News-Sources") or hdr.get("x-news-sources"), "body": txt[:1500]}
    with open(OUT, "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(tag, st, rec["ms"], txt[:220].replace("\n", " "))
    return st, txt
C = "R15CANARYfinal"
which = sys.argv[2]
if which == "A":
    for p in ["/health", "/llm/providers", "/custom-agents", "/agents", "/workspace", "/system/hardware", "/plugins", "/system/provider-health"]:
        req("A " + p, "GET", p)
    for prov in ["openai","anthropic","gemini","groq","deepseek","xai","openrouter","ollama"]:
        st, txt = req("A models " + prov, "GET", "/llm/models?provider=" + prov)
if which == "S":
    req("A searxng", "GET", "/search/searxng/status")
if which == "B":
    fake = {"openai":"sk-"+C+"0123456789abcdef", "anthropic":"sk-ant-"+C+"0123456789", "gemini":"AIza"+C+"0123456789abcdef",
            "groq":"gsk_"+C+"0123456789", "deepseek":"sk-"+C+"ds0123456789", "xai":"xai-"+C+"0123456789", "openrouter":"sk-or-v1-"+C+"0123456789abcdef"}
    for prov, k in fake.items():
        req("B fake " + prov, "POST", "/llm/keys/validate", {"provider": prov, "api_key": k})
    req("B openai trailing-space", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": fake["openai"] + " "})
    req("B anthropic trailing-newline", "POST", "/llm/keys/validate", {"provider": "anthropic", "api_key": fake["anthropic"] + "\n"})
    req("B openrouter whitespace-padded", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": "  " + fake["openrouter"] + "\t"})
    req("B openai dead base_url", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": fake["openai"], "base_url": "http://127.0.0.1:9/v1"})
    req("B gemini dead base_url", "POST", "/llm/keys/validate", {"provider": "gemini", "api_key": fake["gemini"], "base_url": "http://127.0.0.1:9"})
    req("B openai empty key", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": ""})
    req("B openai whitespace-only key", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": "   "})
    req("B ollama no key llama3.1:8b", "POST", "/llm/keys/validate", {"provider": "ollama", "model": "llama3.1:8b"})
    req("B ollama missing model", "POST", "/llm/keys/validate", {"provider": "ollama", "model": "nonexistent-model:1b"})
    req("B unknown provider", "POST", "/llm/keys/validate", {"provider": "nope", "api_key": "x"})
    req("B extra field", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": "x", "evil": 1})
if which == "C":
    req("C provider-health GET", "GET", "/system/provider-health")
    req("C trip (ungated build expects 404)", "POST", "/system/provider-health/trip", {"weight": 3})
    req("C reset (expects 404)", "POST", "/system/provider-health/reset", {})
    req("C diagnostics", "GET", "/system/diagnostics")
if which == "D":
    req("D plugins baseline", "GET", "/plugins")
    req("D example config", "GET", "/plugins/vysted-example/config")
    st, txt = req("D disable example", "POST", "/plugins/vysted-example/config", {"enabled": False})
    req("D plugins after disable", "GET", "/plugins")
    req("D enable example", "POST", "/plugins/vysted-example/config", {"enabled": True})
    req("D plugins after enable", "GET", "/plugins")
    req("D unknown plugin config", "GET", "/plugins/does-not-exist/config")
    req("D malformed config body", "POST", "/plugins/vysted-example/config", {"enabled": "maybe"})
if which == "E":
    req("E news status nokey", "GET", "/news/sources/status")
    req("E news status fakekey", "GET", "/news/sources/status", headers={"X-Vysted-Newsapi-Key": "0123456789abcdef" + C})
    req("E news status whitespace key", "GET", "/news/sources/status", headers={"X-Vysted-Newsapi-Key": "   "})
    req("E news with fakekey", "GET", "/news?limit=5", headers={"X-Vysted-Newsapi-Key": "0123456789abcdef" + C})
if which == "F":
    q = urllib.parse.quote
    layout = {"version": 2, "layout": {"grid": {}, "panels": {}}}
    names = ["R15 Final Swing", "मेरा लेआउट", "../evil", "a/b", "   ", "x"*199, "x"*200, "x"*201, "x"*240, "म"*67, "म"*68, "म"*200, "__mine"]
    for n in names:
        req(f"F save len={len(n)} bytes={len(n.encode())}", "POST", "/workspace", {"name": n, "workspace": layout})
    req("F list", "GET", "/workspace")
    req("F get R15 Final Swing", "GET", "/workspace/" + q("R15 Final Swing"))
    for n in names:
        req(f"F delete len={len(n)}", "DELETE", "/workspace/" + q(n, safe=""))
    req("F delete missing", "DELETE", "/workspace/" + q("never-saved-r15", safe=""))
    req("F list after cleanup", "GET", "/workspace")
