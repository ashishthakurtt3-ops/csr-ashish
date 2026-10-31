import asyncio
from playwright.async_api import async_playwright
import json

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("https://daanveda.com/", wait_until="networkidle", timeout=30000)
        
        computed = await page.evaluate("""() => {
            function getProps(el) {
                if (!el) return null;
                const s = window.getComputedStyle(el);
                return {
                    tag: el.tagName,
                    class: el.className,
                    fontFamily: s.fontFamily,
                    fontSize: s.fontSize,
                    fontWeight: s.fontWeight,
                    color: s.color,
                    background: s.background,
                    backgroundColor: s.backgroundColor,
                    backgroundImage: s.backgroundImage,
                    borderRadius: s.borderRadius,
                    padding: s.padding,
                    boxShadow: s.boxShadow,
                    border: s.border
                };
            }
            const cards = Array.from(document.querySelectorAll('div, section, article'))
                .filter(el => {
                    const s = window.getComputedStyle(el);
                    return s.borderRadius && s.borderRadius !== '0px' && parseInt(s.borderRadius) >= 16;
                })
                .slice(0, 8)
                .map(getProps);
                
            const buttons = Array.from(document.querySelectorAll('button, a[class*="btn"], a[role="button"]'))
                .slice(0, 6)
                .map(getProps);
                
            return { cards, buttons };
        }""")
        print(json.dumps(computed, indent=2))
        await browser.close()

asyncio.run(inspect())

