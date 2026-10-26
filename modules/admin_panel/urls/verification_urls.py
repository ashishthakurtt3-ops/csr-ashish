from django.urls import path
from modules.admin_panel.views.verification_views import (
    verification_queue_view, verification_action_view,
    audit_trail_view, crawler_telemetry_view
)

app_name = 'admin_verification'

urlpatterns = [
    path('queue/', verification_queue_view, name='queue'),
    path('queue/<int:record_id>/action/', verification_action_view, name='action'),
    path('audit-trail/', audit_trail_view, name='audit_trail'),
    path('crawler-status/', crawler_telemetry_view, name='crawler_status'),
]
