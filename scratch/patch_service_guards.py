import os

path = r'modules\website\utils\subscription_service.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. topup_wallet guard
topup_old = """def topup_wallet(user: User, amount_paise: int, payment_method: str = 'WALLET_TOPUP',
                 description: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    if amount_paise <= 0:"""

topup_new = """def topup_wallet(user: User, amount_paise: int, payment_method: str = 'WALLET_TOPUP',
                 description: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    from django.conf import settings
    if not getattr(settings, 'ALLOW_PROTOTYPE_PAYMENTS', False):
        raise SubscriptionError('Prototype wallet top-up is disabled in production mode. A live payment gateway must be configured.', 403, 'prototype_payments_disabled')
    if amount_paise <= 0:"""

assert topup_old in text, 'topup_old not found'
text = text.replace(topup_old, topup_new, 1)

# 2. checkout direct prototype guard
checkout_proto_old = """            else:
                # Other prototype payment methods (UPI, Card, NetBanking, etc.)
                pay_id = f"PAY_{uuid.uuid4().hex[:12].upper()}\""""

checkout_proto_new = """            else:
                from django.conf import settings
                if not getattr(settings, 'ALLOW_PROTOTYPE_PAYMENTS', False):
                    raise SubscriptionError('Direct prototype payment methods are disabled in production mode. A live payment gateway must be configured.', 403, 'prototype_payments_disabled')
                # Other prototype payment methods (UPI, Card, NetBanking, etc.)
                pay_id = f"PAY_{uuid.uuid4().hex[:12].upper()}\""""

assert checkout_proto_old in text, 'checkout_proto_old not found'
text = text.replace(checkout_proto_old, checkout_proto_new, 1)

# 3. renewal auto_renew off expiry
renew_off_old = """        # Check if auto_renew is OFF
        if not sub.auto_renew:
            starter_plan = Plan.objects.filter(code='starter').first()
            sub.status = _STATUS_EXPIRED
            sub.plan_record = starter_plan
            sub.plan_id = 'starter'
            sub.save(update_fields=['status', 'plan_record', 'plan_id', 'updated_at'])
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                event_type='EXPIRED', from_plan=pid, to_plan='starter',"""

renew_off_new = """        # Check if auto_renew is OFF
        if not sub.auto_renew:
            free_plan = Plan.objects.filter(code='free', is_active=True).first() or Plan.objects.filter(code='starter').first()
            sub.status = _STATUS_EXPIRED
            sub.plan_record = free_plan
            sub.plan_id = free_plan.code if free_plan else 'free'
            sub.save(update_fields=['status', 'plan_record', 'plan_id', 'updated_at'])
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                event_type='EXPIRED', from_plan=pid, to_plan='free',"""

assert renew_off_old in text, 'renew_off_old not found'
text = text.replace(renew_off_old, renew_off_new, 1)

# 4. renewal failure count >= 3 expiry
fail_3_old = """                if sub.renewal_failure_count >= 3:
                    # Grace period expired: downgrade to starter
                    starter_plan = Plan.objects.filter(code='starter').first()
                    sub.status = _STATUS_EXPIRED
                    sub.plan_record = starter_plan
                    sub.plan_id = 'starter'
                    SubscriptionEvent.objects.create(
                        subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                        event_type='EXPIRED', from_plan=pid, to_plan='starter',"""

fail_3_new = """                if sub.renewal_failure_count >= 3:
                    # Grace period expired: downgrade to free tier
                    free_plan = Plan.objects.filter(code='free', is_active=True).first() or Plan.objects.filter(code='starter').first()
                    sub.status = _STATUS_EXPIRED
                    sub.plan_record = free_plan
                    sub.plan_id = free_plan.code if free_plan else 'free'
                    SubscriptionEvent.objects.create(
                        subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                        event_type='EXPIRED', from_plan=pid, to_plan='free',"""

assert fail_3_old in text, 'fail_3_old not found'
text = text.replace(fail_3_old, fail_3_new, 1)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)

print('Successfully patched subscription_service.py with guards and free-plan fallbacks')

