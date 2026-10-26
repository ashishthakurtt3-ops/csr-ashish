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
    website_url_history = models.JSONField(default=list, blank=True)
    website_url_locked = models.BooleanField(default=False)
    website_url_status = models.CharField(max_length=40, default='UNKNOWN', blank=True, null=True)
    website_url_verified_at = models.DateTimeField(blank=True, null=True)
    website_url_review_notes = models.TextField(blank=True, null=True)
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
    ats_type = models.CharField(max_length=100, blank=True, null=True)
    ats_token = models.CharField(max_length=150, blank=True, null=True)
    extraction_strategy = models.CharField(max_length=100, blank=True, null=True)
    last_strategy_success_rate = models.FloatField(blank=True, null=True)
    sector = models.CharField(max_length=150, blank=True, null=True)
    headquarters = models.CharField(max_length=200, blank=True, null=True)
    cin = models.CharField(max_length=50, blank=True, null=True)
    last_crawled = models.TextField(blank=True, null=True)
    crawl_status = models.CharField(max_length=50, default='PENDING')
    data_confidence = models.FloatField(default=0.0)
    link_quality = models.CharField(max_length=80, blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)

    # Where the company's own website publishes its data. Used by the portal to show
    # "Available only after login on the company website" instead of an empty / guessed value.
    ACCESS_CHOICES = [
        ('UNKNOWN', 'Not yet checked'),
        ('PUBLIC', 'Publicly visible on the company website'),
        ('LOGIN_REQUIRED', 'Visible only after login on the company website'),
        ('NOT_PUBLISHED', 'Not published on the company website'),
    ]
    jobs_access = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='UNKNOWN')
    csr_access = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='UNKNOWN')
    contacts_access = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='UNKNOWN')
    data_access_note = models.TextField(blank=True, null=True)
    data_access_checked_at = models.DateTimeField(blank=True, null=True)

    # Live Sync & Delta Tracking
    SYNC_STATUS_CHOICES = [
        ('IDLE', 'Idle'),
        ('SYNCING', 'Syncing'),
        ('LIVE_VERIFIED', 'Live Verified'),
        ('FAILED', 'Failed'),
    ]
    sync_status = models.CharField(max_length=30, choices=SYNC_STATUS_CHOICES, default='IDLE')
    last_live_synced_at = models.DateTimeField(blank=True, null=True)
    last_sync_error = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['company_name']

    def __str__(self):
        sym = f" ({self.nse_symbol})" if self.nse_symbol else ""
        return f"{self.company_name}{sym}"

    @property
    def id(self):
        return self.company_id

    @property
    def name(self):
        return self.company_name

    @name.setter
    def name(self, value):
        self.company_name = value

    @property
    def domain(self):
        return self.official_domain or (self.website_url.replace('https://', '').replace('http://', '').split('/')[0] if self.website_url else '')

    @property
    def website(self):
        return self.website_url

    @website.setter
    def website(self, value):
        self.website_url = value

    @property
    def csr_url(self):
        return self.csr_portal_url or self.sustainability_url or self.esg_url or self.foundation_url

    @csr_url.setter
    def csr_url(self, value):
        self.csr_portal_url = value

    @property
    def access_status(self):
        return self.jobs_access

    @access_status.setter
    def access_status(self, value):
        self.jobs_access = value

    @property
    def last_crawled_at(self):
        return self.last_live_synced_at

    @last_crawled_at.setter
    def last_crawled_at(self, value):
        self.last_live_synced_at = value

    @property
    def verified_jobs_count(self):
        from modules.admin_panel.verification import public_jobs
        return public_jobs(self.jobs.all()).count()

