"""
modules/admin_panel/views/admin_management_views.py
===================================================
Dedicated Admin Management Module for ImpactBridge.
Provides complete governance over Full Administrator / Superuser accounts:
- Dashboard KPI cards (Total, Active, Inactive, Recently Added).
- Administrator list with search, status filters, and pagination.
- Add Administrator workflow (forces is_staff=True, is_superuser=True, role=ADMIN).
- Edit Administrator details and status.
- Safe toggle status with Last Active Administrator guard.
- Secure password reset workflow.
- Complete audit trail logging without exposing credentials.
"""

import secrets
import string
from functools import wraps
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from modules.admin_panel.models import User, AuditTrail


def full_admin_required(view_func):
    """
    Decorator enforcing that only authenticated full administrators/superusers
    (is_staff=True and is_superuser=True and is_active=True) can access this view.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/admin-portal/login/?next={request.path}")
        if not (request.user.is_active and request.user.is_staff and request.user.is_superuser):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'message': 'Access denied: Full administrator privileges required.'}, status=403)
            messages.error(request, "Access denied: Full administrator privileges required.")
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped


@full_admin_required
def admin_list_view(request):
    """
    SECTION B: Admin Management Dashboard & Directory.
    Exclusively manages Full Administrator / Superuser accounts (is_staff=True, is_superuser=True).
    Provides live KPI counts, search, status filtering, and administrative action links.
    """
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all').strip().lower()
    page_num = request.GET.get('page', 1)

    # Base queryset: only full administrators / superusers
    base_qs = User.objects.filter(is_staff=True, is_superuser=True).order_by('-date_joined')

    # Compute live dashboard KPI metrics
    now = timezone.now()
    thirty_days_ago = now - datetime.timedelta(days=30)
    
    total_admins = base_qs.count()
    active_admins = base_qs.filter(is_active=True).count()
    inactive_admins = base_qs.filter(is_active=False).count()
    recent_admins = base_qs.filter(date_joined__gte=thirty_days_ago).count()

    filtered_qs = base_qs
    if q:
        filtered_qs = filtered_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(designation__icontains=q) |
            Q(organization_name__icontains=q)
        )

    if status_filter == 'active':
        filtered_qs = filtered_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        filtered_qs = filtered_qs.filter(is_active=False)

    paginator = Paginator(filtered_qs, 12)
    page_obj = paginator.get_page(page_num)

    newly_created_admin = request.session.pop('newly_created_admin', None)

    return render(request, 'admin/admins/list.html', {
        'page_obj': page_obj,
        'q': q,
        'status_filter': status_filter,
        'total_admins': total_admins,
        'active_admins': active_admins,
        'inactive_admins': inactive_admins,
        'recent_admins': recent_admins,
        'filtered_count': paginator.count,
        'newly_created_admin': newly_created_admin,
    })


@full_admin_required
def admin_create_view(request):
    """
    Add New Administrator Workflow.
    Provisions a new Full Administrator / Superuser account.
    Every account created through this view receives full administrator privileges:
    - is_staff = True
    - is_superuser = True
    - is_active = True
    - role = User.ROLE_ADMIN
    No dropdown for Admin vs Superuser: both are identical in this architecture.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        designation = request.POST.get('designation', '').strip() or 'Administrator'
        organization_name = request.POST.get('organization_name', '').strip() or 'ImpactBridge Admin'
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        is_active = request.POST.get('is_active', '1') == '1'

        # Validation
        errors = []
        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append(f"Username '{username}' is already in use.")

        if not email:
            errors.append("Email address is required.")
        elif User.objects.filter(email=email).exists():
            errors.append(f"Email '{email}' is already registered with another account.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'admin/admins/form.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'designation': designation,
                'organization_name': organization_name,
                'is_active': is_active,
            })

        # Provision full administrator
        new_admin = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            designation=designation,
            organization_name=organization_name,
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
            is_active=is_active
        )

        try:
            AuditTrail.objects.create(
                record_type='ADMIN',
                record_id=str(new_admin.id),
                action='CREATE_ADMIN',
                new_value=new_admin.username,
                user_role=request.user.username,
                notes=f"Full administrator '{new_admin.username}' ({new_admin.email}) created by '{request.user.username}' with full privileges.",
                timestamp=timezone.now().isoformat()
            )
        except Exception:
            pass

        request.session['newly_created_admin'] = {
            'username': new_admin.username,
            'email': new_admin.email,
            'full_name': new_admin.get_full_name() or new_admin.username,
            'plain_password': password,
            'designation': new_admin.designation,
            'role': 'Master Super Administrator (is_superuser=True, is_staff=True)'
        }

        messages.success(request, f"Full Administrator '{username}' created successfully. The new administrator can now log in.")
        return redirect('admin_management:list')

    return render(request, 'admin/admins/form.html', {
        'is_active': True,
        'designation': 'System Administrator',
        'organization_name': 'ImpactBridge Admin'
    })


@full_admin_required
def admin_edit_view(request, admin_id):
    """
    Edit details of an existing Full Administrator.
    Guarantees account remains is_staff=True and is_superuser=True.
    Enforces that the last active administrator cannot be deactivated.
    """
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True, is_superuser=True)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        designation = request.POST.get('designation', '').strip()
        organization_name = request.POST.get('organization_name', '').strip()
        desired_active = request.POST.get('is_active', '1') == '1'

        # Check email uniqueness against other users
        if email and User.objects.filter(email=email).exclude(id=admin_obj.id).exists():
            messages.error(request, f"Email '{email}' is already in use by another account.")
            return render(request, 'admin/admins/form.html', {'edit_admin': admin_obj})

        # Last Active Administrator Guard
        if not desired_active and admin_obj.is_active:
            if admin_obj == request.user:
                messages.error(request, "You cannot deactivate your own administrator account.")
                return render(request, 'admin/admins/form.html', {'edit_admin': admin_obj})
            active_admin_count = User.objects.filter(is_staff=True, is_superuser=True, is_active=True).count()
            if active_admin_count <= 1:
                messages.error(request, "Cannot deactivate the last active administrator account. At least one active full administrator must exist.")
                return render(request, 'admin/admins/form.html', {'edit_admin': admin_obj})

        admin_obj.email = email
        admin_obj.first_name = first_name
        admin_obj.last_name = last_name
        admin_obj.phone = phone
        admin_obj.designation = designation
        admin_obj.organization_name = organization_name
        admin_obj.is_active = desired_active
        admin_obj.is_staff = True
        admin_obj.is_superuser = True
        admin_obj.role = User.ROLE_ADMIN
        admin_obj.save()

        try:
            AuditTrail.objects.create(
                record_type='ADMIN',
                record_id=str(admin_obj.id),
                action='UPDATE_ADMIN',
                new_value=admin_obj.username,
                user_role=request.user.username,
                notes=f"Administrator details for '{admin_obj.username}' updated by '{request.user.username}'.",
                timestamp=timezone.now().isoformat()
            )
        except Exception:
            pass

        messages.success(request, f"Administrator '{admin_obj.username}' updated successfully.")
        return redirect('admin_management:list')

    return render(request, 'admin/admins/form.html', {'edit_admin': admin_obj})


@full_admin_required
def admin_toggle_status_view(request, admin_id):
    """
    Safely activate or deactivate an administrator account.
    - Prevents administrators from deactivating their own account.
    - Prevents deactivating the last active administrator.
    """
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True, is_superuser=True)

    if admin_obj == request.user:
        messages.error(request, "Security Guard: You cannot deactivate your own administrator account.")
        return redirect('admin_management:list')

    if admin_obj.is_active:
        active_admin_count = User.objects.filter(is_staff=True, is_superuser=True, is_active=True).count()
        if active_admin_count <= 1:
            messages.error(request, "Security Guard: Cannot deactivate the last active administrator account. At least one active full administrator must be retained.")
            return redirect('admin_management:list')

    admin_obj.is_active = not admin_obj.is_active
    admin_obj.save(update_fields=['is_active'])

    status_str = "activated" if admin_obj.is_active else "deactivated"
    try:
        AuditTrail.objects.create(
            record_type='ADMIN',
            record_id=str(admin_obj.id),
            action='TOGGLE_ADMIN_STATUS',
            new_value=status_str.upper(),
            user_role=request.user.username,
            notes=f"Administrator '{admin_obj.username}' {status_str} by '{request.user.username}'.",
            timestamp=timezone.now().isoformat()
        )
    except Exception:
        pass

    messages.success(request, f"Administrator account '{admin_obj.username}' has been {status_str}.")
    return redirect('admin_management:list')


@full_admin_required
def admin_reset_password_view(request, admin_id):
    """
    Secure password reset workflow for an administrator.
    Uses standard Django password hashing. Never logs or exposes password values.
    """
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True, is_superuser=True)

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password:
            messages.error(request, "New password cannot be empty.")
            return redirect('admin_management:list')

        if len(new_password) < 8:
            messages.error(request, "Administrator password must be at least 8 characters long.")
            return redirect('admin_management:list')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('admin_management:list')

        admin_obj.set_password(new_password)
        admin_obj.save(update_fields=['password'])

        try:
            AuditTrail.objects.create(
                record_type='ADMIN',
                record_id=str(admin_obj.id),
                action='RESET_PASSWORD_ADMIN',
                new_value='PASSWORD_RESET_SUCCESS',
                user_role=request.user.username,
                notes=f"Password for administrator '{admin_obj.username}' was reset by '{request.user.username}'.",
                timestamp=timezone.now().isoformat()
            )
        except Exception:
            pass

        messages.success(request, f"Password for administrator '{admin_obj.username}' was reset successfully.")
        return redirect('admin_management:list')

    return redirect('admin_management:list')


@full_admin_required
def admin_detail_api(request, admin_id):
    """
    Read-only JSON inspection endpoint for administrator details modal.
    """
    admin_obj = get_object_or_404(User, id=admin_id, is_staff=True, is_superuser=True)
    return JsonResponse({
        'status': 'ok',
        'admin': {
            'id': admin_obj.id,
            'username': admin_obj.username,
            'full_name': admin_obj.get_full_name() or admin_obj.username,
            'email': admin_obj.email or '',
            'phone': admin_obj.phone or '—',
            'organization': admin_obj.organization_name or '—',
            'designation': admin_obj.designation or 'Administrator',
            'role_display': 'Administrator / Full Superuser',
            'is_staff': admin_obj.is_staff,
            'is_superuser': admin_obj.is_superuser,
            'is_active': admin_obj.is_active,
            'date_joined': admin_obj.date_joined.strftime('%b %d, %Y %H:%M') if admin_obj.date_joined else '—',
            'last_login': admin_obj.last_login.strftime('%b %d, %Y %H:%M') if admin_obj.last_login else 'Never',
        }
    })


@full_admin_required
def admin_quick_generate_api(request):
    """
    ⚡ 1-Click Fast Superuser Provisioning API.
    Enables instant generation of multiple superuser accounts without cumbersome multi-step typing.
    Automatically provisions:
    - is_staff=True
    - is_superuser=True
    - role=User.ROLE_ADMIN
    - is_active=True
    Returns the created superuser credentials with instant copy-to-clipboard capability.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required.'}, status=405)

    import json
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    else:
        data = request.POST

    first_name = data.get('first_name', '').strip() or 'Admin'
    last_name = data.get('last_name', '').strip() or 'Operator'
    designation = data.get('designation', '').strip() or 'System Administrator'
    organization_name = data.get('organization_name', '').strip() or 'ImpactBridge Admin'

    # Auto-generate unique username if not provided or requested
    username = data.get('username', '').strip()
    if not username:
        base_name = f"admin_{secrets.token_hex(2)}"
        count = 1
        username = base_name
        while User.objects.filter(username=username).exists():
            username = f"{base_name}_{count}"
            count += 1
    elif User.objects.filter(username=username).exists():
        return JsonResponse({'status': 'error', 'message': f"Username '{username}' already exists. Please choose a different username."}, status=400)

    # Auto-generate unique email if not provided
    email = data.get('email', '').strip()
    if not email:
        email = f"{username}@impactbridge.internal"
        count = 1
        while User.objects.filter(email=email).exists():
            email = f"{username}_{count}@impactbridge.internal"
            count += 1
    elif User.objects.filter(email=email).exists():
        return JsonResponse({'status': 'error', 'message': f"Email '{email}' is already registered with another account."}, status=400)

    # Auto-generate strong secure password if not provided
    password = data.get('password', '').strip()
    if not password:
        # Guarantee at least 1 upper, 1 lower, 1 digit, 1 special symbol + random chars
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = (
            secrets.choice(string.ascii_uppercase) +
            secrets.choice(string.ascii_lowercase) +
            secrets.choice(string.digits) +
            secrets.choice("!@#$%^&*") +
            "".join(secrets.choice(alphabet) for _ in range(8))
        )
    elif len(password) < 8:
        return JsonResponse({'status': 'error', 'message': 'Password must be at least 8 characters long.'}, status=400)

    # Create new full superuser
    new_admin = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        designation=designation,
        organization_name=organization_name,
        role=User.ROLE_ADMIN,
        is_staff=True,
        is_superuser=True,
        is_active=True
    )

    try:
        AuditTrail.objects.create(
            record_type='ADMIN',
            record_id=str(new_admin.id),
            action='QUICK_GENERATE_ADMIN',
            new_value=new_admin.username,
            user_role=request.user.username,
            notes=f"Full superuser administrator '{new_admin.username}' ({new_admin.email}) quick-generated by '{request.user.username}'.",
            timestamp=timezone.now().isoformat()
        )
    except Exception:
        pass

    return JsonResponse({
        'status': 'ok',
        'message': f"Superuser '{username}' successfully provisioned with full administrative governance.",
        'admin': {
            'id': new_admin.id,
            'username': new_admin.username,
            'email': new_admin.email,
            'full_name': new_admin.get_full_name() or new_admin.username,
            'designation': new_admin.designation,
            'plain_password': password,
            'is_staff': True,
            'is_superuser': True,
            'role': 'Master Super Administrator',
            'login_url': '/admin-portal/login/'
        }
    })


