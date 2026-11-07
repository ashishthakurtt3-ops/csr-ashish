"""
Root URL Configuration for CSR & Job Intelligence Platform.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Built-in Django Admin Interface
    path('django-admin/', admin.site.urls),

    # Custom Enterprise Administrative Panel (Core & Namespaces)
    path('admin-portal/', include('modules.admin_panel.urls')),
    path('admin-portal/users/', include('modules.admin_panel.urls.user_urls')),
    path('admin-portal/admins/', include('modules.admin_panel.urls.admin_management_urls')),
    path('admin-portal/companies/', include('modules.admin_panel.urls.company_urls')),
    path('admin-portal/jobs/', include('modules.admin_panel.urls.job_urls')),
    path('admin-portal/opportunities/', include('modules.admin_panel.urls.opportunity_urls')),
    path('admin-portal/documents/', include('modules.admin_panel.urls.document_urls')),
    path('admin-portal/subscriptions/', include('modules.admin_panel.urls.subscription_urls')),
    path('admin-portal/verification/', include('modules.admin_panel.urls.verification_urls')),
    path('admin-portal/ai-config/', include('modules.admin_panel.urls.ai_config_urls')),
    path('admin-portal/ai-discovery/', include('modules.admin_panel.urls.batch_discovery_urls')),
    path('admin-portal/preview-settings/', include('modules.admin_panel.urls.preview_settings_urls')),

    # Public Enterprise Website & Core REST APIs
    path('', include('modules.website.urls')),
]

from django.urls import re_path
from django.contrib.staticfiles.views import serve as static_serve
from django.views.static import serve as media_serve

# Static & media file serving for local runs (including DEBUG=False)
urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', static_serve, {'insecure': True}),
    re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
]
