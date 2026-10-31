import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="tab-pricing"')
print(text[pos:pos+2200])

