from django.db import models
from .company import Company


class Job(models.Model):
    job_row_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs', db_column='company_id')
    job_id = models.TextField(blank=True, null=True)
    job_title = models.TextField()
    department = models.TextField(blank=True, null=True)
    function = models.TextField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=80, default='India')
    work_mode = models.CharField(max_length=80, blank=True, null=True)
    employment_type = models.CharField(max_length=80, blank=True, null=True)
    experience = models.CharField(max_length=120, blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    salary = models.CharField(max_length=120, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    posted_date = models.TextField(blank=True, null=True)
    closing_date = models.TextField(blank=True, null=True)
    application_url = models.TextField(blank=True, null=True)
    source_url = models.TextField(blank=True, null=True)
    last_checked_date = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='ACTIVE')
    confidence = models.FloatField(default=0.0)
    link_status = models.CharField(max_length=80, blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)
    data_provenance = models.TextField(blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    class Meta:
        ordering = ['-last_checked_date', '-job_row_id']

    def __str__(self):
        return f"{self.job_title} @ {self.company.company_name}"
