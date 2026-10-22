/**
 * §2I.5 browser checks Phase 8 did not reach: the regression half of MT-006,
 * the kernel heatmap (MT-008) and the sample cap (MT-009).
 *
 * Phase 8's browser harness covered the classifier path only. Two of the
 * checks here guard failure modes that look fine in source:
 *
 *  - a regression renderer that clamps, hides or Math.abs()es a negative R².
 *    The sign is the whole content of the metric -- R² < 0 means the model is
 *    worse than predicting the mean -- so a reader shown "3.672" instead of
 *    "-3.672" is told the opposite of the truth. This asserts against a
 *    genuinely negative fixture, because a test that only ever sees a positive
 *    R² cannot detect a clamp.
 *  - a heatmap whose cells carry a Tailwind class that emits no CSS. That is
 *    the bg-card defect (Phase 8 Stage 2.2) in another component, so cells are
 *    checked for computed colour, never for markup.
 *
 * Run from frontend/web, with a live API on :8000 and the built app on :3001:
 *   UITEST_DIR=/home/user/uitest npx tsx scripts/qml-browser-metrics.mts
 */
import { chromium, type Page } from "playwright";
import { launchOptions, artifactDir, browserHelp } from "./browser-env.mjs";

const APP = process.env.QML_APP_URL ?? "http://localhost:3001";
const API = process.env.QML_API_URL ?? "http://127.0.0.1:8000";
const DIR = artifactDir("qml-lab");

let failures = 0;
function check(ok: boolean, name: string, extra = "") {
  if (!ok) failures += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
}

async function login(page: Page) {
  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "student@quantum.local");
  await page.fill('input[type="password"]', "password123");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/learn", { timeout: 15000 });
}

/** Open the lab and wait until the config form is actually interactive. */
async function openLab(page: Page) {
  await page.goto(`${APP}/qml-lab`, { waitUntil: "networkidle" });
  // The form renders disabled until /qml/describe resolves. A fixed sleep
  // raced that fetch and produced "element is not enabled" intermittently.
  await page.locator('[role="combobox"]').first().waitFor({ state: "visible", timeout: 15000 });
  await page.waitForTimeout(1200);
}

/** Select a past experiment from the Recent rail and show its Results. */
async function openExperiment(page: Page, id: number) {
  await openLab(page);
  const entry = page.locator(`text=/#${id}\\b/`).first();
  if ((await entry.count()) === 0) return false;
  await entry.click();
  await page.waitForTimeout(1800);
  const results = await page.$('button:has-text("Results")');
  if (results) {
    await results.click();
    await page.waitForTimeout(1500);
  }
  return true;
}

async function main() {
  let browser;
  try {
    browser = await chromium.launch(launchOptions());
  } catch (err) {
    if (process.env.QML_BROWSER_REQUIRED === "1") throw err;
    console.log(`SKIP  no browser available — ${(err as Error).message.split("\n")[0]}`);
    console.log(browserHelp());
    return;
  }

  const page = await browser.newPage({ viewport: { width: 1480, height: 1000 } });

  // Pick the fixtures from the API rather than hard-coding ids, so a missing
  // one is reported instead of silently asserting against the wrong row.
  const auth = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "student@quantum.local", password: "password123" }),
  }).then((r) => r.json());
  const token = auth.access_token as string;

  const list = await fetch(`${API}/qml/experiments?limit=50`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then((r) => r.json());
  const rows: { id: number; status: string }[] = Array.isArray(list) ? list : (list.items ?? []);

  let regressionId: number | null = null;
  let kernelId: number | null = null;
  let actualR2: number | null = null;
  for (const row of rows) {
    if (row.status !== "completed") continue;
    const d = await fetch(`${API}/qml/experiments/${row.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => r.json());
    const result = d.result ?? {};
    if (result.task === "regression" && regressionId === null) {
      regressionId = row.id;
      actualR2 = result.evaluation?.r2 ?? null;
    }
    if (result.kernel?.gram_preview && kernelId === null) kernelId = row.id;
  }

  await login(page);

  /* ---- MT-009, the sample cap ------------------------------------------- */
  // Runs first: selecting a past experiment puts the config form into its
  // read-only state, after which every control reads as disabled.
  try {
    await openLab(page);

    const datasetTrigger = page.locator('[role="combobox"]').nth(1);
    await datasetTrigger.click();
    await page.waitForTimeout(600);
    const iris = page.locator('[role="option"]:has-text("iris")').first();
    const haveIris = (await iris.count()) > 0;
    check(haveIris, "MT-009: a low-cap dataset (iris_binary, cap 100) is selectable");

    if (haveIris) {
      await iris.click();
      await page.waitForTimeout(1200);

      // Measured, not assumed.
      const samples = await page.$("#qml-n-samples");
      const maxAttr = await samples?.getAttribute("max");
      const value = await samples?.inputValue();

      check(
        maxAttr === "100",
        "MT-009: the samples field's max tracks the selected dataset's cap",
        `max=${maxAttr} while the hint says 100 — native validation cannot enforce the real cap`,
      );
      // The recorded contract (D-059) is stay-and-error, NOT clamp: switching
      // dataset changes the cap underneath a number the learner chose, and
      // silently rewriting it hides that a choice was overridden. So the value
      // is expected to stay, and the obligation moves to the error below.
      check(
        Number(value) > 100,
        "MT-009: the over-cap value is preserved rather than silently rewritten",
        `value stayed ${value} against a cap of 100, as decided`,
      );

      await samples?.fill("400");
      await page.waitForTimeout(800);

      const runBtn = await page.$('button:has-text("Train model")');
      const blocked = (await runBtn?.isDisabled()) ?? false;
      check(blocked, "MT-009: an over-cap configuration cannot be submitted", `train disabled=${blocked}`);

      const body = (await page.textContent("body")) ?? "";
      await page.screenshot({ path: `${DIR}/07_sample_cap.png`, fullPage: true });

      // MT-009 asks for a legible error naming the cap. A disabled control is
      // not one: it prevents the mistake without explaining it. The assertion
      // demands the actual numbers -- the cap AND the rejected value -- so it
      // cannot pass on generic copy, and scopes the read to the error region
      // so it cannot pass on the form's static range hint.
      const errorRegion = (await page.textContent('[role="alert"], .error-note')) ?? body;
      const namesCap = /\b100\b/.test(errorRegion) && /\b400\b|\b200\b/.test(errorRegion);
      const explains = /cap|exceed|lower|too many|reduce/i.test(errorRegion);
      check(
        namesCap && explains,
        "MT-009: the UI says WHY training is unavailable and names the actual cap",
        errorRegion.slice(0, 120).trim() || "no error region rendered",
      );
    }
  } catch (err) {
    // Reported as a failure, never swallowed: an exception here means MT-009
    // is unproven, which is a result rather than the absence of one.
    check(
      false,
      "MT-009: the sample-cap flow could be driven in a browser",
      (err as Error).message.split("\n")[0].slice(0, 120),
    );
  }

  /* ---- MT-006, the regression half -------------------------------------- */

  if (regressionId === null) {
    check(false, "a completed regression experiment exists to inspect", "none found");
  } else {
    const opened = await openExperiment(page, regressionId);
    check(opened, `regression experiment #${regressionId} opens in the Results view`);
    const body = (await page.textContent("body")) ?? "";
    await page.screenshot({ path: `${DIR}/05_regression_results.png`, fullPage: true });

    check(/\bMAE\b/i.test(body), "MT-006: MAE is reported");
    check(/\bRMSE\b/i.test(body), "MT-006: RMSE is reported");
    check(
      /target(’|')?s own units|in the target|target units/i.test(body),
      "MT-006: MAE/RMSE are stated to be in the target's own units, not percentages",
    );

    check(
      actualR2 !== null && actualR2 < 0,
      "MT-006: the fixture under test has a NEGATIVE R² (so a clamp is detectable)",
      `r2=${actualR2}`,
    );
    const shownR2 = body.match(/R²[^-+0-9]{0,24}([+-]?[0-9]+\.[0-9]+)/);
    check(shownR2 !== null, "MT-006: an R² figure is rendered", shownR2?.[1] ?? "none");
    check(
      shownR2 !== null && Number(shownR2[1]) < 0,
      "MT-006: the negative R² is rendered WITH its sign — not clamped, hidden or abs()ed",
      `rendered ${shownR2?.[1]} for an actual ${actualR2}`,
    );

    const classifierTerms = ["accuracy", "f1", "confusion", "precision", "recall"];
    const leaked = classifierTerms.filter((t) => new RegExp(`\\b${t}\\b`, "i").test(body));
    check(
      leaked.length === 0,
      "MT-006: NO classifier metric appears on a regression result",
      leaked.length ? `leaked: ${leaked.join(", ")}` : "none",
    );
  }

  /* ---- MT-008, the kernel heatmap --------------------------------------- */

  if (kernelId === null) {
    check(false, "a completed kernel experiment with a gram preview exists", "none found");
  } else {
    await openExperiment(page, kernelId);
    await page.screenshot({ path: `${DIR}/06_kernel_results.png`, fullPage: true });

    // The cells are plain divs with an inline style, inside the figure after
    // the "Quantum kernel matrix" heading. There is no class or data hook to
    // target, which is the point: colour must arrive as a computed inline
    // style, so that is what is read back.
    const cells = await page.$$eval(
      "figure div[style*='background-color'], figure div[style*='opacity']",
      (els) =>
        els.slice(0, 400).map((e) => {
          const cs = getComputedStyle(e);
          return {
            bg: cs.backgroundColor,
            inline: (e as HTMLElement).getAttribute("style") ?? "",
          };
        }),
    );
    check(cells.length > 0, "MT-008: the kernel heatmap renders cells", `${cells.length} cell(s)`);
    if (cells.length > 0) {
      const painted = cells.filter((c) => c.bg && c.bg !== "rgba(0, 0, 0, 0)" && c.bg !== "transparent");
      check(
        painted.length === cells.length,
        "MT-008: every heatmap cell carries a real computed colour, not a class that emits nothing",
        `${painted.length}/${cells.length} painted`,
      );
      check(
        cells.some((c) => c.inline.includes("background-color")),
        "MT-008: cell colour arrives via an inline style, not an interpolated Tailwind class",
        cells.find((c) => c.inline)?.inline.slice(0, 64) ?? "none",
      );
    }
  }

  await browser.close();

  console.log(`\nArtifacts: ${DIR}\n`);
  console.log(
    failures === 0
      ? "ALL CHECKS PASSED — the §2I.5 metric surfaces Phase 8 left unproven"
      : `${failures} FAILED`,
  );
  if (failures > 0) process.exitCode = 1;
}

await main();
