from django.db import models
from .company import Company


class CompanyCrawlSummary(models.Model):
    """
    One record per crawl run per company. Tracks the per-company outcome of every
    Fetch Live Data execution. Never fabricated — only created by the crawler.
    """
    summary_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='crawl_summaries', db_column='company_id')
    crawl_started_at = models.DateTimeField(auto_now_add=True)
    crawl_finished_at = models.DateTimeField(blank=True, null=True)

    # Career source discovery
    career_url_found = models.TextField(blank=True, null=True)
    ats_platform = models.CharField(max_length=80, blank=True, null=True)
    ats_url = models.TextField(blank=True, null=True)
    extraction_strategy = models.CharField(max_length=100, blank=True, null=True)
    direct_percentage = models.FloatField(default=0.0)

    # Job statistics
    jobs_discovered = models.IntegerField(default=0)   # Found in listing
    jobs_detail_fetched = models.IntegerField(default=0)  # Detail page visited
    jobs_extracted = models.IntegerField(default=0)    # Successfully parsed
    jobs_validated = models.IntegerField(default=0)    # Passed verification
    jobs_published = models.IntegerField(default=0)    # Now ACTIVE in DB
    jobs_updated = models.IntegerField(default=0)      # Re-seen and refreshed
    jobs_expired = models.IntegerField(default=0)      # No longer found
    jobs_rejected = models.IntegerField(default=0)     # Deduped / invalid

    # CSR statistics
    csr_pages_found = models.IntegerField(default=0)
    csr_pdfs_found = models.IntegerField(default=0)
    csr_projects_discovered = models.IntegerField(default=0)
    csr_opportunities_discovered = models.IntegerField(default=0)

    # Contact statistics
    contacts_discovered = models.IntegerField(default=0)

    # Crawl outcome
    crawl_status = models.CharField(max_length=50, default='PENDING')
    # PENDING / CRAWLED / BLOCKED / FAILED / PARTIAL
    error_log = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'company_crawl_summary'
        ordering = ['-summary_id']

    def __str__(self):
        return f"{self.company.company_name} | {self.crawl_status} | {self.crawl_started_at}"


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

    @property
    def http_status(self):
        try:
            return int(self.status) if self.status and self.status.isdigit() else (200 if '200' in str(self.status) else self.status)
        except Exception:
            return self.status

    @property
    def depth(self):
        return 1

    @property
    def crawled_at(self):
        return self.last_crawled

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
