from django.urls import path
from modules.website.views.crawler_api_views import (
    crawler_logs_api, company_crawler_log_api, recheck_company_domain_api,
    live_sync_fetch_api, live_crawler_stream_api,
    admin_crawler_status_api, admin_verification_queue_api,
    admin_verify_api, admin_audit_trail_api
)

urlpatterns = [
    path('api/crawler/logs', crawler_logs_api, name='crawler_logs'),
    path('api/crawler/logs/', crawler_logs_api, name='crawler_logs_slash'),
    path('api/crawler/logs/<str:company_id>', company_crawler_log_api, name='company_crawler_log'),
    path('api/crawler/logs/<str:company_id>/', company_crawler_log_api, name='company_crawler_log_slash'),
    path('api/crawler/recheck/<str:company_id>', recheck_company_domain_api, name='recheck_company_domain'),
    path('api/crawler/recheck/<str:company_id>/', recheck_company_domain_api, name='recheck_company_domain_slash'),
    path('api/fetch/live-sync', live_sync_fetch_api, name='live_sync_fetch'),
    path('api/fetch/live-sync/', live_sync_fetch_api, name='live_sync_fetch_slash'),
    path('api/crawler/live-stream', live_crawler_stream_api, name='live_crawler_stream'),
    path('api/crawler/live-stream/', live_crawler_stream_api, name='live_crawler_stream_slash'),

    # Legacy admin API compatibility endpoints
    path('admin/crawler-status', admin_crawler_status_api, name='legacy_admin_crawler_status'),
    path('admin/crawler-status/', admin_crawler_status_api, name='legacy_admin_crawler_status_slash'),
    path('admin/verification-queue', admin_verification_queue_api, name='legacy_admin_verification_queue'),
    path('admin/verification-queue/', admin_verification_queue_api, name='legacy_admin_verification_queue_slash'),
    path('admin/verify', admin_verify_api, name='legacy_admin_verify'),
    path('admin/verify/', admin_verify_api, name='legacy_admin_verify_slash'),
    path('admin/audit-trail', admin_audit_trail_api, name='legacy_admin_audit_trail'),
    path('admin/audit-trail/', admin_audit_trail_api, name='legacy_admin_audit_trail_slash'),
]
