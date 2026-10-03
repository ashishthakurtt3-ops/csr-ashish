from django.urls import path
from modules.website.views.subscription_api_views import (
    get_subscription_plans, get_subscription_promos, get_current_subscription,
    quote_subscription, validate_subscription_promo, checkout_subscription,
    cancel_subscription, resume_subscription, subscription_history,
    subscription_invoices, subscription_usage, rotate_subscription_api_key
)

urlpatterns = [
    path('api/subscription/plans', get_subscription_plans, name='subscription_plans'),
    path('api/subscription/plans/', get_subscription_plans, name='subscription_plans_slash'),
    path('api/subscription/promos', get_subscription_promos, name='subscription_promos'),
    path('api/subscription/promos/', get_subscription_promos, name='subscription_promos_slash'),
    path('api/subscription/current', get_current_subscription, name='subscription_current'),
    path('api/subscription/current/', get_current_subscription, name='subscription_current_slash'),
    path('api/subscription/quote', quote_subscription, name='subscription_quote'),
    path('api/subscription/quote/', quote_subscription, name='subscription_quote_slash'),
    path('api/subscription/validate-promo', validate_subscription_promo, name='subscription_validate_promo'),
    path('api/subscription/validate-promo/', validate_subscription_promo, name='subscription_validate_promo_slash'),
    path('api/subscription/checkout', checkout_subscription, name='subscription_checkout'),
    path('api/subscription/checkout/', checkout_subscription, name='subscription_checkout_slash'),
    path('api/subscription/cancel', cancel_subscription, name='subscription_cancel'),
    path('api/subscription/cancel/', cancel_subscription, name='subscription_cancel_slash'),
    path('api/subscription/resume', resume_subscription, name='subscription_resume'),
    path('api/subscription/resume/', resume_subscription, name='subscription_resume_slash'),
    path('api/subscription/history', subscription_history, name='subscription_history'),
    path('api/subscription/history/', subscription_history, name='subscription_history_slash'),
    path('api/subscription/invoices', subscription_invoices, name='subscription_invoices'),
    path('api/subscription/invoices/', subscription_invoices, name='subscription_invoices_slash'),
    path('api/subscription/usage', subscription_usage, name='subscription_usage'),
    path('api/subscription/usage/', subscription_usage, name='subscription_usage_slash'),
    path('api/subscription/api-key/rotate', rotate_subscription_api_key, name='subscription_rotate_key'),
    path('api/subscription/api-key/rotate/', rotate_subscription_api_key, name='subscription_rotate_key_slash'),
]
