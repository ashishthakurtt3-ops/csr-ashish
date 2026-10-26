from django.db import models
from .company import Company


class CompanyCompletenessRegister(models.Model):
    """
    Mandatory 200-Company Completeness Register.
    Maintains independent collection, audit, and verification states per canonical enterprise
    across all supported intelligence categories (Corporate Identity, Official URLs, Careers/ATS,
    Job Inventory, CSR Initiatives, CSR Financials, Reports & PDFs, BRSR/ESG, Opportunities, Contacts).
    """
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('SOURCES_DISCOVERED', 'Sources Discovered'),
        ('FETCHED', 'Fetched'),
        ('PARTIALLY_PROCESSED', 'Partially Processed'),
        ('VERIFIED', 'Verified'),
        ('NO_RECORDS_CONFIRMED', 'No Records Confirmed'),
        ('SOURCE_UNAVAILABLE', 'Source Unavailable'),
        ('CRAWL_FAILED', 'Crawl Failed'),
        ('BLOCKED', 'Blocked'),
        ('PENDING_VERIFICATION', 'Pending Verification'),
        ('PARTIAL_COVERAGE', 'Partial Coverage'),
    ]

    register_id = models.AutoField(primary_key=True)
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='completeness_register',
        db_column='company_id'
    )
    company_id_str = models.CharField(max_length=40, unique=True, db_index=True)
    company_name = models.CharField(max_length=255)
    official_website = models.TextField(blank=True, null=True)

    # 1. Corporate Identity & Official URLs
    corporate_profile_status = models.CharField(max_length=50, default='VERIFIED')
    official_url_status = models.CharField(max_length=50, default='VERIFIED')

    # 2. Careers & ATS Discovery
    careers_source_status = models.CharField(max_length=50, default='NOT_STARTED')
    ats_platform = models.CharField(max_length=80, blank=True, null=True)
    ats_discovery_status = models.CharField(max_length=50, default='NOT_STARTED')

    # 3. Job Inventory & Details
    jobs_discovered = models.IntegerField(default=0)
    jobs_validated = models.IntegerField(default=0)
    jobs_published = models.IntegerField(default=0)
    jobs_status = models.CharField(max_length=50, default='NOT_STARTED')

    # 4. CSR Initiatives & Financial Disclosures
    csr_source_status = models.CharField(max_length=50, default='NOT_STARTED')
    csr_projects_discovered = models.IntegerField(default=0)
    csr_projects_published = models.IntegerField(default=0)
    csr_projects_status = models.CharField(max_length=50, default='NOT_STARTED')
    csr_financials_status = models.CharField(max_length=50, default='NOT_STARTED')

    # 5. Documents, Annual Reports & ESG Disclosures
    annual_reports_status = models.CharField(max_length=50, default='NOT_STARTED')
    brsr_esg_status = models.CharField(max_length=50, default='NOT_STARTED')
    foundation_status = models.CharField(max_length=50, default='NOT_STARTED')

    # 6. Opportunities & Contacts
    opportunities_discovered = models.IntegerField(default=0)
    opportunities_published = models.IntegerField(default=0)
    opportunities_status = models.CharField(max_length=50, default='NOT_STARTED')
    contacts_discovered = models.IntegerField(default=0)
    contacts_published = models.IntegerField(default=0)
    contacts_status = models.CharField(max_length=50, default='NOT_STARTED')

    # 7. Audit Timestamps & Errors
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    last_successful_fetch_at = models.DateTimeField(blank=True, null=True)
    source_urls_discovered = models.TextField(blank=True, null=True)  # JSON-encoded URL list
    failed_requests_error = models.TextField(blank=True, null=True)
    next_retry_at = models.DateTimeField(blank=True, null=True)

    # 8. Overall Intelligence Coverage Status
    overall_coverage_status = models.CharField(
        max_length=50,
        default='NOT_STARTED'
    )

    class Meta:
        db_table = 'company_completeness_register'
        ordering = ['company_id_str']

    def __str__(self):
        return f"{self.company_id_str} | {self.company_name} | {self.overall_coverage_status}"
