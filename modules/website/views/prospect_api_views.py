import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from modules.admin_panel.models import Prospect, Company, Contact, OpportunityScore, AuditTrail
from modules.website.utils.pagination import paginate_queryset


from modules.admin_panel.verification import (
    PUBLIC_VERIFICATION_STATUSES, public_jobs, public_job_q, NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT, LINK_OK,
)

def serialize_prospect_item(p: Prospect):
    c = p.company
    score_obj = getattr(c, 'score_record', None)
    verified_contact = c.contacts.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)).first()

    return {
        'prospect_id': p.prospect_id,
        'company_id': p.company_id,
        'company_name': c.company_name,
        'nse_symbol': c.nse_symbol,
        'website_url': c.website_url,
        'sector': c.sector,
        'stage': p.stage,
        'notes': p.notes,
        'assigned_to': p.assigned_to,
        'target_proposal': p.target_proposal,
        'follow_up_date': p.follow_up_date,
        'match_score': p.match_score,
        'opportunity_score': score_obj.score if score_obj else 0.0,
        'contact_email': verified_contact.email if verified_contact else None,
        'created_at': p.created_at,
        'updated_at': p.updated_at,
    }


@csrf_exempt
def prospects_api(request, company_id=None):
    if request.method == 'GET':
        stage = request.GET.get('stage', '').strip()
        page = request.GET.get('page')
        page_size = request.GET.get('page_size', 10)

        qs = Prospect.objects.select_related('company', 'company__score_record').prefetch_related('company__contacts').all()
        if stage and stage != 'all':
            qs = qs.filter(stage=stage)

        qs = qs.order_by('-updated_at')

        data = paginate_queryset(
            queryset=qs,
            serialize_func=serialize_prospect_item,
            page=page,
            page_size=page_size
        )
        return JsonResponse(data, safe=False)

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = {}

        cid = payload.get('company_id')
        if not cid:
            return JsonResponse({'detail': 'Missing company_id'}, status=400)

        try:
            comp = Company.objects.get(company_id=cid)
        except Company.DoesNotExist:
            return JsonResponse({'detail': f'Company {cid} not found'}, status=404)

        stage = payload.get('stage', 'Shortlisted')
        notes = payload.get('notes', 'Added from Opportunity Radar.')
        assigned = payload.get('assigned_to', 'NGO CSR Team')
        proposal = payload.get('target_proposal', 'General Partnership Brief')
        fdate = payload.get('follow_up_date', '')
        score_obj = getattr(comp, 'score_record', None)
        match_score = float(payload['match_score']) if 'match_score' in payload and payload['match_score'] is not None else (float(score_obj.score) if score_obj else 0.0)
        now_ts = timezone.now().isoformat()

        prospect, created = Prospect.objects.update_or_create(
            company=comp,
            defaults={
                'stage': stage,
                'notes': notes,
                'assigned_to': assigned,
                'target_proposal': proposal,
                'follow_up_date': fdate,
                'match_score': match_score,
                'updated_at': now_ts,
            }
        )
        if created:
            prospect.created_at = now_ts
            prospect.save()

        AuditTrail.objects.create(
            record_type='PROSPECT',
            record_id=cid,
            action='ADD_TO_PIPELINE',
            new_value=stage,
            user_role='NGO Admin',
            notes=f"Added company {cid} to outreach pipeline.",
            timestamp=now_ts
        )

        return JsonResponse({'status': 'success', 'message': f'Company {cid} added to prospects pipeline.'})

    elif request.method in ('PUT', 'PATCH'):
        if not company_id:
            return JsonResponse({'detail': 'Missing company_id in URL'}, status=400)

        try:
            prospect = Prospect.objects.get(company_id=company_id)
        except Prospect.DoesNotExist:
            return JsonResponse({'detail': 'Prospect not found'}, status=404)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = {}

        prev_stage = prospect.stage
        prospect.stage = payload.get('stage', prospect.stage)
        prospect.notes = payload.get('notes', prospect.notes)
        prospect.assigned_to = payload.get('assigned_to', prospect.assigned_to)
        prospect.follow_up_date = payload.get('follow_up_date', prospect.follow_up_date)
        prospect.updated_at = timezone.now().isoformat()
        prospect.save()

        AuditTrail.objects.create(
            record_type='PROSPECT',
            record_id=company_id,
            action='UPDATE_STAGE',
            previous_value=prev_stage,
            new_value=prospect.stage,
            user_role='NGO Admin',
            notes=prospect.notes,
            timestamp=prospect.updated_at
        )

        return JsonResponse({'status': 'success', 'message': f'Prospect {company_id} updated.'})

    elif request.method == 'DELETE':
        if not company_id:
            return JsonResponse({'detail': 'Missing company_id in URL'}, status=400)

        Prospect.objects.filter(company_id=company_id).delete()
        return JsonResponse({'status': 'success', 'message': 'Prospect removed.'})

    return JsonResponse({'detail': 'Method not allowed'}, status=405)
