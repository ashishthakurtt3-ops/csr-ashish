import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('FORCE_SQLITE', '1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from modules.admin_panel.models import User

u = User.objects.first()
c = Client()
c.force_login(u)

r1 = c.get('/admin-portal/jobs/companies/')
html1 = r1.content.decode('utf-8')
print("Page 1 company-cards:", html1.count('class="company-card"'))

r2 = c.get('/admin-portal/jobs/companies/?page=2')
html2 = r2.content.decode('utf-8')
print("Page 2 company-cards:", html2.count('class="company-card"'))

r_all = c.get('/admin-portal/jobs/companies/?status=all')
html_all = r_all.content.decode('utf-8')
print("All Corporations Page 1 cards:", html_all.count('class="company-card"'))
