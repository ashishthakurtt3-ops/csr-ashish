import json
from collections import defaultdict

data = json.load(open('seed_data.json', encoding='utf-8'))
print(f"Total entries: {len(data)}")

counts_by_model = defaultdict(int)
for item in data:
    counts_by_model[item['model']] += 1

for model, count in counts_by_model.items():
    print(f"  {model}: {count}")

# Check top 5 companies in seed_data
companies = [item for item in data if item['model'] == 'admin_panel.company']
print(f"\nTotal companies: {len(companies)}")
print("Sample company fields:")
print(companies[0]['pk'], companies[0]['fields'].keys())
print("Company 0:", companies[0]['fields']['company_name'], "NSE:", companies[0]['fields'].get('nse_symbol'), "Sector:", companies[0]['fields'].get('sector'), "HQ:", companies[0]['fields'].get('headquarters'), "CIN:", companies[0]['fields'].get('cin'))

# Check how many companies have nse_symbol, sector, headquarters, cin in seed_data
has_nse = sum(1 for c in companies if c['fields'].get('nse_symbol'))
has_sector = sum(1 for c in companies if c['fields'].get('sector'))
has_hq = sum(1 for c in companies if c['fields'].get('headquarters'))
has_cin = sum(1 for c in companies if c['fields'].get('cin'))
print(f"Companies with NSE symbol: {has_nse}/{len(companies)}")
print(f"Companies with sector: {has_sector}/{len(companies)}")
print(f"Companies with headquarters: {has_hq}/{len(companies)}")
print(f"Companies with CIN: {has_cin}/{len(companies)}")
