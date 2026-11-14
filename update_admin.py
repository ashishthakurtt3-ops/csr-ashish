#!/usr/bin/env python
"""
Script to update admin.py with delete functionality for Company.
This script will overwrite the existing admin.py with enhanced delete capabilities.
"""
import os
import sys

# Get the current directory (project root)
project_dir = os.path.dirname(os.path.abspath(__file__))

# Add the project directory to the path
sys.path.insert(0, project_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Now we can read and write files
from pathlib import Path

# Read the existing admin.py
admin_py_path = Path('modules/admin_panel/admin.py')
admin_content = '''
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Company, Job, OpportunityScore, CSRProject, CSROpportunity,
    Contact, NGOCollaboration, PageRecord, AuditTrail, Prospect,
    Plan, PlanEntitlement, Wallet, WalletTransaction, Payment,
    PromoCode, Subscription, SubscriptionEvent, Invoice, UsageCounter,
    Document, ServiceCatalog
)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'organization_name', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Platform Details', {'fields': ('role', 'phone', 'organization_name', 'designation', 'is_verified')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Platform Details', {'fields': ('role', 'phone', 'organization_name', 'designation', 'is_verified')}),
    )

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_id', 'company_name', 'nse_symbol', 'sector', 'crawl_status', 'link_quality')
    search_fields = ('company_id', 'company_name', 'nse_symbol', 'sector', 'isin')
    list_filter = ('sector', 'crawl_status', 'link_quality', 'listed_on_nse')
    actions = ['delete_selected_with_related']

    def delete_model(self, request, obj):
        """Delete company and all related data."""
        # Delete all related records first
        Job.objects.filter(company=obj).delete()
        CSRProject.objects.filter(company=obj).delete()
        CSROpportunity.objects.filter(company=obj).delete()
        Contact.objects.filter(company=obj).delete()
        NGOCollaboration.objects.filter(company=obj).delete()
        Prospect.objects.filter(company=obj).delete()
        Document.objects.filter(company=obj).delete()
        OpportunityScore.objects.filter(company=obj).delete()

        # Delete the company itself
        obj.delete()

        # Add success message
        self.message_user(
            request,
            f"Company '{obj.company_name}' (ID: {obj.company_id}) deleted successfully with all related data"
        )

    def delete_selected_with_related(self, request, queryset):
        """Custom bulk delete action that deletes companies and all related data."""
        deleted_count = 0
        for company in queryset:
            self.delete_model(request, company)
            deleted_count += 1

        self.message_user(
            request,
            f"Successfully deleted {deleted_count} company(ies) and all related data."
        )

    delete_selected_with_related.short_description = "Delete selected companies and all related data"
'''

# Read the original file
if admin_py_path.exists():
    original_content = admin_py_path.read_text()
    print("Original admin.py content:")
    print(original_content[:500])
    print("...")
else:
    original_content = ""
    print("File does not exist yet, will create new one")

# Write the new content
admin_py_path.write_text(admin_content)
print("\nAdmin.py updated successfully!")
print(f"File written to: {admin_py_path}")
