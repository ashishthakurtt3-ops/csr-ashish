import os, re

patterns = ['classify_links', 'classify_page']

for p in patterns:
    print(f"\n=== PATTERN: {p} ===")
    for scan_dir in ['modules', 'tests']:
        for root, dirs, files in os.walk(scan_dir):
            if '__pycache__' in root:
                continue
            for f in files:
                if f.endswith('.py'):
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as s:
                            for lno, line in enumerate(s, 1):
                                if p in line:
                                    print(f"  {fp}:{lno} -> {line.strip()[:100]}")
                    except Exception:
                        pass

