from django.db import models
from .company import Company
from .evidence import VerifiableModel

class Contact(VerifiableModel):
    contact_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='contacts', db_column='company_id')
    name = models.TextField(blank=True, null=True)
    designation = models.TextField(blank=True, null=True)
    department = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    confidence = models.FloatField(default=0.0)
    last_verified_date = models.TextField(blank=True, null=True)
    link_status = models.TextField(blank=True, null=True)
    link_verified_at = models.TextField(blank=True, null=True)
    verification_status = models.TextField(blank=True, null=True)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.name or 'CSR Contact'} ({self.company.company_name})"


class NGOCollaboration(VerifiableModel):
    collab_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ngo_collaborations', db_column='company_id')
    ngo_name = models.TextField()
    project_id = models.IntegerField(blank=True, null=True)
    relationship_type = models.TextField(blank=True, null=True)
    location = models.TextField(blank=True, null=True)
    discovered_date = models.TextField(blank=True, null=True)
    confidence = models.FloatField(default=0.0)
    fingerprint = models.CharField(max_length=64, blank=True, null=True, unique=True)

    class Meta:
        verbose_name_plural = 'NGO Collaborations'

    def __str__(self):
        return f"{self.ngo_name} & {self.company.company_name}"
