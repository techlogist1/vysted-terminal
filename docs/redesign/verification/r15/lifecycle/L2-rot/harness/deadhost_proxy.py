#!/usr/bin/env python3
"""Loopback HTTPS CONNECT proxy for ONE sidecar process (L2-rot).
Tunnels every host EXCEPT the ones in the blocklist, which get a 502 to CONNECT --
what a client sees when an upstream host no longer resolves / is gone.
usage: deadhost_proxy.py <port> <logfile> host1,host2,...   (suffix match)"""
import asyncio, json, sys, time
PORT, LOG, BLOCK = int(sys.argv[1]), sys.argv[2], [h for h in sys.argv[3].split(",") if h]

def log(rec):
    rec["t"] = time.strftime("%H:%M:%S")
    with open(LOG, "a") as fh:
        fh.write(json.dumps(rec) + "\n")

async def pipe(r, w):
    try:
        while True:
            b = await r.read(65536)
            if not b:
                break
            w.write(b)
            await w.drain()
    except Exception:
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass

async def handle(cr, cw):
    try:
        line = await cr.readline()
        while (h := await cr.readline()) not in (b"\r\n", b"\n", b""):
            pass
        parts = line.decode("latin-1").split()
        if len(parts) < 2 or parts[0] != "CONNECT":
            cw.write(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"); await cw.drain(); cw.close(); return
        host, _, port = parts[1].rpartition(":")
        if any(host == b or host.endswith("." + b) for b in BLOCK):
            log({"host": host, "action": "blocked"})
            cw.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"); await cw.drain(); cw.close(); return
        log({"host": host, "action": "tunnel"})
        ur, uw = await asyncio.wait_for(asyncio.open_connection(host, int(port)), 20)
        cw.write(b"HTTP/1.1 200 Connection established\r\n\r\n"); await cw.drain()
        await asyncio.gather(pipe(cr, uw), pipe(ur, cw))
    except Exception as exc:
        log({"err": repr(exc)[:200]})
        try:
            cw.close()
        except Exception:
            pass

async def main():
    srv = await asyncio.start_server(handle, "127.0.0.1", PORT)
    async with srv:
        await srv.serve_forever()

asyncio.run(main())
