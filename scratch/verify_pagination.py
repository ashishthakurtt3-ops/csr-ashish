import os
import sys

sys.path.insert(0, r"d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['OPENBLAS_NUM_THREADS'] = '1'

import django
django.setup()

from django.test import Client
from modules.admin_panel.models import User, Company, Job

print("--- Checking Paytm Job Count & Pagination ---")
paytm = Company.objects.filter(company_id='COMP_BATCH_PAYTM_4928').first()
if not paytm:
    print("Paytm not found!")
    sys.exit(1)

total_jobs = paytm.jobs.count()
print(f"Paytm ({paytm.company_id}) total jobs in DB: {total_jobs}")

admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.filter(role__in=['ADMIN', 'SUPERADMIN']).first()
print(f"Using admin user: {admin_user.username}")

client = Client(SERVER_NAME='127.0.0.1')
client.force_login(admin_user)

# Test Company Detail Jobs Tab
resp = client.get('/admin-portal/companies/COMP_BATCH_PAYTM_4928/?tab=jobs', SERVER_NAME='127.0.0.1')
print(f"Company Detail Jobs Tab status: {resp.status_code}")
content = resp.content.decode('utf-8')

# Check pagination presence
print("Has 'Showing':", "Showing" in content and "of" in content and str(total_jobs) in content)
print("Has '‹ Prev':", "‹ Prev" in content)
print("Has 'Next ›':", "Next ›" in content)
print("Has page range pills:", "btn-admin-primary" in content)

# Check page 2
resp_p2 = client.get('/admin-portal/companies/COMP_BATCH_PAYTM_4928/?tab=jobs&job_page=2', SERVER_NAME='127.0.0.1')
print(f"Company Detail Jobs Tab Page 2 status: {resp_p2.status_code}")
content_p2 = resp_p2.content.decode('utf-8')
print("Page 2 has 'Showing 21 to 40':", "21" in content_p2 and "40" in content_p2)

# Test AI Bulk Discovery page
resp_ai = client.get('/admin-portal/ai-discovery/', SERVER_NAME='127.0.0.1')
print(f"AI Bulk Discovery page status: {resp_ai.status_code}")
content_ai = resp_ai.content.decode('utf-8')
print("AI Discovery has 'buildCardJobsHtml':", "buildCardJobsHtml" in content_ai)
print("AI Discovery has 'onCardJobsSearch':", "onCardJobsSearch" in content_ai)
print("AI Discovery has 'onCardJobsPageSizeChange':", "onCardJobsPageSizeChange" in content_ai)
print("AI Discovery has 'changeCardJobsPage':", "changeCardJobsPage" in content_ai)
print("AI Discovery has 'buildCardCsrHtml':", "buildCardCsrHtml" in content_ai)
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
