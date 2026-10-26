from django.urls import path
from modules.admin_panel.views.company_views import (
    company_list_view, company_detail_view, company_edit_view
)
from modules.website.views.company_api_views import company_fetch_live_api

app_name = 'admin_companies'

urlpatterns = [
    path('', company_list_view, name='list'),
    path('<str:company_id>/', company_detail_view, name='detail'),
    path('<str:company_id>/intelligence/', company_detail_view, name='intelligence'),
    path('<str:company_id>/edit/', company_edit_view, name='edit'),
    path('<str:company_id>/fetch-live/', company_fetch_live_api, name='fetch_live'),
]
