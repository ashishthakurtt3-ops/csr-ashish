from django.urls import path
from modules.admin_panel.views.company_views import (
    company_list_view,
    company_create_view,
    company_detail_view,
    company_edit_view,
    company_job_create_view,
    company_job_edit_view,
    company_job_toggle_status_view,
    company_csr_create_view,
    company_csr_edit_view,
    company_csr_toggle_status_view,
    company_delete_view,
)
from modules.website.views.company_api_views import company_fetch_live_api

app_name = 'admin_companies'

urlpatterns = [
    # Company Directory & Creation
    path('', company_list_view, name='list'),
    path('create/', company_create_view, name='create'),

    # Company Detail Dossier & Editing
    path('<str:company_id>/', company_detail_view, name='detail'),
    path('<str:company_id>/intelligence/', company_detail_view, name='intelligence'),
    path('<str:company_id>/edit/', company_edit_view, name='edit'),
    path('<str:company_id>/fetch-live/', company_fetch_live_api, name='fetch_live'),

    # Associated Jobs Management
    path('<str:company_id>/jobs/add/', company_job_create_view, name='job_create'),
    path('<str:company_id>/jobs/<int:job_row_id>/edit/', company_job_edit_view, name='job_edit'),
    path('<str:company_id>/jobs/<int:job_row_id>/toggle-status/', company_job_toggle_status_view, name='job_toggle_status'),

    # Associated CSR Projects Management
    path('<str:company_id>/csr/add/', company_csr_create_view, name='csr_create'),
    path('<str:company_id>/csr/<int:csr_id>/edit/', company_csr_edit_view, name='csr_edit'),
    path('<str:company_id>/csr/<int:csr_id>/toggle-status/', company_csr_toggle_status_view, name='csr_toggle_status'),

    # Company Deletion
    path('<str:company_id>/delete/', company_delete_view, name='delete'),
]
