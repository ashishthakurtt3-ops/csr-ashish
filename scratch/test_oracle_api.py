import requests, json

oracle_host = "https://eibd.fa.em2.oraclecloud.com"
site_number = "CX_1"
api_url = f"{oracle_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber={site_number}&expand=requisitionList&offset=0&limit=2"

resp = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'})
print('Status:', resp.status_code)
data = resp.json()
items = data.get('items', [])
if items:
    reqs = items[0].get('requisitionList', [])
    print(f"Found {len(reqs)} reqs")
    if reqs:
        print("Sample req keys:", list(reqs[0].keys()))
        for k in ['Title', 'Id', 'PrimaryLocation', 'PostingDescription', 'ExternalDescriptionStr', 'ShortDescriptionStr']:
            if k in reqs[0]:
                print(f"{k}: {str(reqs[0][k])[:100]}")
