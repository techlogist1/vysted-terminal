import os, re, subprocess, sys, time, urllib.request
pidfile, out, dur = sys.argv[1], sys.argv[2], float(sys.argv[3])
f = open(out, "a", buffering=1)
t0 = time.monotonic()
f.write(f"# poller start mono={t0:.3f} wall={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} pidfile={pidfile}\n")
def sh(*a):
    try: return subprocess.run(a, capture_output=True, text=True, timeout=3).stdout
    except Exception as e: return ""
def get(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=0.4) as r:
            return f"{r.status}:{r.read(160).decode('utf-8','replace').replace(chr(10),' ')}"
    except urllib.error.HTTPError as e: return f"HTTP{e.code}"
    except Exception as e: return f"ERR:{type(e).__name__}"
while time.monotonic() - t0 < dur:
    t = time.monotonic()
    pid = open(pidfile).read().strip() if os.path.exists(pidfile) else ""
    line = f"t={t-t0:7.2f} wall={time.strftime('%H:%M:%S', time.gmtime())}"
    if pid:
        alive = sh("ps", "-o", "pid=", "-p", pid).strip()
        kids = sh("pgrep", "-P", pid).split()
        main = None; parts = []
        for k in kids:
            args = sh("ps", "-o", "args=", "-p", k).strip()
            name = os.path.basename(args.split(" --")[0]) if args else "?"
            gk = ",".join([k] + sh("pgrep", "-P", k).split())
            ports = re.findall(r":(\d+) \(LISTEN\)", sh("lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-p", gk))
            m = re.search(r"--port (\d+)", args)
            if name.endswith("vysted-sidecar") and m: main = m.group(1)
            parts.append(f"{k}:{name}:listen={','.join(sorted(set(ports))) or '-'}")
        line += f" app={pid}{'' if alive else '(dead)'} kids=[{' '.join(parts)}]"
        if main:
            line += f" main={main} health={get(main,'/health')} openbb={get(main,'/openbb-mcp/status')} sec={get(main,'/sec/status')}"
    f.write(line + "\n")
    time.sleep(max(0, 0.5 - (time.monotonic() - t)))
