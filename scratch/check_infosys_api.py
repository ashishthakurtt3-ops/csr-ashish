import requests, re, json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': '*/*',
}

# Check Infosys search API
try:
    # Common Infosys API patterns
    for endpoint in [
        'https://career.infosys.com/joblist/search',
        'https://career.infosys.com/api/jobs',
        'https://career.infosys.com/careerapi/joblist',
        'https://career.infosys.com/services/jobs'
    ]:
        res = requests.post(endpoint, headers=headers, json={"page": 1}, timeout=5)
        print(endpoint, res.status_code)
except Exception as e:
    print('Infosys API error:', e)
