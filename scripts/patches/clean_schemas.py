with open("backend/app/core/schemas.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "generate_roads: Optional[bool] = None" in line:
        if i > 0 and "generate_roads" in lines[i-1]:
            continue
    new_lines.append(line)

# Let's just use regex to remove duplicate generate_roads
import re
content = "".join(new_lines)
content = re.sub(r'(generate_roads: Optional\[bool\] = None\n\s*)+', r'\1', content)

with open("backend/app/core/schemas.py", "w") as f:
    f.write(content)
