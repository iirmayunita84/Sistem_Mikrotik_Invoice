#tools/fix_imports.py
"""
===========================================================
 FIX WEB IMPORT
 Mikrotik Invoice Refactor Tool
===========================================================

Fungsi:

1. Scan Blueprint di routes/
2. Tambahkan import blueprint ke web.py
3. Register blueprint otomatis
4. Rapikan import routes

===========================================================
"""


from pathlib import Path
import re

# ==========================================================
# CONFIG
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent.parent

WEB_FILE = BASE_DIR / "web.py"

ROUTES_DIR = BASE_DIR / "routes"

# ==========================================================
# UTIL
# ==========================================================
def garis():

    print("=" * 60)

def read_text(file):

    return file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

def write_text(file, content):

    file.write_text(
        content,
        encoding="utf-8"
    )

# ==========================================================
# SCAN BLUEPRINT
# ==========================================================
def scan_blueprints():

    """
    Scan seluruh file routes.
    Nama blueprint dibuat otomatis dari nama file.

    auth_routes.py
        -> auth_bp

    invoice_routes.py
        -> invoice_bp
    """

    result = []

    for file in sorted(ROUTES_DIR.glob("*_routes.py")):

        module = file.stem

        nama = module.replace("_routes", "")

        result.append(
            {
                "file": file.name,
                "module": module,
                "blueprint": f"{nama}_bp",
            }
        )

    return result

# ==========================================================
# GENERATE IMPORT
# ==========================================================
def generate_imports(blueprints):

    imports = []

    for item in blueprints:

        imports.append(
            f"from routes.{item['module']} import bp as {item['blueprint']}"
        )

    return imports

# ==========================================================
# ADD IMPORT TO WEB.PY
# ==========================================================
def add_imports(content, imports):

    marker = "# AUTO BLUEPRINT IMPORT"

    lines = content.splitlines()

    # Cari import terakhir HANYA di bagian header
    last_import = -1

    for i, line in enumerate(lines):

        # Berhenti saat masuk bagian PATH
        if "# ================= PATH =================" in line:
            break

        s = line.strip()

        if s.startswith("import ") or s.startswith("from "):
            last_import = i

    # Semua import yang sudah ada
    existing_imports = {
        line.strip()
        for line in lines
        if line.strip().startswith(("import ", "from "))
    }

    # Ambil hanya import yang belum ada
    new_imports = [
        imp
        for imp in imports
        if imp not in existing_imports
    ]

    # Tidak ada import baru
    if not new_imports:
        return content

    block = []

    # Marker hanya sekali
    if marker not in content:
        block.append("")
        block.append(marker)

    block.extend(new_imports)
    block.append("")

    if last_import == -1:
        return "\n".join(block) + "\n" + content

    lines[last_import + 1:last_import + 1] = block

    return "\n".join(lines)

# ==========================================================
# ADD REGISTER BLUEPRINT
# ==========================================================
def add_register_blueprints(content, blueprints):

    marker = "# AUTO REGISTER BLUEPRINT"

    block = []

    if marker not in content:
        block.append("")
        block.append(marker)

    for item in blueprints:

        line = f"app.register_blueprint({item['blueprint']})"

        # Sudah ada di web.py
        if line in content:
            continue

        block.append(line)

    # Tidak ada yang perlu ditambah
    added = 0

    for item in blueprints:

        line = f"app.register_blueprint({item['blueprint']})"

        if line in content:
            continue

        block.append(line)
        added += 1

    if added == 0:
        return content

    block.append("")
    block = "\n".join(block)

    target = 'if __name__ == "__main__":'

    if target in content:

        idx = content.find(target)

        content = (
            content[:idx]
            + block
            + "\n"
            + content[idx:]
        )

    else:

        content += "\n\n" + block

    return content

# ==========================================================
# FIX WEB IMPORT
# ==========================================================
def fix_web_import():


    garis()

    print(
        "FIX WEB.PY BLUEPRINT IMPORT"
    )

    garis()



    if not WEB_FILE.exists():

        print(
            "web.py tidak ditemukan"
        )

        return False



    blueprints = scan_blueprints()



    if not blueprints:


        print(
            "Tidak ada blueprint ditemukan"
        )

        return False



    content = read_text(
        WEB_FILE
    )



    imports = generate_imports(
        blueprints
    )



    content = add_imports(
        content,
        imports
    )



    content = add_register_blueprints(
        content,
        blueprints
    )



    write_text(
        WEB_FILE,
        content
    )



    print()

    print(
        "Blueprint ditemukan:"
    )


    for item in blueprints:

        print(
            "-",
            item["blueprint"],
            "<-",
            item["file"]
        )



    print()

    print(
        "web.py berhasil diperbaiki"
    )


    garis()


    return True

# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":

    fix_web_import()