import os

file_path = os.path.join('modules', 'admin_panel', 'models', 'preview_config.py')
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read().replace('\r\n', '\n')

old_comp_dict = """    def as_preview_dict(self):
        return {
            'company_id': self.company_id,
            'company_name': self.company_name,
            'nse_symbol': self.nse_symbol or None,
            'sector': self.sector or 'Corporate Enterprise',
            'headquarters': self.headquarters or 'India',
            'website_url': self.website_url or None,
            'careers_url': self.careers_url or None,
            'csr_portal_url': self.csr_portal_url or None,
            'verification_status': self.verification_status or 'VERIFIED',
            'job_count': self.job_count,
            'csr_count': self.csr_count,
            'is_preview': True,
        }"""

new_comp_dict = """    def as_preview_dict(self):
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
            'csr_count': self.csr_count,
            'is_preview': True,
        }"""

if old_comp_dict in content:
    content = content.replace(old_comp_dict, new_comp_dict)
else:
    print("Warning: old_comp_dict not found")

# Add description & skills to PreviewDummyJob
job_target = """    posted_date = models.CharField(max_length=50, blank=True, null=True, default='2026-11-01', help_text="Posting date")"""
job_replacement = """    posted_date = models.CharField(max_length=50, blank=True, null=True, default='2026-11-01', help_text="Posting date")
    description = models.TextField(blank=True, null=True, help_text="Full role description and responsibilities")
    skills = models.CharField(max_length=300, blank=True, null=True, help_text="Required technologies and core competencies")"""

if job_target in content:
    content = content.replace(job_target, job_replacement)
else:
    print("Warning: job_target not found")

# Update PreviewDummyJob as_preview_dict
old_job_dict = """    def as_preview_dict(self):
        return {
            'job_row_id': self.job_row_id,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'nse_symbol': self.nse_symbol or None,
            'location': self.location or 'India',
            'work_mode': self.work_mode or 'On-site / Hybrid',
            'department': self.department or 'General',
            'experience': self.experience or 'Not specified',
            'application_url': self.application_url or None,
            'posted_date': str(self.posted_date) if self.posted_date else '2026-11-01',
            'is_preview': True,
        }"""

new_job_dict = """    def as_preview_dict(self):
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
        }"""

if old_job_dict in content:
    content = content.replace(old_job_dict, new_job_dict)
else:
    print("Warning: old_job_dict not found")

# Add summary & target_districts to PreviewDummyCSRProject
csr_target = """    source_url = models.CharField(max_length=500, blank=True, null=True, help_text="Reference filing / PDF link")"""
csr_replacement = """    source_url = models.CharField(max_length=500, blank=True, null=True, help_text="Reference filing / PDF link")
    summary = models.TextField(blank=True, null=True, help_text="Full project objective and impact metric")
    target_districts = models.CharField(max_length=300, blank=True, null=True, help_text="Operating districts and aspirational regions")
    implementing_partner = models.CharField(max_length=255, blank=True, null=True, help_text="Registered NGO or direct partner")"""

if csr_target in content:
    content = content.replace(csr_target, csr_replacement)
else:
    print("Warning: csr_target not found")

# Update PreviewDummyCSRProject as_preview_dict
old_csr_dict = """    def as_preview_dict(self):
        return {
            'csr_id': self.csr_id,
            'project_name': self.project_name,
            'company_name': self.company_name,
            'sector': self.category or 'Education & Healthcare',
            'state': self.state or 'Pan-India',
            'budget': self.budget or 'Statutory Section 135 Allocation',
            'source_url': self.source_url or None,
            'verification_status': self.verification_status or 'PUBLISHED',
            'is_preview': True,
        }"""

new_csr_dict = """    def as_preview_dict(self):
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
        }"""

if old_csr_dict in content:
    content = content.replace(old_csr_dict, new_csr_dict)
else:
    print("Warning: old_csr_dict not found")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished updating preview_config.py")

