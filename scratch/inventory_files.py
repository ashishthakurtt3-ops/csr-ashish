import os

print("PATH | LINES | SIZE_BYTES")
for base in ['config', 'modules', 'templates', 'static', 'scripts']:
    for root, dirs, files in os.walk(base):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel_p = os.path.relpath(p).replace('\\', '/')
            try:
                size = os.path.getsize(p)
                with open(p, 'rb') as fh:
                    lines = len(fh.readlines())
                print(f"{rel_p} | {lines} | {size}")
            except Exception as e:
                print(f"{rel_p} | ERR | {e}")

