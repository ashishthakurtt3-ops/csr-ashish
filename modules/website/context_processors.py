from django.conf import settings
from modules.admin_panel.models import Company, Job, CSROpportunity, CSRProject


def global_settings(request):
    """Global template context variables."""
    return {
        'PLATFORM_NAME': 'ImpactBridge™ CSR & Job Intelligence OS',
        'PLATFORM_VERSION': '2.5.0',
        'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '4.0.1'),
        'DEBUG': settings.DEBUG,
        'CURRENT_YEAR': 2026,
    }
