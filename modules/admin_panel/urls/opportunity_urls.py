from django.urls import path
from modules.admin_panel.views.opportunity_views import opportunity_list_view, project_list_view

app_name = 'admin_opportunities'

urlpatterns = [
    path('', opportunity_list_view, name='list'),
    path('opportunities/', opportunity_list_view, name='list_alt'),
    path('projects/', project_list_view, name='projects'),
]
