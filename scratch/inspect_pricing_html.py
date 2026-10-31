import sys
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'pricing-plans-grid' in l:
        for j in range(max(0, i-10), min(len(lines), i+60)):
            sys.stdout.buffer.write(f"{j+1}: {lines[j]}".encode('utf-8'))
        break
