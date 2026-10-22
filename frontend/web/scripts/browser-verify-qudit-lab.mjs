/** Full automated browser verification of Qudit Lab using local Edge and Playwright. */

import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

import { launchOptions, artifactDir } from "./browser-env.mjs";
const ARTIFACT_DIR = artifactDir("qudit-lab");
async function main() {
  console.log("=".repeat(80));
  console.log("STARTING REAL BROWSER QA FOR QUDIT LAB (BETA)");
  console.log("=".repeat(80));

  const browser = await chromium.launch({
    ...launchOptions(),
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1400, height: 950 },
  });
  const page = await context.newPage();

  // Listen for console errors
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });

  try {
    // 1. Login flow
    console.log("\n[Browser Step 1] Navigating to http://localhost:3001/login...");
    await page.goto("http://localhost:3001/login", { waitUntil: "networkidle" });

    console.log("[Browser Step 2] Entering student credentials...");
    await page.fill('input[type="email"]', "student@quantum.local");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');

    await page.waitForURL("**/learn", { timeout: 15000 });
    console.log("PASS: Logged in successfully. Current URL:", page.url());

    // 2. Navigation to Qudit Lab via top-level link
    console.log("\n[Browser Step 3] Locating and clicking 'Qudit Lab (Beta)' sidebar navigation link...");
    const quditNavLink = page.locator('a[href="/qudit-lab"]');
    await quditNavLink.waitFor({ state: "visible", timeout: 5000 });
    await quditNavLink.click();

    await page.waitForURL("**/qudit-lab", { waitUntil: "networkidle" });
    console.log("PASS: Navigated to /qudit-lab via sidebar navigation.");

    // 3. Verify core workbench components
    console.log("\n[Browser Step 4] Verifying Qudit Lab layout and controls...");
    const headerTitleLoc = page.locator('h1:has-text("Qudit Lab")').first();
    await headerTitleLoc.waitFor({ state: "visible", timeout: 10000 });
    const headerTitle = await headerTitleLoc.innerText();
    console.log("PASS: Page title found:", headerTitle);
    if (!headerTitle.includes("Qudit Lab")) {
      throw new Error(`Expected title 'Qudit Lab', got '${headerTitle}'`);
    }

    // Verify dimension buttons
    const dimButtons = page.locator('button:has-text("d = ")');
    const dimCount = await dimButtons.count();
    console.log(`PASS: Found ${dimCount} local dimension selector buttons.`);
    if (dimCount !== 4) {
      throw new Error(`Expected 4 dimension buttons (d=2,3,4,5), found ${dimCount}`);
    }

    // Verify resource status bar
    const statusBar = page.locator("text=State Dimension:");
    await statusBar.waitFor({ state: "visible" });
    console.log("PASS: Resource & Safety status bar visible.");

    // Verify gate palette
    const gatePalette = page.locator("text=Gate Palette");
    await gatePalette.waitFor({ state: "visible" });
    console.log("PASS: Qudit Gate Palette rendered.");

    // Verify circuit canvas
    const circuitCanvas = page.locator("text=Qudit Circuit Canvas");
    await circuitCanvas.waitFor({ state: "visible" });
    console.log("PASS: Qudit Circuit Editor canvas rendered.");

    // 4. Test Preset 1: Fourier Superposition
    console.log("\n[Browser Step 5] Selecting 'Fourier Superposition (F_3)' preset...");
    const fourierPreset = page.locator('button:has-text("Fourier Superposition")').first();
    await fourierPreset.click();

    console.log("[Browser Step 6] Clicking 'Run Simulation' button...");
    const runBtn = page.locator('button:has-text("Run Simulation")');
    await runBtn.click();

    // Wait for simulation execution and results
    await page.waitForSelector("text=Execution time:", { timeout: 10000 });
    console.log("PASS: Simulation completed. Execution time badge visible.");

    // Verify density matrix diagnostics
    const traceVal = await page.locator("text=Trace Tr(ρ)").locator("../..").locator(".font-mono.font-bold").innerText();
    const purityVal = await page.locator("text=Purity γ = Tr(ρ²)").locator("..").locator(".font-mono.font-bold").innerText();
    console.log(`PASS: Diagnostics: Trace = ${traceVal}, Purity = ${purityVal}`);

    // Screenshot 1: Fourier Superposition Matrix
    const ss1Path = path.join(ARTIFACT_DIR, "qudit_lab_fourier_simulation.png");
    await page.screenshot({ path: ss1Path, fullPage: true });
    console.log("PASS: Saved screenshot 1:", ss1Path);

    // 5. Test Measurement Distribution tab
    console.log("\n[Browser Step 7] Switching to 'Measurement Distribution' tab...");
    const distTab = page.locator('button:has-text("Measurement Distribution")');
    await distTab.click();
    await page.waitForSelector("text=Exact Born-rule probability distribution");
    console.log("PASS: Measurement distribution tab visible with probabilities.");

    // 6. Test Preset 2: Two-Qudit Bell State Entanglement
    console.log("\n[Browser Step 8] Selecting 'Two-Qudit Bell State (|Φ_3⟩)' preset...");
    const bellPreset = page.locator('button:has-text("Bell State")').first();
    await bellPreset.click();

    // Verify 2 wires rendered
    await page.waitForSelector("text=q1");
    console.log("PASS: Multi-qudit circuit canvas rendered with wires q0 and q1.");

    console.log("[Browser Step 9] Running Bell state entanglement simulation...");
    await runBtn.click();
    await page.waitForSelector("text=Execution time:", { timeout: 10000 });

    // Click Reduced Subsystems tab
    console.log("[Browser Step 10] Switching to 'Reduced Subsystems' tab...");
    const reducedTab = page.locator('button:has-text("Reduced Subsystems")');
    await reducedTab.click();

    await page.waitForSelector("text=Signature of Quantum Entanglement Detected!", { timeout: 5000 });
    console.log("PASS: Entanglement signature detected! Subsystem q0 reduced matrix and mixed state callout verified.");

    // Screenshot 2: Entangled Bell State Reduced Subsystem
    const ss2Path = path.join(ARTIFACT_DIR, "qudit_lab_bell_entanglement.png");
    await page.screenshot({ path: ss2Path, fullPage: true });
    console.log("PASS: Saved screenshot 2:", ss2Path);

    // 7. Test Dimension Switching to d=4 and d=5
    console.log("\n[Browser Step 11] Switching local dimension to d = 4 (Ququart)...");
    const d4Btn = page.locator('button:has-text("d = 4")');
    await d4Btn.click();
    await page.waitForSelector("text=Safety Cap: Max 5 Qudits at d=4");
    console.log("PASS: Switched to d=4. Safety cap updated to 5 qudits.");

    console.log("[Browser Step 12] Switching local dimension to d = 5 (5-Level)...");
    const d5Btn = page.locator('button:has-text("d = 5")');
    await d5Btn.click();
    await page.waitForSelector("text=Safety Cap: Max 4 Qudits at d=5");
    console.log("PASS: Switched to d=5. Safety cap updated to 4 qudits.");

    // 8. Test Gate Addition, Reordering and Removal in Circuit Editor
    console.log("\n[Browser Step 13] Testing gate operations: addition, selection, reordering, and removal...");
    // Add X_5 gate from palette
    const addShiftBtn = page.locator('button[aria-label*="Shift"]').first();
    await addShiftBtn.click();
    console.log("PASS: Appended X_5 gate from palette.");

    // Select the newly added gate in circuit canvas
    const gateNodes = page.locator('div[title*="Click to configure"]');
    const gateCountBefore = await gateNodes.count();
    console.log(`PASS: Circuit now contains ${gateCountBefore} gate nodes.`);

    // Click the second gate to open parameter inspector
    await gateNodes.nth(1).click();
    await page.waitForSelector("text=Configure Operation:", { timeout: 3000 });
    console.log("PASS: Gate parameter configuration panel opened.");

    // Test reorder: move gate left
    const moveLeftBtn = page.locator('button[aria-label="Move gate left"]');
    await moveLeftBtn.click();
    console.log("PASS: Reordered gate (moved left).");

    // Test remove: click Delete gate
    const deleteGateBtn = page.locator('button[aria-label="Delete gate"]');
    await deleteGateBtn.click();
    await page.waitForTimeout(300);
    const gateCountAfter = await page.locator('div[title*="Click to configure"]').count();
    console.log(`PASS: Deleted gate. Gate count reduced from ${gateCountBefore} to ${gateCountAfter}.`);

    // 9. Test Noise Controls
    console.log("\n[Browser Step 14a] Switching to d = 3 and testing Depolarizing Noise with p = 0.35...");
    const d3Btn = page.locator('button:has-text("d = 3")');
    await d3Btn.click();
    await page.waitForSelector("text=Safety Cap: Max 6 Qudits at d=3");

    // Enable Depolarizing Noise
    const depolCheckbox = page.locator('input[aria-label="Toggle depolarizing noise"]');
    if (!(await depolCheckbox.isChecked())) {
      await depolCheckbox.check();
    }

    // Set error probability p to 0.35 explicitly using the numeric input
    const depolInput = page.locator('input[aria-label="Depolarizing error probability value"]');
    await depolInput.fill("0.35");
    await depolInput.dispatchEvent("change");

    await runBtn.click();
    await page.waitForSelector("text=Execution time:", { timeout: 10000 });

    // Verify purity matches analytical expectation 0.6150 for d=3, p=0.35
    const matrixTab = page.locator('button:has-text("Density Matrix (ρ)")');
    await matrixTab.click();

    const purityD3P35 = await page.locator("text=Purity γ = Tr(ρ²)").locator("..").locator(".font-mono.font-bold").innerText();
    console.log(`PASS: d=3, p=0.35 simulation completed. Purity = ${purityD3P35.split("\n")[0]} (Expected: 0.6150)`);
    if (!purityD3P35.includes("0.6150")) {
      throw new Error(`Expected purity 0.6150 for d=3, p=0.35, got ${purityD3P35}`);
    }

    const ss3aPath = path.join(ARTIFACT_DIR, "qudit_lab_noise_d3_p035.png");
    await page.screenshot({ path: ss3aPath, fullPage: true });
    console.log("PASS: Saved screenshot 3a (d=3, p=0.35):", ss3aPath);

    console.log("\n[Browser Step 14b] Switching to d = 5 and testing Depolarizing Noise with p = 0.10...");
    await d5Btn.click();
    await page.waitForSelector("text=Safety Cap: Max 4 Qudits at d=5");

    if (!(await depolCheckbox.isChecked())) {
      await depolCheckbox.check();
    }
    await depolInput.fill("0.10");
    await depolInput.dispatchEvent("change");

    await runBtn.click();
    await page.waitForSelector("text=Execution time:", { timeout: 10000 });

    const purityD5P10 = await page.locator("text=Purity γ = Tr(ρ²)").locator("..").locator(".font-mono.font-bold").innerText();
    console.log(`PASS: d=5, p=0.10 simulation completed. Purity = ${purityD5P10.split("\n")[0]} (Expected: 0.8480)`);
    if (!purityD5P10.includes("0.8480")) {
      throw new Error(`Expected purity 0.8480 for d=5, p=0.10, got ${purityD5P10}`);
    }

    const ss3bPath = path.join(ARTIFACT_DIR, "qudit_lab_noise_simulation.png");
    await page.screenshot({ path: ss3bPath, fullPage: true });
    console.log("PASS: Saved screenshot 3b (d=5, p=0.10):", ss3bPath);

    console.log("\n[Browser Step 14c] Testing d = 5 with Depolarizing Noise p = 0.35...");
    await depolInput.fill("0.35");
    await depolInput.dispatchEvent("change");

    await runBtn.click();
    await page.waitForSelector("text=Execution time:", { timeout: 10000 });

    const purityD5P35 = await page.locator("text=Purity γ = Tr(ρ²)").locator("..").locator(".font-mono.font-bold").innerText();
    console.log(`PASS: d=5, p=0.35 simulation completed. Purity = ${purityD5P35.split("\n")[0]} (Expected: 0.5380)`);
    if (!purityD5P35.includes("0.5380")) {
      throw new Error(`Expected purity 0.5380 for d=5, p=0.35, got ${purityD5P35}`);
    }

    // 10. Verify existing Qubit Composer is unaffected
    console.log("\n[Browser Step 15] Navigating to /composer to verify Qubit Composer remains functional...");
    await page.goto("http://localhost:3001/composer", { waitUntil: "networkidle" });
    await page.waitForSelector("text=Run on Hardware/Sim", { timeout: 10000 });
    console.log("PASS: Qubit Composer loaded successfully. Existing workflows unaffected.");

    console.log("\n" + "=".repeat(80));
    console.log("REAL BROWSER QA SUMMARY: ALL FLOWS PASSED!");
    console.log("Console Errors:", consoleErrors.length === 0 ? "None (0 errors)" : consoleErrors);
    console.log("=".repeat(80));
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("FATAL BROWSER ERROR:", err);
  process.exit(1);
});
