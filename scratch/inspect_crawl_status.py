import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, CompanyCrawlSummary, PageRecord, CSRProject, Job, Contact, CSROpportunity

target_ids = [
    'COMP_TOP200_001', 'COMP_TOP200_007', 'COMP_TOP200_008', 'COMP_TOP200_011', 'COMP_TOP200_013',
    'COMP_TOP200_015', 'COMP_TOP200_016', 'COMP_TOP200_018', 'COMP_TOP200_019', 'COMP_TOP200_021',
    'COMP_TOP200_022', 'COMP_TOP200_023', 'COMP_TOP200_024', 'COMP_TOP200_027', 'COMP_TOP200_028',
    'COMP_TOP200_030', 'COMP_TOP200_032', 'COMP_TOP200_033', 'COMP_TOP200_034', 'COMP_TOP200_035',
    'COMP_TOP200_036', 'COMP_TOP200_037', 'COMP_TOP200_039', 'COMP_TOP200_040', 'COMP_TOP200_041',
    'COMP_TOP200_042', 'COMP_TOP200_043', 'COMP_TOP200_044', 'COMP_TOP200_045', 'COMP_TOP200_046',
    'COMP_TOP200_047', 'COMP_TOP200_048', 'COMP_TOP200_049', 'COMP_TOP200_050', 'COMP_TOP200_051',
    'COMP_TOP200_052', 'COMP_TOP200_053', 'COMP_TOP200_054', 'COMP_TOP200_055', 'COMP_TOP200_056',
    'COMP_TOP200_057', 'COMP_TOP200_058', 'COMP_TOP200_059', 'COMP_TOP200_060', 'COMP_TOP200_061',
    'COMP_TOP200_063', 'COMP_TOP200_064', 'COMP_TOP200_065', 'COMP_TOP200_066', 'COMP_TOP200_067',
    'COMP_TOP200_095', 'COMP_TOP200_106', 'COMP_TOP200_154', 'COMP_TOP200_199', 'COMP_TOP200_200'
]

results = []
for cid in target_ids:
    comp = Company.objects.get(company_id=cid)
    summ = CompanyCrawlSummary.objects.filter(company=comp).first()
    pages = PageRecord.objects.filter(company=comp)
    page_statuses = list(set(pages.values_list('status', flat=True)))
    st = summ.crawl_status if summ else (comp.crawl_status or 'UNTRACKED')
    
    pub_csr = CSRProject.objects.filter(company=comp, verification_status='PUBLISHED').count()
    pub_jobs = Job.objects.filter(company=comp, verification_status='PUBLISHED').count()
    pub_opps = CSROpportunity.objects.filter(company=comp).exclude(verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED']).count()
    pub_contacts = Contact.objects.filter(company=comp, verification_status='PUBLISHED').count()
    
    results.append({
        'cid': cid,
        'name': comp.company_name,
        'status': st,
        'pages_count': pages.count(),
        'page_statuses': page_statuses,
        'error_log': (summ.error_log[:60] if summ and summ.error_log else None),
        'ats': summ.ats_platform if summ else comp.ats_platform,
        'pub_csr': pub_csr,
        'pub_jobs': pub_jobs,
        'pub_opps': pub_opps,
        'pub_contacts': pub_contacts,
    })

print(f"Total surveyed companies: {len(results)}")
status_dist = {}
for r in results:
    s = r['status']
    status_dist[s] = status_dist.get(s, 0) + 1
print("Status distribution:", status_dist)

for r in results:
    err = f" | Err: {r['error_log']}" if r['error_log'] else ""
    print(f"{r['cid']} | {r['name'][:24]} | Status: {r['status']:<16} | Pages: {r['pages_count']:<2} {r['page_statuses']} | CSR: {r['pub_csr']} | Jobs: {r['pub_jobs']} | Opps: {r['pub_opps']} | Contacts: {r['pub_contacts']}{err}")
