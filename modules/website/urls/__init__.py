from django.urls import path, include
from modules.website.views.matching_api_views import match_ngo_api
from modules.website.views.prospect_api_views import prospects_api

app_name = 'website'

urlpatterns = [
    # Top-level website pages & stats
    path('', include('modules.website.urls.home_urls')),

    # Core Intelligence APIs (direct root)
    path('', include('modules.website.urls.company_urls')),
    path('', include('modules.website.urls.job_urls')),
    path('', include('modules.website.urls.opportunity_urls')),
    path('', include('modules.website.urls.crawler_urls')),
    path('', include('modules.website.urls.subscription_urls')),
    path('', include('modules.website.urls.auth_urls')),

    # Core Intelligence APIs (api/ prefix alias)
    path('api/', include('modules.website.urls.home_urls')),
    path('api/', include('modules.website.urls.company_urls')),
    path('api/', include('modules.website.urls.job_urls')),
    path('api/', include('modules.website.urls.opportunity_urls')),
    path('api/', include('modules.website.urls.crawler_urls')),
    path('api/', include('modules.website.urls.subscription_urls')),
    path('api/', include('modules.website.urls.auth_urls')),

    # Matching & Prospects CRM
    path('ngo/matches', match_ngo_api, name='ngo_matches'),
    path('ngo/matches/', match_ngo_api, name='ngo_matches_slash'),
    path('prospects', prospects_api, name='prospects'),
    path('prospects/', prospects_api, name='prospects_slash'),
    path('prospects/<str:company_id>', prospects_api, name='prospect_detail'),
    path('prospects/<str:company_id>/', prospects_api, name='prospect_detail_slash'),
]
