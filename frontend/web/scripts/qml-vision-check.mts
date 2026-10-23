/**
 * QML Lab — vision and live-stack coverage.
 *
 * Why this file exists. `vision-qa-master-suite.mjs` targets /qudit-lab only,
 * so the QML Lab had never had a vision pass at all. Worse, the two existing
 * browser harnesses (`qml-browser-check.mts`, `qml-browser-metrics.mts`)
 * contain no algorithm name anywhere: they post whatever the API defaults to.
 * That default is `vqc`, which is why three of the four algorithms -- and
 * `hybrid_qnn` in particular -- had never been driven through the live stack
 * at all. Engine-level training proved the maths, not the product; it never
 * touched the form, the API, the worker or the polling loop.
 *
 * Every algorithm here is therefore named explicitly and driven through the
 * real form, and each one asserts the thing that is specific to it:
 *
 *   vqc                 accuracy metrics, epoch rows recorded
 *   hybrid_qnn          n_hidden exists ONLY here, and is refused above n_qubits
 *   quantum_regression  MAE/RMSE in target units, R² SIGNED (not clamped,
 *                       hidden or abs()'d), zero classifier metrics
 *   quantum_kernel      a closed-form result with a painted heatmap, and
 *                       ZERO epoch rows by design -- exactly the empty state a
 *                       naive UI spins on forever
 *
 *   npm run qml:vision
 */
import { chromium, type Page } from "playwright";
import { launchOptions, artifactDir, browserHelp } from "./browser-env.mjs";

const APP = process.env.QML_APP_URL ?? "http://localhost:3001";
const DIR = artifactDir("qml-vision");

let failures = 0;
/** The payload of the most recent run, so renderings can be checked against it. */
let lastResult: any = null;
function check(ok: boolean, name: string, extra = "") {
  if (!ok) failures += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
}

async function login(page: Page) {
  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "student@quantum.local");
  await page.fill('input[type="password"]', "password123");
  await page.click('button[type="submit"]');
  await page.waitForURL("**/learn", { timeout: 20000 });
}

/** Radix Select: the items are portalled, so they must be opened to be set. */
async function selectByLabel(page: Page, current: string, option: string) {
  await page.locator(`button[role="combobox"]:has-text("${current}")`).first().click();
  await page.waitForTimeout(350);
  await page.locator(`[role="option"]:has-text("${option}")`).first().click();
  await page.waitForTimeout(500);
}

/**
 * The config inputs carry `id`, not `name`. The first version of this helper
 * selected on [name=...], matched nothing, and returned quietly -- so every
 * run silently used the form defaults instead of the small, fast values the
 * harness thought it had set. A helper that can no-op in silence makes the
 * whole harness lie, so this one reports.
 */
async function setNumber(page: Page, id: string, value: string) {
  const el = page.locator(`#${id}`);
  if ((await el.count()) === 0) {
    check(false, `form field #${id} exists to be set`, "not found");
    return false;
  }
  await el.fill(value);
  await page.waitForTimeout(150);
  const got = await el.inputValue();
  check(got === value, `form field #${id} accepted ${value}`, `reads "${got}"`);
  return got === value;
}

/** Drive one run to a terminal state through the UI, observing the polling. */
async function train(page: Page, label: string) {
  // Polling must be observed to happen and then stop. "0 requests after
  // terminal" is indistinguishable from a run that never started, so both
  // halves are counted.
  // The detail endpoint is /api/qml/experiments/<id>?after_epoch=N (api/qml.ts:367).
  // An earlier regex anchored on $ right after the id, so the query string
  // meant it matched nothing and "0 polls" looked like a product defect.
  const polls: number[] = [];
  let lastStatus = "";
  let lastPayload: any = null;
  const onResp = async (r: any) => {
    if (!/\/api\/qml\/experiments\/[^/?]+\?after_epoch=/.test(r.url())) return;
    polls.push(Date.now());
    try {
      const j = await r.json();
      if (j && typeof j.status === "string") {
        lastStatus = j.status;
        lastPayload = j;
      }
    } catch {
      /* non-JSON responses are not status updates */
    }
  };
  page.on("response", onResp);

  await page.locator('button:has-text("Train model")').first().click();

  // Terminal state comes from the API payload the page itself is polling,
  // not from scraping body text for words like "complete" -- the empty state
  // reads "Results appear here once training completes", which is exactly the
  // sort of near-miss that turns a harness into a liar.
  // The API's vocabulary, from models.py:39 and models/qml.py:53 -- not
  // invented. An earlier version waited for "succeeded", which this API never
  // emits, so every run "timed out" while actually completing fine.
  const TERMINAL = ["completed", "failed", "cancelled", "timed_out"];
  const deadline = Date.now() + 240000;
  while (Date.now() < deadline && !TERMINAL.includes(lastStatus)) {
    await page.waitForTimeout(1200);
  }
  const status = lastStatus;
  lastResult = lastPayload;
  const during = polls.length;
  await page.waitForTimeout(6000);
  const after = polls.length - during;
  page.off("response", onResp);

  check(during > 0, `${label}: polling was observed to happen`, `${during} requests`);
  check(after === 0, `${label}: polling stopped after the terminal state`, `${after} after`);
  return status;
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

  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await login(page);

  /* ================= n_hidden is conditional on hybrid_qnn ============== */
  await page.goto(`${APP}/qml-lab`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);

  const hiddenOnVqc = await page.locator("#qml-n-hidden").count();
  check(hiddenOnVqc === 0, "n_hidden is absent for vqc", `${hiddenOnVqc} field(s)`);

  await selectByLabel(page, "Variational classifier", "Hybrid");
  // Switching model refetches /qml/describe and re-derives which controls the
  // algorithm supports. A fixed 800ms sleep raced that refetch and reported
  // "n_hidden absent for hybrid_qnn" -- a harness timing bug that looked
  // exactly like a product defect. Wait for the condition, not the clock.
  await page
    .locator("#qml-n-hidden")
    .waitFor({ state: "attached", timeout: 15000 })
    .catch(() => {});
  const hiddenOnHybrid = await page.locator("#qml-n-hidden").count();
  check(hiddenOnHybrid === 1, "n_hidden appears for hybrid_qnn", `${hiddenOnHybrid} field(s)`);

  // The backend pins n_hidden <= n_qubits. The UI half had never been looked
  // at, and SSR renders the attribute without ever calling checkValidity().
  if (hiddenOnHybrid === 1) {
    const qubits = await page.locator("#qml-n-qubits").inputValue();
    await setNumber(page, "qml-n-hidden", String(Number(qubits) + 4));
    await page.waitForTimeout(400);
    const verdict = await page.evaluate(() => {
      const el = document.querySelector("#qml-n-hidden") as HTMLInputElement | null;
      if (!el) return null;
      return { valid: el.checkValidity(), max: el.max, value: el.value };
    });
    check(
      verdict !== null && verdict.valid === false,
      "QL-020: the form refuses n_hidden > n_qubits in a real browser",
      JSON.stringify(verdict),
    );
    check(
      verdict !== null && verdict.max === qubits,
      "QL-020: the n_hidden ceiling tracks n_qubits, not the static global",
      `max="${verdict?.max}" with n_qubits=${qubits}`,
    );
    await setNumber(page, "qml-n-hidden", "3");
  }
  await page.screenshot({ path: `${DIR}/qml-hybrid-nhidden-1920x1080.png` });

  /* ================= the four algorithms, each named ==================== */
  const RUNS = [
    // n_hidden 3 needs n_qubits >= 3: the classical layer emits one value per
    // wire (hybrid.py:143). The documented recipe pairs n_hidden 3 with the
    // default n_qubits 2, which the backend rejects 422 every time -- which is
    // exactly why hybrid_qnn had never completed a live run.
    { algo: "Hybrid", dataset: "moons", label: "hybrid_qnn/moons", nHidden: "3", nQubits: "4" },
    { algo: "Variational classifier", dataset: "moons", label: "vqc/moons" },
    { algo: "regression", dataset: "sine", label: "quantum_regression/sine" },
    { algo: "kernel", dataset: "moons", label: "quantum_kernel/moons" },
    // Forced negative R². A model worse than predicting the mean scores below
    // zero, and a renderer that clamps, hides or abs()es that tells the reader
    // the opposite of the truth. sine trains too well to produce it (0.966
    // measured), so a harder target is used deliberately.
    { algo: "regression", dataset: "damped_cosine", label: "quantum_regression/damped_cosine", hard: true },
  ];

  for (const run of RUNS) {
    await page.goto(`${APP}/qml-lab`, { waitUntil: "networkidle" });
    await page.waitForTimeout(2200);

    const cur = await page
      .locator('button[role="combobox"]')
      .first()
      .textContent();
    await selectByLabel(page, (cur ?? "").trim(), run.algo);
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.waitForTimeout(1200);

    // The dataset list is algorithm-dependent: /qml/describe without an
    // algorithm returns only classification sets, so regression must be
    // selected after the model, not before.
    const dsBtn = page.locator('button[role="combobox"]').nth(1);
    const dsNow = ((await dsBtn.textContent()) ?? "").trim();
    if (dsNow !== run.dataset) {
      await selectByLabel(page, dsNow, run.dataset);
    }

    // Keep every run inside the documented caps and fast enough to poll.
    await setNumber(page, "qml-n-samples", "60");
    // quantum_kernel is closed-form, so it exposes no epochs control at all.
    // That absence is the designed state, not a missing field.
    if ((await page.locator("#qml-epochs").count()) > 0) {
      await setNumber(page, "qml-epochs", "3");
    } else {
      check(
        run.label.startsWith("quantum_kernel"),
        `${run.label}: an absent epochs control is expected only for the closed-form kernel`,
      );
    }
    if (run.nQubits) await setNumber(page, "qml-n-qubits", run.nQubits);
    if (run.nHidden) await setNumber(page, "qml-n-hidden", run.nHidden);

    await page.screenshot({ path: `${DIR}/qml-${run.label.replace(/\//g, "-")}-config.png` });

    const status = await train(page, run.label);
    check(status === "completed", `${run.label}: reaches a terminal success state`, status || "timed out");

    // Read the Results tab.
    const tab = page.locator('button:has-text("Results")').first();
    if ((await tab.count()) > 0) await tab.click();
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: `${DIR}/qml-${run.label.replace(/\//g, "-")}-results-1920x1080.png`,
      fullPage: true,
    });

    const body = (await page.textContent("body")) ?? "";

    if (run.label.startsWith("quantum_regression")) {
      // Target-unit error metrics, and a SIGNED R². A renderer that clamps,
      // hides or abs()es a negative R² tells the reader the opposite of the
      // truth, so the sign is asserted directly off the rendered text.
      check(/\bMAE\b/i.test(body), "quantum_regression: MAE is shown");
      check(/\bRMSE\b/i.test(body), "quantum_regression: RMSE is shown");
      check(/R²|R\^2/.test(body), "quantum_regression: R² is shown");
      check(
        !/\baccuracy\b/i.test(body),
        "quantum_regression: no classifier metrics are shown",
        /\baccuracy\b/i.test(body) ? "accuracy leaked in" : "none",
      );
      const r2 = body.match(/R²[^-\d]{0,24}(-?\d+\.\d+)/);
      check(r2 !== null, `${run.label}: R² renders a number`, r2 ? r2[1] : "not found");

      // Compare the rendered string against the value the API actually
      // returned. Asserting only "a number appears" would pass against a
      // renderer that silently dropped the minus sign.
      const apiR2 = lastResult?.result?.evaluation?.r2;
      if (typeof apiR2 === "number" && r2) {
        const rendered = Number(r2[1]);
        check(
          Math.sign(rendered) === Math.sign(apiR2),
          `${run.label}: the rendered R² carries the API's sign`,
          `api ${apiR2.toFixed(4)} -> rendered ${r2[1]}`,
        );
        if (run.hard) {
          check(apiR2 < 0, `${run.label}: the run actually produced a negative R²`, `${apiR2.toFixed(4)}`);
          check(
            rendered < 0 && /-/.test(r2[1]),
            `${run.label}: a negative R² is rendered WITH its minus sign, not clamped or abs()'d`,
            `rendered "${r2[1]}"`,
          );
        }
      }
    }

    if (run.label.startsWith("quantum_kernel")) {
      // The kernel is closed-form: it writes ZERO epoch rows by design, which
      // is precisely where a naive UI spins forever or shows an empty chart.
      const rows = await page.locator("table tbody tr").count();
      check(
        !/training in progress|spinner/i.test(body),
        "quantum_kernel: does not sit spinning on a closed-form result",
      );
      const painted = await page.evaluate(() => {
        const cells = Array.from(document.querySelectorAll("[style*='background']"));
        return cells.filter((c) => {
          const bg = getComputedStyle(c as HTMLElement).backgroundColor;
          return bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent";
        }).length;
      });
      check(painted > 50, "quantum_kernel: the heatmap is painted with real cells", `${painted} cells`);
      console.log(`      (kernel epoch rows rendered: ${rows} — zero is the designed state)`);
    }

    if (run.label.startsWith("vqc") || run.label.startsWith("hybrid_qnn")) {
      check(/accuracy/i.test(body), `${run.label}: classifier accuracy is shown`);
    }
  }

  await page.close();
  await browser.close();
  console.log(`\nArtifacts: ${DIR}\n`);
  console.log(failures === 0 ? "All QML vision checks passed." : `${failures} QML vision check(s) FAILED.`);
  if (failures > 0) process.exitCode = 1;
}

await main();
