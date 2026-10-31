with open('modules/website/views/subscription_api_views.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_block = """        kwargs = {'user': user, 'item_type': item_type, 'notes': notes}
        if item_type == 'JOB':
            kwargs['job_id'] = int(item_id)
        elif item_type == 'CSR_PROJECT':
            kwargs['csr_project_id'] = int(item_id)

        # Prevent duplicate saves
        existing = SavedRecord.objects.filter(
            user=user, item_type=item_type,
            **({'job_id': kwargs.get('job_id')} if item_type == 'JOB' else {'csr_project_id': kwargs.get('csr_project_id')})
        ).first()"""

new_block = """        from modules.admin_panel.models import Job, CSRProject
        kwargs = {'user': user, 'item_type': item_type, 'notes': notes}
        if item_type == 'JOB':
            j_obj = Job.objects.filter(pk=item_id).first() or Job.objects.filter(job_id=str(item_id)).first()
            if not j_obj:
                return JsonResponse({'detail': 'Job opening not found.', 'code': 'not_found'}, status=404)
            kwargs['job'] = j_obj
        elif item_type == 'CSR_PROJECT':
            c_obj = CSRProject.objects.filter(pk=item_id).first() or CSRProject.objects.filter(csr_id=str(item_id)).first()
            if not c_obj:
                return JsonResponse({'detail': 'CSR project not found.', 'code': 'not_found'}, status=404)
            kwargs['csr_project'] = c_obj

        # Prevent duplicate saves
        existing = SavedRecord.objects.filter(
            user=user, item_type=item_type,
            **({'job': kwargs.get('job')} if item_type == 'JOB' else {'csr_project': kwargs.get('csr_project')})
        ).first()"""

for le in ['\r\n', '\n']:
    tgt = old_block.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_block.replace('\n', le))
        print("Updated saved_records_api lookup in subscription_api_views.py")
        break
else:
    print("WARNING: Could not update saved_records_api lookup")

with open('modules/website/views/subscription_api_views.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")

