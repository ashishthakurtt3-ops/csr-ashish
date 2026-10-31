import asyncio
from playwright.async_api import async_playwright
import json

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        print("Navigating to https://daanveda.com/pricing ...")
        await page.goto("https://daanveda.com/pricing", wait_until="networkidle", timeout=30000)
        
        computed = await page.evaluate("""() => {
            function getProps(sel) {
                const el = document.querySelector(sel);
                if (!el) return null;
                const s = window.getComputedStyle(el);
                return {
                    selector: sel,
                    fontFamily: s.fontFamily,
                    fontSize: s.fontSize,
                    fontWeight: s.fontWeight,
                    fontStyle: s.fontStyle,
                    letterSpacing: s.letterSpacing,
                    lineHeight: s.lineHeight,
                    color: s.color,
                    background: s.background,
                    backgroundColor: s.backgroundColor,
                    backgroundImage: s.backgroundImage,
                    borderRadius: s.borderRadius,
                    padding: s.padding,
                    margin: s.margin,
                    boxShadow: s.boxShadow,
                    border: s.border,
                    webkitBackgroundClip: s.webkitBackgroundClip
                };
            }
            return {
                body: getProps('body'),
                eyebrow: getProps('.pr-eyebrow'),
                title: getProps('.pr-title'),
                titleEm: getProps('.pr-title em'),
                sub: getProps('.pr-sub'),
                toggle: getProps('.pr-toggle'),
                toggleBtnActive: getProps('.pr-toggle__btn.is-active, .pr-toggle__btn[aria-selected="true"]'),
                card: getProps('[class*="plan-card"], [class*="pricing-card"], .pricing__card'),
                header: getProps('header, nav'),
                navLink: getProps('header nav a, nav a'),
                navBtn: getProps('header button, header a[class*="btn"], nav a[class*="btn"]')
            };
        }""")
        print(json.dumps(computed, indent=2))
        await browser.close()

asyncio.run(inspect())

