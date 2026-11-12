from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=India', wait_until='networkidle')
    page.wait_for_timeout(4000)

    # Use browser JavaScript to extract cards
    jobs = page.evaluate("""() => {
        const results = [];
        // Look for headings or card elements
        const items = document.querySelectorAll('li, div[role="listitem"], [class*="job"], [class*="requisition"]');
        for (const el of items) {
            const h = el.querySelector('h1, h2, h3, h4, [class*="title"], a');
            if (!h) continue;
            const title = h.innerText ? h.innerText.trim() : '';
            if (!title || title.length < 5 || title.includes('\\n')) continue;
            const a = el.querySelector('a') || (h.tagName === 'A' ? h : null);
            const link = a ? a.href : '';
            if (title && (title.includes('Engineer') || title.includes('Manager') || title.includes('Associate') || title.includes('Lead') || title.includes('Analyst') || title.includes('Specialist') || title.includes('Developer'))) {
                results.push({title, link, text: el.innerText.substring(0, 150)});
            }
        }
        return results;
    }""")

    print(f"Playwright DOM found {len(jobs)} jobs:")
    for j in jobs[:8]:
        print(f"  * {j['title']} -> {j['link']}")

    browser.close()

