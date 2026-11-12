"""
modules/admin_panel/models/preview_config.py
============================================
Database models for Centralized Guest Preview & Public Access Configuration.
Empowers administrators to customize:
- Guest preview active status & record count ceiling
- Top preview banner text, badges, and CTA destinations
- Interactive Auth-Gate modal messaging and action buttons
- Bottom unlock banners and messaging
- Curated vs automatic sample record selection strategies
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class GuestPreviewSettings(models.Model):
    """
    Singleton configuration governing what unauthenticated visitors see
    prior to logging in across all public interfaces and REST APIs.
    """
    # 1. Master Toggle & Record Limits
    preview_enabled = models.BooleanField(
        default=True,
        help_text="If enabled, visitors can browse sample preview records. If disabled, visitors are prompted to log in immediately."
    )
    preview_limit = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(25)],
        help_text="Number of preview records displayed to unauthenticated visitors per category (1-25)."
    )

    # 2. Top Guest Banner
    banner_enabled = models.BooleanField(
        default=True,
        help_text="Show or hide the guest notification banner at the top of the portal."
    )
    banner_badge_text = models.CharField(
        max_length=100,
        default="Guest Preview Mode",
        help_text="Tag / badge text displayed in the top banner."
    )
    banner_headline = models.CharField(
        max_length=300,
        default="Viewing {count} sample records from our verified database of {companies} corporations, {jobs} jobs, and {csr} CSR initiatives.",
        help_text="Headline text. Placeholders {count}, {companies}, {jobs}, {csr} are replaced dynamically."
    )
    banner_cta_text = models.CharField(
        max_length=100,
        default="Unlock All Records Free →",
        help_text="Action button text in the top banner."
    )
    banner_cta_url = models.CharField(
        max_length=200,
        default="/register/",
        help_text="Destination URL for the top banner button."
    )

    # 3. Interactive Auth-Gate Modal
    auth_modal_title = models.CharField(
        max_length=200,
        default="Unlock Full Corporate Dossier",
        help_text="Header title on the auth-gate dialog when visitors click details or gated actions."
    )
    auth_modal_description = models.TextField(
        default="Sign in to access comprehensive statutory filings, active vacancies, and CSR allocations.",
        help_text="Body description inside the auth-gate modal."
    )
    auth_modal_primary_btn_text = models.CharField(
        max_length=100,
        default="Create Free Account",
        help_text="Primary button label in the auth modal."
    )
    auth_modal_primary_btn_url = models.CharField(
        max_length=200,
        default="/register/",
        help_text="Destination URL for primary auth button."
    )
    auth_modal_secondary_btn_text = models.CharField(
        max_length=100,
        default="Sign In",
        help_text="Secondary button label in the auth modal."
    )
    auth_modal_secondary_btn_url = models.CharField(
        max_length=200,
        default="/login/",
        help_text="Destination URL for secondary auth button."
    )

    # 4. Bottom Unlock Banner
    bottom_banner_enabled = models.BooleanField(
        default=True,
        help_text="Display unlock card beneath sample records on public listings."
    )
    bottom_banner_title = models.CharField(
        max_length=200,
        default="Viewing {count} of {total} verified corporations",
        help_text="Title for the bottom unlock card. Placeholders {count} and {total} are replaced."
    )
    bottom_banner_description = models.TextField(
        default="Create a free account to unlock all corporate dossiers, active vacancies, and advanced search filters.",
        help_text="Description for bottom unlock card."
    )
    bottom_banner_btn_text = models.CharField(
        max_length=100,
        default="Create Free Account",
        help_text="CTA button text on bottom unlock card."
    )
    bottom_banner_btn_url = models.CharField(
        max_length=200,
        default="/register/",
        help_text="Target URL for bottom unlock card."
    )

    # 5. Content Selection Modes
    COMPANY_SELECTION_CHOICES = [
        ('ALPHABETICAL', 'Alphabetical (A-Z)'),
        ('RECENT', 'Recently Verified / Crawled'),
        ('MANUAL', 'Curated / Hand-Picked (Specify IDs)'),
    ]
    company_selection_mode = models.CharField(
        max_length=30,
        choices=COMPANY_SELECTION_CHOICES,
        default='ALPHABETICAL',
        help_text="Strategy used to pick which companies appear in guest preview."
    )
    featured_company_ids = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated company IDs for Curated mode (e.g. COMP_TOP200_001,COMP_TOP200_005)."
    )

    JOB_SELECTION_CHOICES = [
        ('LATEST', 'Latest Posted Date'),
        ('MANUAL', 'Curated / Hand-Picked (Specify IDs)'),
    ]
    job_selection_mode = models.CharField(
        max_length=30,
        choices=JOB_SELECTION_CHOICES,
        default='LATEST',
        help_text="Strategy used to pick which jobs appear in guest preview."
    )
    featured_job_ids = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated job row IDs for Curated mode."
    )

    CSR_SELECTION_CHOICES = [
        ('LATEST', 'Latest Section 135 Filings'),
        ('MANUAL', 'Curated / Hand-Picked (Specify IDs)'),
    ]
    csr_selection_mode = models.CharField(
        max_length=30,
        choices=CSR_SELECTION_CHOICES,
        default='LATEST',
        help_text="Strategy used to pick which CSR projects appear in guest preview."
    )
    featured_csr_ids = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated CSR project IDs for Curated mode."
    )

    # 6. Audit & History
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='preview_settings_updates'
    )

    class Meta:
        verbose_name = "Guest Preview Settings"
        verbose_name_plural = "Guest Preview Settings"
        db_table = "guest_preview_settings"

    def __str__(self):
        status = "Active" if self.preview_enabled else "Disabled"
        return f"Guest Preview Settings ({status}, Limit={self.preview_limit})"

    @classmethod
    def get_settings(cls):
        """Retrieve the singleton instance or create default record if none exists."""
        obj, created = cls.objects.get_or_create(id=1)
        return obj



class PreviewDummyCompany(models.Model):
    """
    Dedicated Dummy Corporate Entities for Public / Unsubscribed Preview Mode.
    Decoupled from production databases; manageable and uploadable via Excel/CSV.
    """
    company_id = models.CharField(max_length=100, unique=True, help_text="Unique identifier (e.g. DUMMY_COMP_001)")
    company_name = models.CharField(max_length=255, help_text="Corporate entity name")
    nse_symbol = models.CharField(max_length=50, blank=True, null=True, help_text="NSE/BSE stock ticker (optional)")
    sector = models.CharField(max_length=150, blank=True, null=True, help_text="Primary industry / sector")
    headquarters = models.CharField(max_length=200, blank=True, null=True, help_text="HQ city/state")
    website_url = models.CharField(max_length=500, blank=True, null=True, help_text="Official website URL")
    careers_url = models.CharField(max_length=500, blank=True, null=True, help_text="Careers portal link")
    csr_portal_url = models.CharField(max_length=500, blank=True, null=True, help_text="CSR / Sustainability portal link")
    legal_name = models.CharField(max_length=255, blank=True, null=True, help_text="Statutory legal entity name")
    cin = models.CharField(max_length=50, blank=True, null=True, help_text="Corporate Identity Number (CIN)")
    isin = models.CharField(max_length=50, blank=True, null=True, help_text="ISIN security code")
    operating_locations = models.TextField(blank=True, null=True, help_text="Documented operating locations & facilities (semicolon or comma separated)")
    annual_report_url = models.CharField(max_length=500, blank=True, null=True, help_text="Annual report link")
    brsr_url = models.CharField(max_length=500, blank=True, null=True, help_text="SEBI BRSR disclosures link")
    sustainability_url = models.CharField(max_length=500, blank=True, null=True, help_text="Sustainability portal link")
    verification_status = models.CharField(max_length=50, default='VERIFIED')
    job_count = models.IntegerField(default=5, help_text="Simulated active vacancies count")
    csr_count = models.IntegerField(default=3, help_text="Simulated Section 135 CSR projects count")
    is_active = models.BooleanField(default=True, help_text="Enable or disable from appearing in preview")
    display_order = models.IntegerField(default=0, help_text="Sort order priority")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preview_dummy_companies"
        ordering = ['display_order', 'id']
        verbose_name = "Preview Dummy Company"
        verbose_name_plural = "Preview Dummy Companies"

    def __str__(self):
        return f"{self.company_name} ({self.company_id})"

    def as_preview_dict(self):
        domain = ""
        if self.website_url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(self.website_url)
                domain = parsed.netloc.lower().replace('www.', '')
            except Exception:
                domain = ""
        return {
            'company_id': self.company_id,
            'company_name': self.company_name,
            'legal_name': self.legal_name or self.company_name,
            'cin': self.cin or '',
            'isin': self.isin or '',
            'nse_symbol': self.nse_symbol or None,
            'sector': self.sector or 'Corporate Enterprise',
            'headquarters': self.headquarters or 'India',
            'website_url': self.website_url or None,
            'careers_url': self.careers_url or None,
            'csr_portal_url': self.csr_portal_url or None,
            'sustainability_url': self.sustainability_url or self.csr_portal_url or None,
            'annual_report_url': self.annual_report_url or None,
            'brsr_url': self.brsr_url or None,
            'operating_locations': self.operating_locations or '',
            'official_domain': domain,
            'verification_status': self.verification_status or 'VERIFIED',
            'job_count': self.job_count,
            'verified_jobs_count': self.job_count,
            'csr_count': self.csr_count,
            'published_csr_count': self.csr_count,
            'is_preview': True,
        }


class PreviewDummyJob(models.Model):
    """
    Dedicated Dummy Careers / Vacancies for Public / Unsubscribed Preview Mode.
    """
    job_row_id = models.CharField(max_length=100, unique=True, help_text="Unique job identifier (e.g. DUMMY_JOB_101)")
    job_title = models.CharField(max_length=255, help_text="Designation / job title")
    company_name = models.CharField(max_length=255, help_text="Employing corporate entity")
    nse_symbol = models.CharField(max_length=50, blank=True, null=True, help_text="Ticker symbol")
    location = models.CharField(max_length=200, default='Bengaluru, India', help_text="Job location")
    work_mode = models.CharField(max_length=50, default='Hybrid', help_text="Work mode (Remote, Hybrid, On-site)")
    department = models.CharField(max_length=150, default='Technology', help_text="Department / functional team")
    experience = models.CharField(max_length=100, default='3-5 Years', help_text="Experience requirements")
    application_url = models.CharField(max_length=500, blank=True, null=True, help_text="Application / careers link")
    posted_date = models.CharField(max_length=50, blank=True, null=True, default='2026-11-01', help_text="Posting date")
    description = models.TextField(blank=True, null=True, help_text="Full role description and responsibilities")
    skills = models.CharField(max_length=300, blank=True, null=True, help_text="Required technologies and core competencies")
    is_active = models.BooleanField(default=True, help_text="Enable or disable from preview")
    display_order = models.IntegerField(default=0, help_text="Sort order priority")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preview_dummy_jobs"
        ordering = ['display_order', 'id']
        verbose_name = "Preview Dummy Job"
        verbose_name_plural = "Preview Dummy Jobs"

    def __str__(self):
        return f"{self.job_title} @ {self.company_name}"

    def as_preview_dict(self):
        return {
            'job_row_id': self.job_row_id,
            'job_id': self.job_row_id,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'company_id': f"DUMMY_COMP_{self.nse_symbol.upper()}" if self.nse_symbol else 'DUMMY_COMP_001',
            'nse_symbol': self.nse_symbol or None,
            'location': self.location or 'India',
            'work_mode': self.work_mode or 'On-site / Hybrid',
            'department': self.department or 'General',
            'experience': self.experience or 'Not specified',
            'application_url': self.application_url or None,
            'apply_url': self.application_url or None,
            'posted_date': str(self.posted_date) if self.posted_date else '2026-11-01',
            'description': self.description or f"We are seeking an experienced {self.job_title} to join {self.company_name}. This role will lead key initiatives across {self.department}.",
            'skills': self.skills or 'Enterprise Architecture, Agile, Cloud Delivery, Python, SQL',
            'verification_status': 'VERIFIED',
            'is_preview': True,
        }


class PreviewDummyCSRProject(models.Model):
    """
    Dedicated Dummy Section 135 CSR Initiatives for Public / Unsubscribed Preview Mode.
    """
    csr_id = models.CharField(max_length=100, unique=True, help_text="Unique CSR project identifier (e.g. DUMMY_CSR_501)")
    project_name = models.CharField(max_length=255, help_text="Name of the statutory CSR initiative")
    company_name = models.CharField(max_length=255, help_text="Funding corporate enterprise")
    category = models.CharField(max_length=150, default='Education & Skill Development', help_text="Schedule VII thematic pillar")
    state = models.CharField(max_length=150, default='Maharashtra', help_text="Geographical operational state")
    budget = models.CharField(max_length=100, default='₹ 12.50 Cr', help_text="Allocated statutory budget")
    source_url = models.CharField(max_length=500, blank=True, null=True, help_text="Reference filing / PDF link")
    summary = models.TextField(blank=True, null=True, help_text="Full project objective and impact metric")
    target_districts = models.CharField(max_length=300, blank=True, null=True, help_text="Operating districts and aspirational regions")
    implementing_partner = models.CharField(max_length=255, blank=True, null=True, help_text="Registered NGO or direct partner")
    verification_status = models.CharField(max_length=50, default='PUBLISHED')
    is_active = models.BooleanField(default=True, help_text="Enable or disable from preview")
    display_order = models.IntegerField(default=0, help_text="Sort order priority")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preview_dummy_csr_projects"
        ordering = ['display_order', 'id']
        verbose_name = "Preview Dummy CSR Project"
        verbose_name_plural = "Preview Dummy CSR Projects"

    def __str__(self):
        return f"{self.project_name} ({self.company_name})"

    def as_preview_dict(self):
        return {
            'csr_id': self.csr_id,
            'project_name': self.project_name,
            'company_name': self.company_name,
            'company_id': f"DUMMY_COMP_{self.company_name.split()[0].upper()}",
            'sector': self.category or 'Education & Healthcare',
            'category': self.category or 'Education & Healthcare',
            'state': self.state or 'Pan-India',
            'target_districts': self.target_districts or 'Pan-India Aspirational Districts',
            'budget': self.budget or 'Statutory Section 135 Allocation',
            'source_url': self.source_url or None,
            'summary': self.summary or f"Statutory corporate social responsibility initiative under Section 135 of Companies Act, 2013 by {self.company_name}.",
            'implementing_partner': self.implementing_partner or 'Registered Section 8 / NGO Implementing Agency',
            'verification_status': self.verification_status or 'PUBLISHED',
            'is_preview': True,
        }
