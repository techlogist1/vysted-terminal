// Shared scratch mocks for the S2C harness: a Tauri `invoke` shim that answers
// get_sidecar_port with :52222 and keeps an IN-MEMORY keychain (never the OS one).
export const KEYCHAIN = new Map<string, string>();
export const INVOKES: { cmd: string; args: unknown; ok: boolean }[] = [];
export async function invokeShim(cmd: string, args?: Record<string, unknown>): Promise<unknown> {
  const log = (ok: boolean) => INVOKES.push({ cmd, args: cmd.startsWith("keychain") ? { account: args?.account } : args, ok });
  switch (cmd) {
    case "get_sidecar_port": log(true); return 52222;
    case "keychain_set": log(true); KEYCHAIN.set(String(args?.account), String(args?.secret)); return;
    case "keychain_get": log(true); return KEYCHAIN.get(String(args?.account)) ?? null;
    case "keychain_delete": log(true); KEYCHAIN.delete(String(args?.account)); return;
    default: log(false); throw new Error(`shim: no Tauri command ${cmd}`);
  }
}
export const FETCHES: { m: string; url: string; status: number | string; body?: unknown }[] = [];
const realFetch = globalThis.fetch;
globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = String(input);
  let body: unknown;
  if (init?.body && typeof init.body === "string") {
    try { body = JSON.parse(init.body); } catch { body = init.body.slice(0, 200); }
    if (body && typeof body === "object" && "api_key" in (body as Record<string, unknown>)) body = { ...(body as object), api_key: "<redacted>" };
  }
  try {
    const r = await realFetch(input as RequestInfo, init);
    FETCHES.push({ m: init?.method ?? "GET", url: url.replace("http://127.0.0.1:52222", ""), status: r.status, body });
    return r;
  } catch (e) {
    FETCHES.push({ m: init?.method ?? "GET", url, status: `THROW ${(e as Error).message}`, body });
    throw e;
  }
}) as typeof fetch;
export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
export const text = (el: Element | null | undefined) => (el?.textContent ?? "").replace(/\s+/g, " ").trim();
