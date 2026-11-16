css_path = r"D:\Projects\PolicySetu\app\static\css\main.css"
with open(css_path, "r", encoding="utf-8") as f:
    text = f.read()

target = """.theme-icon-dark { display: none; }
.theme-icon-light { display: block; }

[data-theme="dark"] .theme-icon-dark { display: block; }
[data-theme="dark"] .theme-icon-light { display: none; }"""

replacement = """.theme-toggle-btn .theme-icon-dark { display: none !important; }
.theme-toggle-btn .theme-icon-light { display: block !important; }

[data-theme="dark"] .theme-toggle-btn .theme-icon-dark { display: block !important; }
[data-theme="dark"] .theme-toggle-btn .theme-icon-light { display: none !important; }"""

if target in text:
    new_text = text.replace(target, replacement, 1)
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Updated theme-icon display specificity successfully!")
else:
    print("Target not found")
