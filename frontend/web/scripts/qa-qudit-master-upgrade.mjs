import { chromium } from "playwright";
import fs from "fs";
import path from "path";

import { launchOptions, artifactDir } from "./browser-env.mjs";
const OUTPUT_DIR = artifactDir("qudit-master");

async function runMasterUpgradeQA() {
  console.log("Starting Master Qudit Composer Visual QA Automation with Edge...");
  const browser = await chromium.launch({
    ...launchOptions(),
    headless: true,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  // 0. Login via UI first
  console.log("Logging in via UI...");
  await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "student@quantum.local");
  await page.fill('input[type="password"]', "password123");
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(1500);

  // 1. Navigate to Qudit Lab
  console.log("Navigating to http://localhost:3001/qudit-lab...");
  await page.goto("http://localhost:3001/qudit-lab", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Screenshot 1: Full Qudit Lab Page Overview
  await page.screenshot({
    path: path.join(OUTPUT_DIR, "01_qudit_lab_full_page.png"),
    fullPage: true,
  });
  console.log("Captured 01_qudit_lab_full_page.png");

  // Screenshot 2: Qudit Composer 3-Column Layout (Matching Qubit Composer / Screenshot C)
  const composerCard = page.locator(".rounded-xl.border.border-line.bg-\\[\\#07090e\\]").first();
  if (await composerCard.isVisible()) {
    await composerCard.screenshot({
      path: path.join(OUTPUT_DIR, "02_qudit_composer_3column_layout.png"),
    });
    console.log("Captured 02_qudit_composer_3column_layout.png");
  }

  // Screenshot 3: Upgraded Viridis Density Matrix Heatmap (Matching Screenshot A)
  const heatmapCard = page.locator("div:has-text('Density Matrix (ρ)')").last();
  await heatmapCard.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1000);
  await page.screenshot({
    path: path.join(OUTPUT_DIR, "03_qudit_density_matrix_viridis_mag.png"),
  });
  console.log("Captured 03_qudit_density_matrix_viridis_mag.png");

  // Screenshot 4: Test Real Mode [Re(ρ)]
  const realBtn = page.locator("button:has-text('Re(ρ)')").first();
  if (await realBtn.isVisible()) {
    await realBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "04_qudit_heatmap_real_mode.png"),
    });
    console.log("Captured 04_qudit_heatmap_real_mode.png");
  }

  // Screenshot 5: Test Imaginary Mode [Im(ρ)]
  const imagBtn = page.locator("button:has-text('Im(ρ)')").first();
  if (await imagBtn.isVisible()) {
    await imagBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "05_qudit_heatmap_imag_mode.png"),
    });
    console.log("Captured 05_qudit_heatmap_imag_mode.png");
  }

  // Screenshot 6: Test Phase Mode [∠ρ]
  const phaseBtn = page.locator("button:has-text('∠ρ')").first();
  if (await phaseBtn.isVisible()) {
    await phaseBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "06_qudit_heatmap_phase_mode.png"),
    });
    console.log("Captured 06_qudit_heatmap_phase_mode.png");
  }

  // Switch back to Magnitude mode
  const magBtn = page.locator("button:has-text('|ρ|')").first();
  if (await magBtn.isVisible()) {
    await magBtn.click();
    await page.waitForTimeout(500);
  }

  // Screenshot 7: Load d=3 Bell-like State Preset
  console.log("Testing d=3 Entangled Preset...");
  const bellPreset = page.locator("button:has-text('Two-Qudit Bell State')").first();
  if (await bellPreset.isVisible()) {
    await bellPreset.click();
    await page.waitForTimeout(2000);
    const inspectorElem = page.locator("div:has-text('Density Matrix (ρ)')").last();
    await inspectorElem.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "07_qudit_bell_state_entangled_heatmap.png"),
    });
    console.log("Captured 07_qudit_bell_state_entangled_heatmap.png");
  }

  // Screenshot 8: Cell Hover / Focus Inspection
  const matrixCell = page.locator("div[title*='|ρ|']").first();
  if (await matrixCell.isVisible()) {
    await matrixCell.hover();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "08_qudit_matrix_cell_hover_inspection.png"),
    });
    console.log("Captured 08_qudit_matrix_cell_hover_inspection.png");
  }

  // Screenshot 9: Dimension Switching to d=4
  console.log("Testing Dimension switch to d=4...");
  const d4Btn = page.locator("button:has-text('d = 4 (Ququart)')").first();
  if (await d4Btn.isVisible()) {
    await d4Btn.click();
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "09_qudit_dimension_4_layout.png"),
    });
    console.log("Captured 09_qudit_dimension_4_layout.png");
  }

  // Screenshot 10: Dimension Switching to d=5
  console.log("Testing Dimension switch to d=5...");
  const d5Btn = page.locator("button:has-text('d = 5 (5-Level)')").first();
  if (await d5Btn.isVisible()) {
    await d5Btn.click();
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, "10_qudit_dimension_5_layout.png"),
    });
    console.log("Captured 10_qudit_dimension_5_layout.png");
  }

  // Responsive Screenshots
  console.log("Testing responsive viewports...");
  const viewports = [
    { name: "11_responsive_laptop_1366x768.png", width: 1366, height: 768 },
    { name: "12_responsive_tablet_768x1024.png", width: 768, height: 1024 },
    { name: "13_responsive_mobile_390x844.png", width: 390, height: 844 },
  ];

  for (const vp of viewports) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.waitForTimeout(800);
    await page.screenshot({
      path: path.join(OUTPUT_DIR, vp.name),
    });
    console.log(`Captured ${vp.name}`);
  }

  await browser.close();
  console.log("Master Qudit Upgrade Visual QA Automation completed successfully!");
}

runMasterUpgradeQA().catch((err) => {
  console.error("QA error:", err);
  process.exit(1);
});
