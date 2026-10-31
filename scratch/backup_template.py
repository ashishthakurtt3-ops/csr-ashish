import re

# Read current file
with open('templates/admin/ai_config/index.html', 'r', encoding='utf-8') as f:
    original = f.read()

# Make backup
with open('templates/admin/ai_config/index.html.bak', 'w', encoding='utf-8') as f:
    f.write(original)

print("Backup created. Original length:", len(original))

