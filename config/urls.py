"""
Root URL Configuration for CSR & Job Intelligence Platform.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.staticfiles.views import serve as static_serve
from django.views.static import serve as media_serve

urlpatterns = [
    # Built-in Django Admin Interface
    path('django-admin/', admin.site.urls),

    # Enterprise admin panel. Sub-sections are included by the parent module;
    # do not re-mount them here, otherwise every route is registered twice.
    path('admin-portal/', include('modules.admin_panel.urls')),

    # Only genuinely top-level additions belong here.
    path('admin-portal/ai-discovery/', include('modules.admin_panel.urls.batch_discovery_urls')),

    # Public Enterprise Website & Core REST APIs
    path('', include('modules.website.urls')),
]

# Dev-only convenience serving. In production, static files are served by
# WhiteNoise (see MIDDLEWARE in settings.py) and media must be fronted by the
# web server; Django must never serve MEDIA_ROOT with DEBUG=False.
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', static_serve, {'insecure': True}),
        re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
