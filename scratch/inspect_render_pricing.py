import sys
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(5440, min(len(lines), 5530)):
    sys.stdout.buffer.write(f"{i+1}: {lines[i]}".encode('utf-8'))

