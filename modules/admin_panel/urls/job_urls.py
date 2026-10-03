from django.urls import path
from modules.admin_panel.views.job_views import job_list_view, job_edit_view

app_name = 'admin_jobs'

urlpatterns = [
    path('', job_list_view, name='list'),
    path('<int:job_row_id>/edit/', job_edit_view, name='edit'),
]
