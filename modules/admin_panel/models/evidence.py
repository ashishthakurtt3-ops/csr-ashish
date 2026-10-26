from django.db import models

class VerifiableModel(models.Model):
    VERIFICATION_STATUS_CHOICES = [
        ('UNVERIFIED', 'Unverified'),
        ('DISCOVERED', 'Discovered'),
        ('FETCHED', 'Fetched'),
        ('EXTRACTED', 'Extracted'),
        ('VALIDATED', 'Validated'),
        ('SOURCE_CONFIRMED', 'Source Confirmed'),
        ('STALE', 'Stale'),
        ('NOT_FOUND', 'Not Found'),
        ('REJECTED', 'Rejected'),
        ('FETCH_FAILED', 'Fetch Failed'),
        ('BLOCKED', 'Blocked'),
        ('INVALID_SOURCE', 'Invalid Source'),
        ('LEGACY_UNVERIFIED', 'Legacy Unverified'),
        ('PUBLISHED', 'Published'),
    ]

    verification_status = models.CharField(
        max_length=50, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='UNVERIFIED'
    )
    source_url = models.TextField(blank=True, null=True)
    canonical_url = models.TextField(blank=True, null=True)
    source_domain = models.CharField(max_length=255, blank=True, null=True)
    source_type = models.CharField(max_length=100, blank=True, null=True)
    http_status = models.IntegerField(blank=True, null=True)
    redirect_chain = models.TextField(blank=True, null=True)
    retrieved_at = models.DateTimeField(blank=True, null=True)
    first_seen_at = models.DateTimeField(blank=True, null=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    verification_reason = models.TextField(blank=True, null=True)
    content_hash = models.CharField(max_length=128, blank=True, null=True)
    extraction_method = models.CharField(max_length=100, blank=True, null=True)
    parser_version = models.CharField(max_length=50, blank=True, null=True)
    evidence_text = models.TextField(blank=True, null=True)
    evidence_locator = models.TextField(blank=True, null=True)
    source_snapshot = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.verification_status in ['SOURCE_CONFIRMED', 'PUBLISHED']:
            if not self.source_url:
                raise ValueError("Strict Enforcement: Cannot confirm/publish a record without a source_url.")
            if not self.retrieved_at:
                raise ValueError("Strict Enforcement: Cannot confirm/publish a record without retrieved_at timestamp.")
            if not self.evidence_text and not self.source_snapshot and not self.content_hash:
                raise ValueError("Strict Enforcement: Cannot confirm/publish a record without actual evidence (evidence_text, source_snapshot, or content_hash). HTTP 200 alone is never enough.")
            
            if self.verification_status == 'PUBLISHED':
                orig = self.__class__.objects.filter(pk=self.pk).first() if self.pk else None
                if orig and orig.verification_status not in ['SOURCE_CONFIRMED', 'PUBLISHED', 'DISCOVERED', 'FETCHED', 'EXTRACTED', 'VALIDATED']:
                    raise ValueError(f"Strict Enforcement: State transition to PUBLISHED is only allowed from verified pipeline states. Current state was {orig.verification_status}.")
                
        # Enforce that missing fields are NULL
        if self.source_url == "": self.source_url = None
        if self.canonical_url == "": self.canonical_url = None
        if self.evidence_text == "": self.evidence_text = None
        
        super().save(*args, **kwargs)
