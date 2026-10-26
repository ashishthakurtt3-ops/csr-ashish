from django.urls import path
from modules.website.views.job_api_views import jobs_list_api, jobs_summary_api, job_detail_api

urlpatterns = [
    path('jobs', jobs_list_api, name='jobs_list'),
    path('jobs/', jobs_list_api, name='jobs_list_slash'),
    path('jobs/summary', jobs_summary_api, name='jobs_summary'),
    path('jobs/summary/', jobs_summary_api, name='jobs_summary_slash'),
    path('jobs/<str:job_id>', job_detail_api, name='job_detail_api'),
    path('jobs/<str:job_id>/', job_detail_api, name='job_detail_api_slash'),
]
