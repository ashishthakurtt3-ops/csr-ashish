"""
Export companies from database to reports/stage1a_shortcut/companies.csv.
READ-ONLY ORM queries.
"""
import os
import sys
import csv
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from modules.admin_panel.models import Company

out_dir = os.path.abspath(os.path.join("reports", "stage1a_shortcut"))
os.makedirs(out_dir, exist_ok=True)
out_csv = os.path.join(out_dir, "companies.csv")

companies = Company.objects.all().order_by("company_id")
count = companies.count()

with open(out_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["company_id", "name", "old_url", "nse_symbol"])
    for c in companies:
        c_name = getattr(c, "company_name", None) or getattr(c, "name", "")
        old_url = c.website_url or ""
        nse_sym = getattr(c, "nse_symbol", "") or ""
        writer.writerow([c.company_id, c_name, old_url, nse_sym])

print(f"Exported {count} companies to {out_csv}")

