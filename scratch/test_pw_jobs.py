import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def check_rendered_jobs(url):
    print(f"\n--- Checking rendered DOM for: {url} ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(3000)
        content = await page.content()
        await browser.close()
        
    soup = BeautifulSoup(content, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        txt = a.get_text(' ', strip=True)
        if any(k in href.lower() or k in txt.lower() for k in ['job', 'career', 'opening', 'apply', 'req', 'search']):
            if len(txt) > 2 and len(txt) < 80:
                links.append((txt, href))
    print(f"Found {len(links)} links:")
    for t, h in links[:10]:
        print(f"  {t} -> {h}")

asyncio.run(check_rendered_jobs("https://careers.tatamotors.com/"))
asyncio.run(check_rendered_jobs("https://careers.wipro.com/"))
