from django.urls import path
from modules.admin_panel.views.preview_settings_views import (
    preview_settings_view,
    preview_reset_defaults_api,
    preview_dummy_data_view,
    preview_dummy_upload_api,
    preview_download_template_view,
    preview_dummy_reset_defaults_api,
    preview_dummy_delete_item_api
)

app_name = 'admin_preview_settings'

urlpatterns = [
    path('', preview_settings_view, name='index'),
    path('reset-defaults/', preview_reset_defaults_api, name='reset_defaults'),
    path('dummy-data/', preview_dummy_data_view, name='dummy_data'),
    path('dummy-data/upload/', preview_dummy_upload_api, name='dummy_upload'),
    path('dummy-data/download-template/', preview_download_template_view, name='download_template'),
    path('dummy-data/reset-defaults/', preview_dummy_reset_defaults_api, name='dummy_reset_defaults'),
    path('dummy-data/delete/<str:category>/<str:record_id>/', preview_dummy_delete_item_api, name='dummy_delete_item'),
]
