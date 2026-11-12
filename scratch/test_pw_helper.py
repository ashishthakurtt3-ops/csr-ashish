import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

def fetch_rendered_page_sync(url: str, timeout: int = 15):
    async def _render():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                resp = await page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
                await page.wait_for_timeout(2500)
                status = resp.status if resp else 200
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                for tag in soup(['script', 'style', 'nav', 'footer', 'noscript']):
                    tag.decompose()
                text = re_text = soup.get_text(' ', strip=True)
                return html, text, status
            finally:
                await browser.close()
    return asyncio.run(_render())

try:
    h, t, s = fetch_rendered_page_sync("https://careers.tatamotors.com/viewalljobs/")
    print(f"Rendered Tata Motors! Status: {s}, HTML: {len(h)}, Text: {len(t)}")
    print("Excerpt:", t[:200])
except Exception as e:
    print("Error:", e)

