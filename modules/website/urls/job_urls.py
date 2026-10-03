from django.urls import path
from modules.website.views.job_api_views import jobs_list_api, jobs_summary_api

urlpatterns = [
    path('jobs', jobs_list_api, name='jobs_list'),
    path('jobs/', jobs_list_api, name='jobs_list_slash'),
    path('jobs/summary', jobs_summary_api, name='jobs_summary'),
    path('jobs/summary/', jobs_summary_api, name='jobs_summary_slash'),
]
