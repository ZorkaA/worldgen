import re

with open("backend/app/generator/zones.py", "r") as f:
    content = f.read()

# Change terrace_step from 8.0 to 20.0 to make terraces much wider horizontally
content = content.replace("terrace_step = 8.0 # 8 meter vertical steps", "terrace_step = 20.0 # 20 meter vertical steps (wider horizontal plateaus)")

with open("backend/app/generator/zones.py", "w") as f:
    f.write(content)
print("Patched terrace_step")
