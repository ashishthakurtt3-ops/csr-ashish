import csv
from collections import Counter

decisions_csv = 'reports/stage1a_shortcut/part2/homepage_decisions_051_201.csv'
manual_csv = 'reports/stage1a_shortcut/part2/manual_review_051_201.csv'

with open(decisions_csv, 'r', encoding='utf-8') as f:
    dec_rows = list(csv.DictReader(f))

with open(manual_csv, 'r', encoding='utf-8') as f:
    man_rows = list(csv.DictReader(f))

print(f"Total rows in decisions CSV: {len(dec_rows)}")
print(f"Total rows in manual review CSV: {len(man_rows)}")

class_counts = Counter(r['class'] for r in dec_rows)
print("\nClass counts:")
for cls, cnt in class_counts.most_common():
    print(f"  {cls}: {cnt}")

flag_counts = Counter()
for r in dec_rows:
    flags = [f.strip() for f in r['flags'].split(';') if f.strip() and f.strip() != 'NONE']
    for f in flags:
        flag_counts[f] += 1

print("\nFlag counts:")
for flg, cnt in flag_counts.most_common():
    print(f"  {flg}: {cnt}")

