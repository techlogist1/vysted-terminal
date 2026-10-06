// scripts/build-python.mjs
//
// The one place the sidecar build venvs get their interpreter. The stack
// declares Python 3.13; a bare `python3` follows whatever the OS package
// manager last installed (Homebrew moved it to 3.14 mid-release), so every
// ensure script resolves and verifies 3.13 here instead (R15-LEAD-012).

import { execSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { platform } from "node:os";

const WANT = "3.13";

/** "3.13" for an interpreter command, or null when it cannot be run. */
function versionOf(cmd) {
  try {
    return execSync(`${cmd} -c "import sys; print('%d.%d' % sys.version_info[:2])"`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return null;
  }
}

/**
 * The command for a Python 3.13 interpreter: `VYSTED_PYTHON` when set, else the
 * first of `python3.13`, `py -3.13` (Windows) or a plain `python3`/`python`
 * that reports 3.13. Throws a message naming the fix when none does.
 */
export function resolveBuildPython() {
  const override = process.env.VYSTED_PYTHON;
  if (override) {
    const cmd = `"${override}"`;
    const got = versionOf(cmd);
    if (got !== WANT) {
      throw new Error(
        `VYSTED_PYTHON=${override} is Python ${got ?? "(not runnable)"}, need ${WANT}.`,
      );
    }
    return cmd;
  }
  const candidates =
    platform() === "win32" ? ["py -3.13", "python3.13", "python"] : ["python3.13", "python3"];
  for (const cmd of candidates) {
    if (versionOf(cmd) === WANT) return cmd;
  }
  throw new Error(
    `No Python ${WANT} found (tried ${candidates.join(", ")}). Install Python ${WANT} ` +
      `(e.g. \`brew install python@3.13\`) or set VYSTED_PYTHON to its path.`,
  );
}

/**
 * Make `venvDir` a Python 3.13 venv: create it when missing and recreate it
 * when its interpreter is any other version.
 */
export function ensureBuildVenv(venvDir, venvPython, run) {
  if (existsSync(venvPython)) {
    const got = versionOf(`"${venvPython}"`);
    if (got === WANT) return;
    console.log(`[build-python] ${venvDir} is Python ${got ?? "(broken)"}, recreating on ${WANT}.`);
    rmSync(venvDir, { recursive: true, force: true });
  }
  run(`${resolveBuildPython()} -m venv "${venvDir}"`);
}
