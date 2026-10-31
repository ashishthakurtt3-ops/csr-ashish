import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/css/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('MOBILE & MULTI-DEVICE RESPONSIVE SUITE')
print(text[pos:])

