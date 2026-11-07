import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

def fetch_rendered_page(url: str, timeout: int = 15):
    try:
        async def _run():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                try:
                    resp = await page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
                    await page.wait_for_timeout(2000)
                    content = await page.content()
                    status = resp.status if resp else 200
                    return content, status
                finally:
                    await browser.close()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        content, status = loop.run_until_complete(_run())
        loop.close()
        soup = BeautifulSoup(content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'noscript']):
            tag.decompose()
        text = soup.get_text(' ', strip=True)
        return content, text, status
    except Exception as e:
        return "", "", 0

c, t, s = fetch_rendered_page("https://careers.tatamotors.com/viewalljobs/")
print("Status:", s, "Text len:", len(t))
