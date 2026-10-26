import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import sys
sys.stdout.reconfigure(encoding='utf-8')
from modules.admin_panel.models import Job

jobs = list(Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED'))
print(f"Total active jobs remaining: {len(jobs)}")

image_asset_suspects = []
for j in jobs:
    t = (j.job_title or '').strip()
    u = (j.application_url or '').lower()
    t_low = t.lower()
    
    is_suspect = False
    reason = ""
    
    # Check Adobe / image / media assets
    if '/adobe/assets/' in u or any(u.endswith(ext) or (ext + '?') in u for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']):
        is_suspect = True
        reason = "Image/asset URL"
    elif any(x in t_low for x in ['alt text', 'banner image', 'image1', 'image2', 'img-', 'career-banner', 'view open positions', 'view link', 'press release', 'inclusion and diversity', 'campus programs', 'find your work family', 'why choose us']):
        is_suspect = True
        reason = f"Image/alt/button title: {t}"
    elif t_low.startswith('image ') or t_low.startswith('img ') or t_low.startswith('icon ') or t_low.startswith('logo '):
        is_suspect = True
        reason = f"Asset title: {t}"
    elif any(u.endswith(ext) for ext in ['.pdf', '.doc', '.docx']) and not any(k in t_low for k in ['manager', 'engineer', 'lead', 'officer', 'specialist', 'associate', 'analyst', 'trainee', 'executive', 'director']):
        is_suspect = True
        reason = f"Doc/PDF non-job: {t}"
        
    if is_suspect:
        image_asset_suspects.append((j, reason))

print(f"Total asset/image/button suspects found: {len(image_asset_suspects)}")
for j, r in image_asset_suspects[:35]:
    print(f" - [{j.company_id}] {j.job_title} | {r} | URL: {j.application_url[:70] if j.application_url else 'None'}")
