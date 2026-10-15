"""
Detailed audit of the 128 jobs without stored descriptions.
For each company and job:
1. Fetch the actual application_url and source_url.
2. Inspect the raw HTTP response / API payload.
3. Determine whether the employer actually publishes a full description or only summary metadata.
4. If a description exists, extract and store it.
"""
import os, sys, django, requests, json, urllib.parse, re
from pathlib import Path
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Count, Q

no_desc = Job.objects.filter(
    status='ACTIVE', verification_status='PUBLISHED'
).filter(
    Q(job_description__isnull=True) | Q(job_description='')
).select_related('company').order_by('company__company_id')

print("=" * 80)
print(f"AUDITING {no_desc.count()} JOBS WITHOUT STORED DESCRIPTIONS")
print("=" * 80)

# Group by company
by_comp = {}
for j in no_desc:
    by_comp.setdefault(j.company, []).append(j)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'application/json,text/html,application/xhtml+xml',
}

recovery_candidates = []
confirmed_omitted = []
inaccessible = []

for comp, jobs in by_comp.items():
    print(f"\n{'='*60}")
    print(f"COMPANY: {comp.company_name} ({comp.company_id}) | Count: {len(jobs)}")
    print(f"{'='*60}")
    
    # Test first 2 jobs of this company
    for j in jobs[:2]:
        print(f"\n--- Checking Job: {j.job_id} ---")
        print(f"  Title: {j.job_title}")
        print(f"  App URL: {j.application_url}")
        print(f"  Source URL: {j.source_url}")
        print(f"  ATS: {j.ats_platform}")
        
        url = j.application_url or j.source_url
        if not url:
            print("  NO URL AVAILABLE!")
            continue
            
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            print(f"  HTTP Status: {resp.status_code}")
            print(f"  Final URL: {resp.url}")
            
            # If Oracle Cloud HCM, also test the REST API
            oc_match = re.search(r'oraclecloud\.com.*?/(?:CandidateExperience|hcmUI/CandidateExperience)/.*?/job/(\d+)', url, re.I)
            if oc_match:
                req_id = oc_match.group(1)
                netloc = urllib.parse.urlparse(url).netloc
                api_url = f"https://{netloc}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?finder=ById;Id={req_id}"
                print(f"  Querying Oracle REST API: {api_url}")
                api_resp = requests.get(api_url, headers=HEADERS, timeout=12)
                print(f"  Oracle API Status: {api_resp.status_code}")
                if api_resp.status_code == 200:
                    api_data = api_resp.json()
                    items = api_data.get('items', [])
                    if items:
                        item = items[0]
                        print(f"  Oracle API keys: {list(item.keys())[:15]}")
                        desc = item.get('ExternalDescriptionStr') or item.get('JobDescription') or item.get('ExternalDescription')
                        print(f"  ExternalDescriptionStr present: {bool(desc)} (len={len(desc) if desc else 0})")
                        if desc:
                            clean_desc = BeautifulSoup(desc, 'html.parser').get_text(separator='\n').strip()
                            print(f"  Clean desc preview: {clean_desc[:150]}")
                        resp_text = item.get('ExternalResponsibilitiesStr') or item.get('Responsibilities')
                        print(f"  ExternalResponsibilitiesStr present: {bool(resp_text)} (len={len(resp_text) if resp_text else 0})")
                        qual_text = item.get('ExternalQualificationsStr') or item.get('Qualifications')
                        print(f"  ExternalQualificationsStr present: {bool(qual_text)} (len={len(qual_text) if qual_text else 0})")
                        
            # If SuccessFactors CSB (e.g. Mahindra), check page content
            elif 'mahindracareers.com' in url or 'successfactors' in url:
                soup = BeautifulSoup(resp.text, 'lxml')
                # Look for CSB description containers
                desc_div = soup.find('div', class_=re.compile(r'jobdescription|job-description|desc', re.I))
                if not desc_div:
                    desc_div = soup.find('span', class_=re.compile(r'jobdescription|job-description', re.I))
                if desc_div:
                    text = desc_div.get_text(separator='\n').strip()
                    print(f"  CSB Description container found: len={len(text)}")
                    print(f"  Preview: {text[:150]}")
                else:
                    print(f"  No explicit CSB description container found. Checking page body text length: {len(soup.get_text())}")
                    # Look for requisition overview text
                    job_layout = soup.find('div', class_='job')
                    if job_layout:
                        print(f"  job div found: len={len(job_layout.get_text())}")
                    
            # If SmartRecruiters (Dr. Reddy's)
            elif 'smartrecruiters.com' in url:
                if resp.text.strip().startswith('{'):
                    data = resp.json()
                    job_ad = data.get('jobAd', {})
                    sections = job_ad.get('sections', {})
                    print(f"  SmartRecruiters jobAd sections: {list(sections.keys())}")
                    for sname, sdata in sections.items():
                        stext = sdata.get('text', '') if isinstance(sdata, dict) else ''
                        print(f"    Section '{sname}': len={len(stext)}")
                        
        except Exception as e:
            print(f"  Error inspecting source: {e}")
