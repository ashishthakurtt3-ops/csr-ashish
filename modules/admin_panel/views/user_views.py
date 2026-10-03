from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from modules.admin_panel.models import User


@login_required
def user_list_view(request):
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    page_num = request.GET.get('page', 1)

    users_qs = User.objects.all().order_by('-date_joined')
    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(organization_name__icontains=q)
        )
    if role and role != 'all':
        users_qs = users_qs.filter(role=role)

    paginator = Paginator(users_qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/users/list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_role': role,
        'role_choices': User.ROLE_CHOICES,
        'total_count': paginator.count
    })


@login_required
def user_create_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role', User.ROLE_VIEWER)
        org = request.POST.get('organization_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        desig = request.POST.get('designation', '').strip()

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return render(request, 'admin/users/form.html', {'role_choices': User.ROLE_CHOICES})

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'admin/users/form.html', {'role_choices': User.ROLE_CHOICES})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            organization_name=org,
            phone=phone,
            designation=desig
        )
        if role in (User.ROLE_ADMIN, User.ROLE_STAFF):
            user.is_staff = True
            if role == User.ROLE_ADMIN:
                user.is_superuser = True
            user.save()

        messages.success(request, f"User '{username}' created successfully.")
        return redirect('admin_users:list')

    return render(request, 'admin/users/form.html', {'role_choices': User.ROLE_CHOICES})


@login_required
def user_edit_view(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_obj.email = request.POST.get('email', user_obj.email).strip()
        user_obj.first_name = request.POST.get('first_name', user_obj.first_name).strip()
        user_obj.last_name = request.POST.get('last_name', user_obj.last_name).strip()
        user_obj.role = request.POST.get('role', user_obj.role)
        user_obj.organization_name = request.POST.get('organization_name', user_obj.organization_name).strip()
        user_obj.phone = request.POST.get('phone', user_obj.phone).strip()
        user_obj.designation = request.POST.get('designation', user_obj.designation).strip()
        
        new_pwd = request.POST.get('new_password', '').strip()
        if new_pwd:
            user_obj.set_password(new_pwd)

        if user_obj.role == User.ROLE_ADMIN:
            user_obj.is_staff = True
            user_obj.is_superuser = True
        elif user_obj.role == User.ROLE_STAFF:
            user_obj.is_staff = True
            user_obj.is_superuser = False
        else:
            user_obj.is_staff = False
            user_obj.is_superuser = False

        user_obj.save()
        messages.success(request, f"User '{user_obj.username}' updated successfully.")
        return redirect('admin_users:list')

    return render(request, 'admin/users/form.html', {
        'edit_user': user_obj,
        'role_choices': User.ROLE_CHOICES
    })


@login_required
def user_toggle_status_view(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        status_str = "activated" if user_obj.is_active else "deactivated"
        messages.success(request, f"User '{user_obj.username}' {status_str}.")
    return redirect('admin_users:list')
