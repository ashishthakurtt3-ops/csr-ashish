from django.urls import path
from modules.website.views.opportunity_api_views import (
    csr_projects_api, 
    csr_opportunities_api,
    csr_project_detail_api,
    csr_filters_api
)

urlpatterns = [
    path('csr', csr_projects_api, name='csr_root'),
    path('csr/', csr_projects_api, name='csr_root_slash'),
    path('csr/projects', csr_projects_api, name='csr_projects'),
    path('csr/projects/', csr_projects_api, name='csr_projects_slash'),
    path('csr/filters', csr_filters_api, name='csr_filters'),
    path('csr/filters/', csr_filters_api, name='csr_filters_slash'),
    path('csr/projects/<str:csr_id>', csr_project_detail_api, name='csr_project_detail'),
    path('csr/projects/<str:csr_id>/', csr_project_detail_api, name='csr_project_detail_slash'),
    path('csr/opportunities', csr_opportunities_api, name='csr_opportunities'),
    path('csr/opportunities/', csr_opportunities_api, name='csr_opportunities_slash'),
    path('opportunities', csr_opportunities_api, name='opportunities'),
    path('opportunities/', csr_opportunities_api, name='opportunities_slash'),
]
