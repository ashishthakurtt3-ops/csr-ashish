import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/css/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('.pricing-hero')
end_pos = text.find('/* ==========================================================================\n   MODAL ARCHITECTURE', pos)
print(text[pos-100:end_pos])

