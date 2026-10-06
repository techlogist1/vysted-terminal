// macOS dev signing for built sidecar binaries (R8 hot patch).
//
// PyInstaller output is ad-hoc signed, so every rebuild changes the binary's
// code identity. Signing each freshly built sidecar with the same stable
// "Vysted Terminal Dev Signing" identity keeps macOS permission systems
// (firewall accept-incoming, TCC pairings, any future keychain use) keyed to
// ONE identity across rebuilds — the same fix the cargo runner applies to the
// main dev binary (see docs/redesign/KEYCHAIN_DEV_SIGNING.md).
//
// No-op everywhere it should be: non-Darwin platforms, machines without the
// identity (CI), VYSTED_SKIP_DEV_SIGN=1, or a missing file. Never throws — a
// failed dev signature must not fail a build (release signing is Tauri's job
// and untouched by this).
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";

const IDENTITY = "Vysted Terminal Dev Signing";

let identityPresent = null;

function hasIdentity() {
  if (identityPresent !== null) return identityPresent;
  try {
    const out = execSync("security find-identity -v -p codesigning", {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    identityPresent = out.includes(IDENTITY);
  } catch {
    identityPresent = false;
  }
  return identityPresent;
}

/** Sign `binPath` with the stable dev identity; logs but never throws. */
export function signDevBinary(binPath, identifier) {
  if (process.platform !== "darwin") return;
  if (process.env.VYSTED_SKIP_DEV_SIGN) return;
  if (!existsSync(binPath)) return;
  if (!hasIdentity()) return;
  try {
    execSync(`codesign --force --sign "${IDENTITY}" --identifier "${identifier}" "${binPath}"`, {
      stdio: ["ignore", "ignore", "pipe"],
    });
    console.log(`[dev-sign] signed ${binPath} as ${identifier}`);
  } catch (err) {
    console.warn(`[dev-sign] codesign failed for ${binPath} (continuing unsigned): ${err}`);
  }
}
