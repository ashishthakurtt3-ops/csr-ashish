import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

scan_dirs = ['modules', 'config', 'templates', 'static', 'tests']

patterns = {
    'google.generativeai': re.compile(r'google\.generativeai', re.IGNORECASE),
    'openai': re.compile(r'\bopenai\b', re.IGNORECASE),
    'anthropic': re.compile(r'\banthropic\b', re.IGNORECASE),
    'openrouter': re.compile(r'openrouter', re.IGNORECASE),
    'AIClient': re.compile(r'\bAIClient\b'),
    'GeminiApiClient': re.compile(r'\bGeminiApiClient\b'),
    'OpenRouterApiClient': re.compile(r'\bOpenRouterApiClient\b'),
    'ai_api_client': re.compile(r'ai_api_client', re.IGNORECASE),
    'ai_classifier': re.compile(r'ai_classifier', re.IGNORECASE),
    'ai_config': re.compile(r'ai_config', re.IGNORECASE),
    'ai_telemetry': re.compile(r'ai_telemetry', re.IGNORECASE),
    'test_provider_live': re.compile(r'test_provider_live', re.IGNORECASE),
}

hits = {k: [] for k in patterns}

for sdir in scan_dirs:
    for root, dirs, files in os.walk(sdir):
        if '__pycache__' in root:
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ['.py', '.html', '.js', '.json', '.sql']:
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                        lines = fp.readlines()
                        for i, line in enumerate(lines, 1):
                            for p_name, pat in patterns.items():
                                if pat.search(line):
                                    hits[p_name].append((filepath, i, line.strip()[:100]))
                except Exception as err:
                    pass

print("=== AI SEARCH RESULTS ===", flush=True)
for p_name, occurrences in hits.items():
    print(f"\n--- {p_name} ({len(occurrences)} occurrences) ---", flush=True)
    files = {}
    for fp, line_no, text in occurrences:
        files.setdefault(fp, []).append((line_no, text))
    for fp, locs in files.items():
        print(f"  File: {fp} ({len(locs)} matches)")
        for lno, txt in locs[:3]:
            print(f"    L{lno}: {txt}")
        if len(locs) > 3:
            print(f"    ... and {len(locs)-3} more")
