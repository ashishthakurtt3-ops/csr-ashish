from django.urls import path
from modules.website.views.subscription_api_views import (
    get_subscription_plans, get_subscription_promos, get_current_subscription,
    quote_subscription, validate_subscription_promo, checkout_subscription,
    cancel_subscription, resume_subscription, subscription_history,
    subscription_invoices, subscription_usage, rotate_subscription_api_key,
    wallet_topup, wallet_balance, wallet_transactions,
    subscription_upgrade, subscription_downgrade, subscription_change_plan, subscription_toggle_auto_renew,
    admin_run_renewals_now, admin_refund_payment
)

urlpatterns = [
    # Plans & Pricing
    path('api/subscription/plans', get_subscription_plans, name='subscription_plans'),
    path('api/subscription/plans/', get_subscription_plans, name='subscription_plans_slash'),
    path('api/subscription/promos', get_subscription_promos, name='subscription_promos'),
    path('api/subscription/promos/', get_subscription_promos, name='subscription_promos_slash'),

    # Subscription State & Quotes
    path('api/subscription/current', get_current_subscription, name='subscription_current'),
    path('api/subscription/current/', get_current_subscription, name='subscription_current_slash'),
    path('api/subscription/quote', quote_subscription, name='subscription_quote'),
    path('api/subscription/quote/', quote_subscription, name='subscription_quote_slash'),
    path('api/subscription/validate-promo', validate_subscription_promo, name='subscription_validate_promo'),
    path('api/subscription/validate-promo/', validate_subscription_promo, name='subscription_validate_promo_slash'),

    # Checkout & Plan Changes
    path('api/subscription/checkout', checkout_subscription, name='subscription_checkout'),
    path('api/subscription/checkout/', checkout_subscription, name='subscription_checkout_slash'),
    path('api/subscription/upgrade', subscription_upgrade, name='subscription_upgrade'),
    path('api/subscription/upgrade/', subscription_upgrade, name='subscription_upgrade_slash'),
    path('api/subscription/change-plan', subscription_change_plan, name='subscription_change_plan'),
    path('api/subscription/change-plan/', subscription_change_plan, name='subscription_change_plan_slash'),
    path('api/subscription/downgrade', subscription_downgrade, name='subscription_downgrade'),
    path('api/subscription/downgrade/', subscription_downgrade, name='subscription_downgrade_slash'),
    path('api/subscription/auto-renew', subscription_toggle_auto_renew, name='subscription_toggle_auto_renew'),
    path('api/subscription/auto-renew/', subscription_toggle_auto_renew, name='subscription_toggle_auto_renew_slash'),

    # Lifecycle Operations
    path('api/subscription/cancel', cancel_subscription, name='subscription_cancel'),
    path('api/subscription/cancel/', cancel_subscription, name='subscription_cancel_slash'),
    path('api/subscription/resume', resume_subscription, name='subscription_resume'),
    path('api/subscription/resume/', resume_subscription, name='subscription_resume_slash'),

    # Wallet Endpoints
    path('api/wallet/topup', wallet_topup, name='wallet_topup'),
    path('api/wallet/topup/', wallet_topup, name='wallet_topup_slash'),
    path('api/wallet/balance', wallet_balance, name='wallet_balance'),
    path('api/wallet/balance/', wallet_balance, name='wallet_balance_slash'),
    path('api/wallet/transactions', wallet_transactions, name='wallet_transactions'),
    path('api/wallet/transactions/', wallet_transactions, name='wallet_transactions_slash'),
    path('api/subscription/wallet/balance', wallet_balance, name='sub_wallet_balance'),
    path('api/subscription/wallet/balance/', wallet_balance, name='sub_wallet_balance_slash'),
    path('api/subscription/wallet/topup', wallet_topup, name='sub_wallet_topup'),
    path('api/subscription/wallet/topup/', wallet_topup, name='sub_wallet_topup_slash'),
    path('api/subscription/wallet/transactions', wallet_transactions, name='sub_wallet_transactions'),
    path('api/subscription/wallet/transactions/', wallet_transactions, name='sub_wallet_transactions_slash'),

    # Audit & History
    path('api/subscription/history', subscription_history, name='subscription_history'),
    path('api/subscription/history/', subscription_history, name='subscription_history_slash'),
    path('api/subscription/invoices', subscription_invoices, name='subscription_invoices'),
    path('api/subscription/invoices/', subscription_invoices, name='subscription_invoices_slash'),
    path('api/subscription/usage', subscription_usage, name='subscription_usage'),
    path('api/subscription/usage/', subscription_usage, name='subscription_usage_slash'),
    path('api/subscription/api-key/rotate', rotate_subscription_api_key, name='subscription_rotate_key'),
    path('api/subscription/api-key/rotate/', rotate_subscription_api_key, name='subscription_rotate_key_slash'),

    # Admin Control Operations
    path('api/admin/renewals/run', admin_run_renewals_now, name='admin_run_renewals'),
    path('api/admin/renewals/run/', admin_run_renewals_now, name='admin_run_renewals_slash'),
    path('api/admin/payments/<str:payment_id>/refund', admin_refund_payment, name='admin_refund_payment'),
    path('api/admin/payments/<str:payment_id>/refund/', admin_refund_payment, name='admin_refund_payment_slash'),
]
