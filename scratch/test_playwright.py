import asyncio
from playwright.async_api import async_playwright

async def test_playwright(url):
    print(f"Testing Playwright on {url}...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until='networkidle', timeout=15000)
            content = await page.content()
            title = await page.title()
            print(f"Success! Title: {title}, Content length: {len(content)}")
            await browser.close()
    except Exception as e:
        print(f"Playwright error: {e}")

async def main():
    await test_playwright("https://careers.tatamotors.com/")
    await test_playwright("https://careers.wipro.com/")

if __name__ == '__main__':
    asyncio.run(main())

