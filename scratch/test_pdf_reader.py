import io
from curl_cffi import requests as cffi_requests
from pypdf import PdfReader

url = "https://sbi.co.in/documents/77530/52947104/SCO_27_SELECT_LIST_AVP%28IS+AUDIT%29.pdf/c8925d1f-d8e3-a1a7-b703-7c6a2446215e?t=1779799823836"
r = cffi_requests.get(url, impersonate="chrome124", timeout=12)
print("PDF fetch status:", r.status_code, "Len:", len(r.content))
if r.status_code == 200:
    reader = PdfReader(io.BytesIO(r.content))
    print("Num pages:", len(reader.pages))
    t = reader.pages[0].extract_text()
    print("Page 1 text excerpt:", t[:200])

