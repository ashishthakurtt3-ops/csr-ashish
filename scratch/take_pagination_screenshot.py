import os
import sys

sys.path.insert(0, r"d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

import django
django.setup()

from modules.admin_panel.models import User
admin_user = User.objects.filter(is_superuser=True).first()

from playwright.sync_api import sync_playwright

output_dir = r"C:\Users\ashis\.gemini\antigravity\brain\892e2c23-84e8-4698-be4e-67c3418ac8b9"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    from django.contrib.sessions.backends.db import SessionStore
    s = SessionStore()
    s['_auth_user_id'] = str(admin_user.pk)
    s['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
    s['_auth_user_hash'] = admin_user.get_session_auth_hash()
    s.save()
    context.add_cookies([{
        'name': 'sessionid',
        'value': s.session_key,
        'domain': '127.0.0.1',
        'path': '/',
        'httpOnly': True,
        'secure': False
    }])

    page.goto("http://127.0.0.1:8000/admin-portal/ai-discovery/")
    page.wait_for_timeout(1000)

    page.evaluate("""() => {
        document.getElementById('live-queue-container').style.display = 'flex';
        const dummyJobs = [];
        for (let i = 1; i <= 142; i++) {
            dummyJobs.push({
                job_title: 'Software Development Engineer ' + (i % 3 === 0 ? 'Lead' : (i % 2 === 0 ? 'Backend' : 'Frontend')) + ' #' + i,
                department: i % 4 === 0 ? 'Payments & UPI' : (i % 3 === 0 ? 'Cloud Engineering' : 'Merchant Solutions'),
                location: i % 2 === 0 ? 'Noida, Uttar Pradesh' : 'Bengaluru, Karnataka',
                work_mode: i % 3 === 0 ? 'Hybrid' : 'On-site',
                experience: (i % 5 + 2) + '+ years',
                salary_range: '₹' + (12 + (i % 20)) + ' - ' + (18 + (i % 25)) + ' LPA',
                application_url: 'https://jobs.lever.co/paytm/job-' + i
            });
        }
        discoveredCompaniesResults = [{
            cardId: 'dossier-test-paytm',
            company_name: 'One97 Communications Ltd (Paytm)',
            company_id: 'COMP_BATCH_PAYTM_4928',
            is_new: false,
            sector: 'Fintech & Digital Payments',
            headquarters: 'Noida, Uttar Pradesh',
            nse_symbol: 'PAYTM',
            website_url: 'https://paytm.com',
            careers_url: 'https://jobs.lever.co/paytm',
            csr_url: 'https://paytm.com/company/sustainability/esg',
            jobs: dummyJobs,
            csr: [],
            jobs_imported: 142,
            csr_imported: 0,
            activeTab: 'jobs',
            jobsPage: 1,
            jobsPageSize: 10,
            jobsSearch: '',
            csrPage: 1,
            csrPageSize: 10,
            csrSearch: '',
            timestamp: new Date()
        }];
        resultsCurrentPage = 1;
        renderDiscoveredResultsList();
    }""")
    page.wait_for_timeout(600)

    # 1. Top of dossier card with search toolbar
    card = page.locator('#dossier-test-paytm')
    card.screenshot(path=os.path.join(output_dir, "ai_discovery_card_full.png"))
    print("Captured ai_discovery_card_full.png")

    # 2. Bottom pagination bar
    bar = page.locator('#dossier-test-paytm .card-pagination-bar')
    bar.screenshot(path=os.path.join(output_dir, "ai_discovery_card_pagination_bar.png"))
    print("Captured ai_discovery_card_pagination_bar.png")

    browser.close()
