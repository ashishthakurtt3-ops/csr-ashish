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
    path('admin-portal/companies/', include('modules.admin_panel.urls.company_urls')),
    path('admin-portal/jobs/', include('modules.admin_panel.urls.job_urls')),
    path('admin-portal/opportunities/', include('modules.admin_panel.urls.opportunity_urls')),
    path('admin-portal/documents/', include('modules.admin_panel.urls.document_urls')),
    path('admin-portal/subscriptions/', include('modules.admin_panel.urls.subscription_urls')),
    path('admin-portal/verification/', include('modules.admin_panel.urls.verification_urls')),
    path('admin-portal/ai-config/', include('modules.admin_panel.urls.ai_config_urls')),

    # Public Enterprise Website & Core REST APIs
    path('', include('modules.website.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
