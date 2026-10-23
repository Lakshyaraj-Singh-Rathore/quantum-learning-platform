/**
 * Portable browser resolution for the .mjs QA harnesses.
 *
 * Every one of these harnesses used to hardcode
 *   C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
 * and three of them also hardcoded an artifact directory under
 *   C:\Users\laksh\.gemini\antigravity-ide\brain\<session-uuid>
 * which is an ephemeral IDE session folder that no longer exists. The result
 * was that none of them could run anywhere, including on the machine the paths
 * came from, and two of them are wired into package.json so the published
 * commands crashed on launch.
 *
 * The logic here is lifted from `push-overlay-check.mts`, which was the only
 * portable browser harness in the repo. It is centralised rather than pasted
 * seven times so the resolution order has exactly one definition.
 *
 * Browser resolution order:
 *   1. $PLAYWRIGHT_CHROMIUM_PATH        explicit override
 *   2. $UITEST_DIR/bin/chromium         what tools/browser-setup.sh produces
 *   3. undefined                        let Playwright use its own download
 */
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/** Repo root, derived from this file's location rather than from cwd. */
export const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));

/**
 * Chromium to launch, or undefined to let Playwright resolve its own.
 *
 * Has a side effect by design: the Chromium that `tools/browser-setup.sh`
 * unpacks needs the Amazon Linux shared libraries shipped beside it, and they
 * are not on the system path. Setting LD_LIBRARY_PATH here keeps that coupling
 * next to the path it belongs to, exactly as push-overlay-check.mts does.
 */
export function resolveChromium() {
  const envPath = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  if (envPath) return envPath;

  const uitest = process.env.UITEST_DIR ?? "/home/user/uitest";
  const local = path.join(uitest, "bin", "chromium");
  if (existsSync(local)) {
    process.env.LD_LIBRARY_PATH = [
      path.join(uitest, "al2023", "lib"),
      process.env.LD_LIBRARY_PATH,
    ]
      .filter(Boolean)
      .join(":");
    return local;
  }

  if (process.platform === "win32") {
    const candidates = [
      "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
      "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
      "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ];
    for (const c of candidates) {
      if (existsSync(c)) return c;
    }
  }

  return undefined;
}

/**
 * Launch options for chromium.launch().
 *
 * The conditional spread matters: passing `executablePath: undefined`
 * explicitly is not the same as omitting it, and would stop Playwright falling
 * back to its own browser.
 */
export function launchOptions(extra = {}) {
  const exePath = resolveChromium();
  return {
    ...(exePath ? { executablePath: exePath } : {}),
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    ...extra,
  };
}

/**
 * Where screenshots and other artifacts go.
 *
 * $QA_ARTIFACT_DIR if set, else <repo>/artifacts/<name>, which .gitignore
 * already excludes. Created if missing so a harness never dies on ENOENT
 * half way through a run.
 */
export function artifactDir(name = "qa") {
  const base = process.env.QA_ARTIFACT_DIR ?? path.join(REPO_ROOT, "artifacts", name);
  mkdirSync(base, { recursive: true });
  return base;
}

/** Consistent message when no browser can be started. */
export function browserHelp() {
  return [
    "Could not launch Chromium.",
    "  bash tools/browser-setup.sh      # from the repo root",
    "  then re-run this script",
    "Or set PLAYWRIGHT_CHROMIUM_PATH to an existing browser.",
  ].join("\n");
}
