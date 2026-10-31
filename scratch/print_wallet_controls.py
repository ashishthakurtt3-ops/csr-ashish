import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="portal-wallet-section-card"')
print(text[pos+1500:pos+3200])

