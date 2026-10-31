import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import inspect
from modules.admin_panel.services import ai_config_service

lines = inspect.getsourcelines(ai_config_service.refresh_provider_models)[0]
print("refresh_provider_models length:", len(lines))
print("First 30 lines:\n" + "".join(lines[:30]))

test_lines = inspect.getsourcelines(ai_config_service.test_provider_live)[0]
print("test_provider_live length:", len(test_lines))
print("First 30 lines:\n" + "".join(test_lines[:30]))
