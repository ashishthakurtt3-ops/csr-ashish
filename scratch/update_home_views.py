path = 'modules/website/views/home_views.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        if user_sub:
            sub_status = (user_sub.status or 'INACTIVE').upper()
            is_sub_active = sub_status in ('ACTIVE', 'TRIALING')
            plan_tier = (user_sub.plan_id or 'free').upper()
            if is_sub_active:
                plan_tier_label = f"{plan_tier} Active"
            elif sub_status == 'EXPIRED':
                plan_tier_label = f"{plan_tier} Expired"
            elif sub_status in ('CANCELED', 'CANCELLED'):
                plan_tier_label = f"{plan_tier} Cancelled"
            else:
                plan_tier_label = f"{plan_tier} ({sub_status})"
        elif request.user.is_staff or request.user.is_superuser:"""

replacement = """        trial_days_remaining = None
        if user_sub:
            if user_sub.current_period_end:
                from datetime import datetime, timezone
                try:
                    text = str(user_sub.current_period_end).replace('Z', '+00:00')
                    end_dt = datetime.fromisoformat(text)
                    if not end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    if now_utc >= end_dt:
                        if user_sub.status != 'EXPIRED':
                            user_sub.status = 'EXPIRED'
                            user_sub.save(update_fields=['status'])
                    else:
                        trial_days_remaining = max(0, (end_dt - now_utc).days)
                except Exception:
                    pass

            sub_status = (user_sub.status or 'INACTIVE').upper()
            is_sub_active = sub_status in ('ACTIVE', 'TRIALING')
            plan_tier = (user_sub.plan_id or 'free').upper()
            if is_sub_active:
                if sub_status == 'TRIALING':
                    days_text = f"{trial_days_remaining}d remaining" if trial_days_remaining is not None else "14d remaining"
                    plan_tier_label = f"14-Day Free Trial ({days_text})"
                else:
                    plan_tier_label = f"{plan_tier} Active"
            elif sub_status == 'EXPIRED':
                plan_tier_label = f"{plan_tier} Expired"
            elif sub_status in ('CANCELED', 'CANCELLED'):
                plan_tier_label = f"{plan_tier} Cancelled"
            else:
                plan_tier_label = f"{plan_tier} ({sub_status})"
        elif request.user.is_staff or request.user.is_superuser:"""

assert target in content, 'target not found in home_views.py'
content = content.replace(target, replacement, 1)

# Add trial_days_remaining to context
target_ctx = "'plan_tier_label': plan_tier_label,"
replacement_ctx = "'plan_tier_label': plan_tier_label,\n        'trial_days_remaining': trial_days_remaining,"

assert target_ctx in content, 'target_ctx not found in home_views.py'
content = content.replace(target_ctx, replacement_ctx, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated home_views.py")

