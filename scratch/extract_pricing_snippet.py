import re

with open('scratch/daanveda_pricing.html', 'r', encoding='utf-8') as f:
    text = f.read()

pricing_match = re.search(r'(<main[^>]*pricing.*?</main>)', text, re.DOTALL | re.IGNORECASE)
if pricing_match:
    print('Found pricing main, length:', len(pricing_match.group(1)))
    with open('scratch/daanveda_pricing_snippet.html', 'w', encoding='utf-8') as f:
        f.write(pricing_match.group(1)[:30000])
    print('Saved snippet to scratch/daanveda_pricing_snippet.html')
else:
    print('Pricing main not found, looking for class containing pr-')
    matches = re.findall(r'<div[^>]*class=["\'][^"\']*pr-[^"\']*["\'][^>]*>', text)
    print('pr- classes found:', set(matches[:20]))

