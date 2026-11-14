from django.db import models

from .company import Company


class CSRReport(models.Model):
    """A public CSR / sustainability / annual / BRSR report discovered for a company.

    Reports are kept separate from CSRProject records on purpose: a report is a
    document-level disclosure, while a project is a specific initiative.  Storing
    the document metadata (URL, financial year, summary, topics, evidence) makes
    the discovery traceable without downloading and re-hosting large PDF files.
    """

    REPORT_TYPES = [
        ('CSR', 'CSR Report'),
        ('ANNUAL', 'Annual Report'),
        ('BRSR', 'BRSR / BRSR Core'),
        ('SUSTAINABILITY', 'Sustainability / ESG Report'),
        ('INTEGRATED', 'Integrated Report'),
        ('SECTION_135', 'Section 135 Disclosure'),
        ('OTHER', 'Other Corporate Report'),
    ]

    report_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='csr_reports',
        db_column='company_id',
    )
    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=40, choices=REPORT_TYPES, default='CSR')
    financial_year = models.CharField(max_length=30, blank=True, null=True)
    source_url = models.TextField()
    summary = models.TextField(blank=True, null=True)
    topics = models.JSONField(default=list, blank=True)
    initiatives = models.JSONField(default=list, blank=True)
    key_findings = models.JSONField(default=list, blank=True)
    expenditure = models.TextField(blank=True, null=True)
    beneficiaries = models.TextField(blank=True, null=True)
    geographic_coverage = models.TextField(blank=True, null=True)
    implementing_partners = models.TextField(blank=True, null=True)
    evidence_text = models.TextField(blank=True, null=True)
    content_hash = models.CharField(max_length=128)
    verification_status = models.CharField(max_length=40, default='PUBLISHED')
    retrieved_at = models.DateTimeField(blank=True, null=True)
    first_seen_at = models.DateTimeField(blank=True, null=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-financial_year', '-report_id']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'content_hash'],
                name='uniq_csr_report_company_hash',
            ),
        ]
        indexes = [
            models.Index(fields=['company', 'report_type'], name='idx_csr_rep_cmp_type'),
        ]

    def __str__(self):
        return f"{self.title} ({self.company.company_name})"