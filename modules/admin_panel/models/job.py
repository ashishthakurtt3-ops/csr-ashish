from django.db import models
from .company import Company
from .evidence import VerifiableModel


class Job(VerifiableModel):
    job_row_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs', db_column='company_id')

    # Core identification
    job_id = models.TextField(blank=True, null=True)
    external_job_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)  # ID on ATS platform
    ats_platform = models.CharField(max_length=80, blank=True, null=True)      # Greenhouse / Lever / Workday etc.

    # Job identity
    job_title = models.TextField()
    department = models.TextField(blank=True, null=True)
    team = models.TextField(blank=True, null=True)
    business_unit = models.TextField(blank=True, null=True)
    job_family = models.TextField(blank=True, null=True)
    function = models.TextField(blank=True, null=True)

    # Location
    location = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    # NULL when the source does not state / imply a country (never defaulted to India)
    country = models.CharField(max_length=80, blank=True, null=True)
    work_mode = models.CharField(max_length=80, blank=True, null=True)  # Remote / Hybrid / On-site

    # Employment details
    employment_type = models.CharField(max_length=80, blank=True, null=True)   # Full-time / Part-time / Contract
    experience = models.CharField(max_length=120, blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    skills = models.TextField(blank=True, null=True)

    # Compensation — NULL if not published
    salary = models.CharField(max_length=120, blank=True, null=True)
    salary_min = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    salary_currency = models.CharField(max_length=10, blank=True, null=True)
    pay_band = models.CharField(max_length=120, blank=True, null=True)  # Source pay band/grade e.g. E4 to M2

    # Job content — extracted from detail page
    job_description = models.TextField(blank=True, null=True)
    role_purpose = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)
    day_in_the_life = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True)
    preferred_qualifications = models.TextField(blank=True, null=True)
    technical_skills = models.TextField(blank=True, null=True)
    behavioural_skills = models.TextField(blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)
    employer_info = models.TextField(blank=True, null=True)
    structured_details = models.JSONField(blank=True, null=True)

    # Work conditions
    travel_required = models.CharField(max_length=120, blank=True, null=True)
    shift = models.CharField(max_length=120, blank=True, null=True)
    work_authorization = models.CharField(max_length=120, blank=True, null=True)
    seniority_level = models.CharField(max_length=80, blank=True, null=True, db_index=True)

    # Phase 2 Enhanced Rich Job Details
    description_raw = models.TextField(blank=True, null=True)
    description_html = models.TextField(blank=True, null=True)
    about_role = models.TextField(blank=True, null=True)
    responsibilities_list = models.JSONField(default=list, blank=True, null=True)
    qualifications_education = models.JSONField(default=list, blank=True, null=True)
    qualifications_experience = models.TextField(blank=True, null=True)
    required_skills = models.JSONField(default=list, blank=True, null=True)
    preferred_skills = models.JSONField(default=list, blank=True, null=True)
    salary_text = models.CharField(max_length=120, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)

    # Details extraction status tracking
    DETAILS_STATUS_CHOICES = [
        ('COMPLETE', 'Complete'),
        ('PARTIAL', 'Partial'),
        ('MISSING', 'Missing'),
        ('FAILED', 'Failed'),
    ]
    details_status = models.CharField(max_length=20, choices=DETAILS_STATUS_CHOICES, default='MISSING', db_index=True)
    details_missing_fields = models.JSONField(default=list, blank=True, null=True)
    details_scraped_at = models.DateTimeField(blank=True, null=True)

    # Dates — NULL if not published
    posted_date = models.TextField(blank=True, null=True)
    application_deadline = models.TextField(blank=True, null=True)
    closing_date = models.TextField(blank=True, null=True)

    # URLs
    application_url = models.TextField(blank=True, null=True)
    canonical_url = models.TextField(blank=True, null=True)
    canonical_url_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)

    # Status and tracking
    LINK_QUALITY_CHOICES = [
        ('DIRECT', 'Direct Job URL'),
        ('LISTING_FALLBACK', 'Listing Fallback URL'),
        ('UNVERIFIED', 'Unverified URL'),
    ]
    link_quality = models.CharField(max_length=40, choices=LINK_QUALITY_CHOICES, default='UNVERIFIED')
    link_status = models.CharField(max_length=80, blank=True, null=True)
    link_verified_at = models.DateTimeField(blank=True, null=True)
    link_check_note = models.CharField(max_length=255, blank=True, null=True)
    last_checked_date = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='ACTIVE')
    confidence = models.FloatField(default=0.0)
    data_provenance = models.TextField(blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    # Detail page fetch flag
    detail_fetched = models.BooleanField(default=False)
    detail_fetched_at = models.TextField(blank=True, null=True)
    detail_fetch_status = models.CharField(max_length=50, default='NOT_FETCHED')  # NOT_FETCHED / FETCHED / EXTRACTION_FAILED / SOURCE_UNAVAILABLE

    # Ownership + live link verification (see crawler_engine/ownership.py, link_verifier.py)
    # ats_tenant is filled ONLY when exactly one company owns the posting, so the
    # unique constraint below can never be violated by a posting shared between companies.
    ats_tenant = models.CharField(max_length=255, blank=True, null=True)
    owner_status = models.CharField(max_length=40, blank=True, null=True)   # OWNED / OWNER_UNRESOLVED / OWNER_OTHER_COMPANY / OUT_OF_SCOPE_LOCATION
    link_http_status = models.IntegerField(blank=True, null=True)
    link_check_reason = models.TextField(blank=True, null=True)

    # Live-Sync and Metadata Tracking
    raw_metadata = models.JSONField(default=dict, blank=True)
    last_seen_live_at = models.DateTimeField(blank=True, null=True)
    removed_at = models.DateTimeField(blank=True, null=True)

    # Step 0 Exact-Match Standard: Verbatim Raw Fields & Reconciliation State
    raw_title = models.TextField(blank=True, null=True)
    raw_location = models.TextField(blank=True, null=True)
    raw_department = models.TextField(blank=True, null=True)
    raw_employment_type = models.TextField(blank=True, null=True)
    field_source = models.JSONField(default=dict, blank=True)
    mismatch_reason = models.TextField(blank=True, null=True)
    mismatch_diff = models.JSONField(default=dict, blank=True)
    last_reconciled_at = models.DateTimeField(blank=True, null=True)

    # Snapshot & Performance: Precomputed defect flag & rules version
    is_defective = models.BooleanField(default=False, db_index=True)
    defect_rules_version = models.IntegerField(default=1, db_index=True)

    class Meta:
        ordering = ['-last_checked_date', '-job_row_id']
        constraints = [
            models.UniqueConstraint(fields=['ats_platform', 'ats_tenant', 'external_job_id'],
                                    name='uniq_job_per_ats_tenant'),
            models.UniqueConstraint(fields=['company', 'canonical_url_hash'],
                                    name='uniq_job_company_canonical_hash'),
        ]
        indexes = [
            models.Index(fields=['status', 'is_defective', 'verification_status'], name='idx_job_stat_def_ver'),
            models.Index(fields=['company', 'status', 'is_defective'], name='idx_job_cmp_stat_def'),
            models.Index(fields=['work_mode', 'status', 'is_defective'], name='idx_job_wm_stat_def'),
        ]

    @property
    def summary(self):
        return self.about_role or self.role_purpose or self.job_description

    @summary.setter
    def summary(self, value):
        self.about_role = value

    @property
    def title(self):
        return self.job_title

    @title.setter
    def title(self, value):
        self.job_title = value

    @property
    def apply_url(self):
        return self.application_url

    @apply_url.setter
    def apply_url(self, value):
        self.application_url = value

    @property
    def description(self):
        return self.job_description or self.description_raw

    @description.setter
    def description(self, value):
        self.job_description = value

    def save(self, *args, **kwargs):
        # Synchronize canonical_url and hash
        raw_url = self.application_url or self.canonical_url or self.source_url
        if raw_url and (not self.canonical_url or not self.canonical_url_hash):
            from modules.admin_panel.management.commands.dedupe_jobs import canonicalize_job_url
            import hashlib
            canon = canonicalize_job_url(raw_url)
            self.canonical_url = canon
            # Only DIRECT unique links should enforce unique canonical_url_hash per company
            if getattr(self, 'link_quality', None) == 'DIRECT':
                self.canonical_url_hash = hashlib.sha256(canon.encode('utf-8')).hexdigest() if canon else None
            else:
                self.canonical_url_hash = None

        # Synchronize salary fields
        if self.salary and not self.salary_text:
            self.salary_text = self.salary
        elif self.salary_text and not self.salary:
            self.salary = self.salary_text

        if self.salary_currency and not self.currency:
            self.currency = self.salary_currency
        elif self.currency and not self.salary_currency:
            self.salary_currency = self.currency

        # Automatically evaluate and store defect status
        try:
            from modules.admin_panel.verification import is_defective_job_record
            self.is_defective = is_defective_job_record(self.job_title, self.application_url, self.source_url)
            self.defect_rules_version = 1
        except Exception:
            pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_title} @ {self.company.company_name}"

