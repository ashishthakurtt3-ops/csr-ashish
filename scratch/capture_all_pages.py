import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\ashis\.gemini\antigravity\brain\892e2c23-84e8-4698-be4e-67c3418ac8b9"

DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
MOBILE_VIEWPORT = {"width": 375, "height": 812}

async def capture_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ---------------------------------------------------------
        # 1. Desktop Context (Login as user to see full authenticated profile)
        # ---------------------------------------------------------
        context = await browser.new_context(viewport=DESKTOP_VIEWPORT)
        page = await context.new_page()

        # Login first so profile / account pages have authenticated state
        await page.goto("http://localhost:8000/login/", wait_until="networkidle")
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_login_desktop.png"))

        await page.fill("input[name='username']", "ngo_manager")
        await page.fill("input[name='password']", "Password123!")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(1000)

        # Now on home page
        await page.goto("http://localhost:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 1. Customer Dashboard (Home tab)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_01_dashboard_desktop.png"))

        # 2. Company Directory (Companies tab)
        await page.evaluate("switchTab('companies')")
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_02_company_directory_desktop.png"))

        # 3. Company Details (Open Company Dossier Modal)
        await page.evaluate("openCompanyDossier('RELIANCE')")
        await page.wait_for_timeout(1200)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_03_company_details_desktop.png"))
        await page.evaluate("closeModal('modal-company-dossier')")
        await page.wait_for_timeout(400)

        # 4. Job Listings (Jobs tab)
        await page.evaluate("switchTab('jobs')")
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_04_jobs_desktop.png"))

        # Job Detail Modal
        first_job = await page.evaluate("""() => {
            const row = document.querySelector('#jobs-table-body tr');
            if (row) {
                const btn = row.querySelector('.btn-primary');
                if (btn) { btn.click(); return true; }
            }
            return false;
        }""")
        if first_job:
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_04b_job_details_modal_desktop.png"))
            await page.evaluate("closeModal('modal-job-details')")
            await page.wait_for_timeout(400)

        # 5. CSR Projects (CSR Projects tab)
        await page.evaluate("switchTab('csr-projects')")
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_05_csr_projects_desktop.png"))

        # CSR Details Modal
        first_csr = await page.evaluate("""() => {
            const btn = document.querySelector('#csr-projects-grid .btn-primary');
            if (btn) { btn.click(); return true; }
            return false;
        }""")
        if first_csr:
            await page.wait_for_timeout(1000)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_05b_csr_details_modal_desktop.png"))
            await page.evaluate("closeModal('modal-csr-details')")
            await page.wait_for_timeout(400)

        # 6. Subscription Pricing (Pricing tab)
        await page.evaluate("switchTab('pricing')")
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_06_pricing_desktop.png"))

        # 7. Feature Comparison (Scroll down to comparison table on pricing tab)
        await page.evaluate("""() => {
            const el = document.getElementById('pricing-comparison-container');
            if (el) el.scrollIntoView({ behavior: 'instant' });
        }""")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_07_comparison_table_desktop.png"))

        # 8. Wallet (Scroll to wallet topup card / open wallet modal)
        await page.evaluate("openWalletTopupModal(1000)")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_08_wallet_modal_desktop.png"))
        await page.evaluate("closeModal('modal-wallet-topup')")
        await page.wait_for_timeout(300)

        # 9. Saved Jobs and CSR Projects / CRM Pipeline (Prospects tab)
        await page.evaluate("switchTab('prospects')")
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_09_saved_records_pipeline_desktop.png"))

        # 10. Saved Searches & Quotas (Scroll to Quota Widget on Pricing)
        await page.evaluate("switchTab('pricing')")
        await page.evaluate("""() => {
            const el = document.getElementById('user-quota-widget');
            if (el) el.scrollIntoView({ behavior: 'instant' });
        }""")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_10_saved_quotas_desktop.png"))

        # 11. Transaction History (Open wallet drawer ledger)
        await page.evaluate("""async () => {
            const el = document.getElementById('portal-wallet-section-card');
            if (el) el.scrollIntoView({ behavior: 'instant' });
            await toggleWalletTxHistory();
        }""")
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_11_transaction_history_desktop.png"))

        # 12. Profile and Account Settings (/profile/)
        await page.goto("http://localhost:8000/profile/", wait_until="networkidle")
        await page.wait_for_timeout(800)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_12_profile_account_desktop.png"))
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_12_profile_account_full_desktop.png"), full_page=True)

        # Also capture Register page
        await page.goto("http://localhost:8000/register/", wait_until="networkidle")
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_register_desktop.png"))

        await context.close()

        # ---------------------------------------------------------
        # 2. Mobile Context (375x812)
        # ---------------------------------------------------------
        m_context = await browser.new_context(viewport=MOBILE_VIEWPORT)
        m_page = await m_context.new_page()

        # Mobile Login
        await m_page.goto("http://localhost:8000/login/", wait_until="networkidle")
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_login_mobile.png"))

        await m_page.fill("input[name='username']", "ngo_manager")
        await m_page.fill("input[name='password']", "Password123!")
        await m_page.click("button[type='submit']")
        await m_page.wait_for_timeout(1000)

        # 1. Customer Dashboard Mobile
        await m_page.goto("http://localhost:8000/", wait_until="networkidle")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_01_dashboard_mobile.png"))

        # Mobile Hamburger Drawer
        await m_page.evaluate("toggleMobileNav()")
        await m_page.wait_for_timeout(500)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_00_mobile_nav_drawer.png"))
        await m_page.evaluate("closeMobileNav()")
        await m_page.wait_for_timeout(300)

        # 2. Company Directory Mobile
        await m_page.evaluate("switchTab('companies')")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_02_company_directory_mobile.png"))

        # 3. Company Details Mobile
        await m_page.evaluate("openCompanyDossier('RELIANCE')")
        await m_page.wait_for_timeout(1200)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_03_company_details_mobile.png"))
        await m_page.evaluate("closeModal('modal-company-dossier')")
        await m_page.wait_for_timeout(300)

        # 4. Job Listings Mobile
        await m_page.evaluate("switchTab('jobs')")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_04_jobs_mobile.png"))

        # 5. CSR Projects Mobile
        await m_page.evaluate("switchTab('csr-projects')")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_05_csr_projects_mobile.png"))

        # 6. Subscription Pricing Mobile
        await m_page.evaluate("switchTab('pricing')")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_06_pricing_mobile.png"))

        # 7. Comparison Table Mobile
        await m_page.evaluate("""() => {
            const el = document.getElementById('pricing-comparison-container');
            if (el) el.scrollIntoView({ behavior: 'instant' });
        }""")
        await m_page.wait_for_timeout(500)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_07_comparison_table_mobile.png"))

        # 8. Wallet Modal Mobile
        await m_page.evaluate("openWalletTopupModal(500)")
        await m_page.wait_for_timeout(500)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_08_wallet_modal_mobile.png"))
        await m_page.evaluate("closeModal('modal-wallet-topup')")
        await m_page.wait_for_timeout(300)

        # 9. Saved Records Mobile (Prospects)
        await m_page.evaluate("switchTab('prospects')")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_09_saved_records_pipeline_mobile.png"))

        # 10. Quotas Mobile
        await m_page.evaluate("switchTab('pricing')")
        await m_page.evaluate("""() => {
            const el = document.getElementById('user-quota-widget');
            if (el) el.scrollIntoView({ behavior: 'instant' });
        }""")
        await m_page.wait_for_timeout(500)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_10_saved_quotas_mobile.png"))

        # 11. Transaction History Mobile
        await m_page.evaluate("""async () => {
            const el = document.getElementById('portal-wallet-section-card');
            if (el) el.scrollIntoView({ behavior: 'instant' });
            await toggleWalletTxHistory();
        }""")
        await m_page.wait_for_timeout(600)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_11_transaction_history_mobile.png"))

        # 12. Profile Mobile
        await m_page.goto("http://localhost:8000/profile/", wait_until="networkidle")
        await m_page.wait_for_timeout(800)
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_12_profile_account_mobile.png"))

        # Mobile Register
        await m_page.goto("http://localhost:8000/register/", wait_until="networkidle")
        await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "page_register_mobile.png"))

        await m_context.close()
        await browser.close()
        print("ALL_PAGES_CAPTURED_SUCCESSFULLY")

if __name__ == '__main__':
    asyncio.run(capture_all())

