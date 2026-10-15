import json
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company

seed_path = os.path.join(BASE_DIR, 'seed_data.json')
with open(seed_path, 'r', encoding='utf-8') as f:
    seed = json.load(f)

db_companies = {c.company_id: c for c in Company.objects.all()}

updated = 0
for obj in seed:
    if obj.get('model') == 'admin_panel.company':
        cid = obj['pk']
        if cid in db_companies:
            db_c = db_companies[cid]
            if obj['fields'].get('cin') != db_c.cin:
                old_val = obj['fields'].get('cin')
                new_val = db_c.cin
                print(f"Updating seed_data {cid}: {old_val} -> {new_val}")
                obj['fields']['cin'] = new_val
                updated += 1

print(f"Total seed_data companies updated: {updated}")
with open(seed_path, 'w', encoding='utf-8') as f:
    json.dump(seed, f, indent=2)
print("Successfully saved synchronized seed_data.json")
