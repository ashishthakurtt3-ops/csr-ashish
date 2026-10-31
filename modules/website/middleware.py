"""
Performance and static asset caching middleware.
"""

import re

class StaticCacheMiddleware:
    """Sets cache headers on static assets."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=0, must-revalidate'
        return response
