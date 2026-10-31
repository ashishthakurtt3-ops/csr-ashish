import csv

def generate_detailed_audit():
    with open('reports/accuracy_pilot_batch_001_050/job_candidates.csv', 'r', encoding='utf-8') as f:
        jobs = list(csv.DictReader(f))
    with open('reports/accuracy_pilot_batch_001_050/opportunity_candidates.csv', 'r', encoding='utf-8') as f:
        opps = list(csv.DictReader(f))
    with open('reports/accuracy_pilot_batch_001_050/csr_candidates.csv', 'r', encoding='utf-8') as f:
        csrs = list(csv.DictReader(f))
        
    print(f"Loaded: {len(jobs)} jobs, {len(opps)} opportunities, {len(csrs)} CSR projects.")

if __name__ == '__main__':
    generate_detailed_audit()

