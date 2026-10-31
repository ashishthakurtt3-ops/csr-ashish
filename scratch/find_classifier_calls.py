import os, sys, re

sys.stdout.reconfigure(encoding='utf-8')

scan_dirs = ['modules', 'config', 'management', 'scripts']

searches = ['TwoStagePageClassifier', 'ai_api_client', 'AIClient', 'ai_classifier']

for s in searches:
    pat = re.compile(re.escape(s), re.IGNORECASE)
    print(f"\n=== SEARCH: {s} ===")
    for sdir in scan_dirs:
        for root, dirs, files in os.walk(sdir):
            if '__pycache__' in root:
                continue
            for f in files:
                if f.endswith('.py'):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                            for idx, line in enumerate(fp, 1):
                                if pat.search(line):
                                    print(f"  {fpath}:{idx} -> {line.strip()[:110]}")
                    except Exception:
                        pass

