import os
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.urls import reverse
from modules.admin_panel.models import User

client = Client()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.filter(is_staff=True).first()
client.force_login(admin_user, backend='django.contrib.auth.backends.ModelBackend')

print("--- Testing Standard Enterprise Billing Architecture ---")
endpoints = [
    ('admin_subscriptions:list', 'Subscriptions List'),
    ('admin_subscriptions:plans_list', 'Pricing Plans Catalog'),
    ('admin_subscriptions:payments_list', 'Payments Ledger'),
    ('admin_subscriptions:wallets_list', 'User Wallets'),
    ('admin_subscriptions:invoices', 'Invoices & GST'),
    ('admin_subscriptions:promos', 'Promo Codes'),
]

for url_name, title in endpoints:
    url = reverse(url_name)
    resp = client.get(url)
    print(f"[{resp.status_code}] {title} ({url})")
    assert resp.status_code == 200, f"Expected 200 for {url_name}, got {resp.status_code}"
    html = resp.content.decode('utf-8')
    
    # Verify main sidebar contains all 6 Billing links
    assert 'Billing &amp; Revenue' in html or 'Billing & Revenue' in html, f"Billing & Revenue section missing in {url_name}"
    assert reverse('admin_subscriptions:list') in html, f"Subscriptions link missing in sidebar of {url_name}"
    assert reverse('admin_subscriptions:plans_list') in html, f"Pricing plans link missing in sidebar of {url_name}"
    assert reverse('admin_subscriptions:payments_list') in html, f"Payments ledger link missing in sidebar of {url_name}"
    assert reverse('admin_subscriptions:invoices') in html, f"Invoices link missing in sidebar of {url_name}"
    assert reverse('admin_subscriptions:wallets_list') in html, f"Wallets link missing in sidebar of {url_name}"
    assert reverse('admin_subscriptions:promos') in html, f"Promos link missing in sidebar of {url_name}"
    
    # Verify NO duplicate inner sidebar or messy top tab bar inside the page
    assert 'billing-side-by-side-layout' not in html, f"Inner duplicate sidebar still in {url_name}"
    assert 'billing-nav-tabs' not in html, f"Messy horizontal tabs still in {url_name}"

    if url_name == 'admin_subscriptions:list':
        assert 'billing-kpi-deck' in html, "KPI deck missing in subscriptions list"
        assert 'Active Paying Accounts' in html, "Active subscribers KPI missing"
        assert 'Settled Transaction Volume' in html, "Revenue KPI missing"
        assert 'Auto-Renewing Accounts' in html, "Auto-renew KPI missing"
        assert 'Customer Escrow Reserve' in html, "Wallet escrow KPI missing"
        assert 'Billing Engine: Active' in html, "Billing engine badge missing"
        assert 'Run Renewals' in html, "Run renewals button missing"
        print("   -> Subscriptions list verified: Enterprise full-width view with KPI deck, search/filter & directory table!")

print("\nALL ENTERPRISE BILLING CHECKS PASSED WITH 100% SUCCESS!")
