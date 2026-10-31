import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = 'id="portal-wallet-section-card"'
idx = html.find(target)
print(html[idx:idx+1800])

