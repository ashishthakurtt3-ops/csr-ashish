"""
Targeted recovery script for Mahindra & Mahindra jobs using the improved CSB extractor.
Enriches descriptions, responsibilities, and qualifications from the official portal.
"""
import os, sys, django, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from django.db.models import Q

# Find all active Mahindra jobs that lack descriptions or responsibilities
target_jobs = Job.objects.filter(
    company__company_id='COMP_TOP200_011',
    status='ACTIVE'
).filter(
    Q(job_description__isnull=True) | Q(job_description='') |
    Q(responsibilities__isnull=True) | Q(responsibilities='')
)

print(f"Total eligible Mahindra jobs to enrich: {target_jobs.count()}")

recovered_desc = 0
recovered_resp = 0
recovered_qual = 0

for j in target_jobs:
    url = j.application_url
    if not url:
        continue
    try:
        res = UniversalJobDetailExtractor.extract_from_url(url)
        updated = False
        
        if res.get('job_description') and (not j.job_description or len(j.job_description) < len(res['job_description'])):
            j.job_description = res['job_description']
            recovered_desc += 1
            updated = True
            
        if res.get('responsibilities') and not j.responsibilities:
            j.responsibilities = res['responsibilities']
            recovered_resp += 1
            updated = True
            
        if res.get('qualifications') and not j.qualifications:
            j.qualifications = res['qualifications']
            recovered_qual += 1
            updated = True
            
        if updated:
            j.save()
            print(f"  Enriched: {j.job_id} | {j.job_title[:35]} | desc_len={len(j.job_description or '')} | resp_len={len(j.responsibilities or '')}")
        else:
            print(f"  Checked (no new fields): {j.job_id} | {j.job_title[:35]}")
            
        time.sleep(0.1)
    except Exception as e:
        print(f"  Error on {j.job_id}: {e}")

print("\n" + "=" * 60)
print(f"MAHINDRA RECOVERY SUMMARY:")
print(f"  Recovered Descriptions:    {recovered_desc}")
print(f"  Recovered Responsibilities: {recovered_resp}")
print(f"  Recovered Qualifications:   {recovered_qual}")
print("=" * 60)
