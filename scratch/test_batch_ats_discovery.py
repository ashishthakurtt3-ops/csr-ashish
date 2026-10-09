import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company
from modules.crawler_engine.parsers.ats import ATSParser
from modules.crawler_engine.parsers.generic import GenericHTMLParser
from modules.crawler_engine.crawler import safe_get

comps = Company.objects.exclude(careers_url__isnull=True).exclude(careers_url='').order_by('company_name')[:30]
print(f"Scanning {comps.count()} companies for ATS & Job Discovery...", flush=True)

results = []
for idx, c in enumerate(comps, 1):
    url = c.careers_url or c.website_url
    print(f"[{idx}/{comps.count()}] Checking {c.company_name} ({c.company_id}) -> {url}", flush=True)
    t0 = time.time()
    try:
        resp = safe_get(url)
        elapsed = time.time() - t0
        if not resp:
            print(f"   -> Connect error in {elapsed:.1f}s", flush=True)
            continue
        if not resp.ok:
            print(f"   -> HTTP {resp.status_code} in {elapsed:.1f}s", flush=True)
            continue

        ats = ATSParser(c, url, resp.url, resp.text)
        jobs = ats.extract_jobs()
        ats_platform = ats.discovered_platform
        if not jobs:
            gen = GenericHTMLParser(c, url, resp.url, resp.text)
            jobs = gen.extract_jobs()
            method = gen.get_extraction_method() if jobs else None
        else:
            method = ats.get_extraction_method()

        print(f"   -> OK ({resp.status_code}) in {elapsed:.1f}s | ATS: {ats_platform} | Method: {method} | Jobs Found: {len(jobs)}", flush=True)
        if jobs:
            print(f"      Sample job: {jobs[0].get('title')} ({jobs[0].get('location')})", flush=True)
        results.append({
            'company': c.company_name,
            'ats': ats_platform,
            'jobs': len(jobs)
        })
    except Exception as e:
        print(f"   -> Error: {e}", flush=True)

print(f"\nCompleted scan of {len(results)} companies.", flush=True)
