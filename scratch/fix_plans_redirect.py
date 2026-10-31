# 1. Update subscription_views.py
with open('modules/admin_panel/views/subscription_views.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("redirect('admin_subscriptions:plans')", "redirect('admin_subscriptions:plans_list')")

with open('modules/admin_panel/views/subscription_views.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated redirects in subscription_views.py")

# 2. Update subscription_urls.py to also provide name='plans'
with open('modules/admin_panel/urls/subscription_urls.py', 'r', encoding='utf-8') as f:
    u = f.read()

if "name='plans'" not in u:
    u = u.replace(
        "path('plans/', plan_list_view, name='plans_list'),",
        "path('plans/', plan_list_view, name='plans_list'),\n    path('plans/catalog/', plan_list_view, name='plans'),"
    )
    with open('modules/admin_panel/urls/subscription_urls.py', 'w', encoding='utf-8') as f:
        f.write(u)
    print("Added name='plans' alias to subscription_urls.py")

