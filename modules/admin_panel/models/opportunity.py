from django.db import models
from .company import Company


class OpportunityScore(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, primary_key=True, related_name='score_record', db_column='company_id')
    active_csr = models.FloatField(default=0.0)
    focus_match = models.FloatField(default=0.0)
    recent_activity = models.FloatField(default=0.0)
    ngo_activity = models.FloatField(default=0.0)
    opportunity_page = models.FloatField(default=0.0)
    contact_availability = models.FloatField(default=0.0)
    geographic_match = models.FloatField(default=0.0)
    score = models.FloatField(default=0.0)
    evidence_status = models.TextField(blank=True, null=True)
    rationale = models.TextField(blank=True, null=True)
    scored_at = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f"{self.company.company_name}: {self.score}%"


class CSRProject(models.Model):
    csr_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='csr_projects', db_column='company_id')
    project_name = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    geographic_location = models.TextField(blank=True, null=True)
    state = models.TextField(blank=True, null=True)
    budget = models.TextField(blank=True, null=True)
    source_url = models.TextField(blank=True, null=True)
    discovered_date = models.TextField(blank=True, null=True)
    last_verified_date = models.TextField(blank=True, null=True)
    confidence = models.FloatField(default=0.0)
    link_status = models.TextField(blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    class Meta:
        ordering = ['-confidence', '-csr_id']

    def __str__(self):
        return f"{self.project_name} ({self.company.company_name})"


class CSROpportunity(models.Model):
    opp_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='open_opportunities', db_column='company_id')
    title = models.TextField()
    opportunity_type = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    submission_deadline = models.TextField(blank=True, null=True)
    portal_url = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=40, default='OPEN')
    confidence = models.FloatField(default=0.0)
    link_status = models.TextField(blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    class Meta:
        verbose_name_plural = 'CSR Opportunities'
        ordering = ['-opp_id']

    def __str__(self):
        cname = self.company.company_name if self.company else "General"
        return f"{self.title} ({cname})"
