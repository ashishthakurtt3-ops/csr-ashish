from django.urls import path
from modules.website.views.auth_views import (
    user_login_view, user_register_view, user_logout_view, user_profile_view
)
from modules.website.views.document_views import public_document_upload_view

urlpatterns = [
    path('login/', user_login_view, name='user_login'),
    path('register/', user_register_view, name='user_register'),
    path('logout/', user_logout_view, name='user_logout'),
    path('profile/', user_profile_view, name='user_profile'),
    path('documents/upload/', public_document_upload_view, name='public_document_upload'),
]
