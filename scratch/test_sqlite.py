import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Test with sqlite
os.environ['SQLITE_DB'] = '1'

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
