import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.urls import get_resolver

def list_urls(lis, acc=''):
    for p in lis:
        if hasattr(p, 'url_patterns'):
            list_urls(p.url_patterns, acc + str(p.pattern))
        else:
            cb_name = getattr(p.callback, '__name__', str(p.callback))
            cb_mod = getattr(p.callback, '__module__', '')
            name = getattr(p, 'name', '')
            print(f"{acc}{p.pattern} | {cb_mod}.{cb_name} | name={name}")

list_urls(get_resolver().url_patterns)
