import requests, re

js = requests.get('https://jobs.happiestminds.com/happiestminds/main.898a74dd6a3ec25c.js').text
apis = set(re.findall(r'https?://[^\s\"\'\<\>]+', js))
for a in apis:
    if any(k in a.lower() for k in ['api', 'job', 'career', 'darwin', 'backend', 'recruitment', 'node']):
        print('Found API in JS:', a)

endpoints = set(re.findall(r'[\'\"/](?:api|jobs|v1|v2|candidate|career)/[^\s\"\'\<\>]+', js))
for ep in endpoints:
    print('Found relative endpoint:', ep)

