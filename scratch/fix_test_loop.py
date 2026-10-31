with open('scratch/test_customer_lifecycle_e2e.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_loop = """# Save 10 records
for i in range(10):
    res = client.post('/api/user/saved-records', json.dumps({
        'item_type': 'JOB',
        'item_id': job.pk,
        'notes': f"Saved item {i}"
    }), content_type='application/json')
    # Because our model prevents duplicate saves of the same item, create dummy jobs
    dummy_job = Job.objects.create(job_id=f"JOB_E2E_{i}", company=comp, job_title=f"Role {i}")
    SavedRecord.objects.create(user=test_user, item_type='JOB', job=dummy_job)"""

new_loop = """# Cleanly save exactly 10 distinct records via API
for i in range(10):
    dummy_job = Job.objects.create(job_id=f"JOB_E2E_DISTINCT_{i}", company=comp, job_title=f"Role {i}")
    res = client.post('/api/user/saved-records', json.dumps({
        'item_type': 'JOB',
        'item_id': dummy_job.pk,
        'notes': f"Saved item {i}"
    }), content_type='application/json')
    assert res.status_code == 201"""

c = c.replace(old_loop, new_loop)

with open('scratch/test_customer_lifecycle_e2e.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Fixed distinct job loop in test_customer_lifecycle_e2e.py")

