/**
 * The QML Lab, in a real browser.
 *
 * Every frontend claim in Phases 3, 5c, 6 and 7 came from server-side
 * rendering a component tree and asserting on the HTML string. That cannot see
 * layout, cannot apply a cascade, and -- most importantly -- cannot render a
 * Radix portal, because portalled content is not in the SSR output at all. It
 * also cannot observe a request that does *not* happen, which is the only way
 * to prove polling stops.
 *
 * This harness checks the things SSR is structurally blind to. It is not a
 * replacement for the SSR harnesses: those are faster and assert far more.
 *
 * Requires a running app and API:
 *   backend:  QML_ENABLED=true uvicorn app.main:app --port 8000
 *   frontend: npm run build && vite preview --port 3001
 *   browser:  bash tools/browser-setup.sh
 *
 * Skips (exit 0) when no browser is available, like push-overlay-check.mts.
 * Set QML_BROWSER_REQUIRED=1 to make that a failure instead.
 */
import { chromium } from "playwright";
import { launchOptions, artifactDir } from "./browser-env.mjs";

const APP = process.env.QML_APP_URL ?? "http://localhost:3001";
const EMAIL = process.env.QML_USER ?? "student@quantum.local";
const PASSWORD = process.env.QML_PASS ?? "password123";
const DIR = artifactDir("qml-lab");

let failures = 0;
let checks = 0;
function check(ok: boolean, name: string, detail = "") {
  checks += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures += 1;
}

let browser;
try {
  browser = await chromium.launch(launchOptions());
} catch (err) {
  console.log(`SKIP  could not launch Chromium — ${String(err).split("\n")[0].slice(0, 110)}`);
  console.log("  bash tools/browser-setup.sh      # from the repo root");
  process.exit(process.env.QML_BROWSER_REQUIRED === "1" ? 1 : 0);
}

const page = await browser.newPage({ viewport: { width: 1480, height: 1000 } });

/** Every request the page makes, so polling can be observed rather than inferred. */
const requests: { url: string; at: number }[] = [];
page.on("request", (r) => requests.push({ url: r.url(), at: Date.now() }));

try {
  // ---- auth -------------------------------------------------------------
  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL("**/learn", { timeout: 20000 });

  // ---- the lab loads ----------------------------------------------------
  await page.goto(`${APP}/qml-lab`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  const heading = (await page.textContent("h1")) ?? "";
  check(heading.includes("Quantum ML Lab"), "the lab renders with the flag on", heading.trim());

  const tabs = await page.$$eval('button, [role="tab"]', (els) =>
    els.map((e) => e.textContent?.trim() ?? "").filter((t) => /^(Configuration|Circuit|Training|Results)$/.test(t)),
  );
  check(tabs.length === 4, "all four views are present", tabs.join(" · "));

  // ---- the Radix portal: never rendered before --------------------------
  // Portalled content is absent from SSR entirely, so no previous harness
  // could see whether a Select actually opens or what it contains.
  const triggers = await page.$$('[role="combobox"]');
  check(triggers.length >= 4, "Radix Select triggers are present", `${triggers.length} found`);

  const beforeOpen = await page.$$eval('[role="option"]', (o) => o.length);
  await triggers[0].click();
  await page.waitForTimeout(600);
  const options = await page.$$eval('[role="option"]', (o) =>
    o.map((x) => x.textContent?.trim() ?? ""),
  );
  check(
    beforeOpen === 0 && options.length > 0,
    "a Radix Select actually OPENS and portals its options",
    `${beforeOpen} before → ${options.length} after: ${options.slice(0, 4).join(", ")}`,
  );

  const inBody = await page.$$eval('[role="option"]', (o) =>
    o.length === 0 ? false : o[0].closest("[data-radix-popper-content-wrapper]") !== null,
  );
  check(inBody, "options are portalled outside the form subtree", "confirms SSR could never see them");

  await page.screenshot({ path: `${DIR}/02_select_open.png` });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);

  const afterEsc = await page.$$eval('[role="option"]', (o) => o.length);
  check(afterEsc === 0, "Escape closes the portalled listbox", `${afterEsc} options remain`);

  // ---- the form's own defaults must be submittable ---------------------
  // Found in Phase 8: Samples had min=20 step=50, so HTML constraint
  // validation rejected the server's own default of 200 (nearest valid: 170,
  // 220) and the browser refused to submit. The whole feature was unusable and
  // nothing caught it, because `step` is a validity constraint that only a
  // real browser evaluates -- SSR renders the attribute and never checks it.
  // Asserted over every numeric field, not just the one that broke.
  const invalid = await page.$$eval('input[type="number"]', (els) =>
    els
      .filter((e) => !(e as HTMLInputElement).checkValidity())
      .map((e) => {
        const i = e as HTMLInputElement;
        return `${i.id || i.name || "?"}=${i.value} (min=${i.min} max=${i.max} step=${i.step}): ${i.validationMessage}`;
      }),
  );
  check(
    invalid.length === 0,
    "every numeric field's DEFAULT value passes browser constraint validation",
    invalid.join(" | ") || "all valid",
  );

  // ---- run a real experiment -------------------------------------------
  const runBtn = await page.$('button:has-text("Train model")');
  check(runBtn !== null, "the train control is offered");

  if (runBtn) {
    requests.length = 0;
    // Capture the id the server assigns, so the terminal assertion is scoped
    // to THIS run. Scanning the whole body for /completed|failed/ is unsound:
    // the Recent rail renders the status of EVERY past experiment, so a stale
    // "failed" badge satisfies it. That defect let this check pass during a
    // run in which the form never submitted and no experiment was created.
    let createdId: number | null = null;
    page.on("response", async (r) => {
      if (r.request().method() === "POST" && /\/qml\/experiments$/.test(r.url())) {
        try {
          const j = (await r.json()) as { id?: number };
          if (j && typeof j === "object" && "id" in j) createdId = Number(j.id);
        } catch {
          /* non-JSON error body */
        }
      }
    });

    await runBtn.click();
    await page.waitForTimeout(2500);

    check(createdId !== null, "the form SUBMITS and the server creates an experiment", `id=${createdId}`);

    // Wait for THIS experiment's row to reach a terminal status.
    let terminal = "";
    for (let i = 0; i < 60 && createdId !== null; i += 1) {
      const row = await page
        .locator(`text=/#${createdId}\\b/`)
        .first()
        .locator("xpath=ancestor-or-self::*[self::button or self::li or self::div][1]")
        .textContent()
        .catch(() => null);
      if (row && /completed|succeeded|failed|cancelled/i.test(row)) {
        terminal = (row.match(/completed|succeeded|failed|cancelled/i) ?? [""])[0];
        break;
      }
      await page.waitForTimeout(1000);
    }
    check(
      /completed|succeeded/i.test(terminal),
      "THIS experiment reaches a successful terminal status in the browser",
      `#${createdId} -> ${terminal || "never terminal"}`,
    );

    await page.screenshot({ path: `${DIR}/03_after_run.png`, fullPage: true });

    // ---- polling stops: observed, not inferred ---------------------------
    // Phases 3-7 asserted refetchInterval by reading the source. This counts
    // real requests, in two halves: "0 requests after terminal" is also what a
    // run that never started looks like, so polling must be shown to have
    // HAPPENED before its absence means anything.
    const detail = new RegExp(`/qml/experiments/${createdId}($|\\?|/)`);
    check(
      requests.filter((r) => detail.test(r.url)).length >= 1,
      "the UI actually polled this experiment's detail",
      `${requests.filter((r) => detail.test(r.url)).length} request(s)`,
    );

    await page.waitForTimeout(2000);
    const mark = Date.now();
    await page.waitForTimeout(12000);
    const after = requests.filter((r) => r.at > mark && detail.test(r.url));
    check(
      after.length === 0,
      "polling STOPS once the run is terminal (observed over 12 s)",
      `${after.length} further request(s) for #${createdId}`,
    );
  }

  // ---- results, and MT-006's visual half --------------------------------
  const resultsTab = await page.$('button:has-text("Results")');
  if (resultsTab) {
    await resultsTab.click();
    await page.waitForTimeout(1500);
    const body = (await page.textContent("body")) ?? "";
    const shown = (body.match(/accuracy[^0-9]{0,24}([0-9]+\.[0-9]+)%/i) ?? [])[1];
    check(
      shown !== undefined,
      "classification results show a numeric accuracy (MT-006: a classifier metric)",
      shown ? `${shown}%` : "no accuracy figure rendered",
    );
    await page.screenshot({ path: `${DIR}/04_results.png`, fullPage: true });
  }

  console.log(`\nArtifacts: ${DIR}`);
} catch (err) {
  console.log(`FAIL  harness error — ${String(err).split("\n")[0].slice(0, 160)}`);
  failures += 1;
} finally {
  await browser.close();
}

console.log(
  failures === 0
    ? `\nALL CHECKS PASSED — ${checks} browser assertions the SSR harnesses cannot make`
    : `\n${failures} FAILED of ${checks}`,
);
process.exit(failures === 0 ? 0 : 1);
