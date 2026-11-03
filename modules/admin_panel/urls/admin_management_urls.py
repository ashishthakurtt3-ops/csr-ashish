from django.urls import path
from modules.admin_panel.views.admin_management_views import (
    admin_list_view, admin_create_view, admin_edit_view,
    admin_toggle_status_view, admin_reset_password_view, admin_detail_api,
    admin_quick_generate_api
)

app_name = 'admin_management'

urlpatterns = [
    path('', admin_list_view, name='list'),
    path('create/', admin_create_view, name='create'),
    path('quick-generate/', admin_quick_generate_api, name='quick_generate'),
    path('<int:admin_id>/edit/', admin_edit_view, name='edit'),
    path('<int:admin_id>/toggle-status/', admin_toggle_status_view, name='toggle_status'),
    path('<int:admin_id>/reset-password/', admin_reset_password_view, name='reset_password'),
    path('<int:admin_id>/detail-api/', admin_detail_api, name='detail_api'),
]

