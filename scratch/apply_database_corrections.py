import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import CSRProject, CSROpportunity, Contact, AuditTrail

print("=== VERIFYING BEFORE AUDIT CORRECTIONS ===")
print("CSRProject published count:", CSRProject.objects.filter(verification_status='PUBLISHED').count())
print("CSROpportunity non-legacy count:", CSROpportunity.objects.exclude(verification_status__in=['LEGACY_UNVERIFIED']).count())
print("Contact published count:", Contact.objects.filter(verification_status='PUBLISHED').count())

# 1. Reject the 4 UltraTech homebuilder commercial tools (974, 975, 976, 977)
commercial_ids = [974, 975, 976, 977]
for pid in commercial_ids:
    p = CSRProject.objects.get(csr_id=pid)
    print(f"Updating Project {pid} ({p.project_name}): PUBLISHED -> REJECTED")
    p.verification_status = 'REJECTED'
    p.verification_reason = 'Excluded during audit: Commercial homebuilder web utility (Cost Calculator/EMI/Store Locator), not a CSR initiative.'
    p.save(update_fields=['verification_status', 'verification_reason'])

# 2. Project 993: Update budget to None, documenting turnover rate extraction error
p993 = CSRProject.objects.get(csr_id=993)
print(f"Updating Project 993 budget: {p993.budget} -> None (turnover rate artifact)")
p993.budget = None
p993.verification_reason = "Forensic audit finding: 'rs 6.5' was extracted from Page 4 Item 22 'Permanent Workers 6.5%' employee turnover rate, not CSR expenditure. Original value preserved in audit trail."
p993.save(update_fields=['budget', 'verification_reason'])

# 3. Correct CSR Opportunities
# Video tutorials (141, 142, 143) -> REJECTED
for oid in [141, 142, 143]:
    o = CSROpportunity.objects.get(opp_id=oid)
    print(f"Updating Opp {oid} ({o.title[:30]}): EXTRACTED -> REJECTED")
    o.verification_status = 'REJECTED'
    o.verification_reason = 'Excluded during audit: Homebuilder instructional video landing page, not a CSR opportunity.'
    o.save(update_fields=['verification_status', 'verification_reason'])

# Commercial customer / merchant forms (136, 146) -> REJECTED
for oid, reason in [
    (136, 'Excluded during audit: Commercial merchant/partner intake form, not a CSR grant/RFP.'),
    (146, 'Excluded during audit: Retail insurance policy proposal form download, not a CSR grant/RFP.')
]:
    o = CSROpportunity.objects.get(opp_id=oid)
    print(f"Updating Opp {oid} ({o.title[:30]}): EXTRACTED -> REJECTED")
    o.verification_status = 'REJECTED'
    o.verification_reason = reason
    o.save(update_fields=['verification_status', 'verification_reason'])

# Localized duplicates (149, 150) -> REJECTED
for oid in [149, 150]:
    o = CSROpportunity.objects.get(opp_id=oid)
    t_safe = o.title[:30].encode('ascii', 'replace').decode('ascii')
    print(f"Updating Opp {oid} ({t_safe}): EXTRACTED -> REJECTED")
    o.verification_status = 'REJECTED'
    o.verification_reason = 'Excluded during audit: Duplicate localized Hindi procurement notice.'
    o.save(update_fields=['verification_status', 'verification_reason'])

# Legitimate procurement notices -> set opportunity_type = 'Procurement / Vendor EOI'
for oid in [137, 138, 139, 144, 145, 147, 148]:
    o = CSROpportunity.objects.get(opp_id=oid)
    o.opportunity_type = 'Procurement / Vendor EOI'
    o.category = 'Procurement & Supply Chain'
    o.verification_reason = 'B2B Commercial procurement notice / supplier EOI (non-CSR).'
    o.save(update_fields=['opportunity_type', 'category', 'verification_reason'])

# Genuine CSR RFP (140) -> set opportunity_type = 'Grant / RFP'
o140 = CSROpportunity.objects.get(opp_id=140)
o140.opportunity_type = 'Grant / RFP'
o140.category = 'Social Impact Assessment'
o140.verification_reason = 'Verified CSR RFP for Social Impact Assessment.'
o140.save(update_fields=['opportunity_type', 'category', 'verification_reason'])

# 4. Correct Contacts: flag duplicates 837 and 844
for cid, reason in [
    (837, 'Excluded during audit: Duplicate phone number of Contact 831 (Polycab India).'),
    (844, 'Excluded during audit: Duplicate phone number of Contact 842 (Apollo Hospitals).')
]:
    c = Contact.objects.get(contact_id=cid)
    print(f"Updating Contact {cid}: PUBLISHED -> REJECTED ({reason})")
    c.verification_status = 'REJECTED'
    c.verification_reason = reason
    c.save(update_fields=['verification_status', 'verification_reason'])

print("\n=== VERIFYING AFTER AUDIT CORRECTIONS ===")
print("CSRProject published count (eligible public):", CSRProject.objects.filter(verification_status='PUBLISHED').count())
print("CSRProject rejected count:", CSRProject.objects.filter(verification_status='REJECTED').count())
print("CSRProject total in DB:", CSRProject.objects.count())
print("CSROpportunity active non-legacy:", CSROpportunity.objects.exclude(verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED']).count())
print("Contact published non-duplicate channels:", Contact.objects.filter(verification_status='PUBLISHED').count())
