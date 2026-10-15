import urllib.request, json

headers = {'User-Agent': 'Mozilla/5.0'}
url = "https://eibd.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1&expand=requisitionList&offset=0&limit=5"
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
        items = data.get('items', [{}])[0].get('requisitionList', [])
        for item in items[:5]:
            print("Title:", item.get('Title'))
            print("Id:", item.get('Id'))
            print("Organization:", item.get('Organization'))
            print("PrimaryLocation:", item.get('PrimaryLocation'))
except Exception as e:
    print("Err:", e)
