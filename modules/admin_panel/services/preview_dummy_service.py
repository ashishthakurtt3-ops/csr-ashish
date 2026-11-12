"""
modules/admin_panel/services/preview_dummy_service.py
=====================================================
Service to manage, seed, parse, import, and export dummy preview datasets
for public / unsubscribed visitors. Decoupled from production database records.
Supports Excel (.xlsx, .xls) multi-sheet workbooks and individual CSV files.
"""

import io
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.db import transaction
from modules.admin_panel.models import (
    PreviewDummyCompany, PreviewDummyJob, PreviewDummyCSRProject
)

DEFAULT_DUMMY_COMPANIES = [
    {
        'company_id': 'DUMMY_COMP_TCS',
        'company_name': 'Tata Consultancy Services Limited',
        'legal_name': 'Tata Consultancy Services Limited',
        'nse_symbol': 'TCS',
        'sector': 'Information Technology & Digital Solutions',
        'headquarters': 'TCS House, Raveline Street, Fort, Mumbai - 400001, Maharashtra, India',
        'cin': 'L72200MH1995PLC085699',
        'isin': 'INE467B01029',
        'operating_locations': 'Mumbai, Maharashtra, IN; Bengaluru, Karnataka, IN; Hyderabad, Telangana, IN; Chennai, Tamil Nadu, IN; Pune, Maharashtra, IN; Kolkata, West Bengal, IN; New Delhi, Delhi, IN',
        'website_url': 'https://www.tcs.com',
        'careers_url': 'https://www.tcs.com/careers/india',
        'csr_portal_url': 'https://www.tcs.com/who-we-are/corporate-social-responsibility',
        'sustainability_url': 'https://www.tcs.com/who-we-are/sustainability',
        'annual_report_url': 'https://www.tcs.com/investor-relations/financial-statements',
        'brsr_url': 'https://www.tcs.com/who-we-are/sustainability/reports',
        'verification_status': 'VERIFIED',
        'job_count': 180,
        'csr_count': 7,
        'display_order': 1,
    },
    {
        'company_id': 'DUMMY_COMP_RELIANCE',
        'company_name': 'Reliance Industries Limited',
        'legal_name': 'Reliance Industries Limited',
        'nse_symbol': 'RELIANCE',
        'sector': 'Energy, Petrochemicals, Retail & Digital Services',
        'headquarters': 'Maker Chambers IV, 222 Nariman Point, Mumbai - 400021, Maharashtra, India',
        'cin': 'L17110MH1973PLC019786',
        'isin': 'INE002A01018',
        'operating_locations': 'Mumbai, Maharashtra, IN; Jamnagar, Gujarat, IN; Dahej, Gujarat, IN; Hazira, Gujarat, IN; Vadodara, Gujarat, IN; Navi Mumbai, Maharashtra, IN',
        'website_url': 'https://www.ril.com',
        'careers_url': 'https://careers.ril.com/rilcareers/frmjobsearch.Aspx',
        'csr_portal_url': 'https://www.ril.com/sustainability',
        'sustainability_url': 'https://www.ril.com/sustainability',
        'annual_report_url': 'https://www.ril.com/investors/financial-reporting',
        'brsr_url': 'https://www.ril.com/sustainability/esg-reports',
        'verification_status': 'VERIFIED',
        'job_count': 240,
        'csr_count': 8,
        'display_order': 2,
    },
    {
        'company_id': 'DUMMY_COMP_INFY',
        'company_name': 'Infosys Limited',
        'legal_name': 'Infosys Limited',
        'nse_symbol': 'INFY',
        'sector': 'IT Consulting, Software & Cloud Platforms',
        'headquarters': 'Electronics City, Hosur Road, Bengaluru - 560100, Karnataka, India',
        'cin': 'L85110KA1981PLC013115',
        'isin': 'INE009A01021',
        'operating_locations': 'Bengaluru, Karnataka, IN; Pune, Maharashtra, IN; Hyderabad, Telangana, IN; Chennai, Tamil Nadu, IN; Mysuru, Karnataka, IN; Chandigarh, Chandigarh, IN',
        'website_url': 'https://www.infosys.com',
        'careers_url': 'https://career.infosys.com',
        'csr_portal_url': 'https://www.infosys.com/infosys-foundation.html',
        'sustainability_url': 'https://www.infosys.com/sustainability.html',
        'annual_report_url': 'https://www.infosys.com/investors/reports-filings/annual-report.html',
        'brsr_url': 'https://www.infosys.com/sustainability/documents/infosys-esg-report-2026.pdf',
        'verification_status': 'VERIFIED',
        'job_count': 220,
        'csr_count': 6,
        'display_order': 3,
    },
    {
        'company_id': 'DUMMY_COMP_HDFCBANK',
        'company_name': 'HDFC Bank Limited',
        'legal_name': 'HDFC Bank Limited',
        'nse_symbol': 'HDFCBANK',
        'sector': 'Banking & Financial Services',
        'headquarters': 'HDFC Bank House, Senapati Bapat Marg, Lower Parel, Mumbai - 400013, Maharashtra, India',
        'cin': 'L65920MH1994PLC080618',
        'isin': 'INE040A01034',
        'operating_locations': 'Mumbai, Maharashtra, IN; Gurugram, Haryana, IN; Chennai, Tamil Nadu, IN; Kolkata, West Bengal, IN; Ahmedabad, Gujarat, IN; Bengaluru, Karnataka, IN',
        'website_url': 'https://www.hdfcbank.com',
        'careers_url': 'https://www.hdfcbank.com/personal/about-us/careers',
        'csr_portal_url': 'https://www.hdfcbank.com/personal/about-us/corporate-governance/csr',
        'sustainability_url': 'https://www.hdfcbank.com/personal/about-us/corporate-governance/csr',
        'annual_report_url': 'https://www.hdfcbank.com/personal/about-us/investor-relations/annual-reports',
        'brsr_url': 'https://www.hdfcbank.com/personal/about-us/corporate-governance/esg-disclosures',
        'verification_status': 'VERIFIED',
        'job_count': 190,
        'csr_count': 5,
        'display_order': 4,
    },
    {
        'company_id': 'DUMMY_COMP_TATAMOTORS',
        'company_name': 'Tata Motors Limited',
        'legal_name': 'Tata Motors Limited',
        'nse_symbol': 'TATAMOTORS',
        'sector': 'Automotive & Electric Mobility',
        'headquarters': 'Bombay House, 24 Homi Mody Street, Mumbai - 400001, Maharashtra, India',
        'cin': 'L28920MH1945PLC004520',
        'isin': 'INE155A01022',
        'operating_locations': 'Mumbai, Maharashtra, IN; Pune, Maharashtra, IN; Jamshedpur, Jharkhand, IN; Sanand, Gujarat, IN; Pantnagar, Uttarakhand, IN; Lucknow, Uttar Pradesh, IN',
        'website_url': 'https://www.tatamotors.com',
        'careers_url': 'https://careers.tatamotors.com',
        'csr_portal_url': 'https://www.tatamotors.com/corporate-social-responsibility/',
        'sustainability_url': 'https://www.tatamotors.com/sustainability/',
        'annual_report_url': 'https://www.tatamotors.com/investors/financials/annual-reports/',
        'brsr_url': 'https://www.tatamotors.com/sustainability/sustainability-reporting/',
        'verification_status': 'VERIFIED',
        'job_count': 150,
        'csr_count': 6,
        'display_order': 5,
    },
    {
        'company_id': 'DUMMY_COMP_MM',
        'company_name': 'Mahindra & Mahindra Limited',
        'legal_name': 'Mahindra & Mahindra Limited',
        'nse_symbol': 'M&M',
        'sector': 'Automotive & Farm Equipment',
        'headquarters': 'Gateway Building, Apollo Bunder, Colaba, Mumbai - 400001, Maharashtra, India',
        'cin': 'L65990MH1945PLC004558',
        'isin': 'INE101A01026',
        'operating_locations': 'Chakan, Chakan, IN; Mumbai A.O, MUM-KND-AD, IN; Mumbai A.O, MUM-KND-AFS(AD), IN; Chennai, Chennai-MRV-AD, IN; Mohali, Mohali-Foundry, IN; Chennai, Chennai, IN',
        'website_url': 'https://www.mahindra.com',
        'careers_url': 'https://jobs.mahindra.com',
        'csr_portal_url': 'https://www.mahindra.com/sustainability',
        'sustainability_url': 'https://www.mahindra.com/sustainability',
        'annual_report_url': 'https://www.mahindra.com/investors/reports-filings',
        'brsr_url': 'https://www.mahindra.com/sustainability/esg-reports',
        'verification_status': 'VERIFIED',
        'job_count': 260,
        'csr_count': 1,
        'display_order': 6,
    },
]

DEFAULT_DUMMY_JOBS = [
    {
        'job_row_id': 'DUMMY_JOB_101',
        'job_title': 'Senior Cloud Infrastructure Architect',
        'company_name': 'Tata Consultancy Services Limited',
        'nse_symbol': 'TCS',
        'location': 'Bengaluru, Karnataka (Hybrid)',
        'work_mode': 'Hybrid',
        'department': 'Cloud Platform & Infrastructure Engineering',
        'experience': '5-9 Years',
        'application_url': 'https://ibegin.tcsapps.com/candidate/?geography=IN&language=EN#job-CLOUD991',
        'posted_date': '2026-11-01',
        'description': 'Lead enterprise hyperscaler cloud migrations, multi-tenant Kubernetes infrastructure orchestration, and zero-trust hybrid cloud architecture across mission-critical platforms.',
        'skills': 'AWS, Azure, Kubernetes, Terraform, Python, Distributed Systems',
        'display_order': 1,
    },
    {
        'job_row_id': 'DUMMY_JOB_102',
        'job_title': 'DevOps & Platform Engineering Lead',
        'company_name': 'Tata Consultancy Services Limited',
        'nse_symbol': 'TCS',
        'location': 'Pune, Maharashtra',
        'work_mode': 'Hybrid',
        'department': 'Platform Engineering & SRE',
        'experience': '4-8 Years',
        'application_url': 'https://ibegin.tcsapps.com/candidate/?geography=IN&language=EN#job-DEVOPS442',
        'posted_date': '2026-11-02',
        'description': 'Architect end-to-end GitOps CI/CD delivery pipelines, automated canary deployments, telemetry monitoring clusters, and high-availability observability fabrics.',
        'skills': 'CI/CD, Docker, Prometheus, Grafana, ArgoCD, Linux Kernel',
        'display_order': 2,
    },
    {
        'job_row_id': 'DUMMY_JOB_103',
        'job_title': 'Const Engr - CHO Projects Civil',
        'company_name': 'Reliance Industries Limited',
        'nse_symbol': 'RELIANCE',
        'location': 'Jamnagar, Gujarat',
        'work_mode': 'On-site',
        'department': 'Project Management & Infrastructure',
        'experience': '4-8 Years',
        'application_url': 'https://careers.ril.com/rilcareers/frmJobSearch.aspx',
        'posted_date': '2026-11-02',
        'description': 'Oversee major mega-infrastructure industrial construction and civil engineering execution at the world-scale Jamnagar refinery and green energy complex.',
        'skills': 'Civil Engineering, Project Planning, QA/QC, Industrial Safety, AutoCAD',
        'display_order': 3,
    },
    {
        'job_row_id': 'DUMMY_JOB_104',
        'job_title': 'Petrochemical Process Reliability Lead',
        'company_name': 'Reliance Industries Limited',
        'nse_symbol': 'RELIANCE',
        'location': 'Dahej, Gujarat',
        'work_mode': 'On-site',
        'department': 'Petrochemicals & Materials Engineering',
        'experience': '5-10 Years',
        'application_url': 'https://careers.ril.com/rilcareers/frmJobSearch.aspx',
        'posted_date': '2026-11-03',
        'description': 'Lead continuous process safety optimization, chemical manufacturing asset lifecycle integrity, and high-yield petrochemical manufacturing efficiency.',
        'skills': 'Chemical Engineering, Process Safety, Root Cause Analysis, HAZOP',
        'display_order': 4,
    },
    {
        'job_row_id': 'DUMMY_JOB_105',
        'job_title': 'Principal AI/ML Solutions Architect',
        'company_name': 'Infosys Limited',
        'nse_symbol': 'INFY',
        'location': 'Bengaluru, Karnataka',
        'work_mode': 'Hybrid',
        'department': 'Applied AI & Cognitive Systems',
        'experience': '7-12 Years',
        'application_url': 'https://career.infosys.com/jobdesc?jobReferenceCode=PRO-AIML992',
        'posted_date': '2026-11-03',
        'description': 'Spearhead enterprise generative AI pipelines, LLM fine-tuning, RAG frameworks, and scalable deep learning model serving across Global 2000 clients.',
        'skills': 'PyTorch, Transformers, LangChain, Vector Databases, Python, MLOps',
        'display_order': 5,
    },
    {
        'job_row_id': 'DUMMY_JOB_106',
        'job_title': 'Senior Java Microservices & Cloud Specialist',
        'company_name': 'Infosys Limited',
        'nse_symbol': 'INFY',
        'location': 'Pune, Maharashtra',
        'work_mode': 'Hybrid',
        'department': 'Digital Modernization & Software Engineering',
        'experience': '4-8 Years',
        'application_url': 'https://career.infosys.com/jobdesc?jobReferenceCode=PRO-JAVA881',
        'posted_date': '2026-11-04',
        'description': 'Build resilient event-driven microservices architectures, Kafka streaming topologies, and high-throughput transactional backends.',
        'skills': 'Java 21, Spring Boot, Apache Kafka, PostgreSQL, Docker, AWS',
        'display_order': 6,
    },
    {
        'job_row_id': 'DUMMY_JOB_107',
        'job_title': 'AVP - Enterprise Credit Risk & AI Analytics',
        'company_name': 'HDFC Bank Limited',
        'nse_symbol': 'HDFCBANK',
        'location': 'Mumbai, Maharashtra',
        'work_mode': 'On-site',
        'department': 'Enterprise Risk Governance & Analytics',
        'experience': '6-10 Years',
        'application_url': 'https://www.hdfcbank.com/personal/about-us/careers',
        'posted_date': '2026-11-04',
        'description': 'Develop statistical underwriting risk scorecards, credit default prediction models, and regulatory compliance algorithms for retail banking products.',
        'skills': 'Credit Risk, Statistical Modeling, Python, SQL, SAS, Basel III',
        'display_order': 7,
    },
    {
        'job_row_id': 'DUMMY_JOB_108',
        'job_title': 'Lead Full Stack Fintech Platform Engineer',
        'company_name': 'HDFC Bank Limited',
        'nse_symbol': 'HDFCBANK',
        'location': 'Gurugram, Haryana',
        'work_mode': 'Hybrid',
        'department': 'Digital Banking & Core Fintech Systems',
        'experience': '4-7 Years',
        'application_url': 'https://www.hdfcbank.com/personal/about-us/careers',
        'posted_date': '2026-11-05',
        'description': 'Architect low-latency digital payment gateways, mobile banking API integrations, and secure PCI-DSS compliant transactional interfaces.',
        'skills': 'TypeScript, Node.js, React, Redis, Distributed Locking, REST APIs',
        'display_order': 8,
    },
    {
        'job_row_id': 'DUMMY_JOB_109',
        'job_title': 'Senior EV Powertrain & Battery Systems Engineer',
        'company_name': 'Tata Motors Limited',
        'nse_symbol': 'TATAMOTORS',
        'location': 'Pune, Maharashtra',
        'work_mode': 'On-site',
        'department': 'Electric Vehicle Powertrain Engineering',
        'experience': '4-8 Years',
        'application_url': 'https://careers.tatamotors.com/jobs/EV-9921',
        'posted_date': '2026-11-05',
        'description': 'Design electric vehicle high-voltage battery packs, thermal management systems, and regenerative braking control algorithms for next-gen EV platforms.',
        'skills': 'MATLAB/Simulink, Battery Management Systems (BMS), HV Architecture, ISO 26262',
        'display_order': 9,
    },
    {
        'job_row_id': 'DUMMY_JOB_110',
        'job_title': 'ADAS Perception & Autonomous Software Specialist',
        'company_name': 'Tata Motors Limited',
        'nse_symbol': 'TATAMOTORS',
        'location': 'Bengaluru, Karnataka',
        'work_mode': 'Hybrid',
        'department': 'Vehicle Software & Autonomous Systems',
        'experience': '5-9 Years',
        'application_url': 'https://careers.tatamotors.com/jobs/ADAS-8812',
        'posted_date': '2026-11-06',
        'description': 'Develop computer vision perception pipelines, sensor fusion algorithms (Radar, Camera, LiDAR), and real-time obstacle detection software.',
        'skills': 'C++, Computer Vision, OpenCV, ROS2, Sensor Fusion, Deep Learning',
        'display_order': 10,
    },
    {
        'job_row_id': 'DUMMY_JOB_111',
        'job_title': 'Senior Automotive Embedded Systems Specialist',
        'company_name': 'Mahindra & Mahindra Limited',
        'nse_symbol': 'M&M',
        'location': 'Chennai, Chennai-MRV-AD, IN',
        'work_mode': 'On-site',
        'department': 'Automotive R&D & Embedded Systems',
        'experience': '4-8 Years',
        'application_url': 'https://jobs.mahindra.com',
        'posted_date': '2026-11-07',
        'description': 'Develop AUTOSAR compliant ECU firmware, CAN/LIN bus communication protocols, and vehicle telemetry integration for flagship SUV lines.',
        'skills': 'Embedded C, AUTOSAR, CANoe, Automotive Ethernet, Microcontrollers',
        'display_order': 11,
    },
]

DEFAULT_DUMMY_CSR = [
    {
        'csr_id': 'DUMMY_CSR_501',
        'project_name': 'TCS Adult Literacy & Rural Digital Empowerment Program',
        'company_name': 'Tata Consultancy Services Limited',
        'category': 'Education & Digital Literacy',
        'state': 'Pan-India',
        'budget': '₹ 38.50 Cr',
        'source_url': 'https://www.tcs.com/who-we-are/corporate-social-responsibility',
        'verification_status': 'PUBLISHED',
        'display_order': 1,
    },
    {
        'csr_id': 'DUMMY_CSR_502',
        'project_name': 'TCS STEM Education & Youth Bridge Initiative',
        'company_name': 'Tata Consultancy Services Limited',
        'category': 'Education & Skill Development',
        'state': 'Maharashtra & Gujarat',
        'budget': '₹ 24.00 Cr',
        'source_url': 'https://www.tcs.com/who-we-are/corporate-social-responsibility',
        'verification_status': 'PUBLISHED',
        'display_order': 2,
    },
    {
        'csr_id': 'DUMMY_CSR_503',
        'project_name': 'Reliance Foundation Bharat Rural Transformation & Water Security',
        'company_name': 'Reliance Industries Limited',
        'category': 'Rural Development & Agriculture',
        'state': 'Gujarat & Madhya Pradesh',
        'budget': '₹ 48.00 Cr',
        'source_url': 'https://www.ril.com/sustainability',
        'verification_status': 'PUBLISHED',
        'display_order': 3,
    },
    {
        'csr_id': 'DUMMY_CSR_504',
        'project_name': 'Dhirubhai Ambani Healthcare Outreach & Mobile Medical Units',
        'company_name': 'Reliance Industries Limited',
        'category': 'Healthcare & Nutrition Support',
        'state': 'Maharashtra & Odisha',
        'budget': '₹ 32.50 Cr',
        'source_url': 'https://www.ril.com/sustainability',
        'verification_status': 'PUBLISHED',
        'display_order': 4,
    },
    {
        'csr_id': 'DUMMY_CSR_505',
        'project_name': 'Infosys Foundation Aarohan Social Innovation Initiative',
        'company_name': 'Infosys Limited',
        'category': 'Skill Development & Technology for Good',
        'state': 'Pan-India',
        'budget': '₹ 28.00 Cr',
        'source_url': 'https://www.infosys.com/infosys-foundation/aarohan-social-innovation-awards.html',
        'verification_status': 'PUBLISHED',
        'display_order': 5,
    },
    {
        'csr_id': 'DUMMY_CSR_506',
        'project_name': 'Tertiary Hospital Medical Equipment & ICU Infrastructure Support',
        'company_name': 'Infosys Limited',
        'category': 'Healthcare & Sanitation',
        'state': 'Rajasthan & Karnataka',
        'budget': '₹ 31.00 Cr',
        'source_url': 'https://www.infosys.com/infosys-foundation/initiatives/healthcare.html',
        'verification_status': 'PUBLISHED',
        'display_order': 6,
    },
    {
        'csr_id': 'DUMMY_CSR_507',
        'project_name': 'HDFC Bank Parivartan: Holistic Rural Development & Micro-Enterprise',
        'company_name': 'HDFC Bank Limited',
        'category': 'Rural Development & Women Empowerment',
        'state': 'Pan-India (24 States)',
        'budget': '₹ 55.00 Cr',
        'source_url': 'https://www.hdfcbank.com/personal/about-us/corporate-governance/csr',
        'verification_status': 'PUBLISHED',
        'display_order': 7,
    },
    {
        'csr_id': 'DUMMY_CSR_508',
        'project_name': 'Zero Dropout Education & Smart Classrooms Initiative',
        'company_name': 'HDFC Bank Limited',
        'category': 'Education & Digital Literacy',
        'state': 'Bihar & West Bengal',
        'budget': '₹ 22.80 Cr',
        'source_url': 'https://www.hdfcbank.com/personal/about-us/corporate-governance/csr',
        'verification_status': 'PUBLISHED',
        'display_order': 8,
    },
    {
        'csr_id': 'DUMMY_CSR_509',
        'project_name': 'Tata Motors Kaushalya: Automotive Technical Apprenticeships for Rural Youth',
        'company_name': 'Tata Motors Limited',
        'category': 'Skill Development & Vocational Training',
        'state': 'Pan-India',
        'budget': '₹ 26.00 Cr',
        'source_url': 'https://www.tatamotors.com/corporate-social-responsibility/',
        'verification_status': 'PUBLISHED',
        'display_order': 9,
    },
    {
        'csr_id': 'DUMMY_CSR_510',
        'project_name': 'Arogya: Mobile Primary Healthcare & Malnutrition Mitigation',
        'company_name': 'Tata Motors Limited',
        'category': 'Healthcare & Sanitation',
        'state': 'Maharashtra, Gujarat & Jharkhand',
        'budget': '₹ 21.50 Cr',
        'source_url': 'https://www.tatamotors.com/corporate-social-responsibility/',
        'verification_status': 'PUBLISHED',
        'display_order': 10,
    },
    {
        'csr_id': 'DUMMY_CSR_511',
        'project_name': 'Mahindra Hariyali: Mass Afforestation & Agro-Forestry Mandate',
        'company_name': 'Mahindra & Mahindra Limited',
        'category': 'Environmental Sustainability & Climate Action',
        'state': 'Maharashtra, Madhya Pradesh & Andhra Pradesh',
        'budget': '₹ 35.00 Cr',
        'source_url': 'https://www.mahindra.com/sustainability',
        'summary': 'Flagship mass afforestation initiative planting climate-resilient fruit and forest trees to enhance green cover and rural farmer livelihoods.',
        'target_districts': 'Araku Valley, Chakan, Nashik, Zaheerabad',
        'implementing_partner': 'Naandi Foundation',
        'verification_status': 'PUBLISHED',
        'display_order': 11,
    },
]


def seed_default_dummy_data(force=False):
    """Seed baseline realistic dummy records if empty or if force=True."""
    with transaction.atomic():
        if force or not PreviewDummyCompany.objects.exists():
            if force:
                PreviewDummyCompany.objects.all().delete()
            for item in DEFAULT_DUMMY_COMPANIES:
                PreviewDummyCompany.objects.update_or_create(
                    company_id=item['company_id'],
                    defaults=item
                )

        if force or not PreviewDummyJob.objects.exists():
            if force:
                PreviewDummyJob.objects.all().delete()
            for item in DEFAULT_DUMMY_JOBS:
                PreviewDummyJob.objects.update_or_create(
                    job_row_id=item['job_row_id'],
                    defaults=item
                )

        if force or not PreviewDummyCSRProject.objects.exists():
            if force:
                PreviewDummyCSRProject.objects.all().delete()
            for item in DEFAULT_DUMMY_CSR:
                PreviewDummyCSRProject.objects.update_or_create(
                    csr_id=item['csr_id'],
                    defaults=item
                )


def get_dummy_preview_summary():
    """Return overview counts of dummy records currently active."""
    return {
        'companies_count': PreviewDummyCompany.objects.filter(is_active=True).count(),
        'jobs_count': PreviewDummyJob.objects.filter(is_active=True).count(),
        'csr_count': PreviewDummyCSRProject.objects.filter(is_active=True).count(),
        'total_records': (
            PreviewDummyCompany.objects.filter(is_active=True).count() +
            PreviewDummyJob.objects.filter(is_active=True).count() +
            PreviewDummyCSRProject.objects.filter(is_active=True).count()
        )
    }


def normalize_key(s):
    if not s:
        return ''
    return str(s).strip().lower().replace(' ', '_').replace('-', '_')


def parse_and_import_dummy_file(uploaded_file, mode='REPLACE', target_category='AUTO'):
    """
    Parse an Excel (.xlsx, .xls) or CSV (.csv) file containing dummy preview data.
    - AUTO mode: detects sheets 'Companies', 'Jobs', 'CSR' in Excel or headers in CSV.
    - REPLACE: clears existing records in target category before inserting.
    - APPEND: updates existing by ID and adds new.
    """
    filename = uploaded_file.name.lower()
    results = {
        'status': 'success',
        'companies_imported': 0,
        'jobs_imported': 0,
        'csr_imported': 0,
        'messages': []
    }

    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
        sheet_names = [s.strip() for s in wb.sheetnames]

        # Check multi-sheet or single sheet
        with transaction.atomic():
            for sname in sheet_names:
                norm_name = sname.lower()
                ws = wb[sname]

                if 'comp' in norm_name or target_category == 'COMPANIES':
                    c_count = _import_companies_from_sheet(ws, mode)
                    results['companies_imported'] += c_count
                    results['messages'].append(f"Imported {c_count} dummy companies from sheet '{sname}'.")

                elif 'job' in norm_name or 'career' in norm_name or target_category == 'JOBS':
                    j_count = _import_jobs_from_sheet(ws, mode)
                    results['jobs_imported'] += j_count
                    results['messages'].append(f"Imported {j_count} dummy jobs from sheet '{sname}'.")

                elif 'csr' in norm_name or 'sustain' in norm_name or 'project' in norm_name or target_category == 'CSR':
                    csr_count = _import_csr_from_sheet(ws, mode)
                    results['csr_imported'] += csr_count
                    results['messages'].append(f"Imported {csr_count} dummy CSR initiatives from sheet '{sname}'.")

            # Fallback if only 1 sheet without explicit category naming
            if len(sheet_names) == 1 and results['companies_imported'] == 0 and results['jobs_imported'] == 0 and results['csr_imported'] == 0:
                ws = wb[sheet_names[0]]
                headers = [normalize_key(cell.value) for cell in ws[1] if cell.value]
                if any('comp' in h for h in headers):
                    c_count = _import_companies_from_sheet(ws, mode)
                    results['companies_imported'] = c_count
                elif any('job' in h or 'title' in h for h in headers):
                    j_count = _import_jobs_from_sheet(ws, mode)
                    results['jobs_imported'] = j_count
                elif any('csr' in h or 'budget' in h for h in headers):
                    csr_count = _import_csr_from_sheet(ws, mode)
                    results['csr_imported'] = csr_count

    elif filename.endswith('.csv'):
        # Parse CSV
        content = uploaded_file.read().decode('utf-8-sig', errors='replace')
        reader = list(csv.DictReader(io.StringIO(content)))
        fieldnames = list(reader[0].keys()) if reader else []
        headers = [normalize_key(h) for h in fieldnames]

        has_comp = any('comp' in h for h in headers)
        has_job = any('job' in h or 'title' in h for h in headers)
        has_csr = any('csr' in h or 'project' in h for h in headers)

        with transaction.atomic():
            if target_category == 'UNIFIED' or (target_category == 'AUTO' and has_comp and (has_job or has_csr) and len(headers) >= 6):
                c_cnt, j_cnt, csr_cnt = _import_unified_from_csv(reader, mode)
                results['companies_imported'] = c_cnt
                results['jobs_imported'] = j_cnt
                results['csr_imported'] = csr_cnt
                results['messages'].append(f"Imported unified dataset from CSV: {c_cnt} companies, {j_cnt} jobs, and {csr_cnt} CSR initiatives.")
            elif target_category == 'COMPANIES' or (target_category == 'AUTO' and has_comp and not has_job):
                c_count = _import_companies_from_csv(reader, mode)
                results['companies_imported'] = c_count
                results['messages'].append(f"Imported {c_count} dummy companies from CSV.")
            elif target_category == 'JOBS' or (target_category == 'AUTO' and has_job):
                j_count = _import_jobs_from_csv(reader, mode)
                results['jobs_imported'] = j_count
                results['messages'].append(f"Imported {j_count} dummy jobs from CSV.")
            elif target_category == 'CSR' or (target_category == 'AUTO' and has_csr):
                csr_count = _import_csr_from_csv(reader, mode)
                results['csr_imported'] = csr_count
                results['messages'].append(f"Imported {csr_count} dummy CSR initiatives from CSV.")
            else:
                results['status'] = 'error'
                results['messages'].append("Could not determine category from CSV headers. Please specify category or use standard columns.")

    return results


def _import_companies_from_sheet(ws, mode):
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        return 0
    headers = [normalize_key(c) for c in rows[0]]
    if mode == 'REPLACE':
        PreviewDummyCompany.objects.all().delete()

    count = 0
    for r_idx, row in enumerate(rows[1:], start=1):
        if not any(row):
            continue
        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        name = str(row_dict.get('company_name') or row_dict.get('name') or '').strip()
        if not name:
            continue
        comp_id = str(row_dict.get('company_id') or f"DUMMY_COMP_{r_idx:03d}").strip()
        PreviewDummyCompany.objects.update_or_create(
            company_id=comp_id,
            defaults={
                'company_name': name,
                'nse_symbol': str(row_dict.get('nse_symbol') or row_dict.get('symbol') or '').strip() or None,
                'sector': str(row_dict.get('sector') or row_dict.get('industry') or 'Corporate Enterprise').strip(),
                'headquarters': str(row_dict.get('headquarters') or row_dict.get('hq') or 'India').strip(),
                'website_url': str(row_dict.get('website_url') or row_dict.get('website') or '').strip() or None,
                'careers_url': str(row_dict.get('careers_url') or row_dict.get('careers') or '').strip() or None,
                'csr_portal_url': str(row_dict.get('csr_portal_url') or row_dict.get('csr') or '').strip() or None,
                'job_count': int(row_dict.get('job_count') or row_dict.get('jobs') or 5),
                'csr_count': int(row_dict.get('csr_count') or row_dict.get('csr_projects') or 3),
                'is_active': True,
                'display_order': r_idx
            }
        )
        count += 1
    return count


def _import_jobs_from_sheet(ws, mode):
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        return 0
    headers = [normalize_key(c) for c in rows[0]]
    if mode == 'REPLACE':
        PreviewDummyJob.objects.all().delete()

    count = 0
    for r_idx, row in enumerate(rows[1:], start=1):
        if not any(row):
            continue
        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        title = str(row_dict.get('job_title') or row_dict.get('title') or '').strip()
        if not title:
            continue
        job_id = str(row_dict.get('job_row_id') or row_dict.get('job_id') or f"DUMMY_JOB_{r_idx:03d}").strip()
        PreviewDummyJob.objects.update_or_create(
            job_row_id=job_id,
            defaults={
                'job_title': title,
                'company_name': str(row_dict.get('company_name') or row_dict.get('company') or 'Verified Corporate').strip(),
                'nse_symbol': str(row_dict.get('nse_symbol') or row_dict.get('symbol') or '').strip() or None,
                'location': str(row_dict.get('location') or 'India').strip(),
                'work_mode': str(row_dict.get('work_mode') or 'Hybrid').strip(),
                'department': str(row_dict.get('department') or 'Technology').strip(),
                'experience': str(row_dict.get('experience') or '3-5 Years').strip(),
                'application_url': str(row_dict.get('application_url') or '').strip() or None,
                'posted_date': str(row_dict.get('posted_date') or '2026-11-01').strip(),
                'is_active': True,
                'display_order': r_idx
            }
        )
        count += 1
    return count


def _import_csr_from_sheet(ws, mode):
    rows = list(ws.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        return 0
    headers = [normalize_key(c) for c in rows[0]]
    if mode == 'REPLACE':
        PreviewDummyCSRProject.objects.all().delete()

    count = 0
    for r_idx, row in enumerate(rows[1:], start=1):
        if not any(row):
            continue
        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        pname = str(row_dict.get('project_name') or row_dict.get('name') or '').strip()
        if not pname:
            continue
        csr_id = str(row_dict.get('csr_id') or f"DUMMY_CSR_{r_idx:03d}").strip()
        PreviewDummyCSRProject.objects.update_or_create(
            csr_id=csr_id,
            defaults={
                'project_name': pname,
                'company_name': str(row_dict.get('company_name') or row_dict.get('company') or 'Verified Enterprise').strip(),
                'category': str(row_dict.get('category') or row_dict.get('sector') or 'Education & Healthcare').strip(),
                'state': str(row_dict.get('state') or 'Pan-India').strip(),
                'budget': str(row_dict.get('budget') or '₹ 10.00 Cr').strip(),
                'source_url': str(row_dict.get('source_url') or '').strip() or None,
                'is_active': True,
                'display_order': r_idx
            }
        )
        count += 1
    return count


def _import_companies_from_csv(reader, mode):
    if mode == 'REPLACE':
        PreviewDummyCompany.objects.all().delete()
    count = 0
    for r_idx, row in enumerate(reader, start=1):
        normalized_row = {normalize_key(k): v for k, v in row.items()}
        name = str(normalized_row.get('company_name') or normalized_row.get('name') or '').strip()
        if not name:
            continue
        comp_id = str(normalized_row.get('company_id') or f"DUMMY_COMP_{r_idx:03d}").strip()
        PreviewDummyCompany.objects.update_or_create(
            company_id=comp_id,
            defaults={
                'company_name': name,
                'nse_symbol': str(normalized_row.get('nse_symbol') or normalized_row.get('symbol') or '').strip() or None,
                'sector': str(normalized_row.get('sector') or normalized_row.get('industry') or 'Corporate Enterprise').strip(),
                'headquarters': str(normalized_row.get('headquarters') or normalized_row.get('hq') or 'India').strip(),
                'website_url': str(normalized_row.get('website_url') or '').strip() or None,
                'careers_url': str(normalized_row.get('careers_url') or '').strip() or None,
                'csr_portal_url': str(normalized_row.get('csr_portal_url') or '').strip() or None,
                'job_count': int(normalized_row.get('job_count') or 5),
                'csr_count': int(normalized_row.get('csr_count') or 3),
                'is_active': True,
                'display_order': r_idx
            }
        )
        count += 1
    return count


def _import_jobs_from_csv(reader, mode):
    if mode == 'REPLACE':
        PreviewDummyJob.objects.all().delete()
    count = 0
    for r_idx, row in enumerate(reader, start=1):
        normalized_row = {normalize_key(k): v for k, v in row.items()}
        title = str(normalized_row.get('job_title') or normalized_row.get('title') or '').strip()
        if not title:
            continue
        job_id = str(normalized_row.get('job_row_id') or normalized_row.get('job_id') or f"DUMMY_JOB_{r_idx:03d}").strip()
        PreviewDummyJob.objects.update_or_create(
            job_row_id=job_id,
            defaults={
                'job_title': title,
                'company_name': str(normalized_row.get('company_name') or 'Verified Corporate').strip(),
                'nse_symbol': str(normalized_row.get('nse_symbol') or '').strip() or None,
                'location': str(normalized_row.get('location') or 'India').strip(),
                'work_mode': str(normalized_row.get('work_mode') or 'Hybrid').strip(),
                'department': str(normalized_row.get('department') or 'Technology').strip(),
                'experience': str(normalized_row.get('experience') or '3-5 Years').strip(),
                'application_url': str(normalized_row.get('application_url') or '').strip() or None,
                'posted_date': str(normalized_row.get('posted_date') or '2026-11-01').strip(),
                'is_active': True,
                'display_order': r_idx
            }
        )
        count += 1
    return count


def _import_csr_from_csv(reader, mode):
    if mode == 'REPLACE':
        PreviewDummyCSRProject.objects.all().delete()
    count = 0
    for r_idx, row in enumerate(reader, start=1):
        normalized_row = {normalize_key(k): v for k, v in row.items()}
        pname = str(normalized_row.get('project_name') or normalized_row.get('name') or '').strip()
        if not pname:
            continue
        csr_id = str(normalized_row.get('csr_id') or f"DUMMY_CSR_{r_idx:03d}").strip()
        PreviewDummyCSRProject.objects.update_or_create(
            csr_id=csr_id,
            defaults={
                'project_name': pname,
                'company_name': str(normalized_row.get('company_name') or 'Verified Enterprise').strip(),
                'category': str(normalized_row.get('category') or normalized_row.get('sector') or 'Education & Healthcare').strip(),
                'state': str(normalized_row.get('state') or 'Pan-India').strip(),
                'budget': str(normalized_row.get('budget') or '₹ 10.00 Cr').strip(),
                'source_url': str(normalized_row.get('source_url') or '').strip() or None,
                'is_active': True,
                'display_order': r_idx
            }
        )
        count += 1
    return count


def _import_unified_from_csv(rows, mode):
    """
    Imports companies, jobs, and CSR initiatives from a single unified CSV file
    where each row contains company details, job vacancy details, and Section 135 CSR allocations.
    """
    if mode == 'REPLACE':
        PreviewDummyCompany.objects.all().delete()
        PreviewDummyJob.objects.all().delete()
        PreviewDummyCSRProject.objects.all().delete()

    company_order_map = {}
    job_order = PreviewDummyJob.objects.count()
    csr_order = PreviewDummyCSRProject.objects.count()
    j_count = 0
    csr_count = 0

    for r_idx, row in enumerate(rows, start=1):
        normalized_row = {normalize_key(k): str(v or '').strip() for k, v in row.items()}
        cname = normalized_row.get('company_name') or normalized_row.get('company') or normalized_row.get('name') or ''

        if cname:
            symbol = normalized_row.get('nse_symbol') or normalized_row.get('symbol') or ''
            comp_id = normalized_row.get('company_id') or (f"DUMMY_COMP_{symbol.upper()}" if symbol else f"DUMMY_COMP_{r_idx:03d}")

            if comp_id not in company_order_map:
                company_order_map[comp_id] = len(company_order_map) + 1

            defaults = {
                'company_name': cname,
                'legal_name': normalized_row.get('legal_name') or normalized_row.get('legal_entity_name') or cname,
                'cin': normalized_row.get('cin') or normalized_row.get('corporate_identity_number') or None,
                'isin': normalized_row.get('isin') or normalized_row.get('isin_code') or None,
                'operating_locations': normalized_row.get('operating_locations') or normalized_row.get('locations') or normalized_row.get('regions') or None,
                'annual_report_url': normalized_row.get('annual_report_url') or normalized_row.get('annual_report') or None,
                'brsr_url': normalized_row.get('brsr_url') or normalized_row.get('brsr_report') or normalized_row.get('esg_report') or None,
                'sustainability_url': normalized_row.get('sustainability_url') or normalized_row.get('csr_portal_url') or None,
                'nse_symbol': symbol or None,
                'sector': normalized_row.get('sector') or normalized_row.get('industry') or 'Corporate Enterprise',
                'headquarters': normalized_row.get('headquarters') or normalized_row.get('hq') or 'India',
                'website_url': normalized_row.get('website_url') or None,
                'careers_url': normalized_row.get('careers_url') or None,
                'csr_portal_url': normalized_row.get('csr_portal_url') or normalized_row.get('csr_url') or None,
                'is_active': True,
                'display_order': company_order_map[comp_id]
            }
            if normalized_row.get('job_count'):
                try:
                    defaults['job_count'] = int(normalized_row['job_count'])
                except Exception:
                    pass
            if normalized_row.get('csr_count'):
                try:
                    defaults['csr_count'] = int(normalized_row['csr_count'])
                except Exception:
                    pass

            PreviewDummyCompany.objects.update_or_create(
                company_id=comp_id,
                defaults=defaults
            )

        # Job Extraction
        job_title = normalized_row.get('job_title') or normalized_row.get('job') or normalized_row.get('title') or ''
        if job_title and cname:
            job_order += 1
            job_id = normalized_row.get('job_row_id') or normalized_row.get('job_id') or f"DUMMY_JOB_{job_order:03d}"
            PreviewDummyJob.objects.update_or_create(
                job_row_id=job_id,
                defaults={
                    'job_title': job_title,
                    'company_name': cname,
                    'nse_symbol': normalized_row.get('nse_symbol') or normalized_row.get('symbol') or None,
                    'location': normalized_row.get('job_location') or normalized_row.get('location') or 'India',
                    'work_mode': normalized_row.get('work_mode') or normalized_row.get('job_work_mode') or 'Hybrid',
                    'department': normalized_row.get('department') or normalized_row.get('job_department') or 'Technology',
                    'experience': normalized_row.get('experience') or normalized_row.get('job_experience') or '3-6 Years',
                    'application_url': normalized_row.get('job_apply_url') or normalized_row.get('application_url') or normalized_row.get('job_url') or None,
                    'description': normalized_row.get('job_description') or normalized_row.get('description') or f"We are seeking an experienced {job_title} to join {cname}.",
                    'skills': normalized_row.get('job_skills') or normalized_row.get('skills') or 'Enterprise Architecture, Agile, Cloud Delivery, Python, SQL',
                    'posted_date': normalized_row.get('posted_date') or '2026-11-01',
                    'is_active': True,
                    'display_order': job_order
                }
            )
            j_count += 1

        # CSR Extraction
        csr_name = normalized_row.get('csr_project_name') or normalized_row.get('project_name') or normalized_row.get('csr_initiative') or normalized_row.get('csr_project') or ''
        if csr_name and cname:
            csr_order += 1
            csr_id = normalized_row.get('csr_id') or f"DUMMY_CSR_{csr_order:03d}"
            PreviewDummyCSRProject.objects.update_or_create(
                csr_id=csr_id,
                defaults={
                    'project_name': csr_name,
                    'company_name': cname,
                    'category': normalized_row.get('csr_category') or normalized_row.get('category') or 'Education & Healthcare',
                    'state': normalized_row.get('csr_state') or normalized_row.get('state') or 'Pan-India',
                    'target_districts': normalized_row.get('csr_districts') or normalized_row.get('target_districts') or 'Aspirational Districts',
                    'budget': normalized_row.get('csr_budget') or normalized_row.get('budget') or '₹ 10.00 Cr',
                    'source_url': normalized_row.get('csr_source_url') or normalized_row.get('source_url') or normalized_row.get('csr_portal_url') or None,
                    'summary': normalized_row.get('csr_summary') or normalized_row.get('summary') or f"Statutory CSR initiative under Section 135 by {cname}.",
                    'implementing_partner': normalized_row.get('csr_partner') or normalized_row.get('implementing_partner') or 'Registered NGO Agency',
                    'is_active': True,
                    'display_order': csr_order
                }
            )
            csr_count += 1

    c_count = len(company_order_map)
    return c_count, j_count, csr_count


def build_sample_unified_csv():
    """
    Generates a complete, high-fidelity Unified CSV for flagship Indian enterprises,
    featuring all corporate entity master attributes (CIN, ISIN, Legal Name, Operating Locations),
    real-world job openings, and statutory Section 135 CSR projects.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Company Name", "Legal Entity Name", "CIN", "ISIN", "NSE Symbol", "Sector", "Headquarters",
        "Operating Locations", "Website URL", "Careers URL", "CSR Portal URL", "Annual Report URL", "BRSR URL",
        "Job Title", "Job Location", "Work Mode", "Department", "Experience", "Job Description", "Job Skills", "Job Apply URL",
        "CSR Project Name", "CSR Category", "CSR State", "CSR Target Districts", "CSR Budget", "CSR Summary", "CSR Partner", "CSR Source URL"
    ])

    pairs = [
        # 1. TCS
        (DEFAULT_DUMMY_COMPANIES[0], DEFAULT_DUMMY_JOBS[0], DEFAULT_DUMMY_CSR[0]),
        (DEFAULT_DUMMY_COMPANIES[0], DEFAULT_DUMMY_JOBS[1], DEFAULT_DUMMY_CSR[1]),
        # 2. Reliance
        (DEFAULT_DUMMY_COMPANIES[1], DEFAULT_DUMMY_JOBS[2], DEFAULT_DUMMY_CSR[2]),
        (DEFAULT_DUMMY_COMPANIES[1], DEFAULT_DUMMY_JOBS[3], DEFAULT_DUMMY_CSR[3]),
        # 3. Infosys
        (DEFAULT_DUMMY_COMPANIES[2], DEFAULT_DUMMY_JOBS[4], DEFAULT_DUMMY_CSR[4]),
        (DEFAULT_DUMMY_COMPANIES[2], DEFAULT_DUMMY_JOBS[5], DEFAULT_DUMMY_CSR[5]),
        # 4. HDFC Bank
        (DEFAULT_DUMMY_COMPANIES[3], DEFAULT_DUMMY_JOBS[6], DEFAULT_DUMMY_CSR[6]),
        (DEFAULT_DUMMY_COMPANIES[3], DEFAULT_DUMMY_JOBS[7], DEFAULT_DUMMY_CSR[7]),
        # 5. Tata Motors
        (DEFAULT_DUMMY_COMPANIES[4], DEFAULT_DUMMY_JOBS[8], DEFAULT_DUMMY_CSR[8]),
        (DEFAULT_DUMMY_COMPANIES[4], DEFAULT_DUMMY_JOBS[9], DEFAULT_DUMMY_CSR[9]),
        # 6. Mahindra & Mahindra
        (DEFAULT_DUMMY_COMPANIES[5], DEFAULT_DUMMY_JOBS[10], DEFAULT_DUMMY_CSR[10]),
    ]

    for c, j, csr in pairs:
        writer.writerow([
            c['company_name'], c.get('legal_name', c['company_name']), c.get('cin', ''), c.get('isin', ''),
            c['nse_symbol'], c['sector'], c['headquarters'], c.get('operating_locations', ''),
            c['website_url'], c['careers_url'], c['csr_portal_url'], c.get('annual_report_url', ''), c.get('brsr_url', ''),
            j['job_title'], j['location'], j['work_mode'], j['department'], j['experience'],
            j.get('description', ''), j.get('skills', ''), j['application_url'],
            csr['project_name'], csr['category'], csr['state'], csr.get('target_districts', ''),
            csr['budget'], csr.get('summary', ''), csr.get('implementing_partner', ''), csr['source_url']
        ])

    return output.getvalue()


def build_sample_excel_template():
    """Build a multi-sheet Excel workbook pre-populated with realistic dummy data."""
    wb = openpyxl.Workbook()
    
    # 1. Sheet: Companies
    ws_comp = wb.active
    ws_comp.title = "Companies"
    comp_headers = [
        "Company ID", "Company Name", "NSE Symbol", "Sector", "Headquarters",
        "Website URL", "Careers URL", "CSR Portal URL", "Job Count", "CSR Count"
    ]
    _style_header_row(ws_comp, comp_headers)
    for c in DEFAULT_DUMMY_COMPANIES:
        ws_comp.append([
            c['company_id'], c['company_name'], c['nse_symbol'], c['sector'],
            c['headquarters'], c['website_url'], c['careers_url'], c['csr_portal_url'],
            c['job_count'], c['csr_count']
        ])
    _auto_column_widths(ws_comp)

    # 2. Sheet: Jobs
    ws_jobs = wb.create_sheet("Jobs")
    job_headers = [
        "Job ID", "Job Title", "Company Name", "NSE Symbol", "Location",
        "Work Mode", "Department", "Experience", "Application URL", "Posted Date"
    ]
    _style_header_row(ws_jobs, job_headers)
    for j in DEFAULT_DUMMY_JOBS:
        ws_jobs.append([
            j['job_row_id'], j['job_title'], j['company_name'], j['nse_symbol'],
            j['location'], j['work_mode'], j['department'], j['experience'],
            j['application_url'], j['posted_date']
        ])
    _auto_column_widths(ws_jobs)

    # 3. Sheet: CSR Initiatives
    ws_csr = wb.create_sheet("CSR Initiatives")
    csr_headers = [
        "CSR ID", "Project Name", "Company Name", "Category", "State", "Budget", "Source URL"
    ]
    _style_header_row(ws_csr, csr_headers)
    for p in DEFAULT_DUMMY_CSR:
        ws_csr.append([
            p['csr_id'], p['project_name'], p['company_name'], p['category'],
            p['state'], p['budget'], p['source_url']
        ])
    _auto_column_widths(ws_csr)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _style_header_row(ws, headers):
    ws.append(headers)
    header_fill = PatternFill(start_color="0A6CFF", end_color="0A6CFF", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _auto_column_widths(ws):
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

