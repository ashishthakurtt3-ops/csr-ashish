"""
modules/admin_panel/urls/ai_config_urls.py
===========================================
URL routing for the centralized AI Models & API Configuration admin interface and APIs.
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
]
