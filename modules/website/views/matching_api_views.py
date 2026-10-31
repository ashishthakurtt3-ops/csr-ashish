import json
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from modules.admin_panel.models import Company, CSRProject
from modules.website.utils.scoring_service import calculate_ngo_match


@csrf_exempt
def match_ngo_api(request):
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = {}
        profile = payload.get('profile', {})
        weights = payload.get('weights', None)
        limit = int(payload.get('limit', 50))
    else:
        # GET request support
        sectors_str = request.GET.get('sector', '').strip()
        state = request.GET.get('state', '').strip()
        profile = {
            'sectors': [s.strip() for s in sectors_str.split(',') if s.strip()] if sectors_str else [],
            'state': state
        }
        weights = None
        limit = int(request.GET.get('limit', 50))

    # Cache key based on profile, weights and limit
    cache_str = f"{','.join(sorted(profile.get('sectors', [])))}_{profile.get('state', '')}_{profile.get('budget', '')}_{weights}_{limit}"
    cache_key = f"ngo_match_{hashlib.md5(cache_str.encode('utf-8')).hexdigest()}"
    cached_res = cache.get(cache_key)
    if cached_res is not None:
        return JsonResponse(cached_res, safe=False)

    # Precompute / cache base inputs (companies and CSR projects) for 10 minutes
    base_data = cache.get('ngo_matching_base_data')
    if base_data is None:
        companies = list(Company.objects.values(
            'company_id', 'company_name', 'nse_symbol', 'sector', 'website_url', 'csr_portal_url'
        ))
        all_projects = list(CSRProject.objects.values(
            'company_id', 'category', 'state', 'geographic_location'
        ))

        comp_projects = {}
        for p in all_projects:
            cid = p['company_id']
            if cid not in comp_projects:
                comp_projects[cid] = []
            comp_projects[cid].append(p)
        base_data = {'companies': companies, 'projects': comp_projects}
        cache.set('ngo_matching_base_data', base_data, 600)
    else:
        companies = base_data['companies']
        comp_projects = base_data['projects']

    results = []
    for comp in companies:
        cid = comp['company_id']
        projects = comp_projects.get(cid, [])
        match_data = calculate_ngo_match(comp, projects, profile, weights)
        results.append(match_data)

    results.sort(key=lambda x: x['match_score'], reverse=True)
    out = results[:limit]
    cache.set(cache_key, out, 600)
    return JsonResponse(out, safe=False)
