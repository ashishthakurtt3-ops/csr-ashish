"""Tests for full company deletion (service + admin view)."""

import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from modules.admin_panel.models import (
    AuditRun,
    AuditTrail,
    Company,
    CompanyCompletenessRegister,
    CompanyCrawlSummary,
    CompanyMetrics,
    CompanyRefreshRequest,
    CompanySource,
    Contact,
    CSROpportunity,
    CSRProject,
    Document,
    DroppedCandidate,
    Job,
    NGOCollaboration,
    OpportunityScore,
    PageRecord,
    Prospect,
)
from modules.admin_panel.services.company_deletion_service import delete_company_completely

User = get_user_model()


class CompanyDeletionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix='company-delete-test-')
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='delete_admin',
            email='delete_admin@example.com',
            password='Password123!',
            role='SUPERADMIN',
        )

        self.company = Company.objects.create(
            company_id='DEL_TEST_01',
            company_name='Delete Me Ltd',
            nse_symbol='DELME',
        )
        self.other_company = Company.objects.create(
            company_id='KEEP_TEST_01',
            company_name='Keep Me Ltd',
        )

        self.job = Job.objects.create(
            company=self.company,
            job_title='Engineer',
            status='ACTIVE',
        )
        self.other_job = Job.objects.create(
            company=self.other_company,
            job_title='Designer',
            status='ACTIVE',
        )
        self.csr = CSRProject.objects.create(company=self.company, project_name='CSR Project')
        self.opportunity = CSROpportunity.objects.create(company=self.company, title='Open RFP')
        self.contact = Contact.objects.create(company=self.company, name='Jane Doe')
        self.ngo = NGOCollaboration.objects.create(company=self.company, ngo_name='Helping Hands')
        self.prospect = Prospect.objects.create(company=self.company)
        self.score = OpportunityScore.objects.create(company=self.company, score=42.0)
        self.source = CompanySource.objects.create(
            company=self.company,
            original_url='https://deleteme.example/careers',
            final_url='https://deleteme.example/careers',
            source_type='CAREERS_LANDING',
        )
        self.crawl_summary = CompanyCrawlSummary.objects.create(company=self.company, crawl_status='CRAWLED')
        self.page = PageRecord.objects.create(company=self.company, url='https://deleteme.example/careers')
        self.dropped = DroppedCandidate.objects.create(
            company=self.company,
            candidate_type='JOB',
            reason='Duplicate',
        )
        self.completeness = CompanyCompletenessRegister.objects.create(
            company=self.company,
            company_id_str='DEL_TEST_01',
            company_name='Delete Me Ltd',
        )
        self.audit_run = AuditRun.objects.create(triggered_by='TEST')
        CompanyMetrics.objects.create(audit_run=self.audit_run, company=self.company)
        CompanyRefreshRequest.objects.create(user=self.admin, company=self.company)

        self.document = Document.objects.create(
            company=self.company,
            title='Proof of registration',
            file=SimpleUploadedFile('proof.txt', b'company evidence'),
        )
        self.document_path = self.document.file.path

        # Audit history that must be purged with the company.
        AuditTrail.objects.create(record_type='Company', record_id='DEL_TEST_01', action='CREATE')
        AuditTrail.objects.create(record_type='Job', record_id=str(self.job.job_row_id), action='CREATE')
        AuditTrail.objects.create(record_type='CSRProject', record_id=str(self.csr.csr_id), action='CREATE')
        AuditTrail.objects.create(record_type='DOCUMENT', record_id=str(self.document.document_id), action='CREATE')
        # Unrelated audit history must survive.
        AuditTrail.objects.create(record_type='Company', record_id='KEEP_TEST_01', action='CREATE')

    def test_delete_company_completely_removes_every_related_record(self):
        stats = delete_company_completely(self.company, deleted_by=self.admin)

        self.assertEqual(stats['company_id'], 'DEL_TEST_01')
        self.assertEqual(stats['jobs'], 1)
        self.assertEqual(stats['csr_projects'], 1)
        self.assertEqual(stats['documents'], 1)

        self.assertFalse(Company.objects.filter(company_id='DEL_TEST_01').exists())
        self.assertFalse(Job.objects.filter(job_row_id=self.job.job_row_id).exists())
        self.assertFalse(CSRProject.objects.filter(csr_id=self.csr.csr_id).exists())
        self.assertFalse(CSROpportunity.objects.filter(opp_id=self.opportunity.opp_id).exists())
        self.assertFalse(Contact.objects.filter(contact_id=self.contact.contact_id).exists())
        self.assertFalse(NGOCollaboration.objects.filter(collab_id=self.ngo.collab_id).exists())
        self.assertFalse(Prospect.objects.filter(prospect_id=self.prospect.prospect_id).exists())
        self.assertFalse(OpportunityScore.objects.filter(company_id='DEL_TEST_01').exists())
        self.assertFalse(CompanySource.objects.filter(source_id=self.source.source_id).exists())
        self.assertFalse(CompanyCrawlSummary.objects.filter(summary_id=self.crawl_summary.summary_id).exists())
        self.assertFalse(PageRecord.objects.filter(page_id=self.page.page_id).exists())
        self.assertFalse(DroppedCandidate.objects.filter(pk=self.dropped.pk).exists())
        self.assertFalse(CompanyCompletenessRegister.objects.filter(register_id=self.completeness.register_id).exists())
        self.assertFalse(CompanyMetrics.objects.filter(company_id='DEL_TEST_01').exists())
        self.assertFalse(CompanyRefreshRequest.objects.filter(company_id='DEL_TEST_01').exists())
        self.assertFalse(Document.objects.filter(document_id=self.document.document_id).exists())

        # Uploaded file removed from storage.
        self.assertFalse(os.path.exists(self.document_path))

        # Company-scoped audit history purged; deletion action retained.
        self.assertFalse(AuditTrail.objects.filter(record_type='Company', record_id='DEL_TEST_01').exists())
        self.assertFalse(AuditTrail.objects.filter(record_type='Job', record_id=str(self.job.job_row_id)).exists())
        self.assertFalse(AuditTrail.objects.filter(record_type='CSRProject', record_id=str(self.csr.csr_id)).exists())
        self.assertFalse(AuditTrail.objects.filter(record_type='DOCUMENT', record_id=str(self.document.document_id)).exists())
        self.assertTrue(AuditTrail.objects.filter(record_type='CompanyDeletion', record_id='DEL_TEST_01').exists())

        # Other companies are untouched.
        self.assertTrue(Company.objects.filter(company_id='KEEP_TEST_01').exists())
        self.assertTrue(Job.objects.filter(job_row_id=self.other_job.job_row_id).exists())
        self.assertTrue(AuditTrail.objects.filter(record_type='Company', record_id='KEEP_TEST_01').exists())

    def test_company_management_delete_view_deletes_on_post(self):
        self.client.force_login(self.admin)
        url = reverse('admin_companies:delete', args=['DEL_TEST_01'])

        # GET must not delete anything.
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Company.objects.filter(company_id='DEL_TEST_01').exists())

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Company.objects.filter(company_id='DEL_TEST_01').exists())