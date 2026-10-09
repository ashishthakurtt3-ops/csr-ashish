from django.db import models
from .company import Company
from .evidence import VerifiableModel


class Job(VerifiableModel):
    job_row_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs', db_column='company_id')

    # Core identification
    job_id = models.TextField(blank=True, null=True)
    external_job_id = models.CharField(max_length=120, blank=True, null=True)  # ID on ATS platform
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
    country = models.CharField(max_length=80, default='India')
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

    # Job content — extracted from detail page
    job_description = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    qualifications = models.TextField(blank=True, null=True)
    preferred_qualifications = models.TextField(blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)

    # Work conditions
    travel_required = models.CharField(max_length=120, blank=True, null=True)
    shift = models.CharField(max_length=120, blank=True, null=True)
    work_authorization = models.CharField(max_length=120, blank=True, null=True)

    # Dates — NULL if not published
    posted_date = models.TextField(blank=True, null=True)
    application_deadline = models.TextField(blank=True, null=True)
    closing_date = models.TextField(blank=True, null=True)

    # URLs
    application_url = models.TextField(blank=True, null=True)

    # Status and tracking
    last_checked_date = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='ACTIVE')
    confidence = models.FloatField(default=0.0)
    link_status = models.CharField(max_length=80, blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)
    data_provenance = models.TextField(blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    # Detail page fetch flag
    detail_fetched = models.BooleanField(default=False)
    detail_fetched_at = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-last_checked_date', '-job_row_id']

    def __str__(self):
        return f"{self.job_title} @ {self.company.company_name}"
