import os
import sys

# Add the project directory to the path
os.chdir(r'D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)')
sys.path.insert(0, os.getcwd())

# Setup Django
import django
django.setup()

# Import models
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, NGOCollaboration, Prospect, Document

print("=== Company Model Relationships ===")
for field in Company._meta.get_fields():
    if field.is_relation:
        print(f"  {field.name}: FK to {field.remote_field.model.__name__}")
    else:
        print(f"  {field.name}: {type(field).__name__}")

print("\n=== Sample Data Counts ===")
print(f"  Companies: {Company.objects.count()}")
print(f"  Jobs: {Job.objects.count()}")
print(f"  CSR Projects: {CSRProject.objects.count()}")
print(f"  CSR Opportunities: {CSROpportunity.objects.count()}")
print(f"  Contacts: {Contact.objects.count()}")
print(f"  NGOCollaborations: {NGOCollaboration.objects.count()}")
print(f"  Prospects: {Prospect.objects.count()}")
print(f"  Documents: {Document.objects.count()}")

# Check one company and its related data
c = Company.objects.first()
if c:
    print("\n=== Sample Company:", c.company_name, "===")
    print(f"  Jobs: {Job.objects.filter(company=c).count()}")
    print(f"  CSR Projects: {CSRProject.objects.filter(company=c).count()}")
    print(f"  Contacts: {Contact.objects.filter(company=c).count()}")
