import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const BASE_URL = "http://localhost:3001";
const ARTIFACT_DIR = "C:\\Users\\laksh\\.gemini\\antigravity-ide\\brain\\26034555-2d87-4dfd-b3f2-9f9fdcef1962";
const SCREENSHOT_PATH = path.join(ARTIFACT_DIR, "circuit_lines_and_gate_colors_fixed.png");

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

  console.log("Logging in...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', "student@quantum.local");
  await page.fill('input[type="password"]', "password123");
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL("**/learn", { timeout: 15000 });

  console.log("Navigating to Qudit Lab...");
  await page.goto(`${BASE_URL}/qudit-lab`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Clear existing circuit
  const clearBtn = await page.waitForSelector("button:has-text('Clear')", { timeout: 5000 });
  if (clearBtn) await clearBtn.click();
  await page.waitForTimeout(500);

  // Click + Qudit twice to have 3 wires
  const addQuditBtn = await page.waitForSelector("button:has-text('+ Qudit')");
  await addQuditBtn.click();
  await page.waitForTimeout(300);
  await addQuditBtn.click();
  await page.waitForTimeout(300);

  // 1. Add F3
  console.log("Adding F3...");
  const fGate = await page.waitForSelector("div[role='button']:has-text('F3')");
  await fGate.click();
  await page.waitForTimeout(300);

  // 2. Add SUM3
  console.log("Adding SUM3...");
  const sumGate = await page.waitForSelector("div[role='button']:has-text('SUM3')");
  await sumGate.click();
  await page.waitForTimeout(300);

  // 3. Add SUM†
  console.log("Adding SUM†...");
  const sumDagGate = await page.waitForSelector("div[role='button']:has-text('SUM†')");
  await sumDagGate.click();
  await page.waitForTimeout(300);

  // 4. Add MCP
  console.log("Adding MCP...");
  const mcpGate = await page.waitForSelector("div[role='button']:has-text('MCP')");
  await mcpGate.click();
  await page.waitForTimeout(300);

  // 5. Add P(θ)
  console.log("Adding P(θ)...");
  const pGate = await page.waitForSelector("div[role='button']:has-text('P(θ)')");
  await pGate.click();
  await page.waitForTimeout(300);

  // 6. Add CCX
  console.log("Adding CCX...");
  const ccxGate = await page.waitForSelector("div[role='button']:has-text('CCX')");
  await ccxGate.click();
  await page.waitForTimeout(300);

  // Deselect by clicking body
  await page.mouse.click(10, 10);
  await page.waitForTimeout(500);

  // Take screenshot of the entire viewport
  await page.screenshot({ path: SCREENSHOT_PATH });
  console.log(`Saved screenshot to: ${SCREENSHOT_PATH}`);

  await browser.close();
  console.log("Verification finished successfully!");
}

run().catch((err) => {
  console.error("Error running visual verification:", err);
  process.exit(1);
});
