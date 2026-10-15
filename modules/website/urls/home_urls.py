from django.urls import path
from modules.website.views.home_views import (
    index_view, health_view, stats_view, search_view, coverage_report_api
)

urlpatterns = [
    path('', index_view, name='home'),
    path('health', health_view, name='health'),
    path('health/', health_view, name='health_slash'),
    path('stats', stats_view, name='stats'),
    path('stats/', stats_view, name='stats_slash'),
    path('api/stats', stats_view, name='api_stats'),
    path('api/stats/', stats_view, name='api_stats_slash'),
    path('api/coverage', coverage_report_api, name='api_coverage'),
    path('api/coverage/', coverage_report_api, name='api_coverage_slash'),
    path('search', search_view, name='search'),
    path('search/', search_view, name='search_slash'),
]
