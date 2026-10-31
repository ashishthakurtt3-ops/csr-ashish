"""
modules/admin_panel/urls/ai_config_urls.py
===========================================
URL routing for the centralized AI Models & API Configuration admin interface and APIs.
Includes provider management, dynamic model catalog, diagnostics, routing, telemetry, and audit logs.
"""

from django.urls import path
from modules.admin_panel.views import ai_config_views

app_name = 'admin_ai_config'

urlpatterns = [
    path('', ai_config_views.ai_config_index_view, name='index'),
    path('settings/save/', ai_config_views.ai_config_save_settings_api, name='save_settings'),
    path('provider/create/', ai_config_views.ai_config_create_provider_api, name='create_provider'),
    path('provider/<str:provider>/save/', ai_config_views.ai_config_save_provider_api, name='save_provider'),
    path('provider/<str:provider>/test/', ai_config_views.ai_config_test_provider_api, name='test_provider'),
    path('provider/<str:provider>/refresh-models/', ai_config_views.ai_config_refresh_models_api, name='refresh_models'),
    path('provider/<str:provider>/delete/', ai_config_views.ai_config_delete_provider_api, name='delete_provider'),
    path('audit-logs/', ai_config_views.ai_config_audit_logs_api, name='audit_logs'),

    # Control Center: Diagnostics, Routing, Batch Testing, Telemetry & Catalog
    path('test-routing/', ai_config_views.ai_config_test_routing_api, name='test_routing'),
    path('test-all/', ai_config_views.ai_config_test_all_api, name='test_all'),
    path('models/catalog/', ai_config_views.ai_config_model_catalog_api, name='model_catalog'),
    path('company/search/', ai_config_views.ai_config_company_search_api, name='company_search'),
    path('company/diagnostic/', ai_config_views.ai_config_company_diagnostic_api, name='company_diagnostic'),
    path('company/history/', ai_config_views.ai_config_company_history_api, name='company_history_all'),
    path('company/<str:company_id>/history/', ai_config_views.ai_config_company_history_api, name='company_history'),
    path('usage/summary/', ai_config_views.ai_config_usage_summary_api, name='usage_summary'),
    path('usage/events/', ai_config_views.ai_config_usage_events_api, name='usage_events'),
]
