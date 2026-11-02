from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from datetime import timedelta
import uuid

from modules.admin_panel.models import User, Plan, Subscription, SubscriptionEvent
from modules.website.utils.email_service import send_welcome_email
from modules.website.utils.subscription_service import get_or_create_wallet


class PublicLoginForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username or Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))


class PublicRegisterForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Official Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password (min 6 characters)'}))
    organization_name = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Organization or Company Name (Optional)'}))
    role = forms.ChoiceField(choices=[
        (User.ROLE_VIEWER, 'Standard User / Job Seeker / Researcher'),
        (User.ROLE_NGO_MANAGER, 'NGO / Non-Profit Representative'),
        (User.ROLE_CORPORATE, 'Corporate / CSR Foundation Partner'),
    ], widget=forms.Select(attrs={'class': 'form-input'}))


def _get_safe_next_url(request):
    """Extract and validate redirect URL to prevent open-redirect vulnerabilities."""
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return next_url
    return None


def user_login_view(request):
    safe_next = _get_safe_next_url(request)

    if request.user.is_authenticated:
        return redirect(safe_next or '/')

    form = PublicLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username'].strip()
        password = form.cleaned_data['password']

        user = authenticate(request, username=username, password=password)
        if not user:
            # Fallback: attempt email lookup
            try:
                user_obj = User.objects.filter(email__iexact=username).first()
                if user_obj:
                    user = authenticate(request, username=user_obj.username, password=password)
            except Exception:
                user = None

        if user and user.is_active:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect(safe_next or '/')
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    context = {
        'form': form,
        'next_url': safe_next or '',
    }
    return render(request, 'website/login.html', context)


def user_register_view(request):
    safe_next = _get_safe_next_url(request)

    if request.user.is_authenticated:
        return redirect(safe_next or '/')

    form = PublicRegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username'].strip()
        email = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']
        org = form.cleaned_data['organization_name'].strip()
        role = form.cleaned_data['role']

        # Validate unique username
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f"Username '{username}' is already taken. Please choose another.")
            return render(request, 'website/register.html', {'form': form, 'next_url': safe_next or ''})

        # Validate unique email
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, f"Email '{email}' is already registered. Please sign in instead.")
            return render(request, 'website/register.html', {'form': form, 'next_url': safe_next or ''})

        # Validate password strength
        dummy_user = User(username=username, email=email)
        try:
            validate_password(password, user=dummy_user)
        except ValidationError as e:
            for err in e.messages:
                messages.error(request, err)
            return render(request, 'website/register.html', {'form': form, 'next_url': safe_next or ''})

        # Atomically provision customer, active FREE plan subscription, and zero wallet
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    organization_name=org or f"{username}'s Organization",
                    role=role,
                    is_staff=False,
                    is_superuser=False,
                    is_active=True,
                    is_verified=False
                )

                # Initialize prototype wallet with zero balance
                wallet = get_or_create_wallet(user)

                # Retrieve canonical active FREE plan (code='free', 0 INR)
                free_plan = Plan.objects.filter(code='free', is_active=True).first()
                if not free_plan:
                    free_plan = Plan.objects.filter(monthly_price_paise=0, is_active=True).first()

                sub_id = f"SUB_{uuid.uuid4().hex[:12].upper()}"
                now_iso = timezone.now().isoformat()
                end_iso = (timezone.now() + timedelta(days=3650)).isoformat()

                sub = Subscription.objects.create(
                    subscription_id=sub_id,
                    user=user,
                    tenant_id=f"user_{user.id}",
                    plan_record=free_plan,
                    plan_id=free_plan.code if free_plan else 'free',
                    status='ACTIVE',
                    billing_cycle='monthly',
                    auto_renew=False,
                    current_period_start=now_iso,
                    current_period_end=end_iso,
                    organization_name=user.organization_name or user.username,
                    contact_email=user.email,
                    activated_at=now_iso,
                )

                SubscriptionEvent.objects.create(
                    subscription_id=sub_id,
                    tenant_id=sub.tenant_id,
                    event_type='SUBSCRIPTION_CREATED',
                    notes=f"Community Free tier subscription initialized on registration @{user.username}.",
                    actor=user.username,
                    created_at=now_iso
                )

            # Send welcome email asynchronously or safely
            try:
                send_welcome_email(user.email, user.username, user.get_role_display())
            except Exception:
                pass

            # Log user in immediately upon successful registration
            login(request, user)
            messages.success(request, f"Welcome to ImpactBridge, {user.username}! Your free account has been activated.")
            return redirect(safe_next or '/')

        except Exception as e:
            messages.error(request, f"Registration failed due to an internal error: {str(e)}")
            return render(request, 'website/register.html', {'form': form, 'next_url': safe_next or ''})

    context = {
        'form': form,
        'next_url': safe_next or '',
    }
    return render(request, 'website/register.html', context)


def user_logout_view(request):
    """Terminates customer session and redirects safely."""
    logout(request)
    messages.info(request, "You have been signed out successfully.")
    return redirect('/')


@login_required
def user_profile_view(request):
    from modules.website.utils.subscription_service import (
        get_or_create_wallet, get_plan, topup_wallet,
        toggle_auto_renew, schedule_plan_change, cancel, resume,
        rupees_to_paise
    )
    from modules.admin_panel.models import (
        Subscription, SubscriptionEvent, Payment, Invoice, WalletTransaction, Plan
    )

    user = request.user
    wallet = get_or_create_wallet(user)

    # Get active subscription or create fallback free tier
    sub = Subscription.objects.filter(user=user, status='ACTIVE').order_by('-created_at').first()
    if not sub:
        sub = Subscription.objects.filter(tenant_id=f"user_{user.id}", status='ACTIVE').order_by('-created_at').first()
        if sub and not sub.user:
            sub.user = user
            sub.save(update_fields=['user'])

    if not sub:
        plan_obj = Plan.objects.filter(code='free', is_active=True).first()
        sub = Subscription.objects.create(
            subscription_id=f"SUB_{uuid.uuid4().hex[:12].upper()}",
            user=user,
            tenant_id=f"user_{user.id}",
            plan_record=plan_obj,
            plan_id=plan_obj.code if plan_obj else 'free',
            status='ACTIVE',
            billing_cycle='monthly',
            auto_renew=False,
            current_period_start=timezone.now().isoformat(),
            current_period_end=(timezone.now() + timedelta(days=3650)).isoformat()
        )

    # Handle Profile Actions (Top-up, Auto-renew, Cancel)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'topup':
            amount_inr = request.POST.get('amount_inr', '0')
            try:
                amt = float(amount_inr)
                if amt <= 0:
                    messages.error(request, "Top-up amount must be greater than zero.")
                else:
                    paise = rupees_to_paise(amt)
                    res = topup_wallet(user, paise, description="User prototype wallet self-service top-up")
                    messages.success(request, f"Successfully added Rs {amt:,.2f} to your prototype wallet!")
            except Exception as e:
                messages.error(request, f"Top-up failed: {str(e)}")
            return redirect('website:user_profile')

        elif action == 'toggle_autorenew':
            enable = request.POST.get('enable') == '1'
            toggle_auto_renew(user, enable=enable)
            messages.success(request, f"Auto-renewal is now {'ENABLED' if enable else 'DISABLED'}.")
            return redirect('website:user_profile')

        elif action == 'cancel_autorenew':
            toggle_auto_renew(user, enable=False)
            messages.info(request, "Auto-renewal cancelled. Your plan will remain active until current period end.")
            return redirect('website:user_profile')

        elif action == 'reactivate_autorenew':
            toggle_auto_renew(user, enable=True)
            messages.success(request, "Auto-renewal reactivated successfully.")
            return redirect('website:user_profile')

        elif action == 'cancel_subscription':
            try:
                cancel({'reason': 'Cancelled by subscriber via profile'}, tenant_id=sub.tenant_id, user=user)
                messages.info(request, "Subscription auto-renewal cancelled. You will retain access until current period end.")
            except Exception as e:
                messages.error(request, f"Cancellation failed: {str(e)}")
            return redirect('website:user_profile')

    plan = get_plan(sub.plan_id)
    plan_obj = Plan.objects.filter(code=sub.plan_id).first()
    entitlements = plan_obj.entitlements.all() if plan_obj else []
    wallet_txs = WalletTransaction.objects.filter(user=user).order_by('-created_at')[:20]
    payments = Payment.objects.filter(user=user).order_by('-created_at')[:20]
    invoices = Invoice.objects.filter(user=user).order_by('-issued_at')[:20]
    available_plans = Plan.objects.filter(is_active=True, is_visible=True).order_by('display_order')

    context = {
        'user': user,
        'wallet': wallet,
        'subscription': sub,
        'plan': plan,
        'entitlements': entitlements,
        'wallet_txs': wallet_txs,
        'payments': payments,
        'invoices': invoices,
        'available_plans': available_plans,
    }
    return render(request, 'website/profile.html', context)
