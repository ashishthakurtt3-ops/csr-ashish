with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="pricing-plans-grid"')
print(text[pos:pos+2500].encode('ascii', 'replace').decode('ascii'))

