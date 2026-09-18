from pathlib import Path
import re

file = Path("../web.py")

text = file.read_text(encoding="utf-8")

patterns = [
    r'@app\.route\(.*?\n(?:.*\n)*?def .*?:',
]

# backup
Path("../web_before_clean_routes.py").write_text(
    text,
    encoding="utf-8"
)

lines = text.splitlines()

hasil = []
skip = False

for line in lines:

    if line.startswith("@app.route"):
        skip = True
        continue

    if skip and line.startswith("def "):
        skip = False
        continue

    if skip:
        continue

    hasil.append(line)


file.write_text(
    "\n".join(hasil),
    encoding="utf-8"
)

print("WEB ROUTE CLEAN SELESAI")
print("Backup: web_before_clean_routes.py")