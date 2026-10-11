/* Guards the sidebar's push/overlay contract — in a real browser.
 *
 *   npx tsx scripts/push-overlay-check.mts
 *   npm run push:overlay
 *
 * Why this exists when five other render harnesses already run: those render
 * React to a string in Node, where there is no layout, no CSS cascade and no
 * hover. The behaviour being checked here is *computed padding driven by a
 * sibling selector*, which does not exist until a browser resolves it. And it
 * degrades silently: delete the `peer` class from Sidebar.tsx and the rail
 * stops pushing content on /learn with no error, no failing test — it just
 * quietly covers the text instead. This is the only check that notices.
 *
 * It is self-booting (build -> ephemeral port -> run -> teardown) so it is a
 * real CI harness rather than something that only works in one sandbox.
 *
 * Browser resolution, in order:
 *   1. $PLAYWRIGHT_CHROMIUM_PATH
 *   2. $UITEST_DIR/bin/chromium   (what tools/browser-setup.sh produces)
 *   3. Playwright's own download  (normal CI, where the CDNs are reachable)
 *
 * If no browser can be started it SKIPS with a clear message and exits 0, so a
 * machine without Chromium is not a red build. Set PUSH_OVERLAY_REQUIRED=1 to
 * make an unavailable browser a failure instead.
 */
import { existsSync } from "node:fs";
import path from "node:path";

const BASE_DIR = path.resolve(new URL("..", import.meta.url).pathname);

let failures = 0;
function check(name: string, ok: boolean, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures += 1;
}

function skip(why: string) {
  console.log(`SKIP  ${why}`);
  console.log();
  console.log("The push/overlay contract was NOT checked. To run it:");
  console.log("  bash tools/browser-setup.sh      # from the repo root");
  console.log("  npm run push:overlay");
  if (process.env.PUSH_OVERLAY_REQUIRED === "1") {
    console.error("\nPUSH_OVERLAY_REQUIRED=1, so a missing browser is a failure.");
    process.exit(1);
  }
  process.exit(0);
}

/** Chromium to launch: explicit override, the setup script's build, or Playwright's. */
function resolveChromium(): string | undefined {
  const envPath = process.env.PLAYWRIGHT_CHROMIUM_PATH;
  if (envPath) return envPath;

  const uitest = process.env.UITEST_DIR ?? "/home/user/uitest";
  const local = path.join(uitest, "bin", "chromium");
  if (existsSync(local)) {
    // tools/browser-setup.sh unpacks a Chromium that needs the Amazon Linux
    // libs shipped alongside it; they are not on the system path.
    process.env.LD_LIBRARY_PATH = [
      path.join(uitest, "al2023", "lib"),
      process.env.LD_LIBRARY_PATH,
    ]
      .filter(Boolean)
      .join(":");
    return local;
  }

  return undefined; // let Playwright resolve its own
}

const exePath = resolveChromium();

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  skip("playwright is not installed (npm install in frontend/web)");
}

const { build, preview } = await import("vite");

console.log("Building the app…");
await build({ logLevel: "error", root: BASE_DIR });

const server = await preview({ root: BASE_DIR, preview: { port: 0 }, logLevel: "error" });
// resolvedUrls carries a trailing slash; concatenating "/learn" onto it yields
// "//learn", whose pathname matches no route, so every push check would read
// the overlay branch and quietly pass for the wrong reason.
const url = (server.resolvedUrls?.local?.[0] ?? "http://localhost:4173").replace(/\/+$/, "");
console.log(`Serving ${url}\n`);

let browser;
try {
  browser = await chromium.launch({
    ...(exePath ? { executablePath: exePath } : {}),
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  });
} catch (err) {
  await server.close();
  skip(`could not launch Chromium — ${String(err).split("\n")[0].slice(0, 120)}`);
}

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // The app redirects unauthenticated visitors to /login and the shell only
  // renders behind auth, so seed the same session shape the other harnesses use.
  await page.addInitScript(() => {
    localStorage.setItem(
      "ql-session",
      JSON.stringify({
        state: {
          token: "push-overlay-token",
          user: {
            id: 1,
            email: "a@b.dev",
            role: "admin",
            display_name: "Push Overlay Check",
            is_active: true,
          },
        },
        version: 0,
      }),
    );
  });

  /** Rail width and the padding of the region beside it. */
  const metrics = () =>
    page.evaluate(() => {
      const aside = document.querySelector("aside");
      if (!aside) return { rail: null, pad: null };
      const sib = aside.nextElementSibling;
      return {
        rail: getComputedStyle(aside).width,
        pad: sib ? getComputedStyle(sib).paddingLeft : null,
      };
    });

  async function measure(route: string) {
    await page.goto(`${url}${route}`, { waitUntil: "networkidle" });
    await page.waitForSelector("aside", { timeout: 15_000 });
    // Playwright's pointer starts at (0,0), which is inside the rail — park it
    // away before reading "rest", or the rail counts as already hovered.
    await page.mouse.move(1200, 500);
    await page.waitForTimeout(400);
    const rest = await metrics();
    await page.hover("aside");
    await page.waitForTimeout(400);
    const hovered = await metrics();
    return { rest, hovered };
  }

  const learn = await measure("/learn");
  console.log(`  /learn     rest rail=${learn.rest.rail} pad=${learn.rest.pad} | hovered rail=${learn.hovered.rail} pad=${learn.hovered.pad}`);
  check("learn: at rest the content reserves only the collapsed rail", learn.rest.pad === "60px", String(learn.rest.pad));
  check("learn: hovering expands the rail to 240px", learn.hovered.rail === "240px", String(learn.hovered.rail));
  check("learn: hovering PUSHES the content to 240px", learn.hovered.pad === "240px", String(learn.hovered.pad));

  const composer = await measure("/composer");
  console.log(`  /composer  rest rail=${composer.rest.rail} pad=${composer.rest.pad} | hovered rail=${composer.hovered.rail} pad=${composer.hovered.pad}`);
  check("composer: at rest the content reserves only the collapsed rail", composer.rest.pad === "60px", String(composer.rest.pad));
  check("composer: hovering expands the rail to 240px", composer.hovered.rail === "240px", String(composer.hovered.rail));
  check(
    "composer: hovering does NOT push the canvas (overlay preserved)",
    composer.hovered.pad === "60px",
    String(composer.hovered.pad),
  );
} finally {
  await browser.close();
  await server.close();
}

console.log();
if (failures === 0) {
  console.log("Push/overlay contract holds.");
} else {
  console.log(`${failures} push/overlay check(s) FAILED.`);
}
process.exit(failures === 0 ? 0 : 1);
