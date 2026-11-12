import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from scratch.test_tatamotors_multihop import find_deep_openings_link_v2
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

hop1 = "https://tatamotors.turbohire.co/careerpage/39ddba0d-55f7-4206-abf0-e6121e93436a"
html2, text2, status2 = BatchDiscoveryService.fetch_rendered_page(hop1)
hop2 = find_deep_openings_link_v2(html2, hop1)
print("Rendered Hop 2 result:", hop2)

