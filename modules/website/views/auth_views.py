from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from modules.admin_panel.models import User
from modules.website.utils.email_service import send_welcome_email


class PublicLoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username or Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))


class PublicRegisterForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Official Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password (min 6 chars)'}))
    organization_name = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'NGO / Organization Name'}))
    role = forms.ChoiceField(choices=[
        (User.ROLE_NGO_MANAGER, 'NGO / Non-Profit Representative'),
        (User.ROLE_VIEWER, 'Job Seeker / Sustainability Professional'),
        (User.ROLE_CORPORATE, 'Corporate / CSR Foundation'),
    ], widget=forms.Select(attrs={'class': 'form-input'}))


def user_login_view(request):
    if request.user.is_authenticated:
        return redirect('website:home')

    form = PublicLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']

        user = authenticate(request, username=username, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user and user.is_active:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('website:home')
        else:
            messages.error(request, "Invalid credentials. Please verify your details.")

    return render(request, 'website/login.html', {'form': form})


def user_register_view(request):
    if request.user.is_authenticated:
        return redirect('website:home')

    form = PublicRegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        org = form.cleaned_data['organization_name']
        role = form.cleaned_data['role']

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already in use.")
            return render(request, 'website/register.html', {'form': form})

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return render(request, 'website/register.html', {'form': form})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            organization_name=org,
            role=role,
            is_verified=False
        )

        send_welcome_email(user.email, user.username, user.get_role_display())
        login(request, user)
        messages.success(request, "Your account has been created successfully!")
        return redirect('website:home')

    return render(request, 'website/register.html', {'form': form})


def user_logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect('website:home')


@login_required
def user_profile_view(request):
    return render(request, 'website/profile.html', {'user': request.user})
