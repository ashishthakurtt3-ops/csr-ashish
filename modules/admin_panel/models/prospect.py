from django.db import models
from .company import Company


class Prospect(models.Model):
    prospect_id = models.AutoField(primary_key=True)
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='prospect_entry', db_column='company_id')
    stage = models.CharField(max_length=60, default='Shortlisted')
    notes = models.TextField(blank=True, null=True)
    assigned_to = models.TextField(blank=True, null=True)
    target_proposal = models.TextField(blank=True, null=True)
    follow_up_date = models.TextField(blank=True, null=True)
    match_score = models.FloatField(default=85.0)
    created_at = models.TextField(blank=True, null=True)
    updated_at = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.company.company_name} [{self.stage}]"
