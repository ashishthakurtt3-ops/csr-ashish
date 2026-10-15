from django.db import models
from .evidence import VerifiableModel

class Company(VerifiableModel):
    company_id = models.CharField(max_length=40, primary_key=True)
    company_name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True, null=True)
    isin = models.CharField(max_length=30, blank=True, null=True)
    nse_symbol = models.CharField(max_length=30, blank=True, null=True)
    bse_scrip_code = models.CharField(max_length=30, blank=True, null=True)
    listed_on_nse = models.BooleanField(default=False)
    listed_on_bse = models.BooleanField(default=False)
    listing_status = models.CharField(max_length=40, default='ACTIVE')
    website_url = models.TextField(blank=True, null=True)
    # Discovered official page URLs — never guessed
    official_domain = models.CharField(max_length=255, blank=True, null=True)
    careers_url = models.TextField(blank=True, null=True)
    jobs_page_url = models.TextField(blank=True, null=True)
    csr_portal_url = models.TextField(blank=True, null=True)
    sustainability_url = models.TextField(blank=True, null=True)
    esg_url = models.TextField(blank=True, null=True)
    foundation_url = models.TextField(blank=True, null=True)
    investor_url = models.TextField(blank=True, null=True)
    annual_report_url = models.TextField(blank=True, null=True)
    brsr_url = models.TextField(blank=True, null=True)
    contact_page_url = models.TextField(blank=True, null=True)
    # ATS detection
    ats_platform = models.CharField(max_length=80, blank=True, null=True)
    ats_url = models.TextField(blank=True, null=True)
    sector = models.CharField(max_length=150, blank=True, null=True)
    headquarters = models.CharField(max_length=200, blank=True, null=True)
    cin = models.CharField(max_length=50, blank=True, null=True)
    last_crawled = models.TextField(blank=True, null=True)
    crawl_status = models.CharField(max_length=50, default='PENDING')
    data_confidence = models.FloatField(default=0.0)
    link_quality = models.CharField(max_length=80, blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['company_name']

    def __str__(self):
        sym = f" ({self.nse_symbol})" if self.nse_symbol else ""
        return f"{self.company_name}{sym}"

    @property
    def verified_jobs_count(self):
        return self.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()

