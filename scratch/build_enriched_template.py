# Script to build and verify the enriched index.html
import os

with open('templates/admin/ai_config/index.html', 'r', encoding='utf-8') as f:
    orig_content = f.read()

print("Original index.html lines:", len(orig_content.splitlines()))

