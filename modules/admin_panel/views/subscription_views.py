from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from modules.admin_panel.models import Subscription, Invoice, PromoCode, SubscriptionEvent


@login_required
def subscription_list_view(request):
    plan_id = request.GET.get('plan', '').strip()
    status = request.GET.get('status', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Subscription.objects.all().order_by('-created_at')
    if plan_id and plan_id != 'all':
        qs = qs.filter(plan_id=plan_id)
    if status and status != 'all':
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/subscriptions/list.html', {
        'page_obj': page_obj,
        'selected_plan': plan_id,
        'selected_status': status,
        'total_count': paginator.count
    })


@login_required
def invoice_list_view(request):
    page_num = request.GET.get('page', 1)
    qs = Invoice.objects.all().order_by('-issued_at', '-invoice_id')
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/subscriptions/invoices.html', {
        'page_obj': page_obj,
        'total_count': paginator.count
    })


@login_required
def promo_code_list_view(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        pct = int(request.POST.get('percent_off', 10))
        max_r = request.POST.get('max_redemptions')
        desc = request.POST.get('description', '').strip()

        if code:
            PromoCode.objects.update_or_create(
                code=code,
                defaults={
                    'percent_off': pct,
                    'max_redemptions': int(max_r) if max_r else None,
                    'description': desc,
                    'active': True
                }
            )
            messages.success(request, f"Promo code '{code}' saved.")
            return redirect('admin_subscriptions:promos')

    promos = PromoCode.objects.all().order_by('code')
    return render(request, 'admin/subscriptions/promos.html', {'promos': promos})
