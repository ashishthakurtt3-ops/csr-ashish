from django.db import models
from .company import Company


class PageRecord(models.Model):
    page_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='crawled_pages', db_column='company_id')
    url = models.TextField()
    title = models.TextField(blank=True, null=True)
    page_type = models.TextField(blank=True, null=True)
    content_hash = models.TextField(blank=True, null=True)
    last_modified = models.TextField(blank=True, null=True)
    last_crawled = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    relevant_snippet = models.TextField(blank=True, null=True)
    confidence = models.FloatField(default=0.0)

    class Meta:
        db_table = 'pages'
        ordering = ['-page_id']

    def __str__(self):
        return f"{self.title or self.url} ({self.company.company_name})"


class AuditTrail(models.Model):
    audit_id = models.AutoField(primary_key=True)
    record_type = models.TextField()
    record_id = models.TextField(blank=True, null=True)
    action = models.TextField()
    previous_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    user_role = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.TextField()

    class Meta:
        db_table = 'audit_trail'
        ordering = ['-audit_id']

    def __str__(self):
        return f"[{self.timestamp}] {self.record_type} - {self.action}"
