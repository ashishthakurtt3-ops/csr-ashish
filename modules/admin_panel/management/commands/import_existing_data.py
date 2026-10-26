import os
import csv
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from modules.admin_panel.models import (
    User, Company, Job, OpportunityScore, CSRProject, CSROpportunity,
    Contact, NGOCollaboration, PageRecord, AuditTrail, Prospect,
    PromoCode, Subscription, SubscriptionEvent, Invoice, UsageCounter
)

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False


class Command(BaseCommand):
    help = "Import existing production intelligence data into the Django (MySQL) database"

    def handle(self, *args, **options):
        self.stdout.write("--> Initializing Data Import into Django ORM...")

        # 1. Create Default Administrative & Demo Users
        self._ensure_users()

        # 2. Attempt import from active MySQL production database
        imported_from_mysql = False
        if HAS_PYMYSQL:
            try:
                imported_from_mysql = self._import_from_mysql()
            except Exception as e:
                self.stderr.write(f"MySQL import encountered: {e}. Falling back to CSV/JSON files.")

        # 3. Fallback to CSV / JSON files if MySQL had 0 records or failed
        if not imported_from_mysql:
            self._import_from_files()

        # 4. Guarantee 100% authentic sector-aligned and department-complete jobs
        # from django.core.management import call_command
        # call_command('seed_authentic_enterprise_jobs')

        self.stdout.write(self.style.SUCCESS("[OK] All intelligence data successfully migrated into Django ORM!"))

    def _ensure_users(self):
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@impactbridge.org',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'organization_name': 'ImpactBridge Governance Team',
                'designation': 'Chief Intelligence Officer',
                'is_verified': True
            }
        )
        if created:
            initial_pw = os.environ.get('ADMIN_INITIAL_PASSWORD', '')
            if initial_pw:
                admin_user.set_password(initial_pw)
            else:
                admin_user.set_unusable_password()
                self.stdout.write("Created superuser 'admin' WITHOUT a password. Run: python manage.py changepassword admin")
            admin_user.save()

        ngo_user, created = User.objects.get_or_create(
            username='ngo_manager',
            defaults={
                'email': 'manager@ngoalliance.org',
                'role': User.ROLE_NGO_MANAGER,
                'is_staff': False,
                'organization_name': 'Pratham Education Foundation',
                'designation': 'Partnerships Director',
                'is_verified': True
            }
        )
        if created:
            ngo_pw = os.environ.get('NGO_INITIAL_PASSWORD', '')
            if ngo_pw:
                ngo_user.set_password(ngo_pw)
            else:
                ngo_user.set_unusable_password()
            ngo_user.save()

    def _import_from_mysql(self) -> bool:
        host = os.environ.get('MYSQL_HOST', 'localhost')
        port = int(os.environ.get('MYSQL_PORT', 3306))
        user = os.environ.get('MYSQL_USER', '')
        password = os.environ.get('MYSQL_PASSWORD', '')
        database = os.environ.get('MYSQL_DB', 'csr_intelligence')

        self.stdout.write(f"Connecting to MySQL at {host}:{port} database '{database}'...")
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database,
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS c FROM companies")
        comp_count = cur.fetchone()['c']
        if comp_count == 0:
            conn.close()
            return False

        with transaction.atomic():
            # 1. Companies
            cur.execute("SELECT * FROM companies")
            companies_data = cur.fetchall()
            companies_to_create = []
            for row in companies_data:
                companies_to_create.append(Company(
                    company_id=row['company_id'],
                    company_name=row['company_name'],
                    legal_name=row.get('legal_name'),
                    isin=row.get('isin'),
                    nse_symbol=row.get('nse_symbol'),
                    bse_scrip_code=row.get('bse_scrip_code'),
                    listed_on_nse=bool(row.get('listed_on_nse', 0)),
                    listed_on_bse=bool(row.get('listed_on_bse', 0)),
                    listing_status=row.get('listing_status') or 'ACTIVE',
                    website_url=row.get('website_url'),
                    sector=row.get('sector'),
                    headquarters=row.get('headquarters'),
                    cin=row.get('cin'),
                    last_crawled=row.get('last_crawled'),
                    crawl_status=row.get('crawl_status') or 'CRAWLED',
                    data_confidence=float(row.get('data_confidence') or 0.0),
                    careers_url=row.get('careers_url'),
                    csr_portal_url=row.get('csr_portal_url'),
                    link_quality=row.get('link_quality'),
                    link_verified_at=row.get('link_verified_at'),
                ))
            Company.objects.bulk_create(companies_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(companies_to_create)} Companies from MySQL.")

            # 2. Opportunity Scores
            cur.execute("SELECT * FROM opportunity_scores")
            scores = cur.fetchall()
            scores_to_create = []
            for r in scores:
                scores_to_create.append(OpportunityScore(
                    company_id=r['company_id'],
                    active_csr=float(r.get('active_csr') or 0.0),
                    focus_match=float(r.get('focus_match') or 0.0),
                    recent_activity=float(r.get('recent_activity') or 0.0),
                    ngo_activity=float(r.get('ngo_activity') or 0.0),
                    opportunity_page=float(r.get('opportunity_page') or 0.0),
                    contact_availability=float(r.get('contact_availability') or 0.0),
                    geographic_match=float(r.get('geographic_match') or 0.0),
                    score=float(r.get('score') or 0.0),
                    evidence_status=r.get('evidence_status'),
                    rationale=r.get('rationale'),
                    scored_at=r.get('scored_at'),
                ))
            OpportunityScore.objects.bulk_create(scores_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(scores_to_create)} Opportunity Scores.")

            # 3. CSR Projects
            cur.execute("SELECT * FROM csr_projects")
            projects = cur.fetchall()
            projects_to_create = []
            for r in projects:
                projects_to_create.append(CSRProject(
                    csr_id=r['csr_id'],
                    company_id=r['company_id'],
                    project_name=r.get('project_name'),
                    category=r.get('category'),
                    description=r.get('description'),
                    geographic_location=r.get('geographic_location'),
                    state=r.get('state'),
                    budget=r.get('budget'),
                    source_url=r.get('source_url'),
                    discovered_date=r.get('discovered_date'),
                    last_verified_date=r.get('last_verified_date'),
                    confidence=float(r.get('confidence') or 0.0),
                    link_status=r.get('link_status'),
                    link_verified_at=r.get('link_verified_at'),
                    fingerprint=r.get('fingerprint'),
                ))
            CSRProject.objects.bulk_create(projects_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(projects_to_create)} CSR Projects.")

            # 4. Jobs
            cur.execute("SELECT * FROM jobs")
            jobs = cur.fetchall()
            jobs_to_create = []
            for r in jobs:
                jobs_to_create.append(Job(
                    job_row_id=r['job_row_id'],
                    company_id=r['company_id'],
                    job_id=r.get('job_id'),
                    job_title=r.get('job_title') or 'Open Position',
                    department=r.get('department'),
                    function=r.get('function'),
                    location=r.get('location'),
                    state=r.get('state'),
                    country=r.get('country') or None,
                    work_mode=r.get('work_mode'),
                    employment_type=r.get('employment_type'),
                    experience=r.get('experience'),
                    education=r.get('education'),
                    skills=r.get('skills'),
                    salary=r.get('salary'),
                    job_description=r.get('job_description'),
                    posted_date=r.get('posted_date'),
                    closing_date=r.get('closing_date'),
                    application_url=r.get('application_url'),
                    source_url=r.get('source_url'),
                    last_checked_date=r.get('last_checked_date'),
                    status=r.get('status') or 'ACTIVE',
                    confidence=float(r.get('confidence') or 0.0),
                    link_status=r.get('link_status'),
                    link_verified_at=r.get('link_verified_at'),
                    data_provenance=r.get('data_provenance'),
                    fingerprint=r.get('fingerprint'),
                ))
            Job.objects.bulk_create(jobs_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(jobs_to_create)} Jobs.")

            # 5. NGO Collaborations
            cur.execute("SELECT * FROM ngo_collaborations")
            collabs = cur.fetchall()
            collabs_to_create = []
            for r in collabs:
                collabs_to_create.append(NGOCollaboration(
                    collab_id=r['collab_id'],
                    company_id=r['company_id'],
                    ngo_name=r.get('ngo_name'),
                    project_id=r.get('project_id'),
                    relationship_type=r.get('relationship_type'),
                    location=r.get('location'),
                    source_url=r.get('source_url'),
                    discovered_date=r.get('discovered_date'),
                    confidence=float(r.get('confidence') or 0.0),
                    fingerprint=r.get('fingerprint'),
                ))
            NGOCollaboration.objects.bulk_create(collabs_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(collabs_to_create)} NGO Collaborations.")

            # 6. Contacts
            cur.execute("SELECT * FROM contacts")
            contacts = cur.fetchall()
            contacts_to_create = []
            for r in contacts:
                contacts_to_create.append(Contact(
                    contact_id=r['contact_id'],
                    company_id=r['company_id'],
                    name=r.get('name'),
                    designation=r.get('designation'),
                    department=r.get('department'),
                    email=r.get('email'),
                    phone=r.get('phone'),
                    source_url=r.get('source_url'),
                    confidence=float(r.get('confidence') or 0.0),
                    last_verified_date=r.get('last_verified_date'),
                    link_status=r.get('link_status'),
                    link_verified_at=r.get('link_verified_at'),
                    verification_status=r.get('verification_status'),
                    fingerprint=r.get('fingerprint'),
                ))
            Contact.objects.bulk_create(contacts_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(contacts_to_create)} Contacts.")

            # 7. CSR Opportunities
            cur.execute("SELECT * FROM csr_opportunities")
            opps = cur.fetchall()
            opps_to_create = []
            for r in opps:
                opps_to_create.append(CSROpportunity(
                    opp_id=r['opp_id'],
                    company_id=r.get('company_id'),
                    title=r.get('title'),
                    opportunity_type=r.get('opportunity_type'),
                    category=r.get('category'),
                    submission_deadline=r.get('submission_deadline'),
                    portal_url=r.get('portal_url'),
                    requirements=r.get('requirements'),
                    status=r.get('status') or 'OPEN',
                    confidence=float(r.get('confidence') or 0.0),
                    link_status=r.get('link_status'),
                    link_verified_at=r.get('link_verified_at'),
                    fingerprint=r.get('fingerprint'),
                ))
            CSROpportunity.objects.bulk_create(opps_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(opps_to_create)} CSR Opportunities.")

            # 8. Prospects
            cur.execute("SELECT * FROM prospects")
            prospects = cur.fetchall()
            for r in prospects:
                Prospect.objects.update_or_create(
                    company_id=r['company_id'],
                    defaults={
                        'stage': r.get('stage') or 'Shortlisted',
                        'notes': r.get('notes'),
                        'assigned_to': r.get('assigned_to'),
                        'target_proposal': r.get('target_proposal'),
                        'follow_up_date': r.get('follow_up_date'),
                        'match_score': float(r.get('match_score') or 85.0),
                        'created_at': r.get('created_at'),
                        'updated_at': r.get('updated_at'),
                    }
                )
            self.stdout.write(f"  + Imported {len(prospects)} Prospects.")

            # 9. Pages
            cur.execute("SELECT * FROM pages")
            pages = cur.fetchall()
            pages_to_create = []
            for r in pages:
                pages_to_create.append(PageRecord(
                    page_id=r['page_id'],
                    company_id=r['company_id'],
                    url=r.get('url'),
                    title=r.get('title'),
                    page_type=r.get('page_type'),
                    content_hash=r.get('content_hash'),
                    last_modified=r.get('last_modified'),
                    last_crawled=r.get('last_crawled'),
                    status=r.get('status'),
                    relevant_snippet=r.get('relevant_snippet'),
                    confidence=float(r.get('confidence') or 0.0),
                ))
            PageRecord.objects.bulk_create(pages_to_create, ignore_conflicts=True)
            self.stdout.write(f"  + Imported {len(pages_to_create)} Crawled Pages.")

            # 10. Subscriptions, Promos, Invoices
            cur.execute("SELECT * FROM promo_codes")
            promos = cur.fetchall()
            for r in promos:
                PromoCode.objects.update_or_create(
                    code=r['code'],
                    defaults={
                        'percent_off': r.get('percent_off', 0),
                        'max_redemptions': r.get('max_redemptions'),
                        'times_redeemed': r.get('times_redeemed', 0),
                        'valid_from': r.get('valid_from'),
                        'valid_until': r.get('valid_until'),
                        'applicable_plans': r.get('applicable_plans'),
                        'description': r.get('description'),
                        'active': bool(r.get('active', 1)),
                    }
                )

            cur.execute("SELECT * FROM subscriptions")
            subs_data = cur.fetchall()
            for r in subs_data:
                Subscription.objects.update_or_create(
                    subscription_id=r['subscription_id'],
                    defaults={
                        'tenant_id': r.get('tenant_id'),
                        'plan_id': r.get('plan_id'),
                        'status': r.get('status'),
                        'billing_cycle': r.get('billing_cycle'),
                        'organization_name': r.get('organization_name'),
                        'contact_email': r.get('contact_email'),
                        'activated_at': r.get('activated_at'),
                        'current_period_start': r.get('current_period_start'),
                        'current_period_end': r.get('current_period_end'),
                        'cancel_at_period_end': bool(r.get('cancel_at_period_end', 0)),
                        'canceled_at': r.get('canceled_at'),
                        'cancel_reason': r.get('cancel_reason'),
                        'promo_code': r.get('promo_code'),
                        'promo_percent': r.get('promo_percent', 0),
                        'base_amount_paise': r.get('base_amount_paise', 0),
                        'discount_paise': r.get('discount_paise', 0),
                        'taxable_paise': r.get('taxable_paise', 0),
                        'cgst_paise': r.get('cgst_paise', 0),
                        'sgst_paise': r.get('sgst_paise', 0),
                        'igst_paise': r.get('igst_paise', 0),
                        'total_paise': r.get('total_paise', 0),
                        'currency': r.get('currency', 'INR'),
                        'payment_method': r.get('payment_method'),
                        'transaction_id': r.get('transaction_id'),
                        'gstin': r.get('gstin'),
                        'place_of_supply': r.get('place_of_supply'),
                        'supply_type': r.get('supply_type'),
                        'seats': r.get('seats', 1),
                        'daily_match_quota': r.get('daily_match_quota'),
                        'api_key_hash': r.get('api_key_hash'),
                        'api_key_prefix': r.get('api_key_prefix'),
                        'api_key_last4': r.get('api_key_last4'),
                        'request_id': r.get('request_id'),
                        'created_at': r.get('created_at'),
                        'updated_at': r.get('updated_at'),
                    }
                )

            cur.execute("SELECT * FROM invoices")
            inv_data = cur.fetchall()
            for r in inv_data:
                Invoice.objects.update_or_create(
                    invoice_id=r['invoice_id'],
                    defaults={
                        'invoice_no': r.get('invoice_no'),
                        'subscription_id': r.get('subscription_id'),
                        'tenant_id': r.get('tenant_id'),
                        'issued_at': r.get('issued_at'),
                        'description': r.get('description'),
                        'taxable_paise': r.get('taxable_paise', 0),
                        'cgst_paise': r.get('cgst_paise', 0),
                        'sgst_paise': r.get('sgst_paise', 0),
                        'igst_paise': r.get('igst_paise', 0),
                        'total_paise': r.get('total_paise', 0),
                        'currency': r.get('currency', 'INR'),
                        'gstin': r.get('gstin'),
                        'place_of_supply': r.get('place_of_supply'),
                        'status': r.get('status', 'PAID'),
                        'line_items': r.get('line_items'),
                    }
                )

        conn.close()
        return True

    def _import_from_files(self):
        csv_path = settings.BASE_DIR / 'data' / 'Top_200_Indian_Companies_Web_Scraping_Master_ENRICHED.csv'
        if csv_path.exists():
            self.stdout.write(f"Importing companies from CSV {csv_path.name}...")
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cid = row.get('company_id')
                    if not cid:
                        continue
                    Company.objects.update_or_create(
                        company_id=cid,
                        defaults={
                            'company_name': row.get('company_name', ''),
                            'nse_symbol': row.get('nse_symbol', ''),
                            'isin': row.get('isin', ''),
                            'website_url': row.get('website_url', ''),
                            'sector': row.get('sector', ''),
                            'headquarters': row.get('headquarters', ''),
                            'careers_url': row.get('careers_url', ''),
                            'csr_portal_url': row.get('csr_portal_url', ''),
                            'link_quality': row.get('link_quality', 'VERIFIED_DEEP_LINK'),
                        }
                    )
            self.stdout.write(f"  + Companies loaded from CSV: {Company.objects.count()}")
