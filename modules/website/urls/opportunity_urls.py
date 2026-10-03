from django.urls import path
from modules.website.views.opportunity_api_views import csr_projects_api, csr_opportunities_api

urlpatterns = [
    path('csr/projects', csr_projects_api, name='csr_projects'),
    path('csr/projects/', csr_projects_api, name='csr_projects_slash'),
    path('csr/opportunities', csr_opportunities_api, name='csr_opportunities'),
    path('csr/opportunities/', csr_opportunities_api, name='csr_opportunities_slash'),
    path('opportunities', csr_opportunities_api, name='opportunities'),
    path('opportunities/', csr_opportunities_api, name='opportunities_slash'),
]
