from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django import forms
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from modules.admin_panel.models import User

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900


class AdminLoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter username or email',
        'autofocus': True,
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter password',
    }))


def _client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _throttle_keys(request, username: str):
    ip = _client_ip(request)
    return (
        f'adminlogin:ip:{ip}',
        f'adminlogin:user:{(username or "").strip().lower()[:150]}',
    )


def _is_locked(keys) -> bool:
    return any((cache.get(key) or 0) >= LOGIN_MAX_ATTEMPTS for key in keys)


def _record_failure(keys) -> None:
    for key in keys:
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, LOGIN_LOCKOUT_SECONDS)


def _clear_failures(keys) -> None:
    for key in keys:
        cache.delete(key)


def _safe_next_url(request, candidate: str) -> str:
    """Return ``candidate`` only if it is a same-origin path, else the dashboard."""
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return 'admin_portal:dashboard'


def admin_login_view(request):
    if (
        request.user.is_authenticated
        and hasattr(request.user, 'is_admin_or_staff')
        and request.user.is_admin_or_staff()
    ):
        return redirect('admin_portal:dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or ''
    form = AdminLoginForm(request.POST or None)

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        throttle_keys = _throttle_keys(request, username)

        if _is_locked(throttle_keys):
            messages.error(
                request,
                'Too many failed sign-in attempts. Try again in 15 minutes.',
            )
            return redirect(request.path)

        if form.is_valid():
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user is None:
                user_obj = User.objects.filter(email__iexact=username).first()
                if user_obj is not None:
                    user = authenticate(request, username=user_obj.username, password=password)

            if user is not None and user.is_active:
                _clear_failures(throttle_keys)
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                return redirect(_safe_next_url(request, next_url))

            if user is not None and not user.is_active:
                messages.error(request, 'This account is currently deactivated.')
            else:
                _record_failure(throttle_keys)
                messages.error(request, 'Invalid username or password. Please try again.')
        else:
            _record_failure(throttle_keys)
            messages.error(request, 'Please enter both username/email and security password.')

        return redirect(request.path)

    return render(request, 'admin/auth/login.html', {'form': form, 'next_url': next_url})


def admin_logout_view(request):
    logout(request)
    messages.info(request, "You have been securely signed out.")
    return redirect('admin_portal:login')


@login_required
def admin_profile_view(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', getattr(user, 'phone', ''))
        user.organization_name = request.POST.get('organization_name', getattr(user, 'organization_name', ''))
        user.designation = request.POST.get('designation', getattr(user, 'designation', ''))
        user.save()
        messages.success(request, "Profile details updated successfully.")
        return redirect('admin_portal:profile')

    return render(request, 'admin/users/profile.html', {'user': user})
