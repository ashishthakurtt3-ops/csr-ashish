"""
modules/admin_panel/management/commands/discover_and_verify_company_sources.py
=============================================================================
Enterprise AI-Powered Management Command for Corporate Source Discovery,
Two-Stage Page Classification, and Database URL Correction.

Features:
- Dynamically processes companies from database (supports 201 current companies and scales beyond 1,000+).
- Memory-bounded streaming via .only() and .iterator(chunk_size=batch_size).
- Source-content hashing: Skips unnecessary reclassification when page content is unchanged.
- Separate status tracking: COMPLETED, PENDING, INACCESSIBLE, REVIEW_REQUIRED, UNCHANGED_SKIPPED, ERROR.
- Resumable checkpointing: Saves progress after every company to survive quota pauses or restarts.
- Strict isolation: Only APPROVED sources update Company primary URLs with atomic transactions and AuditTrail logging.
- Review-required sources are preserved in CompanySource registry without altering verified primary URLs.
- Replaceable AI Provider: OpenRouter Free Models Router is active; dynamic serving models are recorded in metadata.

Usage:
    python manage.py discover_and_verify_company_sources --all --dry-run
    python manage.py discover_and_verify_company_sources --all --apply-verified-updates
    python manage.py discover_and_verify_company_sources --company-id COMP_TOP200_001
    python manage.py discover_and_verify_company_sources --limit 10 --apply-verified-updates
    python manage.py discover_and_verify_company_sources --resume --apply-verified-updates
    python manage.py discover_and_verify_company_sources --batch-size 50 --max-api-calls 100
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.admin_panel.models import Company, CompanySource, AuditTrail
from modules.crawler_engine import ai_classifier_config as cfg
from modules.crawler_engine.ai_api_client import get_ai_client, QuotaExhaustedError
from modules.crawler_engine.page_classifier import TwoStagePageClassifier
from modules.crawler_engine.access_detector import fetch_live_page

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Discover, AI-classify, and verify official company sources (Careers, Jobs, CSR, Reports) with quota safety and scalable batching."

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Process all companies in the directory.')
        parser.add_argument('--company-id', type=str, help='Process a specific company by company_id.')
        parser.add_argument('--limit', type=int, default=0, help='Maximum number of companies to process.')
        parser.add_argument('--batch-size', type=int, default=50, help='Queryset iterator chunk size for memory-bounded processing.')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Simulate classification without modifying DB.')
        parser.add_argument('--apply-verified-updates', action='store_true', default=False, help='Write approved verified sources to DB.')
        parser.add_argument('--resume', action='store_true', default=False, help='Resume from the saved checkpoint.')
        parser.add_argument('--force-reclassify', action='store_true', default=False, help='Bypass content-hash check and force reclassification.')
        parser.add_argument('--retry-inaccessible', action='store_true', default=False, help='Retry companies previously marked inaccessible in checkpoint.')
        parser.add_argument('--retry-review-required', action='store_true', default=False, help='Retry companies previously marked review-required in checkpoint.')
        parser.add_argument('--max-api-calls', type=int, default=0, help='Override max AI API calls limit.')
        parser.add_argument('--report-file', type=str, default='', help='Path to output JSON summary report.')

    def handle(self, *args, **options):
        dry_run = options['dry_run'] or not options['apply_verified_updates']
        is_resume = options['resume']
        company_id_arg = options.get('company_id')
        limit = options.get('limit') or 0
        batch_size = max(options.get('batch_size') or 50, 10)
        force_reclassify = options.get('force_reclassify', False)
        max_api_calls = options.get('max_api_calls') or cfg.MAX_API_CALLS_PER_RUN

        api_key_val = os.environ.get(cfg.AI_API_KEY_ENV, "")
        api_key_status = f"[CONFIGURED ({len(api_key_val)} chars)]" if api_key_val else "[NOT SET]"
        self.stdout.write(self.style.NOTICE(
            f"=== Enterprise Company Source Discovery & Verification ===\n"
            f"Active AI Provider : {cfg.AI_PROVIDER} ({cfg.AI_MODEL})\n"
            f"Configured Model   : {cfg.GEMINI_MODEL if cfg.AI_PROVIDER == 'gemini' else cfg.AI_MODEL}\n"
            f"API Key Env Var    : {cfg.AI_API_KEY_ENV} {api_key_status}\n"
            f"Free Tier Verified : {'YES' if cfg.is_gemini_free_tier_model(cfg.AI_MODEL) else 'NO'}\n"
            f"Fallback Provider  : {cfg.AI_FALLBACK_PROVIDER} (Enabled: {cfg.AI_FALLBACK_ENABLED})\n"
            f"Mode               : {'DRY RUN (Read-Only Preview)' if dry_run else 'PRODUCTION (Apply Verified Updates)'}\n"
            f"Resume mode        : {is_resume}\n"
            f"Batch Chunk Size   : {batch_size}\n"
            f"Max API Calls/Run  : {max_api_calls}\n"
        ))

        # Checkpoints setup
        checkpoint_dir = cfg.CHECKPOINT_DIR
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_file = os.path.join(checkpoint_dir, "discovery_checkpoint.json")

        company_statuses: Dict[str, Any] = {}
        skip_ids: Set[str] = set()

        if is_resume and os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    ckpt = json.load(f)
                    company_statuses = ckpt.get('company_statuses', {})
                    for cid, cinfo in company_statuses.items():
                        c_status = cinfo.get("status") if isinstance(cinfo, dict) else "COMPLETED"
                        if c_status in ("COMPLETED", "UNCHANGED_SKIPPED"):
                            skip_ids.add(cid)
                        elif c_status == "INACCESSIBLE" and not options.get('retry_inaccessible'):
                            skip_ids.add(cid)
                        elif c_status == "REVIEW_REQUIRED" and not options.get('retry_review_required'):
                            skip_ids.add(cid)

                    self.stdout.write(self.style.SUCCESS(
                        f"Resuming from checkpoint: {len(skip_ids)} companies will be skipped "
                        f"({len(company_statuses)} tracked in checkpoint)."
                    ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to read checkpoint: {e}"))

        # Efficient dynamic querying with .only() to keep memory flat
        pk_field = Company._meta.pk.name
        qs = Company.objects.all().order_by(pk_field).only(
            pk_field, 'company_name', 'official_domain',
            'website_url', 'careers_url', 'jobs_page_url', 'csr_portal_url',
            'sustainability_url', 'ats_platform', 'ats_url'
        )

        if company_id_arg:
            qs = qs.filter(**{pk_field: company_id_arg})
        elif is_resume and skip_ids:
            qs = qs.exclude(**{f"{pk_field}__in": skip_ids})

        if limit > 0:
            qs = qs[:limit]

        total_to_process = qs.count()
        self.stdout.write(f"Identified {total_to_process} companies to process dynamically from database.\n")

        # Initialize API client and classifier
        client = get_ai_client()
        client.max_api_calls = max_api_calls
        classifier = TwoStagePageClassifier(client=client)

        stats = {
            "processed_companies": 0,
            "completed_companies": 0,
            "inaccessible_companies": 0,
            "review_required_companies": 0,
            "unchanged_skipped_companies": 0,
            "error_companies": 0,
            "total_links_discovered": 0,
            "stage1_classified_links": 0,
            "stage2_evaluated_pages": 0,
            "approved_sources": 0,
            "review_required_sources": 0,
            "rejected_sources": 0,
            "url_updates_applied": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "models_used": {},
            "errors": []
        }

        quota_exhausted = False
        summary_results = []

        try:
            # Memory-bounded iterator: never loads whole directory at once
            for idx, comp in enumerate(qs.iterator(chunk_size=batch_size), 1):
                self.stdout.write(f"[{idx}/{total_to_process}] Company: {comp.company_name} ({comp.company_id})")

                # Check API quota before starting next company
                metrics_now = client.get_metrics()
                if metrics_now.get("api_calls_made", 0) >= max_api_calls:
                    self.stdout.write(self.style.WARNING(
                        f"Reached maximum API call limit ({max_api_calls}). Pausing safely."
                    ))
                    break

                comp_summary = self._process_single_company(
                    comp, classifier, dry_run, stats, force_reclassify=force_reclassify
                )
                summary_results.append(comp_summary)

                # Record per-company status
                status = comp_summary.get("status", "COMPLETED")
                company_statuses[comp.company_id] = {
                    "status": status,
                    "timestamp": timezone.now().isoformat(),
                    "homepage_content_hash": comp_summary.get("homepage_content_hash"),
                    "approved_count": len(comp_summary.get("approved", [])),
                    "review_required_count": len(comp_summary.get("review_required", [])),
                    "rejected_count": len(comp_summary.get("rejected", []))
                }

                stats["processed_companies"] += 1
                if status == "COMPLETED":
                    stats["completed_companies"] += 1
                elif status == "INACCESSIBLE":
                    stats["inaccessible_companies"] += 1
                elif status == "REVIEW_REQUIRED":
                    stats["review_required_companies"] += 1
                elif status == "UNCHANGED_SKIPPED":
                    stats["unchanged_skipped_companies"] += 1
                elif status == "ERROR":
                    stats["error_companies"] += 1

                # Save checkpoint after each company for bulletproof resumption
                self._save_checkpoint(checkpoint_file, company_statuses, stats)

        except QuotaExhaustedError as qe:
            quota_exhausted = True
            self.stdout.write(self.style.ERROR(
                f"\n[QUOTA EXHAUSTED] Free-tier API quota limit reached: {qe}\n"
                f"Gracefully pausing. Checkpoint saved for {len(company_statuses)} companies."
            ))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nProcess interrupted by user. Saving checkpoint..."))
            self._save_checkpoint(checkpoint_file, company_statuses, stats)
        except Exception as e:
            logger.exception("Unexpected error during execution: %s", e)
            stats["errors"].append(str(e))
            self._save_checkpoint(checkpoint_file, company_statuses, stats)
            self.stdout.write(self.style.ERROR(f"Error encountered: {e}"))

        # Final Metrics
        client_metrics = client.get_metrics()
        stats["api_calls"] = client_metrics.get("api_calls_made", 0)
        stats["cache_hits"] = client_metrics.get("cache_hits", 0)

        self._print_final_summary(stats, dry_run, quota_exhausted, checkpoint_file)

        # Write output report if requested or default
        report_path = options.get('report_file') or os.path.join(
            cfg.REPORT_DIR, f"source_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        try:
            with open(report_path, 'w', encoding='utf-8') as rf:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "provider": cfg.AI_PROVIDER,
                    "model": cfg.AI_MODEL,
                    "dry_run": dry_run,
                    "stats": stats,
                    "results": summary_results
                }, rf, indent=2)
            self.stdout.write(self.style.SUCCESS(f"Detailed report saved to: {report_path}"))
        except Exception as re:
            self.stdout.write(self.style.WARNING(f"Could not save report file: {re}"))

    def _process_single_company(
        self,
        company: Company,
        classifier: TwoStagePageClassifier,
        dry_run: bool,
        stats: Dict[str, Any],
        force_reclassify: bool = False
    ) -> Dict[str, Any]:
        """
        Executes discovery, Stage 1 link classification, Stage 2 page classification,
        evidence validation, and transactional updates for one company.
        """
        comp_res = {
            "company_id": company.company_id,
            "company_name": company.company_name,
            "links_found": 0,
            "candidates_evaluated": 0,
            "approved": [],
            "review_required": [],
            "rejected": [],
            "updates": [],
            "homepage_content_hash": None,
            "status": "PENDING"
        }

        # 1. Determine base homepage URL
        base_url = company.website_url or ""
        if not base_url and company.official_domain:
            base_url = f"https://{company.official_domain}"
        if not base_url:
            comp_res["status"] = "INACCESSIBLE"
            return comp_res

        # 2. Fetch homepage
        homepage_resp = fetch_live_page(base_url)
        if not homepage_resp.get("ok"):
            comp_res["status"] = "INACCESSIBLE"
            return comp_res

        html = homepage_resp.get("html", "")
        homepage_content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()[:32] if html else None
        comp_res["homepage_content_hash"] = homepage_content_hash

        # 3. Source-content hash check: Skip unnecessary reclassification if unchanged
        if not force_reclassify and homepage_content_hash:
            approved_sources = CompanySource.objects.filter(
                company=company,
                verification_status="APPROVED",
                is_primary=True
            )
            # If the company already has approved primary sources and verified URLs
            has_primary_urls = (company.careers_url or company.jobs_page_url) and (company.csr_portal_url or company.sustainability_url)
            if approved_sources.exists() and has_primary_urls:
                matched_source = approved_sources.filter(content_hash=homepage_content_hash).first()
                if matched_source:
                    self.stdout.write(f"  -> Homepage content unchanged ({homepage_content_hash[:8]}...). Skipping redundant reclassification.")
                    comp_res["status"] = "UNCHANGED_SKIPPED"
                    return comp_res

        # 4. Extract candidate links independently of AI provider
        raw_links = classifier.extract_candidate_links_from_html(
            base_url=homepage_resp.get("final_url") or base_url,
            html=html,
            max_links=cfg.MAX_LINKS_PER_COMPANY
        )
        stats["total_links_discovered"] += len(raw_links)
        comp_res["links_found"] = len(raw_links)

        if not raw_links:
            comp_res["status"] = "REVIEW_REQUIRED"
            return comp_res

        self.stdout.write(f"  -> Discovered {len(raw_links)} links. Running Stage 1 batch classification...")
        import sys
        sys.stdout.flush()

        stage2_candidates = []
        cand_idx = 0
        try:
            # 5. Stage 1: Batch link classification via AI adapter
            classified_links = classifier.classify_discovered_links(
                company_name=company.company_name,
                domain=company.official_domain or urlparse(base_url).netloc,
                links=raw_links
            )
            stats["stage1_classified_links"] += len(classified_links)
            for cl in classified_links:
                m = cl.get("actual_model")
                if m:
                    stats["models_used"][m] = stats["models_used"].get(m, 0) + 1
                err = cl.get("error")
                if err and err not in stats.setdefault("errors", []):
                    stats["errors"].append(f"Stage 1 Error: {err}")

            # 6. Filter promising candidates for Stage 2
            stage2_candidates = classifier.filter_promising_candidates_for_stage_2(
                classified_links=classified_links,
                max_pages=cfg.MAX_PAGES_PER_COMPANY
            )
            comp_res["candidates_evaluated"] = len(stage2_candidates)
            self.stdout.write(f"  -> Stage 1 complete. Evaluating {len(stage2_candidates)} candidates in Stage 2...")
            sys.stdout.flush()

            # 7. Stage 2: Deep content retrieval and independent evidence validation
            for cand_idx, cand in enumerate(stage2_candidates, 1):
                target_url = cand.get("url")
                stats["stage2_evaluated_pages"] += 1

                page_data = classifier.fetch_and_prepare_page_data(target_url)
                page_class = classifier.classify_destination_page(
                    company_name=company.company_name,
                    url=target_url,
                    page_data=page_data
                )
                # Universal evidence gate: identical validation regardless of AI provider
                validation = classifier.validate_page_evidence(
                    company_name=company.company_name,
                    official_domain=company.official_domain,
                    page_classification=page_class,
                    page_data=page_data
                )

                decision = validation.get("decision", "REVIEW_REQUIRED")
                verified_type = validation.get("verified_type", cand.get("candidate_category"))
                target_field = validation.get("target_field")
                final_url = page_data.get("url") or target_url
                actual_model = page_class.get("actual_model") or validation.get("actual_model", "unknown")
                if actual_model and actual_model != "unknown":
                    stats["models_used"][actual_model] = stats["models_used"].get(actual_model, 0) + 1
                err = page_class.get("error") or validation.get("error")
                if err and err not in stats.setdefault("errors", []):
                    stats["errors"].append(f"Stage 2 Error ({target_url}): {err}")

                record_info = {
                    "url": target_url,
                    "final_url": final_url,
                    "page_type": verified_type,
                    "confidence": page_class.get("confidence", 0.0),
                    "decision": decision,
                    "reason": validation.get("reason", ""),
                    "target_field": target_field,
                    "actual_model": actual_model
                }

                self.stdout.write(f"     [{cand_idx}/{len(stage2_candidates)}] {verified_type} -> {decision} (model: {actual_model}, conf: {record_info['confidence']:.2f})")
                sys.stdout.flush()

                if decision == "APPROVED":
                    comp_res["approved"].append(record_info)
                    stats["approved_sources"] += 1
                    if not dry_run:
                        self._apply_verified_source(company, record_info, cand, page_data, page_class, validation, comp_res, stats)
                elif decision == "REJECTED":
                    comp_res["rejected"].append(record_info)
                    stats["rejected_sources"] += 1
                    if not dry_run:
                        self._record_source_registry(company, record_info, cand, page_data, page_class, "REJECTED")
                else:
                    comp_res["review_required"].append(record_info)
                    stats["review_required_sources"] += 1
                    if not dry_run:
                        self._record_source_registry(company, record_info, cand, page_data, page_class, "REVIEW_REQUIRED")

        except QuotaExhaustedError as qe:
            self.stdout.write(self.style.WARNING(
                f"  -> AI quota exhausted while processing {company.company_name}. "
                f"Preserving candidate sources as PENDING_AI / REVIEW_REQUIRED."
            ))
            # Safely mark remaining unprocessed candidate links as PENDING_AI so they are not lost
            remaining_cands = stage2_candidates[max(0, cand_idx-1):] if stage2_candidates else [
                {"url": l.get("url"), "text": l.get("text"), "location": l.get("location")}
                for l in raw_links[:cfg.MAX_PAGES_PER_COMPANY]
            ]
            for rem in remaining_cands:
                u = rem.get("url")
                rec = {
                    "url": u,
                    "final_url": u,
                    "page_type": rem.get("candidate_category", "UNKNOWN_REQUIRES_REVIEW"),
                    "confidence": 0.0,
                    "decision": "PENDING_AI",
                    "reason": f"AI classification paused due to quota limits: {qe}",
                    "target_field": None,
                    "actual_model": "paused"
                }
                comp_res["review_required"].append(rec)
                if not dry_run:
                    self._record_source_registry(company, rec, rem, {}, {}, "PENDING_AI")
            comp_res["status"] = "REVIEW_REQUIRED"
            raise

        # Set final company status (Requirement 4 & 8)
        genuine_approvals = [
            a for a in comp_res["approved"]
            if a.get("actual_model") not in ("rule_based_fallback", "fallback", "offline_fallback")
        ]
        if genuine_approvals:
            comp_res["status"] = "COMPLETED"
        else:
            comp_res["status"] = "REVIEW_REQUIRED"

        return comp_res

    def _record_source_registry(
        self,
        company: Company,
        record_info: Dict[str, Any],
        cand: Dict[str, Any],
        page_data: Dict[str, Any],
        page_class: Dict[str, Any],
        status: str
    ):
        """
        Creates or updates a CompanySource entry without overriding primary company URLs.
        Ensures uncertain sources remain flagged for review without corrupting verified data.
        """
        try:
            CompanySource.objects.update_or_create(
                company=company,
                final_url=record_info["final_url"],
                defaults={
                    "original_url": record_info["url"],
                    "source_type": self._map_to_source_type_choice(record_info["page_type"]),
                    "detailed_classification": record_info["page_type"],
                    "discovery_method": cand.get("location", "BODY_CONTENT"),
                    "link_text": cand.get("text", "")[:500],
                    "verification_status": status,
                    "is_primary": False,
                    "confidence": record_info["confidence"],
                    "supporting_evidence": record_info["reason"],
                    "classification_json": {**page_class, "actual_model": record_info.get("actual_model")},
                    "review_notes": f"Classified by AI model: {record_info.get('actual_model')}",
                    "content_hash": page_data.get("content_hash"),
                    "last_verified_at": timezone.now() if status == "APPROVED" else None
                }
            )
        except Exception as e:
            logger.warning("Could not persist CompanySource for %s (%s): %s", company.company_id, record_info["url"], e)

    def _apply_verified_source(
        self,
        company: Company,
        record_info: Dict[str, Any],
        cand: Dict[str, Any],
        page_data: Dict[str, Any],
        page_class: Dict[str, Any],
        validation: Dict[str, Any],
        comp_res: Dict[str, Any],
        stats: Dict[str, Any]
    ):
        """
        Transactionally updates Company primary URL fields, marks older sources superseded,
        and creates an immutable AuditTrail entry.
        """
        target_field = record_info.get("target_field")
        final_url = record_info.get("final_url")
        if not target_field or not final_url:
            return

        with transaction.atomic():
            # 1. Check existing primary URL on Company
            previous_val = getattr(company, target_field, None)
            if previous_val == final_url:
                # Value is already verified and identical
                return

            # 2. Update company field
            setattr(company, target_field, final_url)

            # If ATS platform was discovered in page_data
            ats_platform = page_data.get("ats_platform")
            if ats_platform and not company.ats_platform:
                company.ats_platform = ats_platform
                if target_field == "jobs_page_url" and not company.ats_url:
                    company.ats_url = final_url

            company.save()

            # 3. Supersede older primary sources in CompanySource registry
            source_type_enum = self._map_to_source_type_choice(record_info["page_type"])
            CompanySource.objects.filter(
                company=company,
                source_type=source_type_enum,
                is_primary=True
            ).update(is_primary=False, verification_status="SUPERSEDED")

            # 4. Upsert approved source as primary
            CompanySource.objects.update_or_create(
                company=company,
                final_url=final_url,
                defaults={
                    "original_url": record_info["url"],
                    "source_type": source_type_enum,
                    "detailed_classification": record_info["page_type"],
                    "discovery_method": cand.get("location", "BODY_CONTENT"),
                    "link_text": cand.get("text", "")[:500],
                    "verification_status": "APPROVED",
                    "is_primary": True,
                    "confidence": record_info["confidence"],
                    "supporting_evidence": record_info["reason"],
                    "classification_json": {**page_class, "actual_model": record_info.get("actual_model")},
                    "review_notes": f"Classified by AI model: {record_info.get('actual_model')}",
                    "content_hash": page_data.get("content_hash"),
                    "previous_url": previous_val,
                    "last_verified_at": timezone.now()
                }
            )

            # 5. Write immutable AuditTrail entry
            AuditTrail.objects.create(
                record_type="Company",
                record_id=company.company_id,
                action=f"VERIFIED_URL_UPDATE_{target_field.upper()}",
                previous_value=previous_val or "",
                new_value=final_url,
                user_role="AI_CLASSIFIER_ENGINE",
                notes=f"Source approved by Stage 2 classification (model: {record_info.get('actual_model')}) & Evidence Gate: {record_info['reason']}",
                timestamp=timezone.now().isoformat()
            )

            comp_res["updates"].append({
                "field": target_field,
                "previous": previous_val,
                "new": final_url,
                "reason": record_info["reason"]
            })
            stats["url_updates_applied"] += 1

    def _map_to_source_type_choice(self, page_type: str) -> str:
        mapping = {
            "CAREERS_LANDING_PAGE": "CAREERS_LANDING",
            "JOBS_LISTING_PAGE": "JOBS_LISTING",
            "ATS_PORTAL": "ATS_PORTAL",
            "INDIVIDUAL_JOB_PAGE": "INDIVIDUAL_JOB",
            "JOB_APPLICATION_PAGE": "JOB_APPLICATION",
            "HR_INFORMATION_PAGE": "HR_PORTAL",
            "CSR_OVERVIEW_PAGE": "CSR_OVERVIEW",
            "CSR_PROJECT_DISCLOSURE": "CSR_PROJECT_DISCLOSURE",
            "CSR_PARTNERSHIP_OR_RFP": "CSR_PARTNERSHIP_RFP",
            "SUSTAINABILITY_OR_ESG_REPORT": "SUSTAINABILITY_REPORT",
            "ANNUAL_REPORT_WITH_CSR_EVIDENCE": "ANNUAL_REPORT",
            "CSR_REPORT": "CSR_REPORT"
        }
        return mapping.get(page_type, "OTHER")

    def _save_checkpoint(self, path: str, company_statuses: Dict[str, Any], stats: Dict[str, Any]):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    "last_updated": timezone.now().isoformat(),
                    "total_processed": len(company_statuses),
                    "processed_company_ids": list(company_statuses.keys()),
                    "company_statuses": company_statuses,
                    "stats": stats
                }, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save checkpoint: %s", e)

    def _print_final_summary(self, stats: Dict[str, Any], dry_run: bool, quota_exhausted: bool, checkpoint_file: str):
        self.stdout.write(self.style.SUCCESS("------------------------------------------------------------"))
        self.stdout.write(self.style.SUCCESS("         DISCOVERY & CLASSIFICATION SUMMARY REPORT          "))
        self.stdout.write(self.style.SUCCESS("------------------------------------------------------------"))

        self.stdout.write(f"Total companies evaluated   : {stats['processed_companies']}")
        self.stdout.write(f"  - Completed (Approved)    : {stats['completed_companies']}")
        self.stdout.write(f"  - Inaccessible / Offline  : {stats['inaccessible_companies']}")
        self.stdout.write(f"  - Review Required         : {stats['review_required_companies']}")
        self.stdout.write(f"  - Unchanged (Skipped)     : {stats['unchanged_skipped_companies']}")
        self.stdout.write(f"  - Error encountered       : {stats['error_companies']}")
        self.stdout.write(f"Total links discovered      : {stats['total_links_discovered']}")
        self.stdout.write(f"Stage 1 Classified links    : {stats['stage1_classified_links']}")
        self.stdout.write(f"Stage 2 Evaluated pages     : {stats['stage2_evaluated_pages']}")
        self.stdout.write(f"Approved Verified sources   : {stats['approved_sources']}")
        self.stdout.write(f"Review Required sources     : {stats['review_required_sources']}")
        self.stdout.write(f"Rejected sources            : {stats['rejected_sources']}")
        self.stdout.write(f"URL updates applied to DB   : {stats['url_updates_applied']} (Dry run: {dry_run})")
        self.stdout.write(f"API calls executed          : {stats['api_calls']}")
        self.stdout.write(f"Cache hits                  : {stats['cache_hits']}")

        models_used = stats.get("models_used", {})
        if models_used:
            self.stdout.write(f"\nModels dynamically used by AI ({cfg.AI_PROVIDER}):")
            for m, count in models_used.items():
                self.stdout.write(f"  - {m}: {count} responses")

        # Explicitly report Gemini vs Fallback usage (Requirement 8)
        gemini_count = sum(cnt for m, cnt in models_used.items() if "gemini" in m.lower())
        fallback_count = sum(cnt for m, cnt in models_used.items() if "fallback" in m.lower())
        self.stdout.write(f"\nClassification Candidate Breakdown:")
        self.stdout.write(f"  - Classified by Gemini : {gemini_count}")
        self.stdout.write(f"  - Fallback utilized    : {'YES (' + str(fallback_count) + ' items)' if fallback_count > 0 else 'NO'}")

        if stats.get("errors"):
            self.stdout.write(self.style.WARNING(f"\nReal errors encountered ({len(stats['errors'])}):"))
            for err in stats["errors"][:5]:
                self.stdout.write(self.style.WARNING(f"  - {err}"))

        if quota_exhausted:
            self.stdout.write(self.style.WARNING(
                "\n* Execution paused due to API quota limits.\n"
                f"* Checkpoint saved at: {checkpoint_file}\n"
                "* To resume once quota is replenished, run:\n"
                "  uv run python manage.py discover_and_verify_company_sources --resume --apply-verified-updates\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\nRun complete."))
        self.stdout.write("=" * 60 + "\n")
