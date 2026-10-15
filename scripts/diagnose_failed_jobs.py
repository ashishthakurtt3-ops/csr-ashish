"""Diagnose the 8 active EXTRACTION_FAILED jobs by testing their actual URLs."""
import os, sys, json, requests
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json,text/html',
}

failed_jobs = Job.objects.filter(status='ACTIVE', detail_fetch_status='EXTRACTION_FAILED').select_related('company')

for j in failed_jobs:
    print(f"\n{'='*80}")
    print(f"JOB: {j.job_id}")
    print(f"  Title: {j.job_title}")
    print(f"  Company: {j.company.company_name}")
    print(f"  ATS: {j.ats_platform}")
    print(f"  App URL: {j.application_url}")
    print(f"  Source URL: {j.source_url}")
    
    # Try fetching the URL directly
    url = j.application_url
    if url:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            print(f"  HTTP Status: {resp.status_code}")
            print(f"  Final URL: {resp.url}")
            content = resp.text[:500]
            print(f"  Content preview: {content[:200]}")
            
            # Check if it's JSON
            if resp.text.strip().startswith('{') or resp.text.strip().startswith('['):
                data = resp.json()
                print(f"  JSON keys: {list(data.keys())[:10]}")
                job_ad = data.get('jobAd', {})
                sections = job_ad.get('sections', {})
                print(f"  jobAd sections: {list(sections.keys())}")
                jd_sec = sections.get('jobDescription', {})
                jd_text = jd_sec.get('text', '')
                print(f"  Has jobDescription text: {bool(jd_text)} (len={len(jd_text)})")
            else:
                print(f"  Content type: HTML/text (not JSON)")
        except Exception as e:
            print(f"  FETCH ERROR: {e}")
    
    # Now test with the UniversalJobDetailExtractor
    print(f"\n  Testing UniversalJobDetailExtractor...")
    result = UniversalJobDetailExtractor.extract_from_url(url)
    print(f"  Extractor status: {result.get('detail_fetch_status')}")
    print(f"  Has description: {bool(result.get('job_description'))}")
    print(f"  Has responsibilities: {bool(result.get('responsibilities'))}")
    print(f"  Has qualifications: {bool(result.get('qualifications'))}")
    print(f"  Location: {result.get('location')}")
    print(f"  Title: {result.get('job_title')}")
