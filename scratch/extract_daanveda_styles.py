from playwright.sync_api import sync_playwright
import json

def extract():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        
        print("Loading daanveda.com/pricing...")
        page.goto('https://daanveda.com/pricing', wait_until='networkidle')

        info = page.evaluate('''() => {
            const bodyStyle = window.getComputedStyle(document.body);
            const extracted = {
                body: {
                    fontFamily: bodyStyle.fontFamily,
                    backgroundColor: bodyStyle.backgroundColor,
                    color: bodyStyle.color,
                    fontSize: bodyStyle.fontSize,
                    lineHeight: bodyStyle.lineHeight,
                },
                elements: []
            };

            const selectors = [
                'header', 'nav', 'nav a', 'h1', 'h2', 'h3',
                'button', '.btn', 'a[class*="btn"]',
                '[class*="card"]', '[class*="plan"]', '[class*="pricing"]',
                '[class*="toggle"]', '[class*="switch"]',
                'table', 'th', 'td', 'footer'
            ];

            for (const sel of selectors) {
                const els = Array.from(document.querySelectorAll(sel)).slice(0, 3);
                for (const el of els) {
                    const s = window.getComputedStyle(el);
                    extracted.elements.push({
                        selector: sel,
                        tag: el.tagName,
                        className: String(el.className || '').slice(0, 100),
                        text: el.innerText ? el.innerText.slice(0, 60).replace(/\\n/g, ' ') : '',
                        color: s.color,
                        backgroundColor: s.backgroundColor,
                        backgroundImage: s.backgroundImage,
                        border: s.border,
                        borderRadius: s.borderRadius,
                        boxShadow: s.boxShadow,
                        fontFamily: s.fontFamily,
                        fontSize: s.fontSize,
                        fontWeight: s.fontWeight,
                        letterSpacing: s.letterSpacing,
                        padding: s.padding,
                        margin: s.margin,
                    });
                }
            }
            return extracted;
        }''')

        # Also get all link stylesheets and css variables
        css_vars = page.evaluate('''() => {
            const root = document.documentElement;
            const s = window.getComputedStyle(root);
            const vars = {};
            for (let i = 0; i < s.length; i++) {
                const prop = s[i];
                if (prop.startsWith('--')) {
                    vars[prop] = s.getPropertyValue(prop).trim();
                }
            }
            return vars;
        }''')
        info['css_variables'] = css_vars

        with open('scratch/daanveda_styles.json', 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)
        print("Saved scratch/daanveda_styles.json")

        browser.close()

if __name__ == '__main__':
    extract()

