import os, sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor

with open('scripts/hero_job_detail.html', 'r', encoding='utf-8') as f:
    html = f.read()

url = 'https://jobs.heromotocorp.com/job/Raipur-TERRITORY-MANAGER-SALES-CT-492001/1368423366/'
res = UniversalJobDetailExtractor.extract_from_url(url, preloaded_html=html)

print("=== EXTRACTION RESULT ===")
for k, v in res.items():
    if k == 'structured_details':
        print(f"structured_details keys: {list(v.keys())}")
    elif isinstance(v, str) and len(v) > 80:
        print(f"{k}: {v[:80]}... (len {len(v)})")
    else:
        print(f"{k}: {v}")
