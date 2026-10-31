import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

for tab_id in ['tab-companies', 'tab-jobs']:
    target = f'id="{tab_id}"'
    pos = text.find(target)
    print(f'=== {tab_id} search bar ===')
    if pos != -1:
        print(text[pos+400:pos+1500])

