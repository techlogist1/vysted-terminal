#!/usr/bin/env python3
"""Junk LLM provider stub for R15 failure-inducer (loopback only, stdlib).

Mode is chosen by the requested model id so one process serves every junk case:
  junk-html        200 text/html page (a captive portal / proxy error page)
  junk-badsse      200 text/event-stream whose data line is not JSON
  junk-truncated   200 SSE: one valid content chunk, then the socket closes (no finish, no [DONE])
  junk-emptychoices 200 SSE: chunks with choices: [] then [DONE]
  junk-429         429 JSON error with Retry-After: 1 (counts attempts)
  junk-500         500 JSON error
  junk-hang        accepts, sends headers, never sends a byte of body (for timeout behaviour)
Ollama (/api/chat) gets: junk-html -> html page; anything else -> NDJSON truncated.
Every request is logged (method, path, model, mode) to stdout for the evidence file.
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COUNTS: dict[str, int] = {}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # quiet default logger
        pass

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw or b"{}")
        except ValueError:
            return {}

    def _send(self, code, ctype, payload: bytes, extra=None, close=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def do_GET(self):
        print(json.dumps({"t": time.time(), "m": "GET", "path": self.path}), flush=True)
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, "application/json", json.dumps({"data": [{"id": "junk-html"}]}).encode())
            return
        self._send(200, "text/html", b"<html><body>Captive portal: please sign in</body></html>")

    def do_POST(self):
        body = self._body()
        model = str(body.get("model") or "")
        COUNTS[model] = COUNTS.get(model, 0) + 1
        print(json.dumps({"t": time.time(), "m": "POST", "path": self.path, "model": model,
                          "n": COUNTS[model], "stream": body.get("stream")}), flush=True)
        chunk = lambda d: ("data: " + json.dumps(d) + "\n\n").encode()
        base = {"id": "junk", "object": "chat.completion.chunk", "created": 0, "model": model}
        if self.path.startswith("/api/chat"):  # ollama
            if model == "junk-html":
                self._send(200, "text/html", b"<html><body>502 Bad Gateway</body></html>")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(json.dumps({"model": model, "message": {"role": "assistant", "content": "Partial ans"}, "done": False}).encode() + b"\n")
            self.wfile.write(b'{"model": "x", "message": {"role": "assist')
            self.wfile.flush()
            self.close_connection = True
            return
        if model == "junk-html":
            self._send(200, "text/html; charset=utf-8", b"<html><head><title>Access denied</title></head><body>Your network blocks this site.</body></html>")
        elif model == "junk-badsse":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b"data: {this is not json at all\n\n")
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            self.close_connection = True
        elif model == "junk-truncated":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            d = dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "content": "RELIANCE closed at Rs 1,4"}, "finish_reason": None}])
            self.wfile.write(chunk(d))
            self.wfile.flush()
            self.close_connection = True
        elif model == "junk-emptychoices":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(chunk(dict(base, choices=[])))
            self.wfile.write(chunk(dict(base, choices=[])))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            self.close_connection = True
        elif model == "junk-chunkdrop":
            # chunked transfer cut mid-body (what a real mid-stream socket drop looks like)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            d = chunk(dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "content": "RELIANCE closed at Rs 1,4"}, "finish_reason": None}]))
            self.wfile.write(hex(len(d))[2:].encode() + b"\r\n" + d + b"\r\n")
            self.wfile.write(b"40\r\ndata: {\"partial")
            self.wfile.flush()
            self.close_connection = True
        elif model == "junk-orerror":
            # OpenRouter-style mid-stream error: an error chunk with finish_reason "error", then [DONE]
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(chunk(dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "content": "RELIANCE closed at Rs 1,4"}, "finish_reason": None}])))
            self.wfile.write(chunk(dict(base, error={"code": 502, "message": "Provider returned error"}, choices=[{"index": 0, "delta": {"content": ""}, "finish_reason": "error"}])))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            self.close_connection = True
        elif model == "junk-429":
            self._send(429, "application/json", json.dumps({"error": {"message": "Rate limit reached for requests", "type": "requests", "code": "rate_limit_exceeded"}}).encode(), {"Retry-After": "1"})
        elif model == "junk-500":
            self._send(500, "application/json", json.dumps({"error": {"message": "internal upstream failure", "type": "server_error"}}).encode())
        elif model == "junk-hang":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.flush()
            time.sleep(600)
        else:
            self._send(404, "application/json", json.dumps({"error": {"message": f"model {model} does not exist", "code": "model_not_found"}}).encode())


if __name__ == "__main__":
    port = int(sys.argv[1])
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
