from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Company, Job, OpportunityScore, CSRProject, CSROpportunity,
    Contact, NGOCollaboration, PageRecord, AuditTrail, Prospect,
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


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'company', 'department', 'work_mode', 'location', 'link_status')
    search_fields = ('job_title', 'company__company_name', 'skills', 'location')
    list_filter = ('work_mode', 'department', 'link_status', 'status')


@admin.register(OpportunityScore)
class OpportunityScoreAdmin(admin.ModelAdmin):
    list_display = ('company', 'score', 'evidence_status', 'scored_at')
    search_fields = ('company__company_name', 'company__nse_symbol')
    list_filter = ('evidence_status',)


@admin.register(CSRProject)
class CSRProjectAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'company', 'category', 'state', 'confidence', 'link_status')
    search_fields = ('project_name', 'company__company_name', 'category', 'state')
    list_filter = ('category', 'state', 'link_status')


@admin.register(CSROpportunity)
class CSROpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'opportunity_type', 'status', 'submission_deadline')
    search_fields = ('title', 'company__company_name', 'category')
    list_filter = ('status', 'opportunity_type')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'designation', 'email', 'verification_status')
    search_fields = ('name', 'email', 'company__company_name')
    list_filter = ('verification_status',)


@admin.register(NGOCollaboration)
class NGOCollaborationAdmin(admin.ModelAdmin):
    list_display = ('ngo_name', 'company', 'relationship_type', 'location')
    search_fields = ('ngo_name', 'company__company_name')


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = ('company', 'stage', 'assigned_to', 'match_score', 'updated_at')
    search_fields = ('company__company_name', 'notes')
    list_filter = ('stage',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'document_type', 'company', 'status', 'uploaded_at')
    search_fields = ('title', 'company__company_name')
    list_filter = ('document_type', 'status')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscription_id', 'organization_name', 'plan_id', 'status', 'total_paise')
    search_fields = ('subscription_id', 'organization_name', 'contact_email', 'tenant_id')
    list_filter = ('plan_id', 'status')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'percent_off', 'times_redeemed', 'max_redemptions', 'active')
    search_fields = ('code',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'tenant_id', 'total_paise', 'status', 'issued_at')
    search_fields = ('invoice_no', 'tenant_id')
    list_filter = ('status',)


@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ('audit_id', 'record_type', 'record_id', 'action', 'user_role', 'timestamp')
    search_fields = ('record_type', 'record_id', 'action')
    list_filter = ('record_type',)


@admin.register(ServiceCatalog)
class ServiceCatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price_inr', 'is_active')
    list_filter = ('category', 'is_active')
