from django.db import models
from .company import Company


class AuditRun(models.Model):
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('COMPLETE', 'Complete'),
        ('FAILED', 'Failed'),
        ('SKIPPED_SUSPECT', 'Skipped Suspect'),
    ]

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RUNNING', db_index=True)
    triggered_by = models.CharField(max_length=120, default='SYSTEM')
    notes = models.TextField(blank=True, null=True)
    is_current = models.BooleanField(default=False, db_index=True)
    job_count = models.IntegerField(default=0)
    defect_rules_version = models.IntegerField(default=1)
    validation_report = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['is_current', 'status'], name='idx_auditrun_curr_status'),
            models.Index(fields=['status', '-finished_at'], name='idx_auditrun_stat_fin'),
        ]

    def __str__(self):
        return f"AuditRun #{self.pk} [{self.status}] (current={self.is_current})"


class StatsSnapshot(models.Model):
    audit_run = models.ForeignKey(AuditRun, on_delete=models.CASCADE, related_name='stats_snapshots')
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"StatsSnapshot for AuditRun #{self.audit_run_id}"


class JobSummarySnapshot(models.Model):
    audit_run = models.ForeignKey(AuditRun, on_delete=models.CASCADE, related_name='job_summary_snapshots')
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"JobSummarySnapshot for AuditRun #{self.audit_run_id}"


class CompanyMetrics(models.Model):
    audit_run = models.ForeignKey(AuditRun, on_delete=models.CASCADE, related_name='company_metrics')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='audit_metrics', db_column='company_id')
    active_jobs_count = models.IntegerField(default=0, db_index=True)
    direct_jobs_count = models.IntegerField(default=0, null=True, blank=True)
    jobs_found = models.IntegerField(default=0, null=True, blank=True)
    direct_link_percentage = models.FloatField(default=0.0, null=True, blank=True)
    csr_projects_count = models.IntegerField(default=0, db_index=True)
    open_opps_count = models.IntegerField(default=0, db_index=True)
    contacts_count = models.IntegerField(default=0)
    coverage_score = models.FloatField(default=0.0, db_index=True)
    crawl_status = models.CharField(max_length=64, null=True, blank=True)
    last_verified = models.CharField(max_length=64, null=True, blank=True)
    ats = models.CharField(max_length=128, null=True, blank=True)
    explanation = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-active_jobs_count', '-coverage_score']
        constraints = [
            models.UniqueConstraint(fields=['audit_run', 'company'], name='uniq_comp_metric_run'),
        ]
        indexes = [
            models.Index(fields=['audit_run', '-active_jobs_count', '-coverage_score'], name='idx_cmp_met_run_cnt_cov'),
            models.Index(fields=['company', '-created_at'], name='idx_cmp_met_comp_created'),
        ]

    def __str__(self):
        return f"CompanyMetrics for {self.company_id} [Run #{self.audit_run_id}]"
