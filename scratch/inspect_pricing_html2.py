with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="tab-pricing"')
print(text[pos+2500:pos+6000].encode('ascii', 'replace').decode('ascii'))

