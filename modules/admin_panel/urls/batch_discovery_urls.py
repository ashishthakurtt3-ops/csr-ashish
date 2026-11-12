from django.urls import path
from modules.admin_panel.views.batch_discovery_views import (
    batch_discovery_view, parse_file_api, process_company_api,
    download_sample_template_view, ai_status_api
)

app_name = 'admin_ai_discovery'

urlpatterns = [
    path('', batch_discovery_view, name='index'),
    path('ai-status/', ai_status_api, name='ai_status'),
    path('parse-file/', parse_file_api, name='parse_file'),
    path('process-company/', process_company_api, name='process_company'),
    path('sample-template/', download_sample_template_view, name='sample_template'),
]

