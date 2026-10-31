with open('modules/website/utils/subscription_service.py','r',encoding='utf-8') as f:
    c = f.read()

old = "starter = get_plan('starter')\r\n    return [starter] if starter else []"
new = "fallback = get_plan('free') or get_plan('starter')\r\n    return [fallback] if fallback else []"

if old in c:
    c = c.replace(old, new)
    print("Replaced fallback (CRLF)")
else:
    old_lf = old.replace('\r\n', '\n')
    new_lf = new.replace('\r\n', '\n')
    if old_lf in c:
        c = c.replace(old_lf, new_lf)
        print("Replaced fallback (LF)")
    else:
        print("NOT FOUND")

# Also fix the current() function fallback
old2 = "plan = get_plan(sub.get('plan_id')) or get_plan('starter')"
new2 = "plan = get_plan(sub.get('plan_id')) or get_plan('free')"
if old2 in c:
    c = c.replace(old2, new2)
    print("Replaced current() fallback")

with open('modules/website/utils/subscription_service.py','w',encoding='utf-8') as f:
    f.write(c)
print("Done")

