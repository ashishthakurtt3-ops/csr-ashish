import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from modules.admin_panel.models import User, Document, AuditTrail, Company, CSRProject

client = Client()

admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.filter(is_staff=True).first()
print(f"Logged in as admin_user: {admin_user}")
client.force_login(admin_user, backend='django.contrib.auth.backends.ModelBackend')

print("\n--- Testing Verification & Document Hub ---")
# 1. Document List
resp = client.get(reverse('admin_documents:list'))
print(f"1. Documents List View: HTTP {resp.status_code}")
assert resp.status_code == 200
html = resp.content.decode('utf-8')
assert 'Statutory Document Filings' in html
assert 'Project Verification Queue' in html
assert 'docHubHeroBanner' in html
assert 'What is this Hub for?' in html
assert 'Ingest &amp; Upload' in html
print("   Document List UI verified: Sub-nav pills, Onboarding Hero, and Guide rendered.")

# 2. Document Upload
dummy_file = SimpleUploadedFile("test_audit_report.txt", b"Mock Section 135 CSR Compliance Report", content_type="text/plain")
resp = client.post(reverse('admin_documents:upload'), {
    'title': 'Test Q3 Statutory Filing',
    'document_type': 'ANNUAL_REPORT',
    'notes': 'Uploaded for compliance verification testing',
    'file': dummy_file
}, follow=True)
print(f"2. Document Upload: HTTP {resp.status_code}")
test_doc = Document.objects.filter(title='Test Q3 Statutory Filing').first()
assert test_doc is not None
print(f"   Created document id={test_doc.document_id}, type={test_doc.document_type}")

# 3. Document Edit View (GET)
edit_url = reverse('admin_documents:edit', args=[test_doc.document_id])
resp = client.get(edit_url)
print(f"3. Document Edit GET: HTTP {resp.status_code}")
assert resp.status_code == 200
edit_html = resp.content.decode('utf-8')
assert 'Edit Document Information' in edit_html
assert 'Replace File (Optional)' in edit_html
assert 'Delete Document' in edit_html

# 4. Document Edit (POST)
resp = client.post(edit_url, {
    'title': 'Updated Q3 Statutory Filing — Section 135',
    'document_type': 'ANNUAL_REPORT',
    'status': 'VERIFIED',
    'notes': 'Verified against MCA Portal submission',
}, follow=True)
print(f"4. Document Edit POST: HTTP {resp.status_code}")
test_doc.refresh_from_db()
assert test_doc.title == 'Updated Q3 Statutory Filing — Section 135'
assert test_doc.status == 'VERIFIED'
print(f"   Document successfully updated: title='{test_doc.title}', status='{test_doc.status}'")

# Verify Audit Trail for EDIT
edit_audit = AuditTrail.objects.filter(record_type='DOCUMENT', record_id=str(test_doc.document_id), action='EDIT').first()
assert edit_audit is not None
print(f"   Audit trail recorded: action={edit_audit.action}, notes='{edit_audit.notes}'")

# 5. Document Delete
delete_url = reverse('admin_documents:delete', args=[test_doc.document_id])
resp = client.post(delete_url, follow=True)
print(f"5. Document Delete POST: HTTP {resp.status_code}")
assert Document.objects.filter(document_id=test_doc.document_id).count() == 0
print("   Document deleted from DB.")
del_audit = AuditTrail.objects.filter(record_type='DOCUMENT', record_id=str(test_doc.document_id), action='DELETE').first()
assert del_audit is not None
print(f"   Audit trail recorded: action={del_audit.action}, notes='{del_audit.notes}'")

# 6. Verification Queue View
resp = client.get(reverse('admin_verification:queue'))
print(f"6. Verification Queue: HTTP {resp.status_code}")
assert resp.status_code == 200
queue_html = resp.content.decode('utf-8')
assert 'Statutory Document Filings' in queue_html
assert 'Project Verification Queue' in queue_html
print("   Verification Queue verified with unified hub sub-nav.")

print("\n--- Testing Unified Jobs Management & Discovery ---")
# 7. Jobs List (Table View)
resp = client.get(reverse('admin_jobs:list') + '?view=table')
print(f"7. Jobs List (view=table): HTTP {resp.status_code}")
assert resp.status_code == 200
table_html = resp.content.decode('utf-8')
assert 'Jobs Catalog &amp; Discovery' in table_html
assert 'Table View' in table_html
assert 'Discovery Cards' in table_html
assert 'admin-table' in table_html
print("   Table view rendered successfully with full switcher and management table.")

# 8. Jobs List (Cards Discovery View)
resp = client.get(reverse('admin_jobs:list') + '?view=cards')
print(f"8. Jobs List (view=cards): HTTP {resp.status_code}")
assert resp.status_code == 200
cards_html = resp.content.decode('utf-8')
assert 'job-card-grid' in cards_html or 'No Job Openings Found' in cards_html
print("   Cards Discovery view rendered successfully with responsive card grid.")

# 9. Find Jobs Backward-Compatible Redirect
resp = client.get(reverse('admin_jobs:find') + '?q=Engineer&location=Mumbai')
print(f"9. Find Jobs Redirect: HTTP {resp.status_code} -> {resp.url}")
assert resp.status_code == 302
assert '/admin-portal/jobs/' in resp.url
assert 'view=cards' in resp.url
assert 'q=Engineer' in resp.url
assert 'location=Mumbai' in resp.url
print("   Redirect preserved all parameters and activated view=cards.")

print("\n=======================================================")
print("ALL VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
print("=======================================================")
