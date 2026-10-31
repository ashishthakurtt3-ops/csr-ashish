import asyncio
import os
import shutil
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\ashis\.gemini\antigravity\brain\892e2c23-84e8-4698-be4e-67c3418ac8b9"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Context (1440x900)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        
        print("Navigating to http://127.0.0.1:8000/ ...")
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.evaluate("() => { localStorage.removeItem('theme'); document.documentElement.removeAttribute('data-theme'); }")
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(2)
        
        # Capture Desktop Home
        home_path = "scratch/daanveda_redesign_home.png"
        await page.screenshot(path=home_path, full_page=False)
        print(f"Captured {home_path}")
        
        # Switch to Jobs tab
        print("Switching to Jobs tab...")
        await page.evaluate("switchTab('jobs')")
        await asyncio.sleep(2)
        jobs_path = "scratch/daanveda_redesign_jobs.png"
        await page.screenshot(path=jobs_path, full_page=False)
        print(f"Captured {jobs_path}")
        
        # Switch to Pricing tab
        print("Switching to Pricing tab...")
        await page.evaluate("switchTab('pricing')")
        await asyncio.sleep(2)
        pricing_path = "scratch/daanveda_redesign_pricing.png"
        await page.screenshot(path=pricing_path, full_page=False)
        print(f"Captured {pricing_path}")

        # Capture Full Page Pricing to see the cards, wallet, quota, and comparison table
        pricing_full_path = "scratch/daanveda_redesign_pricing_full.png"
        await page.screenshot(path=pricing_full_path, full_page=True)
        print(f"Captured {pricing_full_path}")
        
        await context.close()
        
        # 2. Mobile Context (375x812)
        mobile_context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await mobile_page.evaluate("() => { localStorage.removeItem('theme'); document.documentElement.removeAttribute('data-theme'); }")
        await mobile_page.reload(wait_until="networkidle")
        await asyncio.sleep(2)
        await mobile_page.evaluate("switchTab('pricing')")
        await asyncio.sleep(2)
        
        mobile_path = "scratch/daanveda_redesign_pricing_mobile.png"
        await mobile_page.screenshot(path=mobile_path, full_page=False)
        print(f"Captured {mobile_path}")

        mobile_full_path = "scratch/daanveda_redesign_pricing_mobile_full.png"
        await mobile_page.screenshot(path=mobile_full_path, full_page=True)
        print(f"Captured {mobile_full_path}")
        
        await mobile_context.close()
        await browser.close()
        
        # Copy to artifact directory
        for fname in [
            "daanveda_redesign_home.png",
            "daanveda_redesign_jobs.png",
            "daanveda_redesign_pricing.png",
            "daanveda_redesign_pricing_full.png",
            "daanveda_redesign_pricing_mobile.png",
            "daanveda_redesign_pricing_mobile_full.png"
        ]:
            src = os.path.join("scratch", fname)
            dst = os.path.join(ARTIFACT_DIR, fname)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"Copied {fname} to artifacts directory.")

asyncio.run(main())
