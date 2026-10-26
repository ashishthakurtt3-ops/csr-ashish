from django.urls import path
from modules.admin_panel.views.auth import admin_login_view, admin_logout_view, admin_profile_view

app_name = 'admin_auth'

urlpatterns = [
    path('login/', admin_login_view, name='login'),
    path('logout/', admin_logout_view, name='logout'),
    path('profile/', admin_profile_view, name='profile'),
]
