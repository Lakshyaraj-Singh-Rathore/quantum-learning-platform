import os
import sys
import time

# Force UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

def run_browser_audit():
    print("=" * 80)
    print("STARTING COMPREHENSIVE E2E BROWSER VERIFICATION VIA MICROSOFT EDGE")
    print("=" * 80)

    screenshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "qa", "screenshots"))
    os.makedirs(screenshots_dir, exist_ok=True)
    print(f"[Audit] Destination directory: {screenshots_dir}")

    console_logs = []
    page_errors = []
    network_errors = []

    with sync_playwright() as p:
        print("[Playwright] Launching Microsoft Edge Chromium...")
        browser = p.chromium.launch(
            channel="msedge",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )

        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        )
        page = context.new_page()

        def on_console(msg):
            try:
                text = f"[{msg.type}] {msg.text}"
                console_logs.append(text)
                if msg.type in ["error"]:
                    print(f"  [Browser Console Error] {text.encode('ascii', errors='replace').decode('ascii')}")
            except Exception:
                pass

        def on_page_error(err):
            try:
                page_errors.append(str(err))
                print(f"  [Page Exception] {str(err).encode('ascii', errors='replace').decode('ascii')}")
            except Exception:
                pass

        def on_response(res):
            if res.status >= 400 and not res.url.endswith("/favicon.ico"):
                text = f"HTTP {res.status} on {res.url}"
                network_errors.append(text)
                print(f"  [Network Response Error] {text}")

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("response", on_response)

        # -------------------------------------------------------------
        # 1. AUTHENTICATION & LOGIN
        # -------------------------------------------------------------
        print("\n--- 1. Testing /login & Authentication ---")
        page.goto("http://localhost:3001/login", wait_until="networkidle", timeout=15000)
        time.sleep(1)
        shot1 = os.path.join(screenshots_dir, "01_login_page.png")
        page.screenshot(path=shot1, full_page=True)
        print(f"  Captured: {shot1}")

        student_demo_btn = page.locator("button:has-text('Student Demo')")
        if student_demo_btn.count() > 0:
            print("  Clicking 'Student Demo' 1-click access...")
            student_demo_btn.first.click()
            page.wait_for_url("**/learn", timeout=10000)
            time.sleep(1.5)
        else:
            page.fill("input[type='email']", "student@quantum.local")
            page.fill("input[type='password']", "password123")
            page.click("button[type='submit']")
            page.wait_for_url("**/learn", timeout=10000)
            time.sleep(1.5)

        shot2 = os.path.join(screenshots_dir, "02_learn_dashboard.png")
        page.screenshot(path=shot2, full_page=True)
        print(f"  Captured: {shot2}")

        # -------------------------------------------------------------
        # 2. QUANTUM COMPOSER & MULTI-FORMAT IMPORT
        # -------------------------------------------------------------
        print("\n--- 2. Testing /composer & Multi-Format Import ---")
        page.goto("http://localhost:3001/composer", wait_until="networkidle", timeout=15000)
        time.sleep(2)
        shot3 = os.path.join(screenshots_dir, "03_composer_initial.png")
        page.screenshot(path=shot3, full_page=True)
        print(f"  Captured: {shot3}")

        # Test Import Dialog
        import_btn = page.locator("button:has-text('Import'), [title*='Import'], button:has-text('import')")
        if import_btn.count() > 0:
            print("  Opening Multi-Format Import modal...")
            import_btn.first.click()
            time.sleep(1)
            shot3b = os.path.join(screenshots_dir, "03b_composer_import_modal.png")
            page.screenshot(path=shot3b, full_page=True)
            print(f"  Captured: {shot3b}")
            
            # Close dialog
            cancel_btn = page.locator("button:has-text('Cancel')")
            if cancel_btn.count() > 0:
                cancel_btn.first.click()
                time.sleep(0.5)

        # Run Standard Simulation
        sim_btn = page.locator("button:has-text('Run Simulation'), button:has-text('Simulate'), button:has-text('Run')")
        if sim_btn.count() > 0:
            print("  Running ideal quantum simulation...")
            sim_btn.first.click()
            time.sleep(2.5)
            shot4 = os.path.join(screenshots_dir, "04_composer_simulation_results.png")
            page.screenshot(path=shot4, full_page=True)
            print(f"  Captured: {shot4}")

        # -------------------------------------------------------------
        # 3. EMBEDDED NOISE LAB WORKFLOW IN COMPOSER
        # -------------------------------------------------------------
        print("\n--- 3. Testing Embedded Noise Lab in /composer ---")
        noise_tab_btn = page.locator("button:has-text('Noise Lab')")
        if noise_tab_btn.count() > 0:
            print("  Switching bottom panel to Noise Lab view...")
            noise_tab_btn.first.click()
            time.sleep(1.5)
            shot_nl1 = os.path.join(screenshots_dir, "13_composer_noise_lab_initial.png")
            page.screenshot(path=shot_nl1, full_page=True)
            print(f"  Captured: {shot_nl1}")

            # Run Noisy Simulation
            noise_sim_btn = page.locator("div:has-text('Noise Lab') button:has-text('Simulate'), button:has-text('Simulate')")
            if noise_sim_btn.count() > 0:
                print("  Executing noisy quantum simulation...")
                noise_sim_btn.first.click()
                time.sleep(3)
                shot_nl2 = os.path.join(screenshots_dir, "14_composer_noise_lab_simulation.png")
                page.screenshot(path=shot_nl2, full_page=True)
                print(f"  Captured: {shot_nl2}")

        # -------------------------------------------------------------
        # 4. EMBEDDED SMART COMPOSER AI STUDIO IN COMPOSER
        # -------------------------------------------------------------
        print("\n--- 4. Testing Embedded Smart Composer AI Studio ---")
        smart_btn = page.locator("button:has-text('Smart Composer')")
        if smart_btn.count() > 0:
            print("  Opening Smart Composer panel...")
            smart_btn.first.click()
            time.sleep(1.5)
            shot_sc1 = os.path.join(screenshots_dir, "15_composer_smart_composer_opened.png")
            page.screenshot(path=shot_sc1, full_page=True)
            print(f"  Captured: {shot_sc1}")

            # Switch to Generate Tab if available
            gen_tab = page.locator("button:has-text('Generate'), button:has-text('AI Generate')")
            if gen_tab.count() > 0:
                gen_tab.first.click()
                time.sleep(1)

            # Trigger AI generation
            generate_action_btn = page.locator("button:has-text('Generate Circuit'), button:has-text('Ask AI'), button:has-text('Generate')")
            if generate_action_btn.count() > 0:
                print("  Triggering circuit generation request...")
                generate_action_btn.first.click()
                time.sleep(3)
                shot_sc2 = os.path.join(screenshots_dir, "16_composer_smart_composer_generated.png")
                page.screenshot(path=shot_sc2, full_page=True)
                print(f"  Captured: {shot_sc2}")

        # -------------------------------------------------------------
        # 5. QUDIT LAB DEEP WORKFLOWS
        # -------------------------------------------------------------
        print("\n--- 5. Testing /qudit-lab Deep Workflows ---")
        page.goto("http://localhost:3001/qudit-lab", wait_until="networkidle", timeout=15000)
        time.sleep(2)
        shot_qd1 = os.path.join(screenshots_dir, "07_qudit_lab_initial.png")
        page.screenshot(path=shot_qd1, full_page=True)
        print(f"  Captured: {shot_qd1}")

        # Switch to d=3 (Qutrit)
        dim_3 = page.locator("button:has-text('d=3'), button:has-text('Qutrit')")
        if dim_3.count() > 0:
            print("  Switching to dimension d=3...")
            dim_3.first.click()
            time.sleep(1)

        # Run Qutrit Simulation
        qudit_run_btn = page.locator("button:has-text('Simulate'), button:has-text('Run Simulation'), button:has-text('Run')")
        if qudit_run_btn.count() > 0:
            print("  Running Qutrit density-matrix simulation...")
            qudit_run_btn.first.click()
            time.sleep(2.5)
            shot_qd2 = os.path.join(screenshots_dir, "08_qudit_lab_d3_simulation.png")
            page.screenshot(path=shot_qd2, full_page=True)
            print(f"  Captured: {shot_qd2}")

        # Switch to d=4 (Ququart)
        dim_4 = page.locator("button:has-text('d=4'), button:has-text('Ququart')")
        if dim_4.count() > 0:
            print("  Testing dimension boundary d=4...")
            dim_4.first.click()
            time.sleep(1.5)
            shot_qd3 = os.path.join(screenshots_dir, "19_qudit_lab_d4_fourier_sim.png")
            page.screenshot(path=shot_qd3, full_page=True)
            print(f"  Captured: {shot_qd3}")

        # -------------------------------------------------------------
        # 6. QML LAB COMPREHENSIVE ALGORITHM TESTING
        # -------------------------------------------------------------
        print("\n--- 6. Testing /qml-lab Algorithms ---")
        page.goto("http://localhost:3001/qml-lab", wait_until="networkidle", timeout=15000)
        time.sleep(2)
        shot_qml1 = os.path.join(screenshots_dir, "05_qml_lab_initial.png")
        page.screenshot(path=shot_qml1, full_page=True)
        print(f"  Captured: {shot_qml1}")

        # Test Train Model
        train_btn = page.locator("button:has-text('Train Model'), button:has-text('Start Training'), button:has-text('Train')")
        if train_btn.count() > 0:
            print("  Training QML model...")
            train_btn.first.click()
            time.sleep(4)
            shot_qml2 = os.path.join(screenshots_dir, "06_qml_lab_trained.png")
            page.screenshot(path=shot_qml2, full_page=True)
            print(f"  Captured: {shot_qml2}")

        # -------------------------------------------------------------
        # 7. CURRICULUM & CHALLENGES
        # -------------------------------------------------------------
        print("\n--- 7. Testing /curriculum and /challenges ---")
        page.goto("http://localhost:3001/curriculum", wait_until="networkidle", timeout=15000)
        time.sleep(1.5)
        shot_cur = os.path.join(screenshots_dir, "09_curriculum_page.png")
        page.screenshot(path=shot_cur, full_page=True)
        print(f"  Captured: {shot_cur}")

        page.goto("http://localhost:3001/challenges", wait_until="networkidle", timeout=15000)
        time.sleep(1.5)
        shot_ch = os.path.join(screenshots_dir, "10_challenges_page.png")
        page.screenshot(path=shot_ch, full_page=True)
        print(f"  Captured: {shot_ch}")

        # -------------------------------------------------------------
        # 8. RESPONSIVE MULTI-VIEWPORT VERIFICATION
        # -------------------------------------------------------------
        print("\n--- 8. Testing Responsive Viewports ---")
        # Laptop (1280 x 800)
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto("http://localhost:3001/composer", wait_until="networkidle", timeout=15000)
        time.sleep(1)
        shot_lap = os.path.join(screenshots_dir, "22_responsive_laptop_composer.png")
        page.screenshot(path=shot_lap, full_page=True)
        print(f"  Captured Laptop (1280x800): {shot_lap}")

        # Tablet (768 x 1024)
        page.set_viewport_size({"width": 768, "height": 1024})
        time.sleep(1)
        shot_tab = os.path.join(screenshots_dir, "11_responsive_tablet_composer.png")
        page.screenshot(path=shot_tab, full_page=True)
        print(f"  Captured Tablet (768x1024): {shot_tab}")

        # Mobile (375 x 812)
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto("http://localhost:3001/learn", wait_until="networkidle", timeout=15000)
        time.sleep(1)
        shot_mob = os.path.join(screenshots_dir, "12_responsive_mobile_learn.png")
        page.screenshot(path=shot_mob, full_page=True)
        print(f"  Captured Mobile (375x812): {shot_mob}")

        browser.close()

    print("\n" + "=" * 80)
    print("BROWSER VERIFICATION COMPLETE")
    print(f"Total Console Logs: {len(console_logs)}")
    print(f"Total Page Exceptions: {len(page_errors)}")
    print(f"Total Network HTTP Errors: {len(network_errors)}")
    print("=" * 80)
    return len(page_errors) == 0

if __name__ == "__main__":
    success = run_browser_audit()
    sys.exit(0 if success else 1)
