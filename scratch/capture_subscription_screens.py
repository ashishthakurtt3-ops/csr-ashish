import os
import sys
import django
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.filter(is_staff=True).first()

session = SessionStore()
session['_auth_user_id'] = str(admin_user.pk)
session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
session['_auth_user_hash'] = admin_user.get_session_auth_hash()
session.save()
session_key = session.session_key

artifact_dir = r"C:\Users\ashis\.gemini\antigravity\brain\892e2c23-84e8-4698-be4e-67c3418ac8b9"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1400, 'height': 900})
    context.add_cookies([{
        'name': settings.SESSION_COOKIE_NAME,
        'value': session_key,
        'domain': '127.0.0.1',
        'path': '/',
    }])

    page = context.new_page()

    # 1. Subscriptions list
    print("Navigating to /admin-portal/subscriptions/ ...")
    page.goto('http://127.0.0.1:8000/admin-portal/subscriptions/')
    page.wait_for_timeout(1500)
    shot1 = os.path.join(artifact_dir, "admin_subscriptions_cleaned_view.png")
    page.screenshot(path=shot1, full_page=False)
    print(f"Saved {shot1}")

    # 2. Plan form (Edit Free plan)
    print("Navigating to /admin-portal/subscriptions/plans/free/edit/ ...")
    page.goto('http://127.0.0.1:8000/admin-portal/subscriptions/plans/free/edit/')
    page.wait_for_timeout(1500)
    page.evaluate("window.scrollTo(0, 1050)")
    page.wait_for_timeout(600)
    shot2 = os.path.join(artifact_dir, "admin_plan_form_limits_section.png")
    page.screenshot(path=shot2, full_page=False)
    print(f"Saved {shot2}")

    # 3. User Portal Pricing
    print("Navigating to User Portal /?tab=pricing ...")
    page.goto('http://127.0.0.1:8000/?tab=pricing')
    page.wait_for_timeout(2000)
    page.evaluate("window.scrollTo(0, 700)")
    page.wait_for_timeout(600)
    shot3 = os.path.join(artifact_dir, "user_portal_three_tiers_pricing.png")
    page.screenshot(path=shot3, full_page=False)
    print(f"Saved {shot3}")

    browser.close()
    print("All captures finished.")
