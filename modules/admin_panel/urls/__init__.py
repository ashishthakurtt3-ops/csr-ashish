from django.urls import path, include
from modules.admin_panel.views.dashboard import admin_dashboard_view
from modules.admin_panel.views.auth import admin_login_view, admin_logout_view
from modules.admin_panel.data_exchange import (
    export_entity_view, import_entity_view, sample_template_view,
    quick_sync_entity_view, sync_all_master_backup_view,
    download_hub_view, download_all_archive_view
)

app_name = 'admin_portal'

urlpatterns = [
    path('', admin_dashboard_view, name='dashboard'),
    path('auth/', include('modules.admin_panel.urls.auth_urls')),
    path('users/', include('modules.admin_panel.urls.user_urls')),
    path('companies/', include('modules.admin_panel.urls.company_urls')),
    path('jobs/', include('modules.admin_panel.urls.job_urls')),
    path('opportunities/', include('modules.admin_panel.urls.opportunity_urls')),
    path('documents/', include('modules.admin_panel.urls.document_urls')),
    path('subscriptions/', include('modules.admin_panel.urls.subscription_urls')),
    path('verification/', include('modules.admin_panel.urls.verification_urls')),
    path('ai-config/', include('modules.admin_panel.urls.ai_config_urls')),

    # Dedicated Downloads Hub Section & Full Master Archive
    path('downloads/', download_hub_view, name='download_hub'),
    path('downloads/all-archive/', download_all_archive_view, name='download_all_archive'),

    # Enterprise Data Exchange (Extract & Import Engine)
    path('exchange/export/<str:entity>/', export_entity_view, name='data_export'),
    path('exchange/import/<str:entity>/', import_entity_view, name='data_import'),
    path('exchange/template/<str:entity>/', sample_template_view, name='data_template'),
    path('exchange/quick-sync/<str:entity>/', quick_sync_entity_view, name='quick_sync'),
    path('exchange/sync-all-master/', sync_all_master_backup_view, name='sync_all_master'),

    # Direct routes
    path('login/', admin_login_view, name='login'),
    path('logout/', admin_logout_view, name='logout'),
]
