with open('static/js/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

old_fn = """function normalizeSubscriptionTier(tierOrPlan) {
    if (!tierOrPlan) return 'starter';
    const s = String(tierOrPlan).trim().toLowerCase();
    if (s === 'starter' || s === 'free') return 'starter';
    if (s === 'pro') return 'pro';
    if (s === 'enterprise' || s === 'ultra') return 'enterprise';
    if (s === 'foundation' || s === 'api') return 'foundation';
    return s;
}"""

new_fn = """function normalizeSubscriptionTier(tierOrPlan) {
    if (!tierOrPlan) return 'free';
    const s = String(tierOrPlan).trim().toLowerCase();
    if (s === 'starter' || s === 'free' || s === 'community_free') return 'free';
    if (s === 'pro') return 'pro';
    if (s === 'enterprise' || s === 'ultra' || s === 'foundation' || s === 'api') return 'ultra';
    return s;
}"""

for le in ['\r\n', '\n']:
    tgt = old_fn.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_fn.replace('\n', le))
        print("Updated normalizeSubscriptionTier in app.js successfully")
        break
else:
    print("WARNING: Could not find old_fn in app.js")

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")

