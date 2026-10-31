with open('scratch/test_customer_lifecycle_e2e.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("res_pro_exp = client.get('/api/jobs?export=csv')", "res_pro_exp = client.get('/api/jobs?export=csv&limit=50')")

with open('scratch/test_customer_lifecycle_e2e.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated scratch/test_customer_lifecycle_e2e.py with limit=50")

