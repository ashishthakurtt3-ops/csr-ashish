import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor

def run():
    qs = Job.objects.filter(job_description__isnull=False).exclude(job_description='')
    total = qs.count()
    print(f"Total jobs with job_description to process: {total}")

    updated = 0
    batch = []
    for idx, j in enumerate(qs.iterator(), 1):
        temp = {
            'role_purpose': j.role_purpose,
            'responsibilities': j.responsibilities,
            'qualifications': j.qualifications,
            'education': j.education,
            'experience': j.experience,
            'technical_skills': j.technical_skills,
            'behavioural_skills': j.behavioural_skills,
            'structured_details': {},
            'job_title': j.job_title,
            'location': j.location,
            'posted_date': j.posted_date,
            'function': j.function,
            'pay_band': j.pay_band,
        }

        changed = False
        UniversalJobDetailExtractor._extract_missing_sections_from_prose(j.job_description, temp)

        if temp.get('role_purpose') and temp['role_purpose'] != j.role_purpose:
            j.role_purpose = temp['role_purpose']
            changed = True
        if temp.get('responsibilities') and temp['responsibilities'] != j.responsibilities:
            j.responsibilities = temp['responsibilities']
            changed = True
        if temp.get('qualifications') and temp['qualifications'] != j.qualifications:
            j.qualifications = temp['qualifications']
            changed = True
        if temp.get('education') and temp['education'] != j.education:
            j.education = temp['education']
            changed = True
        if temp.get('experience') and temp['experience'][:120] != j.experience:
            j.experience = temp['experience'][:120]
            changed = True
        if temp.get('technical_skills') and temp['technical_skills'] != j.technical_skills:
            j.technical_skills = temp['technical_skills']
            changed = True
        if temp.get('behavioural_skills') and temp['behavioural_skills'] != j.behavioural_skills:
            j.behavioural_skills = temp['behavioural_skills']
            changed = True

        if changed:
            batch.append(j)
            updated += 1

        if len(batch) >= 200:
            Job.objects.bulk_update(batch, [
                'role_purpose', 'responsibilities', 'qualifications',
                'education', 'experience', 'technical_skills', 'behavioural_skills'
            ])
            batch = []
            print(f"Processed {idx}/{total} - Updated {updated} jobs...")

    if batch:
        Job.objects.bulk_update(batch, [
            'role_purpose', 'responsibilities', 'qualifications',
            'education', 'experience', 'technical_skills', 'behavioural_skills'
        ])
        print(f"Final batch updated. Total updated: {updated}/{total}")

if __name__ == '__main__':
    run()
