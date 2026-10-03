from django.urls import path
from modules.admin_panel.views.company_views import (
    company_list_view, company_detail_view, company_edit_view
)

app_name = 'admin_companies'

urlpatterns = [
    path('', company_list_view, name='list'),
    path('<str:company_id>/', company_detail_view, name='detail'),
    path('<str:company_id>/edit/', company_edit_view, name='edit'),
]
