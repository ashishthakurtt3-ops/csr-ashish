"""
tests/test_m2_concurrent_extraction.py
======================================
Comprehensive verification test suite for Milestone 2:
- Candidate link starvation fix with priority DOM container selection
- Compact batched prompt execution (15-20 candidates per batch) with token limit protection
- Concurrent AI discovery agents (Job Discovery & CSR Discovery)
- Thread-safe trace aggregation across concurrent worker threads
- Resilient CSR Section 135 validation (exact, normalized, n-gram, and token overlap)
"""

import concurrent.futures
from unittest.mock import patch
from django.test import TestCase

from modules.admin_panel.models import Company
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.crawler_engine.hybrid_ai_service import (
    HybridAIExtractionService,
    extract_jobs_concurrent,
    extract_csr_concurrent,
    aggregate_thread_traces,
)


class M2ConcurrentExtractionTests(TestCase):

    def setUp(self):
        self.company = Company.objects.create(
            company_id='m2_test_corp',
            company_name='M2 Test Corp',
            official_domain='m2testcorp.com',
            website_url='https://www.m2testcorp.com',
        )

    def test_candidate_link_starvation_prioritizes_job_containers(self):
        """
        HTML with 50+ navigation/header links followed by authentic vacancy cards
        inside <main class="job-listings"> must prioritize the job cards over navigation.
        """
        nav_anchors = "\n".join([f'<a href="/menu-{i}">Navigation Item {i}</a>' for i in range(1, 55)])
        html = f"""
        <html>
        <head><title>Careers Portal</title></head>
        <body>
            <nav id="site-nav">
                {nav_anchors}
            </nav>
            <main class="job-listings">
                <div class="job-card" id="job-101">
                    <a href="/careers/senior-python-dev">Senior Python Developer</a>
                    <span class="location">Bengaluru, Karnataka</span>
                </div>
                <div class="job-card" id="job-102">
                    <a href="/careers/data-engineer">Staff Data Engineer</a>
                    <span class="location">Remote</span>
                </div>
            </main>
        </body>
        </html>
        """

        mock_ai_response = [
            {"candidate_id": 1, "job_title": "Senior Python Developer", "location": "Bengaluru", "confidence": 0.95},
            {"candidate_id": 2, "job_title": "Staff Data Engineer", "location": "Remote", "confidence": 0.95},
        ]

        with patch.object(
            HybridAIExtractionService,
            '_execute_prompt_with_failover',
            return_value=(mock_ai_response, 'gemini', 'gemini-2.0-flash'),
        ):
            jobs = HybridAIExtractionService.extract_unstructured_jobs(
                company_id=self.company.company_id,
                company_name=self.company.company_name,
                raw_content=html,
                careers_url='https://www.m2testcorp.com/careers'
            )

        self.assertGreaterEqual(len(jobs), 2)
        urls = [j['application_url'] for j in jobs]
        self.assertIn('https://www.m2testcorp.com/careers/senior-python-dev', urls)
        self.assertIn('https://www.m2testcorp.com/careers/data-engineer', urls)

    def test_job_extraction_prompt_batching(self):
        """
        When more than 15 candidates are evaluated, extraction must batch them
        into chunks of 15 candidates per prompt to avoid token limit truncation.
        """
        # Create 35 mock candidates
        cands = [
            {'id': i, 'text': f'Role {i}', 'card_context': f'Description for role {i}', 'href': f'https://example.com/jobs/{i}'}
            for i in range(1, 36)
        ]

        batch_calls = []

        def _mock_execute_prompt(prompt, *args, **kwargs):
            batch_calls.append(prompt)
            # Return vacancy for first item in each batch
            return [{"candidate_id": 1, "job_title": "Role 1", "confidence": 0.9}], 'gemini', 'gemini-2.0-flash'

        with patch.object(HybridAIExtractionService, '_execute_prompt_with_failover', side_effect=_mock_execute_prompt):
            jobs = HybridAIExtractionService.extract_unstructured_jobs(
                company_id=self.company.company_id,
                company_name=self.company.company_name,
                raw_content="",
                careers_url='https://example.com/careers',
                candidates=cands
            )

        # 35 candidates / 15 per batch = 3 batches
        self.assertEqual(len(batch_calls), 3)

    def test_csr_extraction_compact_batching_and_deduplication(self):
        """
        Long CSR content is segmented into compact chunks without blowing token limits,
        and projects with identical names are deduplicated.
        """
        long_content = (
            "Section 135 Annual Disclosure.\n"
            "Project Clean Water provides drinking water access to 50 villages in Karnataka. "
            "Under Schedule VII, total expenditure was 2.5 Crore INR.\n\n"
        ) * 50  # ~8,000+ characters

        mock_project = [
            {
                "project_name": "Project Clean Water",
                "category": "Water & Sanitation",
                "budget": "2.5 Crore INR",
                "state": "Karnataka",
                "verbatim_quote": "Project Clean Water provides drinking water access to 50 villages in Karnataka.",
                "confidence": 0.95
            }
        ]

        with patch.object(
            HybridAIExtractionService,
            '_execute_prompt_with_failover',
            return_value=(mock_project, 'gemini', 'gemini-2.0-flash'),
        ):
            projects = HybridAIExtractionService.extract_unstructured_csr_projects(
                company_id=self.company.company_id,
                company_name=self.company.company_name,
                raw_content=long_content,
                csr_url='https://www.m2testcorp.com/csr'
            )

        # Must be deduplicated down to 1 distinct project
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]['project_name'], 'Project Clean Water')

    def test_concurrent_ai_agents_and_thread_safe_trace_aggregation(self):
        """
        Job Discovery Agent and CSR Discovery Agent execute concurrently across threads,
        and their trace events feed into the parent thread trace seamlessly.
        """
        HybridAIExtractionService.begin_trace()

        jobs_content = '<main><a href="/jobs/1">Senior Architect</a></main>'
        csr_content = 'Section 135 Initiative: Project Shiksha empowers rural schools in Maharashtra.'

        def _run_jobs():
            with patch.object(
                HybridAIExtractionService,
                '_execute_prompt_with_failover',
                return_value=(
                    [{"candidate_id": 1, "job_title": "Senior Architect"}],
                    'gemini',
                    'gemini-2.0-flash'
                )
            ) as mock_exec:
                # Simulate trace event generated by AI prompt failover
                HybridAIExtractionService._append_trace({
                    'provider': 'gemini',
                    'model': 'gemini-2.0-flash',
                    'task': 'job_extraction',
                    'status': 'SUCCESS'
                })
                return extract_jobs_concurrent(jobs_content, 'https://example.com/careers', 'M2 Corp')

        def _run_csr():
            with patch.object(
                HybridAIExtractionService,
                '_execute_prompt_with_failover',
                return_value=(
                    [{
                        "project_name": "Project Shiksha",
                        "category": "Education & Skill Development",
                        "verbatim_quote": "Project Shiksha empowers rural schools in Maharashtra."
                    }],
                    'openrouter',
                    'meta-llama/llama-3.3-70b-instruct:free'
                )
            ):
                HybridAIExtractionService._append_trace({
                    'provider': 'openrouter',
                    'model': 'meta-llama/llama-3.3-70b-instruct:free',
                    'task': 'csr_extraction',
                    'status': 'SUCCESS'
                })
                return extract_csr_concurrent(csr_content, 'https://example.com/csr', 'M2 Corp')

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_jobs = executor.submit(_run_jobs)
            future_csr = executor.submit(_run_csr)
            jobs_res = future_jobs.result()
            csr_projects, csr_reports = future_csr.result()

        self.assertGreaterEqual(len(jobs_res), 1)
        self.assertGreaterEqual(len(csr_projects), 1)

        # Parent thread calls end_trace()
        trace_events = HybridAIExtractionService.end_trace()
        tasks = [ev['task'] for ev in trace_events]
        self.assertIn('job_extraction', tasks)
        self.assertIn('csr_extraction', tasks)

        models = [ev['model'] for ev in trace_events]
        self.assertIn('gemini-2.0-flash', models)
        self.assertIn('meta-llama/llama-3.3-70b-instruct:free', models)

    def test_resilient_csr_validation(self):
        """
        Tests Section 135 CSR validation resilience:
        - Exact substring match
        - Normalized punctuation/whitespace match
        - Continuous n-gram sub-phrase match
        - Token-level overlap match (>= 75%)
        - Non-aborting batch evaluation
        """
        source_text = (
            "Annual Sustainability and Corporate Social Responsibility Report 2025. "
            "Under Schedule VII of the Companies Act 2013, M2 Corp invested 5 Crores in "
            "Project Jal Shakti to establish 120 rainwater harvesting structures across rural Rajasthan."
        )

        company = self.company

        # 1. Exact match
        cand_exact = {
            'project_name': 'Project Jal Shakti',
            'source_url': 'https://www.m2testcorp.com/csr',
            'verbatim_quote': 'M2 Corp invested 5 Crores in Project Jal Shakti to establish 120 rainwater harvesting structures',
        }
        ok, reason, _ = BatchDiscoveryService.validate_csr(cand_exact, company, source_text)
        self.assertTrue(ok, reason)

        # 2. Normalized punctuation / smart quotes match
        cand_norm = {
            'project_name': 'Project Jal Shakti',
            'source_url': 'https://www.m2testcorp.com/csr',
            'verbatim_quote': 'M2 Corp invested 5 Crores in "Project Jal Shakti" to establish: 120 rainwater harvesting structures!',
        }
        ok, reason, _ = BatchDiscoveryService.validate_csr(cand_norm, company, source_text)
        self.assertTrue(ok, reason)

        # 3. Continuous N-gram sub-phrase match (minor paraphrasing at ends)
        cand_ngram = {
            'project_name': 'Project Jal Shakti',
            'source_url': 'https://www.m2testcorp.com/csr',
            'verbatim_quote': 'Project Jal Shakti to establish 120 rainwater harvesting structures across rural Rajasthan',
        }
        ok, reason, _ = BatchDiscoveryService.validate_csr(cand_ngram, company, source_text)
        self.assertTrue(ok, reason)

        # 4. Token overlap match (>= 75% token overlap)
        cand_token_overlap = {
            'project_name': 'Project Jal Shakti',
            'source_url': 'https://www.m2testcorp.com/csr',
            'verbatim_quote': 'M2 Corp invested 5 Crores establishing rainwater harvesting structures in rural Rajasthan',
        }
        ok, reason, _ = BatchDiscoveryService.validate_csr(cand_token_overlap, company, source_text)
        self.assertTrue(ok, reason)

        # 5. Invalid policy candidate rejected
        cand_policy = {
            'project_name': 'Corporate Code of Conduct & Ethics Policy',
            'source_url': 'https://www.m2testcorp.com/csr',
            'verbatim_quote': 'Annual Sustainability and Corporate Social Responsibility Report 2025.',
        }
        ok, reason, _ = BatchDiscoveryService.validate_csr(cand_policy, company, source_text)
        self.assertFalse(ok)
        self.assertTrue('POLICY_NOT_PROJECT' in reason or 'INVALID_CSR_PROJECT_NAME' in reason)

        # 6. Batch evaluation evaluates all candidates without aborting on invalid items
        batch_candidates = [cand_exact, cand_policy, cand_token_overlap]
        valid_list, rejected_list = BatchDiscoveryService.validate_csr(company, batch_candidates, source_text)
        self.assertEqual(len(valid_list), 2)
        self.assertEqual(len(rejected_list), 1)
        self.assertEqual(rejected_list[0]['candidate']['project_name'], 'Corporate Code of Conduct & Ethics Policy')
