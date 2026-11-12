import os

job_views_file = os.path.join('modules', 'website', 'views', 'job_api_views.py')
with open(job_views_file, 'r', encoding='utf-8') as f:
    job_code = f.read().replace('\r\n', '\n')

old_job_target = 'def job_detail_api(request, job_id):'
new_job_replacement = '''def job_detail_api(request, job_id):
    from modules.admin_panel.models import PreviewDummyJob
    is_dummy = str(job_id).startswith('DUMMY_') or str(job_id).startswith('dummy_')
    dummy_j = None
    if is_dummy:
        dummy_j = PreviewDummyJob.objects.filter(job_row_id=job_id).first()
    if not dummy_j and PreviewDummyJob.objects.filter(job_row_id=job_id).exists():
        dummy_j = PreviewDummyJob.objects.filter(job_row_id=job_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_j:
            dummy_j = PreviewDummyJob.objects.first()
        if dummy_j:
            return JsonResponse(dummy_j.as_preview_dict())'''

assert old_job_target in job_code, 'job target not found'
job_code = job_code.replace(old_job_target, new_job_replacement, 1)

with open(job_views_file, 'w', encoding='utf-8') as f:
    f.write(job_code)
print("Updated job_api_views.py")

opp_views_file = os.path.join('modules', 'website', 'views', 'opportunity_api_views.py')
with open(opp_views_file, 'r', encoding='utf-8') as f:
    opp_code = f.read().replace('\r\n', '\n')

old_csr_target = 'def csr_project_detail_api(request, csr_id):'
new_csr_replacement = '''def csr_project_detail_api(request, csr_id):
    from modules.admin_panel.models import PreviewDummyCSRProject
    is_dummy = str(csr_id).startswith('DUMMY_') or str(csr_id).startswith('dummy_')
    dummy_p = None
    if is_dummy:
        dummy_p = PreviewDummyCSRProject.objects.filter(csr_id=csr_id).first()
    if not dummy_p and PreviewDummyCSRProject.objects.filter(csr_id=csr_id).exists():
        dummy_p = PreviewDummyCSRProject.objects.filter(csr_id=csr_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_p:
            dummy_p = PreviewDummyCSRProject.objects.first()
        if dummy_p:
            return JsonResponse(dummy_p.as_preview_dict())'''

assert old_csr_target in opp_code, 'csr target not found'
opp_code = opp_code.replace(old_csr_target, new_csr_replacement, 1)

with open(opp_views_file, 'w', encoding='utf-8') as f:
    f.write(opp_code)
print("Updated opportunity_api_views.py")

