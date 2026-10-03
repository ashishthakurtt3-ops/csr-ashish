from django.urls import path
from modules.admin_panel.views.subscription_views import (
    subscription_list_view, invoice_list_view, promo_code_list_view
)

app_name = 'admin_subscriptions'

urlpatterns = [
    path('', subscription_list_view, name='list'),
    path('invoices/', invoice_list_view, name='invoices'),
    path('promos/', promo_code_list_view, name='promos'),
]
