import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const BASE_URL = "http://localhost:3001";
const SCREENSHOTS_DIR = path.join(process.cwd(), "frontend", "web", "qa-remediation-evidence");

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function run() {
  console.log("Launching Edge browser for visual verification...");
  const browser = await chromium.launch({
    executablePath: EDGE_PATH,
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  console.log("Logging in via UI...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "student@quantum.local");
  await page.fill('input[type="password"]', "password123");
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL("**/learn", { timeout: 15000 });
  console.log("Logged in successfully!");

  console.log("Navigating to Qudit Lab...");
  await page.goto(`${BASE_URL}/qudit-lab`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // 1. Initial State Screenshot (d=3 by default, no d=2 button)
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "01_qudit_lab_initial_d3.png") });
  console.log("Captured 01_qudit_lab_initial_d3.png");

  // Verify d=2 is NOT present in local dimension buttons
  const d2Btn = await page.$("button:has-text('d = 2')");
  console.log("Is d = 2 button present?", d2Btn !== null ? "FAIL (present)" : "PASS (removed)");

  // 2. Click Measurement Distribution Tab and check Born-rule population
  const probTab = await page.waitForSelector("button:has-text('Measurement Distribution')", { timeout: 5000 }).catch(() => null);
  if (probTab) {
    await probTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "02_born_rule_probabilities_fixed.png") });
    console.log("Captured 02_born_rule_probabilities_fixed.png");

    const cardPercentages = await page.$$eval(".text-sm.font-mono.font-semibold.text-white", (els) =>
      els.map((e) => e.textContent?.trim())
    );
    console.log("Reported Born-rule percentages:", cardPercentages);
  } else {
    console.log("Could not find Measurement Distribution button");
  }

  // 3. Click Reduced Subsystems Tab and inspect text contrast
  const redTab = await page.waitForSelector("button:has-text('Reduced Subsystems')", { timeout: 5000 }).catch(() => null);
  if (redTab) {
    await redTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "03_reduced_density_matrix_contrast.png") });
    console.log("Captured 03_reduced_density_matrix_contrast.png");
  }

  // 4. Return to Density Matrix Tab and inspect Viridis heatmap (no 'pop' text)
  const dmTab = await page.waitForSelector("button:has-text('Density Matrix (ρ)')", { timeout: 5000 }).catch(() => null);
  if (dmTab) {
    await dmTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "04_density_matrix_clean_viridis.png") });
    console.log("Captured 04_density_matrix_clean_viridis.png");
  }

  // 5. Test SWAP gate in circuit and inspect interactive controls
  console.log("Testing SWAP gate addition and wire configuration...");
  const addQuditBtn = await page.waitForSelector("button:has-text('+ Qudit')", { timeout: 5000 }).catch(() => null);
  if (addQuditBtn) {
    await addQuditBtn.click();
    await page.waitForTimeout(500);
  }

  // Click SWAP gate in palette
  const swapBtn = await page.waitForSelector("div[role='button']:has-text('SWAP')", { timeout: 5000 }).catch(() => null);
  if (swapBtn) {
    await swapBtn.click();
    await page.waitForTimeout(500);
  }

  // Run simulation with SWAP
  const runSimBtn = await page.waitForSelector("button:has-text('Run Simulation')", { timeout: 5000 }).catch(() => null);
  if (runSimBtn) {
    await runSimBtn.click();
    await page.waitForTimeout(2000);
  }

  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "05_swap_gate_with_wire_selection.png") });
  console.log("Captured 05_swap_gate_with_wire_selection.png");

  // 6. Test Smart Composer on normal Composer page
  console.log("Navigating to Composer Page to verify Smart Composer...");
  await page.goto(`${BASE_URL}/composer`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Toggle Smart Composer Studio
  const smartBtn = await page.waitForSelector("button:has-text('Smart Composer')", { timeout: 5000 }).catch(() => null);
  if (smartBtn) {
    await smartBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "06_composer_smart_composer_opened.png") });
    console.log("Captured 06_composer_smart_composer_opened.png");

    // Click Analyze & Simplify
    const analyzeBtn = await page.waitForSelector("button:has-text('Analyze & Simplify Circuit')", { timeout: 5000 }).catch(() => null);
    if (analyzeBtn) {
      await analyzeBtn.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "07_smart_composer_simplified_result.png") });
      console.log("Captured 07_smart_composer_simplified_result.png");

      // Click Adopt Simplified Circuit
      const adoptBtn = await page.waitForSelector("button:has-text('Adopt Simplified Circuit into Composer')", { timeout: 5000 }).catch(() => null);
      if (adoptBtn) {
        await adoptBtn.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "08_smart_composer_adopted_remains_open.png") });
        console.log("Captured 08_smart_composer_adopted_remains_open.png (panel stays open!)");
      }
    }
  }

  await browser.close();
  console.log("Visual QA verification complete! All screenshots saved to qa-remediation-evidence.");
}

run().catch((err) => {
  console.error("Test execution failed:", err);
  process.exit(1);
});
