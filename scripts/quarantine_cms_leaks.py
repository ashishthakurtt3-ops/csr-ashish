import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from modules.admin_panel.models import Job

def quarantine_cms_leaks():
    print("=" * 80)
    print("QUARANTINING SYSTEMIC CMS & MARKETING LEAK DATA")
    print("=" * 80)

    with transaction.atomic():
        # 1. Yes Bank internal CMS pages
        yb_count = Job.objects.filter(
            company_id='COMP_TOP200_119',
            status='ACTIVE'
        ).update(
            status='INACTIVE',
            verification_status='REJECTED',
            verification_reason='CMS_ARTICLE_LEAK: YES Bank CMS nodes (/sites/web/ui/idcs) crawled as job records.'
        )
        print(f"Yes Bank CMS Pages Rejected: {yb_count}")

        # 2. Indian Hotels (Taj) footer & sustainability links
        ihcl_count = Job.objects.filter(
            company_id='COMP_TOP200_085',
            status='ACTIVE'
        ).update(
            status='INACTIVE',
            verification_status='REJECTED',
            verification_reason='FOOTER_POLICY_LINK_LEAK: Indian Hotels corporate portal links crawled as job records.'
        )
        print(f"Indian Hotels Policy Links Rejected: {ihcl_count}")

        # 3. Infosys marketing & partnership pages
        infy_count = Job.objects.filter(
            company_id='COMP_TOP200_010',
            status='ACTIVE'
        ).update(
            status='INACTIVE',
            verification_status='REJECTED',
            verification_reason='MARKETING_PARTNERSHIP_LEAK: Infosys marketing and partnership pages crawled as job records.'
        )
        print(f"Infosys Marketing Pages Rejected: {infy_count}")

        print(f"\nTotal CMS / Marketing rows cleaned: {yb_count + ihcl_count + infy_count}")
        print(f"Genuine Active Jobs Remaining Across Platform: {Job.objects.filter(status='ACTIVE').count()}")

if __name__ == '__main__':
    quarantine_cms_leaks()
