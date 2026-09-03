with open("frontend/src/style.css", "r") as f:
    content = f.read()

content = content.replace("var(--bg-tertiary)", "var(--bg-input)")
content = content.replace("var(--border-color)", "var(--border-subtle)")
content = content.replace("var(--accent-color)", "var(--color-primary)")
content = content.replace("var(--text-color)", "var(--text-primary)")

with open("frontend/src/style.css", "w") as f:
    f.write(content)
print("style patched")
