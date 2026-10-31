import asyncio
import os
import shutil
from playwright.async_api import async_playwright
from PIL import Image

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
        home_path = "scratch/portal_fidelity_home_desktop.png"
        await page.screenshot(path=home_path, full_page=False)
        print(f"Captured {home_path}")
        
        # Switch to Pricing tab
        print("Switching to Pricing tab...")
        await page.evaluate("switchTab('pricing')")
        await asyncio.sleep(2)
        pricing_path = "scratch/portal_fidelity_pricing_desktop.png"
        await page.screenshot(path=pricing_path, full_page=False)
        print(f"Captured {pricing_path}")

        pricing_full_path = "scratch/portal_fidelity_pricing_full.png"
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
        
        mobile_path = "scratch/portal_fidelity_pricing_mobile.png"
        await mobile_page.screenshot(path=mobile_path, full_page=False)
        print(f"Captured {mobile_path}")

        mobile_full_path = "scratch/portal_fidelity_pricing_mobile_full.png"
        await mobile_page.screenshot(path=mobile_full_path, full_page=True)
        print(f"Captured {mobile_full_path}")
        
        await mobile_context.close()
        await browser.close()

    # 3. Create Side-by-Side Composite Images with PIL
    def create_side_by_side(img1_path, img2_path, out_path, title1="REFERENCE: DaanVeda.com", title2="CSR JOB INTELLIGENCE"):
        if not (os.path.exists(img1_path) and os.path.exists(img2_path)):
            print(f"Skipping {out_path}, source missing.")
            return
        im1 = Image.open(img1_path)
        im2 = Image.open(img2_path)
        
        # Target height = max of both
        h = min(im1.height, im2.height)
        im1 = im1.crop((0, 0, im1.width, h))
        im2 = im2.crop((0, 0, im2.width, h))
        
        total_w = im1.width + im2.width
        composite = Image.new("RGB", (total_w, h))
        composite.paste(im1, (0, 0))
        composite.paste(im2, (im1.width, 0))
        composite.save(out_path)
        print(f"Created side-by-side composite: {out_path}")

    create_side_by_side(
        "scratch/daanveda_pricing_desktop.png",
        "scratch/portal_fidelity_pricing_desktop.png",
        "scratch/comparison_pricing_desktop_sidebyside.png"
    )
    
    create_side_by_side(
        "scratch/daanveda_home_desktop.png",
        "scratch/portal_fidelity_home_desktop.png",
        "scratch/comparison_home_desktop_sidebyside.png"
    )
    
    create_side_by_side(
        "scratch/daanveda_pricing_mobile.png",
        "scratch/portal_fidelity_pricing_mobile.png",
        "scratch/comparison_pricing_mobile_sidebyside.png"
    )

    # 4. Copy to Artifact Directory
    for fname in [
        "portal_fidelity_pricing_desktop.png",
        "portal_fidelity_pricing_full.png",
        "portal_fidelity_home_desktop.png",
        "portal_fidelity_pricing_mobile.png",
        "portal_fidelity_pricing_mobile_full.png",
        "comparison_pricing_desktop_sidebyside.png",
        "comparison_home_desktop_sidebyside.png",
        "comparison_pricing_mobile_sidebyside.png"
    ]:
        src = os.path.join("scratch", fname)
        dst = os.path.join(ARTIFACT_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {fname} to artifacts directory.")

asyncio.run(main())

