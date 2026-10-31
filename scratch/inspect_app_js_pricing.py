with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('function renderPricingGrid')
print(text[pos+1500:pos+3500].encode('ascii', 'replace').decode('ascii'))

