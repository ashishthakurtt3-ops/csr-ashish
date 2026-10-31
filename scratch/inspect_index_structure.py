import re

with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("Length of index.html:", len(text))
print("\n--- Header / Nav elements ---")
header = re.findall(r'<header[^>]*>.*?</header>', text, re.DOTALL)
if header:
    print(header[0][:600])

print("\n--- Main sections / Views ---")
sections = re.findall(r'<section[^>]*id=["\']([^"\']+)["\']', text)
print("Section IDs:", sections)

div_views = re.findall(r'<div[^>]*id=["\']([^"\']*(?:view|modal|tab|panel|container|section)[^"\']*)["\']', text, re.I)
print("View/Modal/Container IDs:", div_views[:30])

print("\n--- Modals ---")
modals = re.findall(r'id=["\']([^"\']*modal[^"\']*)["\']', text, re.I)
print("Modal IDs:", modals)

