with open('templates/website/login.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_block = [
    '            {% if login_error %}\n',
    '            <div class="messages" id="auth-messages-container">\n',
    '                <div class="alert alert-error" style="display:flex; justify-content:space-between; align-items:center; gap:10px;">\n',
    '                    <span>{{ login_error }}</span>\n',
    '                    <button type="button" onclick="this.parentElement.remove()" style="background:none; border:none; color:inherit; font-size:16px; cursor:pointer; line-height:1; padding:0 4px; opacity:0.75;" title="Dismiss">✕</button>\n',
    '                </div>\n',
    '            </div>\n',
    '            {% elif messages %}\n',
    '            <div class="messages" id="auth-messages-container">\n',
    '                {% for message in messages %}\n',
    '                {% if message.tags != "error" %}\n',
    '                <div class="alert {% if message.tags == "success" %}alert-success{% else %}alert-info{% endif %}" style="display:flex; justify-content:space-between; align-items:center; gap:10px;">\n',
    '                    <span>{{ message }}</span>\n',
    '                    <button type="button" onclick="this.parentElement.remove()" style="background:none; border:none; color:inherit; font-size:16px; cursor:pointer; line-height:1; padding:0 4px; opacity:0.75;" title="Dismiss">✕</button>\n',
    '                </div>\n',
    '                {% endif %}\n',
    '                {% endfor %}\n',
    '            </div>\n',
    '            {% endif %}\n',
]

start = None
end = None
for i, line in enumerate(lines):
    if '{% if messages %}' in line:
        start = i
    if start is not None and '{% endif %}' in line:
        end = i + 1
        break

assert start is not None and end is not None, f"Could not find block: start={start}, end={end}"
lines[start:end] = new_block

with open('templates/website/login.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print(f"SUCCESS: Replaced lines {start} to {end}")
