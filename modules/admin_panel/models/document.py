from django.db import models
from django.conf import settings
from .company import Company


class Document(models.Model):
    DOC_TYPES = [
        ('CSR_PROPOSAL', 'CSR Grant / Funding Proposal'),
        ('ANNUAL_REPORT', 'Corporate Annual / CSR Report'),
        ('VERIFICATION_PROOF', 'Official Website Domain Proof'),
        ('TAX_EXEMPTION', '12A / 80G / CSR-1 Certificate'),
        ('IDENTITY_PROOF', 'Identity / Organization Registration'),
        ('OTHER', 'Other Documentation'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Verification'),
        ('VERIFIED', 'Verified / Approved'),
        ('REJECTED', 'Rejected'),
    ]

    document_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, choices=DOC_TYPES, default='CSR_PROPOSAL')
    file = models.FileField(upload_to='documents/%Y/%m/')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_documents')
    file_size = models.IntegerField(default=0, help_text="Size in bytes")
    file_format = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
