import re

with open('modules/admin_panel/models/subscription.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace tier properties
old_block = """    @property
    def plan_tier(self) -> str:
        \"\"\"Normalized canonical tier code: 'starter', 'pro', 'enterprise', 'foundation'.\"\"\"
        pid = str(self.plan_id or '').strip().lower()
        if pid in ('free', 'starter'):
            return 'starter'
        if pid in ('pro',):
            return 'pro'
        if pid in ('enterprise', 'ultra'):
            return 'enterprise'
        if pid in ('foundation', 'api'):
            return 'foundation'
        return 'starter'

    @property
    def is_free(self) -> bool:
        return self.plan_tier == 'starter'

    @property
    def is_pro(self) -> bool:
        return self.plan_tier == 'pro'

    @property
    def is_enterprise(self) -> bool:
        return self.plan_tier in ('enterprise', 'foundation')

    @property
    def is_ultra(self) -> bool:
        return self.plan_tier in ('enterprise', 'foundation')"""

new_block = """    @property
    def plan_tier(self) -> str:
        \"\"\"Normalized canonical tier code: 'free', 'pro', 'ultra'.\"\"\"
        pid = str(self.plan_id or '').strip().lower()
        if pid in ('free', 'starter'):
            return 'free'
        if pid in ('pro',):
            return 'pro'
        if pid in ('enterprise', 'ultra', 'foundation', 'api'):
            return 'ultra'
        return 'free'

    @property
    def is_free(self) -> bool:
        return self.plan_tier == 'free'

    @property
    def is_pro(self) -> bool:
        return self.plan_tier == 'pro'

    @property
    def is_enterprise(self) -> bool:
        return self.plan_tier == 'ultra'

    @property
    def is_ultra(self) -> bool:
        return self.plan_tier == 'ultra'

    @property
    def max_saved_records(self) -> int | None:
        \"\"\"Max combined saved jobs and CSR projects.\"\"\"
        if self.plan:
            return self.get_limit('saved_records_limit', 10 if self.is_free else (100 if self.is_pro else None))
        return 10 if self.is_free else (100 if self.is_pro else None)

    @property
    def max_saved_searches(self) -> int:
        \"\"\"Max saved search queries (Free: 1, Pro: 10, Ultra: 50).\"\"\"
        if self.plan:
            return int(self.get_limit('saved_searches_limit', 1 if self.is_free else (10 if self.is_pro else 50)))
        return 1 if self.is_free else (10 if self.is_pro else 50)

    @property
    def max_monthly_exports(self) -> int:
        \"\"\"Max records exported per month (Free: 0, Pro: 200, Ultra: 2000).\"\"\"
        if self.plan:
            return int(self.get_limit('export_rows_per_month', 0 if self.is_free else (200 if self.is_pro else 2000)))
        return 0 if self.is_free else (200 if self.is_pro else 2000)

    @property
    def max_team_members(self) -> int:
        \"\"\"Team seats: Free 1, Pro 1, Ultra 3 (including owner).\"\"\"
        if self.plan:
            return int(self.get_limit('seats', 1 if self.is_free or self.is_pro else 3))
        return 1 if self.is_free or self.is_pro else 3

    @property
    def can_use_advanced_filters(self) -> bool:
        \"\"\"Advanced filters: Pro and Ultra only.\"\"\"
        if self.plan:
            return bool(self.has_entitlement('advanced_filters', not self.is_free))
        return not self.is_free

    @property
    def can_request_refresh(self) -> bool:
        \"\"\"On-demand company data refresh: Ultra only.\"\"\"
        if self.plan:
            return bool(self.has_entitlement('request_company_refresh', self.is_ultra))
        return self.is_ultra"""

content_norm = content.replace('\r\n', '\n')
if old_block in content_norm:
    content_norm = content_norm.replace(old_block, new_block, 1)
    print("Replaced subscription properties successfully.")
else:
    print("WARNING: old_block not found in content!")

new_models = """

class SavedRecord(models.Model):
    \"\"\"
    User-saved jobs and CSR projects.
    Quota is strictly enforced on save (10 Free, 100 Pro, Unlimited Ultra).
    Deleting a saved record immediately frees up quota.
    \"\"\"
    TYPE_JOB = 'JOB'
    TYPE_CSR = 'CSR_PROJECT'
    TYPE_CHOICES = (
        (TYPE_JOB, 'Job Opening'),
        (TYPE_CSR, 'CSR Project'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_records')
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    job = models.ForeignKey('Job', on_delete=models.CASCADE, null=True, blank=True, related_name='saved_by_records')
    csr_project = models.ForeignKey('CSRProject', on_delete=models.CASCADE, null=True, blank=True, related_name='saved_by_records')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_records'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} saved {self.item_type}: {self.title}"

    @property
    def title(self) -> str:
        if self.item_type == self.TYPE_JOB and self.job:
            return self.job.job_title
        elif self.item_type == self.TYPE_CSR and self.csr_project:
            return self.csr_project.title
        return 'Saved Item'

    @property
    def company_name(self) -> str:
        if self.item_type == self.TYPE_JOB and self.job and self.job.company:
            return self.job.company.company_name
        elif self.item_type == self.TYPE_CSR and self.csr_project and self.csr_project.company:
            return self.csr_project.company.company_name
        return ''


class SavedSearch(models.Model):
    \"\"\"
    User-saved search queries with automated alert frequencies.
    Limits: Free 1, Pro 10, Ultra 50.
    \"\"\"
    TYPE_JOBS = 'JOBS'
    TYPE_CSR = 'CSR_PROJECTS'
    TYPE_COMPANIES = 'COMPANIES'
    SEARCH_TYPES = (
        (TYPE_JOBS, 'Jobs'),
        (TYPE_CSR, 'CSR Projects'),
        (TYPE_COMPANIES, 'Companies'),
    )

    FREQ_WEEKLY = 'WEEKLY'
    FREQ_DAILY = 'DAILY'
    FREQ_CUSTOM = 'CUSTOM'
    FREQ_CHOICES = (
        (FREQ_WEEKLY, 'Weekly Alerts'),
        (FREQ_DAILY, 'Daily Alerts'),
        (FREQ_CUSTOM, 'Custom / Real-Time Alerts'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=120)
    search_type = models.CharField(max_length=20, default=TYPE_JOBS, choices=SEARCH_TYPES)
    query_params = models.JSONField(default=dict, blank=True)
    alert_frequency = models.CharField(max_length=20, default=FREQ_WEEKLY, choices=FREQ_CHOICES)
    is_active = models.BooleanField(default=True)
    last_alert_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'saved_searches'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} search: {self.name} ({self.alert_frequency})"


class TeamMembership(models.Model):
    \"\"\"
    Multi-user team workspace for Ultra tier (max 3 members total including owner).
    \"\"\"
    ROLE_MEMBER = 'MEMBER'
    ROLE_ANALYST = 'ANALYST'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = (
        (ROLE_MEMBER, 'Team Member'),
        (ROLE_ANALYST, 'Research Analyst'),
        (ROLE_ADMIN, 'Team Administrator'),
    )

    STATUS_INVITED = 'INVITED'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_REVOKED = 'REVOKED'
    STATUS_CHOICES = (
        (STATUS_INVITED, 'Invited'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_REVOKED, 'Revoked'),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_team_memberships')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='team_memberships')
    invited_email = models.EmailField(max_length=190)
    role = models.CharField(max_length=20, default=ROLE_MEMBER, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, default=STATUS_INVITED, choices=STATUS_CHOICES)
    invitation_token = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'team_memberships'
        unique_together = ('owner', 'invited_email')
        ordering = ['-created_at']

    def __str__(self):
        return f"Team of {self.owner.username}: {self.invited_email} [{self.status}]"


class CompanyRefreshRequest(models.Model):
    \"\"\"
    Ultra tier feature: On-demand company data crawl & refresh request.
    \"\"\"
    STATUS_PENDING = 'PENDING'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_IN_PROGRESS, 'Crawl in Progress'),
        (STATUS_COMPLETED, 'Completed & Updated'),
        (STATUS_REJECTED, 'Rejected / Ineligible'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_refresh_requests')
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='refresh_requests')
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=24, default=STATUS_PENDING, choices=STATUS_CHOICES)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'company_refresh_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Refresh req: {self.company.company_name} by {self.user.username} [{self.status}]"
"""

if 'class SavedRecord(models.Model):' not in content_norm:
    content_norm += new_models
    print("Appended new models successfully.")

with open('modules/admin_panel/models/subscription.py', 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Saved modules/admin_panel/models/subscription.py.")

