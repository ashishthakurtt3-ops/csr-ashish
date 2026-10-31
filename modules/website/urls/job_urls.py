from django.urls import path
from modules.website.views.job_api_views import (
    jobs_list_api, jobs_summary_api, job_detail_api, job_refresh_status_api, jobs_filters_api
)

urlpatterns = [
    path('jobs', jobs_list_api, name='jobs_list'),
    path('jobs/', jobs_list_api, name='jobs_list_slash'),
    path('jobs/summary', jobs_summary_api, name='jobs_summary'),
    path('jobs/summary/', jobs_summary_api, name='jobs_summary_slash'),
    path('jobs/filters', jobs_filters_api, name='jobs_filters'),
    path('jobs/filters/', jobs_filters_api, name='jobs_filters_slash'),
    path('jobs/<str:job_id>/refresh-status', job_refresh_status_api, name='job_refresh_status'),
    path('jobs/<str:job_id>/refresh-status/', job_refresh_status_api, name='job_refresh_status_slash'),
    path('jobs/<str:job_id>', job_detail_api, name='job_detail_api'),
    path('jobs/<str:job_id>/', job_detail_api, name='job_detail_api_slash'),
]
