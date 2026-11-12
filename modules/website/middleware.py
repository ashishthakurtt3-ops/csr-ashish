"""
Performance, static asset caching, and strict subscription enforcement middleware.
"""

from django.shortcuts import redirect
from django.http import JsonResponse
from modules.website.utils.entitlement_service import user_has_active_plan


class StaticCacheMiddleware:
    """Sets cache headers on static assets."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'public, max-age=0, must-revalidate'
        return response


class StrictSubscriptionEnforcementMiddleware:
    """
    Strictly redirects authenticated users with no active subscription plan to the plans page.
    Blocks any data access or data leakage until a plan has been selected and activated.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path_info

            # Allow management routes in Admin Portal console for admin/staff
            is_admin = bool(
                request.user.is_staff
                or request.user.is_superuser
                or getattr(request.user, 'role', '') in ('ADMIN', 'SUPER_ADMIN', 'STAFF')
                or (hasattr(request.user, 'is_admin_or_staff') and request.user.is_admin_or_staff())
            )
            if is_admin and (path.startswith('/admin-portal') or path.startswith('/admin/')):
                return self.get_response(request)

            has_active = user_has_active_plan(request.user)
            if not has_active:
                # Whitelist essential routes for subscription selection, auth, profile, and styling
                allowed_prefixes = (
                    '/pricing',
                    '/logout',
                    '/login',
                    '/static/',
                    '/media/',
                    '/api/subscription/',
                    '/api/user/quotas',
                    '/profile',
                )

                # If root URL '/' is requested, allow view so home_views renders the pricing tab
                if path == '/' or any(path.startswith(prefix) for prefix in allowed_prefixes):
                    return self.get_response(request)

                # Block data APIs with strict 403 JSON response
                if path.startswith('/api/') or path.startswith('/jobs') or path.startswith('/companies') or path.startswith('/search') or path.startswith('/csr'):
                    return JsonResponse({
                        'error': 'PLAN_REQUIRED',
                        'message': 'Active subscription plan required to access corporate intelligence data.',
                        'redirect': '/pricing/?plan_required=1'
                    }, status=403)

                # For any other HTML page, strictly redirect to pricing
                return redirect('/pricing/?plan_required=1')

        return self.get_response(request)
