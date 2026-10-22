import { chromium } from "playwright";
import * as path from "path";

import { launchOptions, artifactDir } from "./browser-env.mjs";
const ARTIFACT_DIR = artifactDir("qudit-matrix");
async function main() {
  const browser = await chromium.launch({
    ...launchOptions(),
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1400, height: 1100 },
  });
  const page = await context.newPage();

  try {
    // Login
    await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', "student@quantum.local");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL("**/learn", { timeout: 15000 });

    // Navigate to /qudit-lab
    await page.goto("http://localhost:3001/qudit-lab", { waitUntil: "networkidle" });
    await page.waitForSelector("text=Execution time:", { timeout: 15000 });

    // Select Fourier preset
    const fourierPreset = page.locator('button:has-text("Fourier Superposition")').first();
    await fourierPreset.click();
    await page.click('button:has-text("Run Simulation")');
    await page.waitForSelector("text=Execution time:", { timeout: 10000 });

    // Ensure Density Matrix tab is active
    await page.click('button:has-text("Density Matrix (ρ)")');

    // Scroll down to the matrix inspector
    const matrixCard = page.locator('text=Density Matrix (ρ)').first();
    await matrixCard.scrollIntoViewIfNeeded();

    // Screenshot Magnitude view
    const ssMagPath = path.join(ARTIFACT_DIR, "qudit_lab_matrix_magnitude.png");
    await page.screenshot({ path: ssMagPath });
    console.log("PASS: Saved matrix magnitude view:", ssMagPath);

    // Click Real mode button
    await page.click('button:has-text("Re(ρ)")');
    const ssRealPath = path.join(ARTIFACT_DIR, "qudit_lab_matrix_real.png");
    await page.screenshot({ path: ssRealPath });
    console.log("PASS: Saved matrix real view:", ssRealPath);

    // Click Imag mode button
    await page.click('button:has-text("Im(ρ)")');
    const ssImagPath = path.join(ARTIFACT_DIR, "qudit_lab_matrix_imag.png");
    await page.screenshot({ path: ssImagPath });
    console.log("PASS: Saved matrix imag view:", ssImagPath);

    // Click Phase mode button
    await page.click('button:has-text("∠ρ")');
    const ssPhasePath = path.join(ARTIFACT_DIR, "qudit_lab_matrix_phase.png");
    await page.screenshot({ path: ssPhasePath });
    console.log("PASS: Saved matrix phase view:", ssPhasePath);

    console.log("ALL DENSITY MATRIX VIEW MODES VERIFIED!");
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("ERROR:", err);
  process.exit(1);
});
