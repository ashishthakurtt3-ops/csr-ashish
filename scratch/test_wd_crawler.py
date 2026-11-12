import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.crawler_engine.crawler import try_fetch_workday_json

jobs = try_fetch_workday_json("https://hitachi.wd1.myworkdayjobs.com/en-US/hitachi")
print("Total jobs fetched from Workday:", len(jobs))
for j in jobs[:5]:
    print("Job:", j.get('title'), "| Loc:", j.get('location'), "| URL:", j.get('apply_url'))

