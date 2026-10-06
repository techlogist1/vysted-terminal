# Logging pass-through proxy: 127.0.0.1:52406 -> 127.0.0.1:11434; records the tool names sent per /api/chat request.
import http.client, json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
LOG = sys.argv[1]
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def _fwd(self, method):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        if body and self.path.startswith("/api/chat"):
            try:
                req = json.loads(body)
                names = [t.get("function", {}).get("name") for t in req.get("tools") or []]
                last_user = [m.get("content") for m in req.get("messages", []) if m.get("role") == "user"][-1:]
                with open(LOG, "a") as f:
                    f.write(json.dumps({"t": time.strftime("%H:%M:%S"), "model": req.get("model"), "user": last_user, "n_tools": len(names), "tools": names}) + "\n")
            except Exception as e:
                open(LOG, "a").write(json.dumps({"err": str(e)}) + "\n")
        c = http.client.HTTPConnection("127.0.0.1", 11434, timeout=600)
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
        c.request(method, self.path, body=body, headers=hdrs)
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        while True:
            chunk = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
            if not chunk: break
            self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk)); self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
        self.close_connection = True
    def do_POST(self): self._fwd("POST")
    def do_GET(self): self._fwd("GET")
    def do_HEAD(self): self._fwd("HEAD")
    def log_message(self, *a): pass
ThreadingHTTPServer(("127.0.0.1", 52406), H).serve_forever()
