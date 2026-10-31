import os

for root, dirs, files in os.walk('.'):
    if 'node_modules' in root or '.venv' in root or '.git' in root:
        continue
    for f in files:
        if 'test' in f.lower() and f.endswith('.py'):
            print(os.path.join(root, f).replace('\\', '/'))

