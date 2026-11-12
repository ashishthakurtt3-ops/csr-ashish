import os

path = 'modules/website/utils/entitlement_service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """            self._subscription = (
                Subscription.objects
                .filter(q, Q(status='ACTIVE') | Q(status='TRIALING'))
                .select_related('plan_record')
                .order_by('-created_at')
                .first()
            )"""

replacement1 = """            sub = (
                Subscription.objects
                .filter(q, Q(status='ACTIVE') | Q(status='TRIALING'))
                .select_related('plan_record')
                .order_by('-created_at')
                .first()
            )
            if sub and sub.current_period_end:
                from datetime import datetime, timezone
                try:
                    text = str(sub.current_period_end).replace('Z', '+00:00')
                    end_dt = datetime.fromisoformat(text)
                    if not end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) >= end_dt:
                        sub.status = 'EXPIRED'
                        sub.save(update_fields=['status'])
                        sub = None
                except Exception:
                    pass
            self._subscription = sub"""

assert target1 in content, 'target1 not found in entitlement_service.py'
content = content.replace(target1, replacement1, 1)

target2 = """def user_has_active_plan(user) -> bool:
    \"\"\"
    Check whether a user has an active, selected subscription plan.
    - Staff/superusers always return True (admin bypass).
    - Unauthenticated users return False.
    - Regular users return True ONLY if they have an active/trialing subscription.
    \"\"\"
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True

    from modules.admin_panel.models import Subscription
    from django.db.models import Q

    return Subscription.objects.filter(
        Q(user=user) | Q(tenant_id=f"user_{user.id}") | Q(tenant_id=f"user_{getattr(user, 'username', '')}"),
        status__in=['ACTIVE', 'TRIALING']
    ).exclude(plan_id__isnull=True).exclude(plan_id__exact='').exists()"""

replacement2 = """def user_has_active_plan(user) -> bool:
    \"\"\"
    Check whether a user has an active, selected subscription plan.
    - Staff/superusers always return True (admin bypass).
    - Unauthenticated users return False.
    - Regular users return True ONLY if they have an active/trialing subscription that has not expired.
    \"\"\"
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True

    from modules.admin_panel.models import Subscription
    from django.db.models import Q
    from datetime import datetime, timezone

    subs = Subscription.objects.filter(
        Q(user=user) | Q(tenant_id=f"user_{user.id}") | Q(tenant_id=f"user_{getattr(user, 'username', '')}"),
        status__in=['ACTIVE', 'TRIALING']
    ).exclude(plan_id__isnull=True).exclude(plan_id__exact='').order_by('-created_at')

    now = datetime.now(timezone.utc)
    for sub in subs:
        if sub.current_period_end:
            try:
                text = str(sub.current_period_end).replace('Z', '+00:00')
                end_dt = datetime.fromisoformat(text)
                if not end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                if now >= end_dt:
                    sub.status = 'EXPIRED'
                    sub.save(update_fields=['status'])
                    continue
            except Exception:
                pass
        return True

    return False"""

assert target2 in content, 'target2 not found in entitlement_service.py'
content = content.replace(target2, replacement2, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated entitlement_service.py")

