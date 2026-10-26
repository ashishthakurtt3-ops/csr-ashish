"""
Role-based access control and security middleware for Admin Panel.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class AdminRoleMiddleware:
    """
    Ensures that routes starting with /admin-portal/ (except login/logout)
    require authenticated users with administrative or staff privileges.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith('/admin-portal/') and not (
            path == '/admin-portal/login/' or 
            path == '/admin-portal/logout/' or
            path.startswith('/admin-portal/auth/')
        ):
            if not request.user.is_authenticated:
                return redirect(f"/admin-portal/login/?next={path}")
            
            # Check user role if accessing sensitive areas
            if hasattr(request.user, 'is_admin_or_staff') and not request.user.is_admin_or_staff():
                if (
                    request.content_type == 'application/json' or
                    request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                    '/save/' in path or
                    '/test/' in path or
                    path.endswith('/audit-logs/')
                ):
                    from django.http import JsonResponse
                    return JsonResponse({'success': False, 'error': 'Access denied: Administrative privileges required.'}, status=403)
                messages.error(request, "Access denied: Administrative privileges required.")
                return redirect('/')

        response = self.get_response(request)
        return response
