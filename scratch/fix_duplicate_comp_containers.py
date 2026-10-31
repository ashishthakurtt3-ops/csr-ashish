import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

target_block = """            <!-- Dynamic Three-Tier Feature Comparison Matrix -->
            <div id="pricing-comparison-container"></div>"""

# Count occurrences
count = html.count(target_block)
print(f"Total occurrences of target_block: {count}")

# We want to replace the first 5 occurrences with empty string, keeping only the last one!
parts = html.split(target_block)
if len(parts) == 7: # 6 occurrences means 7 parts
    # Keep parts[0..4] joined with nothing, and parts[5..6] joined with target_block
    new_html = "".join(parts[:5]) + parts[5] + target_block + parts[6]
    with open('templates/website/index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("Successfully removed the first 5 duplicates, leaving only the one inside #tab-pricing!")
else:
    print(f"Unexpected number of parts: {len(parts)}")

