import sqlite3
import re

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# Get all published CSR records
rows = cur.execute('''
    SELECT csr_id, company_id, project_name, category, budget, geographic_location, state, source_url, description, evidence_text
    FROM admin_panel_csrproject
    WHERE verification_status = "PUBLISHED"
    ORDER BY csr_id
''').fetchall()

print(f"Total rows currently PUBLISHED: {len(rows)}")

# Let's inspect all non-template, non-junk rows
def is_junk(name, desc):
    n = ' '.join((name or '').split()).strip()
    nl = n.lower()
    
    if not n or len(n) < 3:
        return True, "EMPTY_OR_TOO_SHORT"
        
    # Template: 'Category Initiative - Company Name'
    if re.search(r'initiative\s*[-—]\s*[A-Za-z]', n, re.IGNORECASE) or 'initiative -' in nl or 'initiative —' in nl:
        return True, "TEMPLATE_SYNTHETIC"
        
    # PDF artifacts, table fragments, page headers
    if any(x in nl for x in [
        'p a g e', '| page', 'board/cmd', 'esg data book', 'annual report 20', 
        'contents about the', '| apollo hospitals', 'data book fy', 'document no',
        'contents preface', 'fy2021-22 s', 'fy2022-23 s', 'fy2023-24 s', 'fy 2024-25 info edge',
        'fy 2025-26 sr', 'modes of implementation', 'annual action plan for csr',
        'r e c o m m e n d a t i o n s', 'statement number:', 'business responsibility & sustainability reporting',
        'disclosure questions', 'environment policy document', 'csr activities area as per sch vii',
        'bajaj auto limited (k in crore)', 'contents introduction'
    ]) or n.startswith('2 |') or n.startswith('3 |') or n.startswith('1 BUSINESS') or n.startswith('1 Annual'):
        return True, "PDF_PAGE_OR_TABLE_ARTIFACT"
        
    # Awards, accolades, ESG rankings/indices
    if any(x in nl for x in [
        'award', 'pepsico’s best', "pepsico's best", 'djsi', 'yearbook', 'msci esg', 
        'sustainalytics', 'cdp 20', 'dun & bradstreet', 'best corporate governance', 
        'golden peacock', 'cfi.co', 'terra carta seal', 'ftse4good', 'conclave 2025',
        'national energy conservation', 'most sustainable companies'
    ]):
        return True, "AWARD_OR_RANKING"
        
    # Slogans, vision statements, narrative text from reports
    if any(x in nl for x in [
        'we work for', 'concrete is the most consumed', 'management framework which has', 
        'to encourage and reward', 'want to create the future', "good health can't wait",
        'technical leaders explaining', 'key features of the sfl', 'net zero initiative',
        'water positive promise', 'zero waste to landfill', 'renewable energy transition',
        'we strengthen the communities', 'we recognize the power', 'we strive for integrity',
        'we recognize and support', 'from vision to strategy', 'blueprint for change',
        'seamless execution', 'intelligence that drives', 'transparency that builds',
        'making a lasting impact', 'performance snapshot and key highlights', 'our initiatives',
        'our efforts are being recognised', 'green parrot, social', 'read the bank\'s sustainability',
        'our esg focus areas', 'our three guiding principles', 'pact with clients', 'pact with societies',
        'pact with partners', 'the climate pledge', 'recognised by time magazine',
        'continuous automation', 'zero fragmentation', 'resilience is not a feature',
        'enterprises were not designed', 'measured in experience', 'one foundation',
        'when the foundation is built', 'leading multi-asset exchange', 'driving esg through',
        'explore the many ways', 'learn more about', 'watch how icici bank',
        'the year was also marked by an important milestone', 'synergy for green energy',
        'want to find out more', 'our spirit of progress', 'champion inclusion & diversity',
        'pioneer grain-to-glass', 'doing business therightway', 'corporate affairs and issues',
        'case study sustainability', 'mechanisms and other incidental', 'policy on remuneration',
        'policy on diversity equity', 'marico’s sustainability program', 'marico launched its sustainability',
        'building the foundations for growth', 'scaling capabilities for expansion',
        'strengthening leadership through reach', 'accelerating growth through science',
        'responsibility, built into the business', 'dear shareholders', 'corporate social responsibility practice”',
        '7 d) environment jbgvs programmes focus', 'what theatre knows: from the rehearsal',
        'sustainable financing framework', 'esg policy for lending', 'design for sustainability'
    ]) or n.startswith('We ') or n.startswith('Watch ') or n.startswith('Case Study'):
        return True, "SLOGAN_OR_REPORT_NARRATIVE"
        
    # Generic nav links, addresses, HR policies, generic headings
    if n in [
        'Social', 'About Us', 'Sustainability', 'Stakeholder Value Created', 'Quick Links', 
        'Career Development', 'Women Development', 'Early Career Development', 
        'Digital Capability Development', 'Leadership Development', 
        'Tech Enabled Employee Lifecycle Assistance', 'Equity, Diversity and Inclusion', 
        'Reducing carbon emissions', 'Enhancing trust with our stakeholders',
        'Torrent Pharmaceuticals Ltd.', 'Area Of Initiatives', 'Featured Capabilities',
        'Material Issues for Enterprise Value Creation', 'Impacts Identified', 'Key Performance Indicators',
        'Corporate Office - One Skymark, Tower-D, Plot No', 'Transparency and Disclosures Compliances 25',
        'Sustaining Growth', 'International Presence', 'Responsible Manufacturing',
        'Inclusive & Equitable Economy', 'Thriving Community', 'Healthier Planet', 'ESG Commitments',
        'Infrastructure and Facilities', 'Business Supply Chain', 'Environmental Impact', 
        'SBTi validated Net-Zero Targets', 'Environmental Leadership in Speciality Chemicals Manufacturing',
        'Occupational Health, Safety & Employee Well-Being',
        'Responsible Supply Chain and Sustainable Procurement',
        'Sustainability & ESG Initiatives in Chemical Manufacturing | Aarti Industries',
        'Dr. Sushil Shah', 'Ms. Ameera Shah', "OIL's Social Footprints", 'ESG Performance Highlights',
        'Waste Management', 'Water Management', 'Diversity and Inclusion', 'Employee Volunteering',
        'Employee Well-Being', 'Supplier Sustainability', 'Product Launches', 'Patient Assistance Programs',
        'Education and Awareness Initiatives', 'Health and safety', 'Environment and safety',
        'Sports and culture', 'Healthcare, water and sanitation', 'Sustainable livelihoods and skilling',
        'Children’s well-being and education', 'Animal welfare and community development',
        'Health & Nutrition', 'ESG data and disclosures', 'Catalysing Economic Growth',
        '12 Embroidery, Computer courses etc', 'CNG, LNG & Electric Fleets', 'Tree Plantation Drives',
        'Tech-Driven Efficiency', 'Increased Transparency & Trust', 'Eco-Friendly Warehousing'
    ] or n.startswith('Community SupportSAS') or n.startswith('Bajaj Auto Limited, Akurdi') or n.startswith('3B BLACKBIO DX LIMITED Regd') or n.startswith('— Abhishek') or n.startswith('— Sonali'):
        return True, "GENERIC_NAV_OR_POLICY_OR_TOPIC"

    # Commercial products, IT offerings, bank accounts, campus contest steps
    if n in [
        'Interior wall paints', 'Exterior Wall Paints', 'Metal enamel paints', 'Paint ancillary', 'Hygine care range',
        'Next-Gen Networks', 'Digital Workplace', 'Unified Service Management', 'Platform-Based Services',
        'Zero balance account with flexible services:', 'Instant account opening:', 'Chequebook facilities:',
        'Internet banking/digital platforms to transact:', 'Havells Product Range Is Radioactive Free',
        'ESG Data Management', 'Carbon Neutrality Roadmap', 'Data Vendor Feed & Domain Consulting', 'Double Materiality',
        'L.I.M.E & FinAce Access(For B-School)', 'TechTonic Access(For Tech-School)', 'Explore Our Brands',
        'Immersive Workshop', 'Build Your Network', 'Tell Us About Yourself', 'We Review Your Application',
        'Gamified Assessment', 'Show Us Your Potential', 'Join Foundation School',
        'Digital Foundation Services is Not a Collection of Capabilities',
        'Building A Sustainable Future: The Need For Greener Supply Chains In The Real…',
        'Building Green Homes: Planet Over Profit',
        'Embodied carbon in high rise buildings - Insights from a baselining study'
    ]:
        return True, "COMMERCIAL_OR_RECRUITMENT"

    # Operational metrics
    if re.match(r'^\d+(\.\d+)?%|^[\d\.]+\s*(bn litres|water positivity)', n, re.IGNORECASE) or 'water positivity' in nl:
        return True, "OPERATIONAL_METRIC"

    return False, "AUTHENTIC"

quarantined = []
authentic = []

for r in rows:
    cid, comp, name, cat, bud, loc, state, url, desc, evid = r
    junk, reason = is_junk(name, desc)
    if junk:
        quarantined.append((cid, comp, name, bud, reason))
    else:
        authentic.append(r)

print(f"\nQuarantined count: {len(quarantined)}")
print(f"Authentic count: {len(authentic)}")
print(f"Sum: {len(quarantined) + len(authentic)} == {len(rows)}")

print("\n--- ALL AUTHENTIC PROJECTS ---")
for p in authentic:
    cid, comp, name, cat, bud, loc, state, url, desc, evid = p
    print(f"[{cid}] ({comp}) '{name}' | Bud: {bud} | Loc: {loc} | State: {state}")
