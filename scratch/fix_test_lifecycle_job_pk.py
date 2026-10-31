with open('scratch/test_customer_lifecycle_e2e.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("'item_id': job.id,", "'item_id': job.pk,")

with open('scratch/test_customer_lifecycle_e2e.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated scratch/test_customer_lifecycle_e2e.py")

