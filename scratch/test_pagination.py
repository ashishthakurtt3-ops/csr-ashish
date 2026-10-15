import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('FORCE_SQLITE', '1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from modules.admin_panel.models import User

u = User.objects.first()
c = Client()
c.force_login(u)

print("Logged in user:", u.username)
r1 = c.get('/admin-portal/jobs/companies/', follow=True)
print("Response status:", r1.status_code, "Final URL:", r1.redirect_chain)
if r1.context:
    page1 = r1.context['page_obj']
    print(f"--- DEFAULT VIEW (Hiring Companies) ---")
    print(f"Page 1 total count in paginator: {page1.paginator.count}")
    print(f"Total pages: {page1.paginator.num_pages}")
    print(f"Companies on Page 1: {len(page1)}")
    for comp in page1:
        print(f"  {comp.company_name}: {comp.job_count} jobs")
else:
    print("No context, redirect occurred to:", r1.url if hasattr(r1, 'url') else 'N/A')

r2 = c.get('/admin-portal/jobs/companies/?page=2')
page2 = r2.context['page_obj']
print(f"\nPage 2 companies count: {len(page2)}")
for comp in page2:
    print(f"  {comp.company_name}: {comp.job_count} jobs")

print(f"Has Page 3? {page2.has_next()}")
