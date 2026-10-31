import asyncio
import os
from playwright.async_api import async_playwright

async def audit_mobile():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Mobile viewport 375x812 (iPhone 13 / 14 / mini standard)
        context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()
        
        # Collect console errors
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: errors.append(f"LOG: {msg.text}") if msg.type == "error" else None)
        
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        await page.evaluate("() => { localStorage.removeItem('theme'); document.documentElement.removeAttribute('data-theme'); }")
        await page.reload(wait_until="networkidle")
        await asyncio.sleep(1)
        
        # Check horizontal overflow on document
        def check_overflow():
            return page.evaluate("""() => {
                const docWidth = document.documentElement.offsetWidth;
                const scrollWidth = document.documentElement.scrollWidth;
                const bodyWidth = document.body.scrollWidth;
                const overflows = [];
                document.querySelectorAll('*').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.right > docWidth + 2) {
                        overflows.push({
                            tag: el.tagName,
                            id: el.id,
                            className: el.className,
                            right: rect.right,
                            docWidth: docWidth
                        });
                    }
                });
                return {
                    docWidth,
                    scrollWidth,
                    bodyWidth,
                    hasDocOverflow: scrollWidth > docWidth || bodyWidth > docWidth,
                    overflowElements: overflows.slice(0, 15)
                };
            }""")
            
        print("=== MOBILE OVERFLOW AUDIT: HOME / COMPANIES TAB ===")
        overflow_home = await check_overflow()
        print("Home tab overflow:", overflow_home)
        await page.screenshot(path="scratch/audit_mobile_home.png", full_page=False)

        print("=== MOBILE OVERFLOW AUDIT: JOBS TAB ===")
        await page.evaluate("switchTab('jobs')")
        await asyncio.sleep(1)
        overflow_jobs = await check_overflow()
        print("Jobs tab overflow:", overflow_jobs)
        await page.screenshot(path="scratch/audit_mobile_jobs.png", full_page=False)

        print("=== MOBILE OVERFLOW AUDIT: CSR PROJECTS TAB ===")
        await page.evaluate("switchTab('csr-projects')")
        await asyncio.sleep(1)
        overflow_csr = await check_overflow()
        print("CSR tab overflow:", overflow_csr)
        await page.screenshot(path="scratch/audit_mobile_csr.png", full_page=False)

        print("=== MOBILE OVERFLOW AUDIT: PRICING TAB ===")
        await page.evaluate("switchTab('pricing')")
        await asyncio.sleep(1)
        overflow_pricing = await check_overflow()
        print("Pricing tab overflow:", overflow_pricing)
        await page.screenshot(path="scratch/audit_mobile_pricing.png", full_page=False)

        await browser.close()

asyncio.run(audit_mobile())

