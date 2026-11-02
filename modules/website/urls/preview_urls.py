from django.urls import path
from modules.website.views.preview_api_views import (
    preview_companies_api, preview_jobs_api, preview_csr_api, preview_bundle_api
)

urlpatterns = [
    path('preview/companies', preview_companies_api, name='preview_companies'),
    path('preview/companies/', preview_companies_api, name='preview_companies_slash'),
    path('preview/jobs', preview_jobs_api, name='preview_jobs'),
    path('preview/jobs/', preview_jobs_api, name='preview_jobs_slash'),
    path('preview/csr', preview_csr_api, name='preview_csr'),
    path('preview/csr/', preview_csr_api, name='preview_csr_slash'),
    path('preview/bundle', preview_bundle_api, name='preview_bundle'),
    path('preview/bundle/', preview_bundle_api, name='preview_bundle_slash'),
]

