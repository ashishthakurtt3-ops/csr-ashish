from django.urls import path
from modules.website.views.company_api_views import (
    companies_list_api, company_detail_api, company_dossier_api,
    company_csr_api, company_jobs_api, company_partners_api,
    company_contacts_api, recommendations_api, company_fetch_live_api
)

urlpatterns = [
    path('companies', companies_list_api, name='companies_list'),
    path('companies/', companies_list_api, name='companies_list_slash'),
    path('companies/<str:company_id>', company_detail_api, name='company_detail'),
    path('companies/<str:company_id>/', company_detail_api, name='company_detail_slash'),
    path('companies/<str:company_id>/fetch-live', company_fetch_live_api, name='company_fetch_live'),
    path('companies/<str:company_id>/fetch-live/', company_fetch_live_api, name='company_fetch_live_slash'),
    path('companies/<str:company_id>/dossier', company_dossier_api, name='company_dossier'),
    path('companies/<str:company_id>/dossier/', company_dossier_api, name='company_dossier_slash'),
    path('companies/<str:company_id>/csr', company_csr_api, name='company_csr'),
    path('companies/<str:company_id>/csr/', company_csr_api, name='company_csr_slash'),
    path('companies/<str:company_id>/projects', company_csr_api, name='company_projects'),
    path('companies/<str:company_id>/projects/', company_csr_api, name='company_projects_slash'),
    path('companies/<str:company_id>/jobs', company_jobs_api, name='company_jobs'),
    path('companies/<str:company_id>/jobs/', company_jobs_api, name='company_jobs_slash'),
    path('companies/<str:company_id>/partners', company_partners_api, name='company_partners'),
    path('companies/<str:company_id>/partners/', company_partners_api, name='company_partners_slash'),
    path('companies/<str:company_id>/contacts', company_contacts_api, name='company_contacts'),
    path('companies/<str:company_id>/contacts/', company_contacts_api, name='company_contacts_slash'),
    path('recommendations', recommendations_api, name='recommendations'),
    path('recommendations/', recommendations_api, name='recommendations_slash'),
]
