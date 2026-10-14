#!/usr/bin/env node
// Loopback update server for the on-machine self-update proof (R16).
//   node scripts/release/serve-update.mjs --dir <dir> [--port 8787] [--rewrite]
// Serves <dir> on 127.0.0.1. With --rewrite, latest.json's platform URLs are
// pointed at this server (by file name) on the fly; signatures are untouched,
// so the app still verifies every bundle against its configured pubkey.
import { createReadStream, readFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { basename, join, resolve, sep } from "node:path";
import { parseArgs } from "node:util";

const { values } = parseArgs({
  options: {
    dir: { type: "string" },
    port: { type: "string", default: "8787" },
    rewrite: { type: "boolean", default: false },
  },
});
if (!values.dir) {
  console.error(
    "usage: serve-update.mjs --dir <dir with latest.json + bundle> [--port 8787] [--rewrite]",
  );
  process.exit(2);
}
const root = resolve(values.dir);
const port = Number(values.port);
const origin = `http://127.0.0.1:${port}`;

function latestJson() {
  const manifest = JSON.parse(readFileSync(join(root, "latest.json"), "utf8"));
  if (values.rewrite) {
    for (const platform of Object.values(manifest.platforms ?? {})) {
      const name = basename(new URL(platform.url).pathname);
      platform.url = `${origin}/${encodeURIComponent(decodeURIComponent(name))}`;
    }
  }
  return JSON.stringify(manifest, null, 2);
}

const server = createServer((req, res) => {
  let path;
  try {
    path = decodeURIComponent(new URL(req.url ?? "/", origin).pathname);
  } catch {
    res.writeHead(400).end();
    return;
  }
  const file = resolve(join(root, path));
  const log = (status) => console.log(`${status} ${req.method} ${path}`);
  if (req.method !== "GET" && req.method !== "HEAD") {
    log(405);
    res.writeHead(405).end();
    return;
  }
  if (!file.startsWith(root + sep)) {
    log(403);
    res.writeHead(403).end();
    return;
  }
  try {
    if (path === "/latest.json") {
      const body = latestJson();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(req.method === "HEAD" ? undefined : body);
    } else {
      const stat = statSync(file);
      if (!stat.isFile()) throw new Error("not a file");
      const size = stat.size;
      res.writeHead(200, {
        "Content-Type": "application/octet-stream",
        "Content-Length": size,
      });
      if (req.method === "HEAD") res.end();
      else createReadStream(file).pipe(res);
    }
    log(200);
  } catch {
    log(404);
    res.writeHead(404).end();
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(
    `Serving ${root} on ${origin}${values.rewrite ? " (latest.json URLs rewritten)" : ""}`,
  );
  console.log(`VYSTED_UPDATER_ENDPOINT=${origin}/latest.json`);
});
