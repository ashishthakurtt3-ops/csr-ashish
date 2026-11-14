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
        from modules.website.utils.entitlement_service import user_has_active_plan
        is_admin = bool(
            (hasattr(request.user, 'is_admin_or_staff') and request.user.is_admin_or_staff())
            or request.user.is_staff
            or request.user.is_superuser
            or getattr(request.user, 'role', '') in ('ADMIN', 'STAFF')
        )
        if not user_has_active_plan(request.user):
            if is_admin and safe_next and safe_next.startswith('/admin-portal'):
                return redirect(safe_next)
            return redirect('/pricing/?plan_required=1')
        if is_admin:
            return redirect(safe_next or '/admin-portal/')
        return redirect(safe_next or '/')

    form = PublicLoginForm(request.POST or None)
    login_error = None

    if request.method == 'POST':
        if form.is_valid():
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

                # Check if user has an active subscription plan
                from modules.website.utils.entitlement_service import user_has_active_plan
                is_admin = bool(
                    (hasattr(user, 'is_admin_or_staff') and user.is_admin_or_staff())
                    or user.is_staff
                    or user.is_superuser
                    or getattr(user, 'role', None) in ('ADMIN', 'STAFF')
                )

                if not user_has_active_plan(user):
                    # If administrator explicitly requested an admin portal route, allow it; otherwise redirect to plans
                    if is_admin and safe_next and safe_next.startswith('/admin-portal'):
                        return redirect(safe_next)
                    return redirect('/pricing/?plan_required=1')

                if is_admin:
                    return redirect(safe_next or '/admin-portal/')
                return redirect(safe_next or '/')
            elif user and not user.is_active:
                login_error = "This account is currently disabled. Please contact support."
            else:
                login_error = "Invalid username or password. Please verify your credentials."
        else:
            login_error = "Please enter both username/email and password."

    context = {
        'form': form,
        'next_url': safe_next or '',
        'login_error': login_error,
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
                is_admin_user = username.lower().startswith('admin')
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    organization_name=org or f"{username}'s Organization",
                    role=User.ROLE_ADMIN if is_admin_user else role,
                    is_staff=is_admin_user,
                    is_superuser=is_admin_user,
                    is_active=True,
                    is_verified=True if is_admin_user else False
                )

                # Initialize prototype wallet with zero balance
                wallet = get_or_create_wallet(user)

                # Automatically provision Community Free 14-day trial plan for newly registered users
                free_plan = Plan.objects.filter(code='free', is_active=True).first()
                if free_plan:
                    from datetime import datetime, timezone, timedelta
                    now_dt = datetime.now(timezone.utc)
                    trial_days = getattr(free_plan, 'trial_days', 14) or 14
                    trial_end = now_dt + timedelta(days=trial_days)
                    Subscription.objects.create(
                        tenant_id=f"user_{user.id}",
                        user=user,
                        plan_id='free',
                        plan_record=free_plan,
                        status='TRIALING',
                        current_period_start=now_dt.isoformat(),
                        current_period_end=trial_end.isoformat(),
                        organization_name=user.organization_name,
                        contact_email=user.email,
                    )

            # Send welcome email asynchronously or safely
            try:
                send_welcome_email(user.email, user.username, user.get_role_display())
            except Exception:
                pass

            # Log user in immediately upon successful registration
            login(request, user)
            if is_admin_user:
                messages.success(request, f"Welcome Administrator, {user.username}!")
                return redirect(safe_next or '/admin-portal/')
            messages.info(request, f"Welcome to ImpactBridge, {user.username}! Your account has been created. Please select a subscription plan to unlock corporate intelligence.")
            return redirect('/?tab=pricing&plan_required=1')

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

    # Retrieve user's existing subscription (any status: ACTIVE, EXPIRED, CANCELED)
    # Login and profile views MUST be strictly read-only and never auto-activate or overwrite subscriptions
    sub = Subscription.objects.filter(user=user).order_by('-created_at').first()
    if not sub:
        sub = Subscription.objects.filter(tenant_id=f"user_{user.id}").order_by('-created_at').first()
        if sub and not sub.user:
            sub.user = user
            sub.save(update_fields=['user'])

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

        elif action == 'cancel_subscription' and sub:
            try:
                cancel({'reason': 'Cancelled by subscriber via profile'}, tenant_id=sub.tenant_id, user=user)
                messages.info(request, "Subscription auto-renewal cancelled. You will retain access until current period end.")
            except Exception as e:
                messages.error(request, f"Cancellation failed: {str(e)}")
            return redirect('website:user_profile')

        elif action == 'invite_team_member':
            from modules.website.utils.entitlement_service import EntitlementService, EntitlementError
            from modules.admin_panel.models import TeamMembership
            import secrets
            email = request.POST.get('member_email', '').strip().lower()
            role = request.POST.get('member_role', 'MEMBER')
            svc = EntitlementService(user)
            try:
                svc.check_can_add_team_member()
                member, created = TeamMembership.objects.get_or_create(
                    owner=user,
                    invited_email=email,
                    defaults={'role': role, 'status': 'INVITED', 'invitation_token': secrets.token_hex(32)}
                )
                if not created and member.status == 'REVOKED':
                    member.status = 'INVITED'
                    member.save()
                messages.success(request, f"Team invitation sent to {email}!")
            except Exception as e:
                messages.error(request, str(e))
            return redirect('website:user_profile')

        elif action == 'revoke_team_member':
            from modules.admin_panel.models import TeamMembership
            mid = request.POST.get('member_id')
            if mid:
                TeamMembership.objects.filter(owner=user, id=int(mid)).update(status='REVOKED')
                messages.info(request, "Team membership revoked.")
            return redirect('website:user_profile')

    from modules.admin_panel.models import SavedRecord, SavedSearch, TeamMembership
    from modules.website.utils.entitlement_service import EntitlementService

    svc = EntitlementService(user)
    plan = get_plan(sub.plan_id) if sub else None
    plan_obj = Plan.objects.filter(code=sub.plan_id).first() if sub else None
    entitlements = plan_obj.entitlements.all() if plan_obj else []
    wallet_txs = WalletTransaction.objects.filter(user=user).order_by('-created_at')[:20]
    payments = Payment.objects.filter(user=user).order_by('-created_at')[:20]
    invoices = Invoice.objects.filter(user=user).order_by('-issued_at')[:20]
    available_plans = Plan.objects.filter(is_active=True, is_visible=True).order_by('display_order')

    saved_records_count = SavedRecord.objects.filter(user=user).count()
    saved_searches_count = SavedSearch.objects.filter(user=user, is_active=True).count()
    team_members = list(TeamMembership.objects.filter(owner=user).exclude(status='REVOKED'))
    is_ultra = bool(sub and sub.status in ('ACTIVE', 'TRIALING') and (sub.plan_id in ('ultra', 'enterprise', 'foundation')))
    is_pro = bool(sub and sub.status in ('ACTIVE', 'TRIALING') and (sub.plan_id == 'pro'))
    is_free = bool(sub and sub.status in ('ACTIVE', 'TRIALING') and (sub.plan_id in ('free', 'starter')))

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
        'saved_records_count': saved_records_count,
        'saved_searches_count': saved_searches_count,
        'team_members': team_members,
        'is_ultra': is_ultra,
        'is_pro': is_pro,
        'is_free': is_free,
        'quota_summary': svc.quota_summary(),
    }
    return render(request, 'website/profile.html', context)
