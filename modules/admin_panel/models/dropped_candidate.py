"""
modules/admin_panel/models/dropped_candidate.py
Tracks all job and CSR candidates that failed validation gates.
Stored separately from Job and CSRProject models for diagnostic audit trails.
"""
from django.db import models
from .company import Company

class DroppedCandidate(models.Model):
    CANDIDATE_TYPES = [
        ('JOB', 'Job Candidate'),
        ('CSR', 'CSR Candidate'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='dropped_candidates')
    candidate_type = models.CharField(max_length=10, choices=CANDIDATE_TYPES)
    title_or_name = models.CharField(max_length=500, blank=True, default='')
    target_url = models.CharField(max_length=1000, blank=True, default='')
    reason = models.TextField()
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_dropped_candidates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'candidate_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.candidate_type}] {self.company.company_name} - {self.title_or_name}: {self.reason}"

