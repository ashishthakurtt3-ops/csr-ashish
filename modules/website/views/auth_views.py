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

        # Provision prototype wallet & starter subscription automatically
        try:
            from modules.website.utils.subscription_service import get_or_create_wallet
            from modules.admin_panel.models import Plan, Subscription, SubscriptionEvent
            from django.utils import timezone
            import uuid

            get_or_create_wallet(user)
            starter_plan = Plan.objects.filter(code='starter').first()
            sub_id = f"SUB_{uuid.uuid4().hex[:12].upper()}"
            now_iso = timezone.now().isoformat()
            end_iso = (timezone.now() + timezone.timedelta(days=3650)).isoformat()
            sub = Subscription.objects.create(
                subscription_id=sub_id,
                user=user,
                tenant_id=f"user_{user.id}",
                plan_record=starter_plan,
                plan_id='starter',
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
                notes=f"Community Starter plan initialized for new registration @{user.username}.",
                actor=user.username,
                created_at=now_iso
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Failed to provision starter subscription on registration: %s", e)

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
    from modules.website.utils.subscription_service import (
        get_or_create_wallet, get_plan, topup_wallet,
        toggle_auto_renew, schedule_plan_change, cancel, resume,
        rupees_to_paise
    )
    from modules.admin_panel.models import (
        Subscription, SubscriptionEvent, Payment, Invoice, WalletTransaction, Plan
    )
    from django.utils import timezone
    from datetime import timedelta

    user = request.user
    wallet = get_or_create_wallet(user)

    # Get active subscription or create fallback starter
    sub = Subscription.objects.filter(user=user, status='ACTIVE').order_by('-created_at').first()
    if not sub:
        # Check by tenant_id
        sub = Subscription.objects.filter(tenant_id=f"user_{user.id}", status='ACTIVE').order_by('-created_at').first()
        if sub and not sub.user:
            sub.user = user
            sub.save(update_fields=['user'])

    if not sub:
        plan_obj = Plan.objects.filter(code='starter').first()
        import uuid
        sub = Subscription.objects.create(
            subscription_id=f"sub_{uuid.uuid4().hex[:12]}",
            user=user,
            tenant_id=f"user_{user.id}",
            plan_record=plan_obj,
            plan_id='starter',
            status='ACTIVE',
            billing_cycle='monthly',
            auto_renew=False,
            current_period_start=timezone.now().isoformat(),
            current_period_end=(timezone.now() + timedelta(days=3650)).isoformat()
        )

    # Handle Profile Actions (Top-up, Auto-renew, Cancel, Reactivate)
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
                    messages.success(request, f"🎉 Successfully added ₹{amt:,.2f} to your prototype wallet!")
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

