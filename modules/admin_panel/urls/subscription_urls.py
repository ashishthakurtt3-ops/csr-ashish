from django.urls import path
from modules.admin_panel.views.subscription_views import (
    subscription_list_view,
    subscription_detail_manage_view,
    plan_list_view,
    plan_create_edit_view,
    plan_duplicate_view,
    plan_toggle_status_view,
    plan_delete_view,
    payment_list_view,
    payment_detail_view,
    admin_payment_refund_view,
    wallet_list_view,
    admin_wallet_adjust_view,
    invoice_list_view,
    invoice_detail_view,
    promo_code_list_view,
    admin_trigger_renewals_view
)

app_name = 'admin_subscriptions'

urlpatterns = [
    # Subscriptions
    path('', subscription_list_view, name='list'),
    path('<str:sub_id>/manage/', subscription_detail_manage_view, name='manage'),
    path('renewals/run/', admin_trigger_renewals_view, name='run_renewals'),

    # Plans Catalog
    path('plans/', plan_list_view, name='plans_list'),
    path('plans/create/', plan_create_edit_view, name='plan_create'),
    path('plans/<str:code>/edit/', plan_create_edit_view, name='plan_edit'),
    path('plans/<str:code>/duplicate/', plan_duplicate_view, name='plan_duplicate'),
    path('plans/<str:code>/toggle/', plan_toggle_status_view, name='plan_toggle'),
    path('plans/<str:code>/delete/', plan_delete_view, name='plan_delete'),

    # Payments & Transactions
    path('payments/', payment_list_view, name='payments_list'),
    path('payments/<str:payment_id>/', payment_detail_view, name='payment_detail'),
    path('payments/<str:payment_id>/refund/', admin_payment_refund_view, name='payment_refund'),

    # Wallets
    path('wallets/', wallet_list_view, name='wallets_list'),
    path('wallets/<int:user_id>/adjust/', admin_wallet_adjust_view, name='wallet_adjust'),

    # Invoices
    path('invoices/', invoice_list_view, name='invoices'),
    path('invoices/<int:invoice_id>/', invoice_detail_view, name='invoice_detail'),

    # Promos
    path('promos/', promo_code_list_view, name='promos'),
]
