from django.db import models
from .company import Company


class CompanySource(models.Model):
    """
    Normalized Corporate Source Registry.
    Tracks all discovered, classified, and verified corporate URLs (Careers, Jobs, CSR, Reports)
    per company, maintaining immutable discovery provenance and evidence audit history.
    """
    SOURCE_TYPE_CHOICES = [
        ('CAREERS_LANDING', 'Careers Landing Page'),
        ('JOBS_LISTING', 'Active Jobs Listing / Search Portal'),
        ('ATS_PORTAL', 'Direct ATS Enterprise Portal'),
        ('INDIVIDUAL_JOB', 'Individual Job Vacancy Posting'),
        ('JOB_APPLICATION', 'Job Application Submission Gateway'),
        ('HR_PORTAL', 'HR & Employee Policies Information'),
        ('CSR_OVERVIEW', 'Corporate Social Responsibility Overview'),
        ('CSR_PROJECT_DISCLOSURE', 'CSR Project Disclosures & Budget'),
        ('CSR_PARTNERSHIP_RFP', 'CSR Call for Proposals / Grants RFP'),
        ('SUSTAINABILITY_REPORT', 'Sustainability / ESG Report Document'),
        ('ANNUAL_REPORT', 'Statutory Annual Report with CSR Evidence'),
        ('CSR_REPORT', 'Annual Standalone CSR Report'),
        ('OTHER', 'Other Corporate Disclosure'),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ('DISCOVERED', 'Discovered in Crawl'),
        ('PENDING_AI', 'Pending AI Classification'),
        ('CLASSIFIED', 'Classified by AI'),
        ('APPROVED', 'Verified & Approved'),
        ('REVIEW_REQUIRED', 'Requires Manual Review'),
        ('REJECTED', 'Rejected (False Positive / Defect)'),
        ('INACCESSIBLE', 'Inaccessible / HTTP 404 / Blocked'),
        ('SUPERSEDED', 'Superseded by Newer Verified Source'),
    ]

    source_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='source_registry',
        db_column='company_id'
    )
    original_url = models.TextField(help_text="Original discovered link URL")
    final_url = models.TextField(help_text="Canonical/redirected final destination URL")
    source_type = models.CharField(max_length=60, choices=SOURCE_TYPE_CHOICES)
    detailed_classification = models.CharField(max_length=80, blank=True, null=True)
    discovery_method = models.CharField(
        max_length=60,
        default='HOMEPAGE_CRAWL',
        help_text="e.g. HEADER_NAV, FOOTER_NAV, SITEMAP, SUBDOMAIN_PROBE, BODY_CONTENT"
    )
    referring_url = models.TextField(blank=True, null=True)
    link_text = models.CharField(max_length=500, blank=True, null=True)
    verification_status = models.CharField(
        max_length=40,
        choices=VERIFICATION_STATUS_CHOICES,
        default='DISCOVERED'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="True if this source actively synchronizes to the primary Company model URL field"
    )
    confidence = models.FloatField(default=0.0)
    supporting_evidence = models.TextField(blank=True, null=True)
    contradictory_evidence = models.TextField(blank=True, null=True)
    classification_json = models.JSONField(default=dict, blank=True)
    last_verified_at = models.DateTimeField(blank=True, null=True)
    content_hash = models.CharField(max_length=128, blank=True, null=True)
    previous_url = models.TextField(blank=True, null=True)
    superseded_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supersedes'
    )
    review_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'company_source_registry'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['company', 'source_type'], name='idx_compsrc_comp_type'),
            models.Index(fields=['verification_status'], name='idx_compsrc_status'),
            models.Index(fields=['is_primary'], name='idx_compsrc_primary'),
        ]

    def __str__(self):
        return f"{self.company.company_name} | {self.source_type} | {self.verification_status} ({self.final_url[:40]})"
