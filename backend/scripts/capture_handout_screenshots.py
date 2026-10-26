import os
import sys
import time
from PIL import Image

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3001"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "handouts", "screenshots"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def wait_and_sleep(page, seconds=1.0):
    page.wait_for_load_state("networkidle", timeout=10000)
    time.sleep(seconds)

def login_if_needed(page):
    try:
        page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=12000)
        time.sleep(1.0)
        demo_btn = page.locator("button:has-text('Student Demo'), button:has-text('Instructor Demo')")
        if demo_btn.count() > 0:
            print("  Logging in via Student/Instructor Demo button...")
            demo_btn.first.click()
            page.wait_for_url("**/learn", timeout=8000)
            time.sleep(1.5)
        else:
            email_input = page.locator("input[type='email']")
            if email_input.count() > 0:
                page.fill("input[type='email']", "student@quantum.local")
                page.fill("input[type='password']", "password123")
                page.click("button[type='submit']")
                page.wait_for_url("**/learn", timeout=8000)
                time.sleep(1.5)
    except Exception as e:
        print(f"  Login check notice: {e}")

def create_montage(image_paths, output_path, cols=2, padding=12, bg_color=(10, 15, 30)):
    images = [Image.open(p) for p in image_paths if os.path.exists(p)]
    if not images:
        return
    n = len(images)
    rows = (n + cols - 1) // cols

    max_w = max(img.width for img in images)
    max_h = max(img.height for img in images)

    target_w = min(max_w, 960)
    resized = []
    for img in images:
        aspect = img.height / img.width
        new_h = int(target_w * aspect)
        resized.append(img.resize((target_w, new_h), Image.Resampling.LANCZOS))

    cell_h = max(img.height for img in resized)
    grid_w = cols * target_w + (cols + 1) * padding
    grid_h = rows * cell_h + (rows + 1) * padding

    montage = Image.new("RGB", (grid_w, grid_h), bg_color)
    for idx, img in enumerate(resized):
        r = idx // cols
        c = idx % cols
        x = padding + c * (target_w + padding)
        y = padding + r * (cell_h + padding)
        montage.paste(img, (x, y))

    montage.save(output_path, quality=92)
    print(f"  Created Montage: {output_path}")

def run():
    print(f"Target Output Folder: {OUTPUT_DIR}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=1.25,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
        page = context.new_page()

        # 0. Login
        login_if_needed(page)

        # ------------------------------------------------------------------
        # Screenshot #1: Learn Tab & Curriculum Pathway
        # ------------------------------------------------------------------
        print("\n[1/12] Capturing Learn Tab & Curriculum Pathway...")
        page.goto(f"{BASE_URL}/learn", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)
        shot1 = os.path.join(OUTPUT_DIR, "01_learn_tab_curriculum_pathway.png")
        page.screenshot(path=shot1, full_page=False)
        print(f"  ✓ Saved: {shot1}")

        # ------------------------------------------------------------------
        # Screenshot #2: Quantum Interactive Playground (All 7 Activities)
        # ------------------------------------------------------------------
        print("\n[2/12] Capturing Quantum Interactive Playground (7 Activities)...")
        page.goto(f"{BASE_URL}/playground", wait_until="networkidle", timeout=15000)
        time.sleep(1.5)

        activities = [
            ("bit-vs-qubit", "02a_playground_bit_vs_qubit.png"),
            ("build-qubit", "02b_playground_build_a_qubit.png"),
            ("measure", "02c_playground_measurement.png"),
            ("interference", "02d_playground_interference.png"),
            ("plus-minus", "02e_playground_plus_minus.png"),
            ("many-qubits", "02f_playground_state_growth.png"),
            ("bit-order", "02g_playground_bit_ordering.png"),
        ]

        activity_shots = []
        for tab_id, filename in activities:
            tab_btn = page.locator(f"button[role='tab'][data-value='{tab_id}'], button:has-text('{tab_id}')")
            if tab_btn.count() == 0:
                # search by button text
                name_map = {
                    "bit-vs-qubit": "Bit vs Qubit",
                    "build-qubit": "Build a Qubit",
                    "measure": "Measurement",
                    "interference": "Interference",
                    "plus-minus": "|+⟩ vs |−⟩",
                    "many-qubits": "State Growth",
                    "bit-order": "Bit Ordering",
                }
                tab_btn = page.locator(f"button:has-text('{name_map.get(tab_id)}')")

            if tab_btn.count() > 0:
                tab_btn.first.click()
                time.sleep(0.8)

            shot_path = os.path.join(OUTPUT_DIR, filename)
            page.screenshot(path=shot_path, full_page=False)
            activity_shots.append(shot_path)
            print(f"  ✓ Activity {tab_id}: {shot_path}")

        montage2 = os.path.join(OUTPUT_DIR, "02_quantum_interactive_playground_all_7_activities.png")
        create_montage(activity_shots, montage2, cols=2)

        # ------------------------------------------------------------------
        # Screenshot #3: Qubit Composer Canvas & Gate Palette
        # ------------------------------------------------------------------
        print("\n[3/12] Capturing Qubit Composer Canvas & Gate Palette...")
        page.goto(f"{BASE_URL}/composer", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)
        shot3 = os.path.join(OUTPUT_DIR, "03_qubit_composer_canvas_and_gate_palette.png")
        page.screenshot(path=shot3, full_page=False)
        print(f"  ✓ Saved: {shot3}")

        # ------------------------------------------------------------------
        # Screenshot #4: Bloch Sphere & Phase-Coloured Histogram
        # ------------------------------------------------------------------
        print("\n[4/12] Capturing Bloch Sphere & Phase-Coloured Histogram...")
        # Make sure IBM dual view is active
        dual_btn = page.locator("button:has-text('IBM Dual View')")
        if dual_btn.count() > 0:
            dual_btn.first.click()
            time.sleep(1.0)

        # Scroll down slightly to make both Bloch sphere and histogram with legend prominent
        page.evaluate("window.scrollBy(0, 420)")
        time.sleep(1.0)
        shot4 = os.path.join(OUTPUT_DIR, "04_bloch_sphere_and_phase_histogram.png")
        page.screenshot(path=shot4, full_page=False)
        print(f"  ✓ Saved: {shot4}")

        # ------------------------------------------------------------------
        # Screenshot #5: Advanced State Views (Job Analytics)
        # ------------------------------------------------------------------
        print("\n[5/12] Capturing Advanced State Views (Phase Disk, Q-Sphere, Density Matrix, Born vs Shots)...")
        adv_btn = page.locator("button:has-text('Job Analytics')")
        if adv_btn.count() > 0:
            adv_btn.first.click()
            time.sleep(1.0)

        # Execute simulation to populate Job Analytics if not already done
        run_btn = page.locator("button:has-text('Run on Hardware/Sim'), button:has-text('Execute Simulation Run')")
        if run_btn.count() > 0:
            run_btn.first.click()
            time.sleep(3.0)

        shot5 = os.path.join(OUTPUT_DIR, "05_advanced_state_views.png")
        page.screenshot(path=shot5, full_page=False)
        print(f"  ✓ Saved: {shot5}")

        # ------------------------------------------------------------------
        # Screenshot #6: Simulation Backend Selector
        # ------------------------------------------------------------------
        print("\n[6/12] Capturing Simulation Backend Selector...")
        page.evaluate("window.scrollTo(0, 400)")
        time.sleep(0.5)
        # Click the backend selector dropdown
        backend_select = page.locator("button[aria-label='Simulation backend']")
        if backend_select.count() > 0:
            backend_select.first.click()
            time.sleep(0.8)

        shot6 = os.path.join(OUTPUT_DIR, "06_simulation_backend_selector.png")
        page.screenshot(path=shot6, full_page=False)
        print(f"  ✓ Saved: {shot6}")

        # Close select dropdown by pressing Escape
        page.keyboard.press("Escape")
        time.sleep(0.5)

        # ------------------------------------------------------------------
        # Screenshot #7: Quantum Noise Lab
        # ------------------------------------------------------------------
        print("\n[7/12] Capturing Quantum Noise Lab...")
        noise_btn = page.locator("button:has-text('Noise Lab')")
        if noise_btn.count() > 0:
            noise_btn.first.click()
            time.sleep(1.5)

        # Run Noisy simulation to generate side-by-side ideal vs noisy comparison
        sim_noisy_btn = page.locator("button:has-text('Simulate Noisy Circuit'), button:has-text('Simulate')")
        if sim_noisy_btn.count() > 0:
            sim_noisy_btn.first.click()
            time.sleep(3.5)

        shot7 = os.path.join(OUTPUT_DIR, "07_quantum_noise_lab.png")
        page.screenshot(path=shot7, full_page=False)
        print(f"  ✓ Saved: {shot7}")

        # ------------------------------------------------------------------
        # Screenshot #8: Smart Composer & AI Generation
        # ------------------------------------------------------------------
        print("\n[8/12] Capturing Smart Composer & AI Generation...")
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.5)
        smart_btn = page.locator("button:has-text('Smart Composer')")
        if smart_btn.count() > 0:
            smart_btn.first.click()
            time.sleep(1.5)

        # Trigger AI prompt or generate
        ask_ai_btn = page.locator("button:has-text('Ask AI'), button:has-text('Generate Circuit'), button:has-text('Generate')")
        if ask_ai_btn.count() > 0:
            ask_ai_btn.first.click()
            time.sleep(3.0)

        shot8 = os.path.join(OUTPUT_DIR, "08_smart_composer_and_ai_generation.png")
        page.screenshot(path=shot8, full_page=False)
        print(f"  ✓ Saved: {shot8}")

        # ------------------------------------------------------------------
        # Screenshot #9: Qudit Lab
        # ------------------------------------------------------------------
        print("\n[9/12] Capturing Qudit Lab & Density-Matrix Inspector...")
        page.goto(f"{BASE_URL}/qudit-lab", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)

        # Click d=3 to show qutrit features and new gate palette
        d3_btn = page.locator("button:has-text('d=3'), button:has-text('Qutrit')")
        if d3_btn.count() > 0:
            d3_btn.first.click()
            time.sleep(0.8)

        # Run qudit simulation to show density-matrix inspector
        qudit_sim_btn = page.locator("button:has-text('Simulate'), button:has-text('Run Simulation')")
        if qudit_sim_btn.count() > 0:
            qudit_sim_btn.first.click()
            time.sleep(2.5)

        shot9 = os.path.join(OUTPUT_DIR, "09_qudit_lab_and_density_matrix.png")
        page.screenshot(path=shot9, full_page=False)
        print(f"  ✓ Saved: {shot9}")

        # ------------------------------------------------------------------
        # Screenshot #10: Quantum ML Lab
        # ------------------------------------------------------------------
        print("\n[10/12] Capturing Quantum ML Lab Configuration & Training...")
        page.goto(f"{BASE_URL}/qml-lab", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)

        # Click Train Model or view training dashboard
        train_btn = page.locator("button:has-text('Train Model'), button:has-text('Start Training'), button:has-text('Train')")
        if train_btn.count() > 0:
            train_btn.first.click()
            time.sleep(4.0)

        shot10 = os.path.join(OUTPUT_DIR, "10_quantum_ml_lab_configuration_and_training.png")
        page.screenshot(path=shot10, full_page=False)
        print(f"  ✓ Saved: {shot10}")

        # ------------------------------------------------------------------
        # Screenshot #11: Code Lab
        # ------------------------------------------------------------------
        print("\n[11/12] Capturing Code Lab (Frameworks, AI Assistant, Output)...")
        page.goto(f"{BASE_URL}/codelab", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)

        # Run code in Code Lab
        run_code_btn = page.locator("button:has-text('Run Code'), button:has-text('Run'), button:has-text('Execute')")
        if run_code_btn.count() > 0:
            run_code_btn.first.click()
            time.sleep(3.5)

        shot11 = os.path.join(OUTPUT_DIR, "11_code_lab_frameworks_and_execution.png")
        page.screenshot(path=shot11, full_page=False)
        print(f"  ✓ Saved: {shot11}")

        # ------------------------------------------------------------------
        # Screenshot #12: Challenges & Games
        # ------------------------------------------------------------------
        print("\n[12/12] Capturing Challenges Auto-Grader & Games Hub...")
        page.goto(f"{BASE_URL}/challenges", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)
        shot12a = os.path.join(OUTPUT_DIR, "12a_challenges_autograder.png")
        page.screenshot(path=shot12a, full_page=False)
        print(f"  ✓ Saved: {shot12a}")

        page.goto(f"{BASE_URL}/games", wait_until="networkidle", timeout=15000)
        time.sleep(2.0)
        shot12b = os.path.join(OUTPUT_DIR, "12b_games_hub.png")
        page.screenshot(path=shot12b, full_page=False)
        print(f"  ✓ Saved: {shot12b}")

        # Combined montage for #12
        montage12 = os.path.join(OUTPUT_DIR, "12_challenges_and_games.png")
        create_montage([shot12a, shot12b], montage12, cols=1)

        browser.close()
        print("\n" + "=" * 80)
        print("ALL 12 SCREENSHOTS & MONTAGES SUCCESSFULLY CAPTURED!")
        print(f"Check folder: {OUTPUT_DIR}")
        print("=" * 80)

if __name__ == "__main__":
    run()
