import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from collections import Counter
from modules.admin_panel.models import Job

jobs = Job.objects.all()
total = jobs.count()
print(f"Total jobs: {total}")

# 1. Job ID patterns (e.g. REQ-*, etc.)
req_cnt = Job.objects.filter(job_id__startswith='REQ').count()
print(f"Jobs with job_id starting with 'REQ': {req_cnt}")

# 2. Status combinations
combo_counter = Counter()
for s, vs, d, lq in Job.objects.values_list('status', 'verification_status', 'is_defective', 'link_quality'):
    combo_counter[(s, vs, d, lq)] += 1

print("\nTop 15 Status combinations (status, ver_status, is_defective, link_quality):")
for k, v in combo_counter.most_common(15):
    print(f"  {k}: {v}")

# 3. Check for synthetic / fake / test fixtures vs genuine scraped jobs
# Look at data_provenance, source_url, application_url
prov_counter = Counter(Job.objects.values_list('data_provenance', flat=True))
print("\nData Provenance breakdown:")
for k, v in prov_counter.most_common(10):
    print(f"  '{k}': {v}")

# Look at extraction_method
ext_counter = Counter(Job.objects.values_list('extraction_method', flat=True))
print("\nExtraction Method breakdown:")
for k, v in ext_counter.most_common(10):
    print(f"  '{k}': {v}")
