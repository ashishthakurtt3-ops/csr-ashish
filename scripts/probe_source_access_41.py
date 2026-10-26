import urllib.request
import ssl
import socket
import urllib.error
import os, sys, json
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import CompanyCompletenessRegister, Company

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

targets = list(CompanyCompletenessRegister.objects.filter(overall_coverage_status__in=['CRAWL_FAILED', 'BLOCKED', 'SOURCE_UNAVAILABLE']).order_by('company_id_str'))
print(f"Probing {len(targets)} targets...")

results = []
for r in targets:
    url = r.official_website
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)
    outcome = {}
    outcome['id'] = r.company_id_str
    outcome['name'] = r.company_name
    outcome['domain'] = url
    outcome['prev_status'] = r.overall_coverage_status
    outcome['last_successful_fetch'] = str(r.last_successful_fetch_at) if r.last_successful_fetch_at else None
    
    try:
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            code = response.getcode()
            outcome['http_code'] = code
            outcome['retry_outcome'] = 'HTTP_200_SUCCESS' if code == 200 else f'HTTP_{code}'
            outcome['remaining_limitation'] = 'None (Domain accessible on retry)' if code == 200 else f'HTTP status {code}'
    except urllib.error.HTTPError as e:
        outcome['http_code'] = e.code
        outcome['retry_outcome'] = f'HTTP_{e.code}'
        if e.code == 403:
            outcome['remaining_limitation'] = 'Anti-Bot / WAF Protection (HTTP 403 Forbidden - Cloudflare/Akamai/Enterprise Gateway)'
        elif e.code == 404:
            outcome['remaining_limitation'] = 'Resource Not Found (HTTP 404)'
        elif e.code >= 500:
            outcome['remaining_limitation'] = f'Server Error (HTTP {e.code}: {e.reason})'
        else:
            outcome['remaining_limitation'] = f'HTTP {e.code}: {e.reason}'
    except urllib.error.URLError as e:
        outcome['http_code'] = None
        outcome['retry_outcome'] = 'CONNECTION_FAILED'
        outcome['remaining_limitation'] = f'Connection Failed: {e.reason}'
    except socket.timeout:
        outcome['http_code'] = None
        outcome['retry_outcome'] = 'TIMEOUT'
        outcome['remaining_limitation'] = 'Connection timed out (>5000ms) - Target server unresponsive'
    except Exception as e:
        outcome['http_code'] = None
        outcome['retry_outcome'] = 'ERROR'
        outcome['remaining_limitation'] = str(e)
    
    results.append(outcome)
    print(f"[{outcome['id']}] {outcome['prev_status']} => {outcome['retry_outcome']} | {outcome['remaining_limitation'][:60]}")

scratch_dir = os.path.join(BASE_DIR, 'scratch')
os.makedirs(scratch_dir, exist_ok=True)
out_file = os.path.join(scratch_dir, 'source_access_41_retry_results.json')
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f"\nProbing complete. Saved {len(results)} records to {out_file}")
