import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from modules.admin_panel.models import Job

def run_deep_remediation():
    print("=" * 80)
    print("DEEP REMEDIATION: PURGING EXAM RESULTS, CSS ARTIFACTS, AND OVERSEAS ROLES")
    print("=" * 80)

    # 1. Historical exam/interview result notices & circulars
    RESULT_PHRASES = [
        'results of', 'result of', 'final result', 'detailed result', 'interview schedule',
        'admit card', 'call letter', 'selection list', 'merit list', 'shortlisted candidates',
        'provisional list', 'written test vide advt', 'advt no', 'advt. no', 'advertisement no'
    ]

    # 2. CSS artifacts and layout tokens
    CSS_AND_LAYOUT_TOKENS = {
        'departments', 'otpccenter', 'otcenterrounded', 'otpc', 'otcenter',
        'categories', 'filters', 'sort by', 'cookie settings', 'saved jobs'
    }

    # 3. Foreign / Overseas indicators
    OVERSEAS_TERRITORIES = [
        'latin america', 'gerente de', 'canada', 'quebec', 'montréal', 'montreal',
        'vodafone germany', 'brazil', 'toronto'
    ]

    active_qs = Job.objects.filter(status='ACTIVE')
    print(f"Total active jobs before deep remediation: {active_qs.count()}")

    demoted_results = 0
    demoted_css = 0
    demoted_overseas = 0

    with transaction.atomic():
        for j in active_qs:
            t = (j.job_title or '').strip()
            tl = t.lower()
            loc_l = (j.location or '').strip().lower()

            # Check exam/interview results
            if any(rp in tl for rp in RESULT_PHRASES):
                j.status = 'INACTIVE'
                j.verification_status = 'REJECTED'
                j.verification_reason = f"EXAM_RESULT_NOTICE_DEFECT: '{t}' is an archived examination/interview result circular, not an active open vacancy."
                j.save(update_fields=['status', 'verification_status', 'verification_reason'])
                demoted_results += 1
                continue

            # Check CSS/layout artifacts
            if tl in CSS_AND_LAYOUT_TOKENS or any(tok in tl for tok in ['otpc', 'otcenter']):
                j.status = 'INACTIVE'
                j.verification_status = 'REJECTED'
                j.verification_reason = f"CSS_LAYOUT_DEFECT: '{t}' is an HTML/CSS layout artifact from the career page."
                j.save(update_fields=['status', 'verification_status', 'verification_reason'])
                demoted_css += 1
                continue

            # Check overseas postings
            if any(ot in tl for ot in OVERSEAS_TERRITORIES) or any(ot in loc_l for ot in ['canada', 'toronto', 'quebec', 'montreal', 'brazil']):
                j.status = 'INACTIVE'
                j.verification_status = 'QUARANTINED'
                j.verification_reason = f"OVERSEAS_TERRITORY_QUARANTINE: '{t}' is in foreign territory outside Indian operations."
                j.save(update_fields=['status', 'verification_status', 'verification_reason'])
                demoted_overseas += 1
                continue

    print(f"Deep Remediation Summary:")
    print(f"  - Demoted Exam / Interview Result Circulars: {demoted_results}")
    print(f"  - Demoted CSS / Layout Artifacts: {demoted_css}")
    print(f"  - Quarantined Overseas / Non-Indian Postings: {demoted_overseas}")
    print(f"  - Pure Active Job Postings Remaining: {Job.objects.filter(status='ACTIVE').count()}")

if __name__ == '__main__':
    run_deep_remediation()
