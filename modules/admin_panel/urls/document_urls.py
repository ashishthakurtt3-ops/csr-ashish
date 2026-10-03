from django.urls import path
from modules.admin_panel.views.document_views import (
    document_list_view, document_upload_view, document_action_view
)

app_name = 'admin_documents'

urlpatterns = [
    path('', document_list_view, name='list'),
    path('upload/', document_upload_view, name='upload'),
    path('<int:document_id>/action/', document_action_view, name='action'),
]
