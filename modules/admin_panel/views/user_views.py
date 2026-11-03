from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from modules.admin_panel.models import User, AuditTrail

# Strictly normal customer/platform roles (Admin & Staff roles are strictly managed under Admin Management)
NORMAL_USER_ROLE_CHOICES = [
    (User.ROLE_VIEWER, 'Standard User / Job Seeker'),
    (User.ROLE_NGO_MANAGER, 'NGO Representative'),
    (User.ROLE_CORPORATE, 'Corporate Partner'),
]
ALLOWED_NORMAL_ROLE_KEYS = {code for code, _ in NORMAL_USER_ROLE_CHOICES}


@login_required
def user_list_view(request):
    """
    SECTION A: Normal Platform User Accounts List.
    Strictly queries users where is_staff=False and is_superuser=False.
    Superusers and administrators are never displayed in this table.
    """
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    page_num = request.GET.get('page', 1)

    # Exclude all staff and superusers
    users_qs = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')

    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(organization_name__icontains=q) |
            Q(designation__icontains=q)
        )
    if role and role != 'all':
        users_qs = users_qs.filter(role=role)

    paginator = Paginator(users_qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/users/list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_role': role,
        'role_choices': NORMAL_USER_ROLE_CHOICES,
        'total_count': paginator.count
    })


@login_required
def user_create_view(request):
    """
    Create a standard platform user account.
    Backend strictly forces is_staff=False and is_superuser=False.
    Admin roles and privileges can never be granted through this view.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', User.ROLE_VIEWER).strip()
        org = request.POST.get('organization_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        desig = request.POST.get('designation', '').strip()

        # Enforce role restriction to normal roles only
        if role not in ALLOWED_NORMAL_ROLE_KEYS:
            role = User.ROLE_VIEWER

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, 'admin/users/form.html', {'role_choices': NORMAL_USER_ROLE_CHOICES})

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'admin/users/form.html', {'role_choices': NORMAL_USER_ROLE_CHOICES})

        if email and User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered with another account.")
            return render(request, 'admin/users/form.html', {'role_choices': NORMAL_USER_ROLE_CHOICES})

        # Create user with strict standard user privileges (never admin)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            organization_name=org,
            phone=phone,
            designation=desig,
            is_staff=False,
            is_superuser=False,
            is_active=True
        )

        try:
            AuditTrail.objects.create(
                record_type='USER',
                record_id=str(user.id),
                action='CREATE_USER',
                new_value=user.username,
                user_role=request.user.username,
                notes=f"Normal user '{user.username}' ({user.get_role_display()}) provisioned by admin '{request.user.username}'.",
                timestamp=timezone.now().isoformat()
            )
        except Exception:
            pass

        messages.success(request, f"User account '{username}' created successfully.")
        return redirect('admin_users:list')

    return render(request, 'admin/users/form.html', {'role_choices': NORMAL_USER_ROLE_CHOICES})


@login_required
def user_edit_view(request, user_id):
    """
    Edit an existing normal platform user.
    If an administrator account ID is passed, rejects modification and redirects.
    Backend guarantees is_staff=False and is_superuser=False remain in effect.
    """
    user_obj = get_object_or_404(User, id=user_id)

    # Security check: administrator accounts cannot be edited from standard user interface
    if user_obj.is_staff or user_obj.is_superuser:
        messages.error(request, f"Account '{user_obj.username}' is an Administrator. Please use Admin Management.")
        return redirect('admin_management:list')

    if request.method == 'POST':
        user_obj.email = request.POST.get('email', user_obj.email).strip()
        user_obj.first_name = request.POST.get('first_name', user_obj.first_name).strip()
        user_obj.last_name = request.POST.get('last_name', user_obj.last_name).strip()
        
        # Enforce normal roles only
        submitted_role = request.POST.get('role', user_obj.role).strip()
        if submitted_role in ALLOWED_NORMAL_ROLE_KEYS:
            user_obj.role = submitted_role

        user_obj.organization_name = request.POST.get('organization_name', user_obj.organization_name).strip()
        user_obj.phone = request.POST.get('phone', user_obj.phone).strip()
        user_obj.designation = request.POST.get('designation', user_obj.designation).strip()

        new_pwd = request.POST.get('new_password', '').strip()
        if new_pwd:
            if len(new_pwd) < 6:
                messages.error(request, "Password must be at least 6 characters long.")
                return render(request, 'admin/users/form.html', {
                    'edit_user': user_obj,
                    'role_choices': NORMAL_USER_ROLE_CHOICES
                })
            user_obj.set_password(new_pwd)

        # Backend guarantee: always keep normal users non-staff and non-superuser
        user_obj.is_staff = False
        user_obj.is_superuser = False
        user_obj.save()

        try:
            AuditTrail.objects.create(
                record_type='USER',
                record_id=str(user_obj.id),
                action='UPDATE_USER',
                new_value=user_obj.username,
                user_role=request.user.username,
                notes=f"User '{user_obj.username}' updated by admin '{request.user.username}'.",
                timestamp=timezone.now().isoformat()
            )
        except Exception:
            pass

        messages.success(request, f"User '{user_obj.username}' updated successfully.")
        return redirect('admin_users:list')

    return render(request, 'admin/users/form.html', {
        'edit_user': user_obj,
        'role_choices': NORMAL_USER_ROLE_CHOICES
    })


@login_required
def user_toggle_status_view(request, user_id):
    """
    Toggle active/inactive status of normal users.
    Rejects actions on administrator accounts.
    """
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj.is_staff or user_obj.is_superuser:
        messages.error(request, "Administrator status cannot be toggled here. Please use Admin Management.")
        return redirect('admin_users:list')

    user_obj.is_active = not user_obj.is_active
    user_obj.save(update_fields=['is_active'])

    status_str = "activated" if user_obj.is_active else "deactivated"
    try:
        AuditTrail.objects.create(
            record_type='USER',
            record_id=str(user_obj.id),
            action='TOGGLE_USER_STATUS',
            new_value=status_str.upper(),
            user_role=request.user.username,
            notes=f"User '{user_obj.username}' {status_str} by admin '{request.user.username}'.",
            timestamp=timezone.now().isoformat()
        )
    except Exception:
        pass

    messages.success(request, f"User account '{user_obj.username}' has been {status_str}.")
    return redirect('admin_users:list')
