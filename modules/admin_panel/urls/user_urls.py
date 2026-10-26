from django.urls import path
from modules.admin_panel.views.user_views import (
    user_list_view, user_create_view, user_edit_view, user_toggle_status_view
)

app_name = 'admin_users'

urlpatterns = [
    path('', user_list_view, name='list'),
    path('create/', user_create_view, name='create'),
    path('<int:user_id>/edit/', user_edit_view, name='edit'),
    path('<int:user_id>/toggle-status/', user_toggle_status_view, name='toggle_status'),
]
