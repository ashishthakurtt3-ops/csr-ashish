import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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

    companies = list(Company.objects.values())
    all_projects = list(CSRProject.objects.values())

    comp_projects = {}
    for p in all_projects:
        cid = p['company_id']
        if cid not in comp_projects:
            comp_projects[cid] = []
        comp_projects[cid].append(p)

    results = []
    for comp in companies:
        cid = comp['company_id']
        projects = comp_projects.get(cid, [])
        match_data = calculate_ngo_match(comp, projects, profile, weights)
        results.append(match_data)

    results.sort(key=lambda x: x['match_score'], reverse=True)
    return JsonResponse(results[:limit], safe=False)
