import os
import sys
import json
import time

# Force UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

print("=" * 70)
print("STARTING PLAYWRIGHT BROWSER UI VERIFICATION")
print("=" * 70)

results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # ─────────────────────────────────────────────────────────────────
    # 1. Desktop UI: Pricing Page, Cards, Toggle & Comparison Table
    # ─────────────────────────────────────────────────────────────────
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # Switch to pricing tab
    print("\n[1] Switching to Pricing Tab...")
    page.evaluate("switchTab('pricing')")
    page.wait_for_selector("#tab-pricing", state="visible")
    time.sleep(1)

    # Verify 3 plans exist in grid
    cards = page.query_selector_all("#pricing-plans-grid .pricing-card")
    print(f"  Found {len(cards)} pricing cards in #pricing-plans-grid")
    results['three_cards_rendered'] = (len(cards) == 3)

    card_names = [c.query_selector(".plan-name").inner_text().strip() for c in cards]
    print(f"  Rendered plan names: {card_names}")
    results['card_names_correct'] = (card_names == ['FREE', 'PRO', 'ULTRA'])

    # Check Monthly prices
    free_price = cards[0].query_selector(".amount").inner_text().strip()
    pro_price_monthly = cards[1].query_selector(".amount").inner_text().strip()
    ultra_price_monthly = cards[2].query_selector(".amount").inner_text().strip()
    print(f"  Monthly prices: FREE=Rs.{free_price}, PRO=Rs.{pro_price_monthly}, ULTRA=Rs.{ultra_price_monthly}")

    # Test Monthly / Yearly Toggle
    print("\n[2] Testing Billing Toggle (Annual)...")
    toggle_btn = page.query_selector(".billing-cycle-btn[data-cycle='yearly']") or page.query_selector("button:has-text('Annual')")
    if toggle_btn:
        toggle_btn.click()
        time.sleep(1)
        cards_yearly = page.query_selector_all("#pricing-plans-grid .pricing-card")
        pro_price_yearly = cards_yearly[1].query_selector(".amount").inner_text().strip()
        ultra_price_yearly = cards_yearly[2].query_selector(".amount").inner_text().strip()
        pro_period = cards_yearly[1].query_selector(".period").inner_text().strip()
        print(f"  Yearly prices: PRO=Rs.{pro_price_yearly}{pro_period}, ULTRA=Rs.{ultra_price_yearly}{pro_period}")
        results['billing_toggle_works'] = (pro_period == '/year' and pro_price_yearly != pro_price_monthly)

        # Toggle back to Monthly
        month_btn = page.query_selector(".billing-cycle-btn[data-cycle='monthly']") or page.query_selector("button:has-text('Monthly')")
        if month_btn:
            month_btn.click()
            time.sleep(1)
    else:
        results['billing_toggle_works'] = False

    # Check Dynamic Comparison Table
    print("\n[3] Checking Dynamic Comparison Table...")
    comp_table = page.query_selector("#pricing-comparison-container table")
    results['comparison_table_present'] = comp_table is not None
    if comp_table:
        comp_rows = comp_table.query_selector_all("tbody tr")
        print(f"  Comparison table rendered with {len(comp_rows)} feature rows")
        results['comparison_rows_count'] = len(comp_rows)
    else:
        print("  WARNING: Comparison table not found in container")

    # Check User Quotas Widget
    quota_widget = page.query_selector("#user-quota-widget")
    results['quota_widget_present'] = (quota_widget is not None and len(quota_widget.inner_text().strip()) > 0)
    print(f"  User quota widget present: {results['quota_widget_present']}")

    # Take Desktop Screenshot
    os.makedirs("scratch", exist_ok=True)
    desktop_shot = "scratch/e2e_desktop_pricing.png"
    page.screenshot(path=desktop_shot, full_page=False)
    print(f"  Saved desktop screenshot: {desktop_shot}")

    # Copy to artifacts directory
    artifact_dir = "C:/Users/ashis/.gemini/antigravity/brain/892e2c23-84e8-4698-be4e-67c3418ac8b9"
    os.system(f'copy "{desktop_shot}" "{artifact_dir}\\e2e_desktop_pricing.png" > nul')

    # ─────────────────────────────────────────────────────────────────
    # 2. Mobile Responsive Viewport (375x812 - iPhone X)
    # ─────────────────────────────────────────────────────────────────
    print("\n[4] Testing Mobile Viewport (375x812)...")
    context_mobile = browser.new_context(viewport={"width": 375, "height": 812})
    page_mobile = context_mobile.new_page()
    page_mobile.goto(BASE_URL)
    page_mobile.wait_for_load_state("networkidle")
    page_mobile.evaluate("switchTab('pricing')")
    time.sleep(1)

    mobile_shot = "scratch/e2e_mobile_pricing.png"
    page_mobile.screenshot(path=mobile_shot, full_page=False)
    print(f"  Saved mobile screenshot: {mobile_shot}")
    os.system(f'copy "{mobile_shot}" "{artifact_dir}\\e2e_mobile_pricing.png" > nul')
    results['mobile_layout_rendered'] = True

    context_mobile.close()
    context.close()
    browser.close()

print("\n" + "=" * 70)
print("BROWSER UI VERIFICATION SUMMARY:")
for k, v in results.items():
    print(f"  {k}: {v}")
print("=" * 70)
