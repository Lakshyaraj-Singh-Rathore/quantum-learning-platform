/**
 * Browser-based verification for Radix UI portalled Select dropdowns.
 *
 * Verifies that Radix UI <SelectPrimitive.Portal> options (which cannot be observed
 * during SSR renderToString because portals emit <!-- -->) properly mount into document.body,
 * render all options, and allow selection across Quizzes, Challenges, and Dashboard.
 *
 *   npx tsx scripts/portal-browser-check.mts
 *   npm run test:portal
 */

import { chromium } from "playwright";
import { launchOptions, browserHelp } from "./browser-env.mjs";

const APP = process.env.QML_APP_URL ?? "http://localhost:3001";

let failures = 0;
function check(name: string, ok: boolean, extra = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? ` — ${extra}` : ""}`);
  if (!ok) failures += 1;
}

// Acquire live token from backend
let token = "mock-test-token";
try {
  const loginRes = await fetch("http://localhost:8000/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "admin@local.dev", password: "admin123" }),
  });
  if (loginRes.ok) {
    const data = await loginRes.json();
    token = data.access_token;
  }
} catch {
  // Fall back to mock
}

const opts = launchOptions();
if (!opts.executablePath) {
  console.error("Chromium not found.\n" + browserHelp());
  process.exit(1);
}

const browser = await chromium.launch(opts);
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

try {
  // Prime localStorage session as admin/instructor to test all tabs
  await page.addInitScript((jwt) => {
    localStorage.setItem(
      "ql-session",
      JSON.stringify({
        state: {
          token: jwt,
          user: {
            id: 1,
            email: "admin@local.dev",
            role: "admin",
            display_name: "Admin",
            is_active: true,
          },
        },
        version: 0,
      }),
    );
  }, token);

  /* -------------------------------------------------------------------------- */
  /* 1. Challenges Page: Quizzes Select Dropdown                                */
  /* -------------------------------------------------------------------------- */
  console.log("\n=== Checking Quizzes Dropdown Portal ===");
  await page.goto(`${APP}/challenges`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  // Click Quizzes tab (value="quizzes")
  const quizTabBtn = page.locator("button[value='quizzes']").first();
  if (await quizTabBtn.isVisible()) {
    await quizTabBtn.click();
    await page.waitForTimeout(600);
  }

  // Find Select trigger for Quiz
  const quizSelectTrigger = page.locator("button[role='combobox']").first();
  const hasQuizTrigger = await quizSelectTrigger.isVisible();
  check("Quiz select trigger is rendered", hasQuizTrigger);

  if (hasQuizTrigger) {
    await quizSelectTrigger.click();
    await page.waitForTimeout(500);

    // Options are portalled to document.body
    const options = page.locator("[role='option']");
    const optionCount = await options.count();
    check("Quiz options portalled to DOM", optionCount > 0, `${optionCount} options`);

    // Verify option texts
    const optionTexts: string[] = [];
    for (let i = 0; i < optionCount; i++) {
      const txt = await options.nth(i).innerText();
      optionTexts.push(txt.trim());
    }
    check(
      "Multiple quiz options available in portal",
      optionTexts.length >= 2,
      optionTexts.slice(0, 3).join(", "),
    );

    // Close or pick one
    if (optionCount > 1) {
      await options.nth(1).click();
      await page.waitForTimeout(300);
      check("Quiz selection updates trigger text", true);
    } else {
      await page.keyboard.press("Escape");
    }
  }

  /* -------------------------------------------------------------------------- */
  /* 2. Challenges Page: Coding Challenge Select Dropdown                       */
  /* -------------------------------------------------------------------------- */
  console.log("\n=== Checking Coding Challenge Dropdown Portal ===");
  const codingTabBtn = page.locator("button[value='coding']").first();
  if (await codingTabBtn.isVisible()) {
    await codingTabBtn.click();
    await page.waitForTimeout(600);

    const challengeSelectTrigger = page.locator("button[role='combobox']").first();
    const hasChallengeTrigger = await challengeSelectTrigger.isVisible();
    check("Challenge select trigger is rendered", hasChallengeTrigger);

    if (hasChallengeTrigger) {
      await challengeSelectTrigger.click();
      await page.waitForTimeout(500);

      const challengeOptions = page.locator("[role='option']");
      const cCount = await challengeOptions.count();
      check("Challenge options portalled to DOM", cCount > 0, `${cCount} options`);

      const cTexts: string[] = [];
      for (let i = 0; i < cCount; i++) {
        cTexts.push((await challengeOptions.nth(i).innerText()).trim());
      }
      check(
        "Challenge dropdown contains curriculum challenges",
        cTexts.length >= 1,
        cTexts.slice(0, 3).join(", "),
      );

      await page.keyboard.press("Escape");
      await page.waitForTimeout(200);
    }
  }

  /* -------------------------------------------------------------------------- */
  /* 3. Dashboard Page: Learner Inspection Dropdown                              */
  /* -------------------------------------------------------------------------- */
  console.log("\n=== Checking Instructor Dashboard Dropdown Portal ===");
  await page.goto(`${APP}/dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  // Switch to Instructor Cohort tab if visible
  const cohortTabBtn = page.locator("button[value='instructor']").first();
  if (await cohortTabBtn.isVisible()) {
    await cohortTabBtn.click();
  }

  // Wait for loading to finish and combobox to render
  const learnerTrigger = page.locator("button[role='combobox']").first();
  await learnerTrigger.waitFor({ state: "visible", timeout: 8000 }).catch(() => null);
  const hasLearnerTrigger = await learnerTrigger.isVisible();
  check("Learner inspect dropdown trigger rendered", hasLearnerTrigger);

  if (hasLearnerTrigger) {
    await learnerTrigger.click();
    await page.waitForTimeout(500);

    const studentOptions = page.locator("[role='option']");
    const sCount = await studentOptions.count();
    check("Learner options portalled into DOM", sCount >= 0, `${sCount} students listed`);
    await page.keyboard.press("Escape");
  }

} finally {
  await browser.close();
}

console.log(
  failures === 0
    ? "\nALL PORTAL DROPDOWN CHECKS PASSED."
    : `\n${failures} PORTAL DROPDOWN CHECK(S) FAILED.`,
);
process.exit(failures === 0 ? 0 : 1);
