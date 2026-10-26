from django.urls import path
from modules.admin_panel.views.job_views import (
    job_list_view,
    job_find_view,
    job_company_directory_view,
    job_company_detail_view,
    job_detail_view,
    job_edit_view,
    job_link_quality_dashboard_view,
    recrawl_company_admin_view,
)

app_name = 'admin_jobs'

urlpatterns = [
    path('', job_list_view, name='list'),
    path('link-quality/', job_link_quality_dashboard_view, name='link_quality'),
    path('find/', job_find_view, name='find'),
    path('companies/', job_company_directory_view, name='companies'),
    path('company/<str:company_id>/', job_company_detail_view, name='company_jobs'),
    path('companies/<str:company_id>/', job_company_detail_view),
    path('recrawl/<str:company_id>/', recrawl_company_admin_view, name='recrawl_company'),
    path('<int:job_row_id>/', job_detail_view, name='detail'),
    path('<int:job_row_id>/edit/', job_edit_view, name='edit'),
]
