#!/usr/bin/env python
"""Debug script to show model relationships for Company."""
import os
import sys
import django

# Setup Django
os.chdir(r"D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)")
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, NGOCollaboration, Prospect, Document

print("=== Company Model Fields ===")
for f in Company._meta.get_fields():
    if f.is_relation:
        print(f"  {f.name}: FK to {f.remote_field.model.__name__ if hasattr(f, 'remote_field') else 'N/A'}")
    else:
        print(f"  {f.name}: {type(f).__name__}")

print("\n=== Sample Relationships ===")
print(f"Company has {Job.objects.filter(company__isnull=False).count()} Job(s)")
print(f"Company has {CSRProject.objects.filter(company__isnull=False).count()} CSRProject(s)")
print(f"Company has {CSROpportunity.objects.filter(company__isnull=False).count()} CSROpportunity(s)")
print(f"Company has {Contact.objects.filter(company__isnull=False).count()} Contact(s)")
print(f"Company has {NGOCollaboration.objects.filter(company__isnull=False).count()} NGOCollaboration(s)")
print(f"Company has {Prospect.objects.filter(company__isnull=False).count()} Prospect(s)")
print(f"Company has {Document.objects.filter(company__isnull=False).count()} Document(s)")

# Show a sample company
sample = Company.objects.first()
if sample:
    print(f"\n=== Sample Company: {sample.company_name} ===")
    print(f"Jobs: {list(Job.objects.filter(company=sample).values_list('job_title', flat=True))}")
    print(f"CSR Projects: {list(CSRProject.objects.filter(company=sample).values_list('project_name', flat=True))}")
    print(f"Contacts: {list(Contact.objects.filter(company=sample).values_list('name', flat=True))}")
