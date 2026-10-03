from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from modules.admin_panel.models import User


class AdminLoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter username or email',
        'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter password'
    }))


def admin_login_view(request):
    if request.user.is_authenticated and hasattr(request.user, 'is_admin_or_staff') and request.user.is_admin_or_staff():
        return redirect('admin_portal:dashboard')

    form = AdminLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        
        # Support logging in by email or username
        user = authenticate(request, username=username, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                next_url = request.GET.get('next', 'admin_portal:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, "This account is currently deactivated.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'admin/auth/login.html', {'form': form})


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
