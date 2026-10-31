import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/css/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

def show_snippet(label, start_str, end_str=None, length=800):
    idx = text.find(start_str)
    print(f"=== {label} (at {idx}) ===")
    if idx != -1:
        if end_str:
            end_idx = text.find(end_str, idx)
            print(text[idx:end_idx + len(end_str)])
        else:
            print(text[idx:idx+length])

show_snippet("ROOT", ":root {", "}")
show_snippet("HEADER NAV", ".header-nav {", "}")
show_snippet("NAV LINK BTN", ".nav-link-btn {", "}")
show_snippet("PRICING HERO", ".pricing-hero {", "}")
show_snippet("PRICING CARD", ".pricing-card {", "}")
show_snippet("PRICING CARD FEATURED", ".pricing-card.featured {", "}")

